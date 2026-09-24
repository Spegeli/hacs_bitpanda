"""Shared fixtures for Bitpanda integration tests."""
import json
from pathlib import Path

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


def pytest_configure(config):
    """Fail loudly if pytest-timeout is missing.

    `test_paginate_stops_when_cursor_does_not_advance` is guarded by
    `@pytest.mark.timeout`, because a regression in the stuck-cursor guard
    spins without ever yielding to the event loop — `asyncio.wait_for` cannot
    cancel it, so only an out-of-band signal stops the run. Without the plugin
    that marker is an unknown mark: pytest warns and carries on, and the test
    hangs the suite instead of failing it. `--strict-markers` would catch this
    but is silently ignored from `addopts` in this setup, so the check is made
    explicit here.
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
