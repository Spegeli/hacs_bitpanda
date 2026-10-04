"""Both services set up, reload and unload end to end (API mocked)."""
import asyncio
from contextlib import nullcontext
from datetime import timedelta
from itertools import count
from types import MappingProxyType
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.sensor import (
    DEVICE_CLASS_STATE_CLASSES,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry, ConfigSubentryData
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.bitpanda import (
    _async_first_refresh,
    async_remove_config_entry_device,
    migration,
    sensor,
)
from custom_components.bitpanda.api import (
    BitpandaApiError,
    BitpandaAuthError,
    BitpandaRateLimitError,
)
from custom_components.bitpanda.assets import slim_asset
from custom_components.bitpanda.const import (
    API_KEY_URL,
    DOMAIN,
    FIRST_LOAD_RETRY_INTERVAL,
    INTEGRATION_VERSION,
    PORTFOLIO_UPDATE_INTERVAL,
    PRICES_URL,
    REWARDS_UPDATE_INTERVAL,
    UNKNOWN_ASSET_RETRY,
)
from custom_components.bitpanda.devices import find_entry_device
from custom_components.bitpanda.ecb import EcbError, EcbRates
from custom_components.bitpanda.groups import async_add_asset_to_group
from custom_components.bitpanda.portfolio_store import async_get_portfolio_store
from custom_components.bitpanda.naming import (
    PORTFOLIO_KEYS,
    portfolio_device_identifier,
    portfolio_unique_id,
)

from tests.conftest import device_names_in_subentry, load_fixture, price_group, wallet_group

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


def _language(language: str | None) -> dict:
    """The entry option of `language`; none at all -- English -- for None."""
    return {} if language is None else {"language": language}


def _portfolio_entry(
    hass, *groups: ConfigSubentryData, api_key: str = "key", language: str | None = None
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": api_key, "currency": "EUR",
              "currency_id": _EUR_ID},
        options=_language(language),
        subentries_data=list(groups),
    )
    entry.add_to_hass(hass)
    return entry


def _price_entry(
    hass, extra, *groups: ConfigSubentryData, language: str | None = None
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="price_tracker", title="Bitpanda Price Tracker",
        data={"entry_type": "price_tracker"},
        options={"extra_currencies": extra, **_language(language)},
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
    """Set up `entry` and wait until it is loaded."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


def _value(hass, entity_id) -> float:
    return float(hass.states.get(entity_id).state)


def test_the_sensor_platform_sets_no_limit_on_parallel_updates():
    """Every sensor reads its coordinator's data and requests nothing
    itself: 0, explicitly (quality scale rule parallel-updates)."""
    assert sensor.PARALLEL_UPDATES == 0


async def test_the_portfolio_keeps_its_store_sections_on_its_runtime(hass, portfolio_api):
    """Loaded before the first refresh, the one store of the entry
    (portfolio_store.async_get_portfolio_store): its reloads keep using its
    sections."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    store = await async_get_portfolio_store(hass, entry.entry_id)
    known, marks = entry.runtime_data.known_wallets, entry.runtime_data.reward_marks
    assert known is store.known_wallets and marks is store.reward_marks
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.known_wallets is known
    assert entry.runtime_data.reward_marks is marks


async def test_portfolio_setup_creates_its_devices_and_sensors(hass, portfolio_api):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 210.0
    assert _value(hass, "sensor.bitpanda_portfolio_cash") == 10.0
    assert _value(hass, "sensor.bitpanda_portfolio_cash_plus") == 0.0
    assert _value(hass, "sensor.bitpanda_portfolio_return_day") == 1.5
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet_available") == 50.0
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet_staking") == 150.0
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet_total") == 200.0
    assert {
        entity_id: hass.states.get(entity_id).attributes["friendly_name"]
        for entity_id in _VSN_ENTITIES
    } == {
        "sensor.bitpanda_vision_vsn_wallet_available": "Vision (VSN) Wallet Balance (available)",
        "sensor.bitpanda_vision_vsn_wallet_staking": "Vision (VSN) Wallet Balance (staking)",
        "sensor.bitpanda_vision_vsn_wallet_total": "Vision (VSN) Wallet Balance (total)",
    }
    devices = {d.name for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)}
    assert devices == {"Portfolio", "Vision (VSN) Wallet"}


async def test_every_device_shows_its_link_the_version_and_the_assets_id(
    hass, portfolio_api, price_api
):
    """"Visit" leads to the API key page from the Portfolio and to Bitpanda's
    prices from a wallet or a price device; each shows the integration's
    version, and an asset's device its ID as the serial number. A device an
    earlier version registered takes them at the next start."""
    portfolio = _portfolio_entry(hass)
    tracker = _price_entry(hass, [], price_group("crypto", BTC))
    dev_reg = dr.async_get(hass)
    dev_reg.async_get_or_create(
        config_entry_id=portfolio.entry_id,
        identifiers={(DOMAIN, portfolio_device_identifier(portfolio.entry_id))},
        name="Portfolio", configuration_url="https://www.bitpanda.com",
    )
    await _setup(hass, portfolio)
    assert tracker.state is ConfigEntryState.LOADED

    devices = {
        device.name: (device.configuration_url, device.sw_version, device.serial_number)
        for entry in (portfolio, tracker)
        for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
    }
    assert devices == {
        "Portfolio": (API_KEY_URL, INTEGRATION_VERSION, None),
        "Vision (VSN) Wallet": (PRICES_URL, INTEGRATION_VERSION, VSN["id"]),
        "Bitcoin (BTC) Price Tracker": (PRICES_URL, INTEGRATION_VERSION, BTC["id"]),
    }


async def test_the_wallet_sensor_keeps_its_name_without_staking(hass, portfolio_api):
    """Named "Balance (available)" whether or not Staking stands beside it:
    nothing staked and no Earn product offered here."""
    position, cash = portfolio_api.return_value
    portfolio_api.return_value = [
        {**position, "available_balance": {"value": "100.00000000"}}, cash,
    ]
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking") is None
    assert (
        hass.states.get("sensor.bitpanda_vision_vsn_wallet_available").attributes["friendly_name"]
        == "Vision (VSN) Wallet Balance (available)"
    )


_PERFORMANCE = {
    "average_buy_price": 1.5,
    "invested_amount": 150.0,
    "total_return": 50.0,
    "total_return_percent": 33.33,
}


async def test_a_wallet_without_staking_shows_its_performance_on_its_total(hass, portfolio_api):
    """Every wallet has its Balance (total), staking or not, and the
    position performance is there only -- never on Balance (available), so
    it does not move between sensors when staking starts or stops."""
    position, cash = portfolio_api.return_value
    portfolio_api.return_value = [
        {
            **position,
            "available_balance": {"value": "100.00000000"},
            "average_buy_price": {"value": "1.50000000"},
            "invested_amount": {"value": "150.00"},
            "total_return": {"value": "50.00"},
            "total_return_percent": "33.33",
        },
        cash,
    ]
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking") is None
    total = hass.states.get("sensor.bitpanda_vision_vsn_wallet_total")
    assert (float(total.state), total.attributes["friendly_name"]) == (
        200.0, "Vision (VSN) Wallet Balance (total)"
    )
    assert {key: total.attributes.get(key) for key in _PERFORMANCE} == _PERFORMANCE
    available = hass.states.get("sensor.bitpanda_vision_vsn_wallet_available").attributes
    assert set(_PERFORMANCE) & set(available) == set()


async def test_no_sensor_state_carries_an_icon(hass, portfolio_api, price_api):
    """Icons come from icons.json by translation key (tests/test_icons.py):
    the frontend looks them up, and no state carries one as an attribute."""
    portfolio = _portfolio_entry(hass)
    _price_entry(hass, ["USD"], price_group("crypto", BTC))
    # The first setup of the domain sets up both entries.
    await _setup(hass, portfolio)
    states = hass.states.async_all("sensor")
    assert len(states) >= 10
    assert [state.entity_id for state in states if "icon" in state.attributes] == []


async def test_every_sensor_keeps_long_term_statistics(hass, portfolio_api, price_api, caplog):
    """Every value sensor sets a state class: money `total` -- the only one
    Home Assistant allows for the monetary device class -- and the returns
    (%) `measurement`. Home Assistant accepts each: no warning about an
    impossible state class."""
    portfolio = _portfolio_entry(hass)
    _price_entry(hass, ["USD"], price_group("crypto", BTC))
    # The first setup of the domain sets up both entries.
    await _setup(hass, portfolio)
    classes = {
        state.entity_id: (
            state.attributes.get("device_class"),
            state.attributes.get("state_class"),
            state.attributes.get("unit_of_measurement"),
        )
        for state in hass.states.async_all("sensor")
    }
    # Eight Portfolio figures, the staked VSN's three sensors, BTC in EUR and USD.
    assert len(classes) == 13
    for entity_id, (device_class, state_class, unit) in classes.items():
        if device_class == SensorDeviceClass.MONETARY:
            assert state_class == SensorStateClass.TOTAL, entity_id
            assert state_class in DEVICE_CLASS_STATE_CLASSES[SensorDeviceClass.MONETARY]
        else:
            assert (device_class, state_class, unit) == (
                None, SensorStateClass.MEASUREMENT, "%"
            ), entity_id
    assert "impossible considering device class" not in caplog.text


async def test_every_portfolio_figure_is_one_the_currency_purge_knows(hass, portfolio_api):
    """The currency purge (purge.py) tells the Portfolio device's sensors
    apart by naming.PORTFOLIO_KEYS: a figure added without its key there
    would keep its old-currency history through a currency change."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    device = find_entry_device(dr.async_get(hass), entry.entry_id, f"{entry.entry_id}_portfolio")
    figures = {
        reg_entry.unique_id
        for reg_entry in er.async_entries_for_device(
            er.async_get(hass), device.id, include_disabled_entities=True
        )
    }
    assert figures == {portfolio_unique_id(entry.entry_id, key) for key in PORTFOLIO_KEYS}


_RUNTIME_SECRET = "totally-secret-runtime-key"


async def test_the_runtime_repr_never_prints_the_api_key(hass, portfolio_api):
    """PortfolioRuntime.data_at_setup is `dict(entry.data)`, which holds the
    key. HA's profiler services (`dump_log_objects`, `start_log_object_sources`)
    log object reprs at CRITICAL, so the dataclass's generated repr must not
    hand the key to them."""
    entry = _portfolio_entry(hass, api_key=_RUNTIME_SECRET)
    await _setup(hass, entry)
    assert _RUNTIME_SECRET not in repr(entry.runtime_data)


_VSN_ENTITIES = (
    "sensor.bitpanda_vision_vsn_wallet_available",
    "sensor.bitpanda_vision_vsn_wallet_staking",
    "sensor.bitpanda_vision_vsn_wallet_total",
)


def _group_devices(hass, entry, group: ConfigSubentry | None) -> set[str]:
    """Names of the devices in `group`, or in none for None."""
    subentry_id = None if group is None else group.subentry_id
    return device_names_in_subentry(hass, entry.entry_id, subentry_id)


async def test_the_portfolio_groups_its_wallets_and_keeps_its_own_device_outside(
    hass, portfolio_api
):
    """The group the wallet manager creates is titled in the entry's language."""
    entry = _portfolio_entry(hass, language="de")
    await _setup(hass, entry)
    [group] = entry.subentries.values()
    assert (group.subentry_type, group.unique_id, group.title) == (
        "wallet_group", "crypto", "Kryptowährungen",
    )
    ent_reg = er.async_get(hass)
    for entity_id in _VSN_ENTITIES:
        assert ent_reg.async_get(entity_id).config_subentry_id == group.subentry_id
    assert _group_devices(hass, entry, group) == {"Vision (VSN) Wallet"}
    for key in ("total", "cash", "cash_plus", "return_day"):
        assert ent_reg.async_get(f"sensor.bitpanda_portfolio_{key}").config_subentry_id is None
    assert _group_devices(hass, entry, None) == {"Portfolio"}


