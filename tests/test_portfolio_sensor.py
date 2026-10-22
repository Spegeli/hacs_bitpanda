"""Tests for the Portfolio service's sensor entities."""
import pytest
from homeassistant.components.sensor import SensorStateClass

from custom_components.bitpanda.naming import PORTFOLIO_DEVICE_NAME
from custom_components.bitpanda.portfolio_model import (
    PORTFOLIO_FIGURES,
    EarnData,
    Holding,
    PortfolioData,
    PortfolioReturns,
    RewardTotals,
)
from custom_components.bitpanda.portfolio_sensor import (
    PortfolioCashPlusSensor,
    PortfolioCashSensor,
    PortfolioInvestedSensor,
    PortfolioReturnSensor,
    PortfolioTotalReturnPercentSensor,
    PortfolioTotalReturnSensor,
    PortfolioTotalSensor,
    StakingSensor,
    WalletSensor,
    WalletTotalSensor,
    portfolio_device_info,
    wallet_device_info,
)

from tests.conftest import manifest_version

VSN = {"id": "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb", "symbol": "VSN", "name": "Vision", "group": "token"}
BCPEUR = {"id": "1edf9721-e545-644c-9796-ae5b69a774d7", "symbol": "BCPEUR",
          "name": "Bitpanda Cash Plus EUR", "group": "fiat_earn"}


class _Coordinator:
    """Duck-typed coordinator: what the entities read. `data_available`
    follows the outcome of the last refresh unless given: a failed refresh
    whose failure is not confirmed yet leaves it True (tolerance.py)."""

    def __init__(self, data=None, last_update_success=True, data_available=None):
        self.data = data
        self.last_update_success = last_update_success
        self.data_available = last_update_success if data_available is None else data_available


class _Prices:
    """The wallets' ticker prices as WalletPrices gives them."""

    def __init__(self, prices=None):
        self.prices = dict(prices or {})

    def price_of(self, asset_id):
        return self.prices.get(asset_id)

    def async_listen(self, asset_id, update):
        return lambda: None


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


def test_the_portfolio_device_shows_the_version_and_leads_to_the_api_key_page():
    """"Visit" opens the page where the user manages the API key; the card
    shows the integration's version. No serial number: the Portfolio is no
    asset."""
    info = portfolio_device_info("eid")
    assert info["configuration_url"] == "https://app.bitpanda.com/my-account/apikey"
    assert info["sw_version"] == manifest_version()
    assert "serial_number" not in info


def test_a_wallet_device_shows_the_assets_id_and_leads_to_bitpandas_prices():
    """"Visit" opens Bitpanda's price overview, the same for every asset
    type; the asset's ID -- the one the log names -- shows as the serial
    number, beside the integration's version."""
    info = wallet_device_info("eid", VSN)
    assert info["configuration_url"] == "https://www.bitpanda.com/en/prices"
    assert info["serial_number"] == VSN["id"]
    assert info["sw_version"] == manifest_version()


def test_devices_are_named_after_the_service_and_the_asset():
    """By naming.py, which builds every entity ID from these names."""
    assert portfolio_device_info("eid")["name"] == PORTFOLIO_DEVICE_NAME == "Portfolio"
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


def test_a_tolerated_failure_keeps_every_figure():
    """The last refresh failed -- the connection dropped, say -- but the
    failure is not confirmed yet: every figure shows the last data,
    available."""
    coordinator = _Coordinator(
        _data(**{VSN["id"]: _vsn()}), last_update_success=False, data_available=True
    )
    for sensor_class, value in (
        (PortfolioTotalSensor, 210.0),
        (PortfolioCashSensor, 10.0),
        (PortfolioCashPlusSensor, 0.0),
    ):
        sensor = sensor_class(coordinator, "eid", "EUR")
        assert (sensor.native_value, sensor.available) == (value, True), sensor_class


def test_a_confirmed_failure_makes_every_figure_unavailable():
    """Unavailable once the failure is confirmed, whatever the last data
    said."""
    coordinator = _Coordinator(_data(**{VSN["id"]: _vsn()}), last_update_success=False)
    for sensor_class in (PortfolioTotalSensor, PortfolioCashSensor, PortfolioCashPlusSensor):
        assert sensor_class(coordinator, "eid", "EUR").available is False, sensor_class


