<p align="center">
  <img src="https://raw.githubusercontent.com/Spegeli/hacs_bitpanda/main/logo.png" alt="Bitpanda Logo" width="300">
</p>

# 🚀 Bitpanda – Home Assistant Integration

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg"></a>
  <a href="https://github.com/Spegeli/hacs_bitpanda/releases"><img src="https://img.shields.io/github/v/release/Spegeli/hacs_bitpanda.svg?label=release&color=blue"></a>
  <img src="https://img.shields.io/badge/License-MIT-green.svg">
</p>

A custom <a href="https://www.home-assistant.io/">Home Assistant</a> integration for **Bitpanda**: your whole portfolio, and live prices of any asset, on your dashboard.

---

## ✨ Features

The integration offers two services. Set up either or both — each one once.

### Bitpanda Portfolio
- Tracks every holding in your account automatically — there is no list to maintain. A holding you buy appears at the next refresh; one you sell is removed after three refreshes without it (about 15 minutes)
- Every value in your Portfolio currency, as Bitpanda reports it
- A **Portfolio** device: **Total value** (every holding, Cash Plus included, plus all fiat), **Cash** (all fiat balances, including funds reserved by a pending order), **Cash Plus**, and your **return** over a day, a week, a month, six months and a year
- **Cash Plus** is the value of all your Cash Plus holdings in the Portfolio currency. Its attributes show each held product's own amount in its own currency — for example `eur: 100.00` while the Portfolio itself is shown in USD
- One device per held asset, such as **Vision (VSN) Wallet**:
  - **Wallet** — the value of the units you can trade (not staked)
  - **Staking** — the value of the staked units, with APR and lifetime rewards
  - **Total** — the whole position, with invested amount, average buy price and total return
  - Staking and Total appear as soon as something is staked or Bitpanda offers an Earn product for the asset, and stay while either is true
- The wallets appear in groups by asset type, such as Cryptocurrencies or Precious metals, named in the language Home Assistant runs in. The Portfolio device stays outside the groups (newer Home Assistant versions list it above them). Groups come and go with your holdings — there is nothing to add. Deleting a group (**⋮ → Delete**) only hides it until the next refresh while you still hold those assets: the group and its wallets come back, under the entity IDs the integration gives them; IDs you renamed yourself, and other customisations, survive only on newer Home Assistant versions
- The wallet of an asset you no longer hold can be deleted from its device page (**⋮ → Delete**) instead of waiting for it to go. The Portfolio device and the wallets of assets you hold cannot be deleted: they would come straight back, and the dialog explains why
- Updates every 5 minutes; Earn products every 24 hours; rewards every hour

### Bitpanda Price Tracker
- Live prices for any of 14,051 assets — crypto, stocks, ETFs, ETCs, Bitpanda Crypto Indices and tokenized precious metals — **without an API key**
- One device per tracked asset, such as **Bitcoin (BTC)**, in groups by asset type, with a price sensor in EUR (**Bitcoin (BTC) EUR**) and, optionally, one in each of the other 11 supported currencies
- EUR prices come from Bitpanda every 60 seconds. Above 30 tracked assets the interval stretches automatically, so the integration never sends more than 1,800 price requests per hour
- Other currencies are converted with the daily reference rates of the European Central Bank (ECB), fetched every 6 hours
- 24h price change (`change_24h_pct`) as an attribute, from the Home Assistant recorder

### Manual Refresh
- The `bitpanda.refresh` service updates the portfolio and the prices immediately
- A call within the cooldown of the last accepted one is ignored. With a Price Tracker set up, the cooldown is its price interval (60 seconds, longer with many tracked assets), so an automation cannot push price requests beyond the normal polling rate; with only the Portfolio, it is 10 seconds

