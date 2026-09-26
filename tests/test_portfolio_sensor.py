"""Tests for the Portfolio service's sensor entities."""
from homeassistant.components.sensor import SensorStateClass

from custom_components.bitpanda.portfolio_model import (
    EarnData,
    Holding,
    PortfolioData,
    PortfolioReturns,
    RewardTotals,
)
from custom_components.bitpanda.portfolio_sensor import (
    PortfolioCashPlusSensor,
    PortfolioCashSensor,
    PortfolioReturnSensor,
    PortfolioTotalSensor,
    StakingSensor,
    WalletSensor,
    WalletTotalSensor,
    portfolio_device_info,
    wallet_device_info,
)

VSN = {"id": "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb", "symbol": "VSN", "name": "Vision", "group": "token"}
BCPEUR = {"id": "1edf9721-e545-644c-9796-ae5b69a774d7", "symbol": "BCPEUR",
          "name": "Bitpanda Cash Plus EUR", "group": "fiat_earn"}


class _Coordinator:
    """Duck-typed coordinator: what the entities read."""

    def __init__(self, data=None, last_update_success=True):
        self.data = data
        self.last_update_success = last_update_success


def _data(**holdings) -> PortfolioData:
    data = PortfolioData(holdings=dict(holdings), cash=10.0)
    data.assets = {VSN["id"]: VSN, BCPEUR["id"]: BCPEUR}
    return data


def _vsn(**overrides) -> Holding:
    values = dict(
        asset_id=VSN["id"], balance=100.0, available=25.0, value=200.0,
        invested=150.0, avg_buy_price=1.5, total_return=50.0, total_return_pct=33.33,
    )
    values.update(overrides)
    return Holding(**values)


def _portfolio(**holdings) -> _Coordinator:
    return _Coordinator(_data(**holdings))


# --- Devices ---------------------------------------------------------------------


def test_devices_are_named_after_the_service_and_the_asset():
    assert portfolio_device_info("eid")["name"] == "Portfolio"
    assert portfolio_device_info("eid")["identifiers"] == {("bitpanda", "eid_portfolio")}
    wallet = wallet_device_info("eid", VSN)
    assert wallet["name"] == "Vision (VSN) Wallet"
    assert wallet["identifiers"] == {("bitpanda", f"eid_wallet_{VSN['id']}")}


# --- Portfolio device -------------------------------------------------------------


def test_total_value_is_the_whole_account_with_no_attributes():
    coordinator = _Coordinator(_data(**{VSN["id"]: _vsn(), BCPEUR["id"]: Holding(
        asset_id=BCPEUR["id"], balance=50.0, available=50.0, value=50.0)}))
    sensor = PortfolioTotalSensor(coordinator, "eid", "EUR")
    assert sensor.entity_id == "sensor.bitpanda_portfolio_total"
    assert sensor.unique_id == "eid_portfolio_total"
    assert sensor.translation_key == "total_value"
    assert sensor.native_unit_of_measurement == "EUR"
    assert sensor.native_value == 260.0
    assert sensor.extra_state_attributes is None


def test_cash_and_cash_plus():
    coordinator = _Coordinator(_data(**{BCPEUR["id"]: Holding(
        asset_id=BCPEUR["id"], balance=50.0, available=50.0, value=50.0)}))
    cash = PortfolioCashSensor(coordinator, "eid", "EUR")
    cash_plus = PortfolioCashPlusSensor(coordinator, "eid", "EUR")
    assert (cash.entity_id, cash.native_value) == ("sensor.bitpanda_portfolio_cash", 10.0)
    assert (cash_plus.entity_id, cash_plus.native_value) == (
        "sensor.bitpanda_portfolio_cash_plus", 50.0)


def test_cash_plus_attributes_show_each_held_products_own_amount():
    coordinator = _Coordinator(_data(**{BCPEUR["id"]: Holding(
        asset_id=BCPEUR["id"], balance=100.0, available=100.0, value=114.2)}))
    sensor = PortfolioCashPlusSensor(coordinator, "eid", "EUR")
    assert sensor.extra_state_attributes == {"eur": 100.0}


def test_cash_plus_attributes_are_empty_without_cash_plus_holdings():
    coordinator = _Coordinator(_data(**{VSN["id"]: _vsn()}))
    sensor = PortfolioCashPlusSensor(coordinator, "eid", "EUR")
    assert sensor.extra_state_attributes == {}


