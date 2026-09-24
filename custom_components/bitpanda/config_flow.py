"""Config flow for the Bitpanda integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig
import homeassistant.helpers.config_validation as cv

from .api import (
    BitpandaApiClient,
    BitpandaApiError,
    BitpandaAuthError,
    BitpandaRateLimitError,
)
from .assets import AssetResolver, category_of
from .const import (
    API_KEY_URL,
    CONF_API_KEY,
    CONF_ASSET_CACHE,
    CONF_CURRENCY,
    CONF_CURRENCY_ID,
    CONF_TRACKED_ASSETS,
    CONF_TRACKED_WALLETS,
    DEFAULT_CURRENCY,
    DOMAIN,
    REQUIRED_SCOPES,
    SCOPE_LABELS,
)

_LOGGER = logging.getLogger(__name__)


class BitpandaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 2

    def __init__(self) -> None:
        self._api_key: str | None = None
        self._currencies: list[dict] = []

    async def _async_validate_key(
        self, api_key: str
    ) -> tuple[dict[str, str], dict[str, str]]:
        """Probe every required scope. Returns (errors, placeholders)."""
        client = BitpandaApiClient(api_key, async_get_clientsession(self.hass))
        try:
            missing = await client.async_missing_scopes()
        except BitpandaRateLimitError:
            return {"base": "rate_limited"}, {}
        except BitpandaApiError:
            return {"base": "cannot_connect"}, {}
        if len(missing) == len(REQUIRED_SCOPES):
            return {"base": "invalid_auth"}, {}
        if missing:
            return {"base": "missing_scopes"}, {
                "missing_scopes": ", ".join(SCOPE_LABELS[s] for s in missing)
            }
        return {}, {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY].strip()
            try:
                errors, placeholders = await self._async_validate_key(self._api_key)
                if not errors:
                    client = BitpandaApiClient(
                        self._api_key, async_get_clientsession(self.hass)
                    )
                    self._currencies = await client.async_get_currencies()
                    return await self.async_step_currency()
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): cv.string}),
            errors=errors,
            description_placeholders={"api_key_url": API_KEY_URL, **placeholders},
        )

    async def async_step_currency(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        by_symbol = {c["symbol"]: c for c in self._currencies}

        if user_input is not None:
            symbol = user_input[CONF_CURRENCY]
            return self.async_create_entry(
                title=f"Bitpanda ({symbol})",
                data={
                    CONF_API_KEY: self._api_key,
                    CONF_CURRENCY: symbol,
                    CONF_CURRENCY_ID: by_symbol[symbol]["id"],
                },
                options={
                    CONF_TRACKED_ASSETS: [],
                    CONF_TRACKED_WALLETS: [],
                    CONF_ASSET_CACHE: {},
                },
            )

        options = [
            {"value": c["symbol"], "label": f"{c['name']} ({c['symbol']})"}
            for c in sorted(self._currencies, key=lambda c: c["symbol"])
        ]
        return self.async_show_form(
            step_id="currency",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CURRENCY, default=DEFAULT_CURRENCY): (
                        SelectSelector(
                            SelectSelectorConfig(options=options, mode="dropdown")
                        )
                    )
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> config_entries.OptionsFlow:
        return BitpandaOptionsFlowHandler()


class BitpandaOptionsFlowHandler(config_entries.OptionsFlow):
    """Add and remove tracked assets and wallets.

    `config_entry` is a read-only property on `OptionsFlow` in this Home
    Assistant version (it resolves the entry from `self.handler` via
    `hass.config_entries`, set by the flow manager after construction).
    Assigning to it in `__init__`, as older integrations do, raises
    `AttributeError` here because the base class defines no setter — so
    this handler never stores the entry itself and only ever reads
    `self.config_entry`.
    """

    def __init__(self) -> None:
        self._assets: list[str] | None = None
        self._wallets: list[str] | None = None
        self._cache: dict[str, dict] | None = None

    def _load(self) -> None:
        if self._assets is None:
            options = self.config_entry.options
            self._assets = list(options.get(CONF_TRACKED_ASSETS, []))
            self._wallets = list(options.get(CONF_TRACKED_WALLETS, []))
            self._cache = dict(options.get(CONF_ASSET_CACHE, {}))

    def _resolver(self) -> AssetResolver:
        client = BitpandaApiClient(
            self.config_entry.data[CONF_API_KEY],
            async_get_clientsession(self.hass),
        )
        return AssetResolver(client, self._cache)

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        self._load()
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_asset", "add_wallet", "remove", "save"],
        )

    async def _async_add(self, step_id: str, target: list[str], user_input):
        """Resolve a typed symbol and add its asset id to `target`.

        `AssetResolver.async_resolve` deliberately re-raises
        `BitpandaAuthError` and `BitpandaRateLimitError` instead of folding
        them into "no such symbol" — a revoked key or a 429 is a different
        problem than a typo, and letting either escape unhandled here would
        show the user Home Assistant's generic error page instead of a
        message they can act on. Both are mapped to a form error, the same
        way the setup step handles them.
        """
        self._load()
        errors: dict[str, str] = {}

        if user_input is not None:
            symbol = user_input["symbol"].strip().upper()
            resolver = self._resolver()
            try:
                asset = await resolver.async_resolve(symbol)
            except BitpandaAuthError:
                errors["base"] = "invalid_auth"
            except BitpandaRateLimitError:
                errors["base"] = "rate_limited"
            else:
                if asset is None:
                    errors["symbol"] = "unknown_symbol"
                else:
                    self._cache = resolver.as_dict()
                    if asset["id"] not in target:
                        target.append(asset["id"])
                    return await self.async_step_init()

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({vol.Required("symbol"): cv.string}),
            errors=errors,
        )

    async def async_step_add_asset(self, user_input=None) -> ConfigFlowResult:
        self._load()
        return await self._async_add("add_asset", self._assets, user_input)

    async def async_step_add_wallet(self, user_input=None) -> ConfigFlowResult:
        self._load()
        return await self._async_add("add_wallet", self._wallets, user_input)

    async def async_step_remove(self, user_input=None) -> ConfigFlowResult:
        self._load()
        by_id = {a["id"]: a for a in self._cache.values() if a.get("id")}

        if user_input is not None:
            keep_assets = set(user_input.get(CONF_TRACKED_ASSETS, []))
            keep_wallets = set(user_input.get(CONF_TRACKED_WALLETS, []))
            self._assets = [a for a in self._assets if a in keep_assets]
            self._wallets = [w for w in self._wallets if w in keep_wallets]
            return await self.async_step_init()

        def _options(ids: list[str]) -> list[dict]:
            # Every tracked id becomes an option, even one with no cache
            # entry (the resolved record can predate this cache, or have
            # been lost some other way) — falling back to the raw id as the
            # label. Otherwise an uncached id would have no corresponding
            # option, `SelectSelector` would reject it as an invalid
            # default/value, and the user would have no way to remove it.
            return [
                {
                    "value": i,
                    "label": (
                        f"{by_id.get(i, {}).get('symbol', i)} "
                        f"({category_of(by_id.get(i, {}))})"
                    ),
                }
                for i in ids
            ]

        return self.async_show_form(
            step_id="remove",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TRACKED_ASSETS, default=self._assets
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=_options(self._assets),
                            multiple=True,
                            mode="list",
                        )
                    ),
                    vol.Optional(
                        CONF_TRACKED_WALLETS, default=self._wallets
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=_options(self._wallets),
                            multiple=True,
                            mode="list",
                        )
                    ),
                }
            ),
        )

    async def async_step_save(self, user_input=None) -> ConfigFlowResult:
        self._load()
        return self.async_create_entry(
            title="",
            data={
                CONF_TRACKED_ASSETS: self._assets,
                CONF_TRACKED_WALLETS: self._wallets,
                CONF_ASSET_CACHE: self._cache,
            },
        )