def test_before_the_first_answer_the_figures_are_unavailable():
    """No answer yet, and the update failed: there is nothing to show."""
    coordinator = _Coordinator(None, last_update_success=False)
    for sensor_class in (PortfolioTotalSensor, PortfolioCashSensor, PortfolioCashPlusSensor):
        sensor = sensor_class(coordinator, "eid", "EUR")
        assert (sensor.native_value, sensor.available) == (None, False), sensor_class


def test_without_data_the_figures_are_unavailable_even_before_any_failure():
    """No data yet, but the update reported success: still unavailable until
    the first answer arrives."""
    coordinator = _Coordinator(None, last_update_success=True)
    for sensor_class in (PortfolioTotalSensor, PortfolioCashSensor, PortfolioCashPlusSensor):
        assert sensor_class(coordinator, "eid", "EUR").available is False, sensor_class


def test_a_waiting_figure_is_unavailable_and_the_others_are_not():
    """The answers no longer list Cash's entry, and that is not confirmed
    yet (PortfolioData.waiting): Cash is unavailable -- a gap in its
    history, never a false 0 -- while Total value and Cash Plus are
    shown."""
    data = _data(**{VSN["id"]: _vsn()})
    data.waiting = frozenset({"cash"})
    coordinator = _Coordinator(data)
    assert PortfolioCashSensor(coordinator, "eid", "EUR").available is False
    for sensor_class in (PortfolioTotalSensor, PortfolioCashPlusSensor):
        assert sensor_class(coordinator, "eid", "EUR").available is True, sensor_class


def test_the_figure_keys_are_the_sensors_keys():
    """The coordinator names the waiting figures by these keys
    (PORTFOLIO_FIGURES), and each figure's sensors wait on one of them
    (`_watch`, else `_key`): a figure no sensor waits on would never show
    its wait."""
    assert {
        sensor_class._watch or sensor_class._key
        for sensor_class in (
            PortfolioTotalSensor, PortfolioCashSensor, PortfolioCashPlusSensor,
            PortfolioInvestedSensor, PortfolioTotalReturnSensor,
            PortfolioTotalReturnPercentSensor,
        )
    } == set(PORTFOLIO_FIGURES)


# --- A return's amount -------------------------------------------------------------------


def _return_sensor(percent, data=None, **outcome) -> PortfolioReturnSensor:
    history = _Coordinator(PortfolioReturns(values={"DAY": percent}))
    portfolio = _Coordinator(data if data is not None else _data(**{VSN["id"]: _vsn()}), **outcome)
    return PortfolioReturnSensor(history, "eid", "DAY", portfolio)


def test_the_return_amount_is_what_the_percentage_means_on_todays_total():
    """Bitpanda gives the return in percent; on today's total value of 210
    a return of 1.24 % means 210 × 1.24 ÷ 101.24 -- the Portfolio card's
    formula."""
    sensor = _return_sensor(1.24)
    assert sensor.native_value == 1.24
    assert sensor.extra_state_attributes == {"return_amount": round(210 * 1.24 / 101.24, 2)}
    assert _return_sensor(-3.5).extra_state_attributes == {
        "return_amount": round(210 * -3.5 / 96.5, 2)
    }


def test_the_return_amount_is_absent_without_a_total_or_a_return():
    waiting = _data(**{VSN["id"]: _vsn()})
    waiting.waiting = frozenset({"total"})
    unknown_total = _data(**{VSN["id"]: _vsn(value=None)})
    for sensor in (
        _return_sensor(None),
        _return_sensor(-100.0),
        _return_sensor(-150.0),
        _return_sensor(1.24, waiting),
        _return_sensor(1.24, unknown_total),
        _return_sensor(1.24, last_update_success=False, data_available=False),
        PortfolioReturnSensor(_Coordinator(PortfolioReturns(values={"DAY": 1.0})), "eid", "DAY"),
    ):
        assert sensor.extra_state_attributes == {}


# --- Invested and the total return of the whole portfolio -------------------------------

_OTHER = {"id": "b86c034b-efe3-11eb-b56f-0691764446a7", "symbol": "BTC", "name": "Bitcoin",
          "group": "coin"}
_A1 = (PortfolioInvestedSensor, PortfolioTotalReturnSensor, PortfolioTotalReturnPercentSensor)


def _two_positions(**overrides) -> PortfolioData:
    """VSN (200 worth, 150 invested), BTC (100 worth, 50 invested), Cash Plus
    and 10 cash: the positions are VSN and BTC."""
    other = {"balance": 1.0, "available": 1.0, "value": 100.0, "invested": 50.0, **overrides}
    data = _data(**{
        VSN["id"]: _vsn(),
        _OTHER["id"]: Holding(asset_id=_OTHER["id"], **other),
        BCPEUR["id"]: Holding(asset_id=BCPEUR["id"], balance=50.0, available=50.0, value=50.0),
    })
    data.assets[_OTHER["id"]] = _OTHER
    return data


