# Contributing

Thanks for your interest in improving this integration. This is a small personal project, so the process is deliberately light.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- **Report a bug** — [open a bug report](https://github.com/Spegeli/hacs_bitpanda/issues/new?template=bug_report.yml). Concrete numbers and diagnostics help most.
- **Suggest a feature** — [open a feature request](https://github.com/Spegeli/hacs_bitpanda/issues/new?template=feature_request.yml).
- **Improve translations** — new languages are welcome, see below.
- **Submit code** — see the workflow below.

## What cannot be added

Stocks, ETFs and commodities are **not** supported and cannot be made to work. The public Bitpanda Price Ticker API returns no prices for them, so there is nothing to read. The config flow deliberately skips the `security` and `equity_security` categories.

## Development setup

No build step and no dependencies beyond Home Assistant itself.

1. Fork and clone the repository.
2. Copy `custom_components/bitpanda/` into your Home Assistant `config/custom_components/` directory — or symlink it, so edits apply without copying again.
3. Restart Home Assistant.
4. Add the integration: **Settings → Devices & Services → Add Integration → Bitpanda**.

You need a Bitpanda API key with the read-only **Balance** scope ([create one](https://web.bitpanda.com/apikey)).

To see what the integration is doing, enable debug logging in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.bitpanda: debug
```

## Project layout

Everything lives in `custom_components/bitpanda/`:

| File | Responsibility |
|---|---|
| `__init__.py` | Setup/unload, the two coordinators, the `bitpanda.refresh` service |
| `api.py` | `BitpandaApiClient` — all HTTP calls |
| `sensor.py` | Price, wallet and portfolio sensors |
| `config_flow.py` | Setup flow and options flow |
| `const.py` | Domain, API URL, update intervals, categories |
| `diagnostics.py` | Config entry diagnostics |
| `strings.json`, `translations/` | UI strings |

Two `DataUpdateCoordinator` instances handle polling: prices every 60 seconds, wallets every 5 minutes. Add new API reads to an existing coordinator rather than polling from a sensor.

## Things that are easy to get wrong

**Wallet balance units differ by category.** This caused a real bug ([#7](https://github.com/Spegeli/hacs_bitpanda/issues/7)):

- **Crypto and metal wallets** — `balance` is the coin/token amount, so the value is `balance × price`.
- **Fiat and index wallets** — `balance` is *already* in the account currency. Return it as-is. Multiplying by the price inflates the value by several orders of magnitude.

The guard is `category == "fiat" or category.startswith("index")` and it appears in three places in `sensor.py`. If you touch one, check all three.

**Never log the API key.** No `exc_info=True` on API error logging — tracebacks can carry the key. `diagnostics.py` must keep it redacted.

**Do not block the event loop.** All I/O is `async`. Use the shared `aiohttp` session from `async_get_clientsession(hass)`.

## Translations

`strings.json` is the source of truth. `translations/en.json` must mirror it exactly, and every other language file must have the same key structure.

To add a language, copy `translations/en.json` to `translations/<code>.json` and translate the values. Keep the emoji prefixes in the options menu (`📈`, `🪙`, `💶`, `🪨`, `📊`, `💾`) so the menu stays visually consistent.

## Code style

Follow the [Home Assistant developer guidelines](https://developers.home-assistant.io/docs/development_guidelines). In short:

- Type hints on function signatures.
- Docstrings on modules, classes and public functions.
- `async`/`await` for anything touching the network.
- Constants in `const.py`, not inline.

## Pull requests

1. Branch from `main`. There is no `dev` branch.
2. Keep the change focused — one topic per PR.
3. Use [Conventional Commits](https://www.conventionalcommits.org) for commit messages: `fix:`, `feat:`, `docs:`, `chore:`, `refactor:`, `ci:`.
4. Open the PR against `main` and fill in the template.
5. CI runs hassfest and HACS validation. Both must pass.

**Do not bump the version in `manifest.json`.** The maintainer sets it when cutting a release.

## Releases

Releases are made by the maintainer. Version format is `YYYY.MM.DD`, tagged `vYYYY.MM.DD`. The version in `manifest.json` is bumped on `main`, then a tag and GitHub release with a changelog are created.
