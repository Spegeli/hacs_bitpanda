"""Tests for the Portfolio data model."""
from datetime import UTC, datetime, timedelta

import pytest

from custom_components.bitpanda.const import PORTFOLIO_UPDATE_INTERVAL
from custom_components.bitpanda.portfolio_model import (
    PORTFOLIO_FIGURES,
    EarnData,
    FigureWatch,
    Holding,
    PortfolioData,
    PortfolioReturns,
    RewardPayout,
    _is_later,
    lists_nothing,
    parse_earn_configs,
    parse_portfolio,
    payouts_after,
    staking_applies,
    sum_rewards,
    tolerate_failed_timeframes,
)

from tests.conftest import load_fixture

VSN = "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb"
BCPEUR = "1edf9721-e545-644c-9796-ae5b69a774d7"
BCPUSD = "1edf9721-e545-644c-9796-ae5b69a774d8"
BCPGBP = "1edf9721-e545-644c-9796-ae5b69a774d9"
EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"


def _money(value: str) -> dict:
    return {"value": value, "currency_id": EUR_ID}


def _asset_entry(asset_id, balance, available, value="100.00", **extra) -> dict:
    entry = {
        "asset_id": asset_id,
        "balance": _money(balance),
        "available_balance": _money(available),
        "average_buy_price": _money("2.00000000"),
        "invested_amount": _money("80.00"),
        "total_return": _money("20.00"),
        "total_return_percent": 25.0,
        **extra,
    }
    if value is not None:
        entry["currency_balance"] = _money(value)
    return entry


def _fiat_entry(balance, available=None) -> dict:
    return {
        "currency_id": EUR_ID,
        "balance": _money(balance),
        "available_balance": _money(available or balance),
    }


# --- Holding: splitting a position ------------------------------------------


def test_split_of_a_partly_staked_position():
    holding = Holding(asset_id=VSN, balance=100.0, available=25.0, value=200.0)
    assert holding.staked == 75.0
    assert holding.wallet_value == 50.0
    assert holding.staking_value == 150.0


def test_fully_staked_position_has_a_wallet_value_of_zero():
    holding = Holding(asset_id=VSN, balance=21466.95, available=0.0, value=431.44)
    assert holding.wallet_value == 0.0
    assert holding.staking_value == 431.44


def test_split_rounds_to_eight_decimals():
    holding = Holding(asset_id=VSN, balance=3.0, available=1.0, value=10.0)
    assert holding.wallet_value == 3.33333333
    assert holding.staking_value == 6.66666667


def test_missing_value_gives_no_value_never_zero():
    holding = Holding(asset_id=VSN, balance=10.0, available=5.0, value=None)
    assert holding.wallet_value is None
    assert holding.staking_value is None


def test_available_above_balance_is_clamped():
    holding = Holding(asset_id=VSN, balance=10.0, available=10.5, value=20.0)
    assert holding.staked == 0.0
    assert holding.wallet_value == 20.0
    assert holding.staking_value == 0.0


def test_the_price_is_what_one_unit_is_worth_in_the_same_answer():
    """The value over the units -- the proportion the value is split by --
    unrounded, so a token worth a fraction of a cent keeps its digits."""
    holding = Holding(asset_id=VSN, balance=21466.95, available=0.0, value=826.72)
    assert holding.price == 826.72 / 21466.95


def test_the_price_is_unknown_without_a_value_or_without_units():
    assert Holding(asset_id=VSN, balance=10.0, available=10.0, value=None).price is None
    assert Holding(asset_id=VSN, balance=0.0, available=0.0, value=0.0).price is None


# --- parse_portfolio ------------------------------------------------------------


def test_parse_splits_assets_from_fiat_and_sums_cash_from_balance():
    data = parse_portfolio(
        [
            _asset_entry(VSN, "100.00000000", "25.00000000", "200.00"),
            _fiat_entry("12.50", available="10.00"),
            _fiat_entry("7.50"),
        ]
    )
    assert set(data.holdings) == {VSN}
    # `balance`, not `available_balance`: fiat locked by an order is still cash.
    assert data.cash == 20.0
    holding = data.holdings[VSN]
    assert holding.invested == 80.0
    assert holding.avg_buy_price == 2.0
    assert holding.total_return == 20.0
    assert holding.total_return_pct == 25.0


