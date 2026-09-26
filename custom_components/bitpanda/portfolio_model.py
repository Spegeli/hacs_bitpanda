"""Pure data model of the Portfolio service: no Home Assistant, no network."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging

from .const import CASH_PLUS_GROUP

_LOGGER = logging.getLogger(__name__)

# The API quotes amounts as 8-decimal strings. Anything computed from them is
# rounded to match rather than publishing float noise.
DECIMALS = 8


def to_float(container: dict | None, key: str = "value") -> float | None:
    """Read a numeric string out of an API value object."""
    if not isinstance(container, dict):
        return None
    try:
        return float(container[key])
    except (KeyError, TypeError, ValueError):
        return None


def _cash_plus_currency_code(symbol: str) -> str:
    """The currency code a Cash Plus product's amount is keyed by.

    `BCP` plus exactly three letters names the product's currency
    (`BCPEUR` -> `eur`, 1:1 with EUR regardless of the Portfolio currency).
    Any other shape -- a future product Bitpanda names differently -- falls
    back to the whole symbol, lowercased, so it still gets some key rather
    than being dropped.
    """
    if len(symbol) == 6 and symbol.startswith("BCP") and symbol[3:].isalpha():
        return symbol[3:].lower()
    return symbol.lower()


@dataclass
class Holding:
    """One asset position. `value` is the whole position in the Portfolio
    currency (`currency_balance`), or None when the API sent none -- an
    unknown value must never read as 0.

    /portfolio has no staked field: staked units are balance minus
    available_balance, and the value splits in the same proportion.
    """

    asset_id: str
    balance: float
    available: float
    value: float | None
    invested: float | None = None
    avg_buy_price: float | None = None
    total_return: float | None = None
    total_return_pct: float | None = None

    @property
    def staked(self) -> float:
        return round(max(self.balance - self.available, 0.0), DECIMALS)

    def _share(self, units: float) -> float | None:
        if self.value is None:
            return None
        if self.balance <= 0:
            return self.value if units > 0 else 0.0
        return round(self.value * units / self.balance, DECIMALS)

    @property
    def wallet_value(self) -> float | None:
        """Value of the unstaked units."""
        return self._share(min(self.available, self.balance))

    @property
    def staking_value(self) -> float | None:
        """Value of the staked units."""
        return self._share(self.staked)


@dataclass
class PortfolioData:
    """Normalised /portfolio response plus the records of the held assets.

    `assets` is filled by the coordinator from the AssetDirectory: only a
    record's `group` tells Cash Plus from a wallet, so a holding without one
    is neither, and makes Cash Plus unknown.

    An entry `parse_portfolio` could not read at all -- not even enough to
    hold a zero -- is recorded in `unparsed_assets` rather than dropped: a
    holding that just vanished would look identical to "not held", turning a
    read failure into a silently low total. The same reasoning makes `cash`
    `None` when a fiat entry's balance could not be read: `None` means
    unknown, never that there was none.
    """

    holdings: dict[str, Holding] = field(default_factory=dict)
    cash: float | None = 0.0
    assets: dict[str, dict] = field(default_factory=dict)
    unparsed_assets: set[str] = field(default_factory=set)

    def is_cash_plus(self, asset_id: str) -> bool | None:
        asset = self.assets.get(asset_id)
        if asset is None:
            return None
        return asset.get("group") == CASH_PLUS_GROUP

    @property
    def total(self) -> float | None:
        """Every holding, Cash Plus included, plus all fiat.

        None when that cannot be said with confidence: any holding value is
        unknown, `cash` is unknown, or an entry failed to parse at all
        (`unparsed_assets`) -- never a number that quietly omits it.
        """
        if self.unparsed_assets or self.cash is None:
            return None
        values = [holding.value for holding in self.holdings.values()]
        if any(value is None for value in values):
            return None
        return round(sum(values) + self.cash, DECIMALS)

    @property
    def cash_plus(self) -> float | None:
        """Cash Plus holdings only.

        None when that cannot be said with confidence: a holding is
        unclassified, its value is unknown, or an entry failed to parse at
        all and so was never classified (`unparsed_assets`) -- it might
        itself be Cash Plus.
        """
        if self.unparsed_assets:
            return None
        amount = 0.0
        for asset_id, holding in self.holdings.items():
            kind = self.is_cash_plus(asset_id)
            if kind is None:
                return None
            if kind:
                if holding.value is None:
                    return None
                amount += holding.value
        return round(amount, DECIMALS)

    @property
    def cash_plus_amounts(self) -> dict[str, float] | None:
        """Each held Cash Plus product's own amount, in its own currency.

        A Cash Plus balance is 1:1 with its product's currency no matter
        which currency the Portfolio displays -- a EUR account shown in USD
        still holds EUR Cash Plus. None under exactly the conditions that
        make `cash_plus` None -- an unclassified holding, an unparsed entry,
        or a Cash Plus holding with an unknown value -- so the attributes
        never carry a partial mapping alongside an unknown state.
        """
        if self.cash_plus is None:
            return None
        amounts: dict[str, float] = {}
        for asset_id, holding in self.holdings.items():
            if not self.is_cash_plus(asset_id):
                continue
            symbol = self.assets[asset_id].get("symbol", "")
            amounts[_cash_plus_currency_code(symbol)] = round(holding.balance, 2)
        return amounts

    @property
    def wallet_ids(self) -> list[str]:
        """Held assets that get a wallet device: resolved and not Cash Plus."""
        return [a for a in self.holdings if self.is_cash_plus(a) is False]

    @property
    def held(self) -> set[str]:
        """Every asset /portfolio listed, its balances readable or not: an
        unreadable entry is no sign of a sale."""
        return set(self.holdings) | self.unparsed_assets


def lists_nothing(entries: list[dict]) -> bool:
    """Whether a /portfolio answer lists no asset and no fiat entry at all.

    An entry with neither `asset_id` nor `currency_id` does not count:
    parse_portfolio ignores it, the same as an entry that never existed.
    """
    return not any(entry.get("asset_id") or entry.get("currency_id") for entry in entries)


def parse_portfolio(entries: list[dict]) -> PortfolioData:
    """Normalise a /portfolio response.

    The list mixes asset entries (`asset_id`, `currency_balance`, ...) and
    fiat entries (`currency_id`, `balance`), with no type field: the split is
    on `asset_id`. `currency_balance` arrives already converted into the
    requested currency and is used as given -- multiplying a balance by a
    price here is what produced issue #7.

    An entry whose balance cannot be read is never silently dropped as if it
    held nothing: an unparsable holding goes into `unparsed_assets` and an
    unparsable fiat balance makes `cash` None, so the affected figure reads
    as unknown rather than quietly low.
    """
    data = PortfolioData()
    cash = 0.0
    cash_ok = True
    for entry in entries:
        asset_id = entry.get("asset_id")
        if not asset_id:
            currency_id = entry.get("currency_id")
            if not currency_id:
                # Neither asset_id nor currency_id: not a shape this endpoint
                # documents. Ignored, same as an entry that never existed.
                continue
            # `balance`, not `available_balance`: fiat reserved by a pending
            # order is still the user's cash.
            amount = to_float(entry.get("balance"))
            if amount is None:
                _LOGGER.debug("Skipping unparsable fiat balance %s", currency_id)
                cash_ok = False
            else:
                cash += amount
            continue

        balance = to_float(entry.get("balance"))
        available = to_float(entry.get("available_balance"))
        if balance is None or available is None:
            _LOGGER.debug("Skipping unparsable holding %s", asset_id)
            data.unparsed_assets.add(asset_id)
            continue
        try:
            return_pct = float(entry["total_return_percent"])
        except (KeyError, TypeError, ValueError):
            return_pct = None
        data.holdings[asset_id] = Holding(
            asset_id=asset_id,
            balance=balance,
            available=available,
            value=to_float(entry.get("currency_balance")),
            invested=to_float(entry.get("invested_amount")),
            avg_buy_price=to_float(entry.get("average_buy_price")),
            total_return=to_float(entry.get("total_return")),
            total_return_pct=return_pct,
        )
    data.cash = round(cash, DECIMALS) if cash_ok else None
    return data


def _is_later(candidate: str | None, current: str | None) -> bool:
    """Return True when `candidate` is the later of two API timestamps.

    Comparing these as strings is wrong. The API emits both
    `2026-09-22T17:16:35Z` and `2026-09-09T18:31:22.080Z`, and within the
    same second `"." < "Z"`, so a zero-fraction timestamp sorts *above* a
    later fractional one. Parse instead, and fall back to string comparison
    only if parsing fails.
    """
    if not candidate:
        return False
    if not current:
        return True
    try:
        return datetime.fromisoformat(candidate) > datetime.fromisoformat(current)
    except (TypeError, ValueError):
        # ValueError for a malformed string; TypeError for a non-string, and
        # for comparing an offset-aware datetime against a naive one. Every
        # timestamp seen from this endpoint carries a Z, but it is undocumented
        # and a mixed batch must not raise out of a coordinator refresh.
        return str(candidate) > str(current)


@dataclass
class RewardTotals:
    """Lifetime Earn rewards for one asset, in that asset's own units."""

    gross: float = 0.0
    fee: float = 0.0
    net: float = 0.0
    count: int = 0
    last_at: str | None = None


