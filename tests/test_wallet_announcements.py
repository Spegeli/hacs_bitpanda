"""A wallet new to the Portfolio is announced (announcements.py): the event
bitpanda_wallet_added always, a notification unless it is switched off --
once the wallet's device exists. Never for the wallets the first refresh
finds, nor for those a restart, a reload, a currency change or a deleted
group creates again. End to end, Bitpanda mocked as in tests/test_init.py."""
import asyncio
from contextlib import contextmanager
from datetime import timedelta
import logging
from unittest.mock import AsyncMock, patch

from awesomeversion import AwesomeVersion
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import __version__ as HAVERSION
from homeassistant.core import CoreState, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    translation,
)
from homeassistant.helpers.event import async_track_device_registry_updated_event
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.bitpanda import purge
from custom_components.bitpanda.announcements import WalletAnnouncer, escape_markdown
from custom_components.bitpanda.api import BitpandaApiError
from custom_components.bitpanda.const import DOMAIN, UNKNOWN_ASSET_RETRY
from custom_components.bitpanda.devices import find_entry_device
from custom_components.bitpanda.naming import price_device_identifier, wallet_unique_id

from tests.conftest import load_fixture

_CLIENT = "custom_components.bitpanda.api.BitpandaApiClient."
_NOTIFY = "custom_components.bitpanda.announcements.persistent_notification.async_create"
_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"
_USD_ID = "b88b8879-efe3-11eb-b56f-0691764446a7"


def _record(symbol: str, type_: str | None = None) -> dict:
    return next(
        a for a in load_fixture("assets-sample.json")
        if a["symbol"] == symbol and (type_ is None or a["type"] == type_)
    )


BTC, VSN, SOL = _record("BTC"), _record("VSN"), _record("SOL")
GOLD = _record("XAU", "commodity")
_CASH = {"currency_id": _EUR_ID, "balance": {"value": "10.00"}}
# The two sensors of Vision's wallet, as long as nothing is staked.
_VSN_BALANCE = "sensor.bitpanda_vision_vsn_wallet_available"
_VSN_TOTAL = "sensor.bitpanda_vision_vsn_wallet_total"

# Home Assistant restores the disabled_by of an entity created again only
# from 2025.7 on: before, a wallet bought again comes back with its sensors
# enabled.
_RESTORES_DISABLED_SENSORS = pytest.mark.skipif(
    AwesomeVersion(HAVERSION) < AwesomeVersion("2025.7.0"),
    reason="Home Assistant restores a re-created entity's disabled_by from 2025.7 on",
)


def _position(asset: dict, *, staked: bool = False) -> dict:
    """One unit of `asset`, worth 100; half of it staked if `staked`."""
    return {
        "asset_id": asset["id"],
        "balance": {"value": "1.00000000"},
        "available_balance": {"value": "0.50000000" if staked else "1.00000000"},
        "currency_balance": {"value": "100.00"},
    }


def _answer(*assets: dict) -> list[dict]:
    """/portfolio's answer: a position in each of `assets`, and cash."""
    return [*(_position(asset) for asset in assets), _CASH]


def _lookup(**kwargs):
    return [a for a in load_fixture("assets-sample.json") if a["id"] == kwargs.get("asset_id")]


@pytest.fixture
def portfolio_api():
    """Bitpanda as the Portfolio asks it; the account holds Bitcoin."""
    with patch(
        f"{_CLIENT}async_get_portfolio", AsyncMock(return_value=_answer(BTC))
    ) as portfolio, patch(
        f"{_CLIENT}async_get_portfolio_history", AsyncMock(return_value={"return_percentage": 1.5})
    ), patch(f"{_CLIENT}async_get_earn_configs", AsyncMock(return_value=[])), patch(
        f"{_CLIENT}async_get_operations", AsyncMock(return_value=[])
    ), patch(f"{_CLIENT}async_get_assets", AsyncMock(side_effect=_lookup)):
        yield portfolio


@pytest.fixture
def events(hass):
    """Every bitpanda_wallet_added fired."""
    return async_capture_events(hass, "bitpanda_wallet_added")


@pytest.fixture
def notifications():
    """Every persistent notification created."""
    with patch(_NOTIFY) as create:
        yield create


def _portfolio_entry(hass, **options) -> MockConfigEntry:
    """A Portfolio in EUR, with `options`: none -- English, notifications on."""
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR",
              "currency_id": _EUR_ID},
        options=options,
    )
    entry.add_to_hass(hass)
    return entry


