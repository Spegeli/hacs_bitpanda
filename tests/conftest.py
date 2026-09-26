"""Shared fixtures for Bitpanda integration tests."""
import json
from pathlib import Path
import string

from homeassistant.config_entries import ConfigSubentryData
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
    while the identical setting in `pytest.ini`'s `addopts` is discarded and
    leaves only a warning. Hence an explicit hook rather than a config line.
    """
    if not config.pluginmanager.hasplugin("timeout"):
        raise pytest.UsageError(
            "pytest-timeout is required; install it from requirements_test.txt"
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
