"""New staking payouts are announced (announcements.RewardAnnouncer): the
event bitpanda_staking_reward_received always, a notification only while it
is switched on -- for an asset whose Balance (staking) sensor is registered
and enabled, each payout once, the payouts missed in a pause added up in one
announcement. Never the payouts listed at the first refresh. End to end,
Bitpanda mocked as in tests/test_wallet_announcements.py."""
import asyncio
from contextlib import contextmanager
from datetime import timedelta
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import CoreState
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    translation,
)
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.bitpanda import announcements
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.devices import find_entry_device

from tests.conftest import load_fixture

_CLIENT = "custom_components.bitpanda.api.BitpandaApiClient."
_NOTIFY = "custom_components.bitpanda.announcements.persistent_notification.async_create"
_TEXTS = "custom_components.bitpanda.announcements.async_get_translations"
_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"
_EVENT = "bitpanda_staking_reward_received"


def _record(symbol: str) -> dict:
    return next(a for a in load_fixture("assets-sample.json") if a["symbol"] == symbol)


BTC, VSN, SOL, ADA = _record("BTC"), _record("VSN"), _record("SOL"), _record("ADA")
_CASH = {"currency_id": _EUR_ID, "balance": {"value": "10.00"}}
_VSN_STAKING = "sensor.bitpanda_vision_vsn_wallet_staking"
_KNOWN_WALLETS = sorted([BTC["id"], VSN["id"]])


def _position(asset: dict, *, staked: bool = False, worth: str | None = "6.60") -> dict:
    """1,000 units of `asset`, worth `worth` in all -- 0.0066 a unit, by
    default; None sends no value -- half of them staked if `staked`."""
    position = {
        "asset_id": asset["id"],
        "balance": {"value": "1000.00000000"},
        "available_balance": {"value": "500.00000000" if staked else "1000.00000000"},
    }
    if worth is not None:
        position["currency_balance"] = {"value": worth}
    return position


def _answer(*positions: dict) -> list[dict]:
    """/portfolio's answer: `positions`, and cash."""
    return [*positions, _CASH]


# Bitcoin, and Vision with half of it staked: Vision's wallet has a Staking
# sensor.
_HOLDINGS = _answer(_position(BTC), _position(VSN, staked=True))


def _reward(asset: dict, credited_at: str, gross: str, fee: str) -> dict:
    """One staking payout of `asset`, as /operations lists it
    (tests/test_coordinator_earn.py)."""
    return {
        "operation_id": f"op-{credited_at}-{asset['id']}",
        "operation_type": "reward",
        "transactions": [
            {
                "asset_id": asset["id"],
                "wallet_owner": "staking-service",
                "asset_amount": {"value": gross},
                "fee_amount": {"value": fee},
                "credited_at": credited_at,
            }
        ],
    }


# Vision's weekly payouts, oldest first: when, gross and fee -- net 9.6, 9.6,
# 10, 10.02962936, 9.87654312 and 9.68 VSN.
_PAYOUTS = [
    ("2026-09-01T16:20:00Z", "12.00000000", "2.40000000"),
    ("2026-09-08T16:20:00Z", "12.00000000", "2.40000000"),
    ("2026-09-15T16:20:00Z", "12.50000000", "2.50000000"),
    ("2026-09-22T16:20:00Z", "12.53703670", "2.50740734"),
    ("2026-09-29T16:20:00Z", "12.34567890", "2.46913578"),
    ("2026-10-06T16:20:00Z", "12.10000000", "2.42000000"),
]
_WHEN = [when for when, _, _ in _PAYOUTS]


def _paid(count: int) -> list[dict]:
    """/operations once Vision's first `count` payouts are made, newest
    first, as Bitpanda lists them."""
    return [_reward(VSN, *payout) for payout in reversed(_PAYOUTS[:count])]


def _lookup(**kwargs):
    return [a for a in load_fixture("assets-sample.json") if a["id"] == kwargs.get("asset_id")]


@pytest.fixture
def operations():
    """/operations: Vision's first four payouts, unless a test lists others."""
    with patch(f"{_CLIENT}async_get_operations", AsyncMock(return_value=_paid(4))) as listing:
        yield listing


@pytest.fixture
def portfolio_api(operations):
    """Bitpanda as the Portfolio asks it: the account holds _HOLDINGS, and
    Earn offers nothing."""
    with patch(
        f"{_CLIENT}async_get_portfolio", AsyncMock(return_value=_HOLDINGS)
    ) as portfolio, patch(
        f"{_CLIENT}async_get_portfolio_history", AsyncMock(return_value={"return_percentage": 1.5})
    ), patch(f"{_CLIENT}async_get_earn_configs", AsyncMock(return_value=[])), patch(
        f"{_CLIENT}async_get_assets", AsyncMock(side_effect=_lookup)
    ):
        yield portfolio


