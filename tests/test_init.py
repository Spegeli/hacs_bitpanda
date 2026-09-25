"""Both services set up, reload and unload end to end (API mocked)."""
from datetime import timedelta
from types import MappingProxyType
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry, ConfigSubentryData
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.bitpanda import async_remove_config_entry_device
from custom_components.bitpanda.api import BitpandaAuthError
from custom_components.bitpanda.assets import slim_asset
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.devices import find_entry_device, subentry_devices
from custom_components.bitpanda.ecb import EcbRates

from tests.conftest import load_fixture, price_group

_CLIENT = "custom_components.bitpanda.api.BitpandaApiClient."
_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"


def _fixture(symbol: str, type_: str | None = None) -> dict:
    return next(
        a for a in load_fixture("assets-sample.json")
        if a["symbol"] == symbol and (type_ is None or a["type"] == type_)
    )


VSN, BTC, SOL = _fixture("VSN"), _fixture("BTC"), _fixture("SOL")
GOLD = _fixture("XAU", "commodity")


def _lookup(**kwargs):
    return [a for a in load_fixture("assets-sample.json") if a["id"] == kwargs.get("asset_id")]


@pytest.fixture
def portfolio_api():
    response = [
        {
            "asset_id": VSN["id"],
            "balance": {"value": "100.00000000"},
            "available_balance": {"value": "25.00000000"},
            "currency_balance": {"value": "200.00"},
        },
        {"currency_id": _EUR_ID, "balance": {"value": "10.00"}},
    ]
    with patch(f"{_CLIENT}async_get_portfolio", AsyncMock(return_value=response)) as portfolio, patch(
        f"{_CLIENT}async_get_portfolio_history", AsyncMock(return_value={"return_percentage": 1.5})
    ), patch(f"{_CLIENT}async_get_earn_configs", AsyncMock(return_value=[])), patch(
        f"{_CLIENT}async_get_operations", AsyncMock(return_value=[])
    ), patch(f"{_CLIENT}async_get_assets", AsyncMock(side_effect=_lookup)):
        yield portfolio


@pytest.fixture
def price_api():
    rates = EcbRates(date="2026-09-24", rates={"USD": 2.0})
    with patch(
        f"{_CLIENT}async_get_ticker", AsyncMock(return_value={"price": "100.00000000"})
    ) as ticker, patch(
        "custom_components.bitpanda.price_coordinator.async_fetch_ecb_rates",
        AsyncMock(return_value=rates),
    ) as ecb:
        yield ticker, ecb


def _portfolio_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR",
              "currency_id": _EUR_ID},
    )
    entry.add_to_hass(hass)
    return entry


def _price_entry(hass, extra, *groups: ConfigSubentryData) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="price_tracker", title="Bitpanda Price Tracker",
        data={"entry_type": "price_tracker"}, options={"extra_currencies": extra},
        subentries_data=list(groups),
    )
    entry.add_to_hass(hass)
    return entry


def _group(entry, category: str) -> ConfigSubentry:
    return next(sub for sub in entry.subentries.values() if sub.unique_id == category)


def _set_group_assets(hass, entry, category: str, *assets: dict) -> None:
    group = _group(entry, category)
    hass.config_entries.async_update_subentry(
        entry, group, data={**group.data, "assets": {a["id"]: slim_asset(a) for a in assets}}
    )


async def _setup(hass, entry) -> None:
    """Set up `entry`, tolerating Home Assistant's own bootstrap cascade.

    The first `hass.config_entries.async_setup()` call for a domain that has
    not been loaded yet also sets up every other existing entry of that
    domain in the same pass (`homeassistant/setup.py`: "Setting up the
    component will set up all its config entries") -- so a second entry
    added before the first `_setup()` call can already be LOADED by the time
    its own turn comes. Calling `async_setup()` again on an already-loaded
    entry raises `OperationNotAllowed`, so that case only waits and confirms
    the outcome instead of repeating the call.
    """
    if entry.state is ConfigEntryState.NOT_LOADED:
        assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


def _value(hass, entity_id) -> float:
    return float(hass.states.get(entity_id).state)


async def test_portfolio_setup_creates_its_devices_and_sensors(hass, portfolio_api):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 210.0
    assert _value(hass, "sensor.bitpanda_portfolio_cash") == 10.0
    assert _value(hass, "sensor.bitpanda_portfolio_cash_plus") == 0.0
    assert _value(hass, "sensor.bitpanda_portfolio_return_day") == 1.5
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet") == 50.0
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet_staking") == 150.0
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet_total") == 200.0
    wallet = hass.states.get("sensor.bitpanda_vision_vsn_wallet")
    assert wallet.attributes["friendly_name"] == "Vision (VSN) Wallet"
    assert (
        hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking").attributes["friendly_name"]
        == "Vision (VSN) Wallet Staking"
    )
    devices = {d.name for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)}
    assert devices == {"Portfolio", "Vision (VSN) Wallet"}


