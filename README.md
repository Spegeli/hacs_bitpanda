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

### Wallet Monitor
- Displays the current value of your Bitpanda wallets in your selected currency
- Supports crypto wallets, metal wallets, commodity wallets, index wallets and fiat wallets
- Wallet values update automatically whenever the price changes
- Raw coin/token balance always available as entity attribute

### Supported Assets
| Type | Price Tracker | Wallet Monitor |
|---|---|---|
| Cryptocurrencies (BTC, ETH, …) | ✅ | ✅ |
| Metals (XAU, XAG, XPT, XPD) | ✅ | ✅ |
| Indices (BCI5, BCI10, …) | ✅ | ✅ |
| Fiat (EUR, USD, …) | ❌ | ✅ |
| Stocks / ETFs | ❌ | ❌ |

> **My stocks, ETFs or commodities are not showing up?**
> This is expected. Stocks, ETFs and commodities are not supported as they are not included in the public Bitpanda Price Ticker API.

---

## 📋 Requirements

- Home Assistant **2025.1.0** or newer
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

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Bitpanda**
3. Enter your **API key** and select your **currency**
   > ⚠️ The currency can only be selected during initial setup. To change it, remove and re-add the integration.
4. Optionally select **wallets** and **assets** to track right away — you can always adjust this later

### Updating your configuration

Go to **Settings → Devices & Services → Bitpanda → Configure** to add or remove tracked assets and wallets at any time. After making your changes, click **Save** to apply them.

---

## ⚖️ Disclaimer

This integration is **not officially developed or supported by Bitpanda**. It is an independent community project using the public [Bitpanda API](https://developers.bitpanda.com/platform). Use it at your own risk.

For integration-related issues, please use the [GitHub issue tracker](https://github.com/Spegeli/hacs_bitpanda/issues).

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