def test_cash_plus_attributes_are_empty_when_cash_plus_itself_is_unknown():
    """An unclassified holding makes `cash_plus` itself None; the state stays
    unchanged (still None) and the attributes publish nothing, never a
    partial mapping."""
    unknown_id = "unresolved-asset-id"
    data = PortfolioData(
        holdings={
            unknown_id: Holding(asset_id=unknown_id, balance=10.0, available=10.0, value=10.0)
        },
        cash=10.0,
    )
    data.assets = {}
    sensor = PortfolioCashPlusSensor(_Coordinator(data), "eid", "EUR")
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}


def test_cash_plus_is_unknown_while_a_holding_is_unclassified():
    """An unclassified holding makes Cash Plus unknown: the fetch succeeded,
    so the sensor stays available and shows `unknown` -- never 0."""
    unknown_id = "unresolved-asset-id"
    data = PortfolioData(
        holdings={
            unknown_id: Holding(asset_id=unknown_id, balance=10.0, available=10.0, value=10.0)
        },
        cash=10.0,
    )
    sensor = PortfolioCashPlusSensor(_Coordinator(data), "eid", "EUR")
    assert sensor.native_value is None
    assert sensor.available is True


def test_cash_plus_attributes_are_empty_before_the_first_refresh():
    sensor = PortfolioCashPlusSensor(_Coordinator(None), "eid", "EUR")
    assert sensor.extra_state_attributes == {}


def test_cash_is_unknown_when_a_fiat_entry_could_not_be_read():
    """`PortfolioData.cash` is None, never 0, when a fiat balance failed to
    parse -- the Cash sensor shows `unknown`, not a quietly low total."""
    coordinator = _Coordinator(PortfolioData(cash=None))
    sensor = PortfolioCashSensor(coordinator, "eid", "EUR")
    assert sensor.native_value is None
    assert sensor.available is True


def test_an_unknown_figure_is_unknown_not_zero():
    data = _data(**{VSN["id"]: _vsn(value=None)})
    sensor = PortfolioTotalSensor(_Coordinator(data), "eid", "EUR")
    assert sensor.native_value is None
    assert sensor.available is True


def test_an_entry_that_could_not_be_read_makes_total_value_and_cash_plus_unknown():
    """It might hold anything, Cash Plus included: neither figure is told."""
    data = _data(**{VSN["id"]: _vsn()})
    data.unparsed_assets = {"unreadable-asset-id"}
    coordinator = _Coordinator(data)
    for sensor_class in (PortfolioTotalSensor, PortfolioCashPlusSensor):
        sensor = sensor_class(coordinator, "eid", "EUR")
        assert (sensor.native_value, sensor.available) == (None, True), sensor_class
    assert PortfolioCashSensor(coordinator, "eid", "EUR").native_value == 10.0


def test_a_failed_update_makes_every_figure_unavailable():
    """Unavailable only when the update failed -- such as an empty answer
    held back until it is confirmed -- whatever the last data said."""
    coordinator = _Coordinator(_data(**{VSN["id"]: _vsn()}), last_update_success=False)
    for sensor_class in (PortfolioTotalSensor, PortfolioCashSensor, PortfolioCashPlusSensor):
        assert sensor_class(coordinator, "eid", "EUR").available is False, sensor_class


def test_before_any_answer_was_taken_as_the_truth_the_figures_are_unavailable():
    """An empty first answer held back at setup: no data, a failed update."""
    coordinator = _Coordinator(None, last_update_success=False)
    for sensor_class in (PortfolioTotalSensor, PortfolioCashSensor, PortfolioCashPlusSensor):
        sensor = sensor_class(coordinator, "eid", "EUR")
        assert (sensor.native_value, sensor.available) == (None, False), sensor_class


def test_return_sensors_read_their_timeframe():
    history = _Coordinator(PortfolioReturns(values={"DAY": 1.25, "SIX_MONTH": -3.5}))
    six_months = PortfolioReturnSensor(history, "eid", "SIX_MONTH")
    assert six_months.entity_id == "sensor.bitpanda_portfolio_return_6_months"
    assert six_months.unique_id == "eid_portfolio_return_six_month"
    assert six_months.translation_key == "return_six_month"
    assert six_months.native_unit_of_measurement == "%"
    assert (six_months.native_value, six_months.available) == (-3.5, True)


def test_a_timeframe_answered_without_a_figure_is_unknown():
    """Bitpanda answered for the week, just without a usable figure: the
    sensor stays available with the state unknown."""
    history = _Coordinator(PortfolioReturns(values={"DAY": 1.25}))
    week = PortfolioReturnSensor(history, "eid", "WEEK")
    assert (week.native_value, week.available) == (None, True)