async def _setup(hass, entry) -> None:
    """Set up `entry` and wait until it is loaded."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def _next_refresh(hass, freezer) -> None:
    """The Portfolio's next regular refresh: Home Assistant's clock moves on
    past its update interval, and the refresh it scheduled runs to its end
    -- a background task, which only wait_background_tasks waits for."""
    freezer.tick(timedelta(minutes=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def _flush(hass, freezer) -> None:
    """Let the list's delayed save run. Only the freezer moves the event
    loop's clock, which the save waits for (tests/test_portfolio_store.py)."""
    freezer.tick(timedelta(seconds=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def _restart(hass, entry, freezer) -> None:
    """Home Assistant stopped and started again: the list's last change is
    written as it stops, and the stores portfolio_store.py keeps in memory are
    gone; the registries and the files stay."""
    await _flush(hass, freezer)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    del hass.data[f"{DOMAIN}_portfolio_stores"]
    await _setup(hass, entry)


async def _update_from_a_version_without_the_list(hass, entry, hass_storage, freezer) -> None:
    """Home Assistant restarted into this version from one without the list:
    the registries stay, and there is no file yet; the catalogue's records,
    kept in memory, are gone like the list."""
    await _flush(hass, freezer)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    del hass.data[f"{DOMAIN}_portfolio_stores"]
    del hass.data[f"{DOMAIN}_asset_directory"]
    del hass_storage[f"{DOMAIN}.portfolio.{entry.entry_id}"]
    await _setup(hass, entry)


def _stored(hass_storage, entry) -> list[str]:
    """The assets the file of `entry`'s list holds."""
    return hass_storage[f"{DOMAIN}.portfolio.{entry.entry_id}"]["data"]["known_wallets"]


def _remember(hass_storage, entry, *assets: dict) -> None:
    """A file for `entry`'s list that holds `assets`, as an earlier start
    left it."""
    key = f"{DOMAIN}.portfolio.{entry.entry_id}"
    hass_storage[key] = {
        "version": 1,
        "key": key,
        "data": {"known_wallets": sorted(asset["id"] for asset in assets)},
    }


def _wallet_device(hass, entry, asset: dict) -> dr.DeviceEntry | None:
    """The wallet device of `asset`; None while there is none."""
    return find_entry_device(
        dr.async_get(hass), entry.entry_id, f"{entry.entry_id}_wallet_{asset['id']}"
    )


def _vision_added(device: dr.DeviceEntry, *, hint: bool) -> str:
    """The English notification on Vision's wallet, on `device` -- with the
    second paragraph on its disabled sensors if `hint`."""
    link = f"/config/devices/device/{device.id}"
    message = (
        f"The Portfolio added a new wallet: **[Vision (VSN) Wallet]({link})** "
        "in the group Cryptocurrencies."
    )
    if hint:
        message += (
            f"\n\nIts sensors are disabled. You can enable them on its [device page]({link})."
        )
    return message


def _disabled_by(hass, *entity_ids: str) -> list[er.RegistryEntryDisabler | None]:
    """Who disabled each of `entity_ids`, as the entity registry has it."""
    ent_reg = er.async_get(hass)
    return [ent_reg.async_get(entity_id).disabled_by for entity_id in entity_ids]


async def _bought_sold_and_bought_again(
    hass, entry, portfolio_api, freezer, *, disabled: tuple[str, ...]
) -> dr.DeviceEntry:
    """Vision bought, the sensors `disabled` of its wallet disabled by the
    user, sold until its wallet went -- the asset leaves the list -- and
    bought again. Returns the wallet device of the first purchase."""
    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)
    device = _wallet_device(hass, entry, VSN)
    ent_reg = er.async_get(hass)
    for entity_id in disabled:
        ent_reg.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.USER)
    portfolio_api.return_value = _answer(BTC)
    for _ in range(3):
        await _next_refresh(hass, freezer)
    assert _wallet_device(hass, entry, VSN) is None
    assert VSN["id"] not in entry.runtime_data.known_wallets

    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)
    return device


async def _delete_on_its_device_page(hass, hass_ws_client, entry, device) -> dict:
    """What "Delete" on a device page sends, on the frontend of Home
    Assistant 2025.5 (tests/test_init.py says more)."""
    assert await async_setup_component(hass, "config", {})
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "config/device_registry/remove_config_entry",
            "config_entry_id": entry.entry_id,
            "device_id": device.id,
        }
    )
    return await client.receive_json()


@contextmanager
def _texts_lacking_the_message(hass, *languages: str, key: str = "wallet_added"):
    """Within it, Home Assistant reads this integration's translation files
    as if those of `languages` lacked the notification's text `key`: by
    default its message.

    `hass` forgets every translation loaded so far, so that each is loaded
    through this: the test plugin loads them once for all tests and keeps
    them in one cache (translations_once), where they may be loaded already
    -- and where a text dropped here would stay dropped for the tests after
    this one."""
    cache = translation._async_get_translations_cache(hass)
    cache.cache_data = type(cache.cache_data)({}, {})
    load = translation._load_translations_files_by_language

    def _load(files):
        loaded = load(files)
        for language in languages:
            loaded.get(language, {}).get(DOMAIN, {}).get("exceptions", {}).pop(key, None)
        return loaded

    with patch.object(translation, "_load_translations_files_by_language", _load):
        yield


# --- What is new ----------------------------------------------------------------------


async def test_the_first_refresh_announces_nothing_and_knows_every_held_asset_but_the_unlisted(
    hass, portfolio_api, events, notifications, hass_storage, freezer
):
    """No list yet, as after a new setup: the wallets found are no news, and
    what is held begins the list. Solana's balances cannot be read, so it
    has no wallet yet, but it is held. Gold is not in Bitpanda's catalogue:
    its wallet, once the catalogue lists it, is news."""
    portfolio_api.return_value = [
        *_answer(BTC, VSN, GOLD),
        {"asset_id": SOL["id"], "balance": {"value": "unreadable"}},
    ]
    without_gold = AsyncMock(
        side_effect=lambda **kwargs: (
            [] if kwargs.get("asset_id") == GOLD["id"] else _lookup(**kwargs)
        )
    )
    with patch(f"{_CLIENT}async_get_assets", without_gold):
        entry = _portfolio_entry(hass)
        await _setup(hass, entry)
    await _flush(hass, freezer)

    assert _wallet_device(hass, entry, VSN) is not None
    assert events == []
    notifications.assert_not_called()
    assert _stored(hass_storage, entry) == sorted([BTC["id"], VSN["id"], SOL["id"]])


async def test_a_wallet_named_only_a_refresh_after_setup_is_not_announced(
    hass, portfolio_api, events, notifications, freezer
):
    """Vision's lookup fails at the first refresh -- a rate limit, a
    timeout: it has no wallet yet, but it is held, so it is known. Its
    wallet, named a refresh later, is no news."""
    portfolio_api.return_value = _answer(BTC, VSN)
    failing = AsyncMock(side_effect=BitpandaApiError("HTTP 503 from /assets"))
    with patch(f"{_CLIENT}async_get_assets", failing):
        entry = _portfolio_entry(hass)
        await _setup(hass, entry)
    assert _wallet_device(hass, entry, VSN) is None

    await _next_refresh(hass, freezer)

    assert _wallet_device(hass, entry, VSN) is not None
    assert events == []
    notifications.assert_not_called()