def test_parse_skips_an_unparsable_holding():
    data = parse_portfolio([{"asset_id": VSN, "balance": {"value": "x"}}])
    assert data.holdings == {}
    assert data.unparsed_assets == {VSN}


def test_an_unparsable_holding_still_counts_as_held():
    """An unreadable entry is no sign of a sale."""
    data = parse_portfolio(
        [_asset_entry(VSN, "100.0", "25.0"), {"asset_id": BCPEUR, "balance": {"value": "x"}}]
    )
    assert data.held == {VSN, BCPEUR}


def test_parse_keeps_a_holding_without_currency_balance_as_no_value():
    data = parse_portfolio([_asset_entry(VSN, "1.0", "1.0", value=None)])
    assert data.holdings[VSN].value is None


def test_a_non_finite_amount_is_no_amount():
    """"NaN" or "Infinity" is no amount Home Assistant could show as a
    sensor's state: read like any amount that is no number."""
    units = parse_portfolio([_asset_entry(VSN, "NaN", "1.0")])
    assert (units.holdings, units.unparsed_assets) == ({}, {VSN})
    value = parse_portfolio([_asset_entry(VSN, "1.0", "1.0", value="Infinity")])
    assert value.holdings[VSN].value is None
    assert parse_portfolio([_fiat_entry("NaN")]).cash is None


def test_an_unparsable_holding_makes_total_and_cash_plus_unknown():
    data = parse_portfolio(
        [
            _asset_entry(VSN, "100.0", "25.0", "200.00"),
            {"asset_id": BCPEUR, "balance": {"value": "x"}},
        ]
    )
    data.assets = {VSN: {"id": VSN, "group": "token"}}
    assert data.total is None
    assert data.cash_plus is None
    assert data.wallet_ids == [VSN]


def test_an_answer_lists_nothing_only_without_any_asset_or_fiat_entry():
    """An unreadable entry is still listed; one of no documented shape is not."""
    assert lists_nothing([])
    assert lists_nothing([{"something": "else"}])
    assert not lists_nothing([_fiat_entry("0.00")])
    assert not lists_nothing([{"asset_id": VSN, "balance": {"value": "x"}}])


def test_an_unparsable_fiat_balance_makes_cash_and_total_unknown():
    data = parse_portfolio(
        [
            _asset_entry(VSN, "100.0", "25.0", "200.00"),
            {"currency_id": EUR_ID, "balance": {"value": "x"}},
        ]
    )
    assert data.cash is None
    assert data.total is None


# --- PortfolioData: total, Cash Plus, wallets -----------------------------------


def _data(assets: dict) -> PortfolioData:
    data = parse_portfolio(
        [
            _asset_entry(VSN, "100.0", "25.0", "200.00"),
            _asset_entry(BCPEUR, "50.0", "50.0", "50.00"),
            _fiat_entry("10.00"),
        ]
    )
    data.assets = assets
    return data


def test_total_is_the_whole_account():
    assert _data({}).total == 260.0


def test_total_is_unknown_when_a_holding_has_no_value():
    data = parse_portfolio([_asset_entry(VSN, "1.0", "1.0", value=None), _fiat_entry("5.00")])
    assert data.total is None


def test_cash_plus_needs_every_holding_classified():
    assert _data({VSN: {"id": VSN, "group": "token"}}).cash_plus is None


def test_cash_plus_sums_fiat_earn_holdings():
    data = _data(
        {VSN: {"id": VSN, "group": "token"}, BCPEUR: {"id": BCPEUR, "group": "fiat_earn"}}
    )
    assert data.cash_plus == 50.0
    assert data.wallet_ids == [VSN]


def test_cash_plus_is_zero_without_cash_plus_holdings():
    data = parse_portfolio([_asset_entry(VSN, "1.0", "1.0", "5.00")])
    data.assets = {VSN: {"id": VSN, "group": "token"}}
    assert data.cash_plus == 0.0
    # A float, as every other figure: the sensor's state reads "0.0", not "0".
    assert isinstance(data.cash_plus, float)


