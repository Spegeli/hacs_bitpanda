"""Constants for the Bitpanda integration."""
from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

DOMAIN = "bitpanda"

CONF_API_KEY = "api_key"
CONF_CURRENCY = "currency"
CONF_CURRENCY_ID = "currency_id"
CONF_TRACKED_ASSETS = "tracked_assets"
CONF_TRACKED_WALLETS = "tracked_wallets"

API_BASE_URL = "https://api.public.bitpanda.com/v1"
API_TIMEOUT = 15
MAX_PAGE_SIZE = 100

# What made a request fail, as api.py and ecb.py report it beside their
# English message for the log. Each kind has a translated text of its own
# (exceptions.update_failed_<kind>, exceptions.ecb_rates_failed_<kind> for
# the kinds an ECB fetch can have), whose only placeholders carry no words:
# the request path, an HTTP status. A 429 from Bitpanda is ERROR_RATE_LIMITED,
# not an HTTP status.
ERROR_TIMEOUT = "timeout"
ERROR_CONNECTION = "connection"
ERROR_HTTP_STATUS = "http_status"
ERROR_RATE_LIMITED = "rate_limited"
ERROR_UNREADABLE = "unreadable"
ERROR_INCOMPLETE_LISTING = "incomplete_listing"
API_ERROR_KINDS: tuple[str, ...] = (
    ERROR_TIMEOUT,
    ERROR_CONNECTION,
    ERROR_HTTP_STATUS,
    ERROR_RATE_LIMITED,
    ERROR_UNREADABLE,
    ERROR_INCOMPLETE_LISTING,
)

API_KEY_URL = "https://app.bitpanda.com/my-account/apikey"
# Bitpanda's price overview, where "Visit" on every wallet and price device
# leads: the same page for every asset type. Bitpanda has no overview of ETFs
# or ETCs, and no address for each asset that can be built reliably from its
# name and symbol (checked 2026-10-01).
PRICES_URL = "https://www.bitpanda.com/en/prices"
# The README's Troubleshooting section. A text links it through a placeholder:
# hassfest allows no URL in a strings file.
TROUBLESHOOTING_URL = "https://github.com/Spegeli/hacs_bitpanda#-troubleshooting"

# The integration's version, as its manifest states it: every device shows it
# ("Version …"). Read once, when Home Assistant imports the integration -- in
# its import executor, so no event loop waits for the file.
INTEGRATION_VERSION: str = json.loads(
    (Path(__file__).parent / "manifest.json").read_text(encoding="utf-8")
)["version"]

# Measured 2026-09-24 with one key per scope: /portfolio needs Balances,
# /operations Transaction, /earn/configs Earn (Read) -- the names on Bitpanda's
# English key page. Trade (Read) unlocks nothing the integration calls, so it
# is not required. The texts name each scope as the key page does in their
# language; the missing-permissions error takes one placeholder per scope.
REQUIRED_SCOPES: tuple[str, ...] = ("balance", "transaction", "earn")

# Stable and used in nearly every response. Verified 2026-09-24.
EUR_CURRENCY_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"

PORTFOLIO_UPDATE_INTERVAL = timedelta(minutes=5)
PRICE_UPDATE_INTERVAL_BASE = timedelta(seconds=60)
EARN_UPDATE_INTERVAL = timedelta(hours=24)
REWARDS_UPDATE_INTERVAL = timedelta(hours=1)
CHANGE_24H_UPDATE_INTERVAL = timedelta(minutes=15)

# Retry for the Earn offers and the ECB rates while they never loaded: until
# then the APRs and the other currencies have no value at all.
FIRST_LOAD_RETRY_INTERVAL = timedelta(minutes=15)

# Floor for the bitpanda.refresh cooldown, which otherwise follows the price
# interval (see __init__.py's _refresh_cooldown).
REFRESH_MIN_COOLDOWN = timedelta(seconds=10)

PORTFOLIO_TIMEFRAMES = ["DAY", "WEEK", "MONTH", "SIX_MONTH", "YEAR"]

DEFAULT_CURRENCY = "EUR"

# --- Two services -----------------------------------------------------------

# Entry data key naming the service an entry belongs to. Each service's entry
# also carries its type as its unique_id, so a second one cannot be created.
ENTRY_TYPE = "entry_type"
ENTRY_TYPE_PORTFOLIO = "portfolio"
ENTRY_TYPE_PRICE_TRACKER = "price_tracker"

PORTFOLIO_TITLE = "Bitpanda Portfolio"
PRICE_TRACKER_TITLE = "Bitpanda Price Tracker"

# Price Tracker options: currencies converted from EUR in addition to EUR.
CONF_EXTRA_CURRENCIES = "extra_currencies"

# Option of both services: the language of the integration's own texts --
# group titles, the refusals to delete a device and the Portfolio's
# notification about a new wallet (language.py). Chosen at setup, Home
# Assistant's system language offered first, and changed under Configure;
# English for an entry without it (one upgraded from version 1).
CONF_LANGUAGE = "language"
DEFAULT_LANGUAGE = "en"