def sum_rewards(operations: list[dict]) -> dict[str, RewardTotals]:
    """Aggregate staking rewards per asset.

    Only `operation_type == "reward"` with `wallet_owner == "staking-service"`
    counts. `earn_on_fiat_reward` is Cash Plus interest, a different product.
    The operation_type enum is open — 29 values were seen in a single account —
    so anything unrecognised is ignored rather than raising.

    The fee is charged in the reward asset and is not a fixed rate: recent
    payouts showed exactly 20 % while lifetime aggregates sat near 17 %. Always
    read `fee_amount`.
    """
    totals: dict[str, RewardTotals] = {}

    for operation in operations:
        if operation.get("operation_type") != "reward":
            continue
        for tx in operation.get("transactions", []):
            if tx.get("wallet_owner") != "staking-service":
                continue
            asset_id = tx.get("asset_id")
            gross = to_float(tx.get("asset_amount"))
            if not asset_id or gross is None:
                continue
            fee = to_float(tx.get("fee_amount")) or 0.0

            entry = totals.setdefault(asset_id, RewardTotals())
            entry.gross += gross
            entry.fee += fee
            entry.net += gross - fee
            entry.count += 1

            credited = tx.get("credited_at")
            if _is_later(credited, entry.last_at):
                entry.last_at = credited

    # The amounts are 8-decimal strings; summing them as floats leaves noise
    # such as 751.4920099999999. Rounded once, at the end, not per step.
    for entry in totals.values():
        entry.gross = round(entry.gross, DECIMALS)
        entry.fee = round(entry.fee, DECIMALS)
        entry.net = round(entry.net, DECIMALS)

    return totals


