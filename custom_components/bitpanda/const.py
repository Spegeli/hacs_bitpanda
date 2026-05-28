"""Constants for the Bitpanda integration."""
from datetime import timedelta

DOMAIN = "bitpanda"
CONF_API_KEY = "api_key"
CONF_CURRENCY = "currency"
CONF_TRACKED_ASSETS = "tracked_assets"
CONF_TRACKED_WALLETS = "tracked_wallets"

# API URLs
API_BASE_URL = "https://api.bitpanda.com/v1"

# Update intervals
PRICE_UPDATE_INTERVAL = timedelta(seconds=60)
WALLET_UPDATE_INTERVAL = timedelta(minutes=5)
CHANGE_24H_UPDATE_INTERVAL = timedelta(minutes=15)

# Asset categories
ASSET_CATEGORIES = {
    "cryptocoin": "Crypto",
    "metal": "Metals",
    "index": "Crypto Indices",
}

# Default values
DEFAULT_CURRENCY = "EUR"