async def _next_refresh(hass, freezer) -> None:
    """The Portfolio's next regular refresh: Home Assistant's clock moves on
    past its update interval, and the refresh it scheduled runs to its end
    -- a background task, which only wait_background_tasks waits for. The
    clock matters: an empty portfolio is believed, and a sold asset's wallet
    removed, only once their answers span two update intervals."""
    freezer.tick(timedelta(minutes=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_a_deleted_wallet_group_comes_back_on_the_next_refresh_without_a_reload(
    hass, portfolio_api, freezer
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

    await _next_refresh(hass, freezer)
    # The refresh's own request, no reload's.
    assert portfolio_api.call_count == calls + 1
    regrouped = _group(entry, "crypto")
    assert regrouped.subentry_id != group.subentry_id
    for entity_id in _VSN_ENTITIES:
        assert ent_reg.async_get(entity_id).config_subentry_id == regrouped.subentry_id
    assert _group_devices(hass, entry, regrouped) == {"Vision (VSN) Wallet"}
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet_available") == 50.0


async def test_wallet_groups_the_manager_adds_or_removes_never_reload_the_portfolio(
    hass, portfolio_api, freezer
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

    await _next_refresh(hass, freezer)
    assert portfolio_api.call_count == calls + 1
    assert [sub.unique_id for sub in entry.subentries.values()] == ["crypto", "metal"]
    assert _value(hass, "sensor.bitpanda_gold_xau_wallet_available") == 3000.0

    portfolio_api.return_value = held
    for _ in range(3):
        await _next_refresh(hass, freezer)
    assert portfolio_api.call_count == calls + 4
    assert [sub.unique_id for sub in entry.subentries.values()] == ["crypto"]
    assert er.async_get(hass).async_get("sensor.bitpanda_gold_xau_wallet_available") is None


async def test_a_staking_sensor_added_later_brings_old_rewards_up_to_date(
    hass, portfolio_api, freezer
):
    """The rewards are polled only while a Staking sensor listens. The first
    one added after setup -- once something is staked -- finds the totals of
    setup's own refresh; older than an interval, they are refreshed at once
    instead of an interval later."""
    staked = portfolio_api.return_value
    portfolio_api.return_value = [
        {**staked[0], "available_balance": {"value": "100.00000000"}},
        staked[1],
    ]
    with patch(f"{_CLIENT}async_get_operations", AsyncMock(return_value=[])) as operations:
        entry = _portfolio_entry(hass)
        await _setup(hass, entry)
        assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking") is None
        assert operations.await_count == 1

        # An interval later, something is staked.
        portfolio_api.return_value = staked
        freezer.tick(REWARDS_UPDATE_INTERVAL)
        async_fire_time_changed(hass)
        await hass.async_block_till_done(wait_background_tasks=True)

    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking") is not None
    assert operations.await_count == 2


async def test_a_staking_sensor_asks_again_for_rewards_that_never_arrived(hass, portfolio_api):
    rejected = AsyncMock(side_effect=BitpandaApiError("HTTP 503 from /operations"))
    with patch(f"{_CLIENT}async_get_operations", rejected):
        entry = _portfolio_entry(hass)
        await _setup(hass, entry)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking") is not None
    # Setup's own refresh, then the one the Staking sensor asked for.
    assert rejected.await_count == 2


async def test_a_staking_sensor_added_with_current_rewards_asks_for_nothing(
    hass, portfolio_api
):
    """No extra polling: setup has just fetched them."""
    with patch(f"{_CLIENT}async_get_operations", AsyncMock(return_value=[])) as operations:
        entry = _portfolio_entry(hass)
        await _setup(hass, entry)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_staking") is not None
    assert operations.await_count == 1


def _no_connection(*, equivalent_currency_id=None):
    """/portfolio while the Internet connection at home is down: no request
    reaches Bitpanda. A side effect raising a fresh error at each call: one
    instance raised again and again keeps a growing traceback, and with it
    the frames of every test that raised it, alive."""
    raise BitpandaApiError("Cannot connect to /portfolio", kind="connection", path="/portfolio")


async def test_the_portfolio_keeps_its_figures_through_two_failed_refreshes(
    hass, portfolio_api, freezer
):
    """The Portfolio's figures and wallets keep their last values through
    two failed refreshes. The third, twelve minutes after the first, confirms
    the outage: unavailable until Bitpanda answers again. The wallet stays
    registered throughout: a failed refresh counts no miss."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.side_effect = _no_connection
    ent_reg = er.async_get(hass)

    for _ in range(2):
        await _next_refresh(hass, freezer)
        assert _value(hass, "sensor.bitpanda_portfolio_total") == 210.0
        assert _value(hass, "sensor.bitpanda_vision_vsn_wallet_available") == 50.0

    await _next_refresh(hass, freezer)
    for entity_id in (
        "sensor.bitpanda_portfolio_total", "sensor.bitpanda_vision_vsn_wallet_available"
    ):
        assert hass.states.get(entity_id).state == "unavailable"
    assert ent_reg.async_get("sensor.bitpanda_vision_vsn_wallet_available") is not None

    portfolio_api.side_effect = None
    await _next_refresh(hass, freezer)
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 210.0
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet_available") == 50.0


async def test_a_sudden_empty_portfolio_changes_nothing_until_it_is_confirmed(
    hass, portfolio_api, freezer
):
    """A Bitpanda glitch must not read as a sale of everything: the
    Portfolio's figures and its wallets stay as they were until three empty
    answers in a row confirm it. From then on the usual rules apply."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = []
    ent_reg = er.async_get(hass)

    for _ in range(2):
        await _next_refresh(hass, freezer)
        assert _value(hass, "sensor.bitpanda_portfolio_total") == 210.0
        assert _value(hass, "sensor.bitpanda_vision_vsn_wallet_available") == 50.0
    assert ent_reg.async_get("sensor.bitpanda_vision_vsn_wallet_available") is not None

    # Confirmed: the truth from here on, and the wallet's first miss.
    await _next_refresh(hass, freezer)
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 0.0
    await _next_refresh(hass, freezer)
    assert ent_reg.async_get("sensor.bitpanda_vision_vsn_wallet_available") is not None
    await _next_refresh(hass, freezer)
    assert ent_reg.async_get("sensor.bitpanda_vision_vsn_wallet_available") is None


async def test_an_empty_portfolio_mixed_with_a_timeout(hass, portfolio_api, freezer):
    """An empty answer, a request that fails (a timeout, or here a lost
    connection), an empty answer: three failed refreshes in a row -- an
    empty answer held back is one -- twelve minutes from the first to the
    last, so the outage is confirmed before the empty portfolio is. The
    figures stay through the first two and are unavailable after the third;
    the next empty answer, the third in a row, confirms the empty
    portfolio: 0."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = []

    await _next_refresh(hass, freezer)
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 210.0
    portfolio_api.side_effect = _no_connection
    await _next_refresh(hass, freezer)
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 210.0
    portfolio_api.side_effect = None
    await _next_refresh(hass, freezer)
    assert hass.states.get("sensor.bitpanda_portfolio_total").state == "unavailable"

    await _next_refresh(hass, freezer)
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 0.0


async def test_a_figure_bitpanda_leaves_unreadable_is_unknown_not_unavailable(
    hass, portfolio_api, freezer
):
    """The answer arrived, but an entry in it cannot be read: Total value and
    Cash Plus -- which it might belong to -- show `unknown`, never a figure
    that quietly leaves it out; Cash, which it cannot belong to, is shown.
    An unreadable fiat balance makes Cash, and so Total value, unknown."""
    readable = portfolio_api.return_value
    portfolio_api.return_value = [
        *readable,
        {"asset_id": BTC["id"], "balance": {"value": "unreadable"}},
    ]
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    assert hass.states.get("sensor.bitpanda_portfolio_total").state == "unknown"
    assert hass.states.get("sensor.bitpanda_portfolio_cash_plus").state == "unknown"
    assert _value(hass, "sensor.bitpanda_portfolio_cash") == 10.0

    portfolio_api.return_value = [
        readable[0], {"currency_id": _EUR_ID, "balance": {"value": "unreadable"}},
    ]
    await _next_refresh(hass, freezer)
    assert hass.states.get("sensor.bitpanda_portfolio_cash").state == "unknown"
    assert hass.states.get("sensor.bitpanda_portfolio_total").state == "unknown"
    assert _value(hass, "sensor.bitpanda_portfolio_cash_plus") == 0.0


async def test_a_return_without_a_figure_is_unknown_and_a_failed_one_unavailable(
    hass, portfolio_api
):
    """The month is answered without a usable figure: unknown. The week's
    own request fails: unavailable. The other timeframes are shown."""

    async def _history(*, timeframe, equivalent_currency_id=None):
        if timeframe == "WEEK":
            raise BitpandaApiError(
                "HTTP 503 from /portfolio-history",
                kind="http_status", path="/portfolio-history", status=503,
            )
        return {"return_percentage": None if timeframe == "MONTH" else 1.5}

    with patch(f"{_CLIENT}async_get_portfolio_history", AsyncMock(side_effect=_history)):
        await _setup(hass, _portfolio_entry(hass))
    assert hass.states.get("sensor.bitpanda_portfolio_return_month").state == "unknown"
    assert hass.states.get("sensor.bitpanda_portfolio_return_week").state == "unavailable"
    assert _value(hass, "sensor.bitpanda_portfolio_return_day") == 1.5


async def test_a_return_keeps_its_value_while_its_timeframe_fails(hass, portfolio_api, freezer):
    """The week's own request starts failing after setup while the other
    timeframes answer: its return keeps its last value through two
    refreshes, and the third, twelve minutes after the first, makes it
    unavailable. The other returns are shown throughout."""
    await _setup(hass, _portfolio_entry(hass))
    week = "sensor.bitpanda_portfolio_return_week"
    others = [
        f"sensor.bitpanda_portfolio_return_{suffix}"
        for suffix in ("day", "month", "6_months", "year")
    ]

    async def _history(*, timeframe, equivalent_currency_id=None):
        if timeframe == "WEEK":
            raise BitpandaApiError(
                "HTTP 503 from /portfolio-history",
                kind="http_status", path="/portfolio-history", status=503,
            )
        return {"return_percentage": 1.5}

    with patch(f"{_CLIENT}async_get_portfolio_history", AsyncMock(side_effect=_history)):
        for _ in range(2):
            await _next_refresh(hass, freezer)
            assert _value(hass, week) == 1.5
            assert [_value(hass, entity_id) for entity_id in others] == [1.5] * 4
        await _next_refresh(hass, freezer)
        assert hass.states.get(week).state == "unavailable"
        assert [_value(hass, entity_id) for entity_id in others] == [1.5] * 4


async def test_a_held_wallet_whose_value_cannot_be_told_is_unknown(hass, portfolio_api, freezer):
    """While /portfolio lists the asset, its Wallet, Staking and Total are
    unknown when Bitpanda sends no value or an entry that cannot be read;
    once it is no longer listed they are unavailable, until removed."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    vsn, eur = portfolio_api.return_value

    portfolio_api.return_value = [
        {key: value for key, value in vsn.items() if key != "currency_balance"}, eur,
    ]
    await _next_refresh(hass, freezer)
    assert {hass.states.get(entity_id).state for entity_id in _VSN_ENTITIES} == {"unknown"}

    portfolio_api.return_value = [
        {"asset_id": VSN["id"], "balance": {"value": "unreadable"}}, eur,
    ]
    await _next_refresh(hass, freezer)
    assert {hass.states.get(entity_id).state for entity_id in _VSN_ENTITIES} == {"unknown"}

    portfolio_api.return_value = [eur]
    await _next_refresh(hass, freezer)
    assert {hass.states.get(entity_id).state for entity_id in _VSN_ENTITIES} == {"unavailable"}


def _registered_wallet(hass, entry) -> str:
    """The VSN wallet of `entry` as a restart finds it: its device and its
    Wallet sensor in the registries, nothing loaded yet."""
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_wallet_{VSN['id']}")},
        name="Vision (VSN) Wallet",
    )
    return er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_wallet_{VSN['id']}", config_entry=entry,
        device_id=device.id, suggested_object_id="bitpanda_vision_vsn_wallet_available",
    ).entity_id


@pytest.mark.parametrize(
    "first_refresh", [None, "before_2026_9"], ids=["current", "before_2026_9"]
)
async def test_after_a_restart_an_empty_portfolio_waits_for_confirmation(
    hass, portfolio_api, caplog, first_refresh, freezer
):
    """A wallet registered from before the restart: the account listed
    something. An empty first answer loads the Portfolio with its sensors
    unavailable -- retrying setup would bring the next answers within
    seconds -- and nothing is removed until three empty answers in a row, at
    the usual pace, confirm it. From then on the usual rules apply. On every
    supported Home Assistant version: before 2026.9 the failed first refresh
    carries its reason only through _async_first_refresh."""
    entry = _portfolio_entry(hass)
    wallet = _registered_wallet(hass, entry)
    portfolio_api.return_value = []

    with _home_assistant_first_refresh(
        None if first_refresh is None else _first_refresh_before_2026_9
    ):
        await _setup(hass, entry)
    assert "Bitpanda reported an empty portfolio" in caplog.text
    ent_reg = er.async_get(hass)
    for _ in range(2):
        assert hass.states.get("sensor.bitpanda_portfolio_total").state == "unavailable"
        assert ent_reg.async_get(wallet) is not None
        await _next_refresh(hass, freezer)

    # The third empty answer in a row: the truth, and the wallet's first miss.
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 0.0
    await _next_refresh(hass, freezer)
    assert ent_reg.async_get(wallet) is not None
    await _next_refresh(hass, freezer)
    assert ent_reg.async_get(wallet) is None


def _refreshed_by_hand():
    """bitpanda.refresh's own clock, a cooldown and more between two calls."""
    return patch("custom_components.bitpanda.monotonic", side_effect=count(1000, 60))


async def test_refreshing_by_hand_never_confirms_an_empty_portfolio_sooner(
    hass, portfolio_api, freezer
):
    """Empty answers by hand, twenty seconds apart: each fails the call, and
    none is the truth, however many -- until two update intervals have
    passed since the first; the first empty answer after that is. Until
    then the figures stay: however many failed refreshes, they came too
    quickly to confirm an outage either."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = []
    ent_reg = er.async_get(hass)
    with _refreshed_by_hand():
        for _ in range(4):
            freezer.tick(timedelta(seconds=20))
            with pytest.raises(HomeAssistantError):
                await _refresh(hass)
        assert _value(hass, "sensor.bitpanda_portfolio_total") == 210.0
        assert ent_reg.async_get("sensor.bitpanda_vision_vsn_wallet_available") is not None

        freezer.tick(2 * PORTFOLIO_UPDATE_INTERVAL)
        await _refresh(hass)
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 0.0


async def test_a_start_of_the_portfolio_keeps_the_not_migrated_issue_up_to_date(
    hass, portfolio_api
):
    """The issue lists what the upgrade left alone; once the user deleted
    all of it by hand, the next start of the Portfolio takes the issue away
    (tests/test_repairs.py has the rest)."""
    ir.async_create_issue(
        hass, DOMAIN, "entities_not_migrated", is_fixable=False, is_persistent=True,
        severity=ir.IssueSeverity.WARNING, translation_key="entities_not_migrated",
        translation_placeholders={"entities": "- `sensor.bitpanda_wallets_stonkbroker_wallet`"},
    )
    await _setup(hass, _portfolio_entry(hass))
    assert ir.async_get(hass).async_get_issue(DOMAIN, "entities_not_migrated") is None


async def test_a_rejected_key_keeps_the_not_migrated_issue_up_to_date_all_the_same(
    hass, portfolio_api
):
    """Right after the upgrade Bitpanda rejects the old key: the start
    still brings the issue up to date, before it asks Bitpanda."""
    portfolio_api.side_effect = BitpandaAuthError("Unauthorized for /portfolio")
    ir.async_create_issue(
        hass, DOMAIN, "entities_not_migrated", is_fixable=False, is_persistent=True,
        severity=ir.IssueSeverity.WARNING, translation_key="entities_not_migrated",
        translation_placeholders={"entities": "- `sensor.bitpanda_wallets_stonkbroker_wallet`"},
    )
    entry = _portfolio_entry(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, "entities_not_migrated") is None


async def test_the_not_migrated_issue_goes_with_the_portfolio(hass, portfolio_api, price_api):
    """Its entities go with the Portfolio, so it goes too -- not with the
    Price Tracker."""
    tracker = _price_entry(hass, [], price_group("crypto", BTC))
    portfolio = _portfolio_entry(hass)
    await _setup(hass, tracker)
    migration.async_raise_not_migrated_issue(
        hass, portfolio.entry_id, ["sensor.bitpanda_wallets_stonkbroker_wallet"]
    )
    await hass.config_entries.async_remove(tracker.entry_id)
    assert ir.async_get(hass).async_get_issue(DOMAIN, "entities_not_migrated") is not None

    _price_entry(hass, [])
    await hass.config_entries.async_remove(portfolio.entry_id)
    assert ir.async_get(hass).async_get_issue(DOMAIN, "entities_not_migrated") is None


async def test_cash_plus_has_its_value_beside_a_holding_the_catalogue_does_not_list(
    hass, portfolio_api
):
    """The catalogue answers without the held asset: it gets no wallet, but
    Cash Plus -- the catalogue lists every Cash Plus product -- keeps its
    value."""
    with patch(f"{_CLIENT}async_get_assets", AsyncMock(return_value=[])):
        await _setup(hass, _portfolio_entry(hass))
    assert _value(hass, "sensor.bitpanda_portfolio_cash_plus") == 0.0
    assert er.async_get(hass).async_get("sensor.bitpanda_vision_vsn_wallet_available") is None


async def test_cash_plus_is_unknown_while_a_holding_cannot_be_looked_up(hass, portfolio_api):
    """A failed lookup tells nothing: the holding might be Cash Plus."""
    failing = AsyncMock(side_effect=BitpandaApiError("HTTP 503 from /assets"))
    with patch(f"{_CLIENT}async_get_assets", failing):
        await _setup(hass, _portfolio_entry(hass))
    assert hass.states.get("sensor.bitpanda_portfolio_cash_plus").state == "unknown"


async def test_a_holding_the_catalogue_lists_later_gets_its_wallet_within_a_day(
    hass, portfolio_api, freezer
):
    """Not in the catalogue -- at least not yet: no wallet, and no lookup at
    every refresh. Once the catalogue lists it, the first refresh a day after
    the last lookup adds its wallet -- without a restart."""
    listed: list[dict] = []
    assets = AsyncMock(
        side_effect=lambda **kwargs: [a for a in listed if a["id"] == kwargs.get("asset_id")]
    )
    ent_reg = er.async_get(hass)
    with patch(f"{_CLIENT}async_get_assets", assets):
        await _setup(hass, _portfolio_entry(hass))
        assert ent_reg.async_get("sensor.bitpanda_vision_vsn_wallet_available") is None

        listed.append(VSN)
        await _next_refresh(hass, freezer)
        assert ent_reg.async_get("sensor.bitpanda_vision_vsn_wallet_available") is None
        assert assets.await_count == 1

        freezer.tick(UNKNOWN_ASSET_RETRY)
        await _next_refresh(hass, freezer)
    assert ent_reg.async_get("sensor.bitpanda_vision_vsn_wallet_available") is not None


async def test_refreshing_by_hand_never_removes_a_sold_wallet_sooner(
    hass, portfolio_api, freezer
):
    """Answers without the sold asset by hand, twenty seconds apart: its
    wallet stays, however many -- until two update intervals have passed
    since the first of them; the first such answer after that removes it."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    _, eur = portfolio_api.return_value
    portfolio_api.return_value = [eur]
    ent_reg = er.async_get(hass)
    with _refreshed_by_hand():
        for _ in range(4):
            freezer.tick(timedelta(seconds=20))
            await _refresh(hass)
        assert ent_reg.async_get("sensor.bitpanda_vision_vsn_wallet_available") is not None

        freezer.tick(2 * PORTFOLIO_UPDATE_INTERVAL)
        await _refresh(hass)
    assert ent_reg.async_get("sensor.bitpanda_vision_vsn_wallet_available") is None


async def test_a_new_empty_account_is_set_up_at_once(hass, portfolio_api):
    """No wallet registered: nothing to hold back."""
    portfolio_api.return_value = []
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 0.0


async def test_the_count_of_empty_answers_survives_a_reload(hass, portfolio_api, freezer):
    """The reload's first answer, at once, is the third empty one in a row,
    not a first -- yet the ten minutes still run from the first: the next
    regular answer, twelve minutes after it, is the truth. Had the reload
    started over, that one would be only the second."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = []
    await _next_refresh(hass, freezer)
    await _next_refresh(hass, freezer)

    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.bitpanda_portfolio_total").state == "unavailable"

    await _next_refresh(hass, freezer)
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 0.0


_BCPEUR = _fixture("BCPEUR")
# Answers of accounts that have no wallet registered although they list
# something: holdings of Cash Plus alone, which gets no wallet, or fiat alone.
_WALLETLESS_ANSWERS = {
    "cash_plus_holdings": [
        {
            "asset_id": _BCPEUR["id"],
            "balance": {"value": "250.75000000"},
            "available_balance": {"value": "250.75000000"},
            "currency_balance": {"value": "250.75"},
        },
    ],
    "fiat_only": [{"currency_id": _EUR_ID, "balance": {"value": "10.00"}}],
}


@pytest.mark.parametrize("listed", list(_WALLETLESS_ANSWERS))
async def test_an_empty_answer_after_a_reload_waits_although_no_wallet_is_registered(
    hass, portfolio_api, freezer, listed
):
    """What the account listed before the reload is remembered, wallets or
    none: an empty answer after it leaves the Portfolio unavailable until
    three answers in a row, at the usual pace, confirm it."""
    portfolio_api.return_value = _WALLETLESS_ANSWERS[listed]
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    assert _value(hass, "sensor.bitpanda_portfolio_total") > 0
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert [device.name for device in devices] == ["Portfolio"]
    portfolio_api.return_value = []

    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    for _ in range(2):
        assert hass.states.get("sensor.bitpanda_portfolio_total").state == "unavailable"
        await _next_refresh(hass, freezer)
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 0.0


async def test_removing_the_portfolio_forgets_its_empty_answers_and_what_it_listed(
    hass, portfolio_api, freezer
):
    """Both outlive reloads and retried setups, not the entry."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = []
    await _next_refresh(hass, freezer)
    assert hass.data["bitpanda_empty_portfolio_answers"][entry.entry_id].count == 1
    assert hass.data["bitpanda_portfolio_listed"][entry.entry_id] is True

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data["bitpanda_empty_portfolio_answers"]
    assert entry.entry_id not in hass.data["bitpanda_portfolio_listed"]


async def test_removing_the_portfolio_deletes_its_known_wallets(
    hass, portfolio_api, hass_storage, freezer
):
    """The list goes with the entry, its file too: a new setup starts
    without one (portfolio_store.py)."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    entry.runtime_data.known_wallets.seed({"BTC"})
    freezer.tick(timedelta(seconds=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    key = f"bitpanda.portfolio.{entry.entry_id}"
    assert key in hass_storage

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert key not in hass_storage
    assert (await async_get_portfolio_store(hass, entry.entry_id)).known_wallets.first_run is True


async def test_a_wallet_may_be_deleted_while_an_empty_answer_awaits_confirmation(
    hass, portfolio_api
):
    """Before any answer is taken as the truth nothing tells whether the
    asset is held, and no wallet was added in this run: it may go, without
    a reload."""
    entry = _portfolio_entry(hass)
    _registered_wallet(hass, entry)
    portfolio_api.return_value = []
    await _setup(hass, entry)
    with patch.object(hass.config_entries, "async_schedule_reload") as reload:
        assert await async_remove_config_entry_device(
            hass, entry, _own_device(hass, entry, "wallet", VSN)
        )
    reload.assert_not_called()


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
    # The integration page shows the reason translated, from its key; the
    # English text is what Home Assistant keeps as the reason itself.
    assert entry.error_reason_translation_key == "api_key_rejected"
    assert entry.reason == "Bitpanda rejected the API key"


async def _first_refresh_before_2026_9(self) -> None:
    """DataUpdateCoordinator.async_config_entry_first_refresh as Home
    Assistant 2025.5 to 2026.8 have it: the ConfigEntryNotReady it raises
    carries no translation, only the failed update as its cause."""
    await self._async_refresh(
        log_failures=False, raise_on_auth_failed=True, raise_on_entry_error=True
    )
    if self.last_update_success:
        return
    ex = ConfigEntryNotReady()
    ex.__cause__ = self.last_exception
    raise ex


_FIRST_REFRESH = pytest.mark.parametrize(
    "first_refresh", [None, _first_refresh_before_2026_9], ids=["current", "before_2026_9"]
)


def _home_assistant_first_refresh(first_refresh):
    return (
        nullcontext() if first_refresh is None
        else patch.object(DataUpdateCoordinator, "async_config_entry_first_refresh", first_refresh)
    )


@_FIRST_REFRESH
async def test_a_failed_first_portfolio_refresh_retries_with_a_translated_reason(
    hass, portfolio_api, first_refresh
):
    """The "retrying setup" reason on the integration page is translated on
    every supported Home Assistant version, the floor included -- all of
    it: its placeholders are the request path and the HTTP status, never
    the API client's English message."""
    portfolio_api.side_effect = BitpandaApiError(
        "HTTP 503 from /portfolio", kind="http_status", path="/portfolio", status=503
    )
    entry = _portfolio_entry(hass)
    with _home_assistant_first_refresh(first_refresh):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "update_failed_http_status"
    assert entry.error_reason_translation_placeholders == {"path": "/portfolio", "status": "503"}
    assert entry.reason == (
        "Could not fetch data from Bitpanda: /portfolio answered with HTTP status 503"
    )


@_FIRST_REFRESH
async def test_a_rate_limited_first_portfolio_refresh_says_so(hass, portfolio_api, first_refresh):
    """A 429 has a text of its own, the request path its only placeholder --
    not "answered with HTTP status 429"."""
    portfolio_api.side_effect = BitpandaRateLimitError(
        "Rate limited on /portfolio", kind="rate_limited", path="/portfolio", status=429
    )
    entry = _portfolio_entry(hass)
    with _home_assistant_first_refresh(first_refresh):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "update_failed_rate_limited"
    assert entry.error_reason_translation_placeholders == {"path": "/portfolio"}
    assert entry.reason == "Could not fetch data from Bitpanda: too many requests for /portfolio"


async def test_the_translated_not_ready_is_raised_from_none():
    """Like every exception this integration raises into Home Assistant: no
    exception chain behind it."""

    class _Coordinator:
        async def async_config_entry_first_refresh(self):
            ex = ConfigEntryNotReady()
            ex.__cause__ = UpdateFailed(translation_domain=DOMAIN, translation_key="no_prices")
            raise ex

    with pytest.raises(ConfigEntryNotReady) as excinfo:
        await _async_first_refresh(_Coordinator())
    assert (excinfo.value.translation_domain, excinfo.value.translation_key) == (
        DOMAIN, "no_prices"
    )
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__


@_FIRST_REFRESH
async def test_a_failed_first_price_refresh_retries_with_a_translated_reason(
    hass, price_api, first_refresh
):
    ticker, _ = price_api
    ticker.side_effect = BitpandaApiError("HTTP 503 from /tickers")
    entry = _price_entry(hass, [], price_group("crypto", BTC))
    with _home_assistant_first_refresh(first_refresh):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "no_prices"
    assert entry.reason == "No prices could be fetched from Bitpanda"


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
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet_available") == 50.0


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
    # A scheduled refresh runs as a background task.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
    await hass.async_block_till_done(wait_background_tasks=True)
    [flow] = _reauth_flows(hass)
    assert hass.states.get("sensor.bitpanda_vision_vsn_wallet_available").state == "unavailable"

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
    assert _value(hass, "sensor.bitpanda_vision_vsn_wallet_available") == 50.0
    # ... and polling goes on from there.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
    await hass.async_block_till_done(wait_background_tasks=True)
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
    assert _value(hass, "sensor.bitpanda_bitcoin_btc_price_tracker_eur") == 100.0
    assert _value(hass, "sensor.bitpanda_bitcoin_btc_price_tracker_usd") == 200.0
    usd = hass.states.get("sensor.bitpanda_bitcoin_btc_price_tracker_usd")
    assert usd.attributes["friendly_name"] == "Bitcoin (BTC) Price Tracker USD"
    assert usd.attributes["rate_source"] == "ECB"
    registry_entry = er.async_get(hass).async_get("sensor.bitpanda_bitcoin_btc_price_tracker_usd")
    assert registry_entry.config_subentry_id == _group(entry, "crypto").subentry_id
    device = dr.async_get(hass).async_get(registry_entry.device_id)
    assert device.name == "Bitcoin (BTC) Price Tracker"


async def _next_price_round(hass, freezer) -> None:
    """The Price Tracker's next regular round: Home Assistant's clock moves
    on past its update interval -- 60 seconds for a few assets -- and the
    refresh it scheduled runs to its end, a background task."""
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_prices_keep_their_value_through_two_failed_rounds(hass, price_api, freezer):
    """No ticker request reaches Bitpanda: the prices keep their last values,
    in every currency, through two rounds. The third, two minutes after the
    first, confirms the outage: unavailable until Bitpanda answers again."""
    ticker, _ = price_api
    await _setup(hass, _price_entry(hass, ["USD"], price_group("crypto", BTC)))
    prices = [
        "sensor.bitpanda_bitcoin_btc_price_tracker_eur",
        "sensor.bitpanda_bitcoin_btc_price_tracker_usd",
    ]
    ticker.side_effect = BitpandaApiError(
        "Cannot connect to /tickers", kind="connection", path="/tickers"
    )

    for _ in range(2):
        await _next_price_round(hass, freezer)
        assert [_value(hass, entity_id) for entity_id in prices] == [100.0, 200.0]

    await _next_price_round(hass, freezer)
    assert [hass.states.get(entity_id).state for entity_id in prices] == ["unavailable"] * 2

    ticker.side_effect = None
    await _next_price_round(hass, freezer)
    assert [_value(hass, entity_id) for entity_id in prices] == [100.0, 200.0]


async def test_one_failing_asset_keeps_its_price_through_two_rounds(hass, price_api, freezer):
    """Only Bitcoin's requests fail, while Solana's answer: Bitcoin keeps its
    last price through two rounds, and the third, two minutes after the
    first, makes it unavailable -- Solana's price is shown throughout.
    Bitcoin's first answer brings it back."""
    ticker, _ = price_api
    await _setup(hass, _price_entry(hass, [], price_group("crypto", BTC, SOL)))
    bitcoin = "sensor.bitpanda_bitcoin_btc_price_tracker_eur"
    solana = "sensor.bitpanda_solana_sol_price_tracker_eur"

    async def _ticker(asset_id):
        if asset_id == BTC["id"]:
            raise BitpandaApiError(
                "HTTP 404 from /tickers", kind="http_status", path="/tickers", status=404
            )
        return {"price": "100.00000000"}

    ticker.side_effect = _ticker
    for _ in range(2):
        await _next_price_round(hass, freezer)
        assert [_value(hass, bitcoin), _value(hass, solana)] == [100.0, 100.0]

    await _next_price_round(hass, freezer)
    assert hass.states.get(bitcoin).state == "unavailable"
    assert _value(hass, solana) == 100.0

    ticker.side_effect = None
    await _next_price_round(hass, freezer)
    assert [_value(hass, bitcoin), _value(hass, solana)] == [100.0, 100.0]


async def test_the_price_tracker_is_set_up_although_its_first_assets_never_answer(
    hass, price_api
):
    """Bitcoin and Solana, tracked first, never answer; Vision does. Setup's
    round is a first round, which asks for every asset all the same: the
    Price Tracker is set up, Vision's price is shown, and Bitcoin's and
    Solana's are unavailable."""
    ticker, _ = price_api

    async def _ticker(asset_id):
        if asset_id in (BTC["id"], SOL["id"]):
            raise BitpandaApiError("Timeout for /tickers", kind="timeout", path="/tickers")
        return {"price": "100.00000000"}

    ticker.side_effect = _ticker
    entry = _price_entry(hass, [], price_group("crypto", BTC, SOL, VSN))
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert _value(hass, "sensor.bitpanda_vision_vsn_price_tracker_eur") == 100.0
    for entity_id in (
        "sensor.bitpanda_bitcoin_btc_price_tracker_eur",
        "sensor.bitpanda_solana_sol_price_tracker_eur",
    ):
        assert hass.states.get(entity_id).state == "unavailable"


# A micro-cap missing from assets-sample.json, as Bitpanda's catalogue lists it.
_SHIB = {
    "id": "516a8dfd-2800-11ec-a40d-0a69e15c2b31",
    "symbol": "SHIB",
    "name": "SHIBA INU",
    "type": "cryptocoin",
    "group": "token",
}


def _stored_precision(hass, entity_id) -> int:
    """The display precision Home Assistant stored for a sensor in the entity
    registry: the frontend rounds the sensor's state to it."""
    options = er.async_get(hass).async_get(entity_id).options
    return options["sensor"]["suggested_display_precision"]


async def test_a_price_sensor_added_without_a_value_stores_its_precision_with_the_first_one(
    hass, price_api, freezer
):
    """Home Assistant stores a sensor's suggested display precision as it
    adds the sensor -- without a value, 2 decimals -- and not again as its
    state changes. SHIBA INU's request fails in the setup round, so its
    sensor is added without a price; its first one, a round later, stores
    the 8 decimals it needs -- once: SHIBA INU's later price, which would
    need 4, keeps them. Bitcoin, added with its price, keeps its 2, though
    its next price would need 4."""
    ticker, _ = price_api
    prices = {BTC["id"]: "100.00000000"}

    async def _ticker(asset_id):
        if asset_id not in prices:
            raise BitpandaApiError("Timeout for /tickers", kind="timeout", path="/tickers")
        return {"price": prices[asset_id]}

    ticker.side_effect = _ticker
    await _setup(hass, _price_entry(hass, [], price_group("crypto", BTC, _SHIB)))
    bitcoin = "sensor.bitpanda_bitcoin_btc_price_tracker_eur"
    shiba = "sensor.bitpanda_shiba_inu_shib_price_tracker_eur"
    assert hass.states.get(shiba).state == "unavailable"
    assert _stored_precision(hass, shiba) == 2

    prices.update({BTC["id"]: "5.00000000", _SHIB["id"]: "0.0000108"})
    await _next_price_round(hass, freezer)
    assert [_value(hass, bitcoin), _value(hass, shiba)] == [5.0, 0.0000108]
    assert _stored_precision(hass, shiba) == 8
    assert _stored_precision(hass, bitcoin) == 2

    prices[_SHIB["id"]] = "5.00000000"
    await _next_price_round(hass, freezer)
    assert _value(hass, shiba) == 5.0
    assert _stored_precision(hass, shiba) == 8


async def test_a_price_sensor_added_at_zero_stores_its_precision_with_its_first_other_price(
    hass, price_api, freezer
):
    """A price of 0 says no more about its size than no price: the sensor
    added at 0 stores the decimals of its first price other than 0 -- not
    those of a later 0."""
    ticker, _ = price_api
    ticker.return_value = {"price": "0.00000000"}
    await _setup(hass, _price_entry(hass, [], price_group("crypto", _SHIB)))
    shiba = "sensor.bitpanda_shiba_inu_shib_price_tracker_eur"
    assert _value(hass, shiba) == 0.0
    assert _stored_precision(hass, shiba) == 2

    await _next_price_round(hass, freezer)
    assert _value(hass, shiba) == 0.0
    assert _stored_precision(hass, shiba) == 2

    ticker.return_value = {"price": "0.0000108"}
    await _next_price_round(hass, freezer)
    assert _value(hass, shiba) == 0.0000108
    assert _stored_precision(hass, shiba) == 8


async def test_a_converted_price_stores_its_precision_once_the_rates_arrive(
    hass, price_api, freezer
):
    """The same for a converted price: the ECB fetch fails at setup, so the
    USD sensor is added without a value. The rates arrive at the retry,
    FIRST_LOAD_RETRY_INTERVAL later, and the sensor stores the precision of
    its first value."""
    ticker, ecb = price_api
    ticker.return_value = {"price": "0.0000108"}
    ecb.side_effect = EcbError("Timeout fetching the ECB rates", kind="timeout")
    await _setup(hass, _price_entry(hass, ["USD"], price_group("crypto", _SHIB)))
    usd = "sensor.bitpanda_shiba_inu_shib_price_tracker_usd"
    assert hass.states.get(usd).state == "unknown"
    assert _stored_precision(hass, usd) == 2

    ecb.side_effect = None
    freezer.tick(FIRST_LOAD_RETRY_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    # 0.0000108 EUR at 2 USD per EUR.
    assert _value(hass, usd) == 0.0000216
    assert _stored_precision(hass, usd) == 8


async def test_a_price_sensor_registered_before_keeps_its_id_and_takes_the_new_names(
    hass, price_api
):
    """Registered under the scheme before this one: Home Assistant keeps
    the registered entity ID, while the device name and with it the
    sensor's name follow the new scheme at the next load."""
    entry = _price_entry(hass, [], price_group("crypto", BTC))
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_price_{BTC['id']}")},
        name="Bitcoin (BTC)",
    )
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_{BTC['id']}_price_EUR", config_entry=entry,
        device_id=device.id, suggested_object_id="bitpanda_bitcoin_btc_eur",
    )
    await _setup(hass, entry)
    assert hass.states.get("sensor.bitpanda_bitcoin_btc_price_tracker_eur") is None
    assert _value(hass, "sensor.bitpanda_bitcoin_btc_eur") == 100.0
    assert (
        hass.states.get("sensor.bitpanda_bitcoin_btc_eur").attributes["friendly_name"]
        == "Bitcoin (BTC) Price Tracker EUR"
    )
    assert dr.async_get(hass).async_get(device.id).name == "Bitcoin (BTC) Price Tracker"


# An ETF missing from assets-sample.json: the one the README's entity ID table shows.
_AMUNDI = {
    "id": "1f0ed6c9-ee10-68c6-8a0e-55a29b7757fe",
    "symbol": "LYY1",
    "name": "Amundi PEA S&P 500 UCITS ETF",
    "isin": "FR0011871136",
    "type": "equity_security",
    "group": "equity_etf",
}


async def test_a_wallet_registered_before_keeps_its_id_and_takes_the_new_names(
    hass, portfolio_api
):
    """The same for a wallet, here an ETF's from before its label carried
    the ISIN: its device was "… (LYY1) Wallet" and its sensor `…_wallet`,
    named as the device. The device takes its new name, the sensor its
    name "Balance (available)"; the sensor keeps its entity ID."""
    position, cash = portfolio_api.return_value
    portfolio_api.return_value = [
        {**position, "asset_id": _AMUNDI["id"], "available_balance": {"value": "100.00000000"}},
        cash,
    ]
    entry = _portfolio_entry(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_wallet_{_AMUNDI['id']}")},
        name="Amundi PEA S&P 500 UCITS ETF (LYY1) Wallet",
    )
    registered = "sensor.bitpanda_amundi_pea_s_p_500_ucits_etf_lyy1_wallet"
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_wallet_{_AMUNDI['id']}", config_entry=entry,
        device_id=device.id, suggested_object_id=registered.split(".", 1)[1],
    )

    def _assets(**kwargs):
        return [_AMUNDI] if kwargs.get("asset_id") == _AMUNDI["id"] else _lookup(**kwargs)

    with patch(f"{_CLIENT}async_get_assets", AsyncMock(side_effect=_assets)):
        await _setup(hass, entry)

    assert dr.async_get(hass).async_get(device.id).name == (
        "Amundi PEA S&P 500 UCITS ETF (LYY1 / FR0011871136) Wallet"
    )
    assert hass.states.get(
        "sensor.bitpanda_amundi_pea_s_p_500_ucits_etf_lyy1_fr0011871136_wallet_available"
    ) is None
    assert _value(hass, registered) == 200.0
    assert hass.states.get(registered).attributes["friendly_name"] == (
        "Amundi PEA S&P 500 UCITS ETF (LYY1 / FR0011871136) Wallet Balance (available)"
    )


