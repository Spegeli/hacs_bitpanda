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
