"""Shared fixtures for Bitpanda integration tests."""
import json
from pathlib import Path

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

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
