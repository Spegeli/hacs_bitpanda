"""Device lookups that work on every supported Home Assistant version."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN


def device_identifier(device: dr.DeviceEntry) -> str | None:
    """The identifier this integration gave `device`, or None.

    Every device it creates carries exactly one: (DOMAIN, identifier).
    """
    return next(
        (identifier for domain, identifier in device.identifiers if domain == DOMAIN), None
    )


def find_entry_device(
    hass: HomeAssistant, entry_id: str, identifier: str
) -> dr.DeviceEntry | None:
    """The device of config entry `entry_id` that carries (DOMAIN, identifier).

    Scoped to the entry on purpose: device identifiers are no longer unique
    across config entries, which is why DeviceRegistry.async_get_device is
    deprecated (it stops working in Home Assistant 2027.8). Its replacements
    (async_get_device_by_identifier and its siblings) do not exist at this
    integration's 2025.5 floor; listing the entry's own devices works on
    every version.
    """
    wanted = (DOMAIN, identifier)
    return next(
        (
            device
            for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry_id)
            if wanted in device.identifiers
        ),
        None,
    )


def subentry_devices(
    hass: HomeAssistant, entry_id: str, subentry_id: str
) -> list[dr.DeviceEntry]:
    """The devices of config entry `entry_id` that belong to its subentry `subentry_id`.

    Read from `config_entries_subentries`, the one field that tells on every
    supported version: Home Assistant 2025.5 lets a device belong to several
    subentries and stores them there, per config entry; later versions give
    a device a single subentry and keep that field as a deprecated
    compatibility property.
    """
    return [
        device
        for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry_id)
        if subentry_id in device.config_entries_subentries.get(entry_id, ())
    ]
