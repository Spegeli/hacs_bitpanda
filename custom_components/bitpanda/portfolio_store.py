"""What the Portfolio remembers: one file per entry, a section per feature.

`.storage/bitpanda.portfolio.<entry_id>` holds:

- `known_wallets` (KnownWallets): the assets whose wallet is no news to the
  Portfolio. The wallet lifecycle manager creates wallet entities at every
  start, after a currency change and after a deleted group: which wallet is
  new to the Portfolio -- and gets the event and the notification of
  announcements.py -- cannot be told from that. This list tells it: the
  assets announced before, and those there when the list began. There is no
  list before the first refresh after a setup, an upgrade or an update from a
  version without it: that refresh fills it with what is held -- but for the
  assets Bitpanda's catalogue does not list -- and with every asset whose
  wallet is registered (portfolio_sensor.py), and announces nothing
  (`first_run`). An asset joins the list when its wallet is announced, and
  leaves it once it is neither held nor has a wallet (`keep_only`).
- `known_rewards` (RewardMarks): per asset, when the newest staking payout
  announced was credited (announcements.RewardAnnouncer). The first
  successful rewards refresh without it marks every asset's newest payout
  and announces nothing. A mark stays as long as the entry: it is what keeps
  an asset sold and bought back from announcing its old payouts again.

Each section is read on its own. A missing one is that feature's first run,
quietly: another section may have begun the file. A malformed one is a first
run too, with that feature's warning; a file that cannot be read at all is
every section's. Saving keeps the sections this code does not know -- a
newer version's, after a downgrade.

One store per entry, kept across its reloads (async_get_portfolio_store), is
the file's only writer: the sections change in memory, on the event loop,
and each change asks for one delayed save of all of them -- two writers on
one file would overwrite each other's sections. A reload never reads a file
whose last change still waits in a delayed save, and removing the entry
cancels such a save before deleting the file.
"""
from __future__ import annotations

from collections.abc import Callable, Collection, Iterable, Mapping
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
_WALLETS = "known_wallets"
_REWARDS = "known_rewards"
# hass.data key of the stores, by entry id: they outlive the entries' reloads.
_STORES = f"{DOMAIN}_portfolio_stores"
# The type name a section reports for a value of the wrong shape.
_MALFORMED = ValueError.__name__


def _storage_key(entry_id: str) -> str:
    return f"{DOMAIN}.portfolio.{entry_id}"


def _section_value(
    raw: object, read_error: str | None, valid: Callable[[object], bool], warning: str
) -> Any:
    """`raw` when it is a section's value, else None: quietly for a missing
    section, with `warning` (one %s, the error's type name) for a malformed
    one or a file that could not be read. Rather a wallet or a payout not
    announced than every one announced."""
    error = read_error
    if error is None and raw is not None:
        if valid(raw):
            return raw
        error = _MALFORMED
    if error is not None:
        _LOGGER.warning(warning, error)
    return None


class PortfolioStore:
    """The file of one Portfolio entry, and its sections once loaded."""

    known_wallets: KnownWallets
    reward_marks: RewardMarks

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, _storage_key(entry_id)
        )
        # The file's sections as read, unknown ones included; each section
        # writes its own back here.
        self._data: dict[str, Any] = {}

    async def async_load(self) -> None:
        """Read the file and build the sections from it."""
        read_error: str | None = None
        try:
            data = await self._store.async_load()
        except Exception as err:  # noqa: BLE001 - a lost file is a first run, never a failure
            data, read_error = None, type(err).__name__
        if isinstance(data, dict):
            self._data = dict(data)
        elif data is not None:
            read_error = _MALFORMED
        self.known_wallets = KnownWallets(self, self._data.get(_WALLETS), read_error)
        self.reward_marks = RewardMarks(self, self._data.get(_REWARDS), read_error)

    def write_section(self, key: str, value: Any) -> None:
        """Set the section `key` to `value` and ask for the delayed save."""
        self._data[key] = value
        self._store.async_delay_save(self._data_to_save, _SAVE_DELAY)

    async def async_remove(self) -> None:
        """Delete the file, a save still waiting included."""
        await self._store.async_remove()

    def _data_to_save(self) -> dict[str, Any]:
        return dict(self._data)


def _is_asset_list(raw: object) -> bool:
    return isinstance(raw, list) and all(isinstance(asset, str) for asset in raw)


def _is_mark_map(raw: object) -> bool:
    return isinstance(raw, dict) and all(
        isinstance(asset, str) and isinstance(mark, str) for asset, mark in raw.items()
    )


class KnownWallets:
    """The assets of one Portfolio entry whose wallet was announced, or that
    were there when the list began: the section `known_wallets`."""

    def __init__(self, store: PortfolioStore, raw: object, read_error: str | None) -> None:
        self._store = store
        assets = _section_value(
            raw,
            read_error,
            _is_asset_list,
            "Could not read which Bitpanda wallets were announced before (%s); "
            "the wallets held now count as known",
        )
        # None while there is no list: before the first refresh fills it.
        self._assets: set[str] | None = None if assets is None else set(assets)

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

    def _save(self) -> None:
        self._store.write_section(_WALLETS, sorted(self._assets or ()))


class RewardMarks:
    """Per asset of one Portfolio entry, when the newest staking payout
    announced was credited: the section `known_rewards`."""

    def __init__(self, store: PortfolioStore, raw: object, read_error: str | None) -> None:
        self._store = store
        marks = _section_value(
            raw,
            read_error,
            _is_mark_map,
            "Could not read which Bitpanda staking rewards were announced before (%s); "
            "the payouts listed now count as known",
        )
        # None while there are no marks: before the first refresh sets them.
        self._marks: dict[str, str] | None = None if marks is None else dict(marks)

    @property
    def first_run(self) -> bool:
        """Whether there are no marks yet."""
        return self._marks is None

    def seed(self, marks: Mapping[str, str]) -> None:
        """Begin the marks with `marks`: asset id -> credited_at."""
        self._marks = dict(marks)
        self._save()

    def __len__(self) -> int:
        """How many assets have a mark: none before the marks begin."""
        return 0 if self._marks is None else len(self._marks)

    def mark_of(self, asset_id: str) -> str | None:
        """When the newest payout of `asset_id` announced was credited;
        None for an asset without a mark."""
        return None if self._marks is None else self._marks.get(asset_id)

    def advance(self, asset_id: str, credited_at: str) -> None:
        """Mark `asset_id` at `credited_at`; nothing before the marks begin,
        and no save when the mark stays the same."""
        if self._marks is None or self._marks.get(asset_id) == credited_at:
            return
        self._marks[asset_id] = credited_at
        self._save()

    def _save(self) -> None:
        self._store.write_section(_REWARDS, dict(sorted((self._marks or {}).items())))


async def async_get_portfolio_store(hass: HomeAssistant, entry_id: str) -> PortfolioStore:
    """The store of the Portfolio entry `entry_id`, loaded once and kept
    across its reloads."""
    stores: dict[str, PortfolioStore] = hass.data.setdefault(_STORES, {})
    store = stores.get(entry_id)
    if store is None:
        store = PortfolioStore(hass, entry_id)
        await store.async_load()
        stores[entry_id] = store
    return store


async def async_remove_portfolio_store(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the store of a Portfolio entry being removed, with its file."""
    store = hass.data.get(_STORES, {}).pop(entry_id, None)
    if store is None:
        store = PortfolioStore(hass, entry_id)
    await store.async_remove()
