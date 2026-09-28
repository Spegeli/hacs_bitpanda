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

### Tests and typing

Tests use `pytest-homeassistant-custom-component`, whose harness does not run on Windows. `tests/requirements.txt` pins it — and with it the Home Assistant release the suite runs against, which needs Python 3.14 — and mypy. Install mypy from that file too, never with a bare `pip install mypy`: another mypy release can report errors CI does not, or miss ones it does. The tests and mypy need Python 3.14; the integration itself must still run on 3.13 (see [Things that are easy to get wrong](#things-that-are-easy-to-get-wrong)). On Linux or macOS, with Python 3.14:

```bash
pip install -r tests/requirements.txt
python -m pytest tests/ -q --cov=custom_components.bitpanda --cov-report=term-missing --cov-fail-under=95
python -m mypy --strict
```

`pytest` runs the suite and reports the line coverage of each file, and fails under 95 % overall, as CI does; `mypy` checks the types of the integration in strict mode, as `pyproject.toml` configures it — the tests are not type-checked.

The same in Docker, on any system, with the Python version and the pinned requirements CI uses; each run installs them afresh, which takes a few minutes. On Windows, run it from PowerShell: Git Bash rewrites the mount path.

```bash
docker run --rm -v "${PWD}:/workspace" -w /workspace python:3.14 sh -c "pip install -q -r tests/requirements.txt && python -m pytest tests/ -q --cov=custom_components.bitpanda --cov-report=term-missing --cov-fail-under=95 && python -m mypy --strict"
```

CI runs both (see [Continuous integration](#continuous-integration)): the suite must pass with at least 95 % line coverage, and `mypy --strict` must report no error. `config_flow.py` and `asset_flow.py` stay at 100 %, and every test that shows an error in a dialog goes on to finish that dialog.

## Project layout

Everything lives in `custom_components/bitpanda/`:

| File | Responsibility |
|---|---|
| `__init__.py` | Setup and unload per service, deleting devices from their device page, the `bitpanda.refresh` service (registered once, in `async_setup`) |
| `api.py` | `BitpandaApiClient` — all HTTP calls; keyless for public endpoints |
| `assets.py` | Asset categories (`asset_category`), legacy symbol resolution (`pick_legacy`), `AssetDirectory` for holding metadata, list labels |
| `asset_flow.py` | The "Add price tracker" subentry flow and the cached catalogue listings |
| `config_flow.py` | Service menu, Portfolio setup/reauth/reconfigure, Price Tracker setup, the options (Configure) of both services, import |
| `const.py` | Domain, URLs, scopes, currencies, intervals, budgets |
| `devices.py` | Device lookups scoped to their config entry |
| `diagnostics.py` | Diagnostics per service, API key redacted |
| `ecb.py` | ECB daily reference rates |
| `groups.py` | Groups by asset type (config subentries): titles, lookups, the Price Tracker's tracked assets, the Portfolio's wallet groups |
| `icons.json` | Every sensor's icon, by its translation key, and the `bitpanda.refresh` service's icon — never set an icon in code |
| `language.py` | The language of the integration's own texts: each entry's language option, the shipped languages |
| `migration.py` | Migration of version 1 (legacy API) entries to version 3; tells the user what changed, and what keeps an entry from being upgraded, as repair issues |
| `naming.py` | Labels, device names, entity IDs, unique_ids, device identifiers |
| `portfolio_coordinator.py` | Portfolio, History, Earn and Rewards coordinators |
| `portfolio_model.py` | Pure data model: holdings, value split, Cash Plus, Earn, rewards |
| `portfolio_sensor.py` | Portfolio sensors and the wallet lifecycle manager, which also keeps the wallet groups |
| `price_coordinator.py` | Keyless ticker coordinator with its request budget, and the repair issue while that stretches its interval past 30 minutes; ECB coordinator |
| `price_sensor.py` | Price sensors per asset and currency |
| `purge.py` | Deletes the Portfolio's sensors with their history and long-term statistics on a currency change |
| `sensor.py` | Dispatches the sensor platform to the service |
| `streaks.py` | The rule for things in a row — failed refreshes, empty answers, missing holdings — confirmed by count and time |
| `strings.json`, `translations/` | UI strings, seven languages (see [Translations](#translations)) |
| `tolerance.py` | `TolerantCoordinator` and `TolerantEntity`: sensors keep their last data through short outages |

The Portfolio polls `/portfolio` and `/portfolio-history` every 5 minutes, `/operations` every hour and `/earn/configs` every 24 hours, all with the key. The Price Tracker polls `/tickers` without a key — every 60 seconds, stretched above 30 assets to stay within 1,800 requests per hour — and the ECB every 6 hours when extra currencies are configured. Add new reads to an existing coordinator rather than polling from a sensor.

The wallet lifecycle manager (`PortfolioEntityManager`) runs after every portfolio refresh. It adds and removes the wallet devices and keeps them in wallet groups, config subentries it creates and removes itself; a group the user deletes comes back with the next refresh while its assets are still held. So the Portfolio's update listener reloads the entry only when `entry.data` or `entry.options` changed since setup — subentry changes never reload it. The Price Tracker reloads on every change, subentries included: its groups are what it tracks.

## Things that are easy to get wrong

**Every ticker price string carries exactly 8 decimals.** `90.93000000` for a stock, `0.00000032` for a micro-cap. Display precision is derived from the price's magnitude (`price_sensor.py`'s `display_precision`), never by counting the string's digits.

**`/portfolio` has no staked field.** Staked units are `balance − available_balance`, and the cent-rounded `currency_balance` of the whole position is split in that proportion (`portfolio_model.py`). A missing `currency_balance` is no value, never 0.

**Entity IDs are set explicitly.** Every entity sets its own `entity_id` from `naming.py`, in English: `sensor.bitpanda_`, the slug of its device's name — English too, "Vision (VSN) Wallet", "Bitcoin (BTC) Price Tracker" — and the sensor's own ending. Never let one derive from a translated name.

**Every value sensor keeps long-term statistics.** Money values set `state_class` `total` — the only state class Home Assistant allows for the monetary device class — and the returns `measurement`; a new sensor needs one too. Statistics are recorded in the sensor's unit, so a sensor whose currency can change must have its statistics cleared with its history: the currency purge (`purge.py`) does that for every Portfolio sensor, and `tests/test_currency_change.py` checks it with a real recorder.

**Home Assistant 2025.5 is the floor** (`hacs.json`), and only APIs that exist there may be used. It is set by the recorder: only from 2025.5 on does it move an entity's history along with an entity-ID rename made while Home Assistant starts, which is when the version 1 migration renames. The device registry's per-entry lookups (`async_get_device_by_identifier` and its siblings) do not exist at the floor, and `async_get_device` is deprecated — find a device through `devices.find_entry_device`. Home Assistant 2025.5 runs on Python 3.13, so the integration must run on 3.13 too, although the tests and mypy need 3.14: use no syntax and no standard-library API newer than 3.13 (such as `except A, B:` without parentheses), and keep `from __future__ import annotations` at the top of every module. 3.13 evaluates annotations as it defines a class or function, so without that line a name defined further down the module — the `PortfolioConfigEntry` a coordinator's `config_entry` is annotated with — fails the import there, while 3.14 evaluates them only when asked. CI compiles the integration with Python 3.13 and checks that every module keeps `from __future__ import annotations`; the rest is for review.

**A device never moves between groups.** A wallet stays in the wallet group it sits in, even when Bitpanda files its asset under another type later: moving a device to another config subentry lists it in both on Home Assistant 2025.5, 2026.9 warns about it and 2027.8 will refuse it. What a group holds is read from the entity registry (`groups.entities_by_group`), never from the device registry's `config_entries_subentries`, a deprecated compatibility property from 2026.9 on.

**`/operations` cursors need milliseconds.** The server ignores a cursor whose timestamp has no fractional seconds and silently answers with page 1 — yet emits such cursors itself. `api.py` rewrites them (`normalize_operations_cursor`), and `_paginate` raises rather than return a partial listing when a cursor repeats. Never loosen that into "return what we have": a partial history publishes wrong lifetime totals as fact.

**A symbol is not an id.** The 14,000-asset catalogue lets one symbol name several assets — `XAU` is both Gold (a tokenized metal) and GoldMoney Inc (a stock). Always resolve to, cache and compare by asset id, never the bare symbol.

**Each authenticated endpoint needs one specific scope.** `/portfolio` needs Guthaben (Balance), `/operations` needs Transaktion (Transaction), `/earn/configs` needs Earn (Read). `/currencies`, `/assets` and `/tickers` are public endpoints that answer regardless of scope, so calling them successfully proves nothing about what a key can do.

**Sensors ride out short outages.** A sensor of the Portfolio, its returns or the prices takes its availability from its coordinator's `data_available` (`tolerance.py`), never from `CoordinatorEntity.available`: the last data stays on show through failed refreshes until `FAILURE_TOLERANCE` of them in a row, at least two regular intervals apart from first to last, confirm the failure, and a rejected key confirms it at once. A coordinator whose sensors show its data derives from `TolerantCoordinator` and implements `_async_fetch`; its sensors derive from `TolerantEntity`. The ticker and history coordinators apply the same rule to a single asset or timeframe. A refresh that fails as a whole counts for every one of them, so a value from before a confirmed outage never comes back after it. A price round stops as a whole once two requests in a row fail at the connection level before any fresh price arrived — never the first round, which has no last value to protect — so a hanging connection cannot stretch the tolerance with the number of tracked assets. This deliberately departs from Home Assistant's quality-scale rule `entity-unavailable` (the maintainer's decision, 2026-09-27): do not "fix" it back.

**Never log the API key.** No `exc_info=True` on API error logging — tracebacks can carry the key. `diagnostics.py` must keep it redacted.

**Do not block the event loop.** All I/O is `async`. Use the shared `aiohttp` session from `async_get_clientsession(hass)`.

## Translations

The integration ships seven languages under `translations/`: English (`en`), German (`de`), French (`fr`), Dutch (`nl`), Italian (`it`), Spanish (`es`) and Polish (`pl`). Corrections by native speakers are welcome.

`strings.json` is the source of truth, and `translations/en.json` mirrors it exactly. **Changing a text means changing it in every translation file**: edit `strings.json`, copy it to `translations/en.json`, and change the same key in all six other files in the same pull request. A new key goes into all seven files too. If you cannot write one of the languages, say so in the pull request rather than leaving English in its file.

Which language a text is shown in depends on who writes it out:

- **Home Assistant's frontend**, in each user's profile language: dialogs and forms, attribute names, group subtitles, repair issues (`issues`: the upgrade details, what blocks the upgrade, the Price Tracker's slow interval), the reason setup is being retried (`exceptions`, from the error's key and placeholders), and the errors of a `bitpanda.refresh` call made in the UI — `exceptions.nothing_to_refresh` while no entry is loaded, raised with its key alone, and `exceptions.refresh_failed` when a refresh failed, its placeholder the titles of the entries concerned (the log and automation traces show their English text, and no entry's language option applies: the call belongs to no single entry). Never write such a text out in the backend; hand the frontend its key and placeholders, and keep the placeholders free of words — entity IDs, codes, numbers, asset labels, entry titles and Markdown only.
- **Home Assistant's backend**, in its system language: sensor names (`entity.sensor.*.name`).
- **This integration**, in the entry's own language option: group titles (`selector.asset_group`) and the refusals to delete a device (`exceptions.*_not_removable`), which Home Assistant shows as they arrive. The option is asked when a service is set up and changed under **Configure** on each service (`language` in the entry's options; English for an entry without it, one upgraded from version 1). Setup offers Home Assistant's system language first where a file ships for it (`language.preselected_language`), English otherwise; `language.entry_language(entry)` reads the option and `language.async_shipped_languages` lists the choices, one per file under `translations/`, each labelled with its own name (`selector.language`, identical in every file). Each setup step words the language section as its service's Configure does; the Price Tracker writes no refusals, so its field names group titles alone. Never resolve one of these texts in `hass.config.language`.

What every language keeps exactly as English has it:

- Placeholders such as `{api_key_url}`, `{old}`, `{new}`, `{asset}`, `{assets}`, `{group}`, `{currency}`, `{entities}`, `{path}`, `{status}`, `{services}`, `{entry}`, `{portfolio}`, `{minimum}`, `{version}`, `{count}` and `{minutes}` — each string uses the same ones as its English original. Never put an apostrophe directly before a placeholder (`l'{asset}`): the frontend reads it as the start of literal text.
- Markdown link targets (`[{api_key_url}]({api_key_url})`), product names (Bitpanda, Bitpanda Portfolio, Bitpanda Price Tracker, Cash Plus, Earn) and currency codes.
- Bitpanda's permission names, `Guthaben (Balance)`, `Transaktion (Transaction)` and `Earn (Read)`, as Bitpanda's key page shows them (German uses the German names alone).

A text that sends the user to one of Home Assistant's menu items or buttons names it in quotation marks, exactly as Home Assistant's frontend labels it in that language — for example "Reconfigure" / „Neu konfigurieren“ / « Reconfigurer » / "Herconfigureer" / "Riconfigura" / "Reconfigurar" / „Rekonfiguracja”, "Configure" / „Konfigurieren“ / « Configurer » / "Configureren" / "Configura" / "Configurar" / „Konfiguruj” and "Delete" / „Löschen“ / « Supprimer » / "Verwijderen" / "Elimina" / "Eliminar" / „Usuń” (`ui.panel.config.integrations.config_entry.*`), and a dialog's "Submit" / „OK“ / « Valider » / "Verzenden" / "Invia" / "Enviar" / „Zatwierdź” (`ui.panel.config.integrations.config_flow.submit`). A text that sends the user to this integration's own "Add price tracker" quotes it exactly as the same file labels it (`config_subentries.price_group.initiate_flow.user`). Such a text also says where to find what it names, for users new to Home Assistant: on the Bitpanda integration page, at the entry by its name, in its ⋮ menu ("Reconfigure", "Delete", and deleting a device or a group on its own page) or with ⚙ ("Configure", a labelled button at the 2025.5 floor). Keep it short; a dialog's own button needs no directions.

Every field of a dialog has a label (`data`) and a help text shown under it (`data_description`): what the field is for, what it needs, what changing it does. A step's `description` keeps only what concerns the whole step. A field inside a section takes both from its section (`sections.<section>.data`, `.data_description`), and each section has a short `name`. The Configure forms put every option in an open section of its own — the Price Tracker's currencies and language, the Portfolio's language — and so do the setups: the Price Tracker's currencies and language, the Portfolio's currency and language. The options are still stored flat.

Group titles (`selector.asset_group`) must differ from one another within a language. A group still titled a shipped default is retitled to the entry's language at every setup; a group whose title is no longer any language's default counts as renamed by the user, so changing a title leaves groups created under the old one alone. Attribute labels (`entity.sensor.*.state_attributes`) carry a group prefix — `Asset:`, `Position:`, `Rewards:`, `24 h:`, `Conversion:` in English — because newer Home Assistant versions sort them alphabetically: keep the prefix identical within a group so related labels stay together.

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
| `test_every_shipped_language_is_offered_by_its_own_name` | the language option lists every shipped language by its own name, the same in every file (`_ENDONYMS`) |
| `test_each_service_has_options_texts_of_its_own` | Configure has one step per service (`options.step.price_tracker`, `options.step.portfolio`), with a label and a help text for each of its fields — the Price Tracker's in two named sections (`currencies`, `language`), the Portfolio's in one (`language`, under the same heading as the Price Tracker's) |
| `test_the_language_field_says_what_it_sets_for_each_service`, `test_the_price_tracker_names_its_language_by_its_own_field` | each service's language field names what it changes: the Price Tracker's group titles alone, the Portfolio's also its messages; both give the crypto group's own title as the example, and every Price Tracker text names the setting by the Price Tracker's label |
| `test_the_setup_names_the_language_as_configure_does`, `test_the_setup_words_the_currencies_as_configure_does` | each setup words its language section, and the Price Tracker's setup its currencies section, like its service's Configure form; the Portfolio's setup adds where to change the language later, Configure what removing a currency does |
| `test_both_portfolio_setup_steps_carry_the_service_name` | both Portfolio setup steps are titled "Bitpanda Portfolio" |
| `test_only_the_securities_search_names_the_isin` | "Add price tracker" names the ISIN only in the step of stocks, ETFs and ETCs (`security`), never in the other types' `asset` step |
| `test_every_field_has_a_help_text` | every labelled field of every dialog step and section (`data`) has its help text (`data_description`); the flow tests `test_every_field_of_every_form_has_a_label_and_a_help_text` (`tests/test_config_flow.py`) and `test_every_field_of_every_step_has_a_label_and_a_help_text` (`tests/test_asset_flow.py`) check that every field a form shows has both |
| `test_menu_items_are_named_with_home_assistants_own_labels` | "Reconfigure", "Configure", "Delete" and the dialog's "Submit" named by Home Assistant's own label, quoted (`_MENU_LABELS`) |
| `test_texts_say_where_to_find_what_they_send_the_user_to` | every text that sends the user to a menu item names the Bitpanda integration page and the ⋮ or ⚙ to look for (`_INTEGRATION_PAGE`, `_LOCATED_TEXTS`) |
| `test_texts_name_the_add_price_tracker_button_by_its_own_label` | texts that send the user to "Add price tracker" quote the same file's label for it |
| `test_every_published_attribute_has_a_translated_label` | every attribute a sensor publishes has a label |
| `test_each_kind_of_failed_request_has_a_text_of_its_own`, `test_every_failure_text_has_exactly_the_placeholders_the_code_fills_in` | each kind of failed request (`const.API_ERROR_KINDS`) has its own text in `exceptions`, with exactly the placeholders the code fills in — the request path and an HTTP status, never words |
| `test_no_exception_text_takes_an_english_message` | no `exceptions` text has an `{error}` placeholder: the API client's English message stays in the log |
| `test_every_issue_text_is_one_the_code_raises` | `issues` holds exactly the repair issues the code raises: the upgrade's (`migration.UPGRADE_ISSUES`), what blocks it (`migration.BLOCKER_ISSUES`) and the Price Tracker's slow interval (`price_coordinator.ISSUE_SLOW_PRICE_INTERVAL`) |
| `tests/test_migration.py::test_every_issue_text_renders_in_every_language`, `tests/test_migration.py::test_every_blocker_text_renders_in_every_language`, `tests/test_price_coordinator.py::test_the_issue_text_renders_in_every_language` | each of those issues, as the code raises it, has a title and a description with exactly the placeholders the code supplies, in every language (`tests/conftest.py`'s `assert_issue_texts_render`) |
| `tests/test_groups.py::test_known_group_titles_are_read_from_every_shipped_language` | each language's group titles count as shipped defaults |

CI's hassfest run validates `strings.json` and `translations/en.json` as well.

To add a language, copy `translations/en.json` to `translations/<code>.json` and translate the values, following Home Assistant's own wording in that language for its UI (device, entity, integration, Configure, Submit). The language option offers the new file at once; add the language's own name to `selector.language` in every file and to `_ENDONYMS` in `tests/test_strings.py` (hassfest accepts lowercase option keys only, so a code with a region, such as `pt-BR`, would first need the lowercase round trip `config_flow.py` gives the currency codes). Add the code to `test_the_shipped_languages`, its menu labels to `_MENU_LABELS` in `tests/test_strings.py`, its group titles to `test_known_group_titles_are_read_from_every_shipped_language`, and the language to the list in the README. Keep option labels short; the currency names under `selector.currency` include their code in brackets.

## Code style

Follow the [Home Assistant developer guidelines](https://developers.home-assistant.io/docs/development_guidelines). In short:

- Complete type hints: `mypy --strict` must pass (see [Tests and typing](#tests-and-typing)).
- Docstrings on modules, classes and public functions.
- `async`/`await` for anything touching the network.
- Constants in `const.py`, not inline.

## Branches

- **`main`** holds the released code. It changes only through the pull request from `dev` and through a release's version commit, and it merges only with a green **Validation result** (see [Continuous integration](#continuous-integration)).
- **`dev`** is where work comes together; betas are released from it.
- **Topic branches** start from `dev` and go back into it.

## Pull requests

1. Branch from `dev`.
2. Keep the change focused — one topic per PR.
3. Write the commit messages as [Conventional Commits](https://www.conventionalcommits.org) — see [Commit messages](#commit-messages).
4. Open the PR against `dev` and fill in the template.
5. Validate runs for pull requests to `main` only, so run the tests and mypy yourself first (see [Tests and typing](#tests-and-typing)). The maintainer validates your pull request by pushing it to a topic branch of this repository, which runs every check.

**Do not bump the version in `manifest.json`.** The Create Release workflow sets it (see [Releases](#releases)).

### Commit messages

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

## Continuous integration

One workflow, **Validate** (`.github/workflows/validate.yml`), checks every change. The checks themselves live in `.github/workflows/_validate.yml`, which a release runs as well:

| Check | What it runs |
|---|---|
| Hassfest validation | Home Assistant's own checks of the integration (`hassfest`) |
| HACS validation | HACS's checks of the repository |
| Python 3.13 syntax | a compile of the integration with Python 3.13, the Python of the 2025.5 floor, and a check that every module keeps `from __future__ import annotations` |
| Release script on Python 3.12 | a compile of `.github/scripts/release.py` with Python 3.12 — the release runs it on the runner's own Python — and a stable release planned from the whole history |
| Tests with coverage | the suite on Python 3.14, as under [Tests and typing](#tests-and-typing); fails under 95 % line coverage |
| Strict typing | `python -m mypy --strict` on Python 3.14 |

When Validate runs:

- **A push to any branch but `main`** — all six checks.
- **A pull request to `main`** — all six checks.
- **By hand** — Actions → Validate → Run workflow, on any branch. Clear "Also run the tests with coverage and mypy --strict" to skip those two; the other four always run.

Validate does not run on `main` itself: changes reach it only through a validated pull request, or as a release's version commit, validated just before. A newer push to the same branch, or a new commit in the same pull request, cancels the run it makes obsolete. A run started by hand and a push's run on the same branch cancel each other as well, whichever starts later cancelling the other: start one by hand only after the push's run has finished, or that run is cancelled and its Validation summary turns red.

One last check sums up each run: green when every check passed or was switched off by hand, red when one failed or the run was cancelled. A pull request's run calls it **Validation result**. It is the one check `main` requires, so a pull request merges only with a green Validation result. Push and manual runs call it **Validation summary**: GitHub would count a push's run on the pull request's head commit for the required check as well, and only the pull request's own run, which validates the merge result, may answer for it. A run started by hand never counts for a pull request anyway, so switching its tests off cannot stand in for the required check.

A pull request to `main` from a fork runs the same checks, with a read-only token and no secrets: Validate uses `pull_request`, never `pull_request_target`. A first-time contributor's run waits for the maintainer's approval.

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

**Release notes** are generated from the commit subjects (see [Commit messages](#commit-messages)), in sections in this order, empty ones left out: 💥 Breaking Changes, ✨ New Features, ⚡ Improvements, 🐛 Bug Fixes, 🔒 Security, ♻️ Refactor & Code Quality, 📝 Documentation. For notes written by hand — the redesign's `2.0.0` — tick "Create a stable release as a draft, to write its notes by hand": the draft carries the generated notes, to be replaced before it is published. A pre-release cannot be a draft: HACS does not see drafts. A draft's tag is pushed already, and it counts as released: it decides the next version, the notes' range and, for `2.0.0`, the one-time suffix. So to withdraw a draft, delete the draft **and its tag** before the next run. The version commit on `main` can stay: a next run with the same settings finds the version in `manifest.json` and commits nothing. With the tag kept, the next run plans past it — for `2.0.0` a plain `v3.0.0` or `v2.0.1`, which no installation on a date version is offered.

To release: Actions → Create Release → Run workflow, on `main` for a stable release or on `dev` for a pre-release. Whenever something in the release path has changed since the last release — the workflow, the release script, the deploy key, `main`'s ruleset — tick "Dry run: validate, compute the version, tag and notes; push and publish nothing" first. The workflow

1. fails at once unless a stable release runs on `main`, and a pre-release on `dev` and not as a draft ("Check branch");
2. runs the complete validation: every check under [Continuous integration](#continuous-integration), the tests included — a release cannot switch them off ("Validate");
3. computes the version, its tag and the release notes with `.github/scripts/release.py`, sets the version in `manifest.json`, stops unless the file then carries exactly that version, and commits it as `github-actions[bot]` (`chore: bump version to <version>`), on top of exactly the commit it validated ("Commit version and tag");
4. pushes with the deploy key whose private key is the secret `RELEASE_DEPLOY_KEY`: a stable release pushes the commit to `main` — the one direct push `main`'s ruleset lets through — and then the tag; a pre-release pushes only the tag, which takes the commit along. The job that holds the key runs no third-party action, only `actions/checkout`, shell and the release script: a tampered action could read the key;
5. creates the GitHub release, titled `v<version>`, with the generated notes, in a job of its own that gets neither a checkout nor the key ("Publish release").

A dry run goes through steps 1–3, the commit staying in the runner: it shows the version, the tag, the previous release, the version commit and the notes, checks that the deploy key reaches the repository (when the secret is set), and stops — it pushes, tags and publishes nothing. It cannot tell whether the key may push past `main`'s ruleset; only a real release shows that.

When a release fails:

- **`main` refuses the push** (step 4): either `main` moved while the release ran — a pull request merged meanwhile, a state that was never validated — or the deploy key cannot push to `main`: it lacks write access, or it is missing from the ruleset's bypass list. Nothing is tagged or published. Fix the key or the ruleset if that was the cause, then start a **new** run (Actions → Create Release → Run workflow). "Re-run jobs" would repeat the failed run on its original commit, which `main` refuses again once it has moved. One exception: if the refused run was a "Re-run all jobs" of a release whose tag was already pushed (the last case below), do not start a new run — it would release the next version. Create the release for that tag by hand instead.
- **The secret `RELEASE_DEPLOY_KEY` is missing**: the release stops with an error before it commits anything.
- **The tag's push fails after `main` took the commit**: start a new run on `main` with the same settings — not "Re-run jobs", whose commit `main` now refuses. The new run computes the same version, finds it in `manifest.json` already and commits nothing, then tags and publishes.
- **Publishing fails after the tag was pushed** (step 5): the tag exists, without a release. Use **Re-run failed jobs**: only "Publish release" runs again, with the same tag, title and notes, because GitHub reuses the outputs of the jobs that succeeded. Never use **Re-run all jobs**, and do not start a new run: either plans past the pushed tag and releases the next version, leaving this tag without a release. If "Publish release" fails again, create the release from the tag by hand (Releases → Draft a new release → choose the tag), titled `v<version>`, marked as a pre-release for a beta, with the notes the "Commit version and tag" job printed in its log.

After a stable release, merge `main` into `dev`, so the version commit reaches `dev` too: `git switch dev`, `git pull`, `git merge origin/main`, `git push`. A pre-release leaves nothing to merge.
