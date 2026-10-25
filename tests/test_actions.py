"""The Portfolio's actions with response data (services.py): the portfolio,
its value history and the staking payouts, answered from what the
Portfolio holds -- never a request to Bitpanda. End to end, Bitpanda mocked
as in tests/test_init.py."""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaApiError, BitpandaAuthError
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.devices import find_entry_device
from custom_components.bitpanda.naming import total_unique_id

from tests.conftest import load_fixture

_CLIENT = "custom_components.bitpanda.api.BitpandaApiClient."
_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"
_UNLISTED = "0f0f0f0f-0f0f-4f0f-8f0f-0f0f0f0f0f0f"


def _record(symbol: str) -> dict:
    return next(a for a in load_fixture("assets-sample.json") if a["symbol"] == symbol)


VSN, BTC, ADA = _record("VSN"), _record("BTC"), _record("ADA")
BCPEUR = next(a for a in load_fixture("assets-sample.json") if a.get("group") == "fiat_earn")


def _money(value: str) -> dict:
    return {"value": value}


# Vision, three quarters staked; Bitcoin; Cash Plus and cash: 760 in all.
_ANSWER = [
    {
        "asset_id": VSN["id"], "balance": _money("100.00000000"),
        "available_balance": _money("25.00000000"), "currency_balance": _money("200.00"),
        "invested_amount": _money("150.00"), "average_buy_price": _money("1.50"),
        "total_return": _money("50.00"), "total_return_percent": "33.33",
    },
    {
        "asset_id": BTC["id"], "balance": _money("0.01000000"),
        "available_balance": _money("0.01000000"), "currency_balance": _money("500.00"),
        "invested_amount": _money("400.00"), "average_buy_price": _money("40000.00"),
        "total_return": _money("100.00"), "total_return_percent": "25.00",
    },
    {
        "asset_id": BCPEUR["id"], "balance": _money("50.00000000"),
        "available_balance": _money("50.00000000"), "currency_balance": _money("50.00"),
    },
    {"currency_id": _EUR_ID, "balance": _money("10.00")},
]
_POINTS = [
    {"time": "2026-10-22T10:00:00Z", "value": _money("750.00")},
    {"time": "2026-10-22T11:00:00Z", "value": _money("760.00")},
]


def _reward(asset: dict, credited_at: str, gross: str, fee: str) -> dict:
    return {
        "operation_id": f"op-{credited_at}-{asset['id']}",
        "operation_type": "reward",
        "transactions": [{
            "asset_id": asset["id"], "wallet_owner": "staking-service",
            "asset_amount": {"value": gross}, "fee_amount": {"value": fee},
            "credited_at": credited_at,
        }],
    }


# Vision's two payouts -- net 9.6 and 10 --, and Cardano's, an asset not held.
_PAYOUTS = [
    _reward(ADA, "2026-09-20T08:00:00Z", "1.00000000", "0.20000000"),
    _reward(VSN, "2026-09-15T16:20:00Z", "12.50000000", "2.50000000"),
    _reward(VSN, "2026-09-08T16:20:00Z", "12.00000000", "2.40000000"),
]


def _lookup(**kwargs):
    return [a for a in load_fixture("assets-sample.json") if a["id"] == kwargs.get("asset_id")]


_PRICES = {VSN["id"]: "2.00000000", BTC["id"]: "50000.00000000"}


async def _ticker(asset_id):
    if asset_id not in _PRICES:
        raise BitpandaApiError("no price", kind="http_status", path="/tickers")
    return {"asset_id": asset_id, "price": _PRICES[asset_id]}


@pytest.fixture
def api():
    """Bitpanda as the Portfolio asks it; tests change the answers."""
    with patch(
        f"{_CLIENT}async_get_portfolio", AsyncMock(return_value=list(_ANSWER))
    ) as portfolio, patch(
        f"{_CLIENT}async_get_portfolio_history",
        AsyncMock(return_value={"return_percentage": 1.5, "datapoints": _POINTS}),
    ) as history, patch(
        f"{_CLIENT}async_get_earn_configs",
        AsyncMock(return_value=[
            {"asset_id": VSN["id"], "annual_percentage_rate": 0.0544, "enabled": True}
        ]),
    ), patch(f"{_CLIENT}async_get_operations", AsyncMock(return_value=_PAYOUTS)), patch(
        f"{_CLIENT}async_get_assets", AsyncMock(side_effect=_lookup)
    ), patch(f"{_CLIENT}async_get_ticker", AsyncMock(side_effect=_ticker)) as ticker:
        yield {"portfolio": portfolio, "history": history, "ticker": ticker}


