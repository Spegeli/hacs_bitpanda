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
- Live prices for any of the 14,051 supported assets — crypto, stocks, ETFs, ETCs, Bitpanda Crypto Indices and tokenized precious metals
- Supports 12 display currencies: CHF, CZK, DKK, EUR, GBP, HUF, NOK, PLN, RON, SEK, TRY, USD
- If you hold the asset, its price is derived from your portfolio value and updates every 5 minutes, together with your wallet balances
- If you don't hold the asset, its price is fetched every 60 seconds; above 30 such tracked assets the interval stretches automatically, to stay inside Bitpanda's 3,000-requests-per-hour limit
- Every price carries exactly 8 decimals from the API; the sensor's displayed precision is derived from the price's magnitude, not from the raw string
- 24h price change (`change_24h_pct`) available as entity attribute, powered by the Home Assistant recorder

### Wallet Monitor
- Displays the current value of your Bitpanda holdings — crypto, stocks, ETFs, ETCs, crypto indices and precious metals — in your selected currency
- Wallet values come from the portfolio every 5 minutes — no longer tied to price updates
- Raw coin/token balance (`balance`, `available`, `staked`) always available as entity attributes
- Earn data for staked assets: staked amount, APR (`earn_apr_percent`) and accumulated rewards (`rewards_net` and related attributes)
- Performance attributes: invested amount, average buy price, total return (amount and percent)
- Fiat is no longer a wallet — see Portfolio Total below

### Portfolio Total
- A single sensor showing the combined value of all tracked holdings, including uninvested cash
- Per-asset value breakdown (`breakdown`) as an entity attribute
- Uninvested fiat balance as the `cash` attribute
- Portfolio return over five timeframes — day, week, month, six months, year — as `return_<timeframe>_percent` attributes

### Manual Refresh
- Call the `bitpanda.refresh` service to trigger an immediate update of all price and wallet data outside of the regular update intervals

### Supported Assets
| Type | Description | Examples | Assets | Price Tracker | Wallet Monitor |
|------|-------------|----------|:------:|:---:|:---:|
| 🪙 **Crypto** | Cryptocurrencies available on Bitpanda | BTC, ETH, ADA, SOL, XRP, etc. | 876 | ✅ | ✅ |
| 📈 **Stocks** | Stocks & shares | AAPL, MSFT, TSLA, etc. | 10,182 | ✅ | ✅ |
| 🏦 **ETFs** | Exchange Traded Funds | S&P 500, NASDAQ 100, DAX, etc. | 2,804 | ✅ | ✅ |
| 🛢️ **ETCs (commodities)** | Exchange-traded commodities | WisdomTree Aluminium, iShares Physical Gold ETC, etc. | 176 | ✅ | ✅ |
| 📊 **Crypto indices** | Bitpanda Crypto Indices | BCI5, BCI10, BCI25, BCISL, etc. | 9 | ✅ | ✅ |
| 🥇 **Precious metals** | Tokenized precious metals | XAU (Gold), XAG (Silver), XPT (Platinum), XPD (Palladium) | 4 | ✅ | ✅ |
| 💶 **Fiat** | Fiat currencies | EUR, USD, CHF, GBP, etc. | — | ❌ | ❌ |

Together, these six categories cover 14,051 of Bitpanda's tradable assets. Only the three Cash Plus products are excluded — a separate interest-bearing cash product, not a priced asset.

Fiat is no longer a wallet: your balance is available as the `cash` attribute of the **Portfolio Total** sensor.

---

## 📋 Requirements

