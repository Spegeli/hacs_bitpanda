"""The bitpanda.refresh service is throttled to the ticker interval.

Every accepted call costs a portfolio request plus one ticker request per
tracked asset; the ticker interval is what keeps the latter inside the
self-imposed budget, so the cooldown follows it and never drops below 10 s.
The clock is the module's own `monotonic` name, patched there alone.
"""
from datetime import timedelta
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers.service import async_get_all_descriptions
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant_custom_component.common import MockConfigEntry
import yaml

from custom_components.bitpanda import _async_register_refresh_service
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.portfolio_coordinator import PortfolioRuntime
from custom_components.bitpanda.price_coordinator import PriceTrackerRuntime


class _Coordinator:
    def __init__(self, interval: timedelta) -> None:
        self.update_interval = interval
        self.async_request_refresh = AsyncMock()


class _Clock:
    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def _register(hass, ticker_interval: timedelta):
    portfolio = _Coordinator(timedelta(minutes=5))
    tickers = _Coordinator(ticker_interval)
    for entry_type, runtime in (
        (
            "portfolio",
            PortfolioRuntime(
                portfolio=portfolio, history=None, earn=None, rewards=None,
                group_titles={}, data_at_setup={}, options_at_setup={},
            ),
        ),
        ("price_tracker", PriceTrackerRuntime(tickers=tickers, ecb=None)),
    ):
        entry = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": entry_type})
        entry.add_to_hass(hass)
        entry.runtime_data = runtime
        entry.mock_state(hass, ConfigEntryState.LOADED)
    _async_register_refresh_service(hass)
    return portfolio, tickers


async def _call(hass) -> None:
    await hass.services.async_call(DOMAIN, "refresh", blocking=True)


async def test_refresh_reaches_both_services_and_is_throttled(hass):
    portfolio, tickers = _register(hass, timedelta(seconds=60))
    clock = _Clock(1000.0)
    with patch("custom_components.bitpanda.monotonic", clock):
        await _call(hass)
        clock.now += 15
        await _call(hass)
        clock.now += 46
        await _call(hass)
    assert tickers.async_request_refresh.await_count == 2
    assert portfolio.async_request_refresh.await_count == 2


async def test_cooldown_follows_a_stretched_ticker_interval(hass):
    _, tickers = _register(hass, timedelta(seconds=120))
    clock = _Clock(1000.0)
    with patch("custom_components.bitpanda.monotonic", clock):
        await _call(hass)
        clock.now += 61
        await _call(hass)
        clock.now += 60
        await _call(hass)
    assert tickers.async_request_refresh.await_count == 2


async def test_cooldown_never_drops_below_ten_seconds(hass):
    _, tickers = _register(hass, timedelta(seconds=5))
    clock = _Clock(1000.0)
    with patch("custom_components.bitpanda.monotonic", clock):
        await _call(hass)
        clock.now += 6
        await _call(hass)
        clock.now += 5
        await _call(hass)
    assert tickers.async_request_refresh.await_count == 2


async def test_first_refresh_is_accepted_right_after_boot(hass):
    _, tickers = _register(hass, timedelta(seconds=60))
    with patch("custom_components.bitpanda.monotonic", _Clock(5.0)):
        await _call(hass)
    assert tickers.async_request_refresh.await_count == 1


_BITPANDA_DIR = Path(__file__).parent.parent / "custom_components" / "bitpanda"
_SERVICES_YAML = _BITPANDA_DIR / "services.yaml"
# Discovered from disk, the way the integration itself finds its shipped
# languages (language.async_shipped_languages): a new one is covered as soon as it
# exists, with no change to this test.
_LANGUAGES = sorted(path.stem for path in (_BITPANDA_DIR / "translations").glob("*.json"))


async def test_the_refresh_service_is_named_and_described_in_every_language(hass):
    """Name and description are translations (`services.refresh`): the
    frontend shows them in the user's language -- Home Assistant 2025.5 also
    copies the English ones into its service descriptions, later versions
    leave that to the frontend. services.yaml only declares the service.

    Looped over every shipped language rather than a couple hardcoded ones,
    each checked against its own translations file -- the source of truth
    for what it should say, guarded for content by tests/test_strings.py."""
    _register(hass, timedelta(seconds=60))
    assert (await async_get_all_descriptions(hass))[DOMAIN]["refresh"]["fields"] == {}
    name_key, description_key = (
        f"component.{DOMAIN}.services.refresh.name",
        f"component.{DOMAIN}.services.refresh.description",
    )
    for language in _LANGUAGES:
        raw = json.loads(
            (_BITPANDA_DIR / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )["services"]["refresh"]
        translations = await async_get_translations(hass, language, "services", {DOMAIN})
        assert (translations[name_key], translations[description_key]) == (
            raw["name"], raw["description"]
        )
    assert yaml.safe_load(_SERVICES_YAML.read_text(encoding="utf-8")) == {"refresh": None}