def _portfolio_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR",
              "currency_id": _EUR_ID},
    )
    entry.add_to_hass(hass)
    return entry


async def _setup(hass, entry=None) -> MockConfigEntry:
    entry = entry or _portfolio_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def _call(hass, action: str, **data) -> dict:
    return await hass.services.async_call(
        DOMAIN, action, data, blocking=True, return_response=True
    )


def _device_id(hass, entry, asset: dict) -> str:
    return find_entry_device(
        dr.async_get(hass), entry.entry_id, f"{entry.entry_id}_wallet_{asset['id']}"
    ).id


# --- bitpanda.get_portfolio -----------------------------------------------------------


async def test_get_portfolio_answers_with_every_figure_and_wallet(hass, api):
    """Rounded as the sensors' attributes; the wallets largest first."""
    entry = await _setup(hass)
    response = await _call(hass, "get_portfolio")
    day = {"percent": 1.5, "amount": round(760 * 1.5 / 101.5, 2)}
    vsn_net = 19.6
    assert response == {
        "currency": "EUR",
        "total_value": 760.0,
        "cash": 10.0,
        "cash_plus": 50.0,
        "invested": 550.0,
        "total_return": 150.0,
        "total_return_percent": 27.27,
        "returns": {timeframe: day for timeframe in ("day", "week", "month", "six_month", "year")},
        "wallets": [
            {
                "asset_id": BTC["id"], "symbol": "BTC", "name": "Bitcoin", "category": "crypto",
                "device_id": _device_id(hass, entry, BTC),
                "units": 0.01, "staked_units": 0.0, "value": 500.0, "price": 50000.0,
                "invested_amount": 400.0, "total_return": 100.0, "total_return_percent": 25.0,
                "change_24h_pct": None, "return_24h": None,
                "portfolio_share_percent": 65.79,
                "apr_percent": None, "rewards_net": None, "rewards_net_value": None,
            },
            {
                "asset_id": VSN["id"], "symbol": "VSN", "name": "Vision",
                "category": "crypto", "device_id": _device_id(hass, entry, VSN),
                "units": 100.0, "staked_units": 75.0, "value": 200.0, "price": 2.0,
                "invested_amount": 150.0, "total_return": 50.0, "total_return_percent": 33.33,
                "change_24h_pct": None, "return_24h": None,
                "portfolio_share_percent": 26.32,
                "apr_percent": 5.44, "rewards_net": vsn_net, "rewards_net_value": 39.2,
            },
        ],
    }


async def test_get_portfolio_asks_bitpanda_nothing(hass, api):
    await _setup(hass)
    calls = {name: mock.call_count for name, mock in api.items()}
    await _call(hass, "get_portfolio")
    assert {name: mock.call_count for name, mock in api.items()} == calls


async def test_a_wallets_24h_figures_come_from_its_balance_totals_reference(hass, api):
    """The reference the lookup found a day ago -- none for a wallet whose
    Balance (total) is disabled, which is not looked up."""
    entry = _portfolio_entry(hass)
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, total_unique_id(entry.entry_id, BTC["id"]), config_entry=entry,
        suggested_object_id="bitpanda_bitcoin_btc_wallet_total",
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    with patch(
        "custom_components.bitpanda.portfolio_sensor.async_wallet_prices_24h_ago",
        AsyncMock(side_effect=lambda hass, entity_ids, now: {entity_id: 1.6 for entity_id in entity_ids}),
    ):
        await _setup(hass, entry)
        await entry.runtime_data.day_ago.async_look_up()
    wallets = {w["symbol"]: w for w in (await _call(hass, "get_portfolio"))["wallets"]}
    assert (wallets["VSN"]["change_24h_pct"], wallets["VSN"]["return_24h"]) == (25.0, 40.0)
    assert (wallets["BTC"]["change_24h_pct"], wallets["BTC"]["return_24h"]) == (None, None)


async def test_without_a_price_a_wallets_price_and_what_needs_it_are_null(hass, api):
    _PRICES.pop(VSN["id"])
    try:
        await _setup(hass)
        [_, vsn] = (await _call(hass, "get_portfolio"))["wallets"]
    finally:
        _PRICES[VSN["id"]] = "2.00000000"
    assert (vsn["price"], vsn["change_24h_pct"], vsn["return_24h"], vsn["rewards_net_value"]) == (
        None, None, None, None
    )
    assert vsn["rewards_net"] == 19.6


