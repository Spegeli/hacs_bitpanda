"""Diagnostics of both services. The API key never appears."""
from datetime import timedelta
from types import SimpleNamespace

from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.diagnostics import async_get_config_entry_diagnostics
from custom_components.bitpanda.ecb import EcbRates
from custom_components.bitpanda.portfolio_model import EarnData, Holding, PortfolioData

_SECRET = "totally-secret-diagnostics-key"


class _Coordinator:
    def __init__(self, data=None, success=True, interval=None):
        self.data = data
        self.last_update_success = success
        self.update_interval = interval


def _portfolio_entry(hass, *, loaded: bool) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "entry_type": "portfolio",
            "api_key": _SECRET,
            "currency": "EUR",
            "currency_id": "b88b8466-efe3-11eb-b56f-0691764446a7",
            # A field added later must not leak by default either.
            "future_field": _SECRET,
        },
    )
    entry.add_to_hass(hass)
    if loaded:
        data = PortfolioData(
            holdings={"a": Holding("a", 1.0, 1.0, 5.0), "b": Holding("b", 1.0, 1.0, 5.0)}
        )
        data.assets = {"a": {"id": "a", "group": "coin"}}
        entry.runtime_data = SimpleNamespace(
            portfolio=_Coordinator(data),
            history=_Coordinator({"DAY": 1.0}),
            earn=_Coordinator(EarnData(apr={}, offered=frozenset({"a"}))),
            rewards=_Coordinator(None, success=False),
        )
        entry.mock_state(hass, ConfigEntryState.LOADED)
    return entry


async def test_portfolio_diagnostics_report_health_and_never_the_key(hass):
    result = await async_get_config_entry_diagnostics(hass, _portfolio_entry(hass, loaded=True))
    assert _SECRET not in repr(result)
    assert result["service"] == "portfolio"
    assert result["config"] == {"api_key": "**REDACTED**", "currency": "EUR"}
    assert result["coordinators"] == {
        "portfolio": {"last_update_success": True, "holdings": 2, "wallets": 1,
                      "unnamed_holdings": 1},
        "history": {"last_update_success": True, "timeframes": 1},
        "earn": {"last_update_success": True, "offered_assets": 1},
        "rewards": {"last_update_success": False, "assets_with_rewards": 0},
    }


async def test_portfolio_that_is_not_loaded_reports_its_config_only(hass):
    """Setup failed or reauth pending: exactly when diagnostics are wanted."""
    result = await async_get_config_entry_diagnostics(hass, _portfolio_entry(hass, loaded=False))
    assert _SECRET not in repr(result)
    assert result == {
        "service": "portfolio",
        "config": {"api_key": "**REDACTED**", "currency": "EUR"},
    }


def _price_entry(hass, *, extra, ecb) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={"entry_type": "price_tracker"},
        options={"extra_currencies": extra},
        subentries_data=[
            ConfigSubentryData(
                data={"asset": {"id": "uuid-btc", "symbol": "BTC", "name": "Bitcoin"}},
                subentry_type="asset",
                title="Bitcoin (BTC)",
                unique_id="uuid-btc",
            )
        ],
    )
    entry.add_to_hass(hass)
    entry.runtime_data = SimpleNamespace(
        tickers=_Coordinator({"uuid-btc": 1.0}, interval=timedelta(seconds=60)), ecb=ecb
    )
    entry.mock_state(hass, ConfigEntryState.LOADED)
    return entry


async def test_price_tracker_diagnostics(hass):
    ecb = _Coordinator(EcbRates(date="2026-09-24", rates={"USD": 1.1}))
    result = await async_get_config_entry_diagnostics(hass, _price_entry(hass, extra=["USD"], ecb=ecb))
    assert result == {
        "service": "price_tracker",
        "assets": ["BTC (uuid-btc)"],
        "currencies": ["EUR", "USD"],
        "tickers": {"last_update_success": True, "priced_assets": 1,
                    "update_interval_seconds": 60.0},
        "ecb": {"last_update_success": True, "rate_date": "2026-09-24"},
    }


async def test_price_tracker_without_extra_currencies_has_no_ecb(hass):
    result = await async_get_config_entry_diagnostics(hass, _price_entry(hass, extra=[], ecb=None))
    assert result["ecb"] is None
