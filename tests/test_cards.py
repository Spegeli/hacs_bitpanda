"""The dashboard cards' bundle: served by the integration and added to every
dashboard, once per Home Assistant run, at a URL that changes with the file."""
from pathlib import Path
import re
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda import cards
from custom_components.bitpanda.api import BitpandaAuthError
from custom_components.bitpanda.cards import (
    CARDS_FILE,
    CARDS_URL,
    async_register_cards,
    cards_digest,
)
from custom_components.bitpanda.const import DOMAIN, SUPPORTED_CURRENCIES


def _http() -> Mock:
    return Mock(async_register_static_paths=AsyncMock())


def _frontend(hass) -> None:
    """Home Assistant's frontend loaded, as in every usual configuration:
    the test environment has no frontend package to load it from."""
    hass.config.components.add("frontend")


async def _websocket_api(hass) -> None:
    """Home Assistant's websocket API set up before the integration, as
    its after-dependency is."""
    assert await async_setup_component(hass, "websocket_api", {})


async def test_the_bundle_is_served_from_the_package(hass):
    hass.http = _http()
    _frontend(hass)
    with patch.object(cards, "add_extra_js_url"):
        await async_register_cards(hass)
    hass.http.async_register_static_paths.assert_awaited_once_with(
        [StaticPathConfig(CARDS_URL, str(CARDS_FILE), True)]
    )
    assert CARDS_FILE.name == "bitpanda-cards.js"
    assert CARDS_FILE.parent.name == "frontend"
    assert CARDS_FILE.is_file()


async def test_the_module_url_carries_the_content_hash(hass):
    hass.http = _http()
    _frontend(hass)
    with patch.object(cards, "add_extra_js_url") as add:
        await async_register_cards(hass)
    add.assert_called_once_with(hass, f"{CARDS_URL}?v={cards_digest(CARDS_FILE)}")


async def test_a_missing_bundle_costs_only_the_cards(hass, caplog):
    """A broken installation without the bundle: the integration still sets
    up, the log says why the cards are missing."""
    hass.http = _http()
    _frontend(hass)
    with (
        patch.object(cards, "CARDS_FILE", Path("/nonexistent/bitpanda-cards.js")),
        patch.object(cards, "add_extra_js_url") as add,
    ):
        await async_register_cards(hass)
    add.assert_not_called()
    assert "The dashboard cards are not available: " in caplog.text


async def test_a_refused_path_costs_only_the_cards(hass, caplog):
    hass.http = Mock(async_register_static_paths=AsyncMock(side_effect=RuntimeError("router frozen")))
    _frontend(hass)
    with patch.object(cards, "add_extra_js_url") as add:
        await async_register_cards(hass)
    add.assert_not_called()
    assert "The dashboard cards are not available: router frozen" in caplog.text


async def test_without_the_frontend_only_the_cards_are_missing(hass, caplog):
    """Home Assistant without its frontend -- a minimal configuration: the
    cards have nowhere to go, the log says so once, and nothing fails."""
    hass.http = _http()
    await async_register_cards(hass)
    hass.http.async_register_static_paths.assert_not_awaited()
    assert caplog.text.count("The dashboard cards are not available") == 1
    assert "Home Assistant's frontend is not loaded" in caplog.text


async def test_without_the_frontend_the_services_set_up(hass, caplog):
    """End to end, nothing patched: the integration and its entries set up
    as always, only the cards are missing."""
    tracker = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="price_tracker", title="Bitpanda Price Tracker",
        data={"entry_type": "price_tracker"}, options={"extra_currencies": []},
    )
    tracker.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert tracker.state is ConfigEntryState.LOADED
    assert "Home Assistant's frontend is not loaded" in caplog.text


async def test_without_the_websocket_api_the_line_command_is_not_registered(hass):
    hass.http = _http()
    hass.config.components.add("frontend")
    with (
        patch.object(cards, "add_extra_js_url"),
        patch.object(cards.websocket_api, "async_register_command") as register,
    ):
        await async_register_cards(hass)
    register.assert_not_called()