@pytest.fixture
def events(hass):
    """Every bitpanda_staking_reward_received fired."""
    return async_capture_events(hass, _EVENT)


@pytest.fixture
def notifications():
    """Every persistent notification created."""
    with patch(_NOTIFY) as create:
        yield create


def _portfolio_entry(hass, **options) -> MockConfigEntry:
    """A Portfolio in EUR, with `options`: none -- English, the
    notification about staking rewards off."""
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR",
              "currency_id": _EUR_ID},
        options=options,
    )
    entry.add_to_hass(hass)
    return entry


def _remember(hass_storage, entry, **sections) -> None:
    """A file for `entry` holding `sections`, as an earlier start left it."""
    key = f"{DOMAIN}.portfolio.{entry.entry_id}"
    hass_storage[key] = {"version": 1, "key": key, "data": sections}


def _known(hass_storage, entry, mark: str) -> None:
    """A file for `entry` that knows Bitcoin's and Vision's wallets, and
    Vision's payouts up to the one credited at `mark`."""
    _remember(
        hass_storage, entry, known_wallets=_KNOWN_WALLETS, known_rewards={VSN["id"]: mark}
    )


def _stored(hass_storage, entry) -> dict:
    """The sections in the file of `entry`."""
    return hass_storage[f"{DOMAIN}.portfolio.{entry.entry_id}"]["data"]