- Home Assistant **2025.1** or newer
- A [Bitpanda](https://www.bitpanda.com) account
- A Bitpanda API key ([create one here](https://app.bitpanda.com/my-account/apikey))

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

1. Go to your [Bitpanda API settings](https://app.bitpanda.com/my-account/apikey) and create a new API key
2. Under **Scope**, select all three required permissions:
   - **Guthaben (Balance)**
   - **Transaktion (Transaction)**
   - **Earn (Read)**
   - ℹ️ All three are read-only. The integration never calls a write endpoint and cannot place trades or move funds. **Trading** is not needed — it unlocks nothing the integration uses.
   - ⚠️ Scopes cannot be added to an existing key afterwards. If your key predates Earn, create a new one.
3. Copy your API key — **you will only see it once!**

Bitpanda API keys expire after **one year** — see [Replacing the API Key](#replacing-the-api-key) below for what happens then.

### 2. Add the Integration to Home Assistant

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Bitpanda**
3. Enter your **API key** and select your **currency**
   > ⚠️ The currency can only be selected during initial setup, and only one Bitpanda entry is allowed per Home Assistant instance. To change the currency, remove and re-add the integration.
4. Setup checks all three scopes and tells you which one is missing, if any

### 3. Configure Assets and Wallets

1. Go to **Settings → Devices & Services → Bitpanda → Configure**
2. Choose from the options menu:
   - **📈 Add price tracker** — pick a category (Crypto, Stocks, ETFs, ETCs, Crypto indices, Precious metals), then search that category's assets by name, symbol or ISIN
   - **🪙 Add wallet** — search the assets you currently hold
   - **🗑️ Remove tracked items** — remove price trackers or wallets
   - **💾 Save** — apply all changes
3. Search results are shown as `Name / SYMBOL / ISIN` (ISIN only for stocks, ETFs and ETCs) and match on any of the three
4. The first time you open the Stocks list it takes about ten seconds to load; it is then cached for 24 hours

### Replacing the API Key

Bitpanda API keys expire after one year. When Bitpanda rejects the stored key, Home Assistant shows **Reauthentication required** for the Bitpanda integration — open it and paste a new key. Every tracked asset and sensor is kept.

You don't have to wait for expiry: open the entry's **⋮ menu → Reconfigure** at any time to replace the key. The display currency cannot be changed this way — see step 2 above.

---

## ⬆️ Upgrading from 2026.06.x

This release moves to Bitpanda's new Public API and adds Earn data. If you're upgrading from a 2026.06.x release:

1. Create a new API key with **Guthaben (Balance)**, **Transaktion (Transaction)** and **Earn (Read)** — keys created from the old key page never had Earn
2. Update the integration through HACS and restart Home Assistant
3. **Reload the browser tab** (`Ctrl+F5` / `Cmd+Shift+R`) — skipping this can leave the integration's dialogs showing raw translation keys like `missing_scopes` from your browser's cached texts
4. Home Assistant shows **Reauthentication required** for the Bitpanda integration — open it and paste the new key
5. What is kept: tracked assets, entity IDs, history, dashboards and automations. What changes: fiat wallet sensors (such as "EUR Wallet") are no longer created — the leftover entity shows as `unavailable` and can be deleted; the balance is now the Portfolio Total sensor's `cash` attribute; and price sensors for assets you hold now update every 5 minutes instead of every 60 seconds, since they are derived from the portfolio rather than a separate ticker call — assets you don't hold are unaffected

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| Integration doesn't load | Restart Home Assistant and clear the HACS cache |
| Sensor shows `unavailable` | Check your API key and review the HA logs |
| 24h price change missing | The Recorder integration must be active and have at least 24 hours of history |
| Wallet not visible | Add it via the integration's options menu (**Add wallet**) |
| Portfolio sensor missing | Add at least one wallet first — the portfolio sensor only appears when wallets are tracked |
| "Reauthentication required" | The key expired, was revoked, or lacks a scope — open the notification and paste a new key |
| Setup says permissions are missing | Create a new key with all three scopes — scopes cannot be added to an existing key |
| Dialogs show raw text like `missing_scopes` | Reload the browser tab (`Ctrl+F5` / `Cmd+Shift+R`) — your browser cached the old translation strings |
| Stocks list takes a while to open | Expected on first use — about ten seconds. It is then cached for 24 hours |

---

## ❓ FAQ

**Which assets are supported?**  
Crypto, stocks, ETFs, ETCs (exchange-traded commodities), Bitpanda Crypto Indices and tokenized precious metals — 14,051 assets in total, for both price tracking and wallets. See [Supported Assets](#supported-assets) above.

**Can I track multiple currencies at the same time?**  
No. Home Assistant allows only one Bitpanda entry per instance, and its display currency is fixed at setup. To use a different currency, remove the integration and add it again.

**How do I change the display currency?**  
Remove the integration and re-add it — you can choose the currency during setup.

**Is my API key safe?**  
Yes. The integration only requires three read scopes — Guthaben (Balance), Transaktion (Transaction) and Earn (Read) — and never calls a write endpoint; it cannot place trades or move funds. The key is never logged, and diagnostics keep it redacted. It is stored locally in Home Assistant and never transmitted to third parties.

**Why are prices converted rather than quoted in my currency?**  
Bitpanda's price endpoint only returns EUR. For any other display currency, the integration derives a conversion rate from your own portfolio, accurate against ECB reference rates to within about half a percent. With an empty portfolio there is nothing to derive a rate from, so prices stay in EUR — the price sensor's `conversion` attribute says so when that happens.

**What happens when my API key expires?**  
Bitpanda API keys expire after one year. When Bitpanda rejects the stored key, Home Assistant shows **Reauthentication required** for the Bitpanda integration — open it and paste a new key. Every tracked asset and sensor is kept. You can also replace the key any time via the entry's **⋮ menu → Reconfigure**.

---

## ⚖️ Disclaimer

This integration is **not officially developed or supported by Bitpanda**. It is an independent community project using the public [Bitpanda API](https://developers.bitpanda.com/platform). Use it at your own risk.

For integration-related issues, please use the [GitHub issue tracker](https://github.com/Spegeli/hacs_bitpanda/issues).

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