async def test_a_position_without_a_wallet_counts_in_invested_but_is_not_listed(hass, api):
    """An asset Bitpanda's catalogue does not list: a position, no wallet."""
    api["portfolio"].return_value = [
        *_ANSWER,
        {
            "asset_id": _UNLISTED, "balance": _money("1.00000000"),
            "available_balance": _money("1.00000000"), "currency_balance": _money("40.00"),
            "invested_amount": _money("30.00"),
        },
    ]
    await _setup(hass)
    response = await _call(hass, "get_portfolio")
    assert (response["invested"], response["total_value"]) == (580.0, 800.0)
    assert [wallet["symbol"] for wallet in response["wallets"]] == ["BTC", "VSN"]


async def test_after_an_empty_answer_the_figures_that_wait_are_null(hass, api):
    """Never 0 for a figure whose entry vanished and waits: null."""
    entry = await _setup(hass)
    api["portfolio"].return_value = []
    await entry.runtime_data.portfolio.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)
    response = await _call(hass, "get_portfolio")
    assert {key: response[key] for key in ("total_value", "cash", "cash_plus", "invested")} == {
        "total_value": None, "cash": None, "cash_plus": None, "invested": None,
    }
    assert response["returns"]["day"] == {"percent": 1.5, "amount": None}
    assert response["wallets"] == []


async def test_a_failed_timeframe_reads_null(hass, api):
    async def _history(*, timeframe, equivalent_currency_id):
        if timeframe == "YEAR":
            raise BitpandaApiError("down", kind="http_status", path="/portfolio-history")
        return {"return_percentage": 1.5, "datapoints": _POINTS}

    api["history"].side_effect = _history
    await _setup(hass)
    returns = (await _call(hass, "get_portfolio"))["returns"]
    assert returns["year"] == {"percent": None, "amount": None}
    assert returns["day"]["percent"] == 1.5


async def test_the_actions_run_on_the_event_loop(hass, api):
    """Callbacks, as Home Assistant sees them: run on the loop, never in an
    executor thread, so that an unload or a reconcile cannot come in
    between. A callback wrapped around a partial is not one -- Home
    Assistant looks at the function inside."""
    from homeassistant.core import HassJobType
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, DOMAIN, {})
    services = hass.services.async_services_internal()[DOMAIN]
    for name in ("get_portfolio", "get_portfolio_history", "get_staking_rewards"):
        assert services[name].job.job_type is HassJobType.Callback, name


async def test_without_a_portfolio_the_actions_are_refused(hass, api):
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, DOMAIN, {})
    for action in ("get_portfolio", "get_staking_rewards"):
        with pytest.raises(ServiceValidationError) as excinfo:
            await _call(hass, action)
        assert excinfo.value.translation_key == "no_portfolio"
    with pytest.raises(ServiceValidationError):
        await _call(hass, "get_portfolio_history", timeframe="day")


async def test_while_the_portfolios_data_is_unavailable_the_actions_fail(hass, api):
    """A rejected key: the sensors are unavailable, and so is what the
    actions would answer -- but the payouts, which come from the store."""
    entry = await _setup(hass)
    api["portfolio"].side_effect = BitpandaAuthError("rejected")
    await entry.runtime_data.portfolio.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)
    for action, data in (("get_portfolio", {}), ("get_portfolio_history", {"timeframe": "day"})):
        with pytest.raises(HomeAssistantError) as excinfo:
            await _call(hass, action, **data)
        assert not isinstance(excinfo.value, ServiceValidationError)
        assert excinfo.value.translation_key == "portfolio_unavailable"
    assert len((await _call(hass, "get_staking_rewards"))["payouts"]) == 3


# --- bitpanda.get_portfolio_history ------------------------------------------------------


async def test_get_portfolio_history_answers_with_the_cards_series(hass, api):
    await _setup(hass)
    assert await _call(hass, "get_portfolio_history", timeframe="week") == {
        "currency": "EUR",
        "timeframe": "week",
        "points": [
            {"time": "2026-10-22T10:00:00+00:00", "value": 750.0},
            {"time": "2026-10-22T11:00:00+00:00", "value": 760.0},
        ],
    }


async def test_get_portfolio_history_is_empty_while_the_history_is_unavailable(hass, api):
    entry = await _setup(hass)
    api["history"].side_effect = BitpandaAuthError("rejected")
    await entry.runtime_data.history.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert (await _call(hass, "get_portfolio_history", timeframe="day"))["points"] == []


async def test_get_portfolio_history_refuses_an_unknown_timeframe(hass, api):
    await _setup(hass)
    with pytest.raises(vol.Invalid):
        await _call(hass, "get_portfolio_history", timeframe="decade")
    with pytest.raises(vol.Invalid):
        await _call(hass, "get_portfolio_history")


# --- bitpanda.get_staking_rewards ----------------------------------------------------------


