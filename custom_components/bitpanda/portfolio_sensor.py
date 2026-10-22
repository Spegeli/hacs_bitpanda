"""Sensors of the Portfolio service.

Every value is in the Portfolio currency, as Bitpanda reports it. Units of an
asset are attributes, never states.

Every sensor keeps long-term statistics: the money values as `total`, the
only state class Home Assistant allows for the monetary device class, the
returns as `measurement`. They are recorded in the Portfolio currency, so a
currency change clears them with the sensors' history (purge.py).
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from functools import partial
from typing import Any, cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .announcements import WalletAnnouncer
from .assets import ASSET_CATEGORIES, asset_attributes, asset_category
from .const import (
    API_KEY_URL,
    CONF_CURRENCY,
    DOMAIN,
    INTEGRATION_VERSION,
    PORTFOLIO_TIMEFRAMES,
    PRICES_URL,
    SUBENTRY_TYPE_WALLET_GROUP,
)
from .day_ago import DayAgoPrices, async_wallet_prices_24h_ago
from .devices import find_wallet_device
from .groups import (
    async_get_or_create_wallet_group,
    entities_by_group,
    group_of_category,
    groups_of_type,
)
from .naming import (
    PORTFOLIO_DEVICE_NAME,
    class_key,
    managed_asset_key,
    portfolio_device_identifier,
    portfolio_entity_id,
    portfolio_unique_id,
    return_key,
    staking_entity_id,
    staking_unique_id,
    total_entity_id,
    total_unique_id,
    wallet_device_identifier,
    wallet_device_name,
    wallet_entity_id,
    wallet_unique_id,
)
from .portfolio_coordinator import (
    EarnCoordinator,
    HistoryCoordinator,
    PortfolioConfigEntry,
    PortfolioCoordinator,
    PortfolioRuntime,
    RewardsCoordinator,
    WalletPrices,
)
from .portfolio_model import (
    DECIMALS,
    EarnData,
    Holding,
    PortfolioData,
    PortfolioReturns,
    PositionTotals,
    confirmed,
    last_payout_net,
    position_totals,
    return_amount,
    rewards_since,
    share_percent,
    staking_applies,
)
from .tolerance import TolerantEntity

# An Earn product's type and mode as Bitpanda sends them -> the values of the
# Staking sensor's attributes `earn_type` and `earn_mode`; any other is left
# out.
_EARN_TYPES = {"FLEXIBLE": "flexible", "LOCKED": "locked"}
_EARN_MODES = {"STAKING_EARN": "staking", "STABLE_COIN_EARN": "stable_coin"}

# The window of a Staking sensor's recent rewards, up to now.
RECENT_REWARDS = timedelta(days=30)


def portfolio_device_info(entry_id: str) -> DeviceInfo:
    """"Visit" opens the page where the user manages the API key."""
    return DeviceInfo(
        identifiers={(DOMAIN, portfolio_device_identifier(entry_id))},
        name=PORTFOLIO_DEVICE_NAME,
        manufacturer="Bitpanda",
        model="Portfolio",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=API_KEY_URL,
        sw_version=INTEGRATION_VERSION,
    )


def wallet_device_info(entry_id: str, asset: dict[str, Any]) -> DeviceInfo:
    """"Visit" opens Bitpanda's price overview; the serial number is the
    asset's ID -- the one the log names."""
    return DeviceInfo(
        identifiers={(DOMAIN, wallet_device_identifier(entry_id, asset["id"]))},
        name=wallet_device_name(asset),
        manufacturer="Bitpanda",
        model="Wallet",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=PRICES_URL,
        serial_number=asset["id"],
        sw_version=INTEGRATION_VERSION,
    )


# --- Portfolio device ------------------------------------------------------------