@dataclass(frozen=True)
class EarnData:
    """The Earn catalogue: APR per asset (a fraction) and the offered assets."""

    apr: dict[str, float]
    offered: frozenset[str]


def parse_earn_configs(configs: list[dict]) -> EarnData:
    """An asset is offered while it has an enabled product -- sold out or not:
    `soldout` and `enabled` are separate flags, and a sold-out product still
    pays the users already in it. The APR is a JSON number and a fraction:
    0.0544 means 5.44 %."""
    apr: dict[str, float] = {}
    offered: set[str] = set()
    for config in configs:
        asset_id = config.get("asset_id")
        if not asset_id:
            continue
        if config.get("enabled") is True:
            offered.add(asset_id)
        rate = config.get("annual_percentage_rate")
        if isinstance(rate, (int, float)) and not isinstance(rate, bool):
            apr[asset_id] = float(rate)
    return EarnData(apr=apr, offered=frozenset(offered))


def staking_applies(holding: Holding, earn: EarnData | None) -> bool | None:
    """Whether a wallet carries Staking and Total sensors.

    True while something is staked, or while Earn offers a product for the
    asset. False only when nothing is staked and a current Earn catalogue
    offers nothing. None when that cannot be told -- nothing staked and no
    current catalogue -- and the caller then keeps whatever exists.
    """
    if holding.staked > 0:
        return True
    if earn is None:
        return None
    return holding.asset_id in earn.offered
