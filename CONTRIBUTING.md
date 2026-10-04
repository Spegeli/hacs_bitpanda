# Contributing

Thanks for your interest in improving this integration. This is a small personal project, so the process is deliberately light.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- **Report a security vulnerability** — privately, never as a public issue: see the [security policy](SECURITY.md).
- **Report a bug** — [open a bug report](https://github.com/Spegeli/hacs_bitpanda/issues/new?template=bug_report.yml). Concrete numbers and diagnostics help most.
- **Suggest a feature** — [open a feature request](https://github.com/Spegeli/hacs_bitpanda/issues/new?template=feature_request.yml).
- **Improve translations** — corrections and new languages are welcome, see [Translations](#translations).
- **Submit a change** — see [Pull requests](#pull-requests).

## Branches

- **`main`** holds the released code. It changes only through the pull request from `dev` and through a release's version commit, and it merges only with a green **Validation result** (see [Continuous integration](#continuous-integration)).
- **`dev`** is where work comes together; betas are released from it.
- **Topic branches** start from `dev` and go back into it.

## Pull requests

1. Fork the repository and branch from `dev`.
2. Keep the change focused — one topic per pull request.
3. Write the commit messages as [Conventional Commits](https://www.conventionalcommits.org) — see [Commit messages](#commit-messages).
4. Open the pull request against `dev` and fill in the template.
5. Validate checks it automatically (see [Continuous integration](#continuous-integration)); it is merged once its **Validation summary** is green. A first-time contributor's run waits for the maintainer's approval, so run the tests and mypy yourself first (see [Tests and typing](#tests-and-typing)): you get the answer sooner.

**Do not bump the version in `manifest.json`.** The Create Release workflow sets it (see [Releases](#releases)).

## Development setup

No build step and no dependencies beyond Home Assistant itself.

1. Fork and clone the repository.
2. Copy `custom_components/bitpanda/` into your Home Assistant `config/custom_components/` directory — or symlink it, so edits apply without copying again.
3. Restart Home Assistant.
4. Add the integration: **Settings → Devices & services → Add integration → Bitpanda**.

The Portfolio needs a Bitpanda API key with all three required read scopes — **Balances**, **Transaction** and **Earn (Read)**, as Bitpanda's English key page names them (create one at [app.bitpanda.com/my-account/apikey](https://app.bitpanda.com/my-account/apikey); the classic web.bitpanda.com has no Earn (Read)). The Price Tracker needs none.

To see what the integration is doing, enable debug logging in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.bitpanda: debug
```

### Tests and typing

Tests use `pytest-homeassistant-custom-component`, whose harness does not run on Windows. Each of its releases pins one Home Assistant release; the suite runs against the newest stable Home Assistant that has one, never a beta, as CI does (see [Continuous integration](#continuous-integration)). `python .github/scripts/ha_version.py` names that release and its package release, `--plugin` the package release alone. `tests/requirements.txt` pins mypy and the rest. Install mypy from that file too, never with a bare `pip install mypy`: another mypy release can report errors CI does not, or miss ones it does. The tests and mypy need Python 3.14; the integration itself must still run on 3.13 (see [Things that are easy to get wrong](#things-that-are-easy-to-get-wrong)). On Linux or macOS, with Python 3.14:

```bash
pip install -r tests/requirements.txt "pytest-homeassistant-custom-component==$(python .github/scripts/ha_version.py --plugin)"
python -m pytest tests/ -q --cov=custom_components.bitpanda --cov-report=term-missing --cov-fail-under=95
python -m mypy --strict
```

`pytest` runs the suite and reports the line coverage of each file, and fails under 95 % overall, as CI does; `mypy` checks the types of the integration and of the scripts in `.github/scripts` in strict mode, as `pyproject.toml` configures it — the tests are not type-checked.

The same in Docker, on any system, with the Python version and the requirements CI uses; each run installs them afresh, which takes a few minutes. On Windows, run it from PowerShell: Git Bash rewrites the mount path.

```bash
docker run --rm -v "${PWD}:/workspace" -w /workspace python:3.14 sh -c 'pip install -q -r tests/requirements.txt "pytest-homeassistant-custom-component==$(python .github/scripts/ha_version.py --plugin)" && python -m pytest tests/ -q --cov=custom_components.bitpanda --cov-report=term-missing --cov-fail-under=95 && python -m mypy --strict'
```

On the minimum Home Assistant in `hacs.json`, as CI's second test job runs it (no coverage gate):

```bash
docker run --rm -v "${PWD}:/workspace" -w /workspace python:3.13 sh -c 'pip install -q -r tests/requirements-floor.txt && python -m pytest tests/ -q'
```

CI runs both (see [Continuous integration](#continuous-integration)): the suite must pass with at least 95 % line coverage, and `mypy --strict` must report no error. `config_flow.py` and `asset_flow.py` stay at 100 %, and every test that shows an error in a dialog goes on to finish that dialog.

## Project layout

Everything lives in `custom_components/bitpanda/`:

| File | Responsibility |
|---|---|
| `__init__.py` | Setup and unload per service, deleting devices from their device page, the `bitpanda.refresh` action (registered once, in `async_setup`) |
| `announcements.py` | The Portfolio's announcements, each an event and, unless switched off, a notification in the Portfolio's language: a wallet new to the Portfolio (`bitpanda_wallet_added`) and new staking payouts (`bitpanda_staking_reward_received`) |
| `api.py` | `BitpandaApiClient` — all HTTP calls; keyless for public endpoints |
| `assets.py` | Asset categories (`asset_category`), legacy symbol resolution (`pick_legacy`), `AssetDirectory` for holding metadata, list labels |
| `asset_flow.py` | The "Add price tracker" subentry flow and the cached catalogue listings |
| `config_flow.py` | Service menu, Portfolio setup/reauth/reconfigure, Price Tracker setup, the options (Configure) of both services, import |
| `const.py` | Domain, URLs, scopes, currencies, intervals, budgets |
| `devices.py` | Device lookups scoped to their config entry |
| `diagnostics.py` | Diagnostics per service, API key redacted |
| `ecb.py` | ECB daily reference rates |
| `groups.py` | Groups by asset type (config subentries): titles, lookups, the Price Tracker's tracked assets, the Portfolio's wallet groups |
| `icons.json` | Every sensor's icon, by its translation key, and the `bitpanda.refresh` action's icon — never set an icon in code |
| `language.py` | The language of the integration's own texts: each entry's language option, the shipped languages |
| `migration.py` | Migration of version 1 (legacy API) entries to version 3; tells the user what changed, and what keeps an entry from being upgraded, as repair issues; finds the entities it left in place and, for `repairs.py`, deletes them |
| `naming.py` | Labels, device names, entity IDs, unique_ids, device identifiers |
| `portfolio_coordinator.py` | Portfolio, History, Earn and Rewards coordinators |
| `portfolio_model.py` | Pure data model: holdings, value split, Cash Plus, Earn, rewards |
| `portfolio_sensor.py` | Portfolio sensors and the wallet lifecycle manager, which also keeps the wallet groups |
| `portfolio_store.py` | What each Portfolio remembers, in `.storage/bitpanda.portfolio.<entry_id>`, one section per feature: the assets known — announced, or there when the list began — (`known_wallets`), and the newest announced staking payout per asset (`known_rewards`) |
| `price_coordinator.py` | Keyless ticker coordinator with its request budget, and the repair issue while that stretches its interval past 30 minutes; ECB coordinator |
| `price_sensor.py` | Price sensors per asset and currency |
| `purge.py` | On a currency change, deletes the Portfolio's sensors and devices with their history and long-term statistics, and the history and statistics of its sensors removed earlier; at setup, the history and statistics an earlier Portfolio left in another currency |
| `repairs.py` | The fix flow of the upgrade's repair issue for entities not migrated: after a confirmation, deletes them and each old device left empty |
| `sensor.py` | Dispatches the sensor platform to the service |
| `streaks.py` | The rule for things in a row — failed refreshes, empty answers, missing holdings — confirmed by count and time |
| `strings.json`, `translations/` | UI strings, seven languages (see [Translations](#translations)) |
| `tolerance.py` | `TolerantCoordinator` and `TolerantEntity`: sensors keep their last data through short outages |

The Portfolio polls `/portfolio` and `/portfolio-history` every 5 minutes, `/operations` every hour and `/earn/configs` every 24 hours, all with the key. The Price Tracker polls `/tickers` without a key — every 60 seconds, stretched above 30 assets to stay within 1,800 requests per hour — and the ECB every 6 hours when extra currencies are configured. Add new reads to an existing coordinator rather than polling from a sensor.

The wallet lifecycle manager (`PortfolioEntityManager`) runs after every portfolio refresh. It adds and removes the wallet devices and keeps them in wallet groups, config subentries it creates and removes itself; a group the user deletes comes back with the next refresh while its assets are still held. So the Portfolio's update listener reloads the entry only when `entry.data` or `entry.options` changed since setup — subentry changes never reload it. The Price Tracker reloads only when its data, options or group data changed since its start: its groups hold what it tracks. A change saved while it starts, before its update listener exists, is caught at the end of setup and reloads it once more. A new title for the entry or a group, or a changed system option, does not reload it; when polling is switched on or off, Home Assistant reloads the entry itself.

## Things that are easy to get wrong

**Every ticker price string carries exactly 8 decimals.** `90.93000000` for a stock, `0.00000032` for a micro-cap. Display precision is derived from the price's magnitude (`price_sensor.py`'s `display_precision`), never by counting the string's digits.

**`/portfolio` has no staked field.** Staked units are `balance − available_balance`, and the cent-rounded `currency_balance` of the whole position is split in that proportion (`portfolio_model.py`). A missing `currency_balance` is no value, never 0.

**Entity IDs are set explicitly.** Every entity sets its own `entity_id` from `naming.py`, in English: `sensor.bitpanda_`, the slug of its device's name — English too, "Vision (VSN) Wallet", "Bitcoin (BTC) Price Tracker" — and the sensor's own ending. Never let one derive from a translated name.

**Every value sensor keeps long-term statistics.** Money values set `state_class` `total` — the only state class Home Assistant allows for the monetary device class — and the returns `measurement`; a new sensor needs one too. Statistics are recorded in the sensor's unit, so a sensor whose currency can change must have its statistics cleared with its history: the currency purge (`purge.py`) does that for every Portfolio sensor, and `tests/test_currency_change.py` checks it with a real recorder. That includes a sensor removed earlier, such as a sold asset's wallet: it comes back under the same entity ID, and Home Assistant would record no statistics for it while the old ones remain. The purge finds such statistics under a Portfolio ID, and under an ID the user gave the sensor through the entity registry, which remembers a removed entity's ID. A new Portfolio setup finds statistics an earlier Portfolio left under the integration's entity IDs in another currency and offers to delete them (`purge.py`): a new entry has new unique_ids, so its sensors take the integration's IDs again, where old statistics in another unit would block them. Both the purge and the setup check count only statistics with a unit and without a live sensor: a deleted Portfolio or a removed sensor leaves neither an entity-registry entry nor a state, while a template's or another integration's sensor under such an ID has one.

**Home Assistant 2025.5 is the floor** (`hacs.json`), and only APIs that exist there may be used. It is set by the recorder: only from 2025.5 on does it move an entity's history along with an entity-ID rename made while Home Assistant starts, which is when the version 1 migration renames. The device registry's per-entry lookups (`async_get_device_by_identifier` and its siblings) do not exist at the floor, and `async_get_device` is deprecated — find a device through `devices.find_entry_device`. Home Assistant 2025.5 runs on Python 3.13, so the integration must run on 3.13 too, although the tests and mypy need 3.14: use no syntax and no standard-library API newer than 3.13 (such as `except A, B:` without parentheses), and keep `from __future__ import annotations` at the top of every module. 3.13 evaluates annotations as it defines a class or function, so without that line a name defined further down the module — the `PortfolioConfigEntry` a coordinator's `config_entry` is annotated with — fails the import there, while 3.14 evaluates them only when asked. CI compiles the integration with Python 3.13, checks that every module keeps `from __future__ import annotations`, and runs the suite on 2025.5; what the tests do not reach is for review.

**A device never moves between groups.** A wallet stays in the wallet group it sits in, even when Bitpanda files its asset under another type later: moving a device to another config subentry lists it in both on Home Assistant 2025.5, warns about it from 2026.8 on, and 2027.8 will refuse it. What a group holds is read from the entity registry (`groups.entities_by_group`), never from the device registry's `config_entries_subentries`, a deprecated compatibility property from 2026.8 on.

**A wallet is announced once, when it is new to the Portfolio.** The wallet lifecycle manager creates wallet entities at every start, after a currency change and after a deleted group, so `portfolio_store.py` tells a new wallet: the assets announced before, kept in the `known_wallets` section of the entry's file in `.storage`. The first refresh without that section — a new setup, an upgrade, an update from a version without it — fills it with every held asset except those Bitpanda's catalogue does not list, and with every asset whose wallet is still registered, and announces nothing. A wallet is announced when its wallet device is created — a restored one too, which Home Assistant reports as created — or at once when its device already exists; only then does its asset go into the file, and a reload in between announces it at the next start. During a start, the announcement waits until Home Assistant has started: automations arm their triggers only then. An asset leaves the file once it is neither held nor has a wallet — after a sale, or when the user deletes a sold asset's wallet; a deleted group or a currency change takes out no held asset. The notification texts live under `exceptions` (`wallet_added_title`, `wallet_added`), the one translation category Home Assistant loads for free messages with placeholders. If all of the wallet's sensors are disabled, the notification adds a second paragraph that says so (`wallet_added_sensors_disabled`). The event `bitpanda_wallet_added` is an interface for users' automations: add fields, never rename or drop one.

**A staking payout is announced once, together with the payouts missed before it.** `RewardsCoordinator` reads the whole `/operations` history every hour, but only while a Staking sensor listens, so the announcer must not listen itself: it hooks into `_async_refresh_finished`, which Home Assistant calls after every refresh. The `known_rewards` section of the entry's file (`portfolio_store.py`) keeps the time of the newest payout announced per asset; the payouts after it are new and go into one event and one notification per asset, with their number (`count`) and their sum. An asset is announced only while its Balance (staking) sensor is registered and enabled; otherwise its mark stays, and its payouts come together once the sensor is enabled again, as after Home Assistant was off. The first refresh without that section — a new setup, an update from a version without it, an unreadable section — marks every asset's newest payout and announces nothing. Each section of the file is read on its own, and saving keeps the sections the code does not know. The texts live under `exceptions` (`staking_reward_title`, `staking_reward`, `staking_rewards`, `staking_reward_value`); amounts use the decimal separator of the entry's language. The event `bitpanda_staking_reward_received` is an interface for users' automations: add fields, never rename or drop one.

**`/operations` cursors need milliseconds.** The server ignores a cursor whose timestamp has no fractional seconds and silently answers with page 1 — yet emits such cursors itself. `api.py` rewrites them (`normalize_operations_cursor`), and `_paginate` raises rather than return a partial listing when a cursor repeats. Never loosen that into "return what we have": a partial history publishes wrong lifetime totals as fact.

**A symbol is not an id.** The 14,000-asset catalogue lets one symbol name several assets — `XAU` is both Gold (a tokenized metal) and GoldMoney Inc (a stock). Always resolve to, cache and compare by asset id, never the bare symbol.

**Each authenticated endpoint needs one specific scope.** `/portfolio` needs Balances, `/operations` needs Transaction, `/earn/configs` needs Earn (Read). `/currencies`, `/assets` and `/tickers` are public endpoints that answer regardless of scope, so calling them successfully proves nothing about what a key can do.

**Sensors ride out short outages.** A sensor of the Portfolio, its returns or the prices takes its availability from its coordinator's `data_available` (`tolerance.py`), never from `CoordinatorEntity.available`: the last data stays on show through failed refreshes until `FAILURE_TOLERANCE` of them in a row, at least two regular intervals apart from first to last, confirm the failure, and a rejected key confirms it at once. A coordinator whose sensors show its data derives from `TolerantCoordinator` and implements `_async_fetch`; its sensors derive from `TolerantEntity`. The ticker and history coordinators apply the same rule to a single asset or timeframe. A refresh that fails as a whole counts for every one of them, so a value from before a confirmed outage never comes back after it. A price round stops as a whole once two requests in a row fail at the connection level before any fresh price arrived — never the first round, which has no last value to protect — so a hanging connection cannot stretch the tolerance with the number of tracked assets. This deliberately departs from Home Assistant's quality-scale rule `entity-unavailable` (the maintainer's decision, 2026-09-27): do not "fix" it back.

**Never log the API key.** No `exc_info=True` on API error logging — tracebacks can carry the key. `diagnostics.py` must keep it redacted.

**Do not block the event loop.** All I/O is `async`. Use the shared `aiohttp` session from `async_get_clientsession(hass)`.

**Cash Plus and fiat are never wallets.** The three Cash Plus products (group `fiat_earn`: BCPEUR, BCPUSD, BCPGBP) are cash equivalents, one unit per unit of their currency, so the Price Tracker leaves them out. The Portfolio shows them as its Cash Plus sensor, and fiat as its Cash sensor.

## Translations

The integration ships seven languages under `translations/`: English (`en`), German (`de`), French (`fr`), Dutch (`nl`), Italian (`it`), Spanish (`es`) and Polish (`pl`). Corrections by native speakers are welcome.

`strings.json` is the source of truth, and `translations/en.json` mirrors it exactly. **Changing a text means changing it in every translation file**: edit `strings.json`, copy it to `translations/en.json`, and change the same key in all six other files in the same pull request. A new key goes into all seven files too. If you cannot write one of the languages, say so in the pull request rather than leaving English in its file.

Which language a text is shown in depends on who writes it out:

- **Home Assistant's frontend**, in each user's profile language: dialogs and forms, attribute names, group subtitles, repair issues (`issues`: the upgrade details, what blocks the upgrade, the Price Tracker's slow interval), the reason setup is being retried (`exceptions`, from the error's key and placeholders), and the errors of a `bitpanda.refresh` call made in the UI — `exceptions.nothing_to_refresh` while no entry is loaded, raised with its key alone, and `exceptions.refresh_failed` when a refresh failed, its placeholder the titles of the entries concerned (the log and automation traces show their English text, and no entry's language option applies: the call belongs to no single entry). Never write such a text out in the backend; hand the frontend its key and placeholders, and keep the placeholders free of words — entity IDs, codes, numbers, asset labels, entry titles, marks such as ✓ and ✗, and Markdown only.
- **Home Assistant's backend**, in its system language: sensor names (`entity.sensor.*.name`).
- **This integration**, in the entry's own language option: group titles (`selector.asset_group`), the refusals to delete a device (`exceptions.*_not_removable`) and the Portfolio's notifications about a new wallet (`exceptions.wallet_added_title`, `exceptions.wallet_added`) and about staking payouts (`exceptions.staking_reward_title`, `exceptions.staking_reward`, `exceptions.staking_rewards`, `exceptions.staking_reward_value`), which Home Assistant shows as they arrive. The option is asked when a service is set up and changed under **Configure** on each service (`language` in the entry's options; English for an entry without it, one upgraded from version 1). Setup offers Home Assistant's system language first where a file ships for it (`language.preselected_language`), English otherwise; `language.entry_language(entry)` reads the option and `language.async_shipped_languages` lists the choices, one per file under `translations/`, each labelled with its own name (`selector.language`, identical in every file). Each setup step words the language section as its service's Configure does; the Price Tracker writes no refusals and no notifications, so its field names group titles alone. Never resolve one of these texts in `hass.config.language`.

What every language keeps exactly as English has it:

- Placeholders such as `{api_key_url}`, `{troubleshooting_url}`, `{old}`, `{new}`, `{asset}`, `{assets}`, `{group}`, `{wallet}`, `{link}`, `{currency}`, `{entities}`, `{path}`, `{status}`, `{services}`, `{entry}`, `{portfolio}`, `{minimum}`, `{version}`, `{count}`, `{minutes}`, `{balance}`, `{transaction}` and `{earn}` — each string uses the same ones as its English original. Never put an apostrophe directly before a placeholder (`l'{asset}`): the frontend reads it as the start of literal text.
- Markdown link targets (`[{api_key_url}]({api_key_url})`, `[Troubleshooting]({troubleshooting_url})` — the link text is the README's heading), product names (Bitpanda, Bitpanda Portfolio, Bitpanda Price Tracker, Cash Plus, Earn) and currency codes.

Bitpanda's permission names follow Bitpanda's key page in each language, in that language's quotation marks (`_PERMISSION_LABELS` in `tests/test_strings.py`, read on 2026-09-29): English "Balances", "Transaction", "Earn (Read)", "Trade (Read)"; German „Guthaben“, „Transaktion“, „Earn (Read)“, „Trading (Read)“; French « Soldes », « Transactions », « Earn (Lecture) », « Trader (Lecture) »; Dutch "Saldi", "Transactie", "Earn (Lezen)", "Traden (Lezen)"; Italian "Saldi", "Transazione", "Earn (Lettura)", "Trading (Lettura)"; Spanish "Créditos", "Transacción", "Earn (Lectura)", "Trading (Lectura)"; Polish „Salda”, „Transakcja”, „Earn (Odczytaj)”, „Trade (Odczytaj)”. A language Bitpanda's website does not offer — it offers Bulgarian, Croatian, Czech, Dutch, English, French, German, Hungarian, Italian, Polish, Portuguese, Romanian and Spanish — takes the English names in its own quotation marks. The missing-permissions error (`config.error.missing_scopes`) names all three the integration needs and puts `{balance}`, `{transaction}` and `{earn}` after them: the code fills in ✓ or ✗.

A text that sends the user to one of Home Assistant's menu items or buttons names it in quotation marks, exactly as Home Assistant's frontend labels it in that language — for example "Reconfigure" / „Neu konfigurieren“ / « Reconfigurer » / "Herconfigureer" / "Riconfigura" / "Reconfigurar" / „Rekonfiguracja”, "Configure" / „Konfigurieren“ / « Configurer » / "Configureren" / "Configura" / "Configurar" / „Konfiguruj” and "Delete" / „Löschen“ / « Supprimer » / "Verwijderen" / "Elimina" / "Eliminar" / „Usuń” (`ui.panel.config.integrations.config_entry.*`), and a dialog's "Submit" / „OK“ / « Valider » / "Verzenden" / "Invia" / "Enviar" / „Zatwierdź” (`ui.panel.config.integrations.config_flow.submit`). A text that sends the user to this integration's own "Add price tracker" quotes it exactly as the same file labels it (`config_subentries.price_group.initiate_flow.user`). Such a text also says where to find what it names, for users new to Home Assistant: on the Bitpanda integration page, at the entry by its name, in its ⋮ menu ("Reconfigure", "Delete", and deleting a device or a group on its own page) or with ⚙ ("Configure", a labelled button before 2025.7). Keep it short; a dialog's own button needs no directions.

The switch from a date version to 2.0.0 has a word of its own in each language, and every repair issue about it names it in its title: "upgrade", „Umstieg“ (umstellen), « migration » (migrer), "overstap" (omzetten), "migrazione" (migrare), "migración" (migrar), „migracja” (zmigrować) — never the word for an ordinary update, which also means any later 2.x version; "update Home Assistant" keeps it (`_SWITCH_WORDS`). German treats a wallet as neuter: „das Wallet“, plural „die Wallets“.

Every field of a dialog has a label (`data`) and a help text shown under it (`data_description`): what the field is for, what it needs, what changing it does. The two exceptions are the key in the Portfolio's setup and in the new-key dialog (`reauth_confirm`): each step's `description` walks through creating the key, and a key that lacks a permission gets the error that says so. A step's `description` keeps only what concerns the whole step. A field inside a section takes both from its section (`sections.<section>.data`, `.data_description`), and each section has a short `name`. A section's `description` holds what concerns all its fields: the Portfolio setup's notifications section says there, once, where to change the notification settings later, so its switch's help text is Configure's word for word. The Configure forms put every option in an open section of its own — the Price Tracker's currencies and language, the Portfolio's notifications and language — and so do the setups: the Price Tracker's currencies and language, the Portfolio's currency, notifications and language. The language comes last in every form. The options are still stored flat.

Group titles (`selector.asset_group`) must differ from one another within a language. A group still titled a shipped default is retitled to the entry's language at every setup; a group whose title is no longer any language's default counts as renamed by the user, so changing a title leaves groups created under the old one alone. Attribute labels (`entity.sensor.*.state_attributes`) carry a group prefix — `Asset:`, `Position:`, `Rewards:`, `24 h:`, `Conversion:` in English — because Home Assistant sorts them alphabetically from 2026.9 on: keep the prefix identical within a group so related labels stay together.

Write the files as UTF-8 without a BOM, formatted like the others (`json.dumps(..., indent=2, ensure_ascii=False)`).

These tests guard the files (`tests/test_strings.py` unless noted):

| Test | Checks |
|---|---|
| `test_the_shipped_languages` | exactly the seven files above |
| `test_string_files_have_no_bom`, `test_string_files_share_one_structure` | no BOM; every key of `strings.json` and no other in every file |
| `test_english_translation_is_the_strings_file` | `translations/en.json` equals `strings.json` |
| `test_every_string_has_the_placeholders_of_its_english_original` | the same placeholders as English |
| `test_no_apostrophe_directly_precedes_a_placeholder` | no `'{` |
| `test_every_link_keeps_its_english_target` | unchanged Markdown link targets |
| `test_no_string_contains_a_url` | no URL in any text — hassfest refuses one; a link target comes in as a placeholder the code fills in, such as `{api_key_url}` |
| `test_every_text_calls_the_key_an_api_key` | the key Bitpanda issues is the API key in every text, never just the key (`_BARE_KEY`, per language) |
| `test_no_language_is_an_untranslated_copy_of_english` | no sentence left in English, and most strings translated |
| `test_every_language_titles_each_group_differently` | distinct group titles |
| `test_every_shipped_language_is_offered_by_its_own_name` | the language option lists every shipped language by its own name, the same in every file (`_ENDONYMS`) |
| `test_each_service_has_options_texts_of_its_own` | Configure has one step per service (`options.step.price_tracker`, `options.step.portfolio`), with a label and a help text for each of its fields — the Price Tracker's in two named sections (`currencies`, `language`), the Portfolio's in two (`notifications`, then `language` under the same heading as the Price Tracker's) |
| `test_the_language_field_says_what_it_sets_for_each_service`, `test_the_price_tracker_names_its_language_by_its_own_field` | each service's language field names what it changes: the Price Tracker's group titles alone, the Portfolio's also its messages; both give the crypto group's own title as the example, and every Price Tracker text names the setting by the Price Tracker's label |
| `test_the_setup_names_the_language_as_configure_does`, `test_the_setup_words_the_currencies_as_configure_does` | each setup words its language section, and the Price Tracker's setup its currencies section, like its service's Configure form; the Portfolio's setup adds where to change the language later, Configure what removing a currency does |
| `test_both_portfolio_setup_steps_carry_the_service_name` | both Portfolio setup steps are titled "Bitpanda Portfolio" |
| `test_only_the_securities_search_names_the_isin` | "Add price tracker" names the ISIN only in the step of stocks, ETFs and ETCs (`security`), never in the other types' `asset` step |
| `test_every_field_has_a_help_text` | every labelled field of every dialog step and section (`data`) has its help text (`data_description`), except the key in the Portfolio's setup and in the new-key dialog (`_WITHOUT_HELP_TEXT`); the flow tests `test_every_field_of_every_form_has_a_label_and_a_help_text` (`tests/test_config_flow.py`, with the same exceptions) and `test_every_field_of_every_step_has_a_label_and_a_help_text` (`tests/test_asset_flow.py`) check that every field a form shows has both |
| `test_german_texts_quote_the_permission_names` | every German text that names the key's permissions quotes them: „Guthaben“, „Transaktion“, „Earn (Read)“, „Trading (Read)“ |
| `test_the_missing_permissions_error_marks_each_permission`, `test_no_language_but_german_names_a_permission_in_german` | every shipped language has its permission names (`_PERMISSION_LABELS`); the missing-permissions error names them with `{balance}`, `{transaction}` and `{earn}` after them; no language but German carries a German name |
| `test_menu_items_are_named_with_home_assistants_own_labels` | "Reconfigure", "Configure", "Delete" and the dialog's "Submit" named by Home Assistant's own label, quoted (`_MENU_LABELS`) |
| `test_texts_say_where_to_find_what_they_send_the_user_to` | every text that sends the user to a menu item names the Bitpanda integration page and the ⋮ or ⚙ to look for (`_INTEGRATION_PAGE`, `_LOCATED_TEXTS`) |
| `test_texts_name_the_add_price_tracker_button_by_its_own_label` | texts that send the user to "Add price tracker" quote the same file's label for it |
| `test_the_deletion_dialog_names_its_button_as_home_assistant_names_delete` | the not-migrated dialog's button is Home Assistant's own "Delete" label (`_MENU_LABELS`), and its text quotes it |
| `test_the_reauth_dialog_walks_through_creating_the_key_as_the_setup_does` | the new-key dialog repeats the setup's steps, its read-only line and its validity line word for word |
| `test_the_upgrade_issues_call_the_switch_by_its_own_word` | every repair issue about the upgrade and what blocks it names the switch in its title by its language's own word (`_SWITCH_WORDS`), and none calls it an update |
| `test_german_texts_say_das_wallet` | German texts treat a wallet as neuter: „das Wallet“ |
| `test_every_list_opens_a_paragraph_of_its_own` | every list — bullets or numbered steps — follows a blank line or another of its items |
| `test_every_published_attribute_has_a_translated_label` | every attribute a sensor publishes has a label |
| `test_each_kind_of_failed_request_has_a_text_of_its_own`, `test_every_failure_text_has_exactly_the_placeholders_the_code_fills_in` | each kind of failed request (`const.API_ERROR_KINDS`) has its own text in `exceptions`, with exactly the placeholders the code fills in — the request path and an HTTP status, never words |
| `test_no_exception_text_takes_an_english_message` | no `exceptions` text has an `{error}` placeholder: the API client's English message stays in the log |
| `test_every_issue_text_is_one_the_code_raises` | `issues` holds exactly the repair issues the code raises: the upgrade's (`migration.UPGRADE_ISSUES`), what blocks it (`migration.BLOCKER_ISSUES`) and the Price Tracker's slow interval (`price_coordinator.ISSUE_SLOW_PRICE_INTERVAL`) |
| `tests/test_migration.py::test_every_issue_text_renders_in_every_language`, `tests/test_migration.py::test_every_blocker_text_renders_in_every_language`, `tests/test_price_coordinator.py::test_the_issue_text_renders_in_every_language` | each of those issues, as the code raises it, has a title and a description — for the issue with a dialog, the dialog's — with exactly the placeholders the code supplies, in every language (`tests/conftest.py`'s `assert_issue_texts_render`) |
| `tests/test_groups.py::test_known_group_titles_are_read_from_every_shipped_language` | each language's group titles count as shipped defaults |

CI's hassfest run validates `strings.json` and `translations/en.json` as well.

To add a language, copy `translations/en.json` to `translations/<code>.json` and translate the values, following Home Assistant's own wording in that language for its UI (device, entity, integration, Configure, Submit, Notifications). The language option offers the new file at once; add the language's own name to `selector.language` in every file and to `_ENDONYMS` in `tests/test_strings.py` (hassfest accepts lowercase option keys only, so a code with a region, such as `pt-BR`, would first need the lowercase round trip `config_flow.py` gives the currency codes). Add the code to `test_the_shipped_languages`, its menu labels to `_MENU_LABELS`, its permission names to `_PERMISSION_LABELS` and its words for the upgrade and for an ordinary update to `_SWITCH_WORDS` in `tests/test_strings.py`, its entries to every other table there that a test checks with `sorted(<table>) == _LANGUAGES`, its group titles to `test_known_group_titles_are_read_from_every_shipped_language`, and the language to the list in the README. Keep option labels short; the currency names under `selector.currency` include their code in brackets.

## Code style

Follow the [Home Assistant developer guidelines](https://developers.home-assistant.io/docs/development_guidelines). In short:

- Complete type hints: `mypy --strict` must pass (see [Tests and typing](#tests-and-typing)).
- Docstrings on modules, classes and public functions.
- `async`/`await` for anything touching the network.
- Constants in `const.py`, not inline.

## Continuous integration

One workflow, **Validate** (`.github/workflows/validate.yml`), checks every change. The checks themselves live in three groups, each a workflow of its own, which a release runs as well: **Newest HA** (`.github/workflows/_validate_newest.yml`), **Minimum HA** (`_validate_minimum.yml`) and **Repository** (`_validate_repository.yml`). GitHub names each check after its group:

| Check | What it runs |
|---|---|
| Newest HA / Hassfest | Home Assistant's own checks of the integration (`hassfest`), as the Home Assistant release below |
| Newest HA / Tests | the suite on Python 3.14, as under [Tests and typing](#tests-and-typing); fails under 95 % line coverage |
| Newest HA / Strict typing | `python -m mypy --strict` on Python 3.14 |
| Minimum HA / Python 3.13 | a compile of the integration with Python 3.13, the Python of the 2025.5 floor, and a check that every module keeps `from __future__ import annotations` |
| Minimum HA / Tests | the suite on Python 3.13 against the minimum release in `hacs.json` (`tests/requirements-floor.txt`), after a check that the installed release is that one |
| Repository / HACS validation | HACS's checks of the repository |
| Repository / Release script | a compile of `.github/scripts/release.py` with Python 3.12 — the release runs it on the runner's own Python — and a stable release planned from the whole history |

**Which Home Assistant.** Hassfest, the tests and mypy check against one release: the newest stable Home Assistant that `pytest-homeassistant-custom-component` has been released for, never a beta. Each of the three jobs finds it first with `.github/scripts/ha_version.py` and names it in its log. So a new stable release reaches CI without a change in this repository, and it can turn a run red although nothing changed here: then the integration needs an update for that release, before the next release goes out. The tests also run against the minimum Home Assistant release in `hacs.json` (`tests/requirements-floor.txt`, no coverage gate): raise both together. That job can turn red without a change here as well: the dependencies of the minimum's packages are not all pinned. HACS validation depends on no Home Assistant release: it checks the repository against HACS's own rules.

When Validate runs:

- **A push to any branch but `main`** — all seven checks.
- **A pull request to `main` or `dev`** — all seven checks.
- **By hand** — all seven checks as well: Actions → Validate → Run workflow, on any branch.

Validate does not run on `main` itself: changes reach it only through a validated pull request, or as a release's version commit, validated just before. A newer push to the same branch, or a new commit in the same pull request, cancels the run it makes obsolete. A run started by hand and a push's run on the same branch cancel each other as well, whichever starts later cancelling the other: start one by hand only after the push's run has finished, or that run is cancelled and its Validation summary turns red.

One last check sums up each run: green when every check passed, red when one failed or the run was cancelled. A pull request to `main` calls it **Validation result**, the check `main` requires: a pull request to `main` merges only when it is green. Every other run — a pull request to `dev`, a push, a run by hand — calls it **Validation summary**: GitHub counts a required check by its name on a commit, so only the run that validates the merge into `main` may answer for it. A pull request to `dev` is merged once its Validation summary is green.

A pull request from a fork, to `dev` or to `main`, runs the same checks, with a read-only token and no secrets: Validate uses `pull_request`, never `pull_request_target`. A first-time contributor's run waits for the maintainer's approval. In your own fork, Validate works as it is: it needs no secrets.

## Commit messages

A release computes its version from the commit messages and writes its release notes from their subjects (see [Releases](#releases)), so a commit's type decides where the change shows up:

| Type | Release notes section |
|---|---|
| `feat` | ✨ New Features |
| `perf` | ⚡ Improvements |
| `fix` | 🐛 Bug Fixes |
| `refactor`, `style` | ♻️ Refactor & Code Quality |
| `docs` — user-facing documentation, the README | 📝 Documentation |
| `test`, `ci`, `build`, `chore` | not listed — unless breaking or scoped `security` (below) |

- **A change to CI, the tests or the release tooling alone is `ci:`, `test:`, `build:` or `chore:`** — also when it fixes or adds something there. **So is a change to the contributor documentation alone** — this file, the issue and pull request templates: `chore:`. `docs:` is for what the people who run the integration read, the README. The notes are for them: a `fix:` for a workflow would show up among their bug fixes, a `docs:` for this file among their documentation.
- A breaking change — a `!` after the type or the scope (`feat!:`, `fix(scope)!:`, `ci!:`), or a line that starts with `BREAKING CHANGE:` in the message body — makes the next version a major one on **any** type, `ci`, `test`, `build` and `chore` included, and is listed under 💥 Breaking Changes, and only there. So mark only what breaks an installation as breaking.
- The scope `security`, with any type — `chore` and `build` included — lists the change under 🔒 Security.
- Write the description for the people who run the integration, in the imperative: the notes print it with a capital first letter, the scope in bold before it — `fix(fx): require …` becomes "**fx:** Require …". Within a section, a description whose first word is `add` (or `adds`, `added`, `adding`) comes first, then everything else, then the forms of `fix`, then the forms of `remove`, `drop` and `delete`.

## Releases

The maintainer releases with the **Create Release** workflow (`.github/workflows/release.yml`); nobody bumps the version in `manifest.json` by hand. A release is one of two types, chosen under "Release type":

| | Stable (`stable`) | Pre-release (`prerelease`), a beta |
|---|---|---|
| Runs on | `main` | `dev` |
| Version and tag | `X.Y.Z`, tag `vX.Y.Z` | `X.Y.Z-beta.N`, tag `vX.Y.Z-beta.N` |
| Version commit | pushed to `main`, then tagged | only in its tag: `dev` stays as it is |
| GitHub release | published at once and marked latest — or a draft, when asked for | published at once, marked as a pre-release, never latest |
| HACS offers it | to everyone | only to installations that switched pre-releases on (see the README's [Beta versions](README.md#beta-versions)) |
| Release notes list | the changes since the previous stable release | the changes since the previous release of either type |

**Versions** follow [Semantic Versioning](https://semver.org). The next stable version is the last stable one plus a bump the commits since then call for (see [Commit messages](#commit-messages)): major when one of them is a breaking change, else minor when one is a `feat`, else patch. "Version bump" overrides that with major, minor or patch. A beta carries the stable version it leads to: after `2.0.0`, a `feat` on `dev` makes the betas `2.1.0-beta.1`, `2.1.0-beta.2`, and then the stable `2.1.0`. `manifest.json` gets the version without the `v`. A forced bump holds for its own run only — every run computes the version again. So force the same bump for every beta of a version and for its stable release: `major` for `3.0.0` and each of its betas. A later run on "auto" could plan `2.1.0`, which ranks below the `3.0.0` betas already out, so HACS offers it to none of their installations.

**From the date versions to 2.0.0.** The date versions (`2026.06.04` and older) are the 1.x line: until the first Semantic Versioning stable exists, the next version counts from `1.0.0`. That first one is the redesign, `2.0.0`: release it — and any beta of it — with "Version bump" set to major, which "auto" would count as `1.1.0`. Its tag, once, is `v2.0.0_redesign`: HACS cannot read that tag as a version and compares it with the installed one as text, so every installation on a date version sees the update, while a plain `2.0.0` ranks below `2026.06.04`. `manifest.json` says `2.0.0` and the release is titled `v2.0.0`; later tags are plain again. An installation that skips `2.0.0` and stays on a date version sees no later update either; the README tells its owner how to install the newest version once. A beta of `2.0.0` ranks below the date versions as well, so HACS offers it to nobody, pre-releases switched on or not: install it by hand, with Redownload → "Need a different version?".

**Release notes** are generated from the commit subjects (see [Commit messages](#commit-messages)), in sections in this order, empty ones left out: 💥 Breaking Changes, ✨ New Features, ⚡ Improvements, 🐛 Bug Fixes, 🔒 Security, ♻️ Refactor & Code Quality, 📝 Documentation. For notes written by hand — the redesign's `2.0.0` — tick "Create a stable release as a draft, to write its notes by hand": the draft carries the generated notes, to be replaced before it is published. A pre-release cannot be a draft: HACS does not see drafts. A draft's tag is pushed already, and it counts as released: it decides the next version, the notes' range and, for `2.0.0`, the one-time suffix. So to withdraw a draft, delete the draft **and its tag** before the next run. The version commit on `main` can stay: a next run with the same settings finds the version in `manifest.json` and commits nothing. With the tag kept, the next run stops with "Nothing to release"; once more was merged, it plans past the tag — for `2.0.0` a plain `v3.0.0` or `v2.0.1`, which no installation on a date version is offered.

To release: Actions → Create Release → Run workflow, on `main` for a stable release or on `dev` for a pre-release. Whenever something in the release path has changed since the last release — the workflow, the release script, the deploy key, `main`'s ruleset — tick "Dry run: validate, compute the version, tag and notes; push and publish nothing" first. The workflow

1. fails at once unless a stable release runs on `main`, and a pre-release on `dev` and not as a draft ("Check branch and type");
2. runs the complete validation: every check under [Continuous integration](#continuous-integration), in the same three groups ("Newest HA", "Minimum HA", "Repository");
3. computes the version, its tag and the release notes with `.github/scripts/release.py`, sets the version in `manifest.json`, stops unless the file then carries exactly that version, and commits it as `github-actions[bot]` (`chore: bump version to <version>`), on top of exactly the commit it validated ("Set version and tag");
4. pushes with the deploy key whose private key is the secret `RELEASE_DEPLOY_KEY`: a stable release pushes the commit to `main` — the one direct push `main`'s ruleset lets through — and then the tag; a pre-release pushes only the tag, which takes the commit along. The job that holds the key runs no third-party action, only `actions/checkout`, shell and the release script: a tampered action could read the key;
5. creates the GitHub release, titled `v<version>`, with the generated notes, in a job of its own that gets neither a checkout nor the key ("Publish release").

A dry run goes through steps 1–3, the commit staying in the runner: it shows the version, the tag, the previous release, the version commit and the notes, checks that the deploy key reaches the repository (when the secret is set), and stops — it pushes, tags and publishes nothing. It cannot tell whether the key may push past `main`'s ruleset; only a real release shows that.

When a release fails:

- **`main` refuses the push** (step 4): either `main` moved while the release ran — a pull request merged meanwhile, a state that was never validated — or the deploy key cannot push to `main`: it lacks write access, or it is missing from the ruleset's bypass list. Nothing is tagged or published. Fix the key or the ruleset if that was the cause, then start a **new** run (Actions → Create Release → Run workflow). "Re-run jobs" would repeat the failed run on its original commit, which `main` refuses again once it has moved. A new run right after a stable release finds nothing to release and stops at its plan (the last case below).
- **The secret `RELEASE_DEPLOY_KEY` is missing**: the release stops with an error before it commits anything.
- **The tag's push fails after `main` took the commit**: start a new run on `main` with the same settings — not "Re-run jobs", whose commit `main` now refuses. The new run computes the same version, finds it in `manifest.json` already and commits nothing, then tags and publishes.
- **Publishing fails after the tag was pushed** (step 5): the tag exists, without a release. Use **Re-run failed jobs**: only "Publish release" runs again, with the same tag, title and notes, because GitHub reuses the outputs of the jobs that succeeded. Never use **Re-run all jobs**, and do not start a new run: both stop at their plan with "Nothing to release" (below), and then only a release by hand is left; once more was merged, a new run releases the next version instead, and this tag stays without a release. If "Publish release" fails again, create the release from the tag by hand (Releases → Draft a new release → choose the tag), titled `v<version>`, marked as a pre-release for a beta, with the notes the "Set version and tag" job printed in its log.
- **The plan stops with "Nothing to release"** (step 3), before anything is committed: no commit came after the previous release — the same release was started a second time, "Re-run all jobs" came after its tag was pushed, or a new run came right after a stable release. If the previous release is published, there is nothing to do; if its tag has no GitHub release yet, create the release from the tag by hand, as under "Publishing fails" — or, for a draft you withdrew, delete the tag.

After a stable release, merge `main` into `dev`, so the version commit reaches `dev` too: `git switch dev`, `git pull`, `git merge origin/main`, `git push`. A pre-release leaves nothing to merge.

## After merging

- A change on `dev` reaches `main` with the next pull request from `dev`.
- Installations get it with the next release: a beta from `dev` brings it to those that switched pre-releases on (see the README's [Beta versions](README.md#beta-versions)), a stable release to everyone.

## License

Contributions are licensed under the repository's [MIT License](LICENSE).