class _PortfolioFigure(TolerantEntity[PortfolioCoordinator], SensorEntity):
    """One figure of the whole account.

    Unavailable once a failure is confirmed (tolerance.py), not at the first
    failed update, and before the first answer. Unavailable too while the
    figure waits (PortfolioData.waiting names it by `_watch`, else `_key`): the answers no
    longer list the entry it depends on, and too few of them confirm that
    yet (PortfolioCoordinator) -- a glitch at Bitpanda then leaves a gap in
    its history, never a false 0. When the answer arrived but the figure
    cannot be told from it -- an entry that could not be read, a holding not
    classified yet, a value Bitpanda did not send -- the sensor stays
    available and its state is unknown: never a figure that quietly leaves
    something out.
    """

    _attr_has_entity_name = True
    _attr_device_class: SensorDeviceClass | None = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2
    _key: str
    # The figure (PORTFOLIO_FIGURES) whose wait this sensor shows, when it is
    # not its own key.
    _watch: str | None = None
    _attr_translation_key: str

    def __init__(
        self, coordinator: PortfolioCoordinator, entry_id: str, currency: str
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = portfolio_unique_id(entry_id, self._key)
        self.entity_id = portfolio_entity_id(self._key)
        self._attr_native_unit_of_measurement = currency
        self._attr_device_info = portfolio_device_info(entry_id)

    def _figure(self, data: PortfolioData) -> float | None:
        raise NotImplementedError

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        return None if data is None else self._figure(data)

    @property
    def available(self) -> bool:
        data: PortfolioData | None = self.coordinator.data
        watch = self._watch or self._key
        return super().available and data is not None and watch not in data.waiting


class PortfolioTotalSensor(_PortfolioFigure):
    """Every holding, Cash Plus included, plus all fiat."""

    _key = "total"
    _attr_translation_key = "total_value"

    def _figure(self, data: PortfolioData) -> float | None:
        return data.total


class PortfolioCashSensor(_PortfolioFigure):
    """Sum of the fiat balances (`balance`: locked fiat is still cash)."""

    _key = "cash"
    _attr_translation_key = "cash"

    def _figure(self, data: PortfolioData) -> float | None:
        return data.cash


class PortfolioCashPlusSensor(_PortfolioFigure):
    """Value of the Cash Plus holdings. Unknown while any holding is
    unclassified -- but one the catalogue does not list, which is none."""

    _key = "cash_plus"
    _attr_translation_key = "cash_plus"

    def _figure(self, data: PortfolioData) -> float | None:
        return data.cash_plus

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Each held Cash Plus product's own amount, keyed by currency code.

        Empty whenever `cash_plus_amounts` is None -- the state (`cash_plus`
        itself) is unknown for the same reason -- or when nothing is held:
        never a partial mapping.
        """
        data = self.coordinator.data
        if data is None:
            return {}
        return data.cash_plus_amounts or {}


class _PortfolioPositionsFigure(_PortfolioFigure):
    """A figure of all positions together -- every holding but Cash Plus:
    the wallets, and a held asset the catalogue does not list
    (PortfolioData.positions). It waits on the positions: an answer that no
    longer lists one makes it unavailable, not 0, until that is confirmed.
    Unknown while a position cannot be told, or lacks its value or its
    invested amount. Its attribute `wallets` counts the positions summed."""

    _watch = "positions"

    def _totals(self, data: PortfolioData) -> PositionTotals | None:
        positions = data.positions
        return None if positions is None else position_totals(positions.values())

    def _of(self, totals: PositionTotals) -> float | None:
        raise NotImplementedError

    def _figure(self, data: PortfolioData) -> float | None:
        totals = self._totals(data)
        return None if totals is None else self._of(totals)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        totals = None if data is None else self._totals(data)
        if totals is None or self._of(totals) is None:
            return {}
        return {"wallets": totals.count}


class PortfolioInvestedSensor(_PortfolioPositionsFigure):
    """What went into the positions, as Bitpanda reports each one's."""

    _key = "invested"
    _attr_translation_key = "invested"

    def _of(self, totals: PositionTotals) -> float | None:
        return totals.invested


class PortfolioTotalReturnSensor(_PortfolioPositionsFigure):
    """What the positions are worth beyond what went into them: open
    positions only -- /portfolio lists nothing sold."""

    _key = "total_return"
    _attr_translation_key = "total_return"

    def _of(self, totals: PositionTotals) -> float | None:
        return totals.total_return


class PortfolioTotalReturnPercentSensor(_PortfolioPositionsFigure):
    """The total return over what was invested, in percent; unknown unless
    something was invested."""

    _key = "total_return_percent"
    _attr_translation_key = "total_return_percent"
    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: PortfolioCoordinator, entry_id: str, currency: str
    ) -> None:
        super().__init__(coordinator, entry_id, currency)
        self._attr_native_unit_of_measurement = PERCENTAGE

    def _of(self, totals: PositionTotals) -> float | None:
        return totals.total_return_percent