def test_a_holding_the_catalogue_does_not_list_is_no_cash_plus():
    """Bitpanda's catalogue lists its Cash Plus products: a holding it
    answered without is none, so Cash Plus has its value. The holding still
    gets no wallet -- nothing names it."""
    data = _data({BCPEUR: _cash_plus_asset(BCPEUR, "BCPEUR")})
    data.unlisted = {VSN}
    assert data.cash_plus == 50.0
    assert data.cash_plus_amounts == {"eur": 50.0}
    assert data.wallet_ids == []


def test_unresolved_holding_is_no_wallet():
    data = _data({BCPEUR: {"id": BCPEUR, "group": "fiat_earn"}})
    assert data.is_cash_plus(VSN) is None
    assert data.wallet_ids == []


# --- PortfolioData: cash_plus_amounts ---------------------------------------------


def _cash_plus_asset(asset_id: str, symbol: str) -> dict:
    return {"id": asset_id, "symbol": symbol, "group": "fiat_earn"}


def test_cash_plus_amounts_reports_the_held_products_own_units():
    data = parse_portfolio([_asset_entry(BCPEUR, "100.0", "100.0", "114.20")])
    data.assets = {BCPEUR: _cash_plus_asset(BCPEUR, "BCPEUR")}
    assert data.cash_plus_amounts == {"eur": 100.0}


def test_cash_plus_amounts_has_one_key_per_held_product():
    data = parse_portfolio(
        [
            _asset_entry(BCPEUR, "100.0", "100.0", "100.00"),
            _asset_entry(BCPUSD, "50.0", "50.0", "43.12"),
            _asset_entry(BCPGBP, "25.0", "25.0", "28.80"),
        ]
    )
    data.assets = {
        BCPEUR: _cash_plus_asset(BCPEUR, "BCPEUR"),
        BCPUSD: _cash_plus_asset(BCPUSD, "BCPUSD"),
        BCPGBP: _cash_plus_asset(BCPGBP, "BCPGBP"),
    }
    assert data.cash_plus_amounts == {"eur": 100.0, "usd": 50.0, "gbp": 25.0}


def test_cash_plus_amounts_uses_the_whole_symbol_for_a_non_standard_product():
    """A future Cash Plus product not shaped BCP + three letters falls back
    to its whole symbol, lowercased, rather than being dropped."""
    data = parse_portfolio([_asset_entry(BCPEUR, "10.0", "10.0", "10.00")])
    data.assets = {BCPEUR: _cash_plus_asset(BCPEUR, "BCPX")}
    assert data.cash_plus_amounts == {"bcpx": 10.0}


def test_cash_plus_amounts_reads_only_ascii_letters_as_a_currency_code():
    """`BCP` plus three ASCII letters names a currency; other letters do not,
    and the whole symbol stands in."""
    data = parse_portfolio([_asset_entry(BCPEUR, "10.0", "10.0", "10.00")])
    data.assets = {BCPEUR: _cash_plus_asset(BCPEUR, "BCPÄÖÜ")}
    assert data.cash_plus_amounts == {"bcpäöü": 10.0}


def test_cash_plus_amounts_is_empty_without_cash_plus_holdings():
    data = parse_portfolio([_asset_entry(VSN, "1.0", "1.0", "5.00")])
    data.assets = {VSN: {"id": VSN, "group": "token"}}
    assert data.cash_plus_amounts == {}


def test_cash_plus_amounts_is_unknown_with_an_unclassified_holding():
    assert _data({VSN: {"id": VSN, "group": "token"}}).cash_plus_amounts is None


def test_cash_plus_amounts_is_unknown_with_an_unparsed_entry():
    data = parse_portfolio(
        [
            _asset_entry(VSN, "100.0", "25.0", "200.00"),
            {"asset_id": BCPEUR, "balance": {"value": "x"}},
        ]
    )
    data.assets = {VSN: {"id": VSN, "group": "token"}}
    assert data.cash_plus_amounts is None


