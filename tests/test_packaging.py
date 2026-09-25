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


def test_hacs_requires_config_subentries():
    assert _json("hacs.json")["homeassistant"] == "2025.3.0"