def test_invested_and_total_return_sum_the_positions():
    """Over the wallets, never Cash or Cash Plus: Σ value − Σ invested, and
    that over Σ invested -- as the Portfolio card's groups compute it."""
    coordinator = _Coordinator(_two_positions())
    invested, total_return, percent = (cls(coordinator, "eid", "EUR") for cls in _A1)
    assert invested.native_value == 200.0
    assert total_return.native_value == 100.0
    assert percent.native_value == 50.0
    assert (invested.entity_id, total_return.entity_id, percent.entity_id) == (
        "sensor.bitpanda_portfolio_invested",
        "sensor.bitpanda_portfolio_total_return",
        "sensor.bitpanda_portfolio_total_return_percent",
    )
    assert (invested.unique_id, percent.translation_key) == (
        "eid_portfolio_invested", "total_return_percent"
    )
    assert (invested.native_unit_of_measurement, percent.native_unit_of_measurement) == ("EUR", "%")


def test_the_portfolio_return_figures_are_unknown_in_doubt():
    unparsed = _two_positions()
    unparsed.unparsed_assets = {"unreadable"}
    unclassified = _two_positions()
    del unclassified.assets[_OTHER["id"]]
    for data in (unparsed, unclassified, _two_positions(invested=None), _two_positions(value=None)):
        coordinator = _Coordinator(data)
        assert [cls(coordinator, "eid", "EUR").native_value for cls in _A1] == [None] * 3


def test_total_return_percent_is_unknown_without_anything_invested():
    data = _data(**{VSN["id"]: _vsn(invested=0.0)})
    percent = PortfolioTotalReturnPercentSensor(_Coordinator(data), "eid", "EUR")
    assert percent.native_value is None
    assert percent.extra_state_attributes == {}


def test_without_positions_nothing_is_invested():
    """Everything sold, once that is confirmed: 0 invested, 0 return, and no
    percentage over nothing."""
    coordinator = _Coordinator(_data())
    assert [cls(coordinator, "eid", "EUR").native_value for cls in _A1] == [0.0, 0.0, None]


def test_the_portfolio_return_figures_wait_with_the_positions():
    data = _two_positions()
    data.waiting = frozenset({"positions"})
    coordinator = _Coordinator(data)
    for cls in _A1:
        assert cls(coordinator, "eid", "EUR").available is False, cls
    assert PortfolioTotalSensor(coordinator, "eid", "EUR").available is True


def test_the_wallets_attribute_counts_the_positions_summed():
    coordinator = _Coordinator(_two_positions())
    for cls in _A1:
        assert cls(coordinator, "eid", "EUR").extra_state_attributes == {"wallets": 2}, cls
    unknown = _Coordinator(_two_positions(invested=None))
    for cls in _A1:
        assert cls(unknown, "eid", "EUR").extra_state_attributes == {}, cls


def test_the_portfolio_return_figures_show_two_decimals():
    coordinator = _Coordinator(_two_positions())
    for cls in _A1:
        assert cls(coordinator, "eid", "EUR").suggested_display_precision == 2, cls


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


def test_a_tolerated_history_failure_keeps_every_return():
    """The history update failed, but the failure is not confirmed yet
    (tolerance.py): the returns show the last data, available."""
    history = _Coordinator(
        PortfolioReturns(values={"DAY": 1.25}), last_update_success=False, data_available=True
    )
    day = PortfolioReturnSensor(history, "eid", "DAY")
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
        PortfolioInvestedSensor(portfolio, "eid", "EUR"),
        PortfolioTotalReturnSensor(portfolio, "eid", "EUR"),
        WalletSensor(portfolio, "eid", "EUR", VSN),
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
    percent = PortfolioTotalReturnPercentSensor(_portfolio(), "eid", "EUR")
    assert (percent.device_class, percent.state_class) == (None, SensorStateClass.MEASUREMENT)


# --- Wallet device ------------------------------------------------------------------