def test_a_timeframe_whose_own_request_failed_is_unavailable():
    """The week's request failed while the others answered: only its sensor
    goes unavailable, like a price whose ticker request failed."""
    history = _Coordinator(
        PortfolioReturns(values={"DAY": 1.25}, failed=frozenset({"WEEK"}))
    )
    week = PortfolioReturnSensor(history, "eid", "WEEK")
    day = PortfolioReturnSensor(history, "eid", "DAY")
    assert (week.native_value, week.available) == (None, False)
    assert (day.native_value, day.available) == (1.25, True)


def test_a_failed_history_update_makes_every_return_unavailable():
    history = _Coordinator(PortfolioReturns(values={"DAY": 1.25}), last_update_success=False)
    assert PortfolioReturnSensor(history, "eid", "DAY").available is False
    assert PortfolioReturnSensor(_Coordinator(None, False), "eid", "DAY").available is False


# --- Long-term statistics ---------------------------------------------------------------


def test_every_money_value_keeps_long_term_statistics_as_a_total():
    """Home Assistant allows only `total` for the monetary device class."""
    portfolio = _portfolio(**{VSN["id"]: _vsn()})
    earn = _Coordinator(EarnData(apr={}, offered=frozenset()))
    sensors = [
        PortfolioTotalSensor(portfolio, "eid", "EUR"),
        PortfolioCashSensor(portfolio, "eid", "EUR"),
        PortfolioCashPlusSensor(portfolio, "eid", "EUR"),
        WalletSensor(portfolio, "eid", "EUR", VSN, lambda _: True),
        StakingSensor(portfolio, earn, _Coordinator(None), "eid", "EUR", VSN),
        WalletTotalSensor(portfolio, "eid", "EUR", VSN),
    ]
    for sensor in sensors:
        assert (sensor.device_class, sensor.state_class) == ("monetary", SensorStateClass.TOTAL), (
            type(sensor).__name__
        )


def test_every_return_keeps_long_term_statistics_as_a_measurement():
    for timeframe in ("DAY", "WEEK", "MONTH", "SIX_MONTH", "YEAR"):
        sensor = PortfolioReturnSensor(_Coordinator(PortfolioReturns(values={})), "eid", timeframe)
        assert (sensor.device_class, sensor.state_class) == (None, SensorStateClass.MEASUREMENT)


# --- Wallet device ------------------------------------------------------------------


def test_wallet_is_the_unstaked_value_and_named_by_its_device():
    sensor = WalletSensor(_portfolio(**{VSN["id"]: _vsn()}), "eid", "EUR", VSN, lambda _: True)
    assert sensor.entity_id == "sensor.bitpanda_vision_vsn_wallet"
    assert sensor.unique_id == f"eid_wallet_{VSN['id']}"
    assert sensor.name is None
    assert sensor.translation_key == "wallet"
    assert sensor.native_value == 50.0
    assert sensor.extra_state_attributes == {
        "asset": "VSN", "asset_name": "Vision", "units": 25.0,
    }


def test_wallet_carries_the_position_performance_while_no_total_sensor_exists():
    sensor = WalletSensor(_portfolio(**{VSN["id"]: _vsn()}), "eid", "EUR", VSN, lambda _: False)
    assert sensor.extra_state_attributes == {
        "asset": "VSN", "asset_name": "Vision", "units": 25.0,
        "average_buy_price": 1.5, "invested_amount": 150.0,
        "total_return": 50.0, "total_return_percent": 33.33,
    }


def test_a_wallet_whose_asset_is_gone_is_unavailable():
    """/portfolio no longer lists the asset: unavailable until the wallet is
    removed."""
    sensor = WalletSensor(_portfolio(), "eid", "EUR", VSN, lambda _: False)
    assert sensor.native_value is None
    assert sensor.available is False


def _held_parts(data: PortfolioData) -> list:
    """Wallet, Staking and Total of VSN over `data`."""
    coordinator = _Coordinator(data)
    earn = _Coordinator(EarnData(apr={}, offered=frozenset()))
    return [
        WalletSensor(coordinator, "eid", "EUR", VSN, lambda _: True),
        StakingSensor(coordinator, earn, _Coordinator(None), "eid", "EUR", VSN),
        WalletTotalSensor(coordinator, "eid", "EUR", VSN),
    ]


def test_a_held_asset_without_a_value_is_unknown():
    """Listed by /portfolio, but Bitpanda sent no value: available, unknown."""
    for sensor in _held_parts(_data(**{VSN["id"]: _vsn(value=None)})):
        assert (sensor.native_value, sensor.available) == (None, True), type(sensor).__name__