async def test_the_price_tracker_polls_the_assets_of_every_group(hass, price_api):
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC, SOL), price_group("metal", GOLD))
    await _setup(hass, entry)
    assert sorted(call.args[0] for call in ticker.call_args_list) == sorted(
        a["id"] for a in (BTC, SOL, GOLD)
    )
    assert _value(hass, "sensor.bitpanda_gold_xau_price_tracker_eur") == 100.0


async def test_the_price_tracker_names_a_stock_etf_or_etc_with_its_isin(
    hass, price_api, caplog, freezer
):
    """Its device, its sensors and the log carry the ISIN in the label; the
    log names the asset itself, without the device's " Price Tracker". The
    asset's failure is warned about once it is confirmed, at the third
    round."""
    ticker, _ = price_api
    top500 = _fixture("SXR8", "security")

    async def _ticker(asset_id):
        if asset_id == top500["id"]:
            raise BitpandaApiError("Timeout for /tickers")
        return {"price": "100.00000000"}

    ticker.side_effect = _ticker
    entry = _price_entry(hass, [], price_group("crypto", BTC), price_group("etf", top500))
    await _setup(hass, entry)
    for _ in range(2):
        await _next_price_round(hass, freezer)
    registry_entry = er.async_get(hass).async_get(
        "sensor.bitpanda_top_500_us_stocks_x_acc_sxr8_ie00b5bmr087_price_tracker_eur"
    )
    assert dr.async_get(hass).async_get(registry_entry.device_id).name == (
        "Top 500 US Stocks X Acc (SXR8 / IE00B5BMR087) Price Tracker"
    )
    assert (
        "No price for Top 500 US Stocks X Acc (SXR8 / IE00B5BMR087); its price sensors"
        in caplog.text
    )


