"""The Portfolio's announcements: a wallet new to the Portfolio, and new
staking payouts.

Each is an event, whether its notification is switched on or not -- an
interface for the users' automations -- and a persistent notification while
the entry's option for it is on (on by default for new wallets, off for
staking rewards), in the entry's language, linking to the wallet's device.
During a start, both wait until Home Assistant has started: it arms the
automations' triggers only as it finishes starting, and an event fired
before would reach none.

A new wallet (WalletAnnouncer). The wallet lifecycle manager
(portfolio_sensor.py) creates wallet entities at every start, after a
currency change and after a deleted group; it marks a wallet it creates as
new only when the Portfolio's list (portfolio_store.KnownWallets) does not
know its asset. Home Assistant creates the wallet's device as it takes in
the first of the wallet's sensors -- or brings back the device deleted with
the wallet before, under its id, which it reports as created too -- and that
creation announces the wallet, so the notification can link to the device.
The device is created even when the sensors are registered disabled and
never added -- the entry's system option "Enable newly added entities" off,
or a wallet bought again whose sensors the user had disabled: the
notification then says that they are disabled. Only after the announcement
does the asset join the list: a reload or a stop between the mark and the
announcement loses the mark, not the announcement -- the next start creates
the wallet again, finds its asset unknown and its device there, and
announces it at once.

New staking payouts (RewardAnnouncer). The rewards coordinator calls the
announcer after every successful refresh -- hourly while an enabled Staking
sensor listens, and at every setup, reload and start -- and never as a
listener, which would keep it reading the whole history every hour with
every Staking sensor disabled. The Portfolio keeps a mark per asset, when the
newest payout announced was credited (portfolio_store.RewardMarks); the
first refresh without marks marks every asset's newest payout and announces
nothing. After that the payouts credited after an asset's mark are new: one
event and one notification for all of them, with their number and their
sum, and the mark moves on to the newest -- payouts missed in a pause come
together. An asset is announced only while its Balance (staking) sensor is
registered for the entry and enabled and the Portfolio's data names it;
otherwise its mark stays, and its payouts wait. One pass at a time announces
them, reading the newest data as it runs; once it has fired its first event
it awaits nothing, so an unload cancels a pass before it announced anything
or not at all, and each payout is announced once.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.translation import async_get_translations

from .const import (
    CONF_CURRENCY,
    DOMAIN,
    EVENT_STAKING_REWARD_RECEIVED,
    EVENT_WALLET_ADDED,
    notifies_new_wallets,
    notifies_staking_rewards,
)
from .devices import device_identifiers, find_entry_device
from .language import entry_language
from .naming import (
    staking_unique_id,
    wallet_device_asset_id,
    wallet_device_identifier,
    wallet_device_name,
)
from .portfolio_coordinator import (
    PortfolioConfigEntry,
    PortfolioCoordinator,
    RewardsCoordinator,
)
from .portfolio_model import DECIMALS, PortfolioData, RewardPayout, payouts_after, time_key
from .portfolio_store import KnownWallets, RewardMarks

# What a wallet's name or an asset's symbol may not carry as it is into a
# notification's link or bold text: Markdown would read it as an escape,
# code, emphasis or the link's end.
_MARKDOWN_CHARACTERS = frozenset("\\`*_[]")

_LOGGER = logging.getLogger(__name__)

_TEXTS = f"component.{DOMAIN}.exceptions"


def escape_markdown(text: str) -> str:
    """`text` with a backslash before each character Markdown would read as
    syntax inside a link's text or bold text, so that it shows as it is."""
    return "".join(f"\\{char}" if char in _MARKDOWN_CHARACTERS else char for char in text)


async def _async_texts(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, str]:
    """The `exceptions` texts, where the notifications' texts live, in the
    language of `entry` (language.py): Home Assistant shows a persistent
    notification as it was written, to every user alike. Read as the
    refusals to delete a device are (__init__._async_refusal): Home
    Assistant fills a text the language lacks with the English one."""
    return await async_get_translations(hass, entry_language(entry), "exceptions", {DOMAIN})


def _device_link(device_id: str) -> str:
    """The link to the page of the device `device_id`, which the texts take
    as a placeholder: hassfest allows no URL in a strings file."""
    return f"/config/devices/device/{device_id}"


def format_amount(value: float, language: str) -> str:
    """`value` units of an asset, as a notification in `language` shows
    them: the API's 8 decimals at most, without trailing zeros -- 10, not
    10.00000000."""
    return _localized(f"{value:.{DECIMALS}f}".rstrip("0").rstrip("."), language)


def format_money(value: float, language: str) -> str:
    """`value` in the Portfolio currency, as a notification in `language`
    shows it: with 2 decimals."""
    return _localized(f"{value:.2f}", language)


