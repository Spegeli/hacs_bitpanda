"""Shared fixtures for Bitpanda integration tests."""
import json
from pathlib import Path

import pytest

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
