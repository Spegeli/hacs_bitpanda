<p align="center">
  <img src="https://raw.githubusercontent.com/Spegeli/hacs_bitpanda/main/logo.png" alt="Bitpanda Logo" width="300">
</p>

# 🚀 Bitpanda – Home Assistant Integration

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg"></a>
  <a href="https://github.com/Spegeli/hacs_bitpanda/releases"><img src="https://img.shields.io/github/v/release/Spegeli/hacs_bitpanda.svg?label=release&color=blue"></a>
  <img src="https://img.shields.io/badge/License-MIT-green.svg">
</p>

A custom <a href="https://www.home-assistant.io/">Home Assistant</a> integration to monitor your **Bitpanda portfolio** directly from your dashboard — track live asset prices and your wallet balances in one place.

---

## ✨ Features

### Price Tracker
- Live prices for any asset available on Bitpanda (crypto, metals, indices)
- Supports multiple currencies (EUR, USD, CHF, GBP, and more)
- Updates every 60 seconds
- Automatic decimal precision based on actual API values
- 24h price change (`change_24h_pct`) available as entity attribute, powered by the Home Assistant recorder

### Wallet Monitor
- Displays the current value of your Bitpanda wallets in your selected currency
- Supports crypto wallets, metal wallets, index wallets and fiat wallets
- Wallet values update automatically whenever the price changes
- Raw coin/token balance always available as entity attribute

### Portfolio Total
- A single sensor showing the combined value of all tracked wallets
- Includes a per-asset value breakdown as an entity attribute

### Manual Refresh
- Call the `bitpanda.refresh` service to trigger an immediate update of all price and wallet data outside of the regular update intervals

### Supported Assets
| Type | Description | Examples | Price Tracker | Wallet Monitor |
|------|-------------|----------|---------------|----------------|
| 🪙 **Cryptocurrencies** | All cryptocurrencies available on Bitpanda | BTC, ETH, ADA, SOL, XRP, etc. | ✅ | ✅ |
| 🥇 **Metals** | Tokenized precious metals | XAU (Gold), XAG (Silver), XPT (Platinum), XPD (Palladium) | ✅ | ✅ |
| 📊 **Indices** | Bitpanda Crypto Indices | BCI5, BCI10, BCI25, BCISL, etc. | ✅ | ✅ |
| 💶 **Fiat** | Fiat currencies | EUR, USD, CHF, GBP, etc. | ❌ | ✅ |
| 📈 **Stocks** | Stocks & shares | AAPL, MSFT, TSLA, etc. | ❌ | ❌ |
| 🏦 **ETFs** | Exchange Traded Funds | S&P 500, NASDAQ 100, DAX, etc. | ❌ | ❌ |
| 🛢️ **Commodities** | Commodities | Oil, Gas, Wheat, etc. | ❌ | ❌ |

> **My stocks, ETFs or commodities are not showing up?**
> 
> This is expected. Stocks, ETFs and commodities are not supported as they are not included in the public Bitpanda Price Ticker API.

---

## 📋 Requirements

- Home Assistant **2025.1** or newer
- A [Bitpanda](https://www.bitpanda.com) account
- A Bitpanda API key ([create one here](https://web.bitpanda.com/apikey))

---

## 📦 Installation

### Via HACS (recommended)

Click the button below to automatically add the repository to HACS:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Spegeli&repository=hacs_bitpanda&category=Integration)

Or add it manually:

1. Open **HACS** in Home Assistant
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**
3. Add `https://github.com/Spegeli/hacs_bitpanda` with category **Integration**
4. Search for **Bitpanda** and install it
5. Restart Home Assistant

### Manual

1. Download the latest release from the [releases page](https://github.com/Spegeli/hacs_bitpanda/releases)
2. Copy the `bitpanda` folder into your `config/custom_components/` directory
3. Restart Home Assistant

---

## ⚙️ Configuration

### 1. Create a Bitpanda API Key

1. Go to your [Bitpanda API settings](https://web.bitpanda.com/apikey) and create a new API key
2. Under **Scope**, select at least **"Balance"**
   - ℹ️ The "Balance" scope is read-only and safe — it cannot be used to place trades or initiate transactions
   - Optional: "Trading" and "Transactions" can also be enabled (both are read-only as well) but are not required for this integration
3. Copy your API key — **you will only see it once!**

### 2. Add the Integration to Home Assistant

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Bitpanda**
3. Enter your **API key** and select your **currency**
   > ⚠️ The currency can only be selected during initial setup. To change it, remove and re-add the integration.

### 3. Configure Assets and Wallets

1. Go to **Settings → Devices & Services → Bitpanda → Configure**
   - **📈 Price Tracker** — add or remove assets to track their live prices
   - **🪙 Crypto Wallets** — add or remove crypto wallets to monitor
   - **💶 Fiat Wallets** — add or remove fiat wallets to monitor
   - **🪨 Metal Wallets** — add or remove metal wallets to monitor
   - **📊 Index Wallets** — add or remove index wallets to monitor
2. When finished, click **💾 Save** to apply all changes

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| Integration doesn't load | Restart Home Assistant and clear the HACS cache |
| Sensor shows `unavailable` | Check your API key and review the HA logs |
| 24h price change missing | The Recorder integration must be active and have at least 24 hours of history |
| Wallet not visible | Add it via the integration's options menu |
| Portfolio sensor missing | Add at least one wallet first — the portfolio sensor only appears when wallets are tracked |

---

## ❓ FAQ

**Why are stocks, ETFs, and commodities not supported?**  
The Bitpanda public API only exposes cryptocurrency prices. Stock, ETF, and commodity prices are not available via the public API.

**Can I track multiple currencies at the same time?**  
Not within a single integration instance. Add a second integration entry for each additional currency you want to track.

**How do I change the display currency?**  
Remove the integration and re-add it — you can choose the currency during setup.

**Is my API key safe?**  
Yes. The integration only requires a read-only API key with the "Balance" scope. Your key is stored locally in Home Assistant and is never transmitted to third parties.

---

## ⚖️ Disclaimer

This integration is **not officially developed or supported by Bitpanda**. It is an independent community project using the public [Bitpanda API](https://developers.bitpanda.com/platform). Use it at your own risk.

For integration-related issues, please use the [GitHub issue tracker](https://github.com/Spegeli/hacs_bitpanda/issues).

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