class PortfolioClassSensor(_PortfolioFigure):
    """The value of one wallet group's wallets together, on the Portfolio
    device; it exists while its group does (PortfolioEntityManager).

    `members` gives the assets whose wallets the manager tracks in the
    group, or None while it tracks none of them. The sum is over those held
    now: a wallet waiting out its misses is left out. The manager settles
    the members after a portfolio update, which may reach this sensor first:
    `reconciled` subscribes it to every reconcile, once the wallets are
    settled, so that a wallet bought since counts with the update that
    brings it. Unavailable while none
    is held -- the group's wallets all wait out their misses, or the group
    holds only a wallet registered before a restart and not tracked since --
    never a false 0; and with Total value, whose wait it shares. Unknown in
    doubt (PortfolioData.in_doubt: an entry that cannot be read, or a
    holding not classified yet, might belong to any group) and while a
    wallet's value is unknown. Its attributes, absent while it is unknown:
    the share of Total value, what went into the wallets and their return
    (absent while one lacks its invested amount), and how many they are.
    """

    _watch = "total"

    def __init__(
        self,
        coordinator: PortfolioCoordinator,
        entry_id: str,
        currency: str,
        category: str,
        members: Callable[[], list[str] | None],
        reconciled: Callable[[CALLBACK_TYPE], CALLBACK_TYPE] | None = None,
    ) -> None:
        self._key = class_key(category)
        self._attr_translation_key = self._key
        self._members = members
        self._reconciled = reconciled
        super().__init__(coordinator, entry_id, currency)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._reconciled is not None:
            self.async_on_remove(self._reconciled(self.async_write_ha_state))

    def _holdings(self, data: PortfolioData) -> list[Holding] | None:
        """The held members' holdings; None while no member is held."""
        members = self._members() or []
        holdings = [data.holdings[asset_id] for asset_id in members if asset_id in data.holdings]
        return holdings or None

    def _figure(self, data: PortfolioData) -> float | None:
        holdings = None if data.in_doubt else self._holdings(data)
        if holdings is None:
            return None
        values = [holding.value for holding in holdings]
        if None in values:
            return None
        return round(sum(cast(list[float], values), 0.0), DECIMALS)

    @property
    def available(self) -> bool:
        data: PortfolioData | None = self.coordinator.data
        if not super().available or data is None:
            return False
        members = self._members()
        return members is not None and not data.held.isdisjoint(members)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data: PortfolioData | None = self.coordinator.data
        value = None if data is None else self._figure(data)
        if data is None or value is None:
            return {}
        # Known: _figure found held members.
        holdings = cast(list[Holding], self._holdings(data))
        attrs: dict[str, Any] = {}
        total = None if "total" in data.waiting else data.total
        share = share_percent(value, total)
        if share is not None:
            attrs["share_percent"] = share
        totals = position_totals(holdings)
        if totals is not None:
            attrs["invested_amount"] = totals.invested
            attrs["total_return"] = totals.total_return
            if totals.total_return_percent is not None:
                attrs["total_return_percent"] = totals.total_return_percent
        attrs["wallets"] = len(holdings)
        return attrs


class PortfolioReturnSensor(TolerantEntity[HistoryCoordinator], SensorEntity):
    """The portfolio's return over one timeframe, in percent.

    Unavailable once a failure is confirmed, not at the first failed
    request: the history update's (tolerance.py) or this timeframe's own
    (PortfolioReturns.failed) -- at once when there is no last return to
    show. Unknown when Bitpanda answered for it without a usable figure.

    Its attribute `return_amount` is what the percentage means in money on
    today's total value (portfolio_model.return_amount), absent while the
    total value is not known; it listens to the portfolio too, so the amount
    follows a new total value.
    """

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: HistoryCoordinator,
        entry_id: str,
        timeframe: str,
        portfolio: PortfolioCoordinator | None = None,
    ) -> None:
        super().__init__(coordinator)
        key = return_key(timeframe)
        self._timeframe = timeframe
        self._portfolio = portfolio
        self._attr_translation_key = key
        self._attr_unique_id = portfolio_unique_id(entry_id, key)
        self.entity_id = portfolio_entity_id(key)
        self._attr_device_info = portfolio_device_info(entry_id)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._portfolio is not None:
            self.async_on_remove(
                self._portfolio.async_add_listener(self._handle_coordinator_update, None)
            )

    @property
    def native_value(self) -> float | None:
        data: PortfolioReturns | None = self.coordinator.data
        return None if data is None else data.values.get(self._timeframe)

    @property
    def available(self) -> bool:
        data: PortfolioReturns | None = self.coordinator.data
        return super().available and data is not None and self._timeframe not in data.failed

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        portfolio = self._portfolio
        data: PortfolioData | None = None if portfolio is None else portfolio.data
        if portfolio is None or data is None or not portfolio.data_available:
            return {}
        if "total" in data.waiting:
            return {}
        amount = return_amount(data.total, self.native_value)
        return {} if amount is None else {"return_amount": amount}


# --- Wallet devices -----------------------------------------------------------------


def _significant(value: float) -> float:
    """`value` to 10 significant digits: a price of a token worth a fraction
    of a cent keeps its digits, which DECIMALS would cut."""
    return float(f"{value:.10g}")


def _performance(holding: Holding) -> dict[str, float]:
    """The position performance Bitpanda computes for the whole position."""
    out: dict[str, float] = {}
    for key, value in (
        ("average_buy_price", holding.avg_buy_price),
        ("invested_amount", holding.invested),
        ("total_return", holding.total_return),
        ("total_return_percent", holding.total_return_pct),
    ):
        if value is not None:
            out[key] = round(value, DECIMALS)
    return out


