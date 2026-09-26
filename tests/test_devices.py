"""Device lookups: portable across Home Assistant versions."""
from pathlib import Path

from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.devices import device_identifiers, find_entry_device

_PACKAGE = Path(__file__).parent.parent / "custom_components" / "bitpanda"


def _offenders(text: str) -> list[str]:
    return [
        path.name
        for path in _PACKAGE.glob("*.py")
        if text in path.read_text(encoding="utf-8")
    ]


def test_no_module_uses_the_deprecated_device_lookup():
    """DeviceRegistry.async_get_device stops working in Home Assistant 2027.8."""
    assert _offenders("async_get_device(") == []


def test_no_module_reads_the_deprecated_device_subentries():
    """DeviceEntry.config_entries_subentries is a deprecated compatibility
    property from Home Assistant 2026.9 on. Group membership is read from the
    entity registry, which records an entity's subentry on every version."""
    assert _offenders("config_entries_subentries") == []


async def test_finds_the_device_of_its_own_entry(hass):
    mine = MockConfigEntry(domain=DOMAIN)
    other = MockConfigEntry(domain=DOMAIN)
    mine.add_to_hass(hass)
    other.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    own = dev_reg.async_get_or_create(
        config_entry_id=mine.entry_id, identifiers={(DOMAIN, "shared")}
    )
    dev_reg.async_get_or_create(
        config_entry_id=other.entry_id, identifiers={(DOMAIN, "elsewhere")}
    )
    assert find_entry_device(hass, mine.entry_id, "shared").id == own.id
    assert find_entry_device(hass, mine.entry_id, "elsewhere") is None
    assert find_entry_device(hass, other.entry_id, "shared") is None


async def test_device_identifiers_are_every_one_under_this_domain(hass):
    """All of them, not one picked at random: a device is judged by every
    identifier this integration gave it."""
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    ours = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("other", "x"), (DOMAIN, "eid_portfolio"), (DOMAIN, "eid_wallets")},
    )
    foreign = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("other", "y")}
    )
    assert device_identifiers(ours) == {"eid_portfolio", "eid_wallets"}
    assert device_identifiers(foreign) == set()