_VSN_ENTITIES = (
    "sensor.bitpanda_vision_vsn_wallet",
    "sensor.bitpanda_vision_vsn_wallet_staking",
    "sensor.bitpanda_vision_vsn_wallet_total",
)


def _group_devices(hass, entry, group: ConfigSubentry) -> list[str]:
    return sorted(d.name for d in subentry_devices(hass, entry.entry_id, group.subentry_id))


async def test_the_portfolio_groups_its_wallets_and_keeps_its_own_device_outside(
    hass, portfolio_api
):
    hass.config.language = "de"
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    [group] = entry.subentries.values()
    assert (group.subentry_type, group.unique_id, group.title) == (
        "wallet_group", "crypto", "Kryptowährungen",
    )
    ent_reg = er.async_get(hass)
    for entity_id in _VSN_ENTITIES:
        assert ent_reg.async_get(entity_id).config_subentry_id == group.subentry_id
    assert _group_devices(hass, entry, group) == ["Vision (VSN) Wallet"]
    for key in ("total", "cash", "cash_plus", "return_day"):
        assert ent_reg.async_get(f"sensor.bitpanda_portfolio_{key}").config_subentry_id is None
    portfolio = _own_device(hass, entry, "portfolio")
    assert portfolio is not None
    assert portfolio.name not in _group_devices(hass, entry, group)


async def _next_refresh(hass) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
    await hass.async_block_till_done()


async def test_a_deleted_wallet_group_comes_back_on_the_next_refresh_without_a_reload(
    hass, portfolio_api
):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    group = _group(entry, "crypto")
    calls = portfolio_api.call_count

    hass.config_entries.async_remove_subentry(entry, group.subentry_id)
    await hass.async_block_till_done()
    ent_reg = er.async_get(hass)
    assert [ent_reg.async_get(entity_id) for entity_id in _VSN_ENTITIES] == [None] * 3
    assert portfolio_api.call_count == calls

    await _next_refresh(hass)
    # The refresh's own request, no reload's.
    assert portfolio_api.call_count == calls + 1
    regrouped = _group(entry, "crypto")
    assert regrouped.subentry_id != group.subentry_id
    for entity_id in _VSN_ENTITIES:
        assert ent_reg.async_get(entity_id).config_subentry_id == regrouped.subentry_id
    assert _group_devices(hass, entry, regrouped) == ["Vision (VSN) Wallet"]
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet") == 50.0


async def test_wallet_groups_the_manager_adds_or_removes_never_reload_the_portfolio(
    hass, portfolio_api
):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    calls = portfolio_api.call_count
    held = portfolio_api.return_value
    portfolio_api.return_value = [
        *held,
        {
            "asset_id": GOLD["id"],
            "balance": {"value": "1.00000000"},
            "available_balance": {"value": "1.00000000"},
            "currency_balance": {"value": "3000.00"},
        },
    ]

    await _next_refresh(hass)
    assert portfolio_api.call_count == calls + 1
    assert [sub.unique_id for sub in entry.subentries.values()] == ["crypto", "metal"]
    assert _value(hass, "sensor.bitpanda_gold_xau_wallet") == 3000.0

    portfolio_api.return_value = held
    for _ in range(3):
        await _next_refresh(hass)
    assert portfolio_api.call_count == calls + 4
    assert [sub.unique_id for sub in entry.subentries.values()] == ["crypto"]
    assert er.async_get(hass).async_get("sensor.bitpanda_gold_xau_wallet") is None


@pytest.mark.parametrize(
    "change",
    [
        {"data": {"entry_type": "portfolio", "api_key": "new-key", "currency": "EUR",
                  "currency_id": _EUR_ID}},
        {"options": {"added_later": True}},
    ],
    ids=["data", "options"],
)
async def test_a_data_or_options_change_reloads_the_portfolio(hass, portfolio_api, change):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    calls = portfolio_api.call_count

    hass.config_entries.async_update_entry(entry, **change)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    # The reload's first refresh.
    assert portfolio_api.call_count == calls + 1


async def test_a_rejected_key_fails_setup_and_asks_for_a_new_one(hass, portfolio_api):
    portfolio_api.side_effect = BitpandaAuthError("Unauthorized for /portfolio")
    entry = _portfolio_entry(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]