### Supported Assets
| Type | Examples | Assets | Price Tracker | Portfolio |
|------|----------|:------:|:---:|:---:|
| 🪙 **Crypto** | BTC, ETH, ADA, SOL, XRP | 876 | ✅ | ✅ wallet |
| 📈 **Stocks** | AAPL, MSFT, TSLA | 10,182 | ✅ | ✅ wallet |
| 🏦 **ETFs** | S&P 500, NASDAQ 100, DAX | 2,804 | ✅ | ✅ wallet |
| 🛢️ **ETCs (commodities)** | WisdomTree Aluminium, iShares Physical Gold ETC | 176 | ✅ | ✅ wallet |
| 📊 **Crypto indices** | BCI5, BCI10, BCI25 | 9 | ✅ | ✅ wallet |
| 🥇 **Precious metals** | Gold (XAU), Silver (XAG), Platinum (XPT), Palladium (XPD) | 4 | ✅ | ✅ wallet |
| 💶 **Fiat** | EUR, USD, CHF | — | ❌ | ✅ Cash sensor |
| 💰 **Cash Plus** | BCPEUR, BCPUSD, BCPGBP | 3 | ❌ | ✅ Cash Plus sensor |

Cash Plus products are cash equivalents — one unit is one unit of their currency — so the Price Tracker leaves them out.

---

## 📋 Requirements