async def test_a_bought_asset_is_announced_once_its_device_exists(
    hass, portfolio_api, events, notifications, hass_storage, freezer
):
    """Vision, bought: Home Assistant creates its wallet's device as it adds
    the first of the wallet's two sensors, and the creation announces the
    wallet -- once, linking to that device -- and the asset joins the list."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(BTC, VSN)

    await _next_refresh(hass, freezer)

    device = _wallet_device(hass, entry, VSN)
    assert [event.data for event in events] == [
        {
            "device_id": device.id,
            "asset_id": VSN["id"],
            "symbol": "VSN",
            "name": "Vision",
            "wallet": "Vision (VSN) Wallet",
            "category": "crypto",
        }
    ]
    notifications.assert_called_once_with(
        hass,
        "The Portfolio added a new wallet: "
        f"**[Vision (VSN) Wallet](/config/devices/device/{device.id})** "
        "in the group Cryptocurrencies.",
        "New Bitpanda wallet",
        notification_id=f"bitpanda_wallet_added_{VSN['id']}",
    )
    await _flush(hass, freezer)
    assert _stored(hass_storage, entry) == sorted([BTC["id"], VSN["id"]])


async def test_an_asset_bought_again_after_its_wallet_went_is_announced(
    hass, portfolio_api, events, notifications, freezer
):
    """Sold: its wallet goes after the confirmed misses, and the asset
    leaves the list. Bought again, its wallet is news."""
    portfolio_api.return_value = _answer(BTC, VSN)
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(BTC)
    for _ in range(3):
        await _next_refresh(hass, freezer)
    assert _wallet_device(hass, entry, VSN) is None
    assert VSN["id"] not in entry.runtime_data.known_wallets

    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)

    assert [event.data["asset_id"] for event in events] == [VSN["id"]]
    notifications.assert_called_once()


async def test_an_asset_bought_again_after_the_user_deleted_its_wallet_is_announced(
    hass, portfolio_api, events, notifications, freezer, hass_ws_client
):
    """Sold, and its wallet deleted on its device page before it went by
    itself: after the reload that follows, the asset is neither held nor
    has a wallet, so it leaves the list. Bought again, its wallet is news."""
    portfolio_api.return_value = _answer(BTC, VSN)
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(BTC)
    await _next_refresh(hass, freezer)

    async def _answer_like_a_request(*_args, **_kwargs):
        # The page's hook starts the reload at once (__init__.py), and the
        # page removes the wallet only once the hook returns. A real request
        # suspends the reload before its first refresh, so the wallet is
        # gone by then; without a suspension the whole reload would run
        # inside the hook, the wallet still registered.
        await asyncio.sleep(0)
        return portfolio_api.return_value

    portfolio_api.side_effect = _answer_like_a_request
    response = await _delete_on_its_device_page(
        hass, hass_ws_client, entry, _wallet_device(hass, entry, VSN)
    )
    await hass.async_block_till_done()
    assert response["success"]
    assert VSN["id"] not in entry.runtime_data.known_wallets

    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)

    assert [event.data["asset_id"] for event in events] == [VSN["id"]]
    notifications.assert_called_once()


async def test_an_asset_bought_again_after_its_group_was_deleted_is_announced(
    hass, portfolio_api, events, notifications, freezer
):
    """Sold, and its group deleted -- the wallet with it -- before the
    wallet went by itself: the asset is neither held nor has a wallet, so it
    leaves the list. Bought again, its wallet is news."""
    portfolio_api.return_value = _answer(BTC, GOLD)
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(BTC)
    await _next_refresh(hass, freezer)
    [metal] = [group for group in entry.subentries.values() if group.unique_id == "metal"]

    hass.config_entries.async_remove_subentry(entry, metal.subentry_id)
    await hass.async_block_till_done()
    await _next_refresh(hass, freezer)
    assert GOLD["id"] not in entry.runtime_data.known_wallets

    portfolio_api.return_value = _answer(BTC, GOLD)
    await _next_refresh(hass, freezer)

    assert [event.data["asset_id"] for event in events] == [GOLD["id"]]
    notifications.assert_called_once()


async def test_an_asset_the_catalogue_lists_later_is_announced(
    hass, portfolio_api, events, notifications, freezer
):
    """Held, but not in Bitpanda's catalogue at the first refresh: no wallet,
    and not known. Once the catalogue lists it, its wallet is news."""
    listed = [BTC]
    catalogue = AsyncMock(
        side_effect=lambda **kwargs: [a for a in listed if a["id"] == kwargs.get("asset_id")]
    )
    portfolio_api.return_value = _answer(BTC, VSN)
    with patch(f"{_CLIENT}async_get_assets", catalogue):
        entry = _portfolio_entry(hass)
        await _setup(hass, entry)
        assert VSN["id"] not in entry.runtime_data.known_wallets

        listed.append(VSN)
        freezer.tick(UNKNOWN_ASSET_RETRY)
        await _next_refresh(hass, freezer)

    assert _wallet_device(hass, entry, VSN) is not None
    assert [event.data["asset_id"] for event in events] == [VSN["id"]]
    notifications.assert_called_once()


async def test_with_new_entities_disabled_a_bought_asset_is_announced_with_the_hint(
    hass, portfolio_api, events, notifications, freezer
):
    """The Portfolio's system option "Enable newly added entities" is off:
    Vision, bought, gets its wallet device, but its sensors are registered
    disabled and never added. The device's creation announces the wallet,
    and the notification says that its sensors are disabled. A sensor
    enabled later -- Home Assistant reloads the entry 30 seconds after -- is
    no news."""
    entry = _portfolio_entry(hass)
    hass.config_entries.async_update_entry(entry, pref_disable_new_entities=True)
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(BTC, VSN)

    await _next_refresh(hass, freezer)

    device = _wallet_device(hass, entry, VSN)
    assert [event.data for event in events] == [
        {
            "device_id": device.id,
            "asset_id": VSN["id"],
            "symbol": "VSN",
            "name": "Vision",
            "wallet": "Vision (VSN) Wallet",
            "category": "crypto",
        }
    ]
    notifications.assert_called_once_with(
        hass,
        "The Portfolio added a new wallet: "
        f"**[Vision (VSN) Wallet](/config/devices/device/{device.id})** "
        "in the group Cryptocurrencies."
        "\n\n"
        "Its sensors are disabled. You can enable them on its "
        f"[device page](/config/devices/device/{device.id}).",
        "New Bitpanda wallet",
        notification_id=f"bitpanda_wallet_added_{VSN['id']}",
    )
    assert _disabled_by(hass, _VSN_BALANCE, _VSN_TOTAL) == [
        er.RegistryEntryDisabler.INTEGRATION
    ] * 2

    er.async_get(hass).async_update_entity(_VSN_BALANCE, disabled_by=None)
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(_VSN_BALANCE) is not None
    assert len(events) == 1
    notifications.assert_called_once()


@_RESTORES_DISABLED_SENSORS
async def test_a_wallet_bought_again_with_all_its_sensors_disabled_is_announced_with_the_hint(
    hass, portfolio_api, events, notifications, freezer
):
    """Vision's two sensors, disabled by the user before the sale: bought
    again after its wallet went, the wallet's device comes back with its id
    and its sensors disabled, never added. The device's return announces the
    wallet, and the notification says that its sensors are disabled."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)

    first = await _bought_sold_and_bought_again(
        hass, entry, portfolio_api, freezer, disabled=(_VSN_BALANCE, _VSN_TOTAL)
    )

    device = _wallet_device(hass, entry, VSN)
    assert device.id == first.id
    assert _disabled_by(hass, _VSN_BALANCE, _VSN_TOTAL) == [er.RegistryEntryDisabler.USER] * 2
    assert [event.data["device_id"] for event in events] == [device.id, device.id]
    assert [call.args[1] for call in notifications.call_args_list] == [
        _vision_added(device, hint=False),
        _vision_added(device, hint=True),
    ]


