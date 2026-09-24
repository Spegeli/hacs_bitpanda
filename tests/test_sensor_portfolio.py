"""Tests for the portfolio total sensor."""
from custom_components.bitpanda.coordinator import Holding, PortfolioData
from custom_components.bitpanda.sensor import (
    BitpandaPortfolioSensor,
    portfolio_breakdown,
)


def _h(asset_id, value):
    return Holding(asset_id=asset_id, balance=1.0, available=1.0,
                   staked=0.0, value=value)


def test_breakdown_uses_symbols_when_resolvable():
    data = PortfolioData(holdings={"uuid-btc": _h("uuid-btc", 100.0)})
    cache = {"uuid-btc": {"id": "uuid-btc", "symbol": "BTC"}}
    assert portfolio_breakdown(data, cache) == {"BTC": 100.0}


def test_breakdown_falls_back_to_asset_id_when_unresolved():
    data = PortfolioData(holdings={"uuid-x": _h("uuid-x", 5.0)})
    assert portfolio_breakdown(data, {}) == {"uuid-x": 5.0}


def test_breakdown_rounds_to_two_decimals():
    data = PortfolioData(holdings={"uuid-a": _h("uuid-a", 12.3456)})
    cache = {"uuid-a": {"id": "uuid-a", "symbol": "A"}}
    assert portfolio_breakdown(data, cache) == {"A": 12.35}


def test_breakdown_of_empty_portfolio_is_empty():
    assert portfolio_breakdown(PortfolioData(), {}) == {}


def test_breakdown_handles_none_data():
    assert portfolio_breakdown(None, {}) == {}


# ---------------------------------------------------------------------------
# BitpandaPortfolioSensor construction
#
# Same trick as the wallet and price sensors (Tasks 11 and 12): CoordinatorEntity
# only stores the coordinator, so the entity can be built and probed with
# duck-typed coordinator stand-ins and no running Home Assistant instance.
# ---------------------------------------------------------------------------


class _FakeCoordinator:
    """Duck-typed stand-in exposing what CoordinatorEntity/the entity read."""

    def __init__(self, data=None, last_update_success=True):
        self.data = data
        self.last_update_success = last_update_success


class _FakeConfigEntry:
    entry_id = "entry1"


def test_portfolio_native_value_is_none_when_coordinator_has_no_data():
    portfolio = _FakeCoordinator(data=None)
    history = _FakeCoordinator(data=None)
    sensor = BitpandaPortfolioSensor(
        portfolio, history, _FakeConfigEntry(), asset_cache={}, currency="EUR",
    )
    assert sensor.native_value is None


def test_portfolio_attributes_expose_timeframe_returns():
    data = PortfolioData(holdings={"uuid-btc": _h("uuid-btc", 100.0)}, total=100.0)
    portfolio = _FakeCoordinator(data=data)
    history = _FakeCoordinator(data={"DAY": -0.64, "YEAR": -60.55})
    sensor = BitpandaPortfolioSensor(
        portfolio, history, _FakeConfigEntry(),
        asset_cache={"uuid-btc": {"id": "uuid-btc", "symbol": "BTC"}},
        currency="EUR",
    )
    attrs = sensor.extra_state_attributes
    assert attrs["return_day_percent"] == -0.64
    assert attrs["return_year_percent"] == -60.55


# ---------------------------------------------------------------------------
# Code review follow-up (Task 13 review)
#
# 1. native_value is data.total, which parse_portfolio builds from holdings
#    AND data.fiat. portfolio_breakdown only iterates holdings, so uninvested
#    cash was never represented anywhere in the entity's attributes, and the
#    total would permanently exceed the sum of its own breakdown with nothing
#    explaining the gap.
# 2. portfolio_breakdown keyed its result by resolved symbol. The catalogue
#    is 14054 assets across crypto, stocks and ETFs with no guaranteed
#    symbol uniqueness across ids, so two ids sharing a symbol silently
#    dropped one holding from the breakdown.
# ---------------------------------------------------------------------------


def test_breakdown_disambiguates_a_symbol_collision():
    data = PortfolioData(holdings={"uuid-aaaa1111": _h("uuid-aaaa1111", 10.0),
                                   "uuid-bbbb2222": _h("uuid-bbbb2222", 20.0)})
    cache = {"x1": {"id": "uuid-aaaa1111", "symbol": "DUP"},
             "x2": {"id": "uuid-bbbb2222", "symbol": "DUP"}}
    result = portfolio_breakdown(data, cache)
    assert len(result) == 2
    assert sorted(result.values()) == [10.0, 20.0]


def test_portfolio_cash_attribute_reflects_uninvested_fiat_balance():
    data = PortfolioData(
        holdings={"uuid-btc": _h("uuid-btc", 100.0)},
        fiat={"eur-fiat": 0.01, "usd-fiat": 4.99},
        total=105.0,
    )
    portfolio = _FakeCoordinator(data=data)
    history = _FakeCoordinator(data=None)
    sensor = BitpandaPortfolioSensor(
        portfolio, history, _FakeConfigEntry(),
        asset_cache={"uuid-btc": {"id": "uuid-btc", "symbol": "BTC"}},
        currency="EUR",
    )
    attrs = sensor.extra_state_attributes
    assert attrs["cash"] == 5.0


def test_portfolio_cash_is_zero_not_absent_when_coordinator_has_no_data():
    portfolio = _FakeCoordinator(data=None)
    history = _FakeCoordinator(data=None)
    sensor = BitpandaPortfolioSensor(
        portfolio, history, _FakeConfigEntry(), asset_cache={}, currency="EUR",
    )
    attrs = sensor.extra_state_attributes
    assert "cash" in attrs
    assert attrs["cash"] is not None
    assert attrs["cash"] == 0.0


def _sensor(data, *, asset_cache=None):
    """Build a BitpandaPortfolioSensor with fake coordinators for a given
    portfolio data value ("no data", "holdings but no cash", "cash only")."""
    portfolio = _FakeCoordinator(data=data)
    history = _FakeCoordinator(data=None)
    return BitpandaPortfolioSensor(
        portfolio, history, _FakeConfigEntry(),
        asset_cache=asset_cache or {}, currency="EUR",
    )


def test_portfolio_cash_is_always_a_float():
    """sum({}.values()) is an int, and round() preserves the type."""
    for data in (None, PortfolioData(holdings={"a": _h("a", 5.0)}),
                 PortfolioData(fiat={"eur": 1.5, "usd": 2.25})):
        sensor = _sensor(data)
        assert isinstance(sensor.extra_state_attributes["cash"], float)
