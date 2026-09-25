"""Device lookups: portable across Home Assistant versions."""
from pathlib import Path

from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.devices import (
    device_identifier,
    find_entry_device,
    subentry_devices,
)

from tests.conftest import wallet_group

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


async def test_device_identifier_is_the_one_under_this_domain(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    ours = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("other", "x"), (DOMAIN, "eid_portfolio")}
    )
    foreign = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("other", "y")}
    )
    assert device_identifier(ours) == "eid_portfolio"
    assert device_identifier(foreign) is None


async def test_subentry_devices_are_the_devices_of_that_subentry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, subentries_data=[wallet_group("crypto"), wallet_group("metal")]
    )
    other = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    other.add_to_hass(hass)
    crypto, metal = (
        next(sub.subentry_id for sub in entry.subentries.values() if sub.unique_id == key)
        for key in ("crypto", "metal")
    )
    dev_reg = dr.async_get(hass)

    def _device(entry_id: str, identifier: str, subentry_id: str | None = None):
        return dev_reg.async_get_or_create(
            config_entry_id=entry_id,
            config_subentry_id=subentry_id,
            identifiers={(DOMAIN, identifier)},
            name=identifier,
        )

    _device(entry.entry_id, "btc", crypto)
    _device(entry.entry_id, "sol", crypto)
    _device(entry.entry_id, "outside")
    _device(other.entry_id, "elsewhere")
    assert sorted(d.name for d in subentry_devices(hass, entry.entry_id, crypto)) == [
        "btc", "sol",
    ]
    assert subentry_devices(hass, entry.entry_id, metal) == []
    assert subentry_devices(hass, other.entry_id, crypto) == []