class _WalletPart(TolerantEntity[PortfolioCoordinator], SensorEntity):
    """One value of one holding.

    It knows nothing of the announcement of a new wallet: Home Assistant
    creates the wallet's device as it takes in the first of its sensors,
    added or registered disabled, and the creation announces the wallet
    (announcements.py).
    """

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: PortfolioCoordinator,
        entry_id: str,
        currency: str,
        asset: dict[str, Any],
        prices: WalletPrices | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._asset = asset
        self._asset_id = asset["id"]
        self._prices = prices
        self._attr_native_unit_of_measurement = currency
        self._attr_device_info = wallet_device_info(entry_id, asset)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # The price arrives after the portfolio's figures (WalletPrices).
        if self._prices is not None:
            self.async_on_remove(
                self._prices.async_listen(self._asset_id, self.async_write_ha_state)
            )

    @property
    def _holding(self) -> Holding | None:
        data = self.coordinator.data
        return None if data is None else data.holdings.get(self._asset_id)

    def _value(self, holding: Holding) -> float | None:
        raise NotImplementedError

    def _units(self, holding: Holding) -> float:
        raise NotImplementedError

    @property
    def native_value(self) -> float | None:
        holding = self._holding
        return None if holding is None else self._value(holding)

    @property
    def available(self) -> bool:
        """Unavailable once a failure is confirmed (tolerance.py), and at
        once when an answer no longer lists the asset -- it is gone, not out
        of reach -- until the manager removes the wallet. While it is listed
        (PortfolioData.held, an unreadable entry included), a value that
        cannot be told is unknown."""
        data: PortfolioData | None = self.coordinator.data
        return super().available and data is not None and self._asset_id in data.held

    def _price(self) -> float | None:
        """One unit's worth: the ticker's price of the last 15 minutes
        (WalletPrices), else none -- never the value over the units, which
        /portfolio gives in cents and which would mix with the ticker's in
        the 24-hour figures."""
        return None if self._prices is None else self._prices.price_of(self._asset_id)

    def _attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = asset_attributes(self._asset)
        holding = self._holding
        if holding is not None:
            attrs["units"] = self._units(holding)
        return attrs


class WalletSensor(_WalletPart):
    """Value of the unstaked units, named like its Total and Staking siblings
    by its part of the balance: "Vision (VSN) Wallet Balance (available)".

    Its attributes name the asset and count the units, never more: the
    position performance is on the Total sensor, which every wallet has.
    """

    _attr_translation_key = "wallet"

    def __init__(
        self,
        coordinator: PortfolioCoordinator,
        entry_id: str,
        currency: str,
        asset: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, entry_id, currency, asset)
        self._attr_unique_id = wallet_unique_id(entry_id, asset["id"])
        self.entity_id = wallet_entity_id(asset)

    def _value(self, holding: Holding) -> float | None:
        return holding.wallet_value

    def _units(self, holding: Holding) -> float:
        return round(min(holding.available, holding.balance), DECIMALS)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes()


class StakingSensor(_WalletPart):
    """Value of the staked units, with everything about Earn as attributes."""

    _attr_translation_key = "staking"

    def __init__(
        self,
        coordinator: PortfolioCoordinator,
        earn: EarnCoordinator,
        rewards: RewardsCoordinator,
        entry_id: str,
        currency: str,
        asset: dict[str, Any],
        prices: WalletPrices | None = None,
    ) -> None:
        super().__init__(coordinator, entry_id, currency, asset, prices)
        self._earn = earn
        self._rewards = rewards
        self._attr_unique_id = staking_unique_id(entry_id, asset["id"])
        self.entity_id = staking_entity_id(asset)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        for coordinator in (self._earn, self._rewards):
            self.async_on_remove(
                coordinator.async_add_listener(self._handle_coordinator_update, None)
            )
        # Staking sensors are all that keeps the rewards polled: a new one
        # catches up on totals that went stale while none was listening.
        self._rewards.async_refresh_if_stale()

    def _value(self, holding: Holding) -> float | None:
        return holding.staking_value

    def _units(self, holding: Holding) -> float:
        return holding.staked

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = self._attributes()
        earn = self._earn.data
        apr = earn.apr.get(self._asset_id) if earn is not None else None
        if apr is not None:
            # The API reports a fraction: 0.0544 means 5.44 %.
            attrs["apr_percent"] = round(apr * 100, DECIMALS)
        product = earn.products.get(self._asset_id) if earn is not None else None
        if product is not None:
            if (kind := _EARN_TYPES.get(product.type or "")) is not None:
                attrs["earn_type"] = kind
            if (mode := _EARN_MODES.get(product.mode or "")) is not None:
                attrs["earn_mode"] = mode
            attrs["earn_sold_out"] = product.sold_out
        # After a failed refresh `data` still holds the last complete totals;
        # a listing that could not be paged completely never replaces them.
        # Gross, fee and net are units of the asset; `count` counts payouts.
        rewards = (self._rewards.data or {}).get(self._asset_id)
        if rewards is not None and rewards.count:
            attrs["rewards_gross"] = rewards.gross
            attrs["rewards_fee"] = rewards.fee
            attrs["rewards_net"] = rewards.net
            # What the net units are worth today, in the Portfolio currency,
            # at the wallet's price (the ticker's, as `price` on Balance
            # (total)) -- as the Bitpanda app shows it. Never their value when
            # paid out: no endpoint prices a past date.
            holding = self._holding
            price = None if holding is None else self._price()
            if price is not None:
                attrs["rewards_net_value"] = round(rewards.net * price, 2)
            attrs["rewards_count"] = rewards.count
            attrs["rewards_last_at"] = rewards.last_at
            # The window moves with every state write -- each portfolio
            # refresh and each price: no timer.
            recent = rewards_since(rewards.payouts, dt_util.utcnow() - RECENT_REWARDS)
            attrs["rewards_net_30d"] = recent
            if price is not None:
                attrs["rewards_net_value_30d"] = round(recent * price, 2)
            last = last_payout_net(rewards)
            if last is not None:
                attrs["rewards_last_net"] = last
                if price is not None:
                    attrs["rewards_last_value"] = round(last * price, 2)
        return attrs