# --- What is not new -------------------------------------------------------------------


async def test_a_restart_announces_nothing(hass, portfolio_api, events, notifications, freezer):
    """Every wallet is created again at a start, one announced before it
    too: none is news."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)
    assert len(events) == 1

    await _restart(hass, entry, freezer)

    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_available") is not None
    assert len(events) == 1
    notifications.assert_called_once()


async def test_an_asset_bought_back_after_a_restart_before_its_wallet_went_is_not_announced(
    hass, portfolio_api, events, notifications, freezer
):
    """Sold, Home Assistant restarted, and bought back before the misses
    removed its wallet: the manager starts afresh -- as at a reload -- and
    tracks no wallet of an asset not held, but this one is still registered,
    so the asset stays known. The wallet never went: no news."""
    portfolio_api.return_value = _answer(BTC, VSN)
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    wallet = _wallet_device(hass, entry, VSN)
    portfolio_api.return_value = _answer(BTC)
    await _next_refresh(hass, freezer)
    await _restart(hass, entry, freezer)

    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)

    assert _wallet_device(hass, entry, VSN).id == wallet.id
    assert events == []
    notifications.assert_not_called()
    assert VSN["id"] in entry.runtime_data.known_wallets


async def test_an_asset_sold_and_bought_back_before_its_wallet_went_is_not_announced(
    hass, portfolio_api, events, notifications, freezer
):
    """Sold, and bought back before the misses removed its wallet: the
    wallet never went, so it is no news."""
    portfolio_api.return_value = _answer(BTC, VSN)
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    wallet = _wallet_device(hass, entry, VSN)
    portfolio_api.return_value = _answer(BTC)
    for _ in range(2):
        await _next_refresh(hass, freezer)
    assert _wallet_device(hass, entry, VSN).id == wallet.id

    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)

    assert _wallet_device(hass, entry, VSN).id == wallet.id
    assert events == []
    notifications.assert_not_called()


async def test_an_asset_sold_before_the_update_and_bought_back_before_its_wallet_went_is_not_announced(
    hass, portfolio_api, events, notifications, hass_storage, freezer
):
    """Sold just before the update to the version that brings the list, and
    bought back before the misses removed its wallet: the first start of
    that version finds no list and does not hold the asset, but its wallet is
    still registered, so the asset begins the list. The wallet never went:
    no news."""
    portfolio_api.return_value = _answer(BTC, VSN)
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    wallet = _wallet_device(hass, entry, VSN)
    portfolio_api.return_value = _answer(BTC)
    await _next_refresh(hass, freezer)
    await _update_from_a_version_without_the_list(hass, entry, hass_storage, freezer)

    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)

    assert _wallet_device(hass, entry, VSN).id == wallet.id
    assert events == []
    notifications.assert_not_called()
    assert VSN["id"] in entry.runtime_data.known_wallets


async def test_a_wallet_whose_asset_the_catalogue_dropped_at_the_update_is_no_news_once_listed(
    hass, portfolio_api, events, notifications, hass_storage, freezer
):
    """Held with its wallet before the update, but not in Bitpanda's
    catalogue at the first start of the version that brings the list: its
    wallet is still registered, so the asset begins the list, and the wallet
    the catalogue names again is no news."""
    listed = [BTC, VSN]
    catalogue = AsyncMock(
        side_effect=lambda **kwargs: [a for a in listed if a["id"] == kwargs.get("asset_id")]
    )
    portfolio_api.return_value = _answer(BTC, VSN)
    with patch(f"{_CLIENT}async_get_assets", catalogue):
        entry = _portfolio_entry(hass)
        await _setup(hass, entry)
        wallet = _wallet_device(hass, entry, VSN)
        listed.remove(VSN)
        await _update_from_a_version_without_the_list(hass, entry, hass_storage, freezer)

        listed.append(VSN)
        freezer.tick(UNKNOWN_ASSET_RETRY)
        await _next_refresh(hass, freezer)

    assert _wallet_device(hass, entry, VSN).id == wallet.id
    assert events == []
    notifications.assert_not_called()
    assert VSN["id"] in entry.runtime_data.known_wallets


async def test_a_configure_save_announces_nothing(
    hass, portfolio_api, events, notifications, hass_storage, freezer
):
    """Saving under Configure right after a purchase was announced reloads
    the Portfolio before the list's change is written: the reload keeps the
    list it had, so it announces nothing again."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    await _flush(hass, freezer)
    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)
    assert len(events) == 1
    assert _stored(hass_storage, entry) == [BTC["id"]]
    calls = portfolio_api.call_count

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"language": {"language": "de"}, "notifications": {"notify_new_wallets": True}},
    )
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()

    # The reload's first refresh.
    assert portfolio_api.call_count == calls + 1
    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_available") is not None
    assert len(events) == 1
    notifications.assert_called_once()