async def test_a_group_without_assets_is_dropped_at_setup(hass, price_api):
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC), price_group("metal"))
    await _setup(hass, entry)
    assert [sub.unique_id for sub in entry.subentries.values()] == ["crypto"]
    # Dropped before the update listener exists: no reload followed.
    assert ticker.call_count == 1


# Four ticker requests an hour: three tracked assets need 45 minutes between
# refreshes, two need 30 -- the Price Tracker's interval above and at the
# 30-minute mark without tracking hundreds of assets.
def _four_tickers_an_hour():
    return patch("custom_components.bitpanda.price_coordinator.TICKER_HOURLY_BUDGET", 4)


def _interval_issue(hass):
    return ir.async_get(hass).async_get_issue(DOMAIN, "slow_price_interval")


async def test_a_price_interval_above_thirty_minutes_is_a_repair_issue_until_it_is_not(
    hass, price_api
):
    """Raised at setup, before any price is asked for; gone with the reload
    that stopping to track an asset causes, the interval back at 30
    minutes."""
    with _four_tickers_an_hour():
        entry = _price_entry(
            hass, [], price_group("crypto", BTC, SOL), price_group("metal", GOLD)
        )
        await _setup(hass, entry)
        assert _interval_issue(hass).translation_placeholders == {
            "count": "3", "minutes": "45"
        }

        _set_group_assets(hass, entry, "crypto", BTC)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert _interval_issue(hass) is None


