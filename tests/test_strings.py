"""The three string files stay structurally identical and BOM-free."""
import json
from pathlib import Path

from custom_components.bitpanda.assets import ASSET_CATEGORY_FILTERS, CATEGORY_OTHER

_DIR = Path(__file__).parent.parent / "custom_components" / "bitpanda"
_FILES = ("strings.json", "translations/en.json", "translations/de.json")


def _paths(node, prefix: str = "") -> set[str]:
    if not isinstance(node, dict):
        return set()
    out: set[str] = set()
    for key, value in node.items():
        out.add(prefix + key)
        out |= _paths(value, f"{prefix}{key}.")
    return out


def test_string_files_have_no_bom():
    for name in _FILES:
        assert not (_DIR / name).read_bytes().startswith(b"\xef\xbb\xbf"), name


def test_string_files_share_one_structure():
    structures = [
        _paths(json.loads((_DIR / name).read_text(encoding="utf-8"))) for name in _FILES
    ]
    assert structures[0] == structures[1] == structures[2]


def test_english_translation_is_the_strings_file():
    strings = json.loads((_DIR / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((_DIR / "translations/en.json").read_text(encoding="utf-8"))
    assert strings == english


def test_every_currency_and_entity_name_is_translated():
    strings = json.loads((_DIR / "strings.json").read_text(encoding="utf-8"))
    # Lowercase: hassfest's translation-key validator rejects uppercase
    # selector option keys (see config_flow.py's _currency_select).
    assert set(strings["selector"]["currency"]["options"]) == {
        "chf", "czk", "dkk", "eur", "gbp", "huf", "nok", "pln", "ron", "sek", "try", "usd",
    }
    assert set(strings["entity"]["sensor"]) == {
        "total_value", "cash", "cash_plus", "return_day", "return_week",
        "return_month", "return_six_month", "return_year", "staking", "wallet_total",
    }


def test_every_asset_category_has_a_group_title():
    strings = json.loads((_DIR / "strings.json").read_text(encoding="utf-8"))
    assert set(strings["selector"]["asset_group"]["options"]) == {
        *ASSET_CATEGORY_FILTERS, CATEGORY_OTHER,
    }
