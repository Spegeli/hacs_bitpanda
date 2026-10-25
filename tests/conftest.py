"""Shared fixtures for Bitpanda integration tests."""
import asyncio
from collections.abc import Mapping
from datetime import timedelta
from functools import partial
import json
import logging
from pathlib import Path
import re
import string
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.components.recorder.statistics import get_metadata
from homeassistant.config_entries import (
    ConfigEntriesFlowManager,
    ConfigSubentryData,
    ConfigSubentryFlowManager,
    OptionsFlowManager,
)
from homeassistant.data_entry_flow import FlowManager, FlowResultType
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.util import dt as dt_util
import pytest
import yaml

from custom_components.bitpanda.api import BitpandaApiError
from custom_components.bitpanda.assets import slim_asset
from custom_components.bitpanda.portfolio_coordinator import PortfolioRuntime
from custom_components.bitpanda.portfolio_store import (
    KnownWallets,
    OperationsHistory,
    PortfolioStore,
    RewardMarks,
)

pytest_plugins = "pytest_homeassistant_custom_component"


def pytest_configure(config):
    """Fail loudly if pytest-timeout is missing.

    The pagination tests (`test_paginate_raises_when_cursor_does_not_advance`
    and `tests/test_api_pagination.py`) are guarded by `@pytest.mark.timeout`,
    because a regression in the cursor-loop guards spins without ever
    yielding to the event loop — `asyncio.wait_for` cannot cancel it, so only
    an out-of-band signal stops the run. Without the plugin that marker is an
    unknown mark: pytest warns and carries on, and the test hangs the suite
    instead of failing it.

    `--strict-markers` would express the same requirement, but only from the
    command line. Measured in this plugin stack: passed as a CLI flag it fails
    collection with "'timeout' not found in `markers` configuration option",
    while the identical setting in `pyproject.toml`'s `addopts` is discarded
    and leaves only a warning. Hence an explicit hook rather than a config line.
    """
    if not config.pluginmanager.hasplugin("timeout"):
        raise pytest.UsageError(
            "pytest-timeout is required; install it from tests/requirements.txt "
            "(tests/requirements-floor.txt on the minimum Home Assistant)"
        )
    # The plugin sets the SQLAlchemy engine's logger to INFO when it is
    # imported, which is after this file: every SQL statement would be
    # written to stderr, and the recorder's thread can write one between two
    # tests, outside pytest's capture. Its warnings still show.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    # A test that runs the real ticker request (no_real_ticker).
    config.addinivalue_line(
        "markers", "real_ticker: the test runs the real BitpandaApiClient.async_get_ticker"
    )

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def stub_the_dashboard_cards(request):
    """Every test but test_cards.py sets up the integration without serving
    the cards' bundle: the test environment has no frontend package, so
    add_extra_js_url finds nothing to add to. test_cards.py owns it."""
    if request.module.__name__.endswith("test_cards"):
        yield
        return
    with patch("custom_components.bitpanda.async_register_cards", AsyncMock()):
        yield