async def test_the_price_interval_issue_goes_with_the_price_tracker(
    hass, price_api, portfolio_api
):
    """Deleting the Price Tracker ends it; deleting the Portfolio does not."""
    with _four_tickers_an_hour():
        tracker = _price_entry(
            hass, [], price_group("crypto", BTC, SOL), price_group("metal", GOLD)
        )
        portfolio = _portfolio_entry(hass)
        # The first setup of the domain sets up both entries.
        await _setup(hass, tracker)
        assert portfolio.state is ConfigEntryState.LOADED
        assert _interval_issue(hass) is not None

        await hass.config_entries.async_remove(portfolio.entry_id)
        assert _interval_issue(hass) is not None

        await hass.config_entries.async_remove(tracker.entry_id)
    assert _interval_issue(hass) is None


async def test_without_extra_currencies_the_ecb_is_never_asked(hass, price_api):
    _, ecb = price_api
    await _setup(hass, _price_entry(hass, [], price_group("crypto", BTC)))
    ecb.assert_not_called()


async def test_the_price_tracker_is_set_up_while_the_ecb_is_unreachable(hass, price_api):
    """Without ECB rates the EUR sensors still work: a failed first fetch of
    the rates does not fail the setup. The other currencies wait for the
    rates, with the status `no_rate`."""
    _, ecb = price_api
    ecb.side_effect = EcbError("Timeout fetching the ECB rates", kind="timeout")
    await _setup(hass, _price_entry(hass, ["USD"], price_group("crypto", BTC)))
    assert _value(hass, "sensor.bitpanda_bitcoin_btc_price_tracker_eur") == 100.0
    usd = hass.states.get("sensor.bitpanda_bitcoin_btc_price_tracker_usd")
    assert (usd.state, usd.attributes["conversion"]) == ("unknown", "no_rate")


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
    assert _value(hass, "sensor.bitpanda_gold_xau_price_tracker_eur") == 100.0


