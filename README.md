<p align="center">
  <img src="https://raw.githubusercontent.com/Spegeli/hacs_bitpanda/main/.github/readme/logo.png" alt="Bitpanda Logo" width="300">
</p>

<h1 align="center">Bitpanda – Home Assistant Integration</h1>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=Spegeli&repository=hacs_bitpanda&category=Integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and open a repository inside the Home Assistant Community Store."></a>
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg"></a>
  <a href="https://github.com/Spegeli/hacs_bitpanda/releases/latest"><img src="https://img.shields.io/github/v/release/Spegeli/hacs_bitpanda.svg?label=release&color=blue&display_name=release" alt="Latest release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-yellow" alt="License: MIT"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-2025.5%2B-41BDF5.svg" alt="Home Assistant 2025.5+"></a>
</p>

A custom <a href="https://www.home-assistant.io/">Home Assistant</a> integration for **Bitpanda**: your whole portfolio, and live prices of any asset, on your dashboard.

[Bitpanda](https://www.bitpanda.com) is a European investment platform for crypto, stocks, ETFs, ETCs and precious metals. The integration reads your account and Bitpanda's prices; it never trades.

> [!IMPORTANT]
> **Updating from a date version (2026.06.04 or older)?** Read [Upgrading from a date version](#%EF%B8%8F-upgrading-from-a-date-version) first — it needs a new API key and cannot be undone.

---

## ✨ Features

The integration offers two services. Set up either or both — each one once.

### Bitpanda Portfolio
- A **Portfolio** device: **Total value** (all holdings, Cash Plus included, and all fiat), **Cash** (all fiat, including money reserved by an open order), **Cash Plus**, your **return** in percent over a day, a week, a month, six months and a year, with what it means in money today, **Invested**, **Total return** and **Total return %** of your positions (everything but Cash and Cash Plus), and the value of each asset group, such as **Value: cryptocurrencies** — every amount in your Portfolio currency, as Bitpanda reports it
- A wallet device for every asset you hold, such as **Vision (VSN) Wallet**, with **Balance (available)** (the value of the units you can trade), **Balance (total)** (the whole position, with its price, invested amount, average buy price, total return, share of the portfolio and the change over 24 hours) and — while something is staked or Bitpanda offers Earn for the asset — **Balance (staking)** (with APR and rewards, also those of the last 30 days and of the last payout)
- Nothing to maintain: a wallet appears at the next update after you buy an asset and goes 10 to 15 minutes after you sell it, in groups by asset type such as Cryptocurrencies or Precious metals
- A notification under **Notifications** when a new wallet appears — you can switch it off — and the event `bitpanda_wallet_added` for your own automations
- A notification under **Notifications** when Bitpanda pays out a staking reward — switch it on if you want it — and the event `bitpanda_staking_reward_received` for your own automations
- The event `bitpanda_earn_changed` when Bitpanda changes the Earn offer of an asset you hold, and the three announcements as event entities on the Portfolio device, for the automation editor's triggers
- Actions that return the portfolio, its value history and the staking payouts in one call, for scripts and automations
- Updates every 5 minutes, each held asset's price from Bitpanda's price ticker right after them; Earn offers and rewards hourly

### Bitpanda Price Tracker
- Live prices for more than 11,000 assets — crypto, stocks, ETFs, ETCs, Bitpanda Crypto Indices and tokenized precious metals — **without an API key**
- One device per tracked asset, such as **Bitcoin (BTC) Price Tracker**, in groups by asset type, with a price sensor in EUR (**Bitcoin (BTC) Price Tracker EUR**) and, optionally, one in each of the other 11 supported currencies
- EUR prices come from Bitpanda every 60 seconds, one request per tracked asset. Should Bitpanda answer "too many requests", the integration slows down by itself and returns to every 60 seconds once Bitpanda answers again.
- Other currencies are converted with the daily reference rates of the European Central Bank (ECB), fetched every 6 hours
- 24-hour price change (`change_24h_pct`) as an attribute, from Home Assistant's statistics

### Dashboard cards
- Two cards for your dashboards, shipped with the integration — nothing else to install: **Bitpanda Portfolio** and **Bitpanda Price Tracker** (see [Dashboard cards](#-dashboard-cards))

### Supported Assets
| Type | Examples | Price Tracker | Portfolio |
|------|----------|:---:|:---:|
| 🪙 **Crypto** | BTC, ETH, ADA, SOL, XRP | ✅ | ✅ wallet |
| 📈 **Stocks** | AAPL, MSFT, TSLA | ✅ | ✅ wallet |
| 🏦 **ETFs** | S&P 500, NASDAQ 100, DAX | ✅ | ✅ wallet |
| 🛢️ **ETCs (commodities)** | WisdomTree Aluminium, iShares Physical Gold ETC | ✅ | ✅ wallet |
| 📊 **Crypto indices** | BCI5, BCI10, BCI25 | ✅ | ✅ wallet |
| 🥇 **Precious metals** | Gold (XAU), Silver (XAG), Platinum (XPT), Palladium (XPD) | ✅ | ✅ wallet |
| 💶 **Fiat** | EUR, USD, CHF | ❌ | ✅ Cash sensor |
| 💰 **Cash Plus** | BCPEUR, BCPUSD, BCPGBP | ❌ | ✅ Cash Plus sensor |

**Currencies:** EUR, CHF, CZK, DKK, GBP, HUF, NOK, PLN, RON, SEK, TRY and USD — for the Portfolio and for the Price Tracker's extra sensors.

### Languages
- English, German, French, Dutch, Italian, Spanish and Polish; any other language gets English
- Native speakers: corrections are welcome as an [issue](https://github.com/Spegeli/hacs_bitpanda/issues) or a pull request (see [CONTRIBUTING](CONTRIBUTING.md#translations))

The integration's texts follow three settings:

| Setting | Where | Applies to |
|---|---|---|
| Profile language (per user) | your profile → **Language** | dialogs, attribute names, group subtitles, **Repairs**, error messages — at once |
| System language (all users) | **Settings → System → General** | sensor names — after a restart |
| Language of group titles (per service) | when you add the service, later **Configure** (⚙) on its entry | group titles; for the Portfolio also the message why a device cannot be deleted, and its notifications — at once |

Entity IDs, device names and log messages are always English. A group you renamed keeps its name; a service upgraded from a date version starts in English. For everything in one language, set all three and restart Home Assistant.

---

## 📋 Requirements

- Home Assistant **2025.5** or newer
- For the installation through HACS: [HACS](https://hacs.xyz) installed in Home Assistant
- For the Portfolio: a Bitpanda account and an API key (see [Set up the Portfolio](#set-up-the-portfolio)). The Price Tracker needs neither.

---

## 📦 Installation

### Method 1: Installation via HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Spegeli&repository=hacs_bitpanda&category=Integration)

**One-Click Install:** Click the button above to add and open the repository directly inside Home Assistant!

**Manual HACS Steps:**
1. In Home Assistant, open **HACS**.
2. Click the three dots `⋮` in the top right corner and choose **Custom repositories**.
3. Paste the repository URL:
   ```text
   https://github.com/Spegeli/hacs_bitpanda
   ```
4. Select **Integration** as the **Type** and click **Add**.
5. Find **Bitpanda** in the list and click **Download**.
6. Restart Home Assistant.

### Method 2: Manual Installation

1. Download the `Source code (zip)` of the latest release from the [Releases](https://github.com/Spegeli/hacs_bitpanda/releases) page.
2. Unpack the ZIP archive.
3. Copy its `custom_components/bitpanda` folder into your Home Assistant directory under:
   ```text
   /config/custom_components/bitpanda/
   ```
4. Restart Home Assistant.

### Beta versions

A new version can come out as a beta first, for testing before everyone gets it. HACS offers two ways to get one:

- **Once, a version of your choice:** **HACS → Bitpanda → ⋮ → Redownload**, open **Need a different version?**, choose the version under **Release** — betas are marked as pre-releases — and select **Download**. Restart Home Assistant afterwards.
- **As updates:** under **Settings → Devices & services → HACS**, open **Bitpanda**. Its **Pre-release** switch is under **Diagnostic** and disabled at first: select it, open its settings (⚙), enable it, and turn it on once it appears. HACS then offers betas as updates too. Turned off again, it offers stable versions only; a beta you installed stays until the next stable version replaces it.

---

## ⚙️ Configuration

### Set up the Portfolio

1. Open [app.bitpanda.com/my-account/apikey](https://app.bitpanda.com/my-account/apikey) and create a new API key
   - ⚠️ Use this address. The key page of Bitpanda's classic website, web.bitpanda.com, has no **Earn (Read)** permission.
2. Under **Scope**, select all three required permissions:
   - **Balances**
   - **Transaction**
   - **Earn (Read)**
   - ℹ️ All three are read-only. The integration never calls a write endpoint and cannot place trades or move funds. **Trade (Read)** is not needed — it unlocks nothing the integration uses.
   - ⚠️ Permissions cannot be added to an existing key afterwards.
3. Copy your API key — **you will only see it once!** Home Assistant stores it locally and sends it only to Bitpanda; the integration never logs it, and diagnostics leave it out.
4. Go to **Settings → Devices & services → Add integration**, search for **Bitpanda**, select it, and choose **Bitpanda Portfolio** in the dialog that follows. If the Price Tracker is already set up, **Add service** on the Bitpanda integration page opens the same dialog. It lists only what is not set up yet.
5. Enter your API key — setup checks all three permissions and marks any that is missing — then choose your currency, the notifications about new wallets (on at first; see [New wallets](#new-wallets)) and about staking rewards (off at first; see [Staking rewards](#staking-rewards)), and the language of group titles and messages (see [Languages](#languages))
   - If an earlier Portfolio left long-term statistics in another currency, a last step asks whether to delete them — see [Troubleshooting](#-troubleshooting).

Bitpanda API keys expire on the date you choose when you create them, **one year** later at most. Home Assistant then asks for a new one — see [Changing settings later](#changing-settings-later).

### Set up the Price Tracker

1. Go to **Settings → Devices & services → Add integration**, search for **Bitpanda**, select it, and choose **Bitpanda Price Tracker** in the dialog that follows. If the Portfolio is already set up, **Add service** on the Bitpanda integration page opens the same dialog.
2. Choose additional currencies if you want them — every asset always gets its EUR sensor — and the language of group titles (see [Languages](#languages))

#### Track prices

The Price Tracker shows its assets in groups by type — Cryptocurrencies, Stocks, ETFs, ETCs, Crypto indices, Precious metals — with one device per asset inside. Precious metals are priced per gram, as in Bitpanda.

1. Select **Add price tracker** at the top of the Bitpanda integration page. With the Portfolio set up as well, a dialog first asks for the entry: pick **Bitpanda Price Tracker** (up to Home Assistant 2026.9, picking **Bitpanda Portfolio** there fails).
   - Before Home Assistant 2025.7 there is no such button: use **⋮ → Add price tracker** on the **Bitpanda Price Tracker** entry. That menu item works on every version and skips the dialog.
2. Choose the **Asset type**: Crypto, Stocks, ETFs, ETCs, Crypto indices or Precious metals.
3. Choose the asset. Type a name or a symbol to search the list — for stocks, ETFs and ETCs also an ISIN. Each entry reads `Name / SYMBOL`, for stocks, ETFs and ETCs `Name / SYMBOL / ISIN`.

The asset gets its own device in the group of its type; the first asset of a type creates the group. The integration keeps each list for an hour. Loading a large list, such as Stocks, can take up to half a minute the first time.

#### Stop tracking

- **One asset:** open its device and select **⋮ → Delete**.
- **A whole group:** select **⋮ → Delete** on the group, under the **Bitpanda Price Tracker** entry of the integration page.

Tracking an asset again later brings its sensors back under the entity IDs the integration gives them, with their history (your own changes: see [Resetting names and entity IDs](#resetting-names-and-entity-ids)).

### Changing settings later

**Configure** — the ⚙ on each service's entry (before Home Assistant 2025.7 a button labelled **Configure**):

- **Price Tracker:** the extra currencies and the language of group titles. Removing a currency deletes its sensors; adding it back brings them back under the entity IDs the integration gives them, with their history (your own changes: see [Resetting names and entity IDs](#resetting-names-and-entity-ids)).
- **Portfolio:** the notifications about new wallets (see [New wallets](#new-wallets)) and about staking rewards (see [Staking rewards](#staking-rewards)), and the language of group titles and messages (see [Languages](#languages)).

**⋮ → Reconfigure** on the Portfolio entry:

- **Replace the API key** at any time. Leave the API key field empty to keep the current one.
- **Change the currency.** ⚠️ This deletes all Portfolio sensors including their history and long-term statistics and recreates them in the new currency, under the entity IDs the integration gives them (your own changes: see [Resetting names and entity IDs](#resetting-names-and-entity-ids)). You are asked to confirm first; if you entered a new API key as well, you can save only the key and keep the currency.

**New Bitpanda API key needed:** when Bitpanda rejects the stored key — it expired, was revoked, or lacks a permission — Home Assistant asks for a new one. Paste it there; every sensor is kept.

---

## 📊 Using the sensors

The Portfolio keeps its wallets and groups up to date by itself:

- **A new asset** gets its wallet, in the group of its type, at the next update — every five minutes.
- **An asset you no longer hold** loses its wallet 10 to 15 minutes after you sell it; until then its sensors are `unavailable`. To remove the wallet sooner, delete it on its device page (**⋮ → Delete**).
- **What you cannot delete:** the Portfolio device and the wallet of an asset you hold — they would come straight back, and the dialog says why. A group you delete (**⋮ → Delete**) while you still hold its assets comes back at the next update.
- **Each group's value**, such as **Value: cryptocurrencies** on the Portfolio device, comes with its group and goes with it.

On the Price Tracker, deleting a device or a group stops tracking (see [Stop tracking](#stop-tracking)).

### New wallets

When the Portfolio adds a wallet for an asset that is new to it — one you bought, one you bought again after its wallet had gone, or one Bitpanda's catalogue lists only later — it announces the wallet as soon as its device is created:

- **A notification** under **Notifications**, linking to the wallet's device, in the Portfolio's language (see [Languages](#languages)). If its sensors are disabled, the notification says so and links to its device page. Switch it off under **Configure** (see [Changing settings later](#changing-settings-later)). Home Assistant does not keep notifications through a restart.
- **The event `bitpanda_wallet_added`**, whether or not the notification is on, for your own automations (see [the example](#5-new-wallet-a-push-message-to-your-phone)). Its data: `device_id` (the wallet's device), `asset_id` (Bitpanda's ID of the asset, the device's serial number), `symbol`, `name`, `wallet` (the wallet's name, such as `Vision (VSN) Wallet`), `category` (`crypto`, `stock`, `etf`, `etc`, `index`, `metal` or `other`), `units` and `value` (the wallet's units and value at the announcement, `null` when Bitpanda no longer lists the asset by then), `currency` and `message` — the notification's text without its formatting, in the Portfolio's language, whether the notification is on or not; `null` when the texts cannot be loaded. `message` is for people: its wording may change, so automations should not read figures from it.

Wallets that exist when you set up the Portfolio or upgrade from a date version are not announced, and neither are wallets that come back after a restart, a reload, a currency change, a deleted group, or an answer from Bitpanda that listed nothing at all.

### Staking rewards

When Bitpanda pays out a staking reward, the Portfolio announces it at the next hourly update of the rewards, for every asset whose **Balance (staking)** sensor is enabled:

- **A notification** under **Notifications**, if you switch it on under **Configure** (see [Changing settings later](#changing-settings-later)); it is off by default. One per asset, linking to the wallet's device, in the Portfolio's language (see [Languages](#languages)); the asset's next payout replaces it. Home Assistant does not keep notifications through a restart.
- **The event `bitpanda_staking_reward_received`**, whether or not the notification is on, for your own automations (see [the example](#4-staking-reward-a-push-message-for-each-payout)). Its data: `device_id` (the wallet's device), `asset_id`, `symbol`, `name`, `wallet` (such as `Vision (VSN) Wallet`), `count` (the number of payouts it covers, usually 1), `gross`, `fee` and `net` (their sum, in units of the asset), `value` (the net amount at today's price, in the Portfolio currency; `null` without a price), `currency`, `credited_at` (when Bitpanda paid the newest of them, in UTC), `apr_percent` (as Balance (staking) shows it; `null` without an Earn rate), `rewards_net` (the net of every payout so far, in units of the asset) and `message`, the notification's text as for a new wallet.

Payouts that could not be announced — while Home Assistant was off, the Portfolio was disabled or the asset's Balance (staking) sensor was disabled — come later, added up: one notification and one event per asset, with their number. Payouts made before you set up the Portfolio, or before you updated to a version with this feature, are not announced.

### Earn changes

When Bitpanda changes the Earn offer of an asset you hold, the Portfolio fires the event `bitpanda_earn_changed` — there is no notification. Its data: `device_id` (the wallet's device; `null` without one), `asset_id`, `symbol`, `name`, `wallet`, `change`, and `apr_before` and `apr_after` (in percent; `null` where there is none). `change` says what happened:

- `offered` — Bitpanda now offers Earn for the asset, sold out or not;
- `withdrawn` — it no longer does;
- `sold_out` and `available_again` — the offer is sold out, or open again;
- `apr` — the APR moved by 0.25 percentage points or more from the one last announced, or first seen.

The Portfolio compares every hourly read of Bitpanda's Earn catalogue with the one before, for every asset you hold, with or without a Balance (staking) sensor. The first read after a start or reload, a wallet new since, and an asset bought back are no news, so a change while Home Assistant was off is not announced. A read that fails, or that lists no offer at all, changes nothing.

### Event entities

The Portfolio device has three event entities that show the same announcements, so that the automation editor offers them as triggers: **New wallet** (`event.bitpanda_portfolio_new_wallet`), **Staking reward** (`event.bitpanda_portfolio_staking_reward`) and **Earn change** (`event.bitpanda_portfolio_earn_change`). Each fires together with its event above, with the event's data as its attributes; its event type is `wallet_added`, `staking_reward_received` or the Earn change's `change`. Several announcements at once each get a state of their own. A disabled event entity misses them; the events fire all the same.

Home Assistant restores an event entity's last event at a start, without firing it. During a reload of the Portfolio the entity is `unavailable` for a moment and then shows its last event again; after a currency change, or when you enable the entity, it comes back with its last event and no state before it. A state trigger on it should fire on none of these: not on the way to or from `unavailable`, and not without a state before. Leave `unknown` out of it — an entity that never fired is `unknown`, and its first event would be lost:

```yaml
triggers:
  - trigger: state
    entity_id: event.bitpanda_portfolio_new_wallet
    not_from: unavailable
    not_to: unavailable
conditions:
  - condition: template
    value_template: "{{ trigger.from_state is not none }}"
```

The events above are not repeated by a reload.

### Reading the Portfolio in one call

Three actions answer with data — try them under **Settings → Tools → Actions** (before Home Assistant 2026.8: **Developer tools → Actions**), or use `response_variable` in a script. They answer from what the Portfolio holds already and never ask Bitpanda:

- **`bitpanda.get_portfolio`** — `currency`, `total_value`, `cash`, `cash_plus`, `invested`, `total_return`, `total_return_percent`, the `returns` per timeframe (`day`, `week`, `month`, `six_month`, `year`) as `percent` and `amount`, and every wallet, largest first: `asset_id`, `symbol`, `name`, `category`, `device_id`, `units`, `staked_units`, `value`, `price`, `invested_amount`, `total_return`, `total_return_percent`, `change_24h_pct`, `return_24h`, `portfolio_share_percent`, `apr_percent`, `rewards_net` and `rewards_net_value`. A figure that is unknown, or that waits after Bitpanda stopped listing it, is `null`, as are a wallet's 24-hour figures while its Balance (total) is disabled.
- **`bitpanda.get_portfolio_history`** with a `timeframe` — the Portfolio's value over it as `points` (`time` in UTC, `value`), the line the Portfolio card draws; empty while the history is unavailable.
- **`bitpanda.get_staking_rewards`**, optionally with `start` and `end` (in Home Assistant's time zone; a payout at `start` counts, one at `end` does not) — every staking payout read so far, oldest first, each with `asset_id`, `symbol` (`null` for an asset you no longer hold), `credited_at`, `gross`, `fee` and `net`; and `updated_at`, when the rewards were last read. They are read every hour only while a Balance (staking) sensor is enabled. For a long history, give a `start`: the trace keeps the whole answer.

Without a loaded Portfolio the actions fail; while its figures are unavailable — before Bitpanda's first answer, during an outage or with a rejected key — `bitpanda.get_portfolio` and `bitpanda.get_portfolio_history` fail too.

### Entity IDs

The integration gives every sensor an English entity ID, the same in every language: `sensor.bitpanda_`, then the device's name in lower case with `_` for spaces and punctuation, then the sensor's own ending. Device names are English too — the asset's label followed by **Wallet** or **Price Tracker**. Assets are labelled `Name (SYMBOL)`, or just the symbol when the name only repeats it (BNB, BCI5). Stocks, ETFs and ETCs add their ISIN: `Name (SYMBOL / ISIN)`, or `SYMBOL (ISIN)` when the name only repeats the symbol.

You can change an entity ID in the sensor's settings: the sensor keeps working under the new ID, with its history, and the integration does not change it back (before Home Assistant 2025.7, a sensor the integration removes and creates again comes back under the integration's ID: after a currency change, after a deleted group, or when a wallet or its Balance (staking) sensor returns). To go back yourself, see [Resetting names and entity IDs](#resetting-names-and-entity-ids).

| Sensor | Entity ID |
|---|---|
| Portfolio Total value / Cash / Cash Plus | `sensor.bitpanda_portfolio_total`, `sensor.bitpanda_portfolio_cash`, `sensor.bitpanda_portfolio_cash_plus` |
| Portfolio returns | `sensor.bitpanda_portfolio_return_day`, `_week`, `_month`, `_6_months`, `_year` |
| Portfolio Invested / Total return / Total return % | `sensor.bitpanda_portfolio_invested`, `sensor.bitpanda_portfolio_total_return`, `sensor.bitpanda_portfolio_total_return_percent` |
| Portfolio value of each asset group | `sensor.bitpanda_portfolio_value_crypto`, `_stock`, `_etf`, `_etc`, `_index`, `_metal`, `_other` |
| Portfolio event entities | `event.bitpanda_portfolio_new_wallet`, `event.bitpanda_portfolio_staking_reward`, `event.bitpanda_portfolio_earn_change` |
| Vision (VSN) Wallet: Balance (available) / (staking) / (total) | `sensor.bitpanda_vision_vsn_wallet_available`, `sensor.bitpanda_vision_vsn_wallet_staking`, `sensor.bitpanda_vision_vsn_wallet_total` |
| Amundi PEA S&P 500 UCITS ETF (LYY1 / FR0011871136) Wallet: Balance (available) / (total) | `sensor.bitpanda_amundi_pea_s_p_500_ucits_etf_lyy1_fr0011871136_wallet_available`, `sensor.bitpanda_amundi_pea_s_p_500_ucits_etf_lyy1_fr0011871136_wallet_total` |
| Bitcoin (BTC) Price Tracker: EUR / USD | `sensor.bitpanda_bitcoin_btc_price_tracker_eur`, `sensor.bitpanda_bitcoin_btc_price_tracker_usd` |
| Amundi PEA S&P 500 UCITS ETF (LYY1 / FR0011871136) Price Tracker: CHF | `sensor.bitpanda_amundi_pea_s_p_500_ucits_etf_lyy1_fr0011871136_price_tracker_chf` |

When two assets share a label, Home Assistant appends `_2` to the second one's ID.

### Resetting names and entity IDs

To go back to the names and entity IDs the integration gives, reset them in Home Assistant as described below. Deleting the device does not help: the wallet of an asset you hold cannot be deleted, and from Home Assistant 2025.7 on, a device that comes back — even after its whole group was deleted — gets your changes back: its name, area and labels, and each of its sensors' names, icons, areas, labels and entity IDs.

1. **Device name:** on the device page, select the pencil, clear the name and save. The device shows its default name again.
2. **Sensor name and icon:** in the sensor's settings, clear **Name** or **Icon** and save.
3. **Entity ID:** first clear a name you gave the sensor (step 2) — a name of your own takes precedence over the integration's entity ID. Then, in the sensor's settings, select ↺ (**Restore entity ID**) next to the entity ID (Home Assistant 2026.7 and newer). From 2025.6 to 2026.6, use **⋮ → Recreate entity IDs** on the device page instead; it resets all of the device's sensors at once. On 2025.5, enter the entity ID by hand (see [Entity IDs](#entity-ids)).

### Attributes

Each sensor's attributes appear in its **Details** view (before Home Assistant 2026.3: **Attributes**), under translated names with a prefix per group, such as "Asset: quantity" or "Position: invested". Templates and automations use the keys in the table below.

| Sensor | Attributes |
|---|---|
| Balance (available) — every wallet | `asset`, `asset_name`, `asset_category`, `asset_isin`, `units` (tradable units) |
| Balance (total) — every wallet | `asset`, `asset_name`, `asset_category`, `asset_isin`, `units` (whole position), the asset's `price`, the position performance: `average_buy_price`, `invested_amount`, `total_return`, `total_return_percent`, `portfolio_share_percent` (the position's share of Total value), and over 24 hours `price_24h_ago`, `change_24h_pct` and `return_24h` |
| Balance (staking) — while something is staked or an Earn product is offered | `asset`, `asset_name`, `asset_category`, `asset_isin`, `units` (staked), `apr_percent`, `earn_type`, `earn_mode`, `earn_sold_out`, `rewards_gross`, `rewards_fee`, `rewards_net`, `rewards_net_value`, `rewards_count`, `rewards_last_at`, `rewards_net_30d`, `rewards_net_value_30d`, `rewards_last_net`, `rewards_last_value` |
| Portfolio returns | `return_amount` — what the return means in money on today's Total value |
| Portfolio Invested / Total return / Total return % | `wallets` — the number of positions they add up |
| Portfolio value of an asset group | `share_percent` (its share of Total value), `invested_amount`, `total_return`, `total_return_percent`, `wallets` (the number of wallets it adds up) |
| Portfolio Cash Plus | `eur`, `usd`, `gbp` — the amount of each held Cash Plus product in its own currency |
| Price (EUR) | `asset`, `asset_name`, `asset_category`, `asset_isin`, `change_24h_pct`, `price_24h_ago` |
| Price (other currencies) | as EUR, plus `conversion` (status `no_rate` until the first ECB rate is loaded), `conversion_rate`, `rate_date`, `rate_source` (`ECB`) |

`asset_isin`, the ISIN, is there for stocks, ETFs and ETCs only.

`asset_category` is the asset's category key: `crypto`, `stock`, `etf`, `etc`, `index`, `metal` or `other`.

`earn_type` (`flexible` or `locked`), `earn_mode` (`staking` or `stable_coin`) and `earn_sold_out` describe the asset's Earn offer while Bitpanda's catalogue lists it; `earn_type` or `earn_mode` is left out when Bitpanda sends a value the integration does not know.

An attribute without a value is left out rather than set to `null`: `apr_percent` without an Earn rate, the `rewards_…` attributes before the first payout, `rewards_net_value` without a price, `change_24h_pct` and `price_24h_ago` until Home Assistant's statistics hold a price from about 24 hours ago (within half an hour); a wallet's `price`, `change_24h_pct`, `price_24h_ago`, `return_24h`, `rewards_net_value`, `rewards_net_value_30d` and `rewards_last_value` without a ticker price of the last 15 minutes; its `price_24h_ago`, `change_24h_pct` and `return_24h` also until a ticker price from about 24 hours ago is recorded (within half an hour); `rewards_last_net` without a payout whose time Bitpanda sent; `return_amount` while Total value is unknown; `portfolio_share_percent` and a group's `share_percent` while Total value is unknown or not above 0; a group's `invested_amount`, `total_return` and `total_return_percent` while one of its wallets lacks an invested amount, and `total_return_percent` unless something was invested. A price in another currency carries either `conversion` (`no_rate`, before the first ECB rate) or `conversion_rate`, `rate_date` and `rate_source`. `rewards_last_at` is when Bitpanda credited the newest payout, in UTC.

The lifetime reward amounts `rewards_gross`, `rewards_fee` and `rewards_net` are in units of the asset, and `rewards_count` is the number of payouts; `rewards_net_value` is what the net rewards are worth at today's price, as the Bitpanda app shows it — not their value when they were paid out. `rewards_net_30d` is the net of the payouts of the last 30 days, in units of the asset (0 without one), and `rewards_last_net` that of the last payout — several payouts at the same moment count as one; `rewards_net_value_30d` and `rewards_last_value` are their worth at today's price.

### Long-term statistics

Every value sensor keeps long-term statistics: the Portfolio's figures and returns, the values of its asset groups, its wallets, and every price.

- **To show them** over weeks or months, use a **Statistics graph** card. Under **Show stat types**, choose *State* for a money value and *Mean*, *Min* or *Max* for a return or Total return %.
- **A currency change** deletes the Portfolio sensors' statistics along with their history — they were recorded in the old currency.
- **Setting up the Portfolio again** in another currency: setup finds the statistics an earlier Portfolio left and asks whether to delete them — see [Troubleshooting](#-troubleshooting).

### Refreshing by hand

The action `bitpanda.refresh` fetches the portfolio — Total value, Cash, Cash Plus, Invested, the total return, the asset groups' values, the wallets and the returns — and the prices right away, or with its **Service** field (`config_entry_id`) only one of them, and finishes when it is done; a wallet's `price` and its 24-hour figures follow right after, from Bitpanda's price ticker, at most once a minute. Earn offers, staking rewards and exchange rates keep their own schedule.

- **Cooldown:** each service has its own; a service refreshed within it is skipped, the other is refreshed. The Portfolio's is 10 seconds, the Price Tracker's the price interval — 60 seconds, longer while Bitpanda rate-limits the price requests (up to 16 minutes). So a call without the field refreshes the Portfolio every 10 seconds at most, and the prices once their interval has passed.
- **Failures:** when a refresh fails — Bitpanda cannot be reached or answers with an error — the action fails with an error naming the service; the other service is refreshed all the same. The returns are fetched only when the portfolio was; returns that could not be fetched keep their last value and fail nothing. The action also fails while neither service is loaded, and when its **Service** is no loaded Bitpanda service.
- **In automations:** a failed action stops a script or automation at that step, unless the step sets `continue_on_error: true` (see the [Morning report](#3-morning-report-portfolio-value-and-todays-return-at-a-set-time) example).
- **Your own update interval:** on the entry of each service you want to refresh yourself, open **⋮ → System options**, turn off **Enable polling for changes** and select **Update**. Then call `bitpanda.refresh` from an automation at the times you choose, with that service picked in its **Service** field. Each call brings the picked service's part up to date — the portfolio and its returns, or the prices — and each wallet's price follows a few seconds later. A wallet's price counts for 15 minutes: with your calls further apart, `bitpanda.get_portfolio` answers `null` for the price and the figures from it (the 24-hour figures, `rewards_net_value`) from then until your next call, and at that call the wallets show none of them for those few seconds. Everything else is read only when Home Assistant starts or the service is reloaded — and not again if that read failed: Earn offers, staking rewards and the exchange rates. Prices in other currencies keep the rate read then, staking rewards are announced only then, and `bitpanda_earn_changed` does not fire. A sold asset's wallet goes after three of your refreshes, at least ten minutes apart from first to last. Calls within the cooldown are ignored.

---

## 🃏 Dashboard cards

The integration brings two cards for your dashboards. They come with it — there is nothing else to install — and find their sensors by themselves: wallets and tracked assets that come and go appear and disappear without editing a card.

To add one, edit a dashboard, choose **Add card**, then **By card**, and search for **Bitpanda**; each card shows a preview. The new **Overview**, the default of new installations since Home Assistant 2026.2, takes no cards: first create a dashboard under **Settings → Dashboards → Add dashboard**. Every option is in the card's visual editor, and YAML works too.

> [!NOTE]
> Your browser loads the cards when it opens Home Assistant. After you set up the integration, and after each update, **reload the page twice**: the first reload can still come from your browser's cache. A new browser tab shows the cards at once. **In the Home Assistant app**, closing and reopening it is not enough: open the app's **Settings → Companion app → Troubleshooting** and select **Reset frontend cache**.

| Card | Type | Shows |
|---|---|---|
| **Bitpanda Portfolio** | `custom:bitpanda-portfolio-card` | Total value with your return over 1 day to 1 year, your return since purchase, and a line of the total value; Cash and Cash Plus; what you stake and in how many wallets — tap it for those wallets; how your money is split across asset types, Cash and Cash Plus; your wallets, by asset type or in one list — tap a group to open it, the arrow beside a wallet for its details: the current price, average buy price, invested amount, the return over 24 hours and in total, and — while something is staked or Bitpanda offers Earn for the asset — staked units, staking APR and, from the first payout, what staking earned in the last 30 days and in all, and the payouts. Each part can be left out, down to total value and return alone |
| **Bitpanda Price Tracker** | `custom:bitpanda-price-tracker-card` | Your tracked assets as a list or as tiles: price, change in percent and in the price's currency, and a line. With extra currencies set up in the Price Tracker, a switch shows the prices in them. The header, the switches, the lines and the change in the price's currency can each be left out |

<table>
  <tr>
    <td valign="top"><img src="https://raw.githubusercontent.com/Spegeli/hacs_bitpanda/main/.github/readme/cards/portfolio-card.png" alt="The Bitpanda Portfolio card: total value with the return over 1 day and the return since purchase, the line of the total value, Cash and Cash Plus, the staking line, the allocation, the search field and the wallets by asset type, one of them opened" width="300"></td>
    <td valign="top">
      <img src="https://raw.githubusercontent.com/Spegeli/hacs_bitpanda/main/.github/readme/cards/portfolio-card-search.png" alt="The Bitpanda Portfolio card's wallet search: the wallets matching “sol”, one of them opened" width="300"><br><br>
      <img src="https://raw.githubusercontent.com/Spegeli/hacs_bitpanda/main/.github/readme/cards/price-tracker-card-list.png" alt="The Bitpanda Price Tracker card as a list" width="300"><br><br>
      <img src="https://raw.githubusercontent.com/Spegeli/hacs_bitpanda/main/.github/readme/cards/price-tracker-card-tiles.png" alt="The Bitpanda Price Tracker card as tiles" width="300">
    </td>
  </tr>
</table>

### What the cards show

- **The line shows the total value, not your return.** A deposit raises it; the percentage beside it is Bitpanda's return, which leaves deposits and withdrawals out, and the amount after it is what that percentage means on today's total value. The line is Bitpanda's own history of your total value, complete from the first day. Its dashed line marks the middle between the highest and the lowest value shown. Point at the line, or move a finger along it, to see the value at that moment, with the highest, middle and lowest value at the right.
- **Since purchase** is the return on what you hold since you bought it — the Portfolio's Total return % and Total return; it does not change with the timeframe.
- **The staking line** under Cash adds up the Balance (staking) of all your wallets — not only the ones the card shows — and counts them; it is left out while nothing is staked. A wallet whose Balance (staking) sensor is disabled does not count.
- **A wallet's percentage** is its return since purchase, and a group's is that of all its wallets together; the timeframe switch changes neither. A wallet's total return as an amount is in its details, and so is its return over 24 hours once Home Assistant has the wallet's price of a day ago.
- **The change in the Price Tracker** comes from Home Assistant's statistics, for 1D as for 1W to 1Y. Beside or below the percentage is the same change in the price's currency. While an asset's statistics are shorter than the timeframe, its change and its line count from their start, and the row says since when ("Change since Oct 6"). A price line breaks where Home Assistant has no statistics: while it was off or the sensor unavailable.
- **Other currencies:** a price in another currency is Bitpanda's euro price converted at the ECB's daily reference rate, so its change includes the rate's move: on a day the euro gains 0.06 % against the dollar, a price that fell 1.12 % in euros fell 1.06 % in dollars.
- **"—"** means that a figure is missing right now: a sensor without a value, or a change the statistics cannot give yet. A sum or a share needs all its parts: one wallet without its value shows "—" for its group and the allocation. The cards never put a figure of their own in its place.
- **Stocks, ETFs and ETCs** count in shares, precious metals in grams. The wallet list shows up to 4 decimals, rounded down as in the Bitpanda app, and a holding below 0.0001 its first two digits, so it never reads 0; the staked units and rewards in a wallet's details show all decimals.
- **The eye** on the Portfolio card hides amounts and units behind a mask — for a screenshot, say — and keeps the percentages and a wallet's current price; pointing at the line then shows the time only. While it is closed, no tap opens a dialog that would show a hidden amount: neither a hidden figure nor the return beside the total value; the percentage since purchase still opens. It hides them on that card only; nothing else changes. Without the card's header, the eye stands beside the total value, or in a row of its own when that is left out too.
- **A tap** opens Home Assistant's dialog of that figure, with its history — of a hidden figure only while the eye is open. A tap on the staking line opens its wallets; a tap on one of them opens its Balance (staking).
- **The keyboard** works too: Tab reaches every part you can tap, Enter or Space taps it. On the line, ← and → move from point to point, Home and End go to its ends, Escape clears the point; a screen reader reads each point's value and time — the time only while the eye is closed.
- **Language:** your profile language — English, German, French, Dutch, Italian, Spanish or Polish; English for any other. Asset group names are the integration's own, in that language — not a title you gave a group, nor the language chosen for the Portfolio.

### Card options

Gains and losses take your theme's success and error colours, green and red in Home Assistant's default theme.

#### Bitpanda Portfolio card

| Option | Values | Default | What it does |
|---|---|---|---|
| `title` | text | `Bitpanda Portfolio` | the card's heading |
| `timeframe` | `day`, `week`, `month`, `six_month`, `year` | `day` | the timeframe the card opens with |
| `show_total` | `true`, `false` | `true` | the total value and its return; the timeframe buttons stay while the line is shown, unless `show_timeframes` is off |
| `show_since_purchase` | `true`, `false` | `true` | under the return: the return since purchase; only with `show_total` |
| `show_graph` | `true`, `false` | `true` | the line of the total value |
| `show_cash` | `true`, `false` | `true` | Cash and Cash Plus |
| `show_staking` | `true`, `false` | `true` | the staking line under Cash; left out while nothing is staked |
| `show_allocation` | `true`, `false` | `true` | the split by asset type, Cash and Cash Plus |
| `show_wallets` | `true`, `false` | `true` | the wallets |
| `show_search` | `true`, `false` | `false` | a search field above the wallets: finds them by name, symbol or ISIN, as one list without groups |
| `group_wallets` | `true`, `false` | `true` | wallets in their asset groups |
| `sort` | `value`, `return`, `name` | `value` | the order of the wallets |
| `limit` | 0 or more; 0 shows all | `5` | wallets before "Show all", when `group_wallets` is off |
| `group_selection` | `all`, `all_except`, `only` | `all` | which asset groups' wallets the card shows |
| `groups` | `crypto`, `stock`, `etf`, `etc`, `index`, `metal`, `other` | — | with `all_except` or `only`: the asset groups left out or shown |
| `asset_selection` | `all`, `all_except`, `only` | `all` | which wallets the card shows, within the asset groups shown |
| `assets` | asset IDs | — | with `all_except` or `only`: the wallets left out or shown |
| `show_header` | `true`, `false` | `true` | the header with the title and the eye; without it the eye stands beside the total value, or in a row of its own when that is left out too |
| `show_timeframes` | `true`, `false` | `true` | the timeframe buttons; without them the card keeps `timeframe` |
| `hide_amounts` | `true`, `false` | `false` | start with amounts hidden |

`assets` holds Bitpanda's asset IDs — a device's serial number; the visual editor fills it in. Device IDs from older configurations still work.

Hiding a section, an asset group or a wallet changes only what the card shows: the total value, Cash, Cash Plus and the allocation always cover your whole portfolio, while a group's count, return and sum cover the wallets it shows.

#### Bitpanda Price Tracker card

| Option | Values | Default | What it does |
|---|---|---|---|
| `title` | text | `Bitpanda Price Tracker` | the card's heading |
| `layout` | `list`, `tiles` | `list` | the prices as a list or as tiles |
| `timeframe` | `day`, `week`, `month`, `six_month`, `year` | `day` | the timeframe the card opens with |
| `currency` | `EUR` or a currency set up in the Price Tracker | `EUR` | the currency the card opens with; EUR while that currency is not set up |
| `sort` | `selection`, `name`, `change_desc`, `change_asc` | `name` | the order of the assets; `change_desc` and `change_asc` by the change of the timeframe shown, `selection` keeps the order of `assets` with `only` — in the visual editor you drag the chosen assets into it —, otherwise by name |
| `limit` | 0 or more; 0 shows all | `0` | assets before "Show all" |
| `group_selection` | `all`, `all_except`, `only` | `all` | which asset groups' prices the card shows |
| `groups` | `crypto`, `stock`, `etf`, `etc`, `index`, `metal`, `other` | — | with `all_except` or `only`: the asset groups left out or shown |
| `asset_selection` | `all`, `all_except`, `only` | `all` | which assets the card shows, within the asset groups shown |
| `assets` | asset IDs | — | with `all_except` or `only`: the price trackers left out or shown |
| `show_header` | `true`, `false` | `true` | the header with the title |
| `show_timeframes` | `true`, `false` | `true` | the timeframe buttons; without them the card keeps `timeframe` |
| `show_currencies` | `true`, `false` | `true` | the currency buttons; without them the card keeps `currency` |
| `show_lines` | `true`, `false` | `true` | a line in every row and tile; the changes come from the statistics either way |
| `show_amounts` | `true`, `false` | `true` | the change in the price's currency beside its percentage; without it the footer of another currency speaks of the percentages only |

`assets` holds Bitpanda's asset IDs — a device's serial number; the visual editor fills it in. Device IDs from older configurations still work.

```yaml
type: custom:bitpanda-price-tracker-card
layout: tiles
currency: USD
sort: change_desc
```

---

## 🤖 Automation examples

Paste one into a new automation's YAML editor (in the automation editor: **⋮ → Edit in YAML**) and adjust the entity IDs and the numbers. A price sensor's entity ID ends in its currency: for US dollars, use `sensor.bitpanda_bitcoin_btc_price_tracker_usd` once USD is one of the Price Tracker's extra currencies, and write the threshold in USD. Every example works from Home Assistant 2025.5 on.

### 1. Price alert: notify when Bitcoin rises above 100,000 EUR

A notification once Bitcoin rises above 100,000 EUR. It fires when the price crosses the threshold, not while it stays above, and at most once an hour, so a price that swings around the threshold does not flood you with messages. The first condition keeps it quiet when the price only comes back after an outage or a restart. Use `below:` for a fall; add `for: "00:05:00"` to the trigger to ignore a spike shorter than five minutes.

```yaml
alias: Bitcoin above 100,000 EUR
triggers:
  - trigger: numeric_state
    entity_id: sensor.bitpanda_bitcoin_btc_price_tracker_eur
    above: 100000
conditions:
  # Only a real crossing: not the price coming back after an outage or a restart.
  - condition: template
    value_template: "{{ trigger.from_state is not none and trigger.from_state.state | is_number }}"
  # At most one message an hour (60 minutes × 60 seconds) — for 10 minutes, write 10 * 60.
  - condition: template
    value_template: "{{ now().timestamp() - as_timestamp(this.attributes.last_triggered, 0) > 60 * 60 }}"
actions:
  - action: persistent_notification.create
    data:
      title: Bitcoin
      message: "Bitcoin is at {{ states('sensor.bitpanda_bitcoin_btc_price_tracker_eur', with_unit=True) }}."
```

For a push message to your phone, use its `notify.mobile_app_…` action instead.

---

### 2. Big move: notify when Bitcoin moves more than 10 % in 24 hours

A notification when Bitcoin has risen or fallen by more than 10 % within 24 hours (the sensor's `change_24h_pct` attribute), again at most once an hour.

```yaml
alias: Bitcoin moved more than 10 % in 24 hours
triggers:
  - trigger: numeric_state
    entity_id: sensor.bitpanda_bitcoin_btc_price_tracker_eur
    attribute: change_24h_pct
    above: 10
  - trigger: numeric_state
    entity_id: sensor.bitpanda_bitcoin_btc_price_tracker_eur
    attribute: change_24h_pct
    below: -10
conditions:
  # Only a real move: not the change appearing after a restart.
  - condition: template
    value_template: "{{ trigger.from_state is not none and trigger.from_state.attributes.change_24h_pct is number }}"
  # At most one message an hour.
  - condition: template
    value_template: "{{ now().timestamp() - as_timestamp(this.attributes.last_triggered, 0) > 60 * 60 }}"
actions:
  - action: persistent_notification.create
    data:
      title: Bitcoin
      message: "Bitcoin moved {{ state_attr('sensor.bitpanda_bitcoin_btc_price_tracker_eur', 'change_24h_pct') }} % in 24 hours."
```

---

### 3. Morning report: portfolio value and today's return at a set time

Ask Bitpanda for the portfolio and its returns at a set time instead of waiting for the next regular update, then show its total value and its return over the last 24 hours, with the amount that return means today when it is known. In the editor, pick your **Bitpanda Portfolio** in the refresh's **Service** field: it fills in `config_entry_id`, so that the prices are not asked for. With `continue_on_error: true`, a failed refresh (see [Refreshing by hand](#refreshing-by-hand)) does not stop the automation: the report still comes, with the last figures.

```yaml
alias: Bitpanda morning report
triggers:
  - trigger: time
    at: "07:00:00"
actions:
  - action: bitpanda.refresh
    continue_on_error: true
    data:
      # The Portfolio alone: the editor's "Service" field fills it in.
      config_entry_id: YOUR_PORTFOLIO_ENTRY_ID
  # Runs even when the refresh failed, then with the last figures.
  - action: persistent_notification.create
    data:
      title: Bitpanda
      message: "Portfolio: {{ states('sensor.bitpanda_portfolio_total', with_unit=True) }}, {{ states('sensor.bitpanda_portfolio_return_day', with_unit=True) }}{% set amount = state_attr('sensor.bitpanda_portfolio_return_day', 'return_amount') %}{% if amount is not none %} ({{ '%+.2f' | format(amount) }} {{ state_attr('sensor.bitpanda_portfolio_total', 'unit_of_measurement') }}){% endif %} in 24 hours"
```

The same steps work in a script, which you can start from anywhere — from a button, for example.

---

### 4. Staking reward: a push message for each payout

A push message when Bitpanda pays out a staking reward (see [Staking rewards](#staking-rewards)), with the event's ready text. Use your phone's `notify.mobile_app_…` action instead of `notify.mobile_app_your_phone`. `mode: queued` with `max: 50` sends one message per asset when several are paid out at once — Home Assistant's default queue would drop those after the tenth.

```yaml
alias: New Bitpanda staking reward
mode: queued
max: 50
triggers:
  - trigger: event
    event_type: bitpanda_staking_reward_received
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: Staking reward
      message: "{{ trigger.event.data.message }}"
```

---

### 5. New wallet: a push message to your phone

A push message when the Portfolio adds a wallet (see [New wallets](#new-wallets)), with the event's ready text. Use your phone's `notify.mobile_app_…` action instead of `notify.mobile_app_your_phone`. `mode: queued` with `max: 50` sends one message per wallet when several arrive at once — Home Assistant's default queue would drop those after the tenth.

```yaml
alias: New Bitpanda wallet
mode: queued
max: 50
triggers:
  - trigger: event
    event_type: bitpanda_wallet_added
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: New Bitpanda wallet
      message: "{{ trigger.event.data.message }}"
```

---

## ⬆️ Upgrading from a date version

This section is for everyone upgrading from a version before 2.0.0 — the date versions, 2026.06.04 and older. Version 2.0.0 moves to Bitpanda's new Public API and splits the integration into two services.

It needs Home Assistant **2025.5** or newer. On 2025.3 or 2025.4 the entry stays as it is, the integration does not load, and **Settings → Repairs** asks you to update Home Assistant; older versions cannot load the integration at all.

⚠️ **The upgrade is one-way.** The previous release cannot load the migrated entries, so going back to it afterwards does not work. Make a backup before you update if you may want to return.

1. Your old key has no Earn permission, so create a new one, as in steps 1–3 of [Set up the Portfolio](#set-up-the-portfolio):
   - Open [app.bitpanda.com/my-account/apikey](https://app.bitpanda.com/my-account/apikey) — the key page of the classic site, web.bitpanda.com, has no **Earn (Read)**.
   - Select **Balances**, **Transaction** and **Earn (Read)**; **Trade (Read)** is not needed.
   - Copy the key — Bitpanda shows it only once.
2. Update the integration through HACS and restart Home Assistant.
   - HACS offers no update? From 2.0.0 on, versions are numbers instead of dates, and HACS can rank a date such as 2026.06.04 above them. Install the newest version once by hand: **HACS → Bitpanda → ⋮ → Redownload**, open **Need a different version?**, pick the newest version not marked as a pre-release and download it. Later updates show up as usual.
   - No version choice in HACS? Open **Settings → Tools → Actions** (before Home Assistant 2026.8: **Developer tools → Actions**) and run `update.install` with the Bitpanda update entity and, as version, the newest release's tag (such as `v2.1.0`).
3. **Reload the browser tab** (`Ctrl+F5` / `Cmd+Shift+R`) — otherwise the integration's dialogs can show raw text from your browser's cached translations.
4. Home Assistant shows **New Bitpanda API key needed**: paste the new key there (or use **⋮ → Reconfigure** on the Bitpanda Portfolio entry).
5. Under **Settings → Repairs**, in your profile language, the upgrade lists:
   - **every renamed entity ID (old → new)**,
   - the entities that could not be migrated, which you can delete right there,
   - the Portfolio's switch to EUR if your old currency is not available,
   - the assets to add to a Bitpanda Price Tracker you had already set up — its prices are not moved into one that existed before the upgrade.

   The Home Assistant log keeps the same list in English, with the reason for each entity that was not migrated. **Check your dashboards, automations and scripts** for the old IDs.
6. Optional: once the Portfolio works with the new key, delete the old key on the classic site, web.bitpanda.com, if nothing else uses it.

**What is kept:** the history of every migrated sensor (it moves with the rename), your price trackers (now in the Bitpanda Price Tracker, in EUR and in your old currency) and the wallets of assets you still hold. Entity IDs you renamed yourself are left as they are.

**What changes:**

- **Two services.** Your entry becomes **Bitpanda Portfolio**; your price trackers move to a new **Bitpanda Price Tracker** entry.
- **Entity IDs follow the new scheme**, for example `sensor.bitpanda_wallets_vsn_wallet` → `sensor.bitpanda_vision_vsn_wallet_available` and `sensor.bitpanda_price_tracker_btc_eur` → `sensor.bitpanda_bitcoin_btc_price_tracker_eur`.
- **Every holding is tracked**, not only the wallets you picked, and each gets its own device, in a group by asset type.
- **Group titles and the integration's own messages start in English** after the upgrade, whatever language Home Assistant runs in. Choose another language under **Configure** on each service (see [Languages](#languages)).
- **Wallets of assets you no longer hold go away.** They are migrated like the others, then removed after three portfolio refreshes without them — about ten minutes after the Portfolio first starts after the upgrade: your old key still reads the portfolio, only Earn needs the new one. Their recorded history stays until the recorder purges it.
- **The wallet sensor still shows the unstaked part**, as before, now named **Balance (available)**. Beside it, every wallet gets the new **Balance (total)** for the whole position, and **Balance (staking)** for the staked part while something is staked or Bitpanda offers an Earn product for the asset; they start without history.
- **Portfolio Total value now covers your whole account** — every holding plus all fiat. It used to add up only the wallets you tracked, so its value steps up at the upgrade: check automations that compare it against a threshold.
- **The fiat wallet in your currency — without one, your only fiat wallet, whatever its currency — becomes Portfolio Cash**, which sums all your fiat balances. Other fiat wallets are left as `unavailable` entities you can delete.
- **Prices in other currencies are converted with ECB daily rates** instead of being quoted by Bitpanda.
- **Long-term statistics.** Every value sensor now keeps them, from the upgrade on (see [Long-term statistics](#long-term-statistics)).
- **A failed `bitpanda.refresh` now fails the call**, and stops a script or automation at that step unless the step sets `continue_on_error: true` (see [Refreshing by hand](#refreshing-by-hand)).
- **Attributes:** `balance` is now `units` (on Balance (available) the unstaked units, as before); the wallet's `price` — now from Bitpanda's price ticker — and the position performance are on Balance (total), APR and rewards on Balance (staking), and the Price Tracker's prices in other currencies carry `conversion_rate`, `rate_date` and `rate_source`. `breakdown`, `wallet_count`, `all_prices`, `trading_pair` and the `icon` attribute are gone.

---

## ⚠️ Known limitations

- **One Bitpanda account per Home Assistant.** Each service can be set up once, and Bitpanda's API does not tell which account a key belongs to: a key of another account — entered under **Reconfigure** or when Home Assistant asks for a new key — switches the Portfolio to that account. Its figures then follow the new account, and the wallets of assets the new account does not hold are removed after three refreshes. The Portfolio then announces that account's wallets as new and, for assets with an enabled Balance (staking) sensor, their past staking rewards. **To switch to another account, delete Bitpanda Portfolio (⋮ → Delete) and set it up again:** its wallets, sensors and the remembered announcements then start fresh for the new account.
- **Cloud polling only.** Bitpanda sends no updates by itself: the integration asks at the intervals under [Features](#-features), and `bitpanda.refresh` asks right away (see [Refreshing by hand](#refreshing-by-hand)).
- **Short outages are bridged, longer ones show.** When Bitpanda cannot be reached — while your Internet connection is down, say — the sensors keep their last value through two failed refreshes. The third failed refresh in a row, at least two regular intervals after the first, makes them `unavailable`: for the Portfolio and its returns after about 15 minutes, for prices after about 3 minutes (longer while Bitpanda rate-limits the requests). A rejected API key makes them `unavailable` at once. After a restart of Home Assistant during an outage, there is no last value to show.
- **What disappears waits ten minutes.** When Bitpanda's answer no longer lists something the Portfolio showed — an asset, all fiat, all Cash Plus, all your positions, or anything at all — the sensors that show it are `unavailable` at first, not 0: a short glitch at Bitpanda then leaves a gap in their history instead of a drop. Once three answers in a row, at least ten minutes apart from first to last, confirm it, the wallet is removed — and with the last wallet of a group, the group and its value — and Total value, Cash, Cash Plus, Invested or Total return shows 0. Refreshing by hand does not make that sooner. What is already missing when the Portfolio starts shows 0 at once.
- **Invested and Total return cover the positions you hold.** They add up what Bitpanda reports for each open position: what you gained or lost on an asset you sold is in neither, and so are Cash and Cash Plus. A position Bitpanda sends no invested amount for leaves them unknown.
- **A return's amount is worked out.** Bitpanda gives the return over a timeframe as a percentage, which leaves deposits and withdrawals out. `return_amount` is what that percentage means on today's Total value — Total value × return ÷ (100 + return), as the Portfolio card shows it — not the change of Total value over that time.
- **A group's value follows its wallets, not the card.** **Value: cryptocurrencies** and its siblings add up the wallets in each group, and a wallet stays in its first group when Bitpanda files its asset under another type later; the Portfolio card groups the wallets by their current `asset_category`. A group's `share_percent` divides by Total value, Cash and Cash Plus included; the card's allocation divides by the sum of the parts it shows.
- **Prices in other currencies are converted, not quoted.** Bitpanda's price endpoint answers in EUR only; every other currency — the Price Tracker's, and a wallet's `price` in a Portfolio outside EUR — is the EUR price × the ECB's daily reference rate, which can differ from the price Bitpanda itself shows in that currency. The ECB publishes its rates once per working day around 16:00 CET; at weekends and on holidays the last rate stays in use; on the Price Tracker the `rate_date` attribute shows which day's rate a price uses, a wallet's `price` does not say.
- **The 24-hour change needs a day of history.** `change_24h_pct` and `price_24h_ago` compare the price with its value from 24 hours ago in Home Assistant's statistics — the one nearest to that time within half an hour: a newly tracked price shows them only after a day, and they are missing while there is no value within that half hour, such as after Home Assistant was off, and never while the recorder does not record the sensor. A wallet's 24-hour figures compare its ticker price with the one its Balance (total) recorded about 24 hours ago, the same way: they appear one day after the update to this version or after the wallet appeared, and only while the wallet has a ticker price; the recorder keeps them for 10 days by default.

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| The integration does not load | The entry on the Bitpanda integration page says why its setup failed or is being retried; **Settings → Repairs** says what blocks an upgrade from a date version. If the upgrade itself failed — for example because Bitpanda could not be reached while Home Assistant started — the entry shows a migration error, the log says why, and the upgrade runs again at the next restart. |
| HACS offers no update while you are on a date version (2026.06.04 or older) | Install the newest version once by hand — see [Upgrading from a date version](#%EF%B8%8F-upgrading-from-a-date-version), step 2 |
| After the upgrade, old sensors stay `unavailable` on a device such as Bitpanda Wallets (old version, not migrated) | The upgrade could not migrate them, for example the wallet of an asset that Bitpanda's new API does not list yet. **Settings → Repairs → Bitpanda upgrade: entities not migrated** deletes them, together with the old device |
| "New Bitpanda API key needed" | The key expired, was revoked, or lacks a permission — paste a new key with all three permissions (see [Set up the Portfolio](#set-up-the-portfolio)) |
| Setup says permissions are missing | Create a new key with all three — permissions cannot be added to an existing key |
| **Add price tracker** fails after choosing **Bitpanda Portfolio** | Home Assistant up to 2026.9 lists both Bitpanda entries in that dialog: choose **Bitpanda Price Tracker**, or use **⋮ → Add price tracker** on its entry (see [Track prices](#track-prices)) |
| Dialogs show raw text | Reload the browser tab (`Ctrl+F5` / `Cmd+Shift+R`) — your browser cached old translations |
| Group titles or the integration's messages are in English while everything else is in your language | They follow the language chosen for each service — when it was added, or later under **Configure** — not Home Assistant's language; after an upgrade from a date version it is English. Choose your language under **Configure** |
| A wallet sensor is `unavailable` | The asset is no longer in your portfolio; the wallet is removed 10 to 15 minutes after you sold it, or at once with **⋮ → Delete** on its device page |
| An asset you hold has no wallet | Bitpanda's asset catalogue does not list the asset, at least not yet: without its name and type, no wallet can be set up. Its value still counts in **Total value**. Bitpanda's API names such an asset only by its ID; to see the ID, enable debug logging and reload the Bitpanda Portfolio. Once the catalogue lists it, the wallet appears within a day |
| A new wallet brought no notification | Check **Configure** on the Portfolio: the notification may be switched off. Wallets that existed when the Portfolio was set up or upgraded from a date version are not announced, and Home Assistant drops notifications at a restart. An asset sold and bought again within ten minutes keeps its wallet, so nothing is new. The event `bitpanda_wallet_added` comes even with the notification off |
| A staking reward brought no notification | The notification is off by default: switch it on under **Configure** on the Portfolio. Only assets with an enabled **Balance (staking)** sensor count, and the rewards are checked once an hour. Payouts made before you set up the Portfolio are not announced, and Home Assistant drops notifications at a restart. The event `bitpanda_staking_reward_received` comes even with the notification off |
| Every sensor of a service is `unavailable` | Bitpanda has not answered three refreshes in a row, or answered "too many requests" (see [Known limitations](#%EF%B8%8F-known-limitations)); after a restart during an outage this shows at once. Or it rejected the API key — then Home Assistant asks for a new one |
| Portfolio Total value, Cash, Cash Plus or a wallet sensor is `unknown` | Bitpanda answered, but an entry could not be read or came without a value; rather than show a figure that silently leaves something out, the sensor shows none until Bitpanda sends it again. Enable debug logging to see which entry. Cash Plus is also `unknown` while looking up an asset you hold fails at Bitpanda; the integration tries again at every refresh. |
| A return sensor is `unknown` | Bitpanda answered for that timeframe without a figure, for example while the account has no history for it yet |
| A return sensor is `unavailable` while the other returns are not | Bitpanda's answer for that timeframe failed three refreshes in a row; it kept its last value until then and comes back with the next answer |
| Total value, Cash or Cash Plus is `unavailable` while the returns are not | Bitpanda's answer no longer lists what it shows — you sold everything, withdrew all your money or ended Cash Plus. It shows 0 once three answers in a row, the last at least ten minutes after the first, confirm it (see [Known limitations](#%EF%B8%8F-known-limitations)) |
| No Balance (staking) sensor for an asset | It appears once something is staked or Bitpanda offers an Earn product for the asset |
| A price in another currency has no value and a `conversion` attribute | The ECB rates could not be loaded since the Price Tracker last started — a restart, or a reload after you added an asset or changed its options; the integration retries every 15 minutes and the value appears with the first success |
| One asset's price sensors are `unavailable` | Bitpanda returned no price for it three rounds in a row; see the warning in the log |
| Prices update less often than every minute | Bitpanda answered "too many requests": the integration waits longer between rounds, up to 16 minutes, and returns to every 60 seconds as soon as Bitpanda answers again. The log warns when it slows down, and Home Assistant adds one error line of its own, "Error fetching bitpanda_tickers data: Bitpanda received too many price requests. Retrying later"; that it is back shows only with debug logging. With many tracked assets a round itself takes a while: the next one starts 60 seconds after it ends. |
| A wallet has no `price` and no 24-hour figures, and the card shows "—" for its price | Bitpanda's price ticker has given no price for the asset for more than 15 minutes; the value of its staking rewards (`rewards_net_value`) is missing then too. The log warns once, naming the asset's ID (the device's serial number); that the price is back shows only with debug logging. Outside EUR the price also needs the ECB rates: until they load, Home Assistant logs "Error fetching bitpanda_portfolio_ecb data", and the integration retries every 15 minutes |
| 24-hour price change missing | A newly tracked price shows it after a day, and only while the recorder records the sensor. A wallet's 24-hour figures appear a day after the update to this version or after the wallet appeared, and only while it has a ticker price (see the row above and [Known limitations](#%EF%B8%8F-known-limitations)) |
| A Portfolio sensor keeps no statistics after you set the Portfolio up again in another currency, and **Settings → Repairs** reports "The unit of sensor.bitpanda_… has changed" | Home Assistant still holds its statistics in the old currency — if setup offered to delete them, you kept them. Delete them under **Settings → Tools → Statistics** (before Home Assistant 2026.8: **Developer tools → Statistics**), where the sensor is listed with the changed unit |
| A card shows "Custom element doesn't exist", or **Add card** does not list the Bitpanda cards | Search under **By card**: the card dialog opens on **By entity**, which lists entities only. Otherwise reload the page twice — your browser loads the cards when it opens Home Assistant, and the first reload after a new installation or an update can still come from its cache. A new browser tab works at once. In the Home Assistant app, reset its frontend cache (see [Dashboard cards](#-dashboard-cards)). The cards need no entry under **Resources**: the integration loads them itself |
| A card shows "—" where a value should be | The sensor behind it has no value right now; the rows above say why |
| A Price Tracker line is missing | Its lines come from Home Assistant's long-term statistics: a newly tracked price draws one once two statistics exist — after about ten minutes on 1D, two hours on 1W and 1M, the next day on 6M and 1Y |

**Still stuck?** Open an [issue](https://github.com/Spegeli/hacs_bitpanda/issues) with the diagnostics (**⋮ → Download diagnostics** on the entry; the API key is left out) and a debug log (**⋮ → Enable debug logging**).

---

## 🗑️ Removal

1. Remove the Bitpanda cards from your dashboards: without the integration they show "Custom element doesn't exist".
2. Go to **Settings → Devices & services → Bitpanda** and delete each service entry — **Bitpanda Portfolio** and **Bitpanda Price Tracker** — with **⋮ → Delete**. Their devices, their sensors and the API key stored in Home Assistant go with them.
3. Remove **Bitpanda** in HACS (its **⋮** menu → **Remove**). Installed manually: delete the `config/custom_components/bitpanda` folder.
4. Restart Home Assistant.
5. Optional: delete the API key at [app.bitpanda.com/my-account/apikey](https://app.bitpanda.com/my-account/apikey) if nothing else uses it.

**History:** the recorded history of the removed sensors stays in Home Assistant's database until the recorder purges it — after 10 days by default (the recorder's `purge_keep_days`).

**Long-term statistics** are not purged: delete them under **Settings → Tools → Statistics** (before Home Assistant 2026.8: **Developer tools → Statistics**) if you no longer want them. A later Portfolio setup in another currency offers to delete them.

---

## ⚖️ Disclaimer

- **Not a Bitpanda product.** This integration is an independent community project. Bitpanda does not develop, endorse or support it, and Bitpanda's support cannot help with it — use the [GitHub issue tracker](https://github.com/Spegeli/hacs_bitpanda/issues) instead.
- **Trademarks.** Bitpanda, the Bitpanda logo and other product names are trademarks of their respective owners. They appear here only to name the service the integration connects to.
- **Figures for information only.** The integration shows what Bitpanda's [public API](https://docs.public.bitpanda.com) returns; prices in other currencies are converted with ECB rates (see [Known limitations](#%EF%B8%8F-known-limitations)). Figures can be delayed or differ from the Bitpanda app. Nothing here is financial advice.
- **Use at your own risk.** The software is provided as is, without warranty, under the MIT License. It only reads your account and never trades — keep your API key private all the same.

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details. It covers this project's code and documentation, not Bitpanda's name and logo (`.github/readme/logo.png` and `custom_components/bitpanda/brand/`), which remain their owner's trademarks (see [Disclaimer](#%EF%B8%8F-disclaimer)).
