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

# Measured 2026-09-24 with one key per scope; see umbau/02-api-basics.md.
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

# Read budget: 3000 requests/hour. Reserve headroom for portfolio, earn and rewards.
HOURLY_READ_BUDGET = 3000
PRICE_BUDGET_SHARE = 0.6

PORTFOLIO_TIMEFRAMES = ["DAY", "WEEK", "MONTH", "SIX_MONTH", "YEAR"]

DEFAULT_CURRENCY = "EUR"