async def test_a_deleted_group_coming_back_announces_nothing(
    hass, portfolio_api, events, notifications, freezer
):
    """A group the user deleted took its wallets along; the next refresh
    creates them again, in a new group -- no news."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    [group] = entry.subentries.values()
    hass.config_entries.async_remove_subentry(entry, group.subentry_id)
    await hass.async_block_till_done()
    assert _wallet_device(hass, entry, BTC) is None

    await _next_refresh(hass, freezer)

    assert _wallet_device(hass, entry, BTC) is not None
    assert events == []
    notifications.assert_not_called()


async def test_a_wallet_created_again_before_the_start_ends_is_announced_once(
    hass, portfolio_api, events, notifications, hass_storage, freezer
):
    """Bought while Home Assistant was off: its announcement waits for the
    start's end, the asset not known yet. Should a refresh before that end
    create its wallet again -- its group deleted in between -- the wallet
    is on its way already, and is announced once."""
    entry = _portfolio_entry(hass)
    _remember(hass_storage, entry, BTC)
    portfolio_api.return_value = _answer(BTC, VSN)
    hass.set_state(CoreState.not_running)
    await _setup(hass, entry)
    [group] = entry.subentries.values()
    hass.config_entries.async_remove_subentry(entry, group.subentry_id)
    await hass.async_block_till_done()
    await _next_refresh(hass, freezer)
    assert _wallet_device(hass, entry, VSN) is not None

    await hass.async_start()
    await hass.async_block_till_done()

    assert [event.data["asset_id"] for event in events] == [VSN["id"]]
    notifications.assert_called_once()


async def test_a_currency_change_announces_nothing(hass, portfolio_api, events, notifications):
    """The change removes every wallet with its device (purge.py), and the
    reload creates them again: none is news."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)

    assert await purge.async_purge_portfolio(hass, entry)
    assert _wallet_device(hass, entry, BTC) is None
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, "currency": "USD", "currency_id": _USD_ID}
    )
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert _wallet_device(hass, entry, BTC) is not None
    assert events == []
    notifications.assert_not_called()


def _by_symbol_or_id(**kwargs):
    """/assets as the upgrade (by symbol) and the Portfolio (by id) ask it."""
    return [
        a for a in load_fixture("assets-sample.json")
        if a["symbol"] == kwargs.get("symbol") or a["id"] == kwargs.get("asset_id")
    ]


async def test_an_upgrade_from_a_date_version_announces_nothing(
    hass, portfolio_api, events, notifications, hass_storage, freezer
):
    """A version 1 install, upgraded (tests/test_migration.py): the
    Portfolio's first setup finds the wallets the upgrade carried over --
    no news -- and begins the list with what is held."""
    # The upgrade runs inside the domain's own setup, so the domain is set up
    # already: the Price Tracker it might create must not set it up again.
    hass.config.components.add(DOMAIN)
    entry = MockConfigEntry(
        domain=DOMAIN, version=1, title="Bitpanda",
        data={"api_key": "legacy-key", "currency": "EUR"},
        options={
            "tracked_assets": [],
            "tracked_wallets": ["cryptocoin_BTC", "commodity_metal_XAU"],
        },
    )
    entry.add_to_hass(hass)
    legacy_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_wallets")},
        name="Bitpanda Wallets",
    )
    for legacy_id, object_id in (
        ("cryptocoin_BTC", "bitpanda_wallets_btc_wallet"),
        ("commodity_metal_XAU", "bitpanda_wallets_xau_wallet"),
    ):
        er.async_get(hass).async_get_or_create(
            "sensor", DOMAIN, f"{entry.entry_id}_wallet_{legacy_id}", config_entry=entry,
            device_id=legacy_device.id, suggested_object_id=object_id,
        )
    portfolio_api.return_value = _answer(BTC, GOLD)
    with patch(
        f"{_CLIENT}async_get_currencies", AsyncMock(return_value=load_fixture("currencies.json"))
    ), patch(f"{_CLIENT}async_get_assets", AsyncMock(side_effect=_by_symbol_or_id)):
        await _setup(hass, entry)
    await _flush(hass, freezer)

    assert entry.version == 3
    assert _wallet_device(hass, entry, GOLD) is not None
    assert events == []
    notifications.assert_not_called()
    assert _stored(hass_storage, entry) == sorted([BTC["id"], GOLD["id"]])


async def test_an_announcement_dropped_by_an_unload_before_the_start_comes_at_the_next_setup(
    hass, portfolio_api, events, notifications, hass_storage
):
    """Bought while Home Assistant was off: its start creates the new
    wallet's device, and the announcement waits for the start to end. The
    Portfolio, unloaded before that, drops it, and the asset stays unknown.
    The next setup finds the wallet's device there and announces the wallet
    at once -- exactly once."""
    entry = _portfolio_entry(hass)
    _remember(hass_storage, entry, BTC)
    portfolio_api.return_value = _answer(BTC, VSN)
    hass.set_state(CoreState.not_running)
    await _setup(hass, entry)
    device = _wallet_device(hass, entry, VSN)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    await hass.async_start()
    await hass.async_block_till_done()
    assert events == []

    await _setup(hass, entry)

    assert [event.data["device_id"] for event in events] == [device.id]
    notifications.assert_called_once()
    assert VSN["id"] in entry.runtime_data.known_wallets


# --- Review focus ----------------------------------------------------------------------


async def test_several_new_assets_in_one_refresh_are_each_announced_once(
    hass, portfolio_api, events, notifications, freezer
):
    """A purchase spree while Home Assistant was off: the start reads the
    list from its file, and its first refresh brings three new wallets.
    Each is announced once, with a notification of its own."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(BTC, VSN, SOL, GOLD)

    await _restart(hass, entry, freezer)

    bought = sorted(asset["id"] for asset in (VSN, SOL, GOLD))
    assert sorted(event.data["asset_id"] for event in events) == bought
    assert sorted(
        call.kwargs["notification_id"] for call in notifications.call_args_list
    ) == [f"bitpanda_wallet_added_{asset_id}" for asset_id in bought]


@pytest.mark.parametrize(
    "automations_first", [True, False], ids=["automations_set_up_first", "portfolio_set_up_first"]
)
async def test_a_wallet_found_as_home_assistant_starts_reaches_its_automations(
    hass, portfolio_api, notifications, hass_storage, automations_first
):
    """Bought while Home Assistant was off: its start finds the new wallet
    before automations listen -- Home Assistant arms their triggers only as
    it finishes starting. The announcement waits until it has started, so an
    automation on the event runs, as README example 5 does -- whichever was
    set up first: up to Home Assistant 2026.6, an automation arms its
    trigger in a listener of its own for the start's end, which may run
    after the Portfolio's."""
    entry = _portfolio_entry(hass)
    _remember(hass_storage, entry, BTC)
    portfolio_api.return_value = _answer(BTC, VSN)
    hass.set_state(CoreState.not_running)
    if not automations_first:
        await _setup(hass, entry)
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "triggers": [{"trigger": "event", "event_type": "bitpanda_wallet_added"}],
                "actions": [
                    {"action": "test.push", "data": {"message": "{{ trigger.event.data.wallet }}"}}
                ],
            }
        },
    )
    pushed = async_mock_service(hass, "test", "push")
    if automations_first:
        await _setup(hass, entry)

    await hass.async_start()
    await hass.async_block_till_done()

    assert [call.data["message"] for call in pushed] == ["Vision (VSN) Wallet"]
    notifications.assert_called_once()
    assert VSN["id"] in entry.runtime_data.known_wallets