def test_a_held_asset_whose_entry_cannot_be_read_is_unknown():
    """Still listed -- PortfolioData.held counts an unreadable entry -- so
    its wallet is unknown, not unavailable; it shows no units either."""
    data = _data()
    data.unparsed_assets = {VSN["id"]}
    for sensor in _held_parts(data):
        assert (sensor.native_value, sensor.available) == (None, True), type(sensor).__name__
        assert "units" not in sensor.extra_state_attributes


def test_a_failed_refresh_makes_the_wallet_unavailable():
    coordinator = _Coordinator(_data(**{VSN["id"]: _vsn()}), last_update_success=False)
    assert WalletSensor(coordinator, "eid", "EUR", VSN, lambda _: False).available is False


def test_staking_is_the_staked_value_with_earn_attributes():
    rewards = _Coordinator({VSN["id"]: RewardTotals(
        gross=12.0, fee=2.4, net=9.6, count=3, last_at="2026-09-22T17:16:35Z")})
    earn = _Coordinator(EarnData(apr={VSN["id"]: 0.0544}, offered=frozenset({VSN["id"]})))
    sensor = StakingSensor(_portfolio(**{VSN["id"]: _vsn()}), earn, rewards, "eid", "EUR", VSN)
    assert sensor.entity_id == "sensor.bitpanda_vision_vsn_wallet_staking"
    assert sensor.unique_id == f"eid_staking_{VSN['id']}"
    assert sensor.translation_key == "staking"
    # Its icon comes from icons.json by that key (tests/test_icons.py).
    assert sensor.icon is None
    assert sensor.native_value == 150.0
    assert sensor.extra_state_attributes == {
        "asset": "VSN", "asset_name": "Vision", "units": 75.0, "apr_percent": 5.44,
        "rewards_gross": 12.0, "rewards_fee": 2.4, "rewards_net": 9.6,
        "rewards_count": 3, "rewards_last_at": "2026-09-22T17:16:35Z",
    }


def test_apr_percent_keeps_every_decimal_the_api_sends():
    """Rounded to DECIMALS (8), like every other computed figure -- 2 decimals
    would turn 0.05125 into 5.12 and quietly drop the last digit."""
    earn = _Coordinator(EarnData(apr={VSN["id"]: 0.05125}, offered=frozenset({VSN["id"]})))
    sensor = StakingSensor(_portfolio(**{VSN["id"]: _vsn()}), earn, _Coordinator(None),
                           "eid", "EUR", VSN)
    assert sensor.extra_state_attributes["apr_percent"] == 5.125


def test_staking_without_earn_or_reward_data_leaves_those_attributes_out():
    """A failed rewards refresh before the first success: attributes absent,
    never a partial recount."""
    sensor = StakingSensor(
        _portfolio(**{VSN["id"]: _vsn()}), _Coordinator(None), _Coordinator(None),
        "eid", "EUR", VSN,
    )
    assert sensor.extra_state_attributes == {"asset": "VSN", "asset_name": "Vision", "units": 75.0}


def test_staking_keeps_the_last_complete_reward_totals_after_a_failed_refresh():
    rewards = _Coordinator({VSN["id"]: RewardTotals(gross=1.0, fee=0.2, net=0.8, count=1)},
                           last_update_success=False)
    sensor = StakingSensor(_portfolio(**{VSN["id"]: _vsn()}), _Coordinator(None), rewards,
                           "eid", "EUR", VSN)
    assert sensor.extra_state_attributes["rewards_net"] == 0.8


def test_a_performance_figure_bitpanda_did_not_send_is_left_out():
    """Absent, never None or 0."""
    holding = _vsn(invested=None, total_return_pct=None)
    sensor = WalletTotalSensor(_portfolio(**{VSN["id"]: holding}), "eid", "EUR", VSN)
    assert sensor.extra_state_attributes == {
        "asset": "VSN", "asset_name": "Vision", "units": 100.0,
        "average_buy_price": 1.5, "total_return": 50.0,
    }


def test_total_is_the_whole_position_with_its_performance():
    sensor = WalletTotalSensor(_portfolio(**{VSN["id"]: _vsn()}), "eid", "EUR", VSN)
    assert sensor.entity_id == "sensor.bitpanda_vision_vsn_wallet_total"
    assert sensor.unique_id == f"eid_total_{VSN['id']}"
    assert sensor.translation_key == "wallet_total"
    assert sensor.native_value == 200.0
    assert sensor.extra_state_attributes == {
        "asset": "VSN", "asset_name": "Vision", "units": 100.0,
        "average_buy_price": 1.5, "invested_amount": 150.0,
        "total_return": 50.0, "total_return_percent": 33.33,
    }
