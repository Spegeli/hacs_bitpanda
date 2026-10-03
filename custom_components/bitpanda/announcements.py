"""Announcing a wallet that is new to the Portfolio.

The wallet lifecycle manager (portfolio_sensor.py) creates wallet entities at
every start, after a currency change and after a deleted group; it marks a
wallet it creates as new only when the Portfolio's list (known_wallets.py)
does not know its asset. Home Assistant creates the wallet's device as it
takes in the first of the wallet's sensors -- or brings back the device
deleted with the wallet before, under its id, which it reports as created
too -- and that creation announces the wallet, so the notification can link
to the device: the event EVENT_WALLET_ADDED, always, and a persistent
notification unless the entry's option switches it off; during a start,
only once Home Assistant has started, when automations listen for the
event. The device is created even when the sensors are registered disabled
and never added -- the entry's system option "Enable newly added entities"
off, or a wallet bought again whose sensors the user had disabled: the
notification then says that they are disabled. Only after the announcement
does the asset join the list: a reload or a stop between the mark and the
announcement loses the mark, not the announcement -- the next start creates
the wallet again, finds its asset unknown and its device there, and
announces it at once.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN, EVENT_WALLET_ADDED, notifies_new_wallets
from .devices import device_identifiers, find_entry_device
from .known_wallets import KnownWallets
from .language import entry_language
from .naming import wallet_device_asset_id, wallet_device_identifier, wallet_device_name
from .portfolio_coordinator import PortfolioConfigEntry

# What a wallet's name may not carry as it is into the notification's link:
# Markdown would read it as an escape, code, emphasis or the link's end.
_MARKDOWN_CHARACTERS = frozenset("\\`*_[]")

_LOGGER = logging.getLogger(__name__)

_TEXTS = f"component.{DOMAIN}.exceptions"


def escape_markdown(text: str) -> str:
    """`text` with a backslash before each character Markdown would read as
    syntax inside a link's text, so that it shows as it is."""
    return "".join(f"\\{char}" if char in _MARKDOWN_CHARACTERS else char for char in text)


@callback
def _is_creation(event_data: dr.EventDeviceRegistryUpdatedData) -> bool:
    """Whether the device registry reports a device created -- a new one, or
    one deleted before and brought back under its id."""
    return event_data["action"] == "create"


