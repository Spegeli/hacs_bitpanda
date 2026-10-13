## Description

<!-- What does this PR change, and why? -->

## Related issue

<!-- e.g. Fixes #7 — or "none" -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Improvement (performance)
- [ ] Security
- [ ] Documentation
- [ ] Refactor / code quality
- [ ] CI / repository
- [ ] Breaking change — existing installations must act after updating

## How was this tested?

<!--
Which service (Portfolio, Price Tracker) or card, and which Home Assistant
version? For a card, which browser or app? Which assets or wallet types, and
in which currency?
Wallet value bugs are easy to miss — state the numbers you verified.
-->

## Checklist

- [ ] Opened against `dev`, not `main` (CONTRIBUTING → Pull requests)
- [ ] Tested on a real Home Assistant instance, if the change affects the running integration
- [ ] Tests and `mypy --strict` pass locally, unless the change is documentation only (see CONTRIBUTING → Tests and typing)
- [ ] If the cards' build changed — `cards/src`, `build.mjs`, `tsconfig.json` or `package-lock.json`: `npm ci`, `npm run typecheck`, `npm test` and `npm run build` pass in `cards/` (Node 24), and the rebuilt `custom_components/bitpanda/frontend/bitpanda-cards.js` is committed with it (CONTRIBUTING → Dashboard cards)
- [ ] Uses only Home Assistant APIs that exist in 2025.5, the supported floor (CONTRIBUTING → Things that are easy to get wrong)
- [ ] Commit messages follow Conventional Commits — the release notes are built from them (CONTRIBUTING → Commit messages: CI, tests, templates or CONTRIBUTING alone are `ci:`, `test:` or `chore:`; `docs:` is for the README)
- [ ] Translations updated and in sync, if UI strings changed: `strings.json` and all seven `translations/*.json` (`en`, `de`, `fr`, `nl`, `it`, `es`, `pl`); for a card text, all seven `cards/src/translations/*.ts`
- [ ] No API key or other secret is logged, committed or included in diagnostics
- [ ] README updated, if user-facing behavior changed

<!--
A pull request to dev or main is validated by CI: hassfest, HACS validation,
the tests (≥ 95 % coverage, and on the minimum Home Assistant), mypy --strict,
the Python 3.13 checks, the release script on Python 3.12 and the dashboard
cards (type check, tests ≥ 95 % coverage, build, committed bundle). A pull request
to dev merges once that run is green; one to main merges only with a green
"Validation result".
Do NOT bump the version in manifest.json — the release workflow sets it.
-->