def test_the_hash_changes_with_the_content(tmp_path):
    one, same, other = (tmp_path / name for name in ("one.js", "same.js", "other.js"))
    one.write_bytes(b"customElements.define('a', A);")
    same.write_bytes(b"customElements.define('a', A);")
    other.write_bytes(b"customElements.define('b', B);")
    assert cards_digest(one) == cards_digest(same)
    assert cards_digest(one) != cards_digest(other)
    assert len(cards_digest(one)) == 12
    assert all(char in "0123456789abcdef" for char in cards_digest(one))


_CLIENT = "custom_components.bitpanda.api.BitpandaApiClient."


async def test_registered_once_for_the_integration_its_entries_and_reloads(hass, caplog):
    """async_setup runs once per run; setting up and reloading either
    service adds nothing more (a second registration of the path would be
    refused and logged)."""
    portfolio = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR",
              "currency_id": "b88b8466-efe3-11eb-b56f-0691764446a7"},
    )
    tracker = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="price_tracker", title="Bitpanda Price Tracker",
        data={"entry_type": "price_tracker"}, options={"extra_currencies": []},
    )
    for entry in (portfolio, tracker):
        entry.add_to_hass(hass)
    _frontend(hass)
    with (
        patch(f"{_CLIENT}async_get_portfolio", AsyncMock(return_value=[])),
        patch(f"{_CLIENT}async_get_portfolio_history", AsyncMock(return_value={"return_percentage": 0})),
        patch(f"{_CLIENT}async_get_earn_configs", AsyncMock(return_value=[])),
        patch(f"{_CLIENT}async_get_operations", AsyncMock(return_value=[])),
        patch(f"{_CLIENT}async_get_assets", AsyncMock(return_value=[])),
        patch.object(cards, "add_extra_js_url") as add,
    ):
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
        assert portfolio.state is ConfigEntryState.LOADED
        assert tracker.state is ConfigEntryState.LOADED
        for entry in (portfolio, tracker):
            for _ in range(2):
                assert await hass.config_entries.async_reload(entry.entry_id)
                await hass.async_block_till_done()
    assert add.call_count == 1
    assert "The dashboard cards are not available" not in caplog.text


async def test_the_portfolio_line_comes_from_bitpandas_value_history(hass, hass_ws_client):
    """bitpanda/portfolio_history answers with the series the Portfolio's
    returns came with, as [milliseconds, value] pairs; a timeframe or a
    Portfolio without one answers with none."""
    portfolio = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR",
              "currency_id": "b88b8466-efe3-11eb-b56f-0691764446a7"},
    )
    portfolio.add_to_hass(hass)
    _frontend(hass)
    await _websocket_api(hass)

    async def history(*, timeframe, equivalent_currency_id=None):
        points = [{"time": "2026-10-12T10:00:00Z", "value": {"value": "860.98"}}] if timeframe == "WEEK" else []
        return {"datapoints": points, "return_percentage": "0.31"}

    with (
        patch(f"{_CLIENT}async_get_portfolio", AsyncMock(return_value=[])),
        patch(f"{_CLIENT}async_get_portfolio_history", AsyncMock(side_effect=history)),
        patch(f"{_CLIENT}async_get_earn_configs", AsyncMock(return_value=[])),
        patch(f"{_CLIENT}async_get_operations", AsyncMock(return_value=[])),
        patch(f"{_CLIENT}async_get_assets", AsyncMock(return_value=[])),
        patch.object(cards, "add_extra_js_url"),
    ):
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "bitpanda/portfolio_history", "timeframe": "week"})
    answer = await client.receive_json()
    assert answer["success"], answer
    assert answer["result"] == {"points": [[1791799200000, 860.98]]}
    await client.send_json_auto_id({"type": "bitpanda/portfolio_history", "timeframe": "day"})
    assert (await client.receive_json())["result"] == {"points": []}
    await client.send_json_auto_id({"type": "bitpanda/portfolio_history", "timeframe": "decade"})
    assert not (await client.receive_json())["success"]
    # A rejected key turns the Portfolio's figures unavailable at once: the
    # line goes with them, instead of standing beside "—".
    with patch(f"{_CLIENT}async_get_portfolio_history", AsyncMock(side_effect=BitpandaAuthError("rejected"))):
        await portfolio.runtime_data.history.async_refresh()
        await hass.async_block_till_done()
    assert not portfolio.runtime_data.history.data_available
    await client.send_json_auto_id({"type": "bitpanda/portfolio_history", "timeframe": "week"})
    assert (await client.receive_json())["result"] == {"points": []}


