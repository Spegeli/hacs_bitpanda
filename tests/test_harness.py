"""Verify the test harness itself works."""
import logging

from homeassistant.data_entry_flow import FlowResultType
import pytest

from tests.conftest import flow_text_problems, load_fixture

# The texts of a made-up flow, for the check every flow test runs through
# (tests/conftest.py, check_flow_texts).
_FLOW_TEXTS = {
    "step": {
        "form": {
            "title": "Form",
            "description": "Pick {thing}.",
            "data_description": {"field": "About {hint}."},
        },
        "menu": {
            "title": "Menu",
            "description": "Choose for {name}.",
            "menu_options": {"yes": "Yes", "no": "No"},
        },
        "button": {
            "title": "Button",
            "description": "Go on.",
            "menu_options": {"go": "Go to {target}"},
        },
    },
    "error": {"bad": "Bad: {why}."},
    "abort": {"done": "Done at {when}."},
}


def test_the_flow_text_check_accepts_complete_texts():
    shown = [
        {"type": FlowResultType.FORM, "step_id": "form", "errors": {"base": "bad"},
         "description_placeholders": {"thing": "x", "hint": "y", "why": "z"}},
        {"type": FlowResultType.MENU, "step_id": "menu", "menu_options": ["yes", "no"],
         "description_placeholders": {"name": "n"}},
        {"type": FlowResultType.MENU, "step_id": "button", "menu_options": ["go"],
         "description_placeholders": {"target": "t"}},
        {"type": FlowResultType.ABORT, "reason": "done",
         "description_placeholders": {"when": "now"}},
    ]
    assert [flow_text_problems(_FLOW_TEXTS, result) for result in shown] == [[], [], [], []]


@pytest.mark.parametrize(
    ("result", "problems"),
    [
        ({"type": FlowResultType.FORM, "step_id": "gone"}, [("no step texts", "gone")]),
        (
            {"type": FlowResultType.MENU, "step_id": "gone", "menu_options": ["no"]},
            [("no step texts", "gone")],
        ),
        (
            {"type": FlowResultType.FORM, "step_id": "form", "errors": {"base": "worse"},
             "description_placeholders": {"thing": "x", "hint": "y"}},
            [("no error text", "form", "worse")],
        ),
        (
            {"type": FlowResultType.MENU, "step_id": "menu", "menu_options": ["yes", "maybe"],
             "description_placeholders": {"name": "n"}},
            [("no menu option text", "menu", "maybe")],
        ),
        ({"type": FlowResultType.ABORT, "reason": "left"}, [("no abort text", "left")]),
        (
            {"type": FlowResultType.FORM, "step_id": "form",
             "description_placeholders": {"thing": "x"}},
            [("placeholder not supplied", "form", frozenset({"hint"}))],
        ),
        (
            {"type": FlowResultType.MENU, "step_id": "menu", "menu_options": ["no"]},
            [("placeholder not supplied", "menu", frozenset({"name"}))],
        ),
        # The frontend fills the placeholders into a button's label too.
        (
            {"type": FlowResultType.MENU, "step_id": "button", "menu_options": ["go"]},
            [("placeholder not supplied", "button", frozenset({"target"}))],
        ),
    ],
    ids=[
        "form_without_texts", "menu_without_texts", "error_without_text",
        "button_without_label", "abort_without_text", "form_placeholder",
        "menu_placeholder", "button_placeholder",
    ],
)
def test_the_flow_text_check_reports_what_a_shown_text_lacks(result, problems):
    assert flow_text_problems(_FLOW_TEXTS, result) == problems


def test_the_database_engine_writes_no_sql_statements():
    """pytest-homeassistant-custom-component sets the SQLAlchemy engine's
    logger to INFO and gives the root logger a handler on stderr, so every
    SQL statement is written out. The recorder's thread can write one between
    two tests, outside pytest's capture, into the suite's output;
    tests/conftest.py sets the level back to WARNING."""
    assert logging.getLogger("sqlalchemy.engine").getEffectiveLevel() >= logging.WARNING


def test_currency_fixture_is_readable():
    currencies = load_fixture("currencies.json")
    symbols = {c["symbol"] for c in currencies}
    assert "EUR" in symbols
    assert len(currencies) == 12


def test_asset_fixture_covers_every_group():
    assets = load_fixture("assets-sample.json")
    groups = {a["group"] for a in assets}
    assert {
        "coin",
        "metal",
        "index",
        "equity_stock",
        "equity_etf",
        "fiat_earn",
    } <= groups


def test_earn_fixture_is_readable():
    configs = load_fixture("earn-configs.json")
    assert len(configs) == 44
    assert all(
        isinstance(c["annual_percentage_rate"], (int, float)) for c in configs
    )


async def test_home_assistant_fixture_starts(hass):
    assert hass.config.config_dir is not None
