"""Tests for price sensor display precision."""
from custom_components.bitpanda.coordinator import PortfolioData
from custom_components.bitpanda.sensor import BitpandaPriceSensor

# ---------------------------------------------------------------------------
# BitpandaPriceSensor.extra_state_attributes — conversion attribute
#
# `self._portfolio.data` is None until PortfolioCoordinator's first
# successful refresh. Gating the whole conversion block on that truthiness,
# in addition to the currency, silently drops the block during that window
# for a non-EUR sensor: no conversion_rate, and no "unavailable" message
# either — an unconverted EUR price with nothing indicating it.
# ---------------------------------------------------------------------------

_USD_RATE = 1.13755257  # the same measured USD rate used elsewhere in this suite

# PriceCoordinator publishes no ticker price without a rate for a non-EUR
# currency (see test_coordinator_price.py), so the attribute must not claim
# an EUR price is shown.
_NO_RATE_MESSAGE = (
    "unavailable - no cash, and no holding worth at least 50 EUR, in the "
    "portfolio to derive an exchange rate from, so prices that would have to "
    "be converted from EUR are not shown"
)


class _FakeCoordinator:
    """Duck-typed stand-in exposing what CoordinatorEntity/the entity read."""

    def __init__(self, data=None, last_update_success=True):
        self.data = data
        self.last_update_success = last_update_success


class _FakeConfigEntry:
    entry_id = "entry1"


def _price_sensor(*, currency, portfolio_data):
    price_coordinator = _FakeCoordinator(data={})
    portfolio_coordinator = _FakeCoordinator(data=portfolio_data)
    return BitpandaPriceSensor(
        price_coordinator, portfolio_coordinator, _FakeConfigEntry(),
        asset={"id": "a1", "symbol": "BTC", "name": "Bitcoin"},
        currency=currency,
    )


def test_conversion_omitted_for_eur_when_rate_present():
    sensor = _price_sensor(currency="EUR", portfolio_data=PortfolioData(rate=_USD_RATE))
    attrs = sensor.extra_state_attributes
    assert "conversion" not in attrs
    assert "conversion_rate" not in attrs
    assert "conversion_source" not in attrs


def test_conversion_omitted_for_eur_when_portfolio_data_is_none():
    sensor = _price_sensor(currency="EUR", portfolio_data=None)
    attrs = sensor.extra_state_attributes
    assert "conversion" not in attrs
    assert "conversion_rate" not in attrs
    assert "conversion_source" not in attrs


def test_conversion_rate_present_for_non_eur_when_rate_is_known():
    sensor = _price_sensor(currency="USD", portfolio_data=PortfolioData(rate=_USD_RATE))
    attrs = sensor.extra_state_attributes
    assert attrs["conversion_rate"] == round(_USD_RATE, 8)
    assert attrs["conversion_source"] == "bitpanda-portfolio"
    assert "conversion" not in attrs


def test_conversion_message_for_non_eur_when_rate_is_none():
    sensor = _price_sensor(currency="USD", portfolio_data=PortfolioData(rate=None))
    attrs = sensor.extra_state_attributes
    assert attrs["conversion"] == _NO_RATE_MESSAGE
    assert "conversion_rate" not in attrs
    # No EUR figure is ever published under the USD unit.
    assert sensor.native_value is None
    assert sensor.native_unit_of_measurement == "USD"


def test_conversion_message_for_non_eur_when_portfolio_data_is_none():
    """Regression: before the coordinator's first refresh, `.data` is None.

    Gating on `portfolio` truthiness as well as currency dropped this whole
    block silently. A non-EUR user must still see the "unavailable" message,
    not an unconverted EUR price with no indication at all.
    """
    sensor = _price_sensor(currency="USD", portfolio_data=None)
    attrs = sensor.extra_state_attributes
    assert attrs["conversion"] == _NO_RATE_MESSAGE
    assert "conversion_rate" not in attrs