async def test_without_a_portfolio_the_line_has_no_points(hass, hass_ws_client):
    hass.http = _http()
    _frontend(hass)
    await _websocket_api(hass)
    with patch.object(cards, "add_extra_js_url"):
        await async_register_cards(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "bitpanda/portfolio_history", "timeframe": "year"})
    assert (await client.receive_json())["result"] == {"points": []}


# The cards' names, as dashboards and the card picker know them: an
# interface from the first release, like entity IDs.
_CARDS = {
    "bitpanda-portfolio-card": "Bitpanda Portfolio",
    "bitpanda-price-tracker-card": "Bitpanda Price Tracker",
}


def test_the_bundle_defines_the_two_cards_by_their_fixed_names():
    bundle = CARDS_FILE.read_text(encoding="utf-8")
    for tag, name in _CARDS.items():
        assert f'"{tag}"' in bundle, tag
        assert f'"{name}"' in bundle, name


def test_the_price_tracker_card_offers_the_integrations_currencies():
    """Its start-currency field lists EUR and every extra currency the
    Price Tracker can be set up with."""
    bundle = CARDS_FILE.read_text(encoding="utf-8")
    for currency in SUPPORTED_CURRENCIES:
        assert f'"{currency}"' in bundle, currency


_README = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")

# Every card's options; the title is common to both.
_OPTIONS = {
    "bitpanda-portfolio-card": {
        "timeframe", "show_total", "show_graph", "show_cash", "show_allocation", "show_wallets",
        "group_wallets", "show_search", "sort", "limit", "group_selection", "groups",
        "asset_selection", "assets", "hide_amounts",
    },
    "bitpanda-price-tracker-card": {
        "layout", "timeframe", "currency", "sort", "group_selection", "groups",
        "asset_selection", "assets", "limit",
    },
}


# Each card's own table of options, under "Card options".
_TABLES = {
    "bitpanda-portfolio-card": "#### Bitpanda Portfolio card",
    "bitpanda-price-tracker-card": "#### Bitpanda Price Tracker card",
}


def _readme_section(heading: str) -> str:
    """From `heading` to the next heading of its level or above."""
    level = len(heading) - len(heading.lstrip("#"))
    start = _README.index(heading)
    ends = [
        found.start()
        for found in re.finditer(rf"^#{{1,{level}}} ", _README, re.MULTILINE)
        if found.start() > start
    ]
    return _README[start : ends[0]] if ends else _README[start:]


def test_every_card_option_is_documented_in_its_cards_table():
    """Each card has a table of exactly its own options, the title among
    them, and each is an option the bundle knows; no colours option is
    left."""
    bundle = CARDS_FILE.read_text(encoding="utf-8")
    for card, heading in _TABLES.items():
        table = _readme_section(heading)
        documented = set(re.findall(r"^\| `([a-z_]+)` \|", table, re.MULTILINE))
        assert documented == _OPTIONS[card] | {"title"}, card
        for option in _OPTIONS[card]:
            assert f'"{option}"' in bundle or f"{option}:" in bundle, (card, option)
    assert "`colors`" not in _readme_section("### Card options")


def test_the_cards_link_to_their_readme_section():
    """The card picker's documentation link opens the README's section."""
    assert "#-dashboard-cards" in CARDS_FILE.read_text(encoding="utf-8")
    assert "\n## 🃏 Dashboard cards\n" in _README
    for card in _OPTIONS:
        assert f"`custom:{card}`" in _README, card
