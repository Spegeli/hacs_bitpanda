"""Tests for the Price Tracker sensors."""
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.assets import slim_asset
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.ecb import EcbRates
from custom_components.bitpanda.price_coordinator import PriceTrackerRuntime
from custom_components.bitpanda.price_sensor import (
    PriceSensor,
    async_setup_price_entities,
    display_precision,
    price_device_info,
)

BTC = {"id": "b86c034b-efe3-11eb-b56f-0691764446a7", "symbol": "BTC", "name": "Bitcoin",
       "type": "cryptocoin", "group": "coin"}
GOLD = {"id": "b86c88d4-efe3-11eb-b56f-0691764446a7", "symbol": "XAU", "name": "Gold",
        "type": "commodity", "group": "metal"}
_RATES = EcbRates(date="2026-09-24", rates={"USD": 1.1367})


class _Coordinator:
    def __init__(self, data=None, last_update_success=True):
        self.data = data
        self.last_update_success = last_update_success


def _sensor(currency="EUR", prices=None, rates=_RATES, ecb=True):
    tickers = _Coordinator({BTC["id"]: 73188.51648958} if prices is None else prices)
    return PriceSensor(tickers, _Coordinator(rates) if ecb else None, "eid", BTC, currency)


def test_ids_names_and_device():
    sensor = _sensor("USD")
    assert sensor.entity_id == "sensor.bitpanda_bitcoin_btc_usd"
    assert sensor.unique_id == f"eid_{BTC['id']}_price_USD"
    assert sensor.name == "Bitcoin (BTC)/USD"
    assert sensor.native_unit_of_measurement == "USD"
    info = price_device_info("eid", BTC)
    assert info["name"] == "Bitcoin (BTC) Price Tracker"
    assert info["identifiers"] == {("bitpanda", f"eid_price_{BTC['id']}")}


def test_eur_is_the_ticker_price():
    sensor = _sensor("EUR", ecb=False)
    assert sensor.native_value == 73188.51648958
    assert sensor.extra_state_attributes == {
        "asset": "BTC", "asset_name": "Bitcoin", "trading_pair": "BTC/EUR",
    }


def test_other_currencies_are_converted_with_the_ecb_rate():
    sensor = _sensor("USD")
    assert sensor.native_value == round(73188.51648958 * 1.1367, 8)
    assert sensor.extra_state_attributes == {
        "asset": "BTC", "asset_name": "Bitcoin", "trading_pair": "BTC/USD",
        "conversion_rate": 1.1367, "rate_date": "2026-09-24", "rate_source": "ECB",
    }


def test_last_rates_are_used_after_a_failed_ecb_refresh():
    sensor = PriceSensor(
        _Coordinator({BTC["id"]: 100.0}), _Coordinator(_RATES, last_update_success=False),
        "eid", BTC, "USD",
    )
    assert sensor.native_value == 113.67
    assert sensor.extra_state_attributes["rate_date"] == "2026-09-24"


def test_without_rates_the_sensor_says_why_instead_of_showing_eur():
    sensor = _sensor("USD", rates=None)
    assert sensor.available is True
    assert sensor.native_value is None
    assert "conversion_rate" not in sensor.extra_state_attributes
    assert sensor.extra_state_attributes["conversion"]


def test_a_failing_ticker_makes_only_that_asset_unavailable():
    assert _sensor("EUR", prices={GOLD["id"]: 1.0}).available is False
    assert _sensor("EUR", prices={BTC["id"]: 1.0}).available is True


def test_change_24h_attributes_from_the_recorded_price():
    sensor = _sensor("EUR", prices={BTC["id"]: 110.0}, ecb=False)
    sensor._price_24h_ago = 100.0
    attrs = sensor.extra_state_attributes
    assert attrs["change_24h_pct"] == 10.0
    assert attrs["price_24h_ago"] == 100.0


def test_precision_follows_the_magnitude():
    assert _sensor("EUR", prices={BTC["id"]: 73188.5}, ecb=False).suggested_display_precision == 2
    assert _sensor("EUR", prices={BTC["id"]: 0.00000032}, ecb=False).suggested_display_precision == 8


# --- Platform setup ------------------------------------------------------------------


async def test_setup_adds_one_sensor_per_subentry_and_currency(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, data={"entry_type": "price_tracker"},
        options={"extra_currencies": ["USD"]},
        subentries_data=[
            ConfigSubentryData(data={"asset": slim_asset(a)}, subentry_type="asset",
                               title=a["name"], unique_id=a["id"])
            for a in (BTC, GOLD)
        ],
    )
    entry.add_to_hass(hass)
    entry.runtime_data = PriceTrackerRuntime(tickers=_Coordinator({}), ecb=_Coordinator(_RATES))
    calls: list = []
    await async_setup_price_entities(
        hass, entry, lambda entities, **kwargs: calls.append((entities, kwargs))
    )
    by_subentry = {
        kwargs["config_subentry_id"]: [e.entity_id for e in entities] for entities, kwargs in calls
    }
    subentry_ids = {s.unique_id: s.subentry_id for s in entry.subentries.values()}
    assert by_subentry[subentry_ids[BTC["id"]]] == [
        "sensor.bitpanda_bitcoin_btc_eur", "sensor.bitpanda_bitcoin_btc_usd",
    ]
    assert by_subentry[subentry_ids[GOLD["id"]]] == [
        "sensor.bitpanda_gold_xau_eur", "sensor.bitpanda_gold_xau_usd",
    ]


async def test_setup_removes_sensors_of_a_dropped_currency(hass):
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "price_tracker"},
                            options={"extra_currencies": []})
    entry.add_to_hass(hass)
    entry.runtime_data = PriceTrackerRuntime(tickers=_Coordinator({}), ecb=None)
    ent_reg = er.async_get(hass)
    usd = ent_reg.async_get_or_create("sensor", DOMAIN, f"{entry.entry_id}_{BTC['id']}_price_USD",
                                      config_entry=entry)
    eur = ent_reg.async_get_or_create("sensor", DOMAIN, f"{entry.entry_id}_{BTC['id']}_price_EUR",
                                      config_entry=entry)
    await async_setup_price_entities(hass, entry, lambda entities, **kwargs: None)
    assert ent_reg.async_get(usd.entity_id) is None
    assert ent_reg.async_get(eur.entity_id) is not None


# --- display_precision (moved from tests/test_sensor_price.py) -----------------------


def test_precision_for_large_values():
    assert display_precision(73331.48806018) == 2
    assert display_precision(29955.20592928) == 2
    assert display_precision(23.395) == 2
    assert display_precision(10.0) == 2


def test_precision_scales_down_for_small_values():
    assert display_precision(5.0) == 4
    assert display_precision(0.5) == 5
    assert display_precision(0.05810025) == 6
    assert display_precision(0.0005) == 7
    assert display_precision(0.00000032) == 8


def test_precision_never_derived_from_decimal_count():
    """Every API price has exactly 8 decimals, so counting them is useless."""
    assert display_precision(90.93000000) == 2


def test_precision_handles_zero_and_none():
    assert display_precision(0.0) == 2
    assert display_precision(None) == 2
