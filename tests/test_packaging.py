"""Packaging facts the redesign depends on."""
import json
from pathlib import Path

_ROOT = Path(__file__).parent.parent


def _json(path: str) -> dict:
    return json.loads((_ROOT / path).read_text(encoding="utf-8"))


def test_manifest_allows_one_entry_per_service():
    manifest = _json("custom_components/bitpanda/manifest.json")
    assert "single_config_entry" not in manifest
    # The migration renames entity IDs; the recorder must already be loaded
    # so their history moves with them.
    assert "recorder" in manifest["after_dependencies"]


def test_hacs_requires_2025_5_where_renames_at_startup_keep_history():
    """Config subentries alone would need 2025.3. But the version 1 migration
    renames entity IDs while Home Assistant starts, and only from 2025.5 on
    does the recorder move an entity's history along with such a rename."""
    assert _json("hacs.json")["homeassistant"] == "2025.5.0"