def _reauth_flows(hass) -> list[dict]:
    return [
        flow for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        if flow["context"]["source"] == "reauth"
    ]


@pytest.mark.parametrize(
    ("method", "path"),
    [("async_get_earn_configs", "/earn/configs"), ("async_get_operations", "/operations")],
)
async def test_an_earn_or_operations_401_keeps_the_portfolio_loaded_and_asks_for_a_key(
    hass, portfolio_api, method, path
):
    """Earn and rewards only add to the Portfolio. A key they reject -- such
    as a migrated legacy key without the Earn or Transaction scope -- leaves
    the Portfolio running and asks for a new key."""
    entry = _portfolio_entry(hass)
    rejected = AsyncMock(side_effect=BitpandaAuthError(f"Unauthorized for {path}"))
    with patch(f"{_CLIENT}{method}", rejected):
        await _setup(hass, entry)
    rejected.assert_awaited()
    assert entry.state is ConfigEntryState.LOADED
    assert len(_reauth_flows(hass)) == 1
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet") == 50.0


async def test_reauth_with_the_same_key_revives_a_portfolio_stopped_by_a_401(
    hass, portfolio_api
):
    """A 401 on a scheduled refresh stops the portfolio coordinator for good
    and asks for a key. When Bitpanda recovers and the user re-enters the
    same, still valid key, nothing in the entry changes -- the Portfolio must
    be reloaded anyway, or it stays unavailable until a restart."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)

    portfolio_api.side_effect = BitpandaAuthError("Unauthorized for /portfolio")
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
    await hass.async_block_till_done()
    [flow] = _reauth_flows(hass)
    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet").state == "unavailable"

    portfolio_api.side_effect = None
    calls = portfolio_api.call_count
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=[])):
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"api_key": "key"}
        )
        await hass.async_block_till_done()
    assert result["reason"] == "reauth_successful"
    assert entry.state is ConfigEntryState.LOADED
    # The reload's first refresh asks for /portfolio again ...
    assert portfolio_api.call_count == calls + 1
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet") == 50.0
    # ... and polling goes on from there.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
    await hass.async_block_till_done()
    assert portfolio_api.call_count == calls + 2


async def test_reauth_with_a_new_key_reloads_the_portfolio_once(hass, portfolio_api):
    """The new key changes the entry's data, so the update listener reloads
    the Portfolio -- once: the flow leaves the reload to it."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    calls = portfolio_api.call_count
    result = await entry.start_reauth_flow(hass)
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=[])):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "new-key"}
        )
        await hass.async_block_till_done()
    assert result["reason"] == "reauth_successful"
    assert entry.data["api_key"] == "new-key"
    assert entry.state is ConfigEntryState.LOADED
    assert portfolio_api.call_count == calls + 1


async def test_price_tracker_setup_creates_one_sensor_per_asset_and_currency(hass, price_api):
    entry = _price_entry(hass, ["USD"], price_group("crypto", BTC))
    await _setup(hass, entry)
    assert _value(hass, "sensor.bitpanda_bitcoin_btc_eur") == 100.0
    assert _value(hass, "sensor.bitpanda_bitcoin_btc_usd") == 200.0
    usd = hass.states.get("sensor.bitpanda_bitcoin_btc_usd")
    assert usd.attributes["friendly_name"] == "Bitcoin (BTC) USD"
    assert usd.attributes["rate_source"] == "ECB"
    registry_entry = er.async_get(hass).async_get("sensor.bitpanda_bitcoin_btc_usd")
    assert registry_entry.config_subentry_id == _group(entry, "crypto").subentry_id
    device = dr.async_get(hass).async_get(registry_entry.device_id)
    assert device.name == "Bitcoin (BTC)"


async def test_the_price_tracker_polls_the_assets_of_every_group(hass, price_api):
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC, SOL), price_group("metal", GOLD))
    await _setup(hass, entry)
    assert sorted(call.args[0] for call in ticker.call_args_list) == sorted(
        a["id"] for a in (BTC, SOL, GOLD)
    )
    assert _value(hass, "sensor.bitpanda_gold_xau_eur") == 100.0


async def test_a_group_without_assets_is_dropped_at_setup(hass, price_api):
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC), price_group("metal"))
    await _setup(hass, entry)
    assert [sub.unique_id for sub in entry.subentries.values()] == ["crypto"]
    # Dropped before the update listener exists: no reload followed.
    assert ticker.call_count == 1


async def test_without_extra_currencies_the_ecb_is_never_asked(hass, price_api):
    _, ecb = price_api
    await _setup(hass, _price_entry(hass, [], price_group("crypto", BTC)))
    ecb.assert_not_called()


