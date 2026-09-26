"""The bitpanda.refresh action: registered once with the integration,
throttled to the ticker interval, and failing when a refresh fails.

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
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.service import async_get_all_descriptions
from homeassistant.helpers.translation import async_get_translations
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import yaml

from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.portfolio_coordinator import PortfolioRuntime
from custom_components.bitpanda.price_coordinator import PriceTrackerRuntime


class _Coordinator:
    """What the action touches: the update interval, which sets the
    cooldown, and the refresh, whose outcome `last_update_success` tells --
    as DataUpdateCoordinator.async_refresh leaves it, which never raises."""

    def __init__(self, interval: timedelta, *, fails: bool = False) -> None:
        self.update_interval = interval
        self.fails = fails
        self.last_update_success = True
        self.async_refresh = AsyncMock(side_effect=self._refresh)
        # The debounced request, which swallows the outcome: never the one used.
        self.async_request_refresh = AsyncMock()

    async def _refresh(self) -> None:
        self.last_update_success = not self.fails


class _Clock:
    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


_TITLES = {"portfolio": "Bitpanda Portfolio", "price_tracker": "Bitpanda Price Tracker"}


def _loaded(hass, entry_type: str, runtime) -> MockConfigEntry:
    """An entry of `entry_type` as a finished setup leaves it: loaded, with
    `runtime` as its runtime data, under the service's own title."""
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, title=_TITLES[entry_type], data={"entry_type": entry_type}
    )
    entry.add_to_hass(hass)
    entry.runtime_data = runtime
    entry.mock_state(hass, ConfigEntryState.LOADED)
    return entry


def _portfolio_runtime(portfolio: _Coordinator) -> PortfolioRuntime:
    return PortfolioRuntime(
        portfolio=portfolio, history=None, earn=None, rewards=None,
        group_titles={}, data_at_setup={}, options_at_setup={},
    )