async def test_a_reload_as_home_assistant_starts_announces_the_wallet_once(
    hass, portfolio_api, events, notifications, hass_storage
):
    """A reload before Home Assistant has started -- a Configure save, say --
    drops the announcement its first setup was waiting with: the reloaded
    Portfolio finds the asset still unknown and announces it, once."""
    entry = _portfolio_entry(hass)
    _remember(hass_storage, entry, BTC)
    portfolio_api.return_value = _answer(BTC, VSN)
    hass.set_state(CoreState.not_running)
    await _setup(hass, entry)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    await hass.async_start()
    await hass.async_block_till_done()

    assert [event.data["asset_id"] for event in events] == [VSN["id"]]
    notifications.assert_called_once()


async def test_a_staking_sensor_added_later_announces_nothing(
    hass, portfolio_api, events, notifications, freezer
):
    """Vision, bought, is announced with its wallet's device. Staked later,
    its wallet gains a Staking sensor: no news."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)
    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking") is None
    assert len(events) == 1

    portfolio_api.return_value = [_position(BTC), _position(VSN, staked=True), _CASH]
    await _next_refresh(hass, freezer)

    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking") is not None
    assert len(events) == 1
    notifications.assert_called_once()


async def test_a_new_group_is_named_in_the_message(
    hass, portfolio_api, events, notifications, freezer
):
    """Gold, bought, is the first metal: its group is created in the same
    refresh, and the message names it."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    assert [group.unique_id for group in entry.subentries.values()] == ["crypto"]
    portfolio_api.return_value = _answer(BTC, GOLD)

    await _next_refresh(hass, freezer)

    assert [group.unique_id for group in entry.subentries.values()] == ["crypto", "metal"]
    device = _wallet_device(hass, entry, GOLD)
    notifications.assert_called_once_with(
        hass,
        "The Portfolio added a new wallet: "
        f"**[Gold (XAU) Wallet](/config/devices/device/{device.id})** "
        "in the group Precious metals.",
        "New Bitpanda wallet",
        notification_id=f"bitpanda_wallet_added_{GOLD['id']}",
    )
    assert [event.data["category"] for event in events] == ["metal"]


async def test_only_a_wallet_device_of_this_entry_announces_a_waiting_asset(
    hass, portfolio_api, events, notifications
):
    """Vision and Solana, marked as new, wait for their wallet devices. A
    device another entry creates for one of them -- under its own wallet
    identifier, or even under this entry's -- is no news; the wallet device
    of this entry announces the wallet, once."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    other = MockConfigEntry(domain=DOMAIN, title="Another Bitpanda Portfolio")
    other.add_to_hass(hass)
    runtime = entry.runtime_data
    announcer = WalletAnnouncer(hass, entry, runtime.known_wallets, runtime.group_titles)
    entry.async_on_unload(announcer.async_listen_for_wallet_devices())
    announcer.mark(VSN, "crypto")
    announcer.mark(SOL, "crypto")
    dev_reg = dr.async_get(hass)

    dev_reg.async_get_or_create(
        config_entry_id=other.entry_id,
        identifiers={(DOMAIN, f"{other.entry_id}_wallet_{VSN['id']}")},
    )
    # Solana, not Vision: on Home Assistant 2025.5 an identifier names one
    # device across all entries, so this entry's Vision device below would
    # join that one instead of being created.
    dev_reg.async_get_or_create(
        config_entry_id=other.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_wallet_{SOL['id']}")},
    )
    await hass.async_block_till_done()
    assert events == []
    notifications.assert_not_called()

    device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_wallet_{VSN['id']}")},
    )
    await hass.async_block_till_done()

    assert [event.data for event in events] == [
        {
            "device_id": device.id,
            "asset_id": VSN["id"],
            "symbol": "VSN",
            "name": "Vision",
            "wallet": "Vision (VSN) Wallet",
            "category": "crypto",
        }
    ]
    notifications.assert_called_once_with(
        hass,
        _vision_added(device, hint=False),
        "New Bitpanda wallet",
        notification_id=f"bitpanda_wallet_added_{VSN['id']}",
    )


async def test_a_price_device_created_while_an_asset_waits_is_no_news(
    hass, portfolio_api, events, notifications
):
    """Vision waits for its wallet device while a Price Tracker creates its
    price device for Vision: no news. (The Portfolio's own device comes with
    its setup, before any wallet is marked.) The wallet device then
    announces Vision, once."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    tracker = MockConfigEntry(
        domain=DOMAIN, title="Bitpanda Price Tracker", data={"entry_type": "price_tracker"}
    )
    tracker.add_to_hass(hass)
    runtime = entry.runtime_data
    announcer = WalletAnnouncer(hass, entry, runtime.known_wallets, runtime.group_titles)
    entry.async_on_unload(announcer.async_listen_for_wallet_devices())
    announcer.mark(VSN, "crypto")
    dev_reg = dr.async_get(hass)

    dev_reg.async_get_or_create(
        config_entry_id=tracker.entry_id,
        identifiers={(DOMAIN, price_device_identifier(tracker.entry_id, VSN["id"]))},
    )
    await hass.async_block_till_done()
    assert events == []
    notifications.assert_not_called()

    device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_wallet_{VSN['id']}")},
    )
    await hass.async_block_till_done()

    assert [event.data["device_id"] for event in events] == [device.id]
    notifications.assert_called_once()