async def _setup(hass, entry) -> None:
    """Set up `entry` and wait until it is loaded, and an announcement it
    started is done: a background task, which only wait_background_tasks
    waits for."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED


async def _next_refresh(hass, freezer) -> None:
    """The Portfolio's next regular refresh of /portfolio."""
    freezer.tick(timedelta(minutes=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def _next_hour(hass, freezer) -> None:
    """The next hourly refresh of the rewards -- while a Staking sensor
    listens -- and the announcement it starts, both run to their end."""
    freezer.tick(timedelta(hours=1, minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def _flush(hass, freezer) -> None:
    """Let the file's delayed save run. Only the freezer moves the event
    loop's clock, which the save waits for (tests/test_portfolio_store.py)."""
    freezer.tick(timedelta(seconds=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def _restart(hass, entry, freezer) -> None:
    """Home Assistant stopped and started again: the file's last change is
    written as it stops, and the store portfolio_store.py keeps in memory is
    gone; the registries and the files stay."""
    await _flush(hass, freezer)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    del hass.data[f"{DOMAIN}_portfolio_stores"]
    await _setup(hass, entry)


async def _reload_after_enabling(hass, freezer) -> None:
    """Home Assistant reloads the Portfolio 30 seconds after one of its
    sensors was enabled -- not after one was disabled."""
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


def _wallet_device(hass, entry) -> dr.DeviceEntry | None:
    """Vision's wallet device; None while there is none."""
    return find_entry_device(
        dr.async_get(hass), entry.entry_id, f"{entry.entry_id}_wallet_{VSN['id']}"
    )


def _mark(entry) -> str | None:
    """Vision's mark, as the Portfolio holds it -- written or not yet."""
    return entry.runtime_data.reward_marks.mark_of(VSN["id"])


@contextmanager
def _texts_lacking(hass, *languages: str, key: str):
    """Within it, Home Assistant reads this integration's translation files
    as if those of `languages` lacked the notification's text `key`
    (tests/test_wallet_announcements.py says why the cache goes)."""
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


# --- What is new -----------------------------------------------------------------------


async def test_a_new_payout_fires_the_event_and_the_notification(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """Vision pays out after its mark: the next hourly refresh of the
    rewards announces the payout -- one event with its figures, its value at
    today's price, one notification linking to the wallet -- and the mark
    moves on to it."""
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    assert events == []
    operations.return_value = _paid(5)

    await _next_hour(hass, freezer)

    device = _wallet_device(hass, entry)
    assert er.async_get(hass).async_get(_VSN_STAKING).device_id == device.id
    assert [event.data for event in events] == [
        {
            "device_id": device.id,
            "asset_id": VSN["id"],
            "symbol": "VSN",
            "name": "Vision",
            "wallet": "Vision (VSN) Wallet",
            "count": 1,
            "gross": 12.3456789,
            "fee": 2.46913578,
            "net": 9.87654312,
            "value": 0.07,
            "currency": "EUR",
            "credited_at": "2026-09-29T16:20:00Z",
        }
    ]
    notifications.assert_called_once_with(
        hass,
        f"**[Vision (VSN) Wallet](/config/devices/device/{device.id})** received a staking "
        "reward of **9.87654312 VSN**. Worth about 0.07 EUR today.",
        "New Bitpanda staking reward",
        notification_id=f"bitpanda_staking_reward_{VSN['id']}",
    )
    await _flush(hass, freezer)
    assert _stored(hass_storage, entry)["known_rewards"] == {VSN["id"]: _WHEN[4]}


async def test_payouts_missed_in_a_pause_come_together(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """Home Assistant off for three weeks, Vision paying out every week: its
    start announces the three payouts once, added up, with their number."""
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _known(hass_storage, entry, _WHEN[1])
    operations.return_value = _paid(2)
    await _setup(hass, entry)
    operations.return_value = _paid(5)

    await _restart(hass, entry, freezer)

    device = _wallet_device(hass, entry)
    assert [event.data for event in events] == [
        {
            "device_id": device.id,
            "asset_id": VSN["id"],
            "symbol": "VSN",
            "name": "Vision",
            "wallet": "Vision (VSN) Wallet",
            "count": 3,
            "gross": 37.3827156,
            "fee": 7.47654312,
            "net": 29.90617248,
            "value": 0.2,
            "currency": "EUR",
            "credited_at": "2026-09-29T16:20:00Z",
        }
    ]
    notifications.assert_called_once_with(
        hass,
        f"**[Vision (VSN) Wallet](/config/devices/device/{device.id})** received 3 staking "
        "rewards, together **29.90617248 VSN**. Worth about 0.20 EUR today.",
        "New Bitpanda staking reward",
        notification_id=f"bitpanda_staking_reward_{VSN['id']}",
    )
    assert _mark(entry) == _WHEN[4]


async def test_a_malformed_rewards_section_is_a_first_run_of_the_rewards_alone(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer, caplog
):
    """A `known_rewards` section of the wrong shape, next to a good
    `known_wallets` one: the rewards begin anew -- every payout listed now
    known, nothing announced, one warning --, and the wallets stay as they
    were."""
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _remember(hass_storage, entry, known_wallets=_KNOWN_WALLETS, known_rewards=[])
    operations.return_value = _paid(3)
    caplog.set_level(logging.WARNING)

    await _setup(hass, entry)
    await _flush(hass, freezer)

    assert events == []
    notifications.assert_not_called()
    assert _stored(hass_storage, entry) == {
        "known_wallets": _KNOWN_WALLETS,
        "known_rewards": {VSN["id"]: _WHEN[2]},
    }
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.name == "custom_components.bitpanda.portfolio_store"
    ]
    assert warnings == [
        "Could not read which Bitpanda staking rewards were announced before (ValueError); "
        "the payouts listed now count as known"
    ]


async def test_a_disabled_staking_sensor_holds_the_mark_until_it_is_enabled(
    hass, portfolio_api, operations, events, hass_storage, freezer
):
    """Vision's Balance (staking) sensor, disabled: nothing polls the rewards
    any more, and the restart that reads them lists a new payout -- no
    announcement, and the mark stays. Enabled again after one more payout,
    the reload Home Assistant follows that with announces both together."""
    entry = _portfolio_entry(hass)
    _known(hass_storage, entry, _WHEN[2])
    operations.return_value = _paid(3)
    await _setup(hass, entry)
    ent_reg = er.async_get(hass)
    ent_reg.async_update_entity(_VSN_STAKING, disabled_by=er.RegistryEntryDisabler.USER)
    await hass.async_block_till_done()

    operations.return_value = _paid(4)
    await _next_hour(hass, freezer)
    assert operations.call_count == 1
    await _restart(hass, entry, freezer)

    assert operations.call_count == 2
    assert events == []
    assert _mark(entry) == _WHEN[2]

    operations.return_value = _paid(5)
    ent_reg.async_update_entity(_VSN_STAKING, disabled_by=None)
    await _reload_after_enabling(hass, freezer)

    assert operations.call_count == 3
    assert [(event.data["count"], event.data["credited_at"]) for event in events] == [
        (2, _WHEN[4])
    ]
    assert _mark(entry) == _WHEN[4]


async def test_an_asset_missing_from_the_portfolio_waits(
    hass, portfolio_api, operations, events, hass_storage, freezer
):
    """Vision missing from /portfolio's answers while its wallet waits out
    its misses: a new payout is not announced -- nothing names the asset or
    prices it -- and the mark stays. Listed again, the next hourly refresh
    announces the payout."""
    entry = _portfolio_entry(hass)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(_position(BTC))
    await _next_refresh(hass, freezer)
    operations.return_value = _paid(5)

    await _next_hour(hass, freezer)

    assert er.async_get(hass).async_get(_VSN_STAKING) is not None
    assert events == []
    assert _mark(entry) == _WHEN[3]

    portfolio_api.return_value = _HOLDINGS
    await _next_refresh(hass, freezer)
    await _next_hour(hass, freezer)

    assert [(event.data["count"], event.data["credited_at"]) for event in events] == [
        (1, _WHEN[4])
    ]


async def test_a_mark_stays_after_the_wallet_goes(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """Vision sold: its wallet goes after the confirmed misses, its mark
    stays. Bought back, its wallet comes again with a new Staking sensor,
    and the listing holds the old payouts and a new one: only the new one is
    announced."""
    entry = _portfolio_entry(hass)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(_position(BTC))
    for _ in range(3):
        await _next_refresh(hass, freezer)
    assert _wallet_device(hass, entry) is None
    assert er.async_get(hass).async_get(_VSN_STAKING) is None

    portfolio_api.return_value = _HOLDINGS
    operations.return_value = _paid(5)
    await _next_refresh(hass, freezer)
    await _next_hour(hass, freezer)

    assert [(event.data["count"], event.data["credited_at"]) for event in events] == [
        (1, _WHEN[4])
    ]
    assert events[0].data["device_id"] == _wallet_device(hass, entry).id


async def test_assets_are_announced_in_the_order_of_their_newest_payout(
    hass, portfolio_api, operations, events, hass_storage, freezer
):
    """Cardano's new payout came before Vision's: Cardano is announced
    first, whatever order Bitpanda lists them in."""
    portfolio_api.return_value = _answer(
        _position(BTC), _position(VSN, staked=True), _position(ADA, staked=True)
    )
    entry = _portfolio_entry(hass)
    _remember(
        hass_storage,
        entry,
        known_wallets=sorted([BTC["id"], VSN["id"], ADA["id"]]),
        known_rewards={VSN["id"]: _WHEN[3], ADA["id"]: "2026-09-21T08:00:00Z"},
    )
    await _setup(hass, entry)
    operations.return_value = [
        *_paid(5),
        _reward(ADA, "2026-09-28T08:00:00Z", "0.50000000", "0.10000000"),
    ]

    await _next_hour(hass, freezer)

    assert [event.data["asset_id"] for event in events] == [ADA["id"], VSN["id"]]


# --- What is not new -------------------------------------------------------------------


async def test_the_first_refresh_marks_every_payout_and_announces_nothing(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """No file, as after a new setup: the payouts listed are no news. The
    newest of every asset becomes its mark, held or not -- Solana is not
    held -- and the next refresh finds nothing new either."""
    operations.return_value = [
        *_paid(5),
        _reward(SOL, "2026-09-30T08:00:00Z", "0.01000000", "0.00200000"),
        _reward(SOL, "2026-09-23T08:00:00Z", "0.01000000", "0.00200000"),
    ]
    entry = _portfolio_entry(hass, notify_staking_rewards=True)

    await _setup(hass, entry)
    await _next_hour(hass, freezer)
    await _flush(hass, freezer)

    assert events == []
    notifications.assert_not_called()
    assert _stored(hass_storage, entry)["known_rewards"] == {
        VSN["id"]: _WHEN[4],
        SOL["id"]: "2026-09-30T08:00:00Z",
    }


async def test_an_update_without_the_rewards_section_announces_nothing(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """Updated from a version without the marks: the file holds the known
    wallets only. The payouts listed are no news, and the wallets stay as
    they were."""
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _remember(hass_storage, entry, known_wallets=_KNOWN_WALLETS)
    operations.return_value = _paid(5)

    await _setup(hass, entry)
    await _next_hour(hass, freezer)
    await _flush(hass, freezer)

    assert events == []
    notifications.assert_not_called()
    assert _stored(hass_storage, entry) == {
        "known_wallets": _KNOWN_WALLETS,
        "known_rewards": {VSN["id"]: _WHEN[4]},
    }


async def test_without_a_staking_sensor_nothing_is_announced(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """Vision held, nothing of it staked and no Earn offer for it: its
    wallet has no Staking sensor. A payout after its mark -- one made before
    it was unstaked, say -- is not announced by the restart that lists it,
    though the wallet's device is there, and the mark stays."""
    portfolio_api.return_value = _answer(_position(BTC), _position(VSN))
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    operations.return_value = _paid(5)

    await _restart(hass, entry, freezer)

    assert operations.call_count == 2
    assert _wallet_device(hass, entry) is not None
    assert er.async_get(hass).async_get(_VSN_STAKING) is None
    assert events == []
    notifications.assert_not_called()
    assert _mark(entry) == _WHEN[3]


async def test_another_entrys_staking_sensor_does_not_open_the_gate(
    hass, portfolio_api, operations, events, hass_storage
):
    """A sensor registered under the unique_id of Vision's Staking sensor,
    with a device of its own, but for another config entry: it is not the
    Portfolio's, so a payout after the mark is not announced, and the mark
    stays. Nothing of Vision is staked, so the Portfolio registers no
    Staking sensor of its own that would take the registry entry over."""
    portfolio_api.return_value = _answer(_position(BTC), _position(VSN))
    entry = _portfolio_entry(hass)
    _known(hass_storage, entry, _WHEN[3])
    other = MockConfigEntry(domain=DOMAIN, title="Another Bitpanda Portfolio")
    other.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id, identifiers={(DOMAIN, "a device of another entry")}
    )
    sensor = er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_staking_{VSN['id']}",
        config_entry=other, device_id=device.id,
    )
    operations.return_value = _paid(5)

    await _setup(hass, entry)

    assert operations.call_count == 1
    registered = er.async_get(hass).async_get(sensor.entity_id)
    assert (registered.config_entry_id, registered.device_id) == (other.entry_id, device.id)
    assert events == []
    assert _mark(entry) == _WHEN[3]


async def test_a_staking_sensor_without_a_device_does_not_open_the_gate(
    hass, portfolio_api, operations, events, hass_storage, freezer
):
    """Vision's Staking sensor, registered for the Portfolio but without a
    device: the announcement would have no wallet to name and link, so a
    payout after the mark is not announced, and the mark stays."""
    entry = _portfolio_entry(hass)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    er.async_get(hass).async_update_entity(_VSN_STAKING, device_id=None)
    await hass.async_block_till_done()
    operations.return_value = _paid(5)

    await _next_hour(hass, freezer)

    assert operations.call_count == 2
    assert er.async_get(hass).async_get(_VSN_STAKING).device_id is None
    assert events == []
    assert _mark(entry) == _WHEN[3]


async def test_changing_the_switch_announces_nothing_again(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """Saving under Configure reloads the Portfolio -- here right after a
    payout was announced, its mark not written yet. The reload keeps the
    marks it had: switching the notification off, and on again, announces
    the payout no second time."""
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    operations.return_value = _paid(5)
    await _next_hour(hass, freezer)
    assert len(events) == 1
    assert _stored(hass_storage, entry)["known_rewards"] == {VSN["id"]: _WHEN[3]}
    refreshes = operations.call_count

    for switch in (False, True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "notifications": {"notify_new_wallets": True, "notify_staking_rewards": switch},
                "language": {"language": "en"},
            },
        )
        assert result["type"] == "create_entry"
        await hass.async_block_till_done(wait_background_tasks=True)
        assert entry.options["notify_staking_rewards"] is switch

    # Each reload's first refresh of the rewards.
    assert operations.call_count == refreshes + 2
    assert len(events) == 1
    notifications.assert_called_once()


async def test_a_new_wallet_and_an_advanced_mark_are_saved_together(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """Home Assistant off while Solana was bought and Vision paid out: its
    start announces both, and a single write holds both sections."""
    entry = _portfolio_entry(hass)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    portfolio_api.return_value = _answer(
        _position(BTC), _position(VSN, staked=True), _position(SOL)
    )
    operations.return_value = _paid(5)

    await _restart(hass, entry, freezer)

    assert [event.data["credited_at"] for event in events] == [_WHEN[4]]
    assert f"bitpanda_wallet_added_{SOL['id']}" in [
        call.kwargs["notification_id"] for call in notifications.call_args_list
    ]
    assert _stored(hass_storage, entry) == {
        "known_wallets": _KNOWN_WALLETS,
        "known_rewards": {VSN["id"]: _WHEN[3]},
    }
    await _flush(hass, freezer)
    assert _stored(hass_storage, entry) == {
        "known_wallets": sorted([BTC["id"], SOL["id"], VSN["id"]]),
        "known_rewards": {VSN["id"]: _WHEN[4]},
    }


# --- When it runs ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("state", "automations_first"),
    [
        (CoreState.not_running, True),
        (CoreState.not_running, False),
        (CoreState.starting, False),
    ],
    ids=["automations_set_up_first", "portfolio_set_up_first", "portfolio_set_up_while_starting"],
)
async def test_during_a_start_the_announcement_waits_until_home_assistant_has_started(
    hass, portfolio_api, operations, events, hass_storage, state, automations_first
):
    """A payout made while Home Assistant was off: its start finds it before
    automations listen -- Home Assistant arms their triggers only as it
    finishes starting. The announcement waits until it has started, so an
    automation on the event runs, whichever was set up first: up to Home
    Assistant 2026.6, an automation arms its trigger in a listener of its
    own for the start's end, which may run after the Portfolio's."""
    entry = _portfolio_entry(hass)
    _known(hass_storage, entry, _WHEN[3])
    operations.return_value = _paid(5)
    hass.set_state(state)
    if not automations_first:
        await _setup(hass, entry)
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "triggers": [{"trigger": "event", "event_type": _EVENT}],
                "actions": [
                    {
                        "action": "test.push",
                        "data": {
                            "message": "{{ trigger.event.data.wallet }} received "
                            "{{ trigger.event.data.net }} {{ trigger.event.data.symbol }}"
                        },
                    }
                ],
            }
        },
    )
    pushed = async_mock_service(hass, "test", "push")
    if automations_first:
        await _setup(hass, entry)
    assert events == []

    await hass.async_start()
    await hass.async_block_till_done(wait_background_tasks=True)

    assert [event.data["credited_at"] for event in events] == [_WHEN[4]]
    assert [call.data["message"] for call in pushed] == [
        "Vision (VSN) Wallet received 9.87654312 VSN"
    ]


async def test_an_unload_before_the_start_drops_the_pass_and_the_next_start_announces(
    hass, portfolio_api, operations, events, hass_storage
):
    """A payout made while Home Assistant was off waits for the start's end.
    The Portfolio, unloaded before that, drops the announcement, and the
    mark stays: its next setup announces the payout -- exactly once."""
    entry = _portfolio_entry(hass)
    _known(hass_storage, entry, _WHEN[3])
    operations.return_value = _paid(5)
    hass.set_state(CoreState.not_running)
    await _setup(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    await hass.async_start()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert events == []

    await _setup(hass, entry)

    assert [event.data["credited_at"] for event in events] == [_WHEN[4]]
    assert _mark(entry) == _WHEN[4]


async def test_a_pass_cancelled_while_loading_texts_fires_nothing(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """An unload -- a reload, a stop -- cancels an announcement still
    loading the notification's texts: nothing announced, the mark unchanged.
    Once its first event has fired an announcement awaits nothing more, so
    an unload never cuts one in half: the next setup announces the payout,
    exactly once."""
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    operations.return_value = _paid(5)
    loading = asyncio.Event()

    async def _never_loaded(*_args, **_kwargs):
        loading.set()
        await asyncio.Event().wait()

    with patch(_TEXTS, _never_loaded):
        freezer.tick(timedelta(hours=1, minutes=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert loading.is_set()
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert events == []
    notifications.assert_not_called()
    await _flush(hass, freezer)
    assert _stored(hass_storage, entry)["known_rewards"] == {VSN["id"]: _WHEN[3]}

    await _setup(hass, entry)

    assert [event.data["credited_at"] for event in events] == [_WHEN[4]]
    notifications.assert_called_once()


async def test_one_pass_at_a_time(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """Two refreshes before Home Assistant has started -- setup's and an
    hourly one, each listing a new payout: one pass after the start, which
    reads the newest data and covers both payouts. While Home Assistant
    runs, a refresh that comes while a pass still loads its texts starts no
    second pass either. Each pass loads the texts once."""
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _known(hass_storage, entry, _WHEN[2])
    hass.set_state(CoreState.not_running)
    loaded = AsyncMock(side_effect=translation.async_get_translations)
    with patch(_TEXTS, loaded):
        await _setup(hass, entry)
        operations.return_value = _paid(5)
        await _next_hour(hass, freezer)
        assert operations.call_count == 2
        assert events == []

        await hass.async_start()
        await hass.async_block_till_done(wait_background_tasks=True)

    assert [(event.data["count"], event.data["credited_at"]) for event in events] == [
        (2, _WHEN[4])
    ]
    assert loaded.call_count == 1

    release = asyncio.Event()

    async def _held(*args, **kwargs):
        texts = await loaded(*args, **kwargs)
        await release.wait()
        return texts

    loaded.reset_mock()
    operations.return_value = _paid(6)
    with patch(_TEXTS, _held):
        for _ in range(2):
            freezer.tick(timedelta(hours=1, minutes=1))
            async_fire_time_changed(hass)
            await hass.async_block_till_done()
        assert operations.call_count == 4
        release.set()
        await hass.async_block_till_done(wait_background_tasks=True)

    assert [(event.data["count"], event.data["credited_at"]) for event in events] == [
        (2, _WHEN[4]),
        (1, _WHEN[5]),
    ]
    assert loaded.call_count == 1
    assert notifications.call_count == 2


# --- What it says ----------------------------------------------------------------------


async def test_switched_off_only_the_event_fires(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """The notification is off by default: the event fires all the same,
    and the mark moves on."""
    entry = _portfolio_entry(hass)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    operations.return_value = _paid(5)

    await _next_hour(hass, freezer)

    assert [event.data["credited_at"] for event in events] == [_WHEN[4]]
    notifications.assert_not_called()
    assert _mark(entry) == _WHEN[4]


async def test_without_a_price_the_value_is_none_and_the_sentence_left_out(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """/portfolio sent no value for Vision, so there is no price: the
    event's value is None, and the notification says nothing of what the
    payout is worth."""
    portfolio_api.return_value = _answer(_position(BTC), _position(VSN, staked=True, worth=None))
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    operations.return_value = _paid(5)

    await _next_hour(hass, freezer)

    device = _wallet_device(hass, entry)
    assert [(event.data["net"], event.data["value"]) for event in events] == [(9.87654312, None)]
    notifications.assert_called_once_with(
        hass,
        f"**[Vision (VSN) Wallet](/config/devices/device/{device.id})** received a staking "
        "reward of **9.87654312 VSN**.",
        "New Bitpanda staking reward",
        notification_id=f"bitpanda_staking_reward_{VSN['id']}",
    )


async def test_the_notification_follows_the_entrys_language(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """German, the Portfolio's language, while Home Assistant runs in
    English: the German texts, and the amounts with a decimal comma."""
    entry = _portfolio_entry(hass, language="de", notify_staking_rewards=True)
    _known(hass_storage, entry, _WHEN[0])
    operations.return_value = _paid(1)
    await _setup(hass, entry)
    operations.return_value = _paid(5)

    await _next_hour(hass, freezer)

    device = _wallet_device(hass, entry)
    notifications.assert_called_once_with(
        hass,
        f"**[Vision (VSN) Wallet](/config/devices/device/{device.id})** hat 4 "
        "Staking-Belohnungen erhalten, zusammen **39,50617248 VSN**. Heute etwa 0,26 EUR wert.",
        "Neue Bitpanda-Staking-Belohnung",
        notification_id=f"bitpanda_staking_reward_{VSN['id']}",
    )
    assert [(event.data["count"], event.data["net"], event.data["value"]) for event in events] == [
        (4, 39.50617248, 0.26)
    ]


def test_format_amount_and_format_money():
    """Amounts with up to 8 decimals, without trailing zeros; money with 2.
    A decimal point in English, a comma in every other language; never a
    thousands separator."""
    assert announcements.format_amount(9.87654312, "en") == "9.87654312"
    assert announcements.format_amount(39.50617248, "de") == "39,50617248"
    assert announcements.format_amount(10.0, "en") == "10"
    assert announcements.format_amount(10.0, "de") == "10"
    assert announcements.format_amount(1234567.5, "en") == "1234567.5"
    assert announcements.format_money(0.0661, "en") == "0.07"
    assert announcements.format_money(0.07, "de") == "0,07"
    assert announcements.format_money(1234.5, "de") == "1234,50"
    assert [
        announcements.format_amount(0.5, language) for language in ("fr", "nl", "it", "es", "pl")
    ] == ["0,5"] * 5


def test_every_shipped_language_has_its_decimal_separator():
    """A language added under translations/ needs its separator named in
    announcements.py; until then -- and for any language not shipped -- a
    point, the English way, rather than a guess."""
    shipped = {
        path.stem
        for path in (Path(announcements.__file__).parent / "translations").glob("*.json")
    }
    assert shipped == announcements.DECIMAL_COMMA | announcements.DECIMAL_POINT
    assert not announcements.DECIMAL_COMMA & announcements.DECIMAL_POINT
    assert announcements.format_amount(1.5, "ja") == "1.5"


async def test_a_failing_notification_still_fires_the_event_and_advances_the_mark(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer, caplog
):
    """Should Home Assistant fail to show the notification, the event has
    fired and the mark moves on all the same -- rather a notification
    missed than the payout announced again --, and a warning names the
    wallet and the error's type, without a traceback."""
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    notifications.side_effect = HomeAssistantError("the notification failed")
    operations.return_value = _paid(5)
    caplog.clear()

    await _next_hour(hass, freezer)
    await _flush(hass, freezer)

    assert [event.data["credited_at"] for event in events] == [_WHEN[4]]
    assert _stored(hass_storage, entry)["known_rewards"] == {VSN["id"]: _WHEN[4]}
    [record] = [r for r in caplog.records if r.name == "custom_components.bitpanda.announcements"]
    assert (record.levelname, record.getMessage(), record.exc_info) == (
        "WARNING",
        "Could not show the notification about the staking rewards of Vision (VSN) Wallet "
        "(HomeAssistantError)",
        None,
    )
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []


async def test_texts_that_cannot_be_loaded_still_fire_the_event_and_advance_the_mark(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer, caplog
):
    """Should the notification's texts fail to load -- a broken translation
    file, say -- the event fires and the mark moves on all the same, as when
    the notification itself fails, and the same warning names the wallet and
    the error's type, without a traceback."""
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    operations.return_value = _paid(5)
    caplog.clear()

    with patch(_TEXTS, AsyncMock(side_effect=HomeAssistantError("the texts could not be read"))):
        await _next_hour(hass, freezer)

    assert [event.data["credited_at"] for event in events] == [_WHEN[4]]
    assert _mark(entry) == _WHEN[4]
    notifications.assert_not_called()
    [record] = [r for r in caplog.records if r.name == "custom_components.bitpanda.announcements"]
    assert (record.levelname, record.getMessage(), record.exc_info) == (
        "WARNING",
        "Could not show the notification about the staking rewards of Vision (VSN) Wallet "
        "(HomeAssistantError)",
        None,
    )
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []


async def test_without_its_text_the_event_still_fires_and_the_mark_moves_on(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer, caplog
):
    """A broken install, whose files lack the message in every language: no
    notification, quietly, as for a new wallet -- but the event fires all
    the same, and the mark moves on."""
    with _texts_lacking(hass, "en", key="staking_reward"):
        entry = _portfolio_entry(hass, notify_staking_rewards=True)
        _known(hass_storage, entry, _WHEN[3])
        await _setup(hass, entry)
        operations.return_value = _paid(5)
        caplog.clear()
        await _next_hour(hass, freezer)

    assert [event.data["credited_at"] for event in events] == [_WHEN[4]]
    notifications.assert_not_called()
    assert _mark(entry) == _WHEN[4]
    assert [r for r in caplog.records if r.name == "custom_components.bitpanda.announcements"] == []


async def test_a_name_with_markdown_characters_shows_as_it_is(
    hass, portfolio_api, operations, events, notifications, hass_storage, freezer
):
    """Bitpanda's catalogue names some assets with Markdown's characters,
    such as "QuickSwap [Old]", and a symbol may carry one too: the
    notification escapes them, in its link and in its amount, so that they
    show as they are; the event carries them as they are."""
    quickswap = {**VSN, "name": "QuickSwap [Old]", "symbol": "QUICK_OLD"}
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _known(hass_storage, entry, _WHEN[3])
    renamed = AsyncMock(
        side_effect=lambda **kwargs: (
            [quickswap] if kwargs.get("asset_id") == VSN["id"] else _lookup(**kwargs)
        )
    )
    with patch(f"{_CLIENT}async_get_assets", renamed):
        await _setup(hass, entry)
        operations.return_value = _paid(5)
        await _next_hour(hass, freezer)

    device = _wallet_device(hass, entry)
    assert [(event.data["wallet"], event.data["symbol"]) for event in events] == [
        ("QuickSwap [Old] (QUICK_OLD) Wallet", "QUICK_OLD")
    ]
    assert notifications.call_args.args[1] == (
        rf"**[QuickSwap \[Old\] (QUICK\_OLD) Wallet](/config/devices/device/{device.id})** "
        r"received a staking reward of **9.87654312 QUICK\_OLD**. Worth about 0.07 EUR today."
    )


async def test_the_next_payout_replaces_the_notification(
    hass, portfolio_api, operations, hass_storage, hass_ws_client, freezer
):
    """In Home Assistant's own store, not patched: one notification per
    asset, carrying its title, its message and the link to the wallet; the
    asset's next payout replaces it instead of adding a second one."""
    assert await async_setup_component(hass, "persistent_notification", {})
    entry = _portfolio_entry(hass, notify_staking_rewards=True)
    _known(hass_storage, entry, _WHEN[3])
    await _setup(hass, entry)
    client = await hass_ws_client(hass)

    async def _shown() -> list[tuple[str, str, str]]:
        await client.send_json_auto_id({"type": "persistent_notification/get"})
        return [
            (notification["notification_id"], notification["title"], notification["message"])
            for notification in (await client.receive_json())["result"]
        ]

    link = f"/config/devices/device/{_wallet_device(hass, entry).id}"
    operations.return_value = _paid(5)
    await _next_hour(hass, freezer)
    assert await _shown() == [
        (
            f"bitpanda_staking_reward_{VSN['id']}",
            "New Bitpanda staking reward",
            f"**[Vision (VSN) Wallet]({link})** received a staking reward of "
            "**9.87654312 VSN**. Worth about 0.07 EUR today.",
        )
    ]

    operations.return_value = _paid(6)
    await _next_hour(hass, freezer)

    assert await _shown() == [
        (
            f"bitpanda_staking_reward_{VSN['id']}",
            "New Bitpanda staking reward",
            f"**[Vision (VSN) Wallet]({link})** received a staking reward of "
            "**9.68 VSN**. Worth about 0.06 EUR today.",
        )
    ]