def test_a_cash_plus_holding_without_a_value_makes_cash_plus_unknown():
    """A holding may come without `currency_balance`: its value is unknown.
    For Cash Plus that makes the sum unknown, and the amounts with it -- never
    one without the other. The wallets are unaffected."""
    data = parse_portfolio(
        [
            _asset_entry(BCPEUR, "50.0", "50.0", value=None),
            _asset_entry(VSN, "1.0", "1.0", "5.00"),
        ]
    )
    data.assets = {
        BCPEUR: _cash_plus_asset(BCPEUR, "BCPEUR"),
        VSN: {"id": VSN, "group": "token"},
    }
    assert data.cash_plus is None
    assert data.cash_plus_amounts is None
    assert data.wallet_ids == [VSN]


# --- PortfolioData: what the answer lists ------------------------------------------


def test_the_figures_follow_what_the_answer_lists():
    """Each figure depends on its own entry: Total value on any entry at all,
    Cash on a fiat entry, Cash Plus on a holding of the group `fiat_earn`."""
    nothing = {"total": False, "cash": False, "cash_plus": False}
    empty = parse_portfolio([])
    assert empty.figures_listed() == nothing
    # Keyed as the figures are: the coordinator looks each one up by its key.
    assert set(empty.figures_listed()) == set(PORTFOLIO_FIGURES)

    fiat = parse_portfolio([_fiat_entry("5.00")])
    assert fiat.figures_listed() == {"total": True, "cash": True, "cash_plus": False}

    token = parse_portfolio([_asset_entry(VSN, "1.0", "1.0", "5.00")])
    token.assets = {VSN: {"id": VSN, "group": "token"}}
    assert token.figures_listed() == {"total": True, "cash": False, "cash_plus": False}

    cash_plus = parse_portfolio([_asset_entry(BCPEUR, "1.0", "1.0", "1.00")])
    cash_plus.assets = {BCPEUR: _cash_plus_asset(BCPEUR, "BCPEUR")}
    assert cash_plus.figures_listed() == {"total": True, "cash": False, "cash_plus": True}

    # An entry of no shape this endpoint documents is no entry at all.
    assert parse_portfolio([{"something": "else"}]).figures_listed() == nothing


def test_data_built_by_hand_lists_nothing_and_waits_for_nothing():
    """What the sensors read of data built by hand, before the coordinator
    tells which figures wait."""
    data = PortfolioData()
    assert data.figures_listed() == {"total": False, "cash": False, "cash_plus": False}
    assert data.waiting == frozenset()


def test_only_cash_plus_can_be_in_doubt():
    """An entry that is listed but cannot be read is there for Total value,
    and a fiat one for Cash: an unreadable entry is no sign of a sale. Cash
    Plus alone can be in doubt (None): a holding that cannot be read, or
    that no record classifies yet, might or might not be one. Only a holding
    the catalogue does not list is sure to be no Cash Plus."""
    fiat = parse_portfolio([{"currency_id": EUR_ID, "balance": {"value": "x"}}])
    assert fiat.cash is None
    assert fiat.listed_fiat is True

    unreadable = parse_portfolio([{"asset_id": BCPEUR, "balance": {"value": "x"}}])
    assert unreadable.figures_listed() == {"total": True, "cash": False, "cash_plus": None}

    unclassified = parse_portfolio([_asset_entry(VSN, "1.0", "1.0", "5.00")])
    assert unclassified.listed_cash_plus is None
    unclassified.unlisted = {VSN}
    assert unclassified.listed_cash_plus is False


# --- Returns: a timeframe whose own request fails ----------------------------------

_I = timedelta(minutes=5)
_T0 = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
# A refresh in which the week's own request failed and the day answered.
_WEEK_FAILED = PortfolioReturns(values={"DAY": 1.0}, failed=frozenset({"WEEK"}))


def test_a_failing_timeframe_keeps_its_last_return_until_confirmed():
    """At the regular pace the week keeps its last return through two
    failures of its own; the third, two intervals after the first, confirms
    the failure."""
    streaks = {}
    returns = PortfolioReturns(values={"DAY": 1.0, "WEEK": 2.0})
    for at in (_T0, _T0 + _I):
        returns = tolerate_failed_timeframes(_WEEK_FAILED, returns, streaks, at, _I)
        assert returns == PortfolioReturns(values={"DAY": 1.0, "WEEK": 2.0})
    returns = tolerate_failed_timeframes(_WEEK_FAILED, returns, streaks, _T0 + 2 * _I, _I)
    assert returns == PortfolioReturns(values={"DAY": 1.0}, failed=frozenset({"WEEK"}))