# The decimal separator of every language this integration ships. A language
# added under translations/ needs its place here too -- a test checks that
# each shipped language has one; until then, and for any other language, a
# point, the English way, rather than a guess.
DECIMAL_COMMA = frozenset({"de", "fr", "nl", "it", "es", "pl"})
DECIMAL_POINT = frozenset({"en"})


def _localized(number: str, language: str) -> str:
    """`number`, written with a decimal point, with the decimal separator of
    `language`. No thousands separator in any language."""
    return number.replace(".", ",") if language in DECIMAL_COMMA else number


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
        """The notification, in the entry's language (_async_texts). A text
        missing even in English -- a broken install -- leaves the wallet
        without a notification, or the notification without its hint on
        disabled sensors."""
        translations = await _async_texts(self._hass, self._entry)
        title = translations.get(f"{_TEXTS}.wallet_added_title.message")
        message = translations.get(f"{_TEXTS}.wallet_added.message")
        if not title or not message:
            return
        link = _device_link(device_id)
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


def _warn_reward_notification_failed(wallet: str, error: str) -> None:
    """Log that the notification about the staking rewards of `wallet`
    could not be shown, `error` naming the type of the error: its message
    and its traceback stay out of the log."""
    _LOGGER.warning(
        "Could not show the notification about the staking rewards of %s (%s)", wallet, error
    )


