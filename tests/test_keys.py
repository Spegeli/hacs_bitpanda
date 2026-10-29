"""keys.py: the Portfolio's API key, which both services use, and the one way
to ask for a new one."""
import pytest
from homeassistant.config_entries import (
    SOURCE_IGNORE,
    SOURCE_REAUTH,
    ConfigEntryDisabler,
    ConfigEntryState,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda import keys
from custom_components.bitpanda.const import DOMAIN


def _portfolio(hass, key="portfolio-key", **kwargs) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="portfolio",
        data={"entry_type": "portfolio", "api_key": key, "currency": "EUR"},
        **kwargs,
    )
    entry.add_to_hass(hass)
    return entry


def _reauth_flows(hass) -> list:
    return [
        flow
        for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        if flow["context"]["source"] == SOURCE_REAUTH
    ]


async def test_no_portfolio_lends_no_key(hass):
    price_tracker = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="price_tracker", data={"entry_type": "price_tracker"}
    )
    price_tracker.add_to_hass(hass)
    assert keys.portfolio_entry(hass) is None
    assert keys.portfolio_api_key(hass) is None


@pytest.mark.parametrize(
    "state",
    [
        ConfigEntryState.LOADED,
        ConfigEntryState.SETUP_ERROR,
        ConfigEntryState.SETUP_RETRY,
        ConfigEntryState.SETUP_IN_PROGRESS,
        ConfigEntryState.NOT_LOADED,
    ],
)
async def test_the_portfolios_key_is_lent_whatever_its_state(hass, state):
    entry = _portfolio(hass)
    entry.mock_state(hass, state)
    assert keys.portfolio_entry(hass) is entry
    assert keys.portfolio_api_key(hass) == "portfolio-key"


async def test_a_disabled_portfolio_still_lends_its_key(hass):
    """A Portfolio the user disabled is still set up as far as its key goes:
    the Price Tracker keeps its prices."""
    _portfolio(hass, disabled_by=ConfigEntryDisabler.USER)
    assert keys.portfolio_api_key(hass) == "portfolio-key"


async def test_a_disabled_portfolio_gets_the_reauth(hass):
    """Its key is the one the Price Tracker sends: a refused one asks for a
    new key on the disabled entry, which stores it and stays disabled."""
    _portfolio(hass, disabled_by=ConfigEntryDisabler.USER)
    keys.async_request_portfolio_reauth(hass, "portfolio-key")
    await hass.async_block_till_done()
    assert len(_reauth_flows(hass)) == 1


async def test_the_portfolio_with_its_unique_id_wins(hass):
    """The upgrade's blocker "a Bitpanda Portfolio is already set up" leaves
    a version 1 entry beside the Portfolio; another Portfolio-type entry
    without the unique ID may exist too. The one with the unique ID lends."""
    other = MockConfigEntry(
        domain=DOMAIN, version=3, data={"entry_type": "portfolio", "api_key": "other-key"}
    )
    other.add_to_hass(hass)
    legacy = MockConfigEntry(domain=DOMAIN, version=1, data={"api_key": "legacy-key", "currency": "EUR"})
    legacy.add_to_hass(hass)
    entry = _portfolio(hass)
    assert keys.portfolio_entry(hass) is entry
    assert keys.portfolio_api_key(hass) == "portfolio-key"


async def test_a_version_1_entry_lends_its_key(hass):
    """While a date version's entry waits for its upgrade, it is the
    Portfolio: the Price Tracker the upgrade creates asks with its key."""
    legacy = MockConfigEntry(domain=DOMAIN, version=1, data={"api_key": "legacy-key", "currency": "EUR"})
    legacy.add_to_hass(hass)
    assert keys.portfolio_entry(hass) is legacy
    assert keys.portfolio_api_key(hass) == "legacy-key"


async def test_an_ignored_entry_lends_nothing(hass):
    """An ignored discovery holds no key -- its version defaults to 1 and its
    unique ID may well be the Portfolio's."""
    ignored = MockConfigEntry(domain=DOMAIN, source=SOURCE_IGNORE, unique_id="portfolio", data={})
    ignored.add_to_hass(hass)
    assert keys.portfolio_entry(hass) is None
    assert keys.portfolio_api_key(hass) is None


async def test_the_reauth_is_requested_once(hass):
    """Every refusal asks again -- the Price Tracker every round, the
    Portfolio's lookups and prices -- and the user gets one dialog."""
    entry = _portfolio(hass)
    entry.mock_state(hass, ConfigEntryState.LOADED)
    keys.async_request_portfolio_reauth(hass, "portfolio-key")
    keys.async_request_portfolio_reauth(hass, "portfolio-key")
    await hass.async_block_till_done()
    keys.async_request_portfolio_reauth(hass, "portfolio-key")
    await hass.async_block_till_done()
    flows = _reauth_flows(hass)
    assert len(flows) == 1
    assert flows[0]["context"]["entry_id"] == entry.entry_id


async def test_a_reauth_while_the_portfolio_sets_up(hass):
    """At Home Assistant's start both services set up at once: a refusal
    while the Portfolio is still setting up asks it for a new key, as Home
    Assistant itself does in that state."""
    entry = _portfolio(hass)
    entry.mock_state(hass, ConfigEntryState.SETUP_IN_PROGRESS)
    keys.async_request_portfolio_reauth(hass, "portfolio-key")
    await hass.async_block_till_done()
    assert len(_reauth_flows(hass)) == 1


@pytest.mark.parametrize("state", [ConfigEntryState.MIGRATION_ERROR, ConfigEntryState.FAILED_UNLOAD])
async def test_no_reauth_on_an_entry_that_cannot_reload(hass, state):
    """Storing a new key reloads the entry, which Home Assistant refuses in
    these states: no dialog that cannot finish."""
    entry = _portfolio(hass)
    entry.mock_state(hass, state)
    keys.async_request_portfolio_reauth(hass, "portfolio-key")
    await hass.async_block_till_done()
    assert _reauth_flows(hass) == []


async def test_no_reauth_for_a_key_already_replaced(hass):
    """A request still under way with the old key comes back refused after
    the user entered a new one: it asks for nothing."""
    entry = _portfolio(hass, key="new-key")
    entry.mock_state(hass, ConfigEntryState.LOADED)
    keys.async_request_portfolio_reauth(hass, "old-key")
    await hass.async_block_till_done()
    assert _reauth_flows(hass) == []


async def test_no_reauth_without_a_portfolio(hass):
    keys.async_request_portfolio_reauth(hass, "portfolio-key")
    await hass.async_block_till_done()
    assert _reauth_flows(hass) == []