async def test_get_staking_rewards_lists_every_payout_oldest_first(hass, api):
    entry = await _setup(hass)
    response = await _call(hass, "get_staking_rewards")
    assert response == {
        "updated_at": entry.runtime_data.rewards.last_update_success_time.isoformat(),
        "payouts": [
            {"asset_id": VSN["id"], "symbol": "VSN", "credited_at": "2026-09-08T16:20:00Z",
             "gross": 12.0, "fee": 2.4, "net": 9.6},
            {"asset_id": VSN["id"], "symbol": "VSN", "credited_at": "2026-09-15T16:20:00Z",
             "gross": 12.5, "fee": 2.5, "net": 10.0},
            # Not held: no record to name it by.
            {"asset_id": ADA["id"], "symbol": None, "credited_at": "2026-09-20T08:00:00Z",
             "gross": 1.0, "fee": 0.2, "net": 0.8},
        ],
    }
    assert response["updated_at"].endswith("+00:00")


async def test_after_a_restart_whose_first_read_fails_the_payouts_name_their_last_read(
    hass, hass_storage, api
):
    """The payouts come from the store, and so does the time they were read
    last -- not null because this run has not read them yet."""
    entry = _portfolio_entry(hass)
    key = f"bitpanda.portfolio.{entry.entry_id}"
    hass_storage[key] = {"version": 1, "key": key, "data": {"operations": {
        "kinds": ["staking"],
        "full_read_at": "2026-10-20T08:00:00+00:00",
        "read_at": "2026-10-22T09:00:00+00:00",
        "anchor": "2026-09-15T16:20:00Z",
        "recent_ids": {},
        "staking": {VSN["id"]: {
            "gross": 12.5, "fee": 2.5, "net": 10.0, "count": 1, "last_at": "2026-09-15T16:20:00Z",
            "payouts": [["2026-09-15T16:20:00Z", 12.5, 2.5, 10.0]],
        }},
    }}}
    with patch(
        f"{_CLIENT}async_get_operations",
        AsyncMock(side_effect=BitpandaApiError("down", kind="http_status", path="/operations")),
    ):
        await _setup(hass, entry)
    assert entry.runtime_data.rewards.last_update_success_time is None
    response = await _call(hass, "get_staking_rewards")
    assert response["updated_at"] == "2026-10-22T09:00:00+00:00"
    assert [payout["credited_at"] for payout in response["payouts"]] == ["2026-09-15T16:20:00Z"]


async def test_get_staking_rewards_filters_by_time_in_home_assistants_time_zone(hass, api):
    """`start` counts, `end` does not; both read in Home Assistant's time
    zone -- here US/Pacific, UTC-7 in September."""
    await hass.config.async_set_time_zone("America/Los_Angeles")
    await _setup(hass)
    response = await _call(
        hass, "get_staking_rewards", start="2026-09-08 09:20:00", end="2026-09-15 09:20:00"
    )
    assert [payout["credited_at"] for payout in response["payouts"]] == ["2026-09-08T16:20:00Z"]


async def test_get_staking_rewards_refuses_a_start_after_its_end(hass, api):
    await _setup(hass)
    with pytest.raises(ServiceValidationError) as excinfo:
        await _call(hass, "get_staking_rewards", start="2026-09-20 00:00:00", end="2026-09-10 00:00:00")
    assert excinfo.value.translation_key == "rewards_start_after_end"


async def test_a_payout_whose_time_does_not_parse_is_left_out_under_a_filter(hass, api):
    with patch(
        f"{_CLIENT}async_get_operations",
        AsyncMock(return_value=[*_PAYOUTS, _reward(VSN, "last Tuesday", "1.00000000", "0.00000000")]),
    ):
        await _setup(hass)
    every = (await _call(hass, "get_staking_rewards"))["payouts"]
    assert [payout["credited_at"] for payout in every][-1] == "last Tuesday"
    filtered = (await _call(hass, "get_staking_rewards", start="2026-01-01 00:00:00"))["payouts"]
    assert "last Tuesday" not in [payout["credited_at"] for payout in filtered]


async def test_the_actions_have_their_responses_only(hass, api):
    """Response data alone: no call without a response."""
    await _setup(hass)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "get_portfolio", {}, blocking=True)


async def test_the_staking_rewards_say_how_fresh_they_are(hass, api, freezer):
    entry = await _setup(hass)
    before = (await _call(hass, "get_staking_rewards"))["updated_at"]
    freezer.tick(timedelta(hours=2))
    await entry.runtime_data.rewards.async_refresh()
    after = (await _call(hass, "get_staking_rewards"))["updated_at"]
    assert dt_util.parse_datetime(after) - dt_util.parse_datetime(before) == timedelta(hours=2)
