# Contributing

Thanks for your interest in improving this integration. This is a small personal project, so the process is deliberately light.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- **Report a bug** — [open a bug report](https://github.com/Spegeli/hacs_bitpanda/issues/new?template=bug_report.yml). Concrete numbers and diagnostics help most.
- **Suggest a feature** — [open a feature request](https://github.com/Spegeli/hacs_bitpanda/issues/new?template=feature_request.yml).
- **Improve translations** — corrections and new languages are welcome, see below.
- **Submit code** — see the workflow below.

## What cannot be added

The Price Tracker covers crypto, stocks, ETFs, ETCs, Bitpanda Crypto Indices and tokenized precious metals — 14,051 assets across six catalogue categories. The three Cash Plus products (`fiat_earn` group) are left out of it: they are cash equivalents, one unit per unit of their currency. The Portfolio shows them as its Cash Plus sensor, and fiat as its Cash sensor — neither is a wallet.

## Development setup

No build step and no dependencies beyond Home Assistant itself.

1. Fork and clone the repository.
2. Copy `custom_components/bitpanda/` into your Home Assistant `config/custom_components/` directory — or symlink it, so edits apply without copying again.
3. Restart Home Assistant.
4. Add the integration: **Settings → Devices & Services → Add Integration → Bitpanda**.

The Portfolio needs a Bitpanda API key with all three required read scopes — **Guthaben (Balance)**, **Transaktion (Transaction)** and **Earn (Read)** ([create one](https://app.bitpanda.com/my-account/apikey)). The Price Tracker needs none.

To see what the integration is doing, enable debug logging in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.bitpanda: debug
```

Tests use `pytest-homeassistant-custom-component`, whose harness does not run on Windows. On Linux or macOS:

```bash
pip install -r requirements_test.txt
pytest tests/ -q
```

## Project layout

Everything lives in `custom_components/bitpanda/`:

| File | Responsibility |
|---|---|
| `__init__.py` | Setup and unload per service, deleting devices from their device page, the `bitpanda.refresh` service |
| `api.py` | `BitpandaApiClient` — all HTTP calls; keyless for public endpoints |
| `assets.py` | Asset categories (`asset_category`), legacy symbol resolution (`pick_legacy`), `AssetDirectory` for holding metadata, list labels |
| `asset_flow.py` | The "Add price tracker" subentry flow and the cached catalogue listings |
| `config_flow.py` | Service menu, Portfolio setup/reauth/reconfigure, Price Tracker setup and options, import |
| `const.py` | Domain, URLs, scopes, currencies, intervals, budgets |
| `devices.py` | Device lookups scoped to their config entry |
| `diagnostics.py` | Diagnostics per service, API key redacted |
| `ecb.py` | ECB daily reference rates |
| `groups.py` | Groups by asset type (config subentries): titles, lookups, the Price Tracker's tracked assets, the Portfolio's wallet groups |
| `migration.py` | Migration of version 1 (legacy API) entries to version 3 |
| `naming.py` | Labels, entity IDs, unique_ids, device identifiers |
| `portfolio_coordinator.py` | Portfolio, History, Earn and Rewards coordinators |
| `portfolio_model.py` | Pure data model: holdings, value split, Cash Plus, Earn, rewards |
| `portfolio_sensor.py` | Portfolio sensors and the wallet lifecycle manager, which also keeps the wallet groups |
| `price_coordinator.py` | Keyless ticker coordinator with its request budget, ECB coordinator |
| `price_sensor.py` | Price sensors per asset and currency |
| `purge.py` | Deletes the Portfolio's sensors with their history on a currency change |
| `sensor.py` | Dispatches the sensor platform to the service |
| `strings.json`, `translations/` | UI strings, seven languages (see [Translations](#translations)) |

The Portfolio polls `/portfolio` and `/portfolio-history` every 5 minutes, `/operations` every hour and `/earn/configs` every 24 hours, all with the key. The Price Tracker polls `/tickers` without a key — every 60 seconds, stretched above 30 assets to stay within 1,800 requests per hour — and the ECB every 6 hours when extra currencies are configured. Add new reads to an existing coordinator rather than polling from a sensor.

The wallet lifecycle manager (`PortfolioEntityManager`) runs after every portfolio refresh. It adds and removes the wallet devices and keeps them in wallet groups, config subentries it creates and removes itself; a group the user deletes comes back with the next refresh while its assets are still held. So the Portfolio's update listener reloads the entry only when `entry.data` or `entry.options` changed since setup — subentry changes never reload it. The Price Tracker reloads on every change, subentries included: its groups are what it tracks.

## Things that are easy to get wrong

**Every ticker price string carries exactly 8 decimals.** `90.93000000` for a stock, `0.00000032` for a micro-cap. Display precision is derived from the price's magnitude (`price_sensor.py`'s `display_precision`), never by counting the string's digits.

**`/portfolio` has no staked field.** Staked units are `balance − available_balance`, and the cent-rounded `currency_balance` of the whole position is split in that proportion (`portfolio_model.py`). A missing `currency_balance` is no value, never 0.

**Entity IDs are set explicitly.** Every entity sets its own `entity_id` from `naming.py`, in English. Never let one derive from a translated name.

**Home Assistant 2025.5 is the floor** (`hacs.json`), and only APIs that exist there may be used. It is set by the recorder: only from 2025.5 on does it move an entity's history along with an entity-ID rename made while Home Assistant starts, which is when the version 1 migration renames. The device registry's per-entry lookups (`async_get_device_by_identifier` and its siblings) do not exist at the floor, and `async_get_device` is deprecated — find a device through `devices.find_entry_device`.

**A device never moves between groups.** A wallet stays in the wallet group it sits in, even when Bitpanda files its asset under another type later: moving a device to another config subentry lists it in both on Home Assistant 2025.5, 2026.9 warns about it and 2027.8 will refuse it. What a group holds is read from the entity registry (`groups.entities_by_group`), never from the device registry's `config_entries_subentries`, a deprecated compatibility property from 2026.9 on.

**`/operations` cursors need milliseconds.** The server ignores a cursor whose timestamp has no fractional seconds and silently answers with page 1 — yet emits such cursors itself. `api.py` rewrites them (`normalize_operations_cursor`), and `_paginate` raises rather than return a partial listing when a cursor repeats. Never loosen that into "return what we have": a partial history publishes wrong lifetime totals as fact.

**A symbol is not an id.** The 14,000-asset catalogue lets one symbol name several assets — `XAU` is both Gold (a tokenized metal) and GoldMoney Inc (a stock). Always resolve to, cache and compare by asset id, never the bare symbol.

**Each authenticated endpoint needs one specific scope.** `/portfolio` needs Guthaben (Balance), `/operations` needs Transaktion (Transaction), `/earn/configs` needs Earn (Read). `/currencies`, `/assets` and `/tickers` are public endpoints that answer regardless of scope, so calling them successfully proves nothing about what a key can do.

**Never log the API key.** No `exc_info=True` on API error logging — tracebacks can carry the key. `diagnostics.py` must keep it redacted.

**Do not block the event loop.** All I/O is `async`. Use the shared `aiohttp` session from `async_get_clientsession(hass)`.

## Translations

The integration ships seven languages under `translations/`: English (`en`), German (`de`), French (`fr`), Dutch (`nl`), Italian (`it`), Spanish (`es`) and Polish (`pl`). Corrections by native speakers are welcome.

`strings.json` is the source of truth, and `translations/en.json` mirrors it exactly. **Changing a text means changing it in every translation file**: edit `strings.json`, copy it to `translations/en.json`, and change the same key in all six other files in the same pull request. A new key goes into all seven files too. If you cannot write one of the languages, say so in the pull request rather than leaving English in its file.

What every language keeps exactly as English has it:

- Placeholders such as `{api_key_url}`, `{old}`, `{new}`, `{asset}`, `{group}` and `{error}` — each string uses the same ones as its English original. Never put an apostrophe directly before a placeholder (`l'{asset}`): the frontend reads it as the start of literal text.
- Markdown link targets (`[{api_key_url}]({api_key_url})`), product names (Bitpanda, Bitpanda Portfolio, Bitpanda Price Tracker, Cash Plus, Earn) and currency codes.
- Bitpanda's permission names, `Guthaben (Balance)`, `Transaktion (Transaction)` and `Earn (Read)`, as Bitpanda's key page shows them (German uses the German names alone).

A text that sends the user to one of Home Assistant's menu items or buttons names it in quotation marks, exactly as Home Assistant's frontend labels it in that language — for example "Reconfigure" / „Neu konfigurieren“ / « Reconfigurer » / "Herconfigureer" / "Riconfigura" / "Reconfigurar" / „Rekonfiguracja” and "Configure" / „Konfigurieren“ / « Configurer » / "Configureren" / "Configura" / "Configurar" / „Konfiguruj” (`ui.panel.config.integrations.config_entry.*`), and a dialog's "Submit" / „OK“ / « Valider » / "Verzenden" / "Invia" / "Enviar" / „Zatwierdź” (`ui.panel.config.integrations.config_flow.submit`).

Group titles (`selector.asset_group`) must differ from one another within a language. A group still titled a shipped default is retitled to Home Assistant's language at every start; a group whose title is no longer any language's default counts as renamed by the user, so changing a title leaves groups created under the old one alone. Attribute labels (`entity.sensor.*.state_attributes`) carry a group prefix — `Asset:`, `Balance:`, `Rewards:`, `24 h:`, `Conversion:` in English — because Home Assistant sorts them alphabetically: keep the prefix identical within a group so related labels stay together.

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
| `test_no_language_is_an_untranslated_copy_of_english` | no sentence left in English, and most strings translated |
| `test_every_language_titles_each_group_differently` | distinct group titles |
| `test_menu_items_are_named_with_home_assistants_own_labels` | "Reconfigure", "Configure" and the dialog's "Submit" named by Home Assistant's own label, quoted (`_MENU_LABELS`) |
| `test_every_published_attribute_has_a_translated_label` | every attribute a sensor publishes has a label |
| `tests/test_migration.py::test_every_text_of_the_migration_has_a_template` | every text of the upgrade notification has a template |
| `tests/test_migration.py::test_every_text_of_the_migration_renders_in_every_language` | each of those templates has exactly the placeholders the code fills, in every language |
| `tests/test_groups.py::test_known_group_titles_are_read_from_every_shipped_language` | each language's group titles count as shipped defaults |

CI's hassfest run validates `strings.json` and `translations/en.json` as well.

To add a language, copy `translations/en.json` to `translations/<code>.json` and translate the values, following Home Assistant's own wording in that language for its UI (device, entity, integration, Configure, Submit). Add the code to `test_the_shipped_languages`, its menu labels to `_MENU_LABELS` in `tests/test_strings.py`, its group titles to `test_known_group_titles_are_read_from_every_shipped_language`, and the language to the list in the README. Keep option labels short; the currency names under `selector.currency` include their code in brackets.

## Code style

Follow the [Home Assistant developer guidelines](https://developers.home-assistant.io/docs/development_guidelines). In short:

- Type hints on function signatures.
- Docstrings on modules, classes and public functions.
- `async`/`await` for anything touching the network.
- Constants in `const.py`, not inline.

## Pull requests

1. Branch from `main`.
2. Keep the change focused — one topic per PR.
3. Use [Conventional Commits](https://www.conventionalcommits.org) for commit messages: `fix:`, `feat:`, `docs:`, `chore:`, `refactor:`, `ci:`.
4. Open the PR against `main` and fill in the template.
5. CI runs hassfest and HACS validation. Both must pass.

**Do not bump the version in `manifest.json`.** The maintainer sets it when cutting a release.

## Releases

Releases are made by the maintainer. Version format is `YYYY.MM.DD`, tagged `vYYYY.MM.DD`. The version in `manifest.json` is bumped on `main`, then a tag and GitHub release with a changelog are created.
