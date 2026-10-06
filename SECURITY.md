# Security policy

## Reporting a vulnerability

Please report a vulnerability privately, never in a public issue, discussion or pull request:

1. Open [Report a vulnerability](https://github.com/Spegeli/hacs_bitpanda/security/advisories/new) — or the **Security** tab → **Report a vulnerability**.
2. Describe the problem, how to reproduce it and what an attacker could do with it. Name the version of the integration and of Home Assistant.

Never put a real API key into a report. If your key has leaked, delete it in your Bitpanda account and create a new one.

Only you and the maintainer see the report. This is a personal project, maintained in spare time: you get an answer as soon as possible, but there is no fixed response time. The advisory is published together with the release that fixes the vulnerability, and you are credited unless you ask not to be.

Not sure whether it is a vulnerability? Report it privately anyway.

## Scope

In scope is the code in this repository, in particular:

- how the integration stores and uses your Bitpanda API key, and that it keeps the key out of logs, diagnostics and error messages
- the requests to Bitpanda and to the European Central Bank
- the workflows that check and publish releases

Vulnerabilities in Bitpanda's own services, in Home Assistant or in HACS are out of scope: report them to Bitpanda, to [Home Assistant](https://www.home-assistant.io/security/) or to the HACS project.

## Supported versions

Only the latest release receives security fixes. Update through HACS.

| Version | Security fixes |
|---|---|
| Latest release | ✅ |
| Older releases, including the date versions (2026.06.04 or older) | ❌ |