class WalletTotalSensor(_WalletPart):
    """Value of the whole position, with its performance, the asset's price
    and the price's change over 24 hours.

    Every wallet has one for as long as the wallet exists, staking or not:
    the performance stays on this sensor when staking starts or stops. The
    price of 24 hours ago comes from `day_ago` (day_ago.py), which every
    Balance (total) of the entry joins; the next refresh publishes it. The
    position's share of Total value is absent while either is unknown, and
    while Total value waits or is not above 0.
    """

    _attr_translation_key = "wallet_total"

    def __init__(
        self,
        coordinator: PortfolioCoordinator,
        entry_id: str,
        currency: str,
        asset: dict[str, Any],
        day_ago: DayAgoPrices | None = None,
        prices: WalletPrices | None = None,
    ) -> None:
        super().__init__(coordinator, entry_id, currency, asset, prices)
        self._attr_unique_id = total_unique_id(entry_id, asset["id"])
        self.entity_id = total_entity_id(asset)
        self._day_ago = day_ago
        self._price_24h_ago: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._day_ago is not None:
            self.async_on_remove(self._day_ago.join(self))

    def set_price_24h_ago(self, value: float | None) -> None:
        """The price of 24 hours ago (DayAgoPrices); None: none known."""
        self._price_24h_ago = value

    def _value(self, holding: Holding) -> float | None:
        return holding.value

    def _units(self, holding: Holding) -> float:
        return round(holding.balance, DECIMALS)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = self._attributes()
        holding = self._holding
        if holding is None:
            return attrs
        price = self._price()
        if price is not None:
            attrs["price"] = _significant(price)
        attrs.update(_performance(holding))
        data: PortfolioData = self.coordinator.data
        if "total" not in data.waiting:
            share = share_percent(holding.value, data.total)
            if share is not None:
                attrs["portfolio_share_percent"] = share
        then = self._price_24h_ago
        if price is not None and then:
            # What the price's change made of today's units.
            attrs["price_24h_ago"] = _significant(then)
            attrs["change_24h_pct"] = round((price - then) / then * 100, 2)
            attrs["return_24h"] = round(holding.balance * (price - then), DECIMALS)
        return attrs


# --- Lifecycle manager ---------------------------------------------------------------


_UNIQUE_IDS = {
    "wallet": wallet_unique_id,
    "staking": staking_unique_id,
    "total": total_unique_id,
}


