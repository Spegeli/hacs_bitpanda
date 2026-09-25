"""Tests for the Portfolio service's sensor entities."""
from custom_components.bitpanda.portfolio_model import (
    EarnData,
    Holding,
    PortfolioData,
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


def test_cash_is_unavailable_when_a_fiat_entry_could_not_be_read():
    """`PortfolioData.cash` is None, never 0, when a fiat balance failed to
    parse -- the Cash sensor must go unavailable, not show a quietly low
    total."""
    coordinator = _Coordinator(PortfolioData(cash=None))
    sensor = PortfolioCashSensor(coordinator, "eid", "EUR")
    assert sensor.native_value is None
    assert sensor.available is False


def test_an_unknown_figure_makes_its_sensor_unavailable_not_zero():
    data = _data(**{VSN["id"]: _vsn(value=None)})
    sensor = PortfolioTotalSensor(_Coordinator(data), "eid", "EUR")
    assert sensor.native_value is None
    assert sensor.available is False


def test_return_sensors_read_their_timeframe():
    history = _Coordinator({"DAY": 1.25, "SIX_MONTH": -3.5})
    six_months = PortfolioReturnSensor(history, "eid", "SIX_MONTH")
    week = PortfolioReturnSensor(history, "eid", "WEEK")
    assert six_months.entity_id == "sensor.bitpanda_portfolio_return_6_months"
    assert six_months.unique_id == "eid_portfolio_return_six_month"
    assert six_months.translation_key == "return_six_month"
    assert six_months.native_unit_of_measurement == "%"
    assert six_months.native_value == -3.5
    assert week.available is False


# --- Wallet device ------------------------------------------------------------------


def test_wallet_is_the_unstaked_value_and_named_by_its_device():
    sensor = WalletSensor(_portfolio(**{VSN["id"]: _vsn()}), "eid", "EUR", VSN, lambda _: True)
    assert sensor.entity_id == "sensor.bitpanda_vision_vsn_wallet"
    assert sensor.unique_id == f"eid_wallet_{VSN['id']}"
    assert sensor.name is None
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
    sensor = WalletSensor(_portfolio(), "eid", "EUR", VSN, lambda _: False)
    assert sensor.native_value is None
    assert sensor.available is False


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
