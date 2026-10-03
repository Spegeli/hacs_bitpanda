"""The Portfolio's memory of the assets whose wallet is no news to it.

The wallet lifecycle manager creates wallet entities at every start, after a
currency change and after a deleted group: which wallet is new to the
Portfolio -- and gets the event and the notification of announcements.py --
cannot be told from that. This list tells it: per Portfolio entry, in Home
Assistant's storage (`.storage/bitpanda.portfolio.<entry_id>`), the assets
announced before, and those there when the list began.

There is no list before the first refresh after a setup, an upgrade or an
update from a version without it: that refresh fills it with what is held --
but for the assets Bitpanda's catalogue does not list -- and with every
asset whose wallet is registered (portfolio_sensor.py), and announces
nothing (`first_run`). An asset joins the list when its wallet
is announced, and leaves it once it is neither held nor has a wallet
(`keep_only`).

One list per entry, kept across its reloads (async_get_known_wallets): a
reload never reads a file whose last change still waits in a delayed save,
and removing the entry cancels such a save before deleting the file.
"""
from __future__ import annotations

from collections.abc import Collection, Iterable
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_STORAGE_VERSION = 1
# Seconds a change waits before it is written: one write for the changes of
# one refresh. Home Assistant writes a waiting change when it stops.
_SAVE_DELAY = 1
_FIELD = "known_wallets"
# hass.data key of the lists, by entry id: they outlive the entries' reloads.
_LISTS = f"{DOMAIN}_known_wallets"


def _storage_key(entry_id: str) -> str:
    return f"{DOMAIN}.portfolio.{entry_id}"


class KnownWallets:
    """The assets of one Portfolio entry whose wallet was announced, or that
    were there when the list began."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, _storage_key(entry_id)
        )
        # None while there is no list: before the first refresh fills it.
        self._assets: set[str] | None = None

    async def async_load(self) -> None:
        """Read the stored list. A file that cannot be read counts as none:
        rather a wallet not announced than every held wallet announced."""
        try:
            data = await self._store.async_load()
            if data is None:
                return
            assets = data.get(_FIELD)
            if not isinstance(assets, list) or not all(isinstance(a, str) for a in assets):
                raise ValueError(_FIELD)
        except Exception as err:  # noqa: BLE001 - a lost list is a first run, never a failure
            _LOGGER.warning(
                "Could not read which Bitpanda wallets were announced before (%s); "
                "the wallets held now count as known",
                type(err).__name__,
            )
            return
        self._assets = set(assets)

    @property
    def first_run(self) -> bool:
        """Whether there is no list yet."""
        return self._assets is None

    def __contains__(self, asset_id: object) -> bool:
        return self._assets is not None and asset_id in self._assets

    def seed(self, asset_ids: Iterable[str]) -> None:
        """Begin the list with `asset_ids`."""
        self._assets = set(asset_ids)
        self._save()

    def add(self, asset_id: str) -> None:
        """Take `asset_id` into the list. Only seed begins a list: a list
        begun with one asset would have the next start announce every other
        held wallet."""
        if self._assets is not None and asset_id not in self._assets:
            self._assets.add(asset_id)
            self._save()

    def keep_only(self, asset_ids: Collection[str]) -> None:
        """Drop every asset not in `asset_ids`; save only on a change.
        Nothing before the list begins."""
        if self._assets is None:
            return
        kept = self._assets.intersection(asset_ids)
        if kept != self._assets:
            self._assets = kept
            self._save()

    async def async_remove(self) -> None:
        """Delete the file, a save still waiting included."""
        await self._store.async_remove()

    def _save(self) -> None:
        self._store.async_delay_save(self._data_to_save, _SAVE_DELAY)

    def _data_to_save(self) -> dict[str, Any]:
        return {_FIELD: sorted(self._assets or ())}


async def async_get_known_wallets(hass: HomeAssistant, entry_id: str) -> KnownWallets:
    """The list of the Portfolio entry `entry_id`, loaded once and kept
    across its reloads."""
    lists: dict[str, KnownWallets] = hass.data.setdefault(_LISTS, {})
    known = lists.get(entry_id)
    if known is None:
        known = KnownWallets(hass, entry_id)
        await known.async_load()
        lists[entry_id] = known
    return known


async def async_remove_known_wallets(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the list of a Portfolio entry being removed, with its file."""
    known = hass.data.get(_LISTS, {}).pop(entry_id, None)
    if known is None:
        known = KnownWallets(hass, entry_id)
    await known.async_remove()