class PortfolioEntityManager:
    """Adds and removes wallet devices as holdings appear and disappear, and
    keeps them in groups by asset type.

    Runs after every portfolio refresh; a failed refresh changes nothing.
    A holding absent from WALLET_REMOVAL_MISSES consecutive successful
    refreshes, WALLET_REMOVAL_TIME after the first of them was asked for
    (portfolio_model.confirmed), loses its sensors and device -- a wallet
    migrated from version 1 whose asset is no longer held included. At the
    regular pace the third miss removes it; refreshes by hand count, but
    never remove it sooner. Only unique_ids that name an asset UUID are ever
    removed (naming.managed_asset_key), and the value sensors of groups
    that are gone: a legacy wallet the migration could not resolve is left
    for the user.

    A wallet's Wallet and Total sensors come and go with the wallet. Its
    Staking sensor follows portfolio_model.staking_applies: added while it
    is True, removed as soon as it is False. Unknown neither adds nor
    removes one; a Staking sensor registered before a restart is added back.

    Each wallet goes, with its Total and Staking sensors, into the wallet
    group (a config subentry) of its asset's category: created when the
    first wallet of that category arrives, removed once no wallet is left in
    it. A wallet already in a group stays there, even when Bitpanda files its
    asset under another type later: a device never moves between groups.
    The Portfolio device stays outside every group. A group the user
    deleted took its devices and entities along; the next refresh brings
    back the wallets of assets still held, in a new group and under the same
    entity IDs, without reloading the entry.

    Each group has a sensor of its value on the Portfolio device
    (PortfolioClassSensor), outside every group: decided at the end of every
    successful refresh, once the groups are settled -- added while the
    group exists, its registry entry removed once the group is gone. A
    group deleted by the user comes back within the same refresh, so its
    sensor stays. Added once per group and run, it stays as the user left
    it -- disabled, say -- and comes back after a restart under the same
    registry entry.

    With an announcer, a wallet it creates for an asset the Portfolio does
    not know (portfolio_store.py) is marked as new, with the category of the
    group it goes into, before its sensors go to Home Assistant: the
    creation of the wallet's device announces it (announcements.py), and a
    device already there announces it at once. A wallet created again -- at
    a start, after a currency change or a deleted group -- is known, and no
    news. The first successful refresh without a list begins it with every
    asset held but those Bitpanda's catalogue does not list, and every asset
    whose wallet is registered, before any wallet is created: it announces
    nothing. Every successful refresh ends with the list cut to the assets
    held or whose wallet still exists -- tracked by this manager, or
    registered: a sold asset bought back before its wallet went is no news,
    a restart or reload in between included. It leaves the list once its
    wallet went -- removed after the misses, deleted by the user, gone with
    its group or with a currency change -- so that buying it again is news.
    A refresh whose answer lists nothing at all, no asset and no fiat, cuts
    nothing, and an asset whose wallet such a refresh removes leaves the list
    only once answers that list something confirm it missing, as a wallet's
    misses are confirmed: wallets coming back after Bitpanda answered empty
    are no news, even when the first answer back lists only part of them.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PortfolioConfigEntry,
        runtime: PortfolioRuntime,
        currency: str,
        add_entities: AddConfigEntryEntitiesCallback,
        announcer: WalletAnnouncer,
        day_ago: DayAgoPrices | None = None,
    ) -> None:
        self._hass = hass
        self._day_ago = day_ago
        self._entry = entry
        self._runtime = runtime
        self._currency = currency
        self._add_entities = add_entities
        self._announcer = announcer
        # Asset id -> the category of the wallet group its sensors sit in.
        self._wallets: dict[str, str] = {}
        # The assets whose Staking sensor this manager has added.
        self._staking: set[str] = set()
        # The categories whose value sensor this manager has added.
        self._classes: set[str] = set()
        # What runs once a successful reconcile has settled the wallets: the
        # value sensors' state writes (PortfolioClassSensor).
        self._on_reconciled: list[CALLBACK_TYPE] = []
        # Asset id -> its misses in a row, and when the first was asked for.
        self._misses: dict[str, tuple[int, datetime]] = {}
        # The assets whose wallet went while Bitpanda listed nothing at all:
        # known until answers that list something confirm them missing --
        # their misses in a row since, and when the first was asked for.
        self._gone_while_empty: dict[str, tuple[int, datetime] | None] = {}

    def _registered(self) -> dict[str, set[str]]:
        """Asset id -> the kinds ("wallet", "staking", "total") registered for it."""
        entry_id = self._entry.entry_id
        out: dict[str, set[str]] = {}
        ent_reg = er.async_get(self._hass)
        for reg_entry in er.async_entries_for_config_entry(ent_reg, entry_id):
            key = managed_asset_key(entry_id, reg_entry.unique_id)
            if key is not None:
                kind, asset_id = key
                out.setdefault(asset_id, set()).add(kind)
        return out

    def _registered_category(self, asset_id: str) -> str | None:
        """The category of the wallet group the sensors of `asset_id` are
        registered in; None while they are in none (a wallet migrated from
        version 1) or not registered at all."""
        entry_id = self._entry.entry_id
        ent_reg = er.async_get(self._hass)
        for unique_id in (make(entry_id, asset_id) for make in _UNIQUE_IDS.values()):
            entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
            if entity_id is None:
                continue
            # Registered: async_get_entity_id has just found it.
            subentry_id = cast(er.RegistryEntry, ent_reg.async_get(entity_id)).config_subentry_id
            group = None if subentry_id is None else self._entry.subentries.get(subentry_id)
            if group is not None and group.subentry_type == SUBENTRY_TYPE_WALLET_GROUP:
                return group.unique_id
        return None

    def _current_earn(self) -> EarnData | None:
        earn = self._runtime.earn
        return earn.data if earn.last_update_success else None

    def _remove(self, asset_id: str, kinds: tuple[str, ...], *, device: bool) -> None:
        entry_id = self._entry.entry_id
        ent_reg = er.async_get(self._hass)
        for kind in kinds:
            entity_id = ent_reg.async_get_entity_id(
                "sensor", DOMAIN, _UNIQUE_IDS[kind](entry_id, asset_id)
            )
            if entity_id is not None:
                ent_reg.async_remove(entity_id)
        if device:
            dev_reg = dr.async_get(self._hass)
            found = find_wallet_device(dev_reg, entry_id, asset_id)
            if found is not None:
                dev_reg.async_remove_device(found.id)

    @callback
    def async_reconcile(self) -> None:
        portfolio = self._runtime.portfolio
        data: PortfolioData | None = portfolio.data
        if not portfolio.last_update_success or data is None:
            return
        announcer = self._announcer
        if announcer.known.first_run:
            # No list yet -- a new setup, an upgrade, an update from a version
            # without it: the wallets found now are no news, and neither is a
            # wallet still registered -- a sold asset's waiting out its misses,
            # or one whose asset the catalogue does not list at the moment. A
            # held asset left unnamed by a failed lookup is known too, its
            # wallet coming a refresh later; one the catalogue does not list,
            # without a wallet, is not: its wallet, once listed, is news.
            announcer.known.seed((data.held - data.unlisted) | set(self._registered()))
        self._forget_wallets_without_group()
        entry_id = self._entry.entry_id
        registered = self._registered()
        earn = self._current_earn()
        # Category -> the sensors to add to its group.
        new: dict[str, list[SensorEntity]] = {}

        for asset_id in data.wallet_ids:
            asset = data.assets[asset_id]
            entities: list[SensorEntity] = []
            if asset_id not in self._wallets:
                # A wallet registered in a group stays in it, whatever its
                # asset's category says now. Moving its device to another
                # group would list it in both on Home Assistant 2025.5;
                # newer releases warn about such a move, and 2027.8 will
                # refuse it.
                sits_in = self._registered_category(asset_id)
                category = asset_category(asset) if sits_in is None else sits_in
                self._wallets[asset_id] = category
                # Before its sensors go to Home Assistant, which creates the
                # wallet's device -- and so announces the wallet -- as it
                # takes in the first of them, within this refresh.
                if asset_id not in announcer.known:
                    announcer.mark(asset, category)
                entities.append(WalletSensor(portfolio, entry_id, self._currency, asset))
                entities.append(
                    WalletTotalSensor(
                        portfolio, entry_id, self._currency, asset, self._day_ago,
                        self._runtime.prices,
                    )
                )
            applies = staking_applies(data.holdings[asset_id], earn)
            kinds = registered.get(asset_id, set())
            wanted = applies is True or (applies is None and "staking" in kinds)
            if wanted and asset_id not in self._staking:
                self._staking.add(asset_id)
                entities.append(
                    StakingSensor(
                        portfolio, self._runtime.earn, self._runtime.rewards,
                        entry_id, self._currency, asset, self._runtime.prices,
                    )
                )
            elif applies is False and (asset_id in self._staking or "staking" in kinds):
                self._staking.discard(asset_id)
                self._remove(asset_id, ("staking",), device=False)
            if entities:
                new.setdefault(self._wallets[asset_id], []).extend(entities)

        # An asset whose balances could not be read this refresh has no entry
        # in `data.holdings`, yet counts as held (PortfolioData.held), never
        # as a miss.
        held = data.held
        asked_at = data.requested_at or dt_util.utcnow()
        for asset_id in held:
            self._misses.pop(asset_id, None)
        for asset_id in (set(registered) | set(self._wallets)) - held:
            misses, since = self._misses.get(asset_id, (0, asked_at))
            misses += 1
            if not confirmed(misses, since, asked_at):
                self._misses[asset_id] = (misses, since)
                continue
            self._misses.pop(asset_id, None)
            self._wallets.pop(asset_id, None)
            self._staking.discard(asset_id)
            self._remove(asset_id, ("wallet", "staking", "total"), device=True)
            if not data.listed_any:
                self._gone_while_empty[asset_id] = None
        if data.listed_any:
            for asset_id, seen in list(self._gone_while_empty.items()):
                if asset_id in held:
                    del self._gone_while_empty[asset_id]
                    continue
                misses, since = (0, asked_at) if seen is None else seen
                misses += 1
                if confirmed(misses, since, asked_at):
                    del self._gone_while_empty[asset_id]
                else:
                    self._gone_while_empty[asset_id] = (misses, since)

        # One call per group: the group must exist before its sensors are
        # added, and the registry files each sensor and its device under it --
        # moving a sensor that is registered already, such as a migrated one.
        for category, entities in new.items():
            group = async_get_or_create_wallet_group(
                self._hass, self._entry, category, self._runtime.group_titles
            )
            self._add_entities(entities, config_subentry_id=group.subentry_id)
        self._remove_empty_groups()
        # The members are settled: the value sensors write their state again
        # -- before a gone group's sensor leaves the registry.
        for update in list(self._on_reconciled):
            update()
        self._reconcile_classes()
        if data.listed_any:
            # A held asset stays known, and so does a sold one whose wallet
            # still exists: tracked here while it waits out its misses, or
            # registered from before a restart or reload, which this manager
            # tracks only once it is held again. The registry is read afresh:
            # a wallet removed above, after its misses, counts no more. Any
            # other asset has no wallet left, and buying it again is news.
            # An answer that lists nothing at all, not even cash, cuts
            # nothing: its wallets go all the same, but listed again they
            # are no news -- and stay known until answers that list
            # something confirm them missing (_gone_while_empty).
            announcer.known.keep_only(
                data.held
                | set(self._wallets)
                | set(self._registered())
                | set(self._gone_while_empty)
            )

    def _forget_wallets_without_group(self) -> None:
        """Forget every tracked wallet whose group is gone -- deleted by the
        user, its devices and entities with it -- so that this refresh adds
        the wallet again, as if it were new: its miss count goes too."""
        for asset_id, category in list(self._wallets.items()):
            if group_of_category(self._entry, SUBENTRY_TYPE_WALLET_GROUP, category) is None:
                del self._wallets[asset_id]
                self._staking.discard(asset_id)
                self._misses.pop(asset_id, None)

    def _listen_reconciled(self, update: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Run `update` once every successful reconcile has settled the
        wallets, until the returned callback is called."""
        self._on_reconciled.append(update)
        return lambda: self._on_reconciled.remove(update)

    def _members(self, category: str) -> list[str] | None:
        """The assets whose wallets this manager tracks in the group of
        `category`; None while it tracks none of them."""
        return [asset_id for asset_id, sits_in in self._wallets.items() if sits_in == category] or None

    def _reconcile_classes(self) -> None:
        """A value sensor for every wallet group, none for a group that is
        gone: only the categories ASSET_CATEGORIES names count."""
        entry_id = self._entry.entry_id
        groups = {group.unique_id for group in groups_of_type(self._entry, SUBENTRY_TYPE_WALLET_GROUP)}
        ent_reg = er.async_get(self._hass)
        new: list[SensorEntity] = []
        for category in ASSET_CATEGORIES:
            if category in groups:
                if category not in self._classes:
                    self._classes.add(category)
                    new.append(
                        PortfolioClassSensor(
                            self._runtime.portfolio, entry_id, self._currency, category,
                            partial(self._members, category), self._listen_reconciled,
                        )
                    )
                continue
            self._classes.discard(category)
            entity_id = ent_reg.async_get_entity_id(
                "sensor", DOMAIN, portfolio_unique_id(entry_id, class_key(category))
            )
            if entity_id is not None:
                ent_reg.async_remove(entity_id)
        if new:
            self._add_entities(new)

    def _remove_empty_groups(self) -> None:
        """Remove every wallet group that no tracked wallet belongs to and
        that holds nothing of this entry any more.

        A wallet this manager does not track yet -- one registered before a
        restart, whose asset is unnamed for now or has been sold since --
        still has its sensors in its group, and keeps the group until they go.
        """
        in_use = set(self._wallets.values())
        occupied = entities_by_group(self._hass, self._entry)
        for group in groups_of_type(self._entry, SUBENTRY_TYPE_WALLET_GROUP):
            if group.unique_id in in_use or group.subentry_id in occupied:
                continue
            self._hass.config_entries.async_remove_subentry(self._entry, group.subentry_id)


