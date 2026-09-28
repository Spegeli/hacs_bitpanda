"""Shared fixtures for Bitpanda integration tests."""
import json
from pathlib import Path
import string
from unittest.mock import patch

from homeassistant.config_entries import (
    ConfigEntriesFlowManager,
    ConfigSubentryData,
    ConfigSubentryFlowManager,
    OptionsFlowManager,
)
from homeassistant.data_entry_flow import FlowManager, FlowResultType
from homeassistant.helpers import device_registry as dr, issue_registry as ir
import pytest

from custom_components.bitpanda.assets import slim_asset

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
            "pytest-timeout is required; install it from tests/requirements.txt"
        )

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Make Home Assistant load custom_components during tests."""
    return


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


def wallet_group(category: str, title: str | None = None) -> ConfigSubentryData:
    """A Portfolio wallet group as the integration stores it: one config
    subentry per asset category, keyed by the category, holding just that."""
    return ConfigSubentryData(
        data={"category": category},
        subentry_type="wallet_group",
        title=title or category,
        unique_id=category,
    )


_INTEGRATION = Path(__file__).parent.parent / "custom_components" / "bitpanda"


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


@pytest.fixture(autouse=True)
def check_flow_texts():
    """Every form and abort a Bitpanda flow shows has its texts, and every
    placeholder of a text it shows is supplied.

    Home Assistant core checks this with its check_translations fixture,
    which pytest-homeassistant-custom-component does not ship. Without the
    check, a dropped text or a renamed placeholder shows the user a raw key
    or a literal {placeholder}. Checked for the config, options and subentry
    flows: the step's texts, its errors and sections, and the abort reason.
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
        if texts is None:
            return result
        shown: list[str] = []
        if result["type"] == FlowResultType.FORM:
            step = texts.get("step", {}).get(result["step_id"])
            if step is None:
                problems.append(("no step texts", result["step_id"]))
                return result
            shown += [step.get("description", ""), *step.get("data_description", {}).values()]
            for part in step.get("sections", {}).values():
                shown += [part.get("description", ""), *part.get("data_description", {}).values()]
            for error in (result.get("errors") or {}).values():
                if error in texts.get("error", {}):
                    shown.append(texts["error"][error])
                else:
                    problems.append(("no error text", result["step_id"], error))
        elif result["type"] == FlowResultType.ABORT:
            if result["reason"] in texts.get("abort", {}):
                shown.append(texts["abort"][result["reason"]])
            else:
                problems.append(("no abort text", result["reason"]))
        supplied = set(result.get("description_placeholders") or {})
        problems.extend(
            ("placeholder not supplied", result.get("step_id") or result["reason"], missing)
            for text in shown
            if (missing := _placeholders(text) - supplied)
        )
        return result

    with patch.object(FlowManager, "_async_handle_step", _checked):
        yield
    assert problems == []


def assert_issue_texts_render(raised: dict[str, dict[str, str] | None]) -> None:
    """Every issue in `raised` -- translation key -> the placeholders the
    code supplied -- has a title and a description in every shipped
    language that use exactly those placeholders and render with them. A
    list opens a paragraph of its own, so the frontend renders it as a
    Markdown list. Read from the files themselves: Home Assistant would
    replace a mismatched translation with English, hiding it."""
    languages = sorted(path.stem for path in (_INTEGRATION / "translations").glob("*.json"))
    assert len(languages) == 7
    for language in languages:
        texts = json.loads(
            (_INTEGRATION / "translations" / f"{language}.json").read_text(encoding="utf-8")
        )["issues"]
        for key, placeholders in raised.items():
            placeholders = placeholders or {}
            title, description = texts[key]["title"], texts[key]["description"]
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
    `subentry_id` -- in none, for None.

    Read from the device's own `config_subentry_id`, as the test image's
    Home Assistant records it; the integration itself reads group membership
    from the entity registry only.
    """
    return {
        device.name
        for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry_id)
        if device.config_subentry_id == subentry_id
    }
