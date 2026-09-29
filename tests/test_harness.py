"""Verify the test harness itself works."""
import logging

from tests.conftest import load_fixture


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