def test_wallet_is_the_unstaked_value():
    """Named by its translation key, like its Staking and Total siblings
    (tests/test_init.py checks the names). Its attributes name the asset and
    count the units -- never the position performance, which is on the Total
    sensor every wallet has."""
    sensor = WalletSensor(_portfolio(**{VSN["id"]: _vsn()}), "eid", "EUR", VSN)
    assert sensor.entity_id == "sensor.bitpanda_vision_vsn_wallet_available"
    assert sensor.unique_id == f"eid_wallet_{VSN['id']}"
    assert sensor.translation_key == "wallet"
    assert sensor.native_value == 50.0
    assert sensor.extra_state_attributes == {
        "asset": "VSN", "asset_name": "Vision", "asset_category": "other", "units": 25.0,
    }


def test_a_wallet_whose_asset_is_gone_is_unavailable():
    """/portfolio no longer lists the asset: unavailable until the wallet is
    removed."""
    sensor = WalletSensor(_portfolio(), "eid", "EUR", VSN)
    assert sensor.native_value is None
    assert sensor.available is False


def _held_parts(data: PortfolioData, **outcome) -> list:
    """Wallet, Staking and Total of VSN over `data`, the outcome of the last
    refresh as `outcome` gives it (_Coordinator's keywords)."""
    coordinator = _Coordinator(data, **outcome)
    earn = _Coordinator(EarnData(apr={}, offered=frozenset()))
    return [
        WalletSensor(coordinator, "eid", "EUR", VSN),
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


def test_a_tolerated_failure_keeps_the_wallet():
    """A failed refresh whose failure is not confirmed yet: Wallet, Staking
    and Total show the last data, available."""
    parts = _held_parts(
        _data(**{VSN["id"]: _vsn()}), last_update_success=False, data_available=True
    )
    assert [(type(s).__name__, s.native_value, s.available) for s in parts] == [
        ("WalletSensor", 50.0, True),
        ("StakingSensor", 150.0, True),
        ("WalletTotalSensor", 200.0, True),
    ]


def test_staking_keeps_its_value_through_a_tolerated_failure():
    """Earn and Rewards feed attributes only, yet the sensor writes its state
    after each of their refreshes too: whatever they report, its value and
    availability follow the Portfolio's tolerance alone."""
    portfolio = _Coordinator(
        _data(**{VSN["id"]: _vsn()}), last_update_success=False, data_available=True
    )
    earn = _Coordinator(None, last_update_success=False)
    rewards = _Coordinator(None, last_update_success=False)
    sensor = StakingSensor(portfolio, earn, rewards, "eid", "EUR", VSN)
    assert (sensor.native_value, sensor.available) == (150.0, True)


def test_a_confirmed_failure_makes_the_wallet_unavailable():
    coordinator = _Coordinator(_data(**{VSN["id"]: _vsn()}), last_update_success=False)
    assert WalletSensor(coordinator, "eid", "EUR", VSN).available is False


def test_staking_is_the_staked_value_with_earn_attributes():
    rewards = _Coordinator({VSN["id"]: RewardTotals(
        gross=12.0, fee=2.4, net=9.6, count=3, last_at="2026-09-22T17:16:35Z")})
    earn = _Coordinator(EarnData(apr={VSN["id"]: 0.0544}, offered=frozenset({VSN["id"]})))
    sensor = StakingSensor(
        _portfolio(**{VSN["id"]: _vsn()}), earn, rewards, "eid", "EUR", VSN, _Prices({VSN["id"]: 2.0})
    )
    assert sensor.entity_id == "sensor.bitpanda_vision_vsn_wallet_staking"
    assert sensor.unique_id == f"eid_staking_{VSN['id']}"
    assert sensor.translation_key == "staking"
    # Its icon comes from icons.json by that key (tests/test_icons.py).
    assert sensor.icon is None
    assert sensor.native_value == 150.0
    assert sensor.extra_state_attributes == {
        "asset": "VSN", "asset_name": "Vision", "asset_category": "other", "units": 75.0,
        "apr_percent": 5.44,
        "rewards_gross": 12.0, "rewards_fee": 2.4, "rewards_net": 9.6,
        "rewards_net_value": 19.2,
        "rewards_count": 3, "rewards_last_at": "2026-09-22T17:16:35Z",
    }


def test_the_net_rewards_are_valued_at_todays_price():
    """As the Bitpanda app shows them: the net reward units at the wallet's
    ticker price, in the Portfolio currency and to the cent. Today's value of
    the coins -- no endpoint prices the day they were paid out."""
    rewards = _Coordinator({VSN["id"]: RewardTotals(
        gross=2136.65, fee=371.12, net=1765.53, count=62, last_at="2026-09-22T17:16:35Z")})
    holding = _vsn(balance=21466.95, available=0.0, value=826.72)
    sensor = StakingSensor(_portfolio(**{VSN["id"]: holding}), _Coordinator(None), rewards,
                           "eid", "EUR", VSN, _Prices({VSN["id"]: 0.0385}))
    # 1,765.53 VSN at 0.0385 EUR each: 67.97... EUR.
    assert sensor.extra_state_attributes["rewards_net_value"] == 67.97


def test_the_net_rewards_have_no_value_while_the_price_is_unknown():
    """No ticker price of the last 15 minutes -- never the value over the
    units instead --, or the asset's entry could not be read: the key is
    absent -- never None or 0 -- while the rewards themselves are shown."""
    rewards = _Coordinator({VSN["id"]: RewardTotals(gross=12.0, fee=2.4, net=9.6, count=3)})
    unreadable = _data()
    unreadable.unparsed_assets = {VSN["id"]}
    for data in (
        _data(**{VSN["id"]: _vsn()}),
        _data(**{VSN["id"]: _vsn(value=None)}),
        unreadable,
    ):
        sensor = StakingSensor(_Coordinator(data), _Coordinator(None), rewards, "eid", "EUR", VSN)
        attributes = sensor.extra_state_attributes
        assert "rewards_net_value" not in attributes
        assert attributes["rewards_net"] == 9.6


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
    assert sensor.extra_state_attributes == {
        "asset": "VSN", "asset_name": "Vision", "asset_category": "other", "units": 75.0,
    }


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
        "asset": "VSN", "asset_name": "Vision", "asset_category": "other", "units": 100.0,
        "average_buy_price": 1.5, "total_return": 50.0,
    }