def test_a_timeframe_answered_without_a_figure_stays_unknown_while_it_fails():
    """Bitpanda answered for the month without a usable figure, then the
    month's own requests fail: there is no figure to keep, yet no failure is
    confirmed either -- unknown, until the third failure confirms it."""
    month_failed = PortfolioReturns(values={"DAY": 1.0}, failed=frozenset({"MONTH"}))
    streaks = {}
    returns = PortfolioReturns(values={"DAY": 1.0})
    for at in (_T0, _T0 + _I):
        returns = tolerate_failed_timeframes(month_failed, returns, streaks, at, _I)
        assert returns == PortfolioReturns(values={"DAY": 1.0})
    returns = tolerate_failed_timeframes(month_failed, returns, streaks, _T0 + 2 * _I, _I)
    assert returns == PortfolioReturns(values={"DAY": 1.0}, failed=frozenset({"MONTH"}))


def test_a_timeframe_without_a_last_return_fails_at_once():
    """Nothing to keep: there was no refresh before -- the first one after
    setup -- or the week had failed in it as well."""
    for previous in (None, PortfolioReturns(values={"DAY": 1.0}, failed=frozenset({"WEEK"}))):
        returns = tolerate_failed_timeframes(_WEEK_FAILED, previous, {}, _T0, _I)
        assert returns == PortfolioReturns(
            values={"DAY": 1.0}, failed=frozenset({"WEEK"})
        ), previous


@pytest.mark.parametrize(
    "answer", [{"DAY": 1.0, "WEEK": 3.0}, {"DAY": 1.0}], ids=["with_figure", "without_figure"]
)
def test_an_answer_ends_a_timeframes_streak(answer):
    """Fails, fails, answers, fails, fails, at the regular pace: four
    failures in five refreshes, never three in a row. The week never fails
    and keeps what it answered last -- an answer without a usable figure
    ends the streak as well."""
    streaks = {}
    returns = PortfolioReturns(values={"DAY": 1.0, "WEEK": 2.0})
    script = (
        _WEEK_FAILED, _WEEK_FAILED, PortfolioReturns(values=answer), _WEEK_FAILED, _WEEK_FAILED
    )
    for step, result in enumerate(script):
        returns = tolerate_failed_timeframes(result, returns, streaks, _T0 + step * _I, _I)
        assert "WEEK" not in returns.failed, step
    assert returns == PortfolioReturns(values=answer)


# --- A Portfolio figure whose entry vanishes -------------------------------------

_STEP = PORTFOLIO_UPDATE_INTERVAL
# Two refreshes by hand, one right after the other (the cooldown between them
# is const.REFRESH_MIN_COOLDOWN, 10 seconds at the least).
_BY_HAND = timedelta(seconds=20)


def test_a_figure_missing_since_the_start_shows_0_at_once_and_counts_nothing():
    """It was never there to vanish: nothing to wait for, nothing to count."""
    watch = FigureWatch()
    for step in range(5):
        assert watch.observe(False, _T0 + step * _STEP) is False
    assert watch.misses == 0


def test_a_figure_that_disappears_waits_three_misses_ten_minutes_apart():
    watch = FigureWatch()
    assert watch.observe(True, _T0) is False
    assert watch.observe(False, _T0 + _STEP) is True
    assert watch.observe(False, _T0 + 2 * _STEP) is True
    # The third miss, ten minutes after the first, confirms it: 0.
    assert watch.observe(False, _T0 + 3 * _STEP) is False
    assert watch.observe(False, _T0 + 4 * _STEP) is False
    assert watch.misses == 0


def test_a_figure_back_while_waiting_clears_the_count():
    watch = FigureWatch()
    assert watch.observe(True, _T0) is False
    assert watch.observe(False, _T0 + _STEP) is True
    assert watch.observe(True, _T0 + 2 * _STEP) is False
    # Gone again: the next miss is the first, not the second.
    assert watch.observe(False, _T0 + 3 * _STEP) is True
    assert watch.observe(False, _T0 + 4 * _STEP) is True
    assert watch.observe(False, _T0 + 5 * _STEP) is False