async def test_an_asset_added_to_a_group_gets_its_sensors_after_the_reload(hass, price_api):
    entry = _price_entry(hass, [], price_group("crypto", BTC))
    await _setup(hass, entry)
    _set_group_assets(hass, entry, "crypto", BTC, SOL)
    await hass.async_block_till_done()
    assert _value(hass, "sensor.bitpanda_solana_sol_price_tracker_eur") == 100.0
    registry_entry = er.async_get(hass).async_get("sensor.bitpanda_solana_sol_price_tracker_eur")
    assert registry_entry.config_subentry_id == _group(entry, "crypto").subentry_id


async def test_an_asset_tracked_again_gets_its_entity_ids_back(hass, price_api):
    """Leaving its group removes the asset's sensors and device on the
    reload; tracking it again brings the same entity IDs back."""
    entry = _price_entry(hass, [], price_group("crypto", BTC, SOL))
    await _setup(hass, entry)
    _set_group_assets(hass, entry, "crypto", BTC)
    await hass.async_block_till_done()
    assert er.async_get(hass).async_get("sensor.bitpanda_solana_sol_price_tracker_eur") is None
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert [device.name for device in devices] == ["Bitcoin (BTC) Price Tracker"]

    _set_group_assets(hass, entry, "crypto", BTC, SOL)
    await hass.async_block_till_done()
    assert _value(hass, "sensor.bitpanda_solana_sol_price_tracker_eur") == 100.0


async def test_dropping_a_currency_removes_its_sensors_on_reload(hass, price_api):
    entry = _price_entry(hass, ["USD"], price_group("crypto", BTC))
    await _setup(hass, entry)
    hass.config_entries.async_update_entry(entry, options={"extra_currencies": []})
    await hass.async_block_till_done()
    assert er.async_get(hass).async_get("sensor.bitpanda_bitcoin_btc_price_tracker_usd") is None
    assert hass.states.get("sensor.bitpanda_bitcoin_btc_price_tracker_eur") is not None


async def test_renaming_the_price_tracker_asks_for_no_prices(hass, price_api):
    """A new title changes nothing the Price Tracker tracks: no reload, so
    no round of ticker requests either. The empty group its setup dropped
    counts as no change: setup made it itself."""
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC, SOL), price_group("metal"))
    await _setup(hass, entry)
    assert [sub.unique_id for sub in entry.subentries.values()] == ["crypto"]
    runtime = entry.runtime_data
    calls = ticker.call_count

    hass.config_entries.async_update_entry(entry, title="My prices")
    await hass.async_block_till_done()

    assert entry.title == "My prices"
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is runtime
    assert ticker.call_count == calls


async def test_toggling_polling_reloads_the_price_tracker_once(hass, price_api, hass_ws_client):
    """"Enable polling for updates", a system option, is saved through Home
    Assistant's own update, which reloads the entry itself. That is the one
    reload, with its round of ticker requests: the update listener starts
    none, neither before it nor besides it."""
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC, SOL))
    await _setup(hass, entry)
    runtime = entry.runtime_data
    calls = ticker.call_count
    assert await async_setup_component(hass, "config", {})
    client = await hass_ws_client(hass)

    with patch.object(
        hass.config_entries, "async_reload", wraps=hass.config_entries.async_reload
    ) as reload:
        await client.send_json_auto_id(
            {
                "type": "config_entries/update",
                "entry_id": entry.entry_id,
                "pref_disable_polling": True,
            }
        )
        response = await client.receive_json()
        await hass.async_block_till_done()

    assert response["success"]
    # Home Assistant's answer shows the entry as the update left it, before
    # Home Assistant's own reload: still loaded, so no reload had begun.
    assert response["result"]["config_entry"]["state"] == ConfigEntryState.LOADED.value
    assert entry.pref_disable_polling
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not runtime
    assert reload.call_count == 1
    # The reload's first refresh: one request per tracked asset (BTC, SOL).
    assert ticker.call_count == calls + 2


async def test_renaming_a_price_group_does_not_reload_the_price_tracker(hass, price_api):
    """A group's title is no part of what the Price Tracker tracks -- its
    assets are. Newer Home Assistant versions let the user rename a group:
    that asks for no prices."""
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC, SOL))
    await _setup(hass, entry)
    runtime = entry.runtime_data
    calls = ticker.call_count

    hass.config_entries.async_update_subentry(entry, _group(entry, "crypto"), title="My coins")
    await hass.async_block_till_done()

    assert _group(entry, "crypto").title == "My coins"
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is runtime
    assert ticker.call_count == calls


async def test_a_change_to_the_price_trackers_data_reloads_it(hass, price_api):
    """Its data is part of what it tracks, beside its options and its
    groups: a change there reloads it."""
    entry = _price_entry(hass, [], price_group("crypto", BTC))
    await _setup(hass, entry)
    runtime = entry.runtime_data

    hass.config_entries.async_update_entry(entry, data={**entry.data, "note": "changed"})
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not runtime


async def test_switching_new_entities_off_does_not_reload_the_price_tracker(hass, price_api):
    """A system option other than polling changes nothing it tracks, and
    Home Assistant reloads nothing for it either: no prices are asked for."""
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC))
    await _setup(hass, entry)
    runtime = entry.runtime_data
    calls = ticker.call_count

    hass.config_entries.async_update_entry(entry, pref_disable_new_entities=True)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is runtime
    assert ticker.call_count == calls


async def test_an_asset_added_while_the_price_tracker_starts_gets_its_price(hass, price_api):
    """No update listener exists while the Price Tracker starts -- here the
    first price round of a reload. An asset added to a group meanwhile is not
    in what that start tracks: once set up, the Price Tracker sees that what
    it tracks changed and reloads once more, and the asset gets its price."""
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC))
    await _setup(hass, entry)
    gate, entered = asyncio.Event(), asyncio.Event()

    async def _held(asset_id):
        entered.set()
        await gate.wait()
        return {"price": "100.00000000"}

    ticker.side_effect = _held
    # A change to what it tracks: the listener reloads, and the reload's
    # first round waits for the gate.
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType({"category": "metal", "assets": {GOLD["id"]: slim_asset(GOLD)}}),
            subentry_type="price_group",
            title="Precious metals",
            unique_id="metal",
        ),
    )
    await entered.wait()
    async_add_asset_to_group(hass, entry, _group(entry, "crypto"), slim_asset(SOL))
    ticker.side_effect = None
    gate.set()
    await hass.async_block_till_done(wait_background_tasks=True)

    assert entry.state is ConfigEntryState.LOADED
    assert _value(hass, "sensor.bitpanda_solana_sol_price_tracker_eur") == 100.0


async def test_a_start_that_adopts_legacy_prices_reloads_nothing_more(hass, price_api):
    """The first start after an upgrade from a date version takes over the
    legacy price entities and drops the list of them from the entry's data.
    That is setup's own change, made before what the start tracks is read:
    no second reload follows."""
    ticker, _ = price_api
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="price_tracker", title="Bitpanda Price Tracker",
        data={"entry_type": "price_tracker", "legacy_adopt": {"entities": []}},
        options={"extra_currencies": []},
        subentries_data=[price_group("crypto", BTC)],
    )
    entry.add_to_hass(hass)
    await _setup(hass, entry)
    runtime = entry.runtime_data
    await hass.async_block_till_done(wait_background_tasks=True)

    assert "legacy_adopt" not in entry.data
    assert entry.runtime_data is runtime
    assert ticker.call_count == 1


async def test_a_start_with_no_change_meanwhile_reloads_nothing_more(hass, price_api):
    """After an ordinary start the check at its end finds nothing changed --
    the empty group the start dropped is its own change -- and reloads
    nothing: one price round, one runtime."""
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC, SOL), price_group("metal"))
    await _setup(hass, entry)
    runtime = entry.runtime_data
    await hass.async_block_till_done(wait_background_tasks=True)

    assert entry.runtime_data is runtime
    assert ticker.call_count == 2


async def _refresh(hass) -> None:
    await hass.services.async_call(DOMAIN, "refresh", blocking=True)
    await hass.async_block_till_done()


async def test_the_refresh_action_refreshes_a_loaded_portfolio(hass, portfolio_api):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    calls = portfolio_api.call_count
    await _refresh(hass)
    assert portfolio_api.call_count == calls + 1


async def test_the_refresh_action_returns_with_the_new_figures_in_place(hass, portfolio_api):
    """It waits for the refresh itself: once the call returns, the sensors
    show what Bitpanda just answered."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = [
        {**portfolio_api.return_value[0], "currency_balance": {"value": "300.00"}},
        portfolio_api.return_value[1],
    ]
    await hass.services.async_call(DOMAIN, "refresh", blocking=True)
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 310.0


def _portfolio_down(*, equivalent_currency_id=None):
    """/portfolio answering HTTP 503. A side effect raising a fresh error at
    each call, for the reason _no_connection gives."""
    raise BitpandaApiError(
        "HTTP 503 from /portfolio", kind="http_status", path="/portfolio", status=503
    )


async def test_a_failed_refresh_fails_the_action_and_names_the_service(
    hass, portfolio_api, price_api
):
    """The Portfolio's refresh fails, the Price Tracker's works: the call
    fails with a translated error naming the Portfolio, whose sensors keep
    their last figures -- one failure confirms no outage; the prices were
    refreshed all the same."""
    ticker, _ = price_api
    portfolio = _portfolio_entry(hass)
    _price_entry(hass, [], price_group("crypto", BTC))
    # The first setup of the domain sets up both entries.
    await _setup(hass, portfolio)
    ticker_calls = ticker.call_count
    portfolio_api.side_effect = _portfolio_down

    with pytest.raises(HomeAssistantError) as excinfo:
        await _refresh(hass)

    assert not isinstance(excinfo.value, ServiceValidationError)
    assert (excinfo.value.translation_key, excinfo.value.translation_placeholders) == (
        "refresh_failed", {"services": "Bitpanda Portfolio"}
    )
    assert _value(hass, "sensor.bitpanda_portfolio_total") == 210.0
    assert ticker.call_count == ticker_calls + 1
    assert _value(hass, "sensor.bitpanda_bitcoin_btc_price_tracker_eur") == 100.0


async def test_an_empty_portfolio_held_back_fails_the_refresh_action(hass, portfolio_api):
    """An empty answer awaiting confirmation is a failed update, so the call
    fails too -- while the Portfolio's sensors keep their values."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.return_value = []
    with pytest.raises(HomeAssistantError) as excinfo:
        await _refresh(hass)
    assert excinfo.value.translation_key == "refresh_failed"