@callback
def _keep_polling() -> None:
    """No-op listener that keeps a coordinator's periodic refresh alive.

    DataUpdateCoordinator only schedules its next refresh while it has at
    least one listener, and stops once the last one unsubscribes.

    The Earn coordinator's only other listeners are StakingSensors, so an
    entry with none registered -- nothing staked and nothing offered, or the
    last Staking sensor was just removed -- would freeze its catalogue
    forever at whatever the first refresh returned (or at `None` if that one
    failed), even though the manager reads it on every portfolio refresh: an
    Earn product offered later gives a wallet its Staking sensor even with
    nothing staked yet.

    The history coordinator's only other listeners are the five return
    sensors, so with all of them disabled the Portfolio card's line, which
    the card asks for through `bitpanda/portfolio_history` (cards.py), would
    freeze at its setup-time answer.
    """


async def async_setup_portfolio_entities(
    hass: HomeAssistant,
    entry: PortfolioConfigEntry,
    add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """The Portfolio device's sensors, outside every group, then the wallets
    the manager keeps current in their groups -- announcing the new ones."""
    runtime: PortfolioRuntime = entry.runtime_data
    currency = entry.data[CONF_CURRENCY]
    add_entities(
        [
            PortfolioTotalSensor(runtime.portfolio, entry.entry_id, currency),
            PortfolioCashSensor(runtime.portfolio, entry.entry_id, currency),
            PortfolioCashPlusSensor(runtime.portfolio, entry.entry_id, currency),
            PortfolioInvestedSensor(runtime.portfolio, entry.entry_id, currency),
            PortfolioTotalReturnSensor(runtime.portfolio, entry.entry_id, currency),
            PortfolioTotalReturnPercentSensor(runtime.portfolio, entry.entry_id, currency),
            *(
                PortfolioReturnSensor(
                    runtime.history, entry.entry_id, timeframe, runtime.portfolio
                )
                for timeframe in PORTFOLIO_TIMEFRAMES
            ),
        ]
    )
    announcer = WalletAnnouncer(
        hass, entry, runtime.known_wallets, runtime.group_titles, runtime.ready
    )
    # Before the first reconcile, which may create a new wallet's device.
    entry.async_on_unload(announcer.async_listen_for_wallet_devices())
    # The 24-hour references of every wallet's Balance (total), one lookup
    # for all of them.
    day_ago = DayAgoPrices(hass, async_wallet_prices_24h_ago)
    manager = PortfolioEntityManager(
        hass, entry, runtime, currency, add_entities, announcer, day_ago
    )
    manager.async_reconcile()
    entry.async_on_unload(runtime.portfolio.async_add_listener(manager.async_reconcile))
    # Keep Earn polling even without a Staking sensor around (see
    # _keep_polling). Not `manager.async_reconcile` itself: misses are
    # counted once per call, so subscribing it a second time here would
    # remove a holding after fewer than WALLET_REMOVAL_MISSES portfolio
    # refreshes.
    entry.async_on_unload(runtime.earn.async_add_listener(_keep_polling))
    # And the value history, for the Portfolio card's line.
    entry.async_on_unload(runtime.history.async_add_listener(_keep_polling))
    # And the ECB rates of a Portfolio outside EUR, which nothing else
    # listens to (portfolio_coordinator.WalletPrices reads them).
    if runtime.ecb is not None:
        entry.async_on_unload(runtime.ecb.async_add_listener(_keep_polling))
