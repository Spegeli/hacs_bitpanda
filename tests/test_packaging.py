"""Packaging facts the redesign depends on."""
import importlib.metadata
import json
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

_ROOT = Path(__file__).parent.parent


def _json(path: str) -> dict:
    return json.loads((_ROOT / path).read_text(encoding="utf-8"))


def test_manifest_allows_one_entry_per_service():
    manifest = _json("custom_components/bitpanda/manifest.json")
    assert "single_config_entry" not in manifest
    # The migration renames entity IDs; the recorder must already be loaded
    # so their history moves with them.
    assert "recorder" in manifest["after_dependencies"]


def test_manifest_requires_nothing_home_assistant_ships_itself():
    """Home Assistant installs a custom integration's requirements into its
    own environment, so one that Home Assistant depends on itself could
    clash with the version it needs: hassfest refuses it from 2026.10 on.
    aiohttp, which api.py uses, comes with every Home Assistant."""
    manifest = _json("custom_components/bitpanda/manifest.json")
    ships = {
        canonicalize_name(Requirement(requirement).name)
        for requirement in importlib.metadata.requires("homeassistant") or []
    }
    assert ships
    assert [
        requirement
        for requirement in manifest["requirements"]
        if canonicalize_name(Requirement(requirement).name) in ships
    ] == []


def test_hacs_requires_2025_5_where_renames_at_startup_keep_history():
    """Config subentries alone would need 2025.3. But the version 1 migration
    renames entity IDs while Home Assistant starts, and only from 2025.5 on
    does the recorder move an entity's history along with such a rename."""
    assert _json("hacs.json")["homeassistant"] == "2025.5.0"