async def test_continue_on_error_carries_a_script_past_a_failed_refresh(hass, portfolio_api):
    """What the README tells automation authors: a failed refresh stops the
    script at that step, unless the step says `continue_on_error: true`."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    portfolio_api.side_effect = _portfolio_down
    after = async_capture_events(hass, "bitpanda_test_after_refresh")
    step_after = {"event": "bitpanda_test_after_refresh"}
    assert await async_setup_component(
        hass,
        "script",
        {
            "script": {
                "stops": {"sequence": [{"action": "bitpanda.refresh"}, step_after]},
                "goes_on": {
                    "sequence": [
                        {"action": "bitpanda.refresh", "continue_on_error": True},
                        step_after,
                    ]
                },
            }
        },
    )
    # Each run a cooldown apart, so that both really refresh -- and fail.
    clock = iter((1000.0, 2000.0))
    with patch("custom_components.bitpanda.monotonic", lambda: next(clock)):
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call("script", "stops", blocking=True)
        await hass.async_block_till_done()
        assert after == []

        await hass.services.async_call("script", "goes_on", blocking=True)
        await hass.async_block_till_done()
    assert len(after) == 1


async def test_the_refresh_action_outlives_every_entry(hass, portfolio_api, price_api):
    """Registered with the integration, not with an entry: unloading both
    entries leaves it in place, and a call then says why it does nothing."""
    portfolio, tracker = _portfolio_entry(hass), _price_entry(hass, [], price_group("crypto", BTC))
    # The first setup of a domain sets up every entry it has (Home
    # Assistant's setup.py: "Setting up the component will set up all its
    # config entries"), the Price Tracker included.
    await _setup(hass, portfolio)
    assert tracker.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(portfolio.entry_id)
    assert await hass.config_entries.async_unload(tracker.entry_id)
    assert hass.services.has_service(DOMAIN, "refresh")
    with pytest.raises(ServiceValidationError) as excinfo:
        await _refresh(hass)
    assert excinfo.value.translation_key == "nothing_to_refresh"


async def test_the_refresh_action_exists_while_setup_is_retried(hass, portfolio_api):
    """So an automation that uses it validates even then."""
    portfolio_api.side_effect = BitpandaApiError("HTTP 503 from /portfolio")
    entry = _portfolio_entry(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert hass.services.has_service(DOMAIN, "refresh")
    with pytest.raises(ServiceValidationError) as excinfo:
        await _refresh(hass)
    assert excinfo.value.translation_key == "nothing_to_refresh"


# --- Groups follow the entry's language at setup ------------------------------------
#
# Each entry's own language setting (Configure, language.py), English by
# default; Home Assistant's system language plays no part.


async def test_a_price_tracker_group_is_retitled_to_the_entrys_language_at_setup(
    hass, price_api
):
    ticker, _ = price_api
    entry = _price_entry(
        hass, [],
        price_group("crypto", BTC, title="Cryptocurrencies"),
        price_group("metal", GOLD, title="Meine Coins"),
        language="de",
    )
    await _setup(hass, entry)
    assert _group(entry, "crypto").title == "Kryptowährungen"
    assert _group(entry, "metal").title == "Meine Coins"
    # One ticker call per tracked asset (BTC, GOLD): retitled before the
    # update listener exists, so no reload followed with a second round.
    assert ticker.call_count == 2


async def test_groups_are_english_by_default_whatever_language_home_assistant_runs_in(
    hass, price_api, portfolio_api
):
    """Groups titled in the system language before the language became a
    setting of its own become English on the first start with it -- unless
    the entry's language says otherwise; the user's own titles stay."""
    hass.config.language = "de"
    tracker = _price_entry(
        hass, [],
        price_group("crypto", BTC, title="Kryptowährungen"),
        price_group("metal", GOLD, title="Meine Metalle"),
    )
    portfolio = _portfolio_entry(hass, wallet_group("crypto", title="Kryptowährungen"))
    # The first setup of the domain sets up both entries.
    await _setup(hass, tracker)
    assert portfolio.state is ConfigEntryState.LOADED
    assert _group(tracker, "crypto").title == "Cryptocurrencies"
    assert _group(tracker, "metal").title == "Meine Metalle"
    assert _group(portfolio, "crypto").title == "Cryptocurrencies"


async def test_a_price_tracker_group_already_in_the_entrys_language_is_untouched(
    hass, price_api
):
    ticker, _ = price_api
    entry = _price_entry(
        hass, [], price_group("crypto", BTC, title="Kryptowährungen"), language="de"
    )
    group_before = _group(entry, "crypto")

    with patch.object(
        hass.config_entries, "async_update_subentry",
        wraps=hass.config_entries.async_update_subentry,
    ) as spy:
        await _setup(hass, entry)

    spy.assert_not_called()
    assert _group(entry, "crypto") is group_before
    assert _group(entry, "crypto").title == "Kryptowährungen"
    assert ticker.call_count == 1


async def test_a_portfolio_wallet_group_is_retitled_to_the_entrys_language_at_setup(
    hass, portfolio_api
):
    entry = _portfolio_entry(
        hass, wallet_group("crypto", title="Cryptocurrencies"), language="de"
    )
    await _setup(hass, entry)
    assert _group(entry, "crypto").title == "Kryptowährungen"
    assert portfolio_api.call_count == 1


async def test_a_portfolio_wallet_group_already_in_the_entrys_language_is_untouched(
    hass, portfolio_api
):
    entry = _portfolio_entry(
        hass, wallet_group("crypto", title="Kryptowährungen"), language="de"
    )
    group_before = _group(entry, "crypto")

    with patch.object(
        hass.config_entries, "async_update_subentry",
        wraps=hass.config_entries.async_update_subentry,
    ) as spy:
        await _setup(hass, entry)

    spy.assert_not_called()
    assert _group(entry, "crypto") is group_before
    assert _group(entry, "crypto").title == "Kryptowährungen"
    assert portfolio_api.call_count == 1


async def _configure(hass, entry, user_input: dict) -> None:
    """Save `user_input` through the entry's Configure dialog."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input)
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()


async def test_switching_the_price_trackers_language_retitles_its_groups(hass, price_api):
    """From German to English under Configure: saving reloads the entry, and
    the reload's setup retitles the German default titles -- before its
    update listener exists again, so the retitle adds no second reload. The
    system language, German here too, plays no part."""
    ticker, _ = price_api
    hass.config.language = "de"
    entry = _price_entry(
        hass, [],
        price_group("crypto", BTC, title="Cryptocurrencies"),
        price_group("metal", GOLD, title="Meine Metalle"),
        language="de",
    )
    await _setup(hass, entry)
    assert _group(entry, "crypto").title == "Kryptowährungen"
    calls = ticker.call_count

    await _configure(
        hass, entry, {"currencies": {"extra_currencies": []}, "language": {"language": "en"}}
    )

    assert entry.state is ConfigEntryState.LOADED
    assert entry.options["language"] == "en"
    assert _group(entry, "crypto").title == "Cryptocurrencies"
    assert _group(entry, "metal").title == "Meine Metalle"
    # One reload: one more round of first-refresh calls (BTC, GOLD).
    assert ticker.call_count == calls + 2


async def test_switching_the_portfolios_language_retitles_its_wallet_groups(
    hass, portfolio_api
):
    """The group the wallet manager created in German becomes English with
    the one reload that saving the option causes."""
    entry = _portfolio_entry(hass, language="de")
    await _setup(hass, entry)
    assert _group(entry, "crypto").title == "Kryptowährungen"
    calls = portfolio_api.call_count

    await _configure(
        hass, entry,
        {"language": {"language": "en"}, "notifications": {"notify_new_wallets": True}},
    )

    assert entry.state is ConfigEntryState.LOADED
    assert dict(entry.options) == {
        "language": "en", "notify_new_wallets": True, "notify_staking_rewards": False,
    }
    assert _group(entry, "crypto").title == "Cryptocurrencies"
    assert portfolio_api.call_count == calls + 1


# --- Deleting a device from its device page ------------------------------------------


def _identifier(entry, kind: str, asset: dict | None = None) -> str:
    """A device identifier of `entry`: `{entry_id}_{kind}[_{asset id}]`."""
    return f"{entry.entry_id}_{kind}" + (f"_{asset['id']}" if asset else "")


def _own_device(hass, entry, kind: str, asset: dict | None = None) -> dr.DeviceEntry:
    return find_entry_device(dr.async_get(hass), entry.entry_id, _identifier(entry, kind, asset))


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
    assert er.async_get(hass).async_get("sensor.bitpanda_solana_sol_price_tracker_eur") is None
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
    assert er.async_get(hass).async_get("sensor.bitpanda_gold_xau_price_tracker_eur") is None
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
    with pytest.raises(HomeAssistantError) as exc_info:
        await async_remove_config_entry_device(
            hass, entry, _own_device(hass, entry, "portfolio")
        )
    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == "portfolio_device_not_removable"
    assert exc_info.value.translation_placeholders is None


async def test_the_wallet_of_a_held_asset_cannot_be_deleted(hass, portfolio_api):
    """It would come straight back with the next refresh."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    calls = portfolio_api.call_count

    with pytest.raises(HomeAssistantError) as exc_info:
        await async_remove_config_entry_device(
            hass, entry, _own_device(hass, entry, "wallet", VSN)
        )
    await hass.async_block_till_done()
    assert portfolio_api.call_count == calls
    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == "held_wallet_not_removable"
    assert exc_info.value.translation_placeholders == {"asset": "Vision (VSN)"}


async def test_a_held_etf_is_named_with_its_isin(hass, portfolio_api):
    """A stock's, ETF's or ETC's label carries its ISIN, and so do its
    wallet device's name and its entity IDs. The refusal to delete its
    wallet names the asset itself, without the device's " Wallet"."""
    top500 = _fixture("SXR8", "security")
    position, cash = portfolio_api.return_value
    portfolio_api.return_value = [position, {**position, "asset_id": top500["id"]}, cash]
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    wallet = _own_device(hass, entry, "wallet", top500)
    assert wallet.name == "Top 500 US Stocks X Acc (SXR8 / IE00B5BMR087) Wallet"
    assert _value(
        hass, "sensor.bitpanda_top_500_us_stocks_x_acc_sxr8_ie00b5bmr087_wallet_available"
    ) == 50.0

    with pytest.raises(HomeAssistantError) as exc_info:
        await async_remove_config_entry_device(hass, entry, wallet)
    assert exc_info.value.translation_placeholders == {
        "asset": "Top 500 US Stocks X Acc (SXR8 / IE00B5BMR087)"
    }