@pytest.fixture(autouse=True)
def no_real_ticker(request):
    """A Portfolio reads each wallet's price from Bitpanda's ticker in a round
    after every successful refresh: in tests no ticker answers -- a request
    fails at once, as an HTTP error, and the wallets have no price.
    A test that wants ticker prices patches async_get_ticker itself; the API
    tests (test_api_*.py) and a test marked `real_ticker` run the real
    method."""
    if request.node.path.name.startswith("test_api") or request.node.get_closest_marker(
        "real_ticker"
    ):
        yield
        return
    failure = BitpandaApiError("no ticker in tests", kind="http_status", path="/tickers")
    with patch(
        "custom_components.bitpanda.api.BitpandaApiClient.async_get_ticker",
        AsyncMock(side_effect=failure),
    ):
        yield


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Make Home Assistant load custom_components during tests."""
    return


async def async_settle(rounds: int = 1000) -> None:
    """Let the event loop run until it has no callback ready: whatever
    still waits then waits for something -- an event, a lock, a timer, an
    executor job --, and no task of the loop will move it on its own. That
    is what "nothing happened yet" asserts in the tests that call it; a job
    running in a thread can still finish later, so they wait on none.
    Fails when the loop is still busy after `rounds` turns, rather than
    passing on a guess."""
    loop = asyncio.get_running_loop()
    for _ in range(rounds):
        await asyncio.sleep(0)
        # The loop's queue of callbacks ready to run (CPython's asyncio).
        if not loop._ready:  # type: ignore[attr-defined]
            return
    raise AssertionError(f"the event loop was still busy after {rounds} turns")


def load_fixture(name: str):
    """Load a captured API response.

    Fixtures live in tests/fixtures/ and are committed. They hold only public
    catalogue data — currencies, assets, earn products. Account-specific
    responses are synthesised in the tests that need them, so nothing from a
    real portfolio ends up in the repository.
    """
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def price_group(category: str, *assets: dict, title: str | None = None) -> ConfigSubentryData:
    """A Price Tracker group as the integration stores it: one config subentry
    per asset category, keyed by the category, holding slim asset records."""
    return ConfigSubentryData(
        data={"category": category, "assets": {a["id"]: slim_asset(a) for a in assets}},
        subentry_type="price_group",
        title=title or category,
        unique_id=category,
    )


def portfolio_runtime(hass, entry_id: str = "eid", **fields: Any) -> PortfolioRuntime:
    """A Portfolio's runtime data built by hand: `fields` as given -- the
    coordinators at least --, no group titles and setup data unless given,
    the Portfolio's file as at a first start: no list of known wallets, no
    marks, nothing read of the operations -- and its platforms set up."""
    store = PortfolioStore(hass, entry_id)
    runtime = PortfolioRuntime(**{
        "group_titles": {},
        "data_at_setup": {},
        "options_at_setup": {},
        "known_wallets": KnownWallets(store, None, None),
        "reward_marks": RewardMarks(store, None, None),
        "operations": OperationsHistory(store, None, None),
        **fields,
    })
    # Set up already: nothing waits for the platforms.
    runtime.ready.set()
    return runtime


def wallet_group(category: str, title: str | None = None) -> ConfigSubentryData:
    """A Portfolio wallet group as the integration stores it: one config
    subentry per asset category, keyed by the category, holding just that."""
    return ConfigSubentryData(
        data={"category": category},
        subentry_type="wallet_group",
        title=title or category,
        unique_id=category,
    )


# The data of each of the Portfolio's announcements, by event entity key
# (announcements.PORTFOLIO_EVENT_TYPES): the bus event's fields, which the
# entity shows as its attributes.
ANNOUNCEMENT_FIELDS = {
    "new_wallet": frozenset({
        "device_id", "asset_id", "symbol", "name", "wallet", "category", "units", "value",
        "currency", "message",
    }),
    "staking_reward": frozenset({
        "device_id", "asset_id", "symbol", "name", "wallet", "count", "gross", "fee", "net",
        "value", "currency", "credited_at", "apr_percent", "rewards_net", "message",
    }),
    "earn_change": frozenset({
        "device_id", "asset_id", "symbol", "name", "wallet", "change", "apr_before", "apr_after",
    }),
}

_INTEGRATION = Path(__file__).parent.parent / "custom_components" / "bitpanda"


def manifest_version() -> str:
    """The integration's version, as its manifest states it."""
    manifest = json.loads((_INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    version: str = manifest["version"]
    return version


def raised_issues(hass) -> dict[str, dict[str, str] | None]:
    """This integration's repair issues, read back from the issue registry:
    translation key -> the placeholders the code supplied."""
    return {
        issue.translation_key: issue.translation_placeholders
        for (domain, _), issue in ir.async_get(hass).issues.items()
        if domain == "bitpanda"
    }


def _placeholders(template: str) -> frozenset[str]:
    """The {placeholders} of a text, parsed as Home Assistant parses them."""
    return frozenset(
        field for _, field, _, _ in string.Formatter().parse(template) if field is not None
    )


def flow_text_problems(texts: dict, result: Mapping[str, Any]) -> list[tuple]:
    """What the flow result `result` shows without a text, and every
    placeholder a text it shows uses that the code did not supply. `texts`
    are the flow's part of the English strings: `config`, `options` or one
    subentry type's."""
    problems: list[tuple] = []
    shown: list[str] = []
    if result["type"] in (FlowResultType.FORM, FlowResultType.MENU):
        step = texts.get("step", {}).get(result["step_id"])
        if step is None:
            return [("no step texts", result["step_id"])]
        shown += [step.get("title", ""), step.get("description", "")]
    if result["type"] == FlowResultType.FORM:
        shown += step.get("data_description", {}).values()
        for part in step.get("sections", {}).values():
            shown += [part.get("description", ""), *part.get("data_description", {}).values()]
        for error in (result.get("errors") or {}).values():
            if error in texts.get("error", {}):
                shown.append(texts["error"][error])
            else:
                problems.append(("no error text", result["step_id"], error))
    elif result["type"] == FlowResultType.MENU:
        # The frontend fills the placeholders into the button labels too.
        labels = step.get("menu_options", {})
        for option in result["menu_options"]:
            if option in labels:
                shown.append(labels[option])
            else:
                problems.append(("no menu option text", result["step_id"], option))
    elif result["type"] == FlowResultType.ABORT:
        if result["reason"] in texts.get("abort", {}):
            shown.append(texts["abort"][result["reason"]])
        else:
            problems.append(("no abort text", result["reason"]))
    elif result["type"] == FlowResultType.CREATE_ENTRY:
        # The frontend shows create_entry.<description>, create_entry.default
        # without one -- or its own text when there is no such key.
        key = result.get("description") or "default"
        if key in texts.get("create_entry", {}):
            shown.append(texts["create_entry"][key])
        elif result.get("description"):
            problems.append(("no create_entry text", key))
    supplied = set(result.get("description_placeholders") or {})
    problems.extend(
        (
            "placeholder not supplied",
            result.get("step_id") or result.get("reason") or result.get("description") or "default",
            missing,
        )
        for text in shown
        if (missing := _placeholders(text) - supplied)
    )
    return problems


@pytest.fixture(autouse=True)
def check_flow_texts():
    """Every form, menu, abort and created entry a Bitpanda flow shows has
    its texts, and every placeholder of a text it shows is supplied.

    Home Assistant core checks this with its check_translations fixture,
    which pytest-homeassistant-custom-component does not ship. Without the
    check, a dropped text or a renamed placeholder shows the user a raw key
    or a literal {placeholder}. Checked for the config, options and subentry
    flows: the step's title and texts, a form's errors and sections, a menu's
    option labels, the abort reason, and a created entry's text
    (`create_entry.<description>`, else `create_entry.default`).
    Read from translations/en.json, which equals strings.json (test_strings).
    """
    english = json.loads(
        (_INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8")
    )
    problems: list[tuple] = []
    original = FlowManager._async_handle_step

    def _texts(manager, flow) -> dict | None:
        """The texts of the kind of flow `flow` is; None for a flow of
        another integration."""
        if isinstance(manager, OptionsFlowManager):
            entry = manager.hass.config_entries.async_get_entry(flow.handler)
            return english["options"] if entry and entry.domain == "bitpanda" else None
        if isinstance(manager, ConfigSubentryFlowManager):
            entry_id, subentry_type = flow.handler
            entry = manager.hass.config_entries.async_get_entry(entry_id)
            if entry is None or entry.domain != "bitpanda":
                return None
            return english["config_subentries"][subentry_type]
        if isinstance(manager, ConfigEntriesFlowManager) and flow.handler == "bitpanda":
            return english["config"]
        return None

    async def _checked(self, flow, *args, **kwargs):
        result = await original(self, flow, *args, **kwargs)
        texts = _texts(self, flow)
        if texts is not None:
            problems.extend(flow_text_problems(texts, result))
        return result

    with patch.object(FlowManager, "_async_handle_step", _checked):
        yield
    assert problems == []


def assert_issue_texts_render(raised: dict[str, dict[str, str] | None]) -> None:
    """Every issue in `raised` -- translation key -> the placeholders the
    code supplied -- has a title and a description in every shipped
    language that use exactly those placeholders and render with them. A
    fixable issue's description is its dialog's, and that dialog has a
    title of its own. A list opens a paragraph of its own, so the frontend
    renders it as a Markdown list. Read from the files themselves: Home
    Assistant would replace a mismatched translation with English, hiding
    it."""
    languages = sorted(path.stem for path in (_INTEGRATION / "translations").glob("*.json"))
    assert len(languages) == 7
    for language in languages:
        texts = json.loads(
            (_INTEGRATION / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )["issues"]
        for key, placeholders in raised.items():
            placeholders = placeholders or {}
            title = texts[key]["title"]
            if "fix_flow" in texts[key]:
                assert "description" not in texts[key], (language, key)
                confirm = texts[key]["fix_flow"]["step"]["confirm"]
                assert confirm["title"] and not _placeholders(confirm["title"]), (language, key)
                description = confirm["description"]
            else:
                description = texts[key]["description"]
            assert _placeholders(title) | _placeholders(description) == set(placeholders), (
                language, key,
            )
            rendered = title.format(**placeholders) + description.format(**placeholders)
            assert all(value in rendered for value in placeholders.values()), (language, key)
            for name, value in placeholders.items():
                if value.startswith("- "):
                    assert f"\n\n{{{name}}}" in description, (language, key, name)


def device_names_in_subentry(hass, entry_id: str, subentry_id: str | None) -> set[str]:
    """Names of the devices of config entry `entry_id` in its subentry
    `subentry_id` only -- in none, for None.

    Read from the device registry as each Home Assistant release records it
    (_device_subentries). Only: on 2025.5 a device can be in two subentries
    of an entry, and such a device must show in neither. The integration
    itself reads group membership from the entity registry only.
    """
    return {
        device.name
        for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry_id)
        if _device_subentries(device, entry_id) == {subentry_id}
    }


def _device_subentries(device: dr.DeviceEntry, entry_id: str) -> set[str | None]:
    """The subentries of config entry `entry_id` that `device` is in. Newer
    releases record one, `config_subentry_id`; Home Assistant 2025.5, the
    floor in hacs.json, records a set per config entry in
    `config_entries_subentries`."""
    if hasattr(device, "config_subentry_id"):
        return {device.config_subentry_id}
    return set(device.config_entries_subentries.get(entry_id, ()))


async def recorded_history(hass, entity_id: str) -> list[tuple[str, str | None]]:
    """(state, unit) of every state the recorder holds for `entity_id`."""
    start = dt_util.utcnow() - timedelta(hours=1)
    states = await get_instance(hass).async_add_executor_job(
        get_significant_states, hass, start, None, [entity_id]
    )
    return [
        (state.state, state.attributes.get("unit_of_measurement"))
        for state in states.get(entity_id, [])
    ]


async def statistics_units(hass, entity_ids) -> dict[str, str | None]:
    """The unit of the long-term statistics the recorder keeps for each of
    `entity_ids` -- the ones it keeps any for."""
    metadata = await get_instance(hass).async_add_executor_job(
        partial(get_metadata, hass, statistic_ids=set(entity_ids))
    )
    return {
        statistic_id: meta["unit_of_measurement"]
        for statistic_id, (_, meta) in metadata.items()
    }


def readme_event_guard() -> tuple[dict, list]:
    """The README's state trigger on an event entity (section "Event
    entities"): its `not_from` and `not_to`, which keep a reload from running
    it, and its conditions, which keep an entity coming back with its last
    event restored -- after a currency change, say -- from running it."""
    readme = (Path(__file__).parent.parent / "README.md").read_text(encoding="utf-8")
    section = readme[readme.index("### Event entities"):]
    block = re.search(r"```yaml\n(.*?)```", section, re.DOTALL)
    assert block is not None
    config = yaml.safe_load(block.group(1))
    [trigger] = config["triggers"]
    return {key: trigger[key] for key in ("not_from", "not_to")}, config.get("conditions", [])