class RewardAnnouncer:
    """Announces the new staking payouts of one Portfolio entry, each once."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PortfolioConfigEntry,
        marks: RewardMarks,
        rewards: RewardsCoordinator,
        portfolio: PortfolioCoordinator,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._marks = marks
        self._rewards = rewards
        self._portfolio = portfolio
        # A refresh came while Home Assistant had not started yet: a pass
        # runs once it has.
        self._due = False
        # The pass on its way, or the last one.
        self._pass: asyncio.Task[None] | None = None
        # Once, not at every refresh: however many refreshes come during a
        # start, one pass follows its end. An unload drops it with a pass
        # still due -- the marks unchanged, so the next start announces.
        entry.async_on_unload(async_at_started(hass, self._async_started))

    @callback
    def async_rewards_refreshed(self) -> None:
        """After every successful refresh of the rewards
        (RewardsCoordinator.on_refreshed): the first one without marks
        begins them, and announces nothing; any other has a pass announce
        what is new, unless one is on its way already -- it reads the newest
        data as it runs."""
        totals = self._rewards.data
        if totals is None:
            return
        if self._marks.first_run:
            # A new setup, an update from a version without the marks, an
            # unreadable section: every payout listed now is no news -- held
            # or not, with a Staking sensor or not.
            self._marks.seed(
                {
                    asset_id: asset.payouts[-1].credited_at
                    for asset_id, asset in totals.items()
                    if asset.payouts
                }
            )
            return
        if self._due or (self._pass is not None and not self._pass.done()):
            return
        if self._hass.state is not CoreState.running:
            self._due = True
            return
        self._start_pass()

    @callback
    def _async_started(self, hass: HomeAssistant) -> None:
        """Home Assistant has started: the pass a refresh left due runs."""
        if self._due:
            self._due = False
            self._start_pass()

    @callback
    def _start_pass(self) -> None:
        # A background task of the entry, which its unload cancels.
        self._pass = self._entry.async_create_background_task(
            self._hass, self._async_pass(), f"{DOMAIN} staking reward announcement"
        )

    async def _async_pass(self) -> None:
        """Announce, per asset, the payouts after its mark.

        Its awaits all come before its first event: an unload cancels a
        pass before it has announced anything, never halfway, so the marks
        are as they were and the next pass announces it all, once."""
        # Up to Home Assistant 2026.6, an automation arms its trigger in a
        # listener of its own for the start's end, which may run after the
        # one that started this pass: yield once, so that the events come
        # after them all.
        await asyncio.sleep(0)
        texts: dict[str, str] | None = None
        texts_error: str | None = None
        if notifies_staking_rewards(self._entry):
            # An unload's cancellation is no Exception: it still ends the
            # pass here, before its first event.
            try:
                texts = await _async_texts(self._hass, self._entry)
            except Exception as err:  # noqa: BLE001 - the events and the marks come all the same
                texts_error = type(err).__name__
        self._announce(texts, texts_error)

    @callback
    def _announce(self, texts: dict[str, str] | None, texts_error: str | None) -> None:
        """The events, the marks and the notifications, with nothing awaited
        in between. `texts` are the notification's, None while it is
        switched off -- or while `texts_error` names the type of the error
        that kept them from loading: each asset announced then logs it, as a
        notification that failed does."""
        # Never None: setup makes this announcer once the Portfolio's first
        # refresh has succeeded.
        portfolio = self._portfolio.data
        news = [
            (asset_id, payouts)
            for asset_id, totals in (self._rewards.data or {}).items()
            if (payouts := payouts_after(totals.payouts, self._marks.mark_of(asset_id)))
        ]
        # In the order they were paid, each asset by its newest payout.
        news.sort(key=lambda item: time_key(item[1][-1].credited_at))
        for asset_id, payouts in news:
            device_id = self._wallet_device_id(asset_id, portfolio)
            if device_id is not None:
                self._announce_asset(asset_id, payouts, device_id, portfolio, texts, texts_error)

    def _wallet_device_id(self, asset_id: str, portfolio: PortfolioData) -> str | None:
        """The wallet device of `asset_id` while its payouts may be
        announced: the Portfolio's data names the asset -- its name, its
        symbol and its price -- and its Balance (staking) sensor is
        registered for this entry and enabled. None otherwise: its mark
        stays, and its payouts come together once it may be announced.

        The entity registry, not the sensor itself: a setup refreshes the
        rewards before it adds the sensors, and the registry knows them from
        before."""
        if asset_id not in portfolio.assets:
            return None
        ent_reg = er.async_get(self._hass)
        entity_id = ent_reg.async_get_entity_id(
            "sensor", DOMAIN, staking_unique_id(self._entry.entry_id, asset_id)
        )
        sensor = None if entity_id is None else ent_reg.async_get(entity_id)
        if sensor is None or sensor.disabled or sensor.config_entry_id != self._entry.entry_id:
            return None
        return sensor.device_id

    def _announce_asset(
        self,
        asset_id: str,
        payouts: list[RewardPayout],
        device_id: str,
        portfolio: PortfolioData,
        texts: dict[str, str] | None,
        texts_error: str | None,
    ) -> None:
        """The event about `payouts`, the payouts of `asset_id` after its
        mark; the mark on the newest of them; then the notification, if
        `texts` are given -- or the warning that it could not be shown, if
        `texts_error` is."""
        asset = portfolio.assets[asset_id]
        wallet = wallet_device_name(asset)
        newest = payouts[-1].credited_at
        net = round(sum(payout.net for payout in payouts), DECIMALS)
        holding = portfolio.holdings.get(asset_id)
        price = None if holding is None else holding.price
        # At today's price, as the Staking sensor's rewards_net_value: no
        # endpoint prices a past date.
        value = None if price is None else round(net * price, 2)
        # An interface for the users' automations: later versions may add
        # fields, never rename or drop one.
        self._hass.bus.async_fire(
            EVENT_STAKING_REWARD_RECEIVED,
            {
                "device_id": device_id,
                "asset_id": asset_id,
                "symbol": asset["symbol"],
                "name": asset.get("name"),
                "wallet": wallet,
                "count": len(payouts),
                "gross": round(sum(payout.gross for payout in payouts), DECIMALS),
                "fee": round(sum(payout.fee for payout in payouts), DECIMALS),
                "net": net,
                "value": value,
                "currency": self._entry.data[CONF_CURRENCY],
                "credited_at": newest,
            },
        )
        # Before the notification, whatever becomes of it: rather a
        # notification missed than the payouts announced again.
        self._marks.advance(asset_id, newest)
        if texts_error is not None:
            _warn_reward_notification_failed(wallet, texts_error)
        elif texts is not None:
            try:
                self._notify(
                    texts, asset_id, device_id, wallet,
                    symbol=asset["symbol"], count=len(payouts), net=net, value=value,
                )
            except Exception as err:  # noqa: BLE001 - the event has fired; the notification is extra
                _warn_reward_notification_failed(wallet, type(err).__name__)

    def _notify(
        self,
        texts: dict[str, str],
        asset_id: str,
        device_id: str,
        wallet: str,
        *,
        symbol: str,
        count: int,
        net: float,
        value: float | None,
    ) -> None:
        """The notification about `count` payouts of `net` units in all, in
        the entry's language: the net amount alone, what reaches the wallet
        -- the event keeps gross and fee -- and, with a price, what it is
        worth today. A text missing even in English -- a broken install --
        leaves the payouts without a notification, or the notification
        without its value."""
        title = texts.get(f"{_TEXTS}.staking_reward_title.message")
        key = "staking_reward" if count == 1 else "staking_rewards"
        message = texts.get(f"{_TEXTS}.{key}.message")
        if not title or not message:
            return
        language = entry_language(self._entry)
        text = message.format(
            wallet=escape_markdown(wallet),
            link=_device_link(device_id),
            count=count,
            net=format_amount(net, language),
            symbol=escape_markdown(symbol),
        )
        worth = texts.get(f"{_TEXTS}.staking_reward_value.message")
        if value is not None and worth:
            money = format_money(value, language)
            text = f"{text} {worth.format(value=money, currency=self._entry.data[CONF_CURRENCY])}"
        persistent_notification.async_create(
            self._hass,
            text,
            title,
            # One per asset: the next announcement replaces one not yet dismissed.
            notification_id=f"{DOMAIN}_staking_reward_{asset_id}",
        )
