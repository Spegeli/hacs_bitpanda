"""Tests for the sensor platform's async_setup_entry.

The re-keyed, by-id asset cache (task 23) is what makes this possible at
all: two different asset ids sharing one symbol -- XAU the GoldMoney stock
and XAU the Gold metal -- must each get their own sensor, where the old
symbol-keyed cache could only ever hold one of them.
"""
from custom_components.bitpanda.assets import AssetResolver
from custom_components.bitpanda.const import (
    CONF_TRACKED_ASSETS,
    CONF_TRACKED_WALLETS,
    DOMAIN,
)
from custom_components.bitpanda.sensor import (
    BitpandaPriceSensor,
    async_setup_entry,
)

from tests.conftest import load_fixture


class _FakeCoordinator:
    def __init__(self, data=None, last_update_success=True):
        self.data = data
        self.last_update_success = last_update_success


class _FakeConfigEntry:
    entry_id = "entry1"

    def __init__(self, options):
        self.options = options


def _xau_pair() -> tuple[dict, dict]:
    assets = load_fixture("assets-sample.json")
    stock = next(
        a for a in assets if a["symbol"] == "XAU" and a["type"] == "equity_security"
    )
    metal = next(
        a for a in assets if a["symbol"] == "XAU" and a["type"] == "commodity"
    )
    return stock, metal


async def test_setup_builds_two_price_sensors_for_ids_sharing_a_symbol(hass):
    stock, metal = _xau_pair()
    resolver = AssetResolver(None, {stock["id"]: stock, metal["id"]: metal})

    config_entry = _FakeConfigEntry(
        options={
            CONF_TRACKED_ASSETS: [stock["id"], metal["id"]],
            CONF_TRACKED_WALLETS: [],
        }
    )
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = {
        "portfolio_coordinator": _FakeCoordinator(data=None),
        "price_coordinator": _FakeCoordinator(data={}),
        "earn_coordinator": _FakeCoordinator(data={}),
        "rewards_coordinator": _FakeCoordinator(data={}),
        "history_coordinator": _FakeCoordinator(data={}),
        "resolver": resolver,
        "currency": "EUR",
    }

    added: list = []
    await async_setup_entry(hass, config_entry, added.extend)

    price_sensors = [e for e in added if isinstance(e, BitpandaPriceSensor)]
    assert len(price_sensors) == 2
    assert {s._asset_id for s in price_sensors} == {stock["id"], metal["id"]}
    assert {s._attr_name for s in price_sensors} == {"XAU/EUR"}


async def test_setup_skips_a_tracked_id_with_no_cached_record(hass, caplog):
    """Unaffected by the re-keying, but pins that the per-id cache miss path
    still works the same way it always did.
    """
    resolver = AssetResolver(None, {})
    config_entry = _FakeConfigEntry(
        options={CONF_TRACKED_ASSETS: ["uuid-ghost"], CONF_TRACKED_WALLETS: []}
    )
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = {
        "portfolio_coordinator": _FakeCoordinator(data=None),
        "price_coordinator": _FakeCoordinator(data={}),
        "earn_coordinator": _FakeCoordinator(data={}),
        "rewards_coordinator": _FakeCoordinator(data={}),
        "history_coordinator": _FakeCoordinator(data={}),
        "resolver": resolver,
        "currency": "EUR",
    }

    added: list = []
    await async_setup_entry(hass, config_entry, added.extend)

    assert added == []
    assert "uuid-ghost" in caplog.text
