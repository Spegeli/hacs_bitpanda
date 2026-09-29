<p align="center">
  <img src="https://raw.githubusercontent.com/Spegeli/hacs_bitpanda/main/logo.png" alt="Bitpanda Logo" width="300">
</p>

# 🚀 Bitpanda – Home Assistant Integration

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg"></a>
  <a href="https://github.com/Spegeli/hacs_bitpanda/releases"><img src="https://img.shields.io/github/v/release/Spegeli/hacs_bitpanda.svg?label=release&color=blue&display_name=release"></a>
  <img src="https://img.shields.io/badge/License-MIT-green.svg">
</p>

A custom <a href="https://www.home-assistant.io/">Home Assistant</a> integration for **Bitpanda**: your whole portfolio, and live prices of any asset, on your dashboard.

[Bitpanda](https://www.bitpanda.com) is a European investment platform for crypto, stocks, ETFs, ETCs and precious metals. The integration reads your account and Bitpanda's prices; it never trades.

> [!IMPORTANT]
> **Updating from a date version (2026.06.04 or older)?** Read [Upgrading from a date version](#%EF%B8%8F-upgrading-from-a-date-version) first — it needs a new API key and cannot be undone.

---

## ✨ Features

The integration offers two services. Set up either or both — each one once.

### Bitpanda Portfolio
- A **Portfolio** device: **Total value** (all holdings, Cash Plus included, and all fiat), **Cash** (all fiat, including money reserved by an open order), **Cash Plus**, and your **return** over a day, a week, a month, six months and a year — every value in your Portfolio currency, as Bitpanda reports it
- A wallet device for every asset you hold, such as **Vision (VSN) Wallet**, with **Balance (available)** (the value of the units you can trade), **Balance (total)** (the whole position, with invested amount, average buy price and return) and — while something is staked or Bitpanda offers Earn for the asset — **Balance (staking)** (with APR and rewards)
- Nothing to maintain: a wallet appears at the next update after you buy an asset and goes about 15 minutes after you sell it, in groups by asset type such as Cryptocurrencies or Precious metals
- Updates every 5 minutes; Earn offers daily, rewards hourly

### Bitpanda Price Tracker
- Live prices for more than 14,000 assets — crypto, stocks, ETFs, ETCs, Bitpanda Crypto Indices and tokenized precious metals — **without an API key**
- One device per tracked asset, such as **Bitcoin (BTC) Price Tracker**, in groups by asset type, with a price sensor in EUR (**Bitcoin (BTC) Price Tracker EUR**) and, optionally, one in each of the other 11 supported currencies
- EUR prices come from Bitpanda every 60 seconds. Above 30 tracked assets the interval stretches automatically, so the integration never sends more than 1,800 price requests per hour. Should it grow past 30 minutes (above 900 tracked assets), **Settings → Repairs** says so until you track fewer
- Other currencies are converted with the daily reference rates of the European Central Bank (ECB), fetched every 6 hours
- 24h price change (`change_24h_pct`) as an attribute, from the Home Assistant recorder

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
| Language of group titles (per service) | when you add the service, later **Configure** (⚙) on its entry | group titles; for the Portfolio also the message why a device cannot be deleted — at once |

Entity IDs, device names and log messages are always English. A group you renamed keeps its name; a service upgraded from a date version starts in English. For everything in one language, set all three and restart Home Assistant.

---

## 📋 Requirements

- Home Assistant **2025.5** or newer
- For the Portfolio: a Bitpanda account and an API key (see [Set up the Portfolio](#set-up-the-portfolio)). The Price Tracker needs neither.

---

## 📦 Installation

### Via HACS (recommended)

Click the button below to automatically add the repository to HACS:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Spegeli&repository=hacs_bitpanda&category=Integration)

Or add it by hand:

1. Open **HACS**, select **⋮** (top right) → **Custom repositories**
2. Enter `https://github.com/Spegeli/hacs_bitpanda`, choose the type **Integration**, select **Add**
3. Open **Bitpanda** in HACS and select **Download**
4. Restart Home Assistant

### Manual

1. Download the source code (zip) of the latest release from the [releases page](https://github.com/Spegeli/hacs_bitpanda/releases)
2. Copy its `custom_components/bitpanda` folder to `config/custom_components/bitpanda`
3. Restart Home Assistant

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
   - ⚠️ Scopes cannot be added to an existing key afterwards.
3. Copy your API key — **you will only see it once!** Home Assistant stores it locally and sends it only to Bitpanda; the integration never logs it, and diagnostics leave it out.
4. Go to **Settings → Devices & services → Add integration**, search for **Bitpanda**, select it, and choose **Bitpanda Portfolio** in the dialog that follows. If the Price Tracker is already set up, **Add service** on the Bitpanda integration page opens the same dialog. It lists only what is not set up yet.
5. Enter your API key — setup checks all three scopes and names any that is missing — then choose your currency and the language of group titles and messages (see [Languages](#languages))

Bitpanda API keys expire on the date you choose when you create them, **one year** later at most. Home Assistant then asks for a new one — see [Changing settings later](#changing-settings-later).

### Set up the Price Tracker

1. Go to **Settings → Devices & services → Add integration**, search for **Bitpanda**, select it, and choose **Bitpanda Price Tracker** in the dialog that follows. If the Portfolio is already set up, **Add service** on the Bitpanda integration page opens the same dialog.
2. Choose additional currencies if you want them — every asset always gets its EUR sensor — and the language of group titles (see [Languages](#languages))

#### Track prices

The Price Tracker shows its assets in groups by type — Cryptocurrencies, Stocks, ETFs, ETCs, Crypto indices, Precious metals — with one device per asset inside.

1. Select **Add price tracker** at the top of the Bitpanda integration page. With the Portfolio set up as well, a dialog first asks for the entry: pick **Bitpanda Price Tracker** (up to Home Assistant 2026.9, picking **Bitpanda Portfolio** there fails).
   - Before Home Assistant 2025.7 there is no such button: use **⋮ → Add price tracker** on the **Bitpanda Price Tracker** entry. That menu item works on every version and skips the dialog.
2. Choose the **Asset type**: Crypto, Stocks, ETFs, ETCs, Crypto indices or Precious metals.
3. Choose the asset. Type a name or a symbol to search the list — for stocks, ETFs and ETCs also an ISIN. Each entry reads `Name / SYMBOL`, for stocks, ETFs and ETCs `Name / SYMBOL / ISIN`.

The asset gets its own device in the group of its type; the first asset of a type creates the group. The integration keeps each list for 24 hours; loading a large one such as Stocks the first time takes about ten seconds.

#### Stop tracking

- **One asset:** open its device and select **⋮ → Delete**.
- **A whole group:** select **⋮ → Delete** on the group, under the **Bitpanda Price Tracker** entry of the integration page.

Tracking an asset again later brings its sensors back under the entity IDs the integration gives them, with their history (your own changes: see [Resetting names and entity IDs](#resetting-names-and-entity-ids)).

### Changing settings later

**Configure** — the ⚙ on each service's entry (before Home Assistant 2025.7 a button labelled **Configure**):

- **Price Tracker:** the extra currencies and the language of group titles. Removing a currency deletes its sensors; adding it back brings them back under the entity IDs the integration gives them, with their history.
- **Portfolio:** the language of group titles and messages (see [Languages](#languages)).

**⋮ → Reconfigure** on the Portfolio entry:

- **Replace the API key** at any time. Leave the key field empty to keep the current one.
- **Change the currency.** ⚠️ This deletes all Portfolio sensors including their history and long-term statistics and recreates them in the new currency, under the entity IDs the integration gives them (your own changes: see [Resetting names and entity IDs](#resetting-names-and-entity-ids)). You are asked to confirm first.

**New Bitpanda API key needed:** when Bitpanda rejects the stored key — it expired, was revoked, or lacks a permission — Home Assistant asks for a new one. Paste it there; every sensor is kept.

---

## 📊 Using the sensors

The Portfolio keeps its wallets and groups up to date by itself:

- **A new asset** gets its wallet, in the group of its type, at the next update — every five minutes.
- **An asset you no longer hold** loses its wallet about ten minutes after Bitpanda stops listing it. To remove the wallet sooner, delete it on its device page (**⋮ → Delete**).
- **What you cannot delete:** the Portfolio device and the wallet of an asset you hold — they would come straight back, and the dialog says why. A group you delete (**⋮ → Delete**) while you still hold its assets comes back at the next update.

On the Price Tracker, deleting a device or a group stops tracking (see [Stop tracking](#stop-tracking)).

### Entity IDs

The integration gives every sensor an English entity ID, the same in every language: `sensor.bitpanda_`, then the device's name in lower case with `_` for spaces and punctuation, then the sensor's own ending. Device names are English too — the asset's label followed by **Wallet** or **Price Tracker**. Assets are labelled `Name (SYMBOL)`, or just the symbol when the name only repeats it (BNB, BCI5). Stocks, ETFs and ETCs add their ISIN: `Name (SYMBOL / ISIN)`, or `SYMBOL (ISIN)` when the name only repeats the symbol.

You can change an entity ID in the sensor's settings: the sensor keeps working under the new ID, with its history, and the integration does not change it back — only a currency change, which recreates the Portfolio's sensors, returns to the integration's IDs. To go back yourself, see [Resetting names and entity IDs](#resetting-names-and-entity-ids).

| Sensor | Entity ID |
|---|---|
| Portfolio Total value / Cash / Cash Plus | `sensor.bitpanda_portfolio_total`, `sensor.bitpanda_portfolio_cash`, `sensor.bitpanda_portfolio_cash_plus` |
| Portfolio returns | `sensor.bitpanda_portfolio_return_day`, `_week`, `_month`, `_6_months`, `_year` |
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
| Balance (available) — every wallet | `asset`, `asset_name`, `asset_isin`, `units` (tradable units) |
| Balance (total) — every wallet | `asset`, `asset_name`, `asset_isin`, `units` (whole position), and the position performance: `average_buy_price`, `invested_amount`, `total_return`, `total_return_percent` |
| Balance (staking) — while something is staked or an Earn product is offered | `asset`, `asset_name`, `asset_isin`, `units` (staked), `apr_percent`, `rewards_gross`, `rewards_fee`, `rewards_net`, `rewards_net_value`, `rewards_count`, `rewards_last_at` |
| Portfolio Cash Plus | `eur`, `usd`, `gbp` — the amount of each held Cash Plus product in its own currency |
| Price (EUR) | `asset`, `asset_name`, `asset_isin`, `change_24h_pct`, `price_24h_ago` |
| Price (other currencies) | as EUR, plus `conversion` (status `no_rate` until the first ECB rate is loaded), `conversion_rate`, `rate_date`, `rate_source` (`ECB`) |

`asset_isin`, the ISIN, is there for stocks, ETFs and ETCs only.

The lifetime reward amounts `rewards_gross`, `rewards_fee` and `rewards_net` are in units of the asset, and `rewards_count` is the number of payouts; `rewards_net_value` is what the net rewards are worth at today's price, as the Bitpanda app shows it — not their value when they were paid out.

### Long-term statistics

Every value sensor keeps long-term statistics: the Portfolio's figures, returns and wallets, and every price.

- **To show them** over weeks or months, use a **Statistics graph** card. Under **Show stat types**, choose *State* for a money value and *Mean*, *Min* or *Max* for a return.
- **A currency change** deletes the Portfolio sensors' statistics along with their history — they were recorded in the old currency.

### Refreshing by hand

The action `bitpanda.refresh` fetches the portfolio and the prices right away and finishes when both are done.

- **Cooldown:** a call within the cooldown of the last accepted one is ignored. The cooldown is the price interval — 60 seconds, longer with many tracked assets — or 10 seconds with the Portfolio alone.
- **Failures:** when a refresh fails — Bitpanda cannot be reached, answers with an error, or reports an empty portfolio that is not confirmed yet — the action fails with an error naming the service; the other service is refreshed all the same. The action also fails while neither service is loaded.
- **In automations:** a failed action stops a script or automation at that step, unless the step sets `continue_on_error: true` (see the [second example](#-automation-examples)).

---

## 🤖 Automation examples

Paste one into a new automation's YAML editor (in the automation editor: **⋮ → Edit in YAML**) and adjust the entity IDs and the numbers. A price sensor's entity ID ends in its currency: for US dollars, use `sensor.bitpanda_bitcoin_btc_price_tracker_usd` once USD is one of the Price Tracker's extra currencies, and write the threshold in USD. Every example works from Home Assistant 2025.5 on.

**Price alert** — a notification once Bitcoin rises above 100,000 EUR. It fires when the price crosses the threshold, not while it stays above, and at most once an hour, so a price that swings around the threshold does not flood you with messages. The first condition keeps it quiet when the price only comes back after an outage or a restart. Use `below:` for a fall; add `for: "00:05:00"` to the trigger to ignore a spike shorter than five minutes.

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

**Big move** — a notification when Bitcoin has risen or fallen by more than 10 % within 24 hours (the sensor's `change_24h_pct` attribute), again at most once an hour.

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

**Morning report** — ask Bitpanda at a set time instead of waiting for the next regular update, then show the portfolio's total value and today's return. With `continue_on_error: true`, a failed refresh (see [Refreshing by hand](#refreshing-by-hand)) does not stop the automation: the report still comes, with the last figures.

```yaml
alias: Bitpanda morning report
triggers:
  - trigger: time
    at: "07:00:00"
actions:
  - action: bitpanda.refresh
    continue_on_error: true
  # Runs even when the refresh failed, then with the last figures.
  - action: persistent_notification.create
    data:
      title: Bitpanda
      message: "Portfolio: {{ states('sensor.bitpanda_portfolio_total', with_unit=True) }}, today {{ states('sensor.bitpanda_portfolio_return_day', with_unit=True) }}"
```

The same steps work in a script, which you can start from anywhere — from a button, for example.

**Staking reward** — a notification when a new staking reward arrives, on the staking sensor of one wallet (here Ethereum). It compares the number of payouts (`rewards_count`), so a restart stays quiet.

```yaml
alias: New Ethereum staking reward
triggers:
  - trigger: state
    entity_id: sensor.bitpanda_ethereum_eth_wallet_staking
    attribute: rewards_count
conditions:
  # Only a new payout: the count went up, it did not just appear after a restart.
  - condition: template
    value_template: "{{ trigger.from_state is not none and trigger.from_state.attributes.rewards_count is number and trigger.to_state.attributes.rewards_count > trigger.from_state.attributes.rewards_count }}"
actions:
  - action: persistent_notification.create
    data:
      title: Ethereum staking
      message: "New reward: {{ trigger.to_state.attributes.rewards_net }} ETH net so far."
```

---

## ⬆️ Upgrading from a date version

For every version before 2.0.0: the date versions, 2026.06.04 and older. Version 2.0.0 moves to Bitpanda's new Public API and splits the integration into two services. It needs Home Assistant **2025.5** or newer — on 2025.3 or 2025.4 the entry is left unmigrated, the integration does not load, and **Settings → Repairs** asks you to update Home Assistant; older versions cannot load the integration at all.

⚠️ **The upgrade is one-way.** The previous release cannot load the migrated entries, so going back to it afterwards does not work. Make a backup before you update if you may want to return.

1. Create a new API key with **Balances**, **Transaction** and **Earn (Read)** at [app.bitpanda.com/my-account/apikey](https://app.bitpanda.com/my-account/apikey) — keys from the classic site, web.bitpanda.com, lack Earn
2. Update the integration through HACS and restart Home Assistant
   - HACS offers no update? From 2.0.0 on, versions are numbers instead of dates, and HACS can rank a date such as 2026.06.04 above them. Install the newest version once by hand: **HACS → Bitpanda → ⋮ → Redownload**, open **Need a different version?**, pick the newest version not marked as a pre-release and download it. Later updates show up as usual.
   - No version choice in HACS? Open **Settings → Tools → Actions** (before Home Assistant 2026.8: **Developer tools → Actions**) and run `update.install` with the Bitpanda update entity and, as version, the newest release's tag (such as `v2.1.0`).
3. **Reload the browser tab** (`Ctrl+F5` / `Cmd+Shift+R`) — otherwise the integration's dialogs can show raw text from your browser's cached translations
4. Home Assistant shows **New Bitpanda API key needed** — paste the new key (or use **⋮ → Reconfigure** on the Bitpanda Portfolio entry)
5. The upgrade details appear under **Settings → Repairs**, in your profile language: **every renamed entity ID (old → new)**, the entities that could not be migrated, the Portfolio's switch to EUR if your old currency is not available, and the assets to add to a Bitpanda Price Tracker you had already set up — its prices are not moved into one that existed before the upgrade. The Home Assistant log keeps the same list in English, with the reason for each entity that was not migrated. **Check your dashboards, automations and scripts** for the old IDs.

**What is kept:** the history of every migrated sensor (it moves with the rename), your price trackers (now in the Bitpanda Price Tracker, in EUR and in your old currency) and the wallets of assets you still hold. Entity IDs you renamed yourself are left as they are.

**What changes:**

- **Two services.** Your entry becomes **Bitpanda Portfolio**; your price trackers move to a new **Bitpanda Price Tracker** entry.
- **Entity IDs follow the new scheme**, for example `sensor.bitpanda_wallets_vsn_wallet` → `sensor.bitpanda_vision_vsn_wallet_available` and `sensor.bitpanda_price_tracker_btc_eur` → `sensor.bitpanda_bitcoin_btc_price_tracker_eur`.
- **Every holding is tracked**, not only the wallets you picked, and each gets its own device, in a group by asset type.
- **Group titles and the integration's own messages start in English** after the upgrade, whatever language Home Assistant runs in. Choose another language under **Configure** on each service (see [Languages](#languages)).
- **Wallets of assets you no longer hold go away.** They are migrated like the others, then removed after three portfolio refreshes without them — about ten minutes after the Portfolio starts working with your new key. Their recorded history stays until the recorder purges it.
- **The wallet sensor still shows the unstaked part**, as before, now named **Balance (available)**. Beside it, every wallet gets the new **Balance (total)** for the whole position, and **Balance (staking)** for the staked part while something is staked or Bitpanda offers an Earn product for the asset; they start without history.
- **Portfolio Total value now covers your whole account** — every holding plus all fiat. It used to add up only the wallets you tracked, so its value steps up at the upgrade: check automations that compare it against a threshold.
- **The fiat wallet in your currency becomes Portfolio Cash**, which sums all your fiat balances. Other fiat wallets are left as `unavailable` entities you can delete.
- **Prices in other currencies are converted with ECB daily rates** instead of being quoted by Bitpanda.
- **Long-term statistics.** Every value sensor now keeps them, from the upgrade on (see [Long-term statistics](#long-term-statistics)).
- **A failed `bitpanda.refresh` now fails the call**, and stops a script or automation at that step unless the step sets `continue_on_error: true` (see [Refreshing by hand](#refreshing-by-hand)).
- **Attributes:** `balance` is now `units` (on Balance (available) the unstaked units, as before); the position performance is on Balance (total), APR and rewards on Balance (staking), and prices in other currencies carry `conversion_rate`, `rate_date` and `rate_source`. `breakdown`, `wallet_count`, `all_prices`, `trading_pair`, the wallet `price` and the `icon` attribute are gone.

---

## ⚠️ Known limitations

- **One Bitpanda account per Home Assistant.** Each service can be set up once, and Bitpanda's API does not tell which account a key belongs to: a key of another account — entered under **Reconfigure** or when Home Assistant asks for a new key — switches the Portfolio to that account. Its figures then follow the new account, and the wallets of assets the new account does not hold are removed after three refreshes.
- **Cloud polling only.** Bitpanda sends no updates by itself: the integration asks at the intervals under [Features](#-features), and `bitpanda.refresh` asks at once (see [Refreshing by hand](#refreshing-by-hand)).
- **Short outages are bridged, longer ones show.** When Bitpanda cannot be reached — while your Internet connection is down, say — the sensors keep their last value through two failed refreshes. The third failed refresh in a row, at least two regular intervals after the first, makes them `unavailable`: after about 15 minutes for the Portfolio and its returns, about 3 minutes for prices (longer above 30 tracked assets, or while Bitpanda rate-limits the requests). A rejected API key makes them `unavailable` at once, and after a restart of Home Assistant during an outage there is no last value to show.
- **A sudden empty portfolio is held back.** If Bitpanda suddenly reports a completely empty portfolio, nothing is removed and the last figures stay until three empty answers in a row, at least ten minutes apart from first to last, confirm it.
- **Prices in other currencies are converted, not quoted.** Bitpanda's price endpoint answers in EUR only; every other currency is the EUR price × the ECB's daily reference rate, which can differ from the price Bitpanda itself shows in that currency. The ECB publishes its rates once per working day around 16:00 CET; at weekends and on holidays the last rate stays in use, and the `rate_date` attribute shows which day's rate a price uses.

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| Integration doesn't load | The entry on the Bitpanda integration page says why its setup failed or is being retried; **Settings → Repairs** says what blocks an upgrade from a date version. If Bitpanda could not be reached while Home Assistant started, the upgrade runs again at the next restart. |
| HACS offers no update while you are on a date version (2026.06.04 or older) | Install the newest version once by hand — see [Upgrading from a date version](#%EF%B8%8F-upgrading-from-a-date-version), step 2 |
| "New Bitpanda API key needed" | The key expired, was revoked, or lacks a scope — paste a new key with all three scopes |
| Setup says permissions are missing | Create a new key with all three scopes — scopes cannot be added to an existing key |
| Dialogs show raw text | Reload the browser tab (`Ctrl+F5` / `Cmd+Shift+R`) — your browser cached old translations |
| Group titles or the integration's messages are in English while everything else is in your language | They follow the language chosen for each service — when it was added, or later under **Configure** — not Home Assistant's language; after an upgrade from a date version it is English. Choose your language under **Configure** |
| A wallet sensor is `unavailable` | The asset is no longer in your portfolio; the wallet is removed after about 15 minutes, or at once with **⋮ → Delete** on its device page |
| Every sensor of a service is `unavailable` | Bitpanda has not answered three refreshes in a row (see [Known limitations](#%EF%B8%8F-known-limitations)), or it rejected the API key — then Home Assistant asks for a new one |
| Portfolio Total value, Cash, Cash Plus or a wallet sensor is `unknown` | Bitpanda answered, but an entry could not be read or came without a value; rather than show a figure that silently leaves something out, the sensor shows none until Bitpanda sends it again. Enable debug logging to see which entry. Cash Plus is also `unknown` while an asset you hold cannot be looked up at Bitpanda; the integration tries again at every refresh. |
| A return sensor is `unknown` | Bitpanda answered for that timeframe without a figure, for example while the account has no history for it yet |
| A return sensor is `unavailable` while the other returns are not | Bitpanda's answer for that timeframe failed three refreshes in a row; it kept its last value until then and comes back with the next answer |
| The Portfolio still shows your holdings after you emptied your account | An empty answer from Bitpanda counts only once three answers in a row, at least ten minutes apart from first to last, confirm it; until then the last figures stay, and refreshing by hand does not make that sooner. Right after a restart there are no last figures: Total value, Cash, Cash Plus and the wallets are `unavailable` until then. |
| No Balance (staking) sensor for an asset | It appears once something is staked or Bitpanda offers an Earn product for the asset |
| A price in another currency has no value and a `conversion` attribute | The ECB rates could not be loaded since Home Assistant started; the integration retries every 15 minutes and the value appears with the first success |
| One asset's price sensors are `unavailable` | Bitpanda returned no price for it three rounds in a row; see the warning in the log |
| 24h price change missing | The Recorder integration must be active and have at least 24 hours of history |

**Still stuck?** Open an [issue](https://github.com/Spegeli/hacs_bitpanda/issues) with the diagnostics (**⋮ → Download diagnostics** on the entry; the API key is left out) and a debug log (**⋮ → Enable debug logging**).

---

## 🗑️ Removal

1. Go to **Settings → Devices & services → Bitpanda** and delete each service entry — **Bitpanda Portfolio** and **Bitpanda Price Tracker** — with **⋮ → Delete**. Their devices and sensors go with them.
2. Remove **Bitpanda** in HACS (its **⋮** menu → **Remove**). Installed manually: delete the `config/custom_components/bitpanda` folder.
3. Restart Home Assistant.
4. Optional: delete the API key at [app.bitpanda.com/my-account/apikey](https://app.bitpanda.com/my-account/apikey) if nothing else uses it.

The recorded history of the removed sensors stays in Home Assistant's database until the recorder purges it — after 10 days by default (the recorder's `purge_keep_days`). Their long-term statistics are not purged; delete them in the **Statistics** tab under **Settings → Tools** (before Home Assistant 2026.8: **Developer tools**) if you no longer want them.

---

## ⚖️ Disclaimer

This integration is **not officially developed or supported by Bitpanda**. It is an independent community project using the public [Bitpanda API](https://docs.public.bitpanda.com). Use it at your own risk.

For integration-related issues, please use the [GitHub issue tracker](https://github.com/Spegeli/hacs_bitpanda/issues).

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