async def test_a_creation_heard_after_the_device_went_again_announces_nothing(
    hass, portfolio_api, events, notifications, caplog
):
    """Home Assistant 2026.9.4 holds back an event fired while another is
    being dispatched until that one is done, so a device's creation can be
    heard after the device went again. Heard for a device no longer there
    while Vision waits for its wallet device, it is no news and raises
    nothing; the wallet device created then announces Vision, once."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    runtime = entry.runtime_data
    announcer = WalletAnnouncer(hass, entry, runtime.known_wallets, runtime.group_titles)
    entry.async_on_unload(announcer.async_listen_for_wallet_devices())
    announcer.mark(VSN, "crypto")
    caplog.clear()

    hass.bus.async_fire(
        dr.EVENT_DEVICE_REGISTRY_UPDATED, {"action": "create", "device_id": "a device gone again"}
    )
    await hass.async_block_till_done()

    assert events == []
    notifications.assert_not_called()
    assert [
        record.getMessage() for record in caplog.records if record.levelno >= logging.ERROR
    ] == []

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_wallet_{VSN['id']}")},
    )
    await hass.async_block_till_done()

    assert [event.data["device_id"] for event in events] == [device.id]
    notifications.assert_called_once()


async def test_an_unload_removes_the_wallet_device_listener(
    hass, portfolio_api, events, notifications, freezer
):
    """The Portfolio listens for its wallet devices while it is loaded, and
    no more once unloaded. Set up again, it announces a bought asset once."""

    @callback
    def _ignore(event):
        """Nothing to do."""

    # Home Assistant's entities share one listener for their devices'
    # changes, which goes with the last of them: one of the test's own keeps
    # it, so that the count tells the Portfolio's listener alone.
    keep = async_track_device_registry_updated_event(hass, "a device of the test", _ignore)
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    loaded = hass.bus.async_listeners()[dr.EVENT_DEVICE_REGISTRY_UPDATED]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.bus.async_listeners()[dr.EVENT_DEVICE_REGISTRY_UPDATED] == loaded - 1

    await _setup(hass, entry)
    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)

    assert [event.data["asset_id"] for event in events] == [VSN["id"]]
    notifications.assert_called_once()
    keep()


@_RESTORES_DISABLED_SENSORS
async def test_a_wallet_with_one_sensor_disabled_gets_no_hint(
    hass, portfolio_api, events, notifications, freezer
):
    """Vision's Balance sensor disabled by the user before the sale, its
    Total sensor not: bought again, the wallet comes back with one sensor
    enabled, and the notification says nothing of disabled sensors."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)

    await _bought_sold_and_bought_again(
        hass, entry, portfolio_api, freezer, disabled=(_VSN_BALANCE,)
    )

    device = _wallet_device(hass, entry, VSN)
    assert _disabled_by(hass, _VSN_BALANCE, _VSN_TOTAL) == [er.RegistryEntryDisabler.USER, None]
    assert [event.data["device_id"] for event in events] == [device.id, device.id]
    assert [call.args[1] for call in notifications.call_args_list] == [
        _vision_added(device, hint=False)
    ] * 2


async def test_a_new_wallet_with_one_of_its_sensors_disabled_gets_no_hint(
    hass, portfolio_api, events, notifications, freezer
):
    """Vision's Balance sensor registered disabled before Vision's first
    purchase -- by hand here, so on every Home Assistant version -- and its
    Total sensor new and enabled: the notification says nothing of disabled
    sensors. The Balance sensor comes first: a check made before the Total
    sensor was registered would wrongly find all of them disabled."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        wallet_unique_id(entry.entry_id, VSN["id"]),
        config_entry=entry,
        suggested_object_id=_VSN_BALANCE.split(".", 1)[1],
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    portfolio_api.return_value = _answer(BTC, VSN)

    await _next_refresh(hass, freezer)

    device = _wallet_device(hass, entry, VSN)
    assert _disabled_by(hass, _VSN_BALANCE, _VSN_TOTAL) == [er.RegistryEntryDisabler.USER, None]
    assert [call.args[1] for call in notifications.call_args_list] == [
        _vision_added(device, hint=False)
    ]


async def test_with_new_entities_disabled_a_wallet_found_at_the_start_has_the_hint(
    hass, portfolio_api, events, notifications, hass_storage
):
    """Bought while Home Assistant was off, with the Portfolio's system
    option "Enable newly added entities" off: the start creates the wallet's
    device and registers its sensors disabled. The announcement, after the
    start, says that they are disabled."""
    entry = _portfolio_entry(hass)
    hass.config_entries.async_update_entry(entry, pref_disable_new_entities=True)
    _remember(hass_storage, entry, BTC)
    portfolio_api.return_value = _answer(BTC, VSN)
    hass.set_state(CoreState.not_running)
    await _setup(hass, entry)
    assert events == []

    await hass.async_start()
    await hass.async_block_till_done()

    device = _wallet_device(hass, entry, VSN)
    assert [event.data["device_id"] for event in events] == [device.id]
    notifications.assert_called_once_with(
        hass,
        _vision_added(device, hint=True),
        "New Bitpanda wallet",
        notification_id=f"bitpanda_wallet_added_{VSN['id']}",
    )


# --- What it says ----------------------------------------------------------------------


async def test_a_failing_notification_still_makes_the_asset_known(
    hass, portfolio_api, events, notifications, freezer, caplog
):
    """Should Home Assistant fail to show the notification, the event has
    fired and the asset is known all the same -- rather a notification
    missed than the event again at every start --, and a warning names the
    wallet and the error's type, without a traceback."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    notifications.side_effect = HomeAssistantError("the notification failed")
    portfolio_api.return_value = _answer(BTC, VSN)
    caplog.clear()

    await _next_refresh(hass, freezer)

    assert [event.data["asset_id"] for event in events] == [VSN["id"]]
    assert VSN["id"] in entry.runtime_data.known_wallets
    [record] = [r for r in caplog.records if r.name == "custom_components.bitpanda.announcements"]
    assert (record.levelname, record.getMessage(), record.exc_info) == (
        "WARNING",
        "Could not show the notification about the new Bitpanda wallet Vision (VSN) Wallet "
        "(HomeAssistantError)",
        None,
    )
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []


async def test_switched_off_the_event_still_fires_without_a_notification(
    hass, portfolio_api, events, notifications, freezer
):
    entry = _portfolio_entry(hass, notify_new_wallets=False)
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(BTC, VSN)

    await _next_refresh(hass, freezer)

    assert [event.data["asset_id"] for event in events] == [VSN["id"]]
    notifications.assert_not_called()
    assert VSN["id"] in entry.runtime_data.known_wallets


async def test_the_notification_is_in_the_portfolios_language(
    hass, portfolio_api, notifications, freezer
):
    """German, the Portfolio's language, while Home Assistant runs in
    English: a persistent notification shows as it was written, to every
    user alike."""
    entry = _portfolio_entry(hass, language="de")
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(BTC, VSN)

    await _next_refresh(hass, freezer)

    device = _wallet_device(hass, entry, VSN)
    notifications.assert_called_once_with(
        hass,
        "Das Portfolio hat ein neues Wallet angelegt: "
        f"**[Vision (VSN) Wallet](/config/devices/device/{device.id})** "
        "in der Gruppe Kryptowährungen.",
        "Neues Bitpanda-Wallet",
        notification_id=f"bitpanda_wallet_added_{VSN['id']}",
    )