def test_without_a_ticker_price_there_is_no_price():
    """Never the value over the units, which /portfolio gives in cents: no
    ticker price of the last 15 minutes, no price and no 24-hour figures,
    whatever the price of a day ago."""
    holding = _vsn(balance=21516.68407659, available=0.0, value=805.96)
    sensor = WalletTotalSensor(_portfolio(**{VSN["id"]: holding}), "eid", "EUR", VSN, prices=_Prices())
    sensor.set_price_24h_ago(0.0387)
    attributes = sensor.extra_state_attributes
    for key in ("price", "price_24h_ago", "change_24h_pct", "return_24h"):
        assert key not in attributes, key


def test_a_ticker_price_keeps_its_significant_digits():
    """Also for a token worth a fraction of a cent."""
    prices = _Prices({VSN["id"]: 0.0000081199123456})
    sensor = WalletTotalSensor(_portfolio(**{VSN["id"]: _vsn()}), "eid", "EUR", VSN, prices=prices)
    assert sensor.extra_state_attributes["price"] == pytest.approx(0.0000081199123456, rel=1e-9)


def test_the_price_comes_from_the_ticker_when_there_is_one():
    """The ticker's price, not the value over the units -- which /portfolio
    gives in cents; without one, none."""
    holding = _vsn(balance=21516.68407659, available=0.0, value=805.96)
    prices = _Prices({VSN["id"]: 0.03727184})
    sensor = WalletTotalSensor(_portfolio(**{VSN["id"]: holding}), "eid", "EUR", VSN, prices=prices)
    assert sensor.extra_state_attributes["price"] == 0.03727184
    prices.prices = {}
    assert "price" not in sensor.extra_state_attributes


def test_the_24h_figures_use_the_ticker_price():
    holding = _vsn(balance=1000.0, available=1000.0, value=100.0)
    sensor = WalletTotalSensor(
        _portfolio(**{VSN["id"]: holding}), "eid", "EUR", VSN, prices=_Prices({VSN["id"]: 0.11})
    )
    sensor.set_price_24h_ago(0.1)
    attributes = sensor.extra_state_attributes
    assert attributes["change_24h_pct"] == 10.0
    assert attributes["return_24h"] == pytest.approx(10.0)


def test_the_rewards_value_today_uses_the_same_price():
    """„Aktueller Preis“ × „Verdient (netto)“ = „Heutiger Wert“."""
    rewards = _Coordinator({VSN["id"]: RewardTotals(
        gross=12.0, fee=2.0, net=10.0, count=3, last_at="2026-09-22T17:16:35Z")})
    sensor = StakingSensor(
        _portfolio(**{VSN["id"]: _vsn()}), _Coordinator(None), rewards, "eid", "EUR", VSN,
        _Prices({VSN["id"]: 0.0373}),
    )
    assert sensor.extra_state_attributes["rewards_net_value"] == 0.37


