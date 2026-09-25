"""Tests for the Portfolio data model."""
from custom_components.bitpanda.portfolio_model import (
    EarnData,
    Holding,
    PortfolioData,
    _is_later,
    parse_earn_configs,
    parse_portfolio,
    staking_applies,
    sum_rewards,
)

from tests.conftest import load_fixture

VSN = "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb"
BCPEUR = "1edf9721-e545-644c-9796-ae5b69a774d7"
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


def test_unresolved_holding_is_no_wallet():
    data = _data({BCPEUR: {"id": BCPEUR, "group": "fiat_earn"}})
    assert data.is_cash_plus(VSN) is None
    assert data.wallet_ids == []


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


# --- When a wallet has Staking and Total sensors ---------------------------------


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
