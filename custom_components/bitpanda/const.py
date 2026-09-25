"""Constants for the Bitpanda integration."""
from datetime import timedelta

DOMAIN = "bitpanda"

CONF_API_KEY = "api_key"
CONF_CURRENCY = "currency"
CONF_CURRENCY_ID = "currency_id"
CONF_TRACKED_ASSETS = "tracked_assets"
CONF_TRACKED_WALLETS = "tracked_wallets"
CONF_ASSET_CACHE = "asset_cache"

API_BASE_URL = "https://api.public.bitpanda.com/v1"
API_TIMEOUT = 15
MAX_PAGE_SIZE = 100

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

# Read budget: 3000 requests/hour. Reserve headroom for portfolio, earn and rewards.
HOURLY_READ_BUDGET = 3000
PRICE_BUDGET_SHARE = 0.6

PORTFOLIO_TIMEFRAMES = ["DAY", "WEEK", "MONTH", "SIX_MONTH", "YEAR"]

DEFAULT_CURRENCY = "EUR"

# Portfolio amounts (`currency_balance`) are rounded to cents. A figure derived
# from one -- a held asset's unit price (value / balance) or, without cash, the
# exchange rate (the same holding valued in two currencies) -- is only trusted
# from a value of 50 upwards, where the rounding stays near 0.01 %. Below it the
# error grows to whole percent (0.04 over 9.41652 units lies anywhere in a
# +-12 % band; 0.04 EUR shown as 0.05 USD claims a rate of 1.25), and dust valued
# at 0.00 would publish a price of 0.
MIN_PORTFOLIO_DERIVED_VALUE = 50.0

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

# One config subentry per tracked asset; its data holds the slim asset record.
SUBENTRY_TYPE_ASSET = "asset"
CONF_ASSET = "asset"

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
# refreshes without it.
WALLET_REMOVAL_MISSES = 3

# The asset group of Bitpanda's Cash Plus products. They count towards the
# Portfolio's Cash Plus sensor and never get a wallet device.
CASH_PLUS_GROUP = "fiat_earn"
