"""The issue forms ask for what a report needs, in the words Home Assistant
shows.

GitHub reads the forms from `main` only: a change here reaches reporters
with the next stable release.
"""
from pathlib import Path

import yaml

_FORMS = Path(__file__).parent.parent / ".github" / "ISSUE_TEMPLATE"


def _fields(form: str) -> dict[str, dict]:
    """A form's fields by id, in the form's order."""
    body = yaml.safe_load((_FORMS / form).read_text(encoding="utf-8"))["body"]
    return {field["id"]: field for field in body if "id" in field}


def test_the_bug_report_asks_for_the_asset_id_where_the_device_page_shows_it():
    """A symbol can name several assets -- XAU is Gold and GoldMoney Inc --
    the asset ID only one. Optional, right after the symbol: not every
    reporter has it. Every wallet and price device shows it as its serial
    number."""
    fields = _fields("bug_report.yml")
    assert "asset_id" in fields
    ids = list(fields)
    assert ids.index("asset_id") == ids.index("asset") + 1
    field = fields["asset_id"]
    assert field["type"] == "input"
    assert field["validations"]["required"] is False
    description = field["attributes"]["description"]
    assert "**Service info**" in description
    assert "**Serial number**" in description