async def _set_up_the_integration(hass) -> None:
    """What Home Assistant does before it sets up the first entry: the
    integration's own async_setup. Entries are added after it, so none of
    them is set up for real."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()


async def _register(
    hass,
    ticker_interval: timedelta,
    *,
    portfolio_fails: bool = False,
    tickers_fail: bool = False,
):
    await _set_up_the_integration(hass)
    portfolio = _Coordinator(timedelta(minutes=5), fails=portfolio_fails)
    tickers = _Coordinator(ticker_interval, fails=tickers_fail)
    _loaded(hass, "portfolio", _portfolio_runtime(portfolio))
    _loaded(hass, "price_tracker", PriceTrackerRuntime(tickers=tickers, ecb=None))
    return portfolio, tickers


async def _call(hass) -> None:
    await hass.services.async_call(DOMAIN, "refresh", blocking=True)


async def test_refresh_reaches_both_services_and_is_throttled(hass):
    portfolio, tickers = await _register(hass, timedelta(seconds=60))
    clock = _Clock(1000.0)
    with patch("custom_components.bitpanda.monotonic", clock):
        await _call(hass)
        clock.now += 15
        await _call(hass)
        clock.now += 46
        await _call(hass)
    assert tickers.async_refresh.await_count == 2
    assert portfolio.async_refresh.await_count == 2


async def test_cooldown_follows_a_stretched_ticker_interval(hass):
    _, tickers = await _register(hass, timedelta(seconds=120))
    clock = _Clock(1000.0)
    with patch("custom_components.bitpanda.monotonic", clock):
        await _call(hass)
        clock.now += 61
        await _call(hass)
        clock.now += 60
        await _call(hass)
    assert tickers.async_refresh.await_count == 2


async def test_cooldown_never_drops_below_ten_seconds(hass):
    _, tickers = await _register(hass, timedelta(seconds=5))
    clock = _Clock(1000.0)
    with patch("custom_components.bitpanda.monotonic", clock):
        await _call(hass)
        clock.now += 6
        await _call(hass)
        clock.now += 5
        await _call(hass)
    assert tickers.async_refresh.await_count == 2


async def test_first_refresh_is_accepted_right_after_boot(hass):
    _, tickers = await _register(hass, timedelta(seconds=60))
    with patch("custom_components.bitpanda.monotonic", _Clock(5.0)):
        await _call(hass)
    assert tickers.async_refresh.await_count == 1


async def test_only_the_loaded_services_are_refreshed(hass):
    """An entry that is not loaded -- setup failed or is being retried --
    has nothing to refresh; the loaded one is refreshed as usual."""
    await _set_up_the_integration(hass)
    portfolio = _Coordinator(timedelta(minutes=5))
    _loaded(hass, "portfolio", _portfolio_runtime(portfolio))
    MockConfigEntry(
        domain=DOMAIN, version=3, data={"entry_type": "price_tracker"},
        state=ConfigEntryState.SETUP_RETRY,
    ).add_to_hass(hass)
    await _call(hass)
    assert portfolio.async_refresh.await_count == 1


# --- A refresh that fails fails the call ---------------------------------------------


async def test_the_call_waits_for_the_refresh_itself(hass):
    """Not the debounced request, which swallows the outcome: the refresh,
    awaited, so the call knows whether it worked."""
    portfolio, tickers = await _register(hass, timedelta(seconds=60))
    await _call(hass)
    for coordinator in (portfolio, tickers):
        assert coordinator.async_refresh.await_count == 1
        coordinator.async_request_refresh.assert_not_awaited()


def _refresh_failed(services: str) -> str:
    """The English text of the error, its trailing "." dropped, as Home
    Assistant renders a translated exception."""
    return f"Refresh failed for {services}"


async def test_a_failed_refresh_fails_the_call_and_names_the_service(hass):
    """A HomeAssistantError -- the call was right, the refresh failed --
    translated, with the service's title as the placeholder: the frontend
    shows it in the user's language, the log and automation traces in
    English. The other service is refreshed all the same."""
    portfolio, tickers = await _register(hass, timedelta(seconds=60), portfolio_fails=True)
    with pytest.raises(HomeAssistantError) as excinfo:
        await _call(hass)
    assert not isinstance(excinfo.value, ServiceValidationError)
    assert (
        excinfo.value.translation_domain,
        excinfo.value.translation_key,
        excinfo.value.translation_placeholders,
    ) == (DOMAIN, "refresh_failed", {"services": "Bitpanda Portfolio"})
    assert str(excinfo.value) == _refresh_failed("Bitpanda Portfolio")
    assert excinfo.value.__cause__ is None
    assert tickers.async_refresh.await_count == 1


async def test_a_failed_price_refresh_is_named_too(hass):
    _, tickers = await _register(hass, timedelta(seconds=60), tickers_fail=True)
    with pytest.raises(HomeAssistantError) as excinfo:
        await _call(hass)
    assert excinfo.value.translation_placeholders == {"services": "Bitpanda Price Tracker"}


async def test_two_failed_refreshes_are_named_together(hass):
    await _register(hass, timedelta(seconds=60), portfolio_fails=True, tickers_fail=True)
    with pytest.raises(HomeAssistantError) as excinfo:
        await _call(hass)
    assert excinfo.value.translation_placeholders == {
        "services": "Bitpanda Portfolio, Bitpanda Price Tracker"
    }
    assert str(excinfo.value) == _refresh_failed("Bitpanda Portfolio, Bitpanda Price Tracker")


async def test_a_service_is_named_by_the_title_its_entry_carries(hass):
    """The title the integration page shows, renamed by the user or not."""
    await _set_up_the_integration(hass)
    entry = _loaded(hass, "portfolio", _portfolio_runtime(
        _Coordinator(timedelta(minutes=5), fails=True)
    ))
    hass.config_entries.async_update_entry(entry, title="My Bitpanda")
    with pytest.raises(HomeAssistantError) as excinfo:
        await _call(hass)
    assert excinfo.value.translation_placeholders == {"services": "My Bitpanda"}


async def test_a_call_within_the_cooldown_stays_silent_after_a_failed_one(hass):
    """The failed refresh still asked Bitpanda, so it starts the cooldown
    like any other; a call within it refreshes nothing and says nothing."""
    portfolio, _ = await _register(hass, timedelta(seconds=60), portfolio_fails=True)
    clock = _Clock(1000.0)
    with patch("custom_components.bitpanda.monotonic", clock):
        with pytest.raises(HomeAssistantError):
            await _call(hass)
        clock.now += 30
        await _call(hass)
    assert portfolio.async_refresh.await_count == 1


# --- Registered with the integration, not with an entry ----------------------------


async def test_the_action_exists_before_any_entry_is_loaded(hass):
    """So an automation that uses it validates while setup fails or is
    retried."""
    await _set_up_the_integration(hass)
    assert hass.services.has_service(DOMAIN, "refresh")


_NOTHING_TO_REFRESH = (
    "There is nothing to refresh: neither Bitpanda Portfolio nor Bitpanda Price "
    "Tracker is loaded"
)


async def test_a_call_with_nothing_loaded_says_so(hass):
    """Translated: the frontend shows a validation error in the user's
    language; its English text -- the trailing "." dropped, as Home
    Assistant renders it -- goes to the log."""
    await _set_up_the_integration(hass)
    with pytest.raises(ServiceValidationError) as excinfo:
        await _call(hass)
    assert (excinfo.value.translation_domain, excinfo.value.translation_key) == (
        DOMAIN, "nothing_to_refresh"
    )
    assert excinfo.value.translation_placeholders is None
    assert str(excinfo.value) == _NOTHING_TO_REFRESH


async def test_a_refused_call_starts_no_cooldown(hass):
    """Nothing was refreshed, so the next call -- once an entry has loaded --
    goes through at once."""
    await _set_up_the_integration(hass)
    clock = _Clock(1000.0)
    with patch("custom_components.bitpanda.monotonic", clock):
        with pytest.raises(ServiceValidationError):
            await _call(hass)
        tickers = _Coordinator(timedelta(seconds=60))
        _loaded(hass, "price_tracker", PriceTrackerRuntime(tickers=tickers, ecb=None))
        clock.now += 1
        await _call(hass)
    assert tickers.async_refresh.await_count == 1


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
    await _register(hass, timedelta(seconds=60))
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
