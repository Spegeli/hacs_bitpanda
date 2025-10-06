"""Constants for the Bitpanda integration."""
from datetime import timedelta

DOMAIN = "bitpanda"
CONF_API_KEY = "api_key"
CONF_CURRENCY = "currency"
CONF_TRACKED_ASSETS = "tracked_assets"
CONF_TRACKED_WALLETS = "tracked_wallets"

# API URLs
API_BASE_URL = "https://api.bitpanda.com/v1"
API_TICKER_URL = "https://api.bitpanda.com/v1/ticker"

# Update intervals
PRICE_UPDATE_INTERVAL = timedelta(seconds=60)
WALLET_UPDATE_INTERVAL = timedelta(minutes=5)

# Asset categories
ASSET_CATEGORIES = {
    "cryptocoin": "Crypto",
    "metal": "Metals",
    "commodity": "Commodities",
    "index": "Crypto Indices",
    "stock": "Stocks",
    "etf": "ETFs",
}

# Wallet grouping options
WALLET_GROUPING_INDIVIDUAL = "individual"
WALLET_GROUPING_CATEGORY = "category"

# Default values
DEFAULT_CURRENCY = "EUR"
DEFAULT_WALLET_GROUPING = WALLET_GROUPING_CATEGORY

# Sensor types
SENSOR_TYPE_PRICE = "price"
SENSOR_TYPE_WALLET = "wallet"
SENSOR_TYPE_WALLET_TOTAL = "wallet_total"
