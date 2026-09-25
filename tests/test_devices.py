"""Device lookups: portable across Home Assistant versions."""
from pathlib import Path

from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.devices import find_entry_device

_PACKAGE = Path(__file__).parent.parent / "custom_components" / "bitpanda"


def test_no_module_uses_the_deprecated_device_lookup():
    """DeviceRegistry.async_get_device stops working in Home Assistant 2027.8."""
    offenders = [
        path.name
        for path in _PACKAGE.glob("*.py")
        if "async_get_device(" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


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