def test_a_figure_that_came_back_counts_and_times_its_misses_afresh():
    """Time alone confirms nothing: ten minutes after its first miss, a second
    is still only the second. And each time the figure is back, the clock
    starts at the first of its next misses: answers by hand right after it
    never confirm it, however old the misses before."""
    watch = FigureWatch()
    assert watch.observe(True, _T0) is False
    assert watch.observe(False, _T0 + _STEP) is True
    assert watch.observe(True, _T0 + 2 * _STEP) is False
    assert watch.observe(False, _T0 + 3 * _STEP) is True
    assert watch.observe(False, _T0 + 5 * _STEP) is True
    assert watch.observe(True, _T0 + 6 * _STEP) is False
    for answer in range(3):
        assert watch.observe(False, _T0 + 7 * _STEP + answer * _BY_HAND) is True


def test_misses_by_hand_never_confirm_sooner():
    """Refreshing by hand brings answers in faster than the regular pace:
    however many lack the entry, 0 comes no sooner than ten minutes after
    the first."""
    watch = FigureWatch()
    assert watch.observe(True, _T0) is False
    for answer in range(6):
        assert watch.observe(False, _T0 + _STEP + answer * _BY_HAND) is True
    assert watch.observe(False, _T0 + 3 * _STEP) is False


def test_answers_a_hair_less_than_an_interval_apart_confirm_at_the_regular_pace():
    """The wall clock may read a hair less than an update interval between
    two regular refreshes: the third miss still confirms, as it does at
    the regular pace."""
    watch = FigureWatch()
    assert watch.observe(True, _T0) is False
    hair_less = _STEP - timedelta(seconds=1)
    assert watch.observe(False, _T0 + _STEP) is True
    assert watch.observe(False, _T0 + _STEP + hair_less) is True
    assert watch.observe(False, _T0 + _STEP + 2 * hair_less) is False


def test_a_figure_confirmed_empty_waits_again_only_after_it_came_back():
    """Once 0, it stays 0 while its entry stays missing: never `unavailable`
    again on its own."""
    watch = FigureWatch()
    assert watch.observe(True, _T0) is False
    assert watch.observe(False, _T0 + _STEP) is True
    assert watch.observe(False, _T0 + 2 * _STEP) is True
    assert watch.observe(False, _T0 + 3 * _STEP) is False
    assert watch.observe(False, _T0 + 4 * _STEP) is False
    assert watch.observe(True, _T0 + 5 * _STEP) is False
    assert watch.observe(False, _T0 + 6 * _STEP) is True


def test_doubt_never_makes_a_figure_there():
    """Cash Plus beside a holding that might be one: a figure that was not
    there before stays so -- the misses after the doubt count nothing and
    wait for nothing."""
    watch = FigureWatch()
    assert watch.observe(None, _T0) is False
    for step in range(1, 4):
        assert watch.observe(False, _T0 + step * _STEP) is False
    assert watch.misses == 0


def test_doubt_clears_a_running_count():
    """The doubt might be the entry that vanished: no miss, and the count
    starts afresh, so nothing waits. The figure was there, so the misses
    after the doubt wait again, from the first."""
    watch = FigureWatch()
    assert watch.observe(True, _T0) is False
    assert watch.observe(False, _T0 + _STEP) is True
    assert watch.observe(None, _T0 + 2 * _STEP) is False
    assert watch.misses == 0
    results = [watch.observe(False, _T0 + step * _STEP) for step in (3, 4, 5)]
    assert results == [True, True, False]


# --- Earn ------------------------------------------------------------------------


def test_parse_earn_configs_reads_apr_and_offered_assets():
    configs = load_fixture("earn-configs.json")
    earn = parse_earn_configs(configs)
    assert len(earn.offered) == 44
    first = configs[0]
    assert earn.apr[first["asset_id"]] == first["annual_percentage_rate"]