- Home Assistant **2025.5** or newer
- A [Bitpanda](https://www.bitpanda.com) account
- For the Portfolio: a Bitpanda API key ([create one here](https://app.bitpanda.com/my-account/apikey)). The Price Tracker needs none.

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

### 1. Create a Bitpanda API key (Portfolio only)

1. Go to your [Bitpanda API settings](https://app.bitpanda.com/my-account/apikey) and create a new API key
2. Under **Scope**, select all three required permissions:
   - **Guthaben (Balance)**
   - **Transaktion (Transaction)**
   - **Earn (Read)**
   - ℹ️ All three are read-only. The integration never calls a write endpoint and cannot place trades or move funds. **Trading** is not needed — it unlocks nothing the integration uses.
   - ⚠️ Scopes cannot be added to an existing key afterwards.
3. Copy your API key — **you will only see it once!**

Bitpanda API keys expire after **one year** — see [Changing the key or the currency](#changing-the-key-or-the-currency).

### 2. Add a service

1. Go to **Settings → Devices & Services → Add Integration** and search for **Bitpanda**
2. Choose **Bitpanda Portfolio** or **Bitpanda Price Tracker** — the list only offers what is not set up yet
3. **Portfolio:** enter your API key — setup checks all three scopes and names any that is missing — then choose your currency
4. **Price Tracker:** choose additional currencies if you want them. Every asset always gets its EUR sensor.

### 3. Track prices

The Price Tracker shows its assets in groups by type — Cryptocurrencies, Stocks, ETFs, ETCs, Crypto indices, Precious metals — with one device per asset inside. A group is named in the language Home Assistant runs in when it is created, and the name never changes by itself; newer Home Assistant versions let you rename a group with **⋮ → Rename**.

1. On the **Bitpanda Price Tracker** entry, click **Add price tracker** (older versions: **⋮ → Add price tracker**)
2. Pick a category (Crypto, Stocks, ETFs, ETCs, Crypto indices, Precious metals), then type to search by name, symbol or ISIN and pick one asset. Entries read `Name / SYMBOL / ISIN` (ISIN only for stocks, ETFs and ETCs)
3. The asset joins the group of its type; the first asset of a type creates that group
4. The first time you open the Stocks list it takes about ten seconds; it is then cached for 24 hours
5. To stop tracking one asset, open its device and use **⋮ → Delete**. **⋮ → Delete** on a group stops tracking all of its assets. Tracking an asset again later brings its sensors back under the entity IDs the integration gives them, with their history; IDs you renamed yourself, and other customisations, survive only on newer Home Assistant versions
6. To change the extra currencies, use **Configure**: removing a currency deletes its sensors; adding it back brings them back under the entity IDs the integration gives them, with their history; IDs you renamed yourself, and other customisations, survive only on newer Home Assistant versions

### Changing the key or the currency

- When Bitpanda rejects the stored key — it expired, was revoked, or lacks a scope — Home Assistant asks for a new one (**New Bitpanda API key needed**). Paste it there; every sensor is kept.
- **⋮ → Reconfigure** on the Portfolio entry replaces the key at any time (leave the key field empty to keep the current one) and changes the currency.
- ⚠️ **Changing the currency deletes all Portfolio sensors including their history** and recreates them in the new currency, under the entity IDs the integration gives them; IDs you renamed are restored only on newer Home Assistant versions. You are asked to confirm first.

### Entity IDs

Entity IDs are English and fixed, whatever language Home Assistant runs in. Assets are labelled `Name (SYMBOL)`, or just the symbol when the name only repeats it (BNB, BCI5).

| Sensor | Entity ID |
|---|---|
| Portfolio Total value / Cash / Cash Plus | `sensor.bitpanda_portfolio_total`, `sensor.bitpanda_portfolio_cash`, `sensor.bitpanda_portfolio_cash_plus` |
| Portfolio returns | `sensor.bitpanda_portfolio_return_day`, `_week`, `_month`, `_6_months`, `_year` |
| Vision (VSN) Wallet / Staking / Total | `sensor.bitpanda_vision_vsn_wallet`, `sensor.bitpanda_vision_vsn_wallet_staking`, `sensor.bitpanda_vision_vsn_wallet_total` |
| Bitcoin (BTC) in EUR / USD | `sensor.bitpanda_bitcoin_btc_eur`, `sensor.bitpanda_bitcoin_btc_usd` |

When two assets share a label, Home Assistant appends `_2` to the second one's ID.

### Attributes

Home Assistant lists these in the entity's Details view under translated names grouped by prefix (e.g. "Asset: Menge", "Bilanz: investiert"); the keys in the table below are what templates use.

| Sensor | Attributes |
|---|---|
| Wallet | `asset`, `asset_name`, `units` (tradable units). Without a Total sensor also `average_buy_price`, `invested_amount`, `total_return`, `total_return_percent` |
| Staking | `asset`, `asset_name`, `units` (staked), `apr_percent`, `rewards_gross`, `rewards_fee`, `rewards_net`, `rewards_count`, `rewards_last_at` |
| Total | `asset`, `asset_name`, `units` (whole position), `average_buy_price`, `invested_amount`, `total_return`, `total_return_percent` |
| Portfolio Cash Plus | `eur`, `usd`, `gbp` — the amount of each held Cash Plus product in its own currency |
| Price (EUR) | `asset`, `asset_name`, `trading_pair`, `change_24h_pct`, `price_24h_ago` |
| Price (other currencies) | as EUR, plus `conversion_rate`, `rate_date`, `rate_source` (`ECB`) |

---

## ⬆️ Upgrading from 2026.06.x

This release moves to Bitpanda's new Public API and splits the integration into two services. It needs Home Assistant **2025.5** or newer — on an older version the entry is left unmigrated and the integration does not load.

⚠️ **The upgrade is one-way.** The previous release cannot load the migrated entries, so going back to it afterwards does not work. Make a backup before you update if you may want to return.

1. Create a new API key with **Guthaben (Balance)**, **Transaktion (Transaction)** and **Earn (Read)** at [app.bitpanda.com/my-account/apikey](https://app.bitpanda.com/my-account/apikey) — keys from the old key page never had Earn
2. Update the integration through HACS and restart Home Assistant
3. **Reload the browser tab** (`Ctrl+F5` / `Cmd+Shift+R`) — otherwise the integration's dialogs can show raw text from your browser's cached translations
4. Home Assistant shows **New Bitpanda API key needed** — paste the new key (or use **⋮ → Reconfigure** on the Bitpanda Portfolio entry)
5. A notification lists **every renamed entity ID (old → new)** and anything that could not be migrated; the same list goes to the Home Assistant log. **Check your dashboards, automations and scripts** for the old IDs.

**What is kept:** the history of every migrated sensor (it moves with the rename), your price trackers (now in the Bitpanda Price Tracker, in EUR and in your old currency) and the wallets of assets you still hold. Entity IDs you renamed yourself are left as they are.

**What changes:**

- **Two services.** Your entry becomes **Bitpanda Portfolio**; your price trackers move to a new **Bitpanda Price Tracker** entry.
- **Entity IDs follow the new scheme**, for example `sensor.bitpanda_wallets_vsn_wallet` → `sensor.bitpanda_vision_vsn_wallet` and `sensor.bitpanda_price_tracker_btc_eur` → `sensor.bitpanda_bitcoin_btc_eur`.
- **Every holding is tracked**, not only the wallets you picked, and each gets its own device, in a group by asset type.
- **Wallets of assets you no longer hold go away.** They are migrated like the others, then removed together with their history after three portfolio refreshes without them — about ten minutes after the Portfolio starts working with your new key.
- **Wallet still means the unstaked part**, as before. The new **Staking** and **Total** sensors show the staked part and the whole position; they start without history.
- **Portfolio Total value now covers your whole account** — every holding plus all fiat. It used to add up only the wallets you tracked, so its value steps up at the upgrade: check automations that compare it against a threshold.
- **The fiat wallet in your currency becomes Portfolio Cash**, which sums all your fiat balances. Other fiat wallets are left as `unavailable` entities you can delete.
- **Prices in other currencies are converted with ECB daily rates** instead of being quoted by Bitpanda.
- **Attributes:** units are now `units` on each sensor (the Wallet's `units` are the unstaked units its old `balance` showed); the APR is `apr_percent` on the Staking sensor; the position performance is on the Total sensor. `breakdown`, `all_prices` and the wallet `price` attribute are gone.

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| Integration doesn't load | Restart Home Assistant and clear the HACS cache |
| "New Bitpanda API key needed" | The key expired, was revoked, or lacks a scope — paste a new key with all three scopes |
| Setup says permissions are missing | Create a new key with all three scopes — scopes cannot be added to an existing key |
| Dialogs show raw text | Reload the browser tab (`Ctrl+F5` / `Cmd+Shift+R`) — your browser cached old translations |
| A wallet sensor is `unavailable` | The asset is no longer in your portfolio; the wallet is removed after about 15 minutes, or at once with **⋮ → Delete** on its device page |
| Portfolio Total value, Cash or Cash Plus is `unavailable` | Bitpanda sent an entry the integration could not read; rather than show a figure that silently leaves it out, the sensor shows none until the entry reads correctly again. Enable debug logging to see which one. |
| No Staking sensor for an asset | It appears once something is staked or Bitpanda offers an Earn product for the asset |
| A price in another currency has no value and a `conversion` attribute | The ECB rates could not be loaded since Home Assistant started; the integration retries every 15 minutes and the value appears with the first success |
| One asset's price sensors are `unavailable` | Bitpanda returned no price for it; see the warning in the log |
| 24h price change missing | The Recorder integration must be active and have at least 24 hours of history |
| Stocks list takes a while to open | Expected on first use — about ten seconds. It is then cached for 24 hours |

---

## ❓ FAQ

**Which assets are supported?**  
Crypto, stocks, ETFs, ETCs, Bitpanda Crypto Indices and tokenized precious metals — 14,051 assets for price tracking, and every holding in your portfolio. See [Supported Assets](#supported-assets).

**Can I see prices in several currencies?**  
Yes. The Price Tracker always gives EUR and adds one sensor per extra currency you choose under **Configure**.

**How do I change the Portfolio currency?**  
**⋮ → Reconfigure** on the Bitpanda Portfolio entry. This deletes all Portfolio sensors including their history, because every recorded value was in the old currency; they come back under the entity IDs the integration gives them, and IDs you renamed are restored only on newer Home Assistant versions.

**Where do the non-EUR prices come from?**  
Bitpanda's price endpoint only answers in EUR. The Price Tracker converts with the ECB's daily reference rates, published once per working day around 16:00 CET; at weekends and on holidays the last rate stays in use. The `rate_date` attribute shows which day's rate a price uses.

**Is my API key safe?**  
Only the Portfolio uses a key, with three read scopes; the integration never calls a write endpoint and cannot place trades or move funds. The key is never logged, and diagnostics keep it redacted. It is stored locally in Home Assistant and sent only to Bitpanda. The Price Tracker and all asset lookups work without the key.

**What happens when my API key expires?**  
Bitpanda API keys expire after one year. Home Assistant then asks for a new key; every sensor is kept.

---

## ⚖️ Disclaimer

This integration is **not officially developed or supported by Bitpanda**. It is an independent community project using the public [Bitpanda API](https://docs.public.bitpanda.com). Use it at your own risk.

For integration-related issues, please use the [GitHub issue tracker](https://github.com/Spegeli/hacs_bitpanda/issues).

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