# Portfolio option: whether a wallet new to the Portfolio brings a notification
# (announcements.py). Set at setup and under Configure; on for an entry
# without it. The event EVENT_WALLET_ADDED fires either way.
CONF_NOTIFY_NEW_WALLETS = "notify_new_wallets"
DEFAULT_NOTIFY_NEW_WALLETS = True
EVENT_WALLET_ADDED = f"{DOMAIN}_wallet_added"

# Portfolio option: whether new staking payouts bring a notification
# (announcements.RewardAnnouncer). Set at setup and under Configure; off for
# an entry without it. The event EVENT_STAKING_REWARD_RECEIVED fires either
# way -- for an asset whose Balance (staking) sensor is enabled, as the
# notification.
CONF_NOTIFY_STAKING_REWARDS = "notify_staking_rewards"
DEFAULT_NOTIFY_STAKING_REWARDS = False
EVENT_STAKING_REWARD_RECEIVED = f"{DOMAIN}_staking_reward_received"

# The Price Tracker keeps its assets in groups by asset type (groups.py): one
# config subentry per category, keyed by the category, whose data holds the
# category and the slim records of its assets by asset id.
SUBENTRY_TYPE_PRICE_GROUP = "price_group"
CONF_CATEGORY = "category"
CONF_ASSETS = "assets"

# The Portfolio keeps its wallet devices in groups by asset type too: one
# config subentry per category, keyed by the category, whose data holds just
# the category. The wallet manager creates and removes them; the user adds none.
SUBENTRY_TYPE_WALLET_GROUP = "wallet_group"

# Set by the version 1 migration on the Price Tracker entry it creates: the
# legacy price entities that entry adopts on its first setup.
CONF_LEGACY_ADOPT = "legacy_adopt"

# The fiat currencies Bitpanda offers (/currencies, verified 2026-09-24). The
# ECB daily reference rates cover every one of them.
SUPPORTED_CURRENCIES: tuple[str, ...] = (
    "CHF", "CZK", "DKK", "EUR", "GBP", "HUF", "NOK", "PLN", "RON", "SEK", "TRY", "USD",
)
EXTRA_CURRENCIES: tuple[str, ...] = tuple(c for c in SUPPORTED_CURRENCIES if c != "EUR")

ECB_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ECB_UPDATE_INTERVAL = timedelta(hours=6)

# The keyless ticker endpoint documents no limit. The Price Tracker holds
# itself to this many requests per hour: 30 assets at the 60 s base interval.
TICKER_HOURLY_BUDGET = 1800

# A holding is removed only after this many consecutive successful portfolio
# refreshes without it, spread over WALLET_REMOVAL_TIME at the least: the
# time they take at the regular pace, which refreshes by hand
# (bitpanda.refresh) can therefore never shorten. A Portfolio figure whose
# entry vanished from the answer -- Total value, Cash, Cash Plus -- shows 0
# only after the same (portfolio_model.FigureWatch).
WALLET_REMOVAL_MISSES = 3
WALLET_REMOVAL_TIME = (WALLET_REMOVAL_MISSES - 1) * PORTFOLIO_UPDATE_INTERVAL

# A held asset Bitpanda's catalogue does not list -- at least not yet -- is
# asked for again this long after the catalogue last answered without it
# (assets.AssetDirectory): its wallet then comes without a restart, at one
# request a day for each such asset.
UNKNOWN_ASSET_RETRY = timedelta(days=1)

# Failed refreshes in a row, spread over (FAILURE_TOLERANCE - 1) regular
# intervals at the least, that make a coordinator's sensors unavailable
# rather than clearing them at the first failure. The same rule as
# WALLET_REMOVAL_MISSES, applied to failures by streaks.FailureStreak.
FAILURE_TOLERANCE = 3

# The asset group of Bitpanda's Cash Plus products. They count towards the
# Portfolio's Cash Plus sensor and never get a wallet device.
CASH_PLUS_GROUP = "fiat_earn"

# Import data key: the asset records the version 1 migration hands the
# Price Tracker import flow.
IMPORT_ASSETS = "assets"


def notifies_new_wallets(entry: ConfigEntry) -> bool:
    """Whether a wallet new to the Portfolio `entry` brings a notification:
    its CONF_NOTIFY_NEW_WALLETS option, on for an entry without it."""
    enabled: bool = entry.options.get(CONF_NOTIFY_NEW_WALLETS, DEFAULT_NOTIFY_NEW_WALLETS)
    return enabled


def notifies_staking_rewards(entry: ConfigEntry) -> bool:
    """Whether new staking payouts of the Portfolio `entry` bring a
    notification: its CONF_NOTIFY_STAKING_REWARDS option, off for an entry
    without it."""
    enabled: bool = entry.options.get(
        CONF_NOTIFY_STAKING_REWARDS, DEFAULT_NOTIFY_STAKING_REWARDS
    )
    return enabled


def entry_type(entry: ConfigEntry) -> str:
    """The service a config entry belongs to.

    A version 1 entry predates the field; it is the one that becomes the
    Portfolio, so it counts as one.
    """
    service: str = entry.data.get(ENTRY_TYPE, ENTRY_TYPE_PORTFOLIO)
    return service