def test_parse_earn_configs_counts_sold_out_products_but_not_disabled_ones():
    earn = parse_earn_configs(
        [
            {"asset_id": "a", "annual_percentage_rate": 0.05, "enabled": True, "soldout": True},
            {"asset_id": "b", "annual_percentage_rate": 0.04, "enabled": False, "soldout": False},
            {"asset_id": "c", "annual_percentage_rate": True, "enabled": True},
        ]
    )
    assert earn.offered == frozenset({"a", "c"})
    # A boolean is not a rate, even though bool subclasses int.
    assert earn.apr == {"a": 0.05, "b": 0.04}


# --- When a wallet has a Staking sensor ------------------------------------------


def _holding(staked: float) -> Holding:
    return Holding(asset_id=VSN, balance=10.0, available=10.0 - staked, value=10.0)


def test_staking_applies_when_something_is_staked_even_without_earn_data():
    assert staking_applies(_holding(5.0), None) is True


def test_staking_applies_when_a_product_is_offered():
    assert staking_applies(_holding(0.0), EarnData(apr={}, offered=frozenset({VSN}))) is True


def test_staking_does_not_apply_without_stake_or_product():
    assert staking_applies(_holding(0.0), EarnData(apr={}, offered=frozenset())) is False


def test_staking_is_unknown_without_stake_and_without_earn_data():
    assert staking_applies(_holding(0.0), None) is None


# --- Rewards: sum_rewards and _is_later ----------------------------------------


def _reward(asset_id, gross, fee, credited_at, owner="staking-service"):
    return {
        "operation_id": f"op-{credited_at}-{asset_id}",
        "operation_type": "reward",
        "transactions": [
            {
                "asset_id": asset_id,
                "wallet_owner": owner,
                "asset_amount": {"value": gross},
                "fee_amount": {"value": fee},
                "credited_at": credited_at,
            }
        ],
    }


def test_sum_rewards_lists_each_payout_oldest_first():
    """Each payout of an asset, oldest first by time -- not by text: the
    API sends timestamps with and without milliseconds."""
    ops = [
        _reward("vsn", "10", "2", "2026-09-22T17:16:35Z"),
        _reward("vsn", "20", "4", "2026-09-09T18:31:22.080Z"),
        _reward("vsn", "30", "6", "2026-09-15T16:20:00Z"),
    ]
    totals = sum_rewards(ops)["vsn"]
    assert totals.payouts == (
        RewardPayout("2026-09-09T18:31:22.080Z", 20.0, 4.0, 16.0),
        RewardPayout("2026-09-15T16:20:00Z", 30.0, 6.0, 24.0),
        RewardPayout("2026-09-22T17:16:35Z", 10.0, 2.0, 8.0),
    )
    assert (totals.gross, totals.count, totals.last_at) == (60.0, 3, "2026-09-22T17:16:35Z")


def test_a_reward_without_credited_at_counts_in_the_totals_but_lists_no_payout():
    """A payout that cannot be placed in time cannot be told new or old."""
    totals = sum_rewards([_reward("vsn", "1", "0", None)])["vsn"]
    assert (totals.count, totals.payouts) == (1, ())


def test_payouts_after_compares_times_not_text():
    """35.080Z is after 35Z, though "." sorts before "Z"; no mark: all."""
    early = RewardPayout("2026-09-22T17:16:34.999Z", 1.0, 0.0, 1.0)
    later = RewardPayout("2026-09-22T17:16:35.080Z", 1.0, 0.0, 1.0)
    latest = RewardPayout("2026-09-22T17:17:00Z", 1.0, 0.0, 1.0)
    payouts = (early, later, latest)
    assert payouts_after(payouts, "2026-09-22T17:16:35Z") == [later, latest]
    assert payouts_after(payouts, None) == [early, later, latest]


def test_sum_rewards_totals_gross_fee_and_net():
    ops = [
        _reward("vsn", "20.68994769", "4.13798954", "2026-09-22T17:16:35Z"),
        _reward("vsn", "20.67399483", "4.13479897", "2026-09-15T17:16:25Z"),
    ]
    totals = sum_rewards(ops)["vsn"]
    assert abs(totals.gross - 41.36394252) < 1e-8
    assert abs(totals.fee - 8.27278851) < 1e-8
    assert abs(totals.net - (41.36394252 - 8.27278851)) < 1e-8
    assert totals.count == 2