async def test_a_new_group_gets_its_sensors_after_the_reload(hass, price_api):
    entry = _price_entry(hass, [], price_group("crypto", BTC))
    await _setup(hass, entry)
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType({"category": "metal", "assets": {GOLD["id"]: slim_asset(GOLD)}}),
            subentry_type="price_group",
            title="Precious metals",
            unique_id="metal",
        ),
    )
    await hass.async_block_till_done()
    assert _value(hass, "sensor.bitpanda_gold_xau_eur") == 100.0


async def test_an_asset_added_to_a_group_gets_its_sensors_after_the_reload(hass, price_api):
    entry = _price_entry(hass, [], price_group("crypto", BTC))
    await _setup(hass, entry)
    _set_group_assets(hass, entry, "crypto", BTC, SOL)
    await hass.async_block_till_done()
    assert _value(hass, "sensor.bitpanda_solana_sol_eur") == 100.0
    registry_entry = er.async_get(hass).async_get("sensor.bitpanda_solana_sol_eur")
    assert registry_entry.config_subentry_id == _group(entry, "crypto").subentry_id


async def test_an_asset_tracked_again_gets_its_entity_ids_back(hass, price_api):
    """Leaving its group removes the asset's sensors and device on the
    reload; tracking it again brings the same entity IDs back."""
    entry = _price_entry(hass, [], price_group("crypto", BTC, SOL))
    await _setup(hass, entry)
    _set_group_assets(hass, entry, "crypto", BTC)
    await hass.async_block_till_done()
    assert er.async_get(hass).async_get("sensor.bitpanda_solana_sol_eur") is None
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert [device.name for device in devices] == ["Bitcoin (BTC)"]

    _set_group_assets(hass, entry, "crypto", BTC, SOL)
    await hass.async_block_till_done()
    assert _value(hass, "sensor.bitpanda_solana_sol_eur") == 100.0


async def test_dropping_a_currency_removes_its_sensors_on_reload(hass, price_api):
    entry = _price_entry(hass, ["USD"], price_group("crypto", BTC))
    await _setup(hass, entry)
    hass.config_entries.async_update_entry(entry, options={"extra_currencies": []})
    await hass.async_block_till_done()
    assert er.async_get(hass).async_get("sensor.bitpanda_bitcoin_btc_usd") is None
    assert hass.states.get("sensor.bitpanda_bitcoin_btc_eur") is not None


async def test_the_refresh_service_lives_while_any_entry_is_loaded(hass, portfolio_api, price_api):
    portfolio, tracker = _portfolio_entry(hass), _price_entry(hass, [], price_group("crypto", BTC))
    await _setup(hass, portfolio)
    await _setup(hass, tracker)
    assert hass.services.has_service(DOMAIN, "refresh")
    assert await hass.config_entries.async_unload(portfolio.entry_id)
    assert hass.services.has_service(DOMAIN, "refresh")
    assert await hass.config_entries.async_unload(tracker.entry_id)
    assert not hass.services.has_service(DOMAIN, "refresh")


# --- Deleting a device from its device page ------------------------------------------


def _identifier(entry, kind: str, asset: dict | None = None) -> str:
    """A device identifier of `entry`: `{entry_id}_{kind}[_{asset id}]`."""
    return f"{entry.entry_id}_{kind}" + (f"_{asset['id']}" if asset else "")


def _own_device(hass, entry, kind: str, asset: dict | None = None) -> dr.DeviceEntry:
    return find_entry_device(hass, entry.entry_id, _identifier(entry, kind, asset))


def _add_device(hass, entry, name: str, kind: str, asset: dict | None = None) -> dr.DeviceEntry:
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, _identifier(entry, kind, asset))},
        name=name,
    )


async def _remove_through_the_device_page(hass, hass_ws_client, entry, device) -> dict:
    """What "Delete" on a device page sends -- on the frontend of Home
    Assistant 2025.5, this integration's floor.

    Newer versions renamed the command `config/device_registry/remove`,
    which takes the `device_id` alone, and log the old name as a deprecated
    alias that Home Assistant 2027.9 removes. With a test image from 2027.9
    on, the device-page tests fail with an unknown command until this sends
    the new one.
    """
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


async def test_deleting_a_price_device_takes_its_asset_out_of_its_group(hass, price_api):
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC, SOL))
    await _setup(hass, entry)
    device = _own_device(hass, entry, "price", SOL)

    assert await async_remove_config_entry_device(hass, entry, device)
    await hass.async_block_till_done()

    assert list(_group(entry, "crypto").data["assets"]) == [BTC["id"]]
    assert er.async_get(hass).async_get("sensor.bitpanda_solana_sol_eur") is None
    assert dr.async_get(hass).async_get(device.id) is None
    # One reload, whose first refresh asks for the one asset left.
    assert ticker.call_count == 3