class WalletAnnouncer:
    """Announces the wallets new to one Portfolio entry, each once."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PortfolioConfigEntry,
        known: KnownWallets,
        group_titles: dict[str, str],
    ) -> None:
        self._hass = hass
        self._entry = entry
        self.known = known
        # Category -> group title, in the entry's language (runtime.group_titles).
        self._group_titles = group_titles
        # Asset id -> its record and the category of the group its wallet
        # went into: the wallets marked and not announced yet.
        self._pending: dict[str, tuple[dict[str, Any], str]] = {}
        # The assets whose announcement is on its way, waiting for the start's
        # end: a wallet created again before then -- its group deleted, say --
        # is no second news.
        self._scheduled: set[str] = set()

    @callback
    def mark(self, asset: dict[str, Any], category: str) -> None:
        """Announce the wallet just created for `asset`, in the group of
        `category`, once its device is created (async_listen_for_wallet_devices)
        -- or at once, when this entry has the device already: an
        announcement a reload or a stop dropped, whose device stayed."""
        asset_id = asset["id"]
        if asset_id in self._scheduled:
            return
        self._pending[asset_id] = (asset, category)
        device = self._wallet_device(dr.async_get(self._hass), asset_id)
        if device is not None:
            self._async_take(asset_id, device.id)

    def _wallet_device(
        self, dev_reg: dr.DeviceRegistry, asset_id: str
    ) -> dr.DeviceEntry | None:
        """This entry's wallet device of `asset_id`, looked up among the
        entry's own devices (devices.py): another entry's device may carry
        the same identifier."""
        entry_id = self._entry.entry_id
        return find_entry_device(dev_reg, entry_id, wallet_device_identifier(entry_id, asset_id))

    @callback
    def async_listen_for_wallet_devices(self) -> Callable[[], None]:
        """Listen for the devices Home Assistant creates, until the returned
        callable is called: at the entry's unload. The wallet device of this
        entry for a marked asset announces its wallet; any other device -- of
        another entry, the Portfolio's, a known asset's wallet -- is no news.
        Called at setup, before the manager's first refresh may create a new
        wallet's device."""
        return self._hass.bus.async_listen(
            dr.EVENT_DEVICE_REGISTRY_UPDATED, self._async_device_created, event_filter=_is_creation
        )

    @callback
    def _async_device_created(self, event: Event[dr.EventDeviceRegistryUpdatedData]) -> None:
        """Runs as Home Assistant reports a device created -- a wallet's as it
        takes in the wallet's first sensor; during another event's dispatch,
        right after it (Home Assistant 2026.7 on). It only looks the device
        up, takes the mark and schedules the announcement, nothing that could
        fail the device or its sensors."""
        if not self._pending:
            return
        dev_reg = dr.async_get(self._hass)
        device_id = event.data["device_id"]
        device = dev_reg.async_get(device_id)
        # Gone again by now, or a child device: never a wallet device.
        if not isinstance(device, dr.DeviceEntry):
            return
        entry_id = self._entry.entry_id
        for identifier in device_identifiers(device):
            asset_id = wallet_device_asset_id(entry_id, identifier)
            if asset_id is None or asset_id not in self._pending:
                continue
            # Only this entry's own wallet device of the asset announces it.
            wallet = self._wallet_device(dev_reg, asset_id)
            if wallet is not None and wallet.id == device_id:
                self._async_take(asset_id, device_id)
                return

    @callback
    def _async_take(self, asset_id: str, device_id: str) -> None:
        """Take the mark of `asset_id` and announce its wallet, on the device
        `device_id`.

        The announcement runs once Home Assistant has started -- at once
        while it runs. A start adds the wallets before automations listen:
        Home Assistant arms their triggers only as it finishes starting, and
        an event fired before would reach none. An unload drops an
        announcement still waiting; the asset is not known yet, so the
        entry's next setup marks it again -- and announces it at once, its
        device being there (mark)."""
        asset, category = self._pending.pop(asset_id)
        self._scheduled.add(asset_id)

        async def _announce(hass: HomeAssistant) -> None:
            # Up to Home Assistant 2026.6, an automation arms its trigger in a
            # listener of its own for the start's end, which may run after
            # this one: yield once, so that the event comes after them all.
            # While Home Assistant runs, the yield also lets it register the
            # wallet's other sensors first -- a disabled one without pausing,
            # an enabled one before it pauses -- so that the notification can
            # tell whether all of them are disabled.
            await asyncio.sleep(0)
            await self._async_announce(asset_id, asset, category, device_id)

        self._entry.async_on_unload(async_at_started(self._hass, _announce))

    async def _async_announce(
        self, asset_id: str, asset: dict[str, Any], category: str, device_id: str
    ) -> None:
        """The event, the notification unless switched off, and only then
        the asset in the list -- also when the notification failed: rather a
        notification missed than the event again at every start."""
        try:
            wallet = wallet_device_name(asset)
            # An interface for the users' automations: later versions may add
            # fields, never rename or drop one.
            self._hass.bus.async_fire(
                EVENT_WALLET_ADDED,
                {
                    "device_id": device_id,
                    "asset_id": asset_id,
                    "symbol": asset["symbol"],
                    "name": asset.get("name"),
                    "wallet": wallet,
                    "category": category,
                },
            )
            if notifies_new_wallets(self._entry):
                try:
                    await self._async_notify(asset_id, device_id, wallet, category)
                except Exception as err:  # noqa: BLE001 - the event has fired; the notification is extra
                    _LOGGER.warning(
                        "Could not show the notification about the new Bitpanda wallet %s (%s)",
                        wallet,
                        type(err).__name__,
                    )
        finally:
            self.known.add(asset_id)
            self._scheduled.discard(asset_id)

    async def _async_notify(
        self, asset_id: str, device_id: str, wallet: str, category: str
    ) -> None:
        """The notification, in the entry's language (language.py): Home
        Assistant shows a persistent notification as it was written, to every
        user alike. Its texts are read as the refusals to delete a device are
        (__init__._async_refusal): Home Assistant fills a text the language
        lacks with the English one. A text missing even there -- a broken
        install -- leaves the wallet without a notification, or the
        notification without its hint on disabled sensors."""
        translations = await async_get_translations(
            self._hass, entry_language(self._entry), "exceptions", {DOMAIN}
        )
        title = translations.get(f"{_TEXTS}.wallet_added_title.message")
        message = translations.get(f"{_TEXTS}.wallet_added.message")
        if not title or not message:
            return
        # hassfest allows no URL in a strings file.
        link = f"/config/devices/device/{device_id}"
        text = message.format(
            wallet=escape_markdown(wallet),
            link=link,
            group=self._group_titles.get(category, category),
        )
        hint = translations.get(f"{_TEXTS}.wallet_added_sensors_disabled.message")
        if hint and self._sensors_disabled(device_id):
            text = f"{text}\n\n{hint.format(link=link)}"
        persistent_notification.async_create(
            self._hass,
            text,
            title,
            # One per asset: announced again, it replaces one not yet dismissed.
            notification_id=f"{DOMAIN}_wallet_added_{asset_id}",
        )

    def _sensors_disabled(self, device_id: str) -> bool:
        """Whether the wallet's device has sensors and all of them are
        disabled -- by the user, by the entry's system option "Enable newly
        added entities" or with the device, whoever it was: Home Assistant
        then adds none of them, and the wallet shows nothing until the user
        enables one."""
        sensors = er.async_entries_for_device(
            er.async_get(self._hass), device_id, include_disabled_entities=True
        )
        return bool(sensors) and all(sensor.disabled for sensor in sensors)