def test_sum_rewards_rounds_to_eight_decimals():
    """Summing floats leaves noise such as 751.4920099999999 or
    0.30000000000000004; the amounts come from 8-decimal strings.
    """
    ops = [
        _reward("vsn", "0.1", "0.01", "2026-09-15T17:16:25Z"),
        _reward("vsn", "0.2", "0.02", "2026-09-22T17:16:35Z"),
    ]
    totals = sum_rewards(ops)["vsn"]
    assert totals.gross == 0.3
    assert totals.fee == 0.03
    assert totals.net == 0.27


def test_sum_rewards_records_latest_timestamp():
    ops = [
        _reward("vsn", "1", "0", "2026-09-15T17:16:25Z"),
        _reward("vsn", "1", "0", "2026-09-22T17:16:35Z"),
    ]
    assert sum_rewards(ops)["vsn"].last_at == "2026-09-22T17:16:35Z"


def test_sum_rewards_ignores_non_reward_operations():
    ops = [
        _reward("vsn", "1", "0", "2026-09-22T17:16:35Z"),
        {"operation_id": "o2", "operation_type": "buy",
         "transactions": [{"asset_id": "vsn", "asset_amount": {"value": "999"},
                           "fee_amount": {"value": "0"},
                           "credited_at": "2026-09-01T00:00:00Z"}]},
    ]
    assert sum_rewards(ops)["vsn"].gross == 1.0


def test_sum_rewards_ignores_cash_plus_interest():
    """earn_on_fiat_reward is Cash Plus interest, a different product."""
    ops = [{"operation_id": "o1", "operation_type": "earn_on_fiat_reward",
            "transactions": [{"asset_id": "eur", "wallet_owner": "shared-default",
                              "asset_amount": {"value": "0.01"},
                              "fee_amount": {"value": "0"},
                              "credited_at": "2026-01-05T17:46:04Z"}]}]
    assert sum_rewards(ops) == {}


def test_sum_rewards_tolerates_unknown_operation_type():
    """29 types were observed in one account. The enum is open."""
    ops = [{"operation_id": "o1", "operation_type": "brand_new_type",
            "transactions": []}]
    assert sum_rewards(ops) == {}


def test_sum_rewards_survives_a_reward_without_transactions():
    """`transactions: null` is a reward with nothing to count, not an error
    that would stop every later rewards refresh while it stays in the
    history."""
    assert sum_rewards([{"operation_type": "reward", "transactions": None}]) == {}


def test_sum_rewards_picks_the_later_timestamp_across_formats():
    """Same second, one with a fraction and one without — string compare fails here."""
    ops = [
        _reward("vsn", "1", "0", "2026-09-22T17:16:35Z"),
        _reward("vsn", "1", "0", "2026-09-22T17:16:35.500Z"),
    ]
    assert sum_rewards(ops)["vsn"].last_at == "2026-09-22T17:16:35.500Z"


def test_sum_rewards_ignores_a_reward_from_another_wallet_owner():
    """Both conditions are required: operation_type AND wallet_owner."""
    ops = [
        _reward("vsn", "5", "1", "2026-09-22T17:16:35Z"),
        _reward("vsn", "99", "0", "2026-09-21T00:00:00Z", owner="shared-default"),
    ]
    totals = sum_rewards(ops)["vsn"]
    assert totals.count == 1
    assert abs(totals.gross - 5.0) < 1e-9


def test_is_later_ignores_empty_timestamps():
    """The pre-fix code guarded with `if credited`; an empty string must not win."""
    assert _is_later("", None) is False
    assert _is_later("", "2026-09-22T17:16:35Z") is False
    assert _is_later("2026-09-22T17:16:35Z", "") is True


def test_is_later_survives_a_mixed_timezone_batch():
    """A zone-less timestamp must not raise out of a coordinator refresh."""
    result = _is_later("2026-09-22T17:16:35", "2026-09-21T00:00:00Z")
    assert isinstance(result, bool)


def test_is_later_survives_a_non_string():
    result = _is_later(12345, "2026-09-21T00:00:00Z")
    assert isinstance(result, bool)