def test_the_24h_figures_follow_the_price_of_a_day_ago():
    """The change of the price, and what it made of today's units."""
    units = 21516.684
    holding = _vsn(balance=units, available=0.0, value=0.0374 * units)
    sensor = WalletTotalSensor(
        _portfolio(**{VSN["id"]: holding}), "eid", "EUR", VSN, prices=_Prices({VSN["id"]: 0.0374})
    )
    assert "price_24h_ago" not in sensor.extra_state_attributes
    sensor.set_price_24h_ago(0.0382)
    attributes = sensor.extra_state_attributes
    assert attributes["price_24h_ago"] == 0.0382
    assert attributes["change_24h_pct"] == round((0.0374 - 0.0382) / 0.0382 * 100, 2)
    assert attributes["return_24h"] == pytest.approx(units * (0.0374 - 0.0382))
    sensor.set_price_24h_ago(None)
    assert "return_24h" not in sensor.extra_state_attributes


def test_a_stock_etf_or_etc_shows_its_isin_on_every_wallet_part():
    """`asset_isin` beside `asset` and `asset_name`. Any other asset has no
    such key at all -- the tests above compare VSN's whole attributes."""
    etf = {"id": "1f0ed6c9-ee10-68c6-8a0e-55a29b7757fe", "symbol": "LYY1",
           "name": "Amundi PEA S&P 500 UCITS ETF", "isin": "FR0011871136",
           "type": "equity_security", "group": "equity_etf"}
    data = PortfolioData(holdings={etf["id"]: Holding(
        asset_id=etf["id"], balance=10.0, available=10.0, value=5000.0)}, cash=0.0)
    data.assets = {etf["id"]: etf}
    coordinator = _Coordinator(data)
    earn = _Coordinator(EarnData(apr={}, offered=frozenset()))
    wallet = WalletSensor(coordinator, "eid", "EUR", etf)
    assert wallet.extra_state_attributes == {
        "asset": "LYY1", "asset_name": "Amundi PEA S&P 500 UCITS ETF",
        "asset_category": "etf", "asset_isin": "FR0011871136", "units": 10.0,
    }
    for sensor in (
        StakingSensor(coordinator, earn, _Coordinator(None), "eid", "EUR", etf),
        WalletTotalSensor(coordinator, "eid", "EUR", etf),
    ):
        assert sensor.extra_state_attributes["asset_isin"] == "FR0011871136", (
            type(sensor).__name__
        )


def test_every_wallet_sensor_names_its_category():
    """`asset_category` on the available, total and staking sensor alike, so
    a dashboard card can group a wallet by any of them."""
    etf = {"id": "1f0ed6c9-ee10-68c6-8a0e-55a29b7757fe", "symbol": "LYY1",
           "name": "Amundi PEA S&P 500 UCITS ETF", "isin": "FR0011871136",
           "type": "equity_security", "group": "equity_etf"}
    data = PortfolioData(holdings={etf["id"]: Holding(
        asset_id=etf["id"], balance=10.0, available=10.0, value=5000.0)}, cash=0.0)
    data.assets = {etf["id"]: etf}
    coordinator = _Coordinator(data)
    earn = _Coordinator(EarnData(apr={}, offered=frozenset()))
    for sensor in (
        WalletSensor(coordinator, "eid", "EUR", etf),
        WalletTotalSensor(coordinator, "eid", "EUR", etf),
        StakingSensor(coordinator, earn, _Coordinator(None), "eid", "EUR", etf),
    ):
        assert sensor.extra_state_attributes["asset_category"] == "etf", type(sensor).__name__


def test_total_is_the_whole_position_with_its_performance():
    sensor = WalletTotalSensor(_portfolio(**{VSN["id"]: _vsn()}), "eid", "EUR", VSN)
    assert sensor.entity_id == "sensor.bitpanda_vision_vsn_wallet_total"
    assert sensor.unique_id == f"eid_total_{VSN['id']}"
    assert sensor.translation_key == "wallet_total"
    assert sensor.native_value == 200.0
    assert sensor.extra_state_attributes == {
        "asset": "VSN", "asset_name": "Vision", "asset_category": "other", "units": 100.0,
        "average_buy_price": 1.5, "invested_amount": 150.0,
        "total_return": 50.0, "total_return_percent": 33.33,
    }
