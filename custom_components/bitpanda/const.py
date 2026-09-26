"""Constants for the Bitpanda integration."""
from datetime import timedelta

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

# Measured 2026-09-24 with one key per scope: /portfolio needs Guthaben
# (Balance), /operations Transaktion (Transaction), /earn/configs Earn (Read).
# Trading (Read) unlocks nothing the integration calls, so it is not required.
REQUIRED_SCOPES: tuple[str, ...] = ("balance", "transaction", "earn")

# As Bitpanda's key page shows them. German label first because the German UI
# is what the maintainer verified against; the English name follows so the
# same string serves both translations.
SCOPE_LABELS: dict[str, str] = {
    "balance": "Guthaben (Balance)",
    "transaction": "Transaktion (Transaction)",
    "earn": "Earn (Read)",
}

# Stable and used in nearly every response. Verified 2026-09-24.
EUR_CURRENCY_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"

PORTFOLIO_UPDATE_INTERVAL = timedelta(minutes=5)
PRICE_UPDATE_INTERVAL_BASE = timedelta(seconds=60)
EARN_UPDATE_INTERVAL = timedelta(hours=24)
REWARDS_UPDATE_INTERVAL = timedelta(hours=1)
CHANGE_24H_UPDATE_INTERVAL = timedelta(minutes=15)

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
# group titles and the refusals to delete a device (language.py). English
# until the user picks another shipped language under Configure.
CONF_LANGUAGE = "language"
DEFAULT_LANGUAGE = "en"

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
# (bitpanda.refresh) can therefore never shorten. A completely empty
# /portfolio answer is confirmed the same way (portfolio_coordinator.py).
WALLET_REMOVAL_MISSES = 3
WALLET_REMOVAL_TIME = (WALLET_REMOVAL_MISSES - 1) * PORTFOLIO_UPDATE_INTERVAL

# The asset group of Bitpanda's Cash Plus products. They count towards the
# Portfolio's Cash Plus sensor and never get a wallet device.
CASH_PLUS_GROUP = "fiat_earn"

# Import data key: the asset records the version 1 migration hands the
# Price Tracker import flow.
IMPORT_ASSETS = "assets"


def entry_type(entry) -> str:
    """The service a config entry belongs to.

    A version 1 entry predates the field; it is the one that becomes the
    Portfolio, so it counts as one.
    """
    return entry.data.get(ENTRY_TYPE, ENTRY_TYPE_PORTFOLIO)