async def test_a_holding_whose_balances_cannot_be_read_is_still_held(hass, portfolio_api):
    """BTC's balance never parses, so it has no record in data.assets: the
    error falls back to naming the wallet from its device instead of
    naming.asset_display_label."""
    portfolio_api.return_value = [
        *portfolio_api.return_value,
        {"asset_id": BTC["id"], "balance": {"value": "unreadable"}},
    ]
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    wallet = _add_device(hass, entry, "Bitcoin (BTC) Wallet", "wallet", BTC)

    with pytest.raises(HomeAssistantError) as exc_info:
        await async_remove_config_entry_device(hass, entry, wallet)
    assert exc_info.value.translation_key == "held_wallet_not_removable"
    assert exc_info.value.translation_placeholders == {"asset": "Bitcoin (BTC) Wallet"}


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
        with pytest.raises(HomeAssistantError):
            await async_remove_config_entry_device(hass, entry, portfolio)
        assert await async_remove_config_entry_device(hass, entry, wallet)
    reload.assert_not_called()


async def test_a_held_wallet_without_a_record_is_named_as_the_user_named_it(hass, portfolio_api):
    """BTC's balance never parses, so the refusal names the wallet from its
    device -- by the name the user gave it, where there is one."""
    portfolio_api.return_value = [
        *portfolio_api.return_value,
        {"asset_id": BTC["id"], "balance": {"value": "unreadable"}},
    ]
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    wallet = _add_device(hass, entry, "Bitcoin (BTC) Wallet", "wallet", BTC)
    wallet = dr.async_get(hass).async_update_device(wallet.id, name_by_user="My bitcoins")

    with pytest.raises(HomeAssistantError) as exc_info:
        await async_remove_config_entry_device(hass, entry, wallet)
    assert exc_info.value.translation_key == "held_wallet_not_removable"
    assert exc_info.value.translation_placeholders == {"asset": "My bitcoins"}


# Identifiers no device of this integration carries today, merged into one
# that does: a device is judged by every identifier it carries, and with this
# many beside the one that matters, a check that read one arbitrary
# identifier would all but never read that one.
_EXTRA_IDENTIFIERS = frozenset(f"legacy_{number}" for number in range(15))


def _with_extra_identifiers(hass, device: dr.DeviceEntry) -> dr.DeviceEntry:
    return dr.async_get(hass).async_update_device(
        device.id,
        new_identifiers={*device.identifiers, *((DOMAIN, extra) for extra in _EXTRA_IDENTIFIERS)},
    )


async def test_a_device_carrying_the_portfolio_identifier_among_others_is_refused(
    hass, portfolio_api
):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    device = _with_extra_identifiers(hass, _own_device(hass, entry, "portfolio"))

    with pytest.raises(HomeAssistantError) as exc_info:
        await async_remove_config_entry_device(hass, entry, device)
    assert exc_info.value.translation_key == "portfolio_device_not_removable"


async def test_a_device_carrying_a_held_wallet_identifier_among_others_is_refused(
    hass, portfolio_api
):
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    calls = portfolio_api.call_count
    device = _with_extra_identifiers(hass, _own_device(hass, entry, "wallet", VSN))

    with pytest.raises(HomeAssistantError) as exc_info:
        await async_remove_config_entry_device(hass, entry, device)
    await hass.async_block_till_done()
    assert exc_info.value.translation_key == "held_wallet_not_removable"
    assert exc_info.value.translation_placeholders == {"asset": "Vision (VSN)"}
    assert portfolio_api.call_count == calls


async def test_a_price_device_carrying_other_identifiers_still_takes_its_asset_along(
    hass, price_api
):
    entry = _price_entry(hass, [], price_group("crypto", BTC, SOL))
    await _setup(hass, entry)
    device = _with_extra_identifiers(hass, _own_device(hass, entry, "price", SOL))

    assert await async_remove_config_entry_device(hass, entry, device)
    await hass.async_block_till_done()

    assert list(_group(entry, "crypto").data["assets"]) == [BTC["id"]]
    assert er.async_get(hass).async_get("sensor.bitpanda_solana_sol_price_tracker_eur") is None


async def test_the_device_page_deletes_the_last_price_device_of_a_group(
    hass, price_api, hass_ws_client
):
    """The hook removes the emptied group, and with it the device, before
    Home Assistant's own handler goes on to remove that device: the command
    still succeeds."""
    ticker, _ = price_api
    entry = _price_entry(hass, [], price_group("crypto", BTC), price_group("metal", GOLD))
    await _setup(hass, entry)
    device = _own_device(hass, entry, "price", GOLD)

    response = await _remove_through_the_device_page(hass, hass_ws_client, entry, device)
    await hass.async_block_till_done()

    assert response["success"]
    assert [sub.unique_id for sub in entry.subentries.values()] == ["crypto"]
    assert dr.async_get(hass).async_get(device.id) is None
    assert er.async_get(hass).async_get("sensor.bitpanda_gold_xau_price_tracker_eur") is None
    assert ticker.call_count == 3


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
    assert er.async_get(hass).async_get("sensor.bitpanda_solana_sol_price_tracker_eur") is None
    assert ticker.call_count == 3


# What the device page's dialog shows for each refusal: the `message` of the
# websocket error, in the entry's language (language.py) -- chosen at setup
# or under Configure, English for an entry without one, whatever language
# Home Assistant runs in. The trailing "." of strings.json stays: the
# message is the dialog's whole text, of several sentences, so the last one
# must not look cut off (Home Assistant would drop it,
# translation.async_get_exception_message).
_REFUSALS = {
    "en": {
        "portfolio": (
            "The Portfolio device is part of the Bitpanda Portfolio service and "
            'cannot be deleted on its own. To remove it, delete the "Bitpanda '
            'Portfolio" entry on the Bitpanda integration page (⋮ → "Delete").'
        ),
        "wallet": (
            "While you hold Vision (VSN), this wallet cannot be deleted – it would be "
            "created again at the next refresh. Once you no longer hold Vision (VSN), "
            "it is removed automatically."
        ),
    },
    "de": {
        "portfolio": (
            "Das Gerät „Portfolio“ gehört zum Dienst Bitpanda Portfolio und lässt sich "
            "nicht einzeln löschen. Um es zu entfernen, lösche den Eintrag „Bitpanda "
            "Portfolio“ auf der Bitpanda-Integrationsseite (⋮ → „Löschen“)."
        ),
        "wallet": (
            "Solange du Vision (VSN) besitzt, lässt sich dieses Wallet nicht löschen – es "
            "würde beim nächsten Abruf sofort wieder angelegt. Sobald du Vision (VSN) nicht "
            "mehr besitzt, wird es automatisch entfernt."
        ),
    },
}


@pytest.mark.parametrize("language", ["en", "de"])
async def test_the_device_page_refuses_to_delete_the_portfolio_device(
    hass, portfolio_api, hass_ws_client, language
):
    """In the entry's language: the dialog shows the message as it arrives,
    and Home Assistant itself would render it in English only. Home
    Assistant runs in English here, so German is loaded only when asked for."""
    entry = _portfolio_entry(hass, language=language)
    await _setup(hass, entry)
    device = _own_device(hass, entry, "portfolio")

    response = await _remove_through_the_device_page(hass, hass_ws_client, entry, device)

    assert not response["success"]
    assert response["error"]["message"] == _REFUSALS[language]["portfolio"]
    assert response["error"]["translation_domain"] == DOMAIN
    assert response["error"]["translation_key"] == "portfolio_device_not_removable"
    assert response["error"]["translation_placeholders"] is None
    assert dr.async_get(hass).async_get(device.id) is not None


@pytest.mark.parametrize("language", ["en", "de"])
async def test_the_device_page_refuses_to_delete_a_held_wallet(
    hass, portfolio_api, hass_ws_client, language
):
    entry = _portfolio_entry(hass, language=language)
    await _setup(hass, entry)
    wallet = _own_device(hass, entry, "wallet", VSN)

    response = await _remove_through_the_device_page(hass, hass_ws_client, entry, wallet)

    assert not response["success"]
    assert response["error"]["message"] == _REFUSALS[language]["wallet"]
    assert response["error"]["translation_domain"] == DOMAIN
    assert response["error"]["translation_key"] == "held_wallet_not_removable"
    assert response["error"]["translation_placeholders"] == {"asset": "Vision (VSN)"}
    assert dr.async_get(hass).async_get(wallet.id) is not None


async def test_a_refusal_is_english_by_default_whatever_language_home_assistant_runs_in(
    hass, portfolio_api, hass_ws_client
):
    hass.config.language = "de"
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    device = _own_device(hass, entry, "portfolio")

    response = await _remove_through_the_device_page(hass, hass_ws_client, entry, device)

    assert not response["success"]
    assert response["error"]["message"] == _REFUSALS["en"]["portfolio"]
    assert response["error"]["translation_key"] == "portfolio_device_not_removable"


async def test_a_refusal_follows_a_language_switched_under_configure(
    hass, portfolio_api, hass_ws_client
):
    """The language is read when the refusal is written, so the one chosen
    last applies -- here after the reload that saving it causes."""
    entry = _portfolio_entry(hass)
    await _setup(hass, entry)
    await _configure(
        hass, entry,
        {"language": {"language": "de"}, "notifications": {"notify_new_wallets": True}},
    )
    device = _own_device(hass, entry, "portfolio")

    response = await _remove_through_the_device_page(hass, hass_ws_client, entry, device)

    assert not response["success"]
    assert response["error"]["message"] == _REFUSALS["de"]["portfolio"]
    assert response["error"]["translation_domain"] == DOMAIN
    assert response["error"]["translation_key"] == "portfolio_device_not_removable"


async def test_deleting_a_sold_wallet_in_a_group_removes_the_emptied_group(
    hass, portfolio_api, hass_ws_client, freezer
):
    """The hook (__init__.py) only schedules a reload; the emptied group
    disappears at that reload's first reconcile, but only if the reconcile
    runs after the websocket handler has removed the device and its sensors.
    A real /portfolio request suspends there, so this mock does too --
    without the yield, the reconcile would run first and the group would
    only go on the refresh after this one."""
    entry = _portfolio_entry(hass)
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
    await _setup(hass, entry)
    assert [sub.unique_id for sub in entry.subentries.values()] == ["crypto", "metal"]
    wallet = _own_device(hass, entry, "wallet", GOLD)

    sold = [e for e in portfolio_api.return_value if e.get("asset_id") != GOLD["id"]]

    async def _sold_after_a_yield(*_args, **_kwargs):
        await asyncio.sleep(0)
        return sold

    portfolio_api.side_effect = _sold_after_a_yield
    await _next_refresh(hass, freezer)
    # One miss only (WALLET_REMOVAL_MISSES is 3): the wallet and its group
    # are untouched, so the device page below still finds them.
    assert [sub.unique_id for sub in entry.subentries.values()] == ["crypto", "metal"]

    response = await _remove_through_the_device_page(hass, hass_ws_client, entry, wallet)
    await hass.async_block_till_done()

    assert response["success"]
    assert dr.async_get(hass).async_get(wallet.id) is None
    assert [sub.unique_id for sub in entry.subentries.values()] == ["crypto"]