async def test_a_missing_text_falls_back_to_english(hass, portfolio_api, notifications, freezer):
    """German lacks the message: Home Assistant fills it in from English.
    The title and the group's title, which German has, stay German."""
    with _texts_lacking_the_message(hass, "de"):
        entry = _portfolio_entry(hass, language="de")
        await _setup(hass, entry)
        portfolio_api.return_value = _answer(BTC, VSN)
        await _next_refresh(hass, freezer)

    device = _wallet_device(hass, entry, VSN)
    notifications.assert_called_once_with(
        hass,
        "The Portfolio added a new wallet: "
        f"**[Vision (VSN) Wallet](/config/devices/device/{device.id})** "
        "in the group Kryptowährungen.",
        "Neues Bitpanda-Wallet",
        notification_id=f"bitpanda_wallet_added_{VSN['id']}",
    )


async def test_without_any_text_the_event_still_fires_and_the_asset_becomes_known(
    hass, portfolio_api, events, notifications, freezer
):
    """A broken install, whose files lack the message in every language:
    no notification, but the event fires all the same, the asset joins the
    list, and the wallet's sensors are added -- nothing raises while Home
    Assistant adds them."""
    with _texts_lacking_the_message(hass, "en"):
        entry = _portfolio_entry(hass)
        await _setup(hass, entry)
        portfolio_api.return_value = _answer(BTC, VSN)
        await _next_refresh(hass, freezer)

    assert [event.data["asset_id"] for event in events] == [VSN["id"]]
    notifications.assert_not_called()
    assert VSN["id"] in entry.runtime_data.known_wallets
    for ending in ("available", "total"):
        assert hass.states.get(f"sensor.bitpanda_vision_vsn_wallet_{ending}") is not None


@pytest.mark.parametrize(
    ("lacking", "hint"),
    [
        (("de",), "Its sensors are disabled. You can enable them on its [device page]({link})."),
        (("de", "en"), None),
    ],
    ids=["german_lacks_it", "every_language_lacks_it"],
)
async def test_a_missing_hint_text_falls_back_to_english_or_leaves_the_hint_out(
    hass, portfolio_api, notifications, freezer, lacking, hint
):
    """A German Portfolio, its new wallet's sensors disabled: German lacks
    the hint, and Home Assistant fills it in from English. Lacking in every
    language -- a broken install -- the notification comes without it."""
    with _texts_lacking_the_message(hass, *lacking, key="wallet_added_sensors_disabled"):
        entry = _portfolio_entry(hass, language="de")
        hass.config_entries.async_update_entry(entry, pref_disable_new_entities=True)
        await _setup(hass, entry)
        portfolio_api.return_value = _answer(BTC, VSN)
        await _next_refresh(hass, freezer)

    link = f"/config/devices/device/{_wallet_device(hass, entry, VSN).id}"
    message = (
        f"Das Portfolio hat ein neues Wallet angelegt: **[Vision (VSN) Wallet]({link})** "
        "in der Gruppe Kryptowährungen."
    )
    notifications.assert_called_once_with(
        hass,
        message if hint is None else f"{message}\n\n{hint.format(link=link)}",
        "Neues Bitpanda-Wallet",
        notification_id=f"bitpanda_wallet_added_{VSN['id']}",
    )


async def test_a_wallet_announced_again_replaces_its_notification(
    hass, portfolio_api, hass_ws_client, freezer
):
    """In Home Assistant's own store, not patched: the notification carries
    its title, its message and the link to the device; a wallet announced
    again -- bought again after its wallet went -- replaces the earlier
    notification instead of adding a second one."""
    assert await async_setup_component(hass, "persistent_notification", {})
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)
    portfolio_api.return_value = _answer(BTC)
    for _ in range(3):
        await _next_refresh(hass, freezer)
    assert _wallet_device(hass, entry, VSN) is None

    portfolio_api.return_value = _answer(BTC, VSN)
    await _next_refresh(hass, freezer)

    device = _wallet_device(hass, entry, VSN)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "persistent_notification/get"})
    stored = (await client.receive_json())["result"]
    assert [
        (notification["notification_id"], notification["title"], notification["message"])
        for notification in stored
    ] == [
        (
            f"bitpanda_wallet_added_{VSN['id']}",
            "New Bitpanda wallet",
            "The Portfolio added a new wallet: "
            f"**[Vision (VSN) Wallet](/config/devices/device/{device.id})** "
            "in the group Cryptocurrencies.",
        )
    ]


async def test_a_name_with_markdown_characters_shows_as_it_is(
    hass, portfolio_api, events, notifications, freezer
):
    """Bitpanda's catalogue names some assets with Markdown's characters,
    such as "QuickSwap [Old]": the notification escapes them inside its
    link, so the name shows as it is; the event carries the name as it is."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    quickswap = {**VSN, "name": "QuickSwap [Old]", "symbol": "QUICK"}
    portfolio_api.return_value = _answer(BTC, quickswap)

    with patch(
        f"{_CLIENT}async_get_assets",
        AsyncMock(
            side_effect=lambda **kwargs: (
                [quickswap] if kwargs.get("asset_id") == VSN["id"] else _lookup(**kwargs)
            )
        ),
    ):
        await _next_refresh(hass, freezer)

    device = _wallet_device(hass, entry, VSN)
    assert [event.data["wallet"] for event in events] == ["QuickSwap [Old] (QUICK) Wallet"]
    assert notifications.call_args.args[1] == (
        "The Portfolio added a new wallet: "
        rf"**[QuickSwap \[Old\] (QUICK) Wallet](/config/devices/device/{device.id})** "
        "in the group Cryptocurrencies."
    )


def test_escape_markdown_escapes_link_and_emphasis_characters():
    """A wallet's name keeps its characters inside the notification's link:
    a backslash, code, emphasis and brackets are escaped; anything else,
    parentheses included, stays as it is."""
    assert escape_markdown(r"a\b`c*d_e[f]g") == r"a\\b\`c\*d\_e\[f\]g"
    assert escape_markdown("Vision (VSN) Wallet") == "Vision (VSN) Wallet"