async def test_deleting_the_last_price_device_of_a_group_removes_the_group(hass, price_api):
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC), price_group("metal", GOLD))
    await _setup(hass, entry)
    device = _own_device(hass, entry, "price", GOLD)

    assert await async_remove_config_entry_device(hass, entry, device)
    await hass.async_block_till_done()

    assert [sub.unique_id for sub in entry.subentries.values()] == ["crypto"]
    assert er.async_get(hass).async_get("sensor.bitpanda_gold_xau_eur") is None
    assert dr.async_get(hass).async_get(device.id) is None
    assert ticker.call_count == 3


async def test_any_other_device_of_the_price_tracker_may_be_deleted(hass, price_api):
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC))
    await _setup(hass, entry)
    other = _add_device(hass, entry, "Bitpanda Price Tracker", "price_tracker")

    assert await async_remove_config_entry_device(hass, entry, other)
    await hass.async_block_till_done()

    assert list(_group(entry, "crypto").data["assets"]) == [BTC["id"]]
    assert ticker.call_count == 1


async def test_the_portfolio_device_cannot_be_deleted(hass, portfolio_api):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    assert not await async_remove_config_entry_device(
        hass, entry, _own_device(hass, entry, "portfolio")
    )


async def test_the_wallet_of_a_held_asset_cannot_be_deleted(hass, portfolio_api):
    """It would come straight back with the next refresh."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    calls = portfolio_api.call_count

    assert not await async_remove_config_entry_device(
        hass, entry, _own_device(hass, entry, "wallet", VSN)
    )
    await hass.async_block_till_done()
    assert portfolio_api.call_count == calls


async def test_a_holding_whose_balances_cannot_be_read_is_still_held(hass, portfolio_api):
    portfolio_api.return_value = [
        *portfolio_api.return_value,
        {"asset_id": BTC["id"], "balance": {"value": "unreadable"}},
    ]
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    wallet = _add_device(hass, entry, "Bitcoin (BTC) Wallet", "wallet", BTC)

    assert not await async_remove_config_entry_device(hass, entry, wallet)


async def test_the_wallet_of_an_asset_no_longer_held_may_be_deleted(hass, portfolio_api):
    """Allowed, with one reload: the wallet manager starts afresh, so the
    wallet comes back should the asset be bought again soon."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    wallet = _add_device(hass, entry, "Bitcoin (BTC) Wallet", "wallet", BTC)
    calls = portfolio_api.call_count

    assert await async_remove_config_entry_device(hass, entry, wallet)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert portfolio_api.call_count == calls + 1


async def test_a_legacy_device_of_the_portfolio_may_be_deleted(hass, portfolio_api):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    legacy = _add_device(hass, entry, "Bitpanda Wallets", "wallets")
    calls = portfolio_api.call_count

    assert await async_remove_config_entry_device(hass, entry, legacy)
    await hass.async_block_till_done()
    assert portfolio_api.call_count == calls


async def test_a_portfolio_that_is_not_loaded_refuses_only_its_portfolio_device(hass):
    entry = _portfolio_entry(hass)
    portfolio = _add_device(hass, entry, "Portfolio", "portfolio")
    wallet = _add_device(hass, entry, "Vision (VSN) Wallet", "wallet", VSN)
    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        assert not await async_remove_config_entry_device(hass, entry, portfolio)
        assert await async_remove_config_entry_device(hass, entry, wallet)
    reload.assert_not_called()


async def test_the_device_page_deletes_a_price_device(hass, price_api, hass_ws_client):
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC, SOL))
    await _setup(hass, entry)
    device = _own_device(hass, entry, "price", SOL)

    response = await _remove_through_the_device_page(hass, hass_ws_client, entry, device)
    await hass.async_block_till_done()

    assert response["success"]
    assert list(_group(entry, "crypto").data["assets"]) == [BTC["id"]]
    assert dr.async_get(hass).async_get(device.id) is None
    assert er.async_get(hass).async_get("sensor.bitpanda_solana_sol_eur") is None
    assert ticker.call_count == 3


async def test_the_device_page_refuses_to_delete_a_held_wallet(
    hass, portfolio_api, hass_ws_client
):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    wallet = _own_device(hass, entry, "wallet", VSN)

    response = await _remove_through_the_device_page(hass, hass_ws_client, entry, wallet)

    assert not response["success"]
    assert response["error"]["message"] == "Failed to remove device entry, rejected by integration"
    assert dr.async_get(hass).async_get(wallet.id) is not None
