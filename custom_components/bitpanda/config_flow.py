"""Config flow for the Bitpanda integration."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util import dt as dt_util
import homeassistant.helpers.config_validation as cv

from .api import (
    BitpandaApiClient,
    BitpandaApiError,
    BitpandaAuthError,
    BitpandaRateLimitError,
)
from .assets import AssetResolver, asset_label
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
from .coordinator import parse_portfolio

_LOGGER = logging.getLogger(__name__)

# Every category filter below was verified live on 2026-09-24, first page
# type and group checked. Together they cover 14,051 of 14,054 catalogue
# assets -- the three left out are security/fiat_earn (Cash Plus, priced at
# roughly one unit of its own currency and pointless to track). Stocks exist
# in two families -- equity_security/equity_stock and security/stock, often
# the same company twice -- and both are genuine, priced listings, so a
# category can list more than one filter and all of them are merged.
ASSET_CATEGORY_FILTERS: dict[str, list[tuple[str, str | None]]] = {
    "crypto": [("cryptocoin", None)],
    "stock": [("equity_security", "equity_stock"), ("security", "stock")],
    "etf": [
        ("equity_security", "equity_etf"),
        ("equity_security", "equity_complex_etf"),
        ("security", "etf"),
    ],
    "etc": [("equity_security", "equity_complex_etc"), ("security", "etc")],
    "index": [("index", None)],
    "metal": [("commodity", "metal")],
}

# 14000 assets makes even one uncached category listing a meaningful slice of
# the hourly read budget (~103 requests for stocks alone) -- see
# BitpandaOptionsFlowHandler._async_category_listing.
_CATALOGUE_CACHE_TTL = timedelta(hours=24)

# All the options flow reads from a catalogue record: the picker label
# (name, symbol, ISIN) and what the sensors and the cache need later. The
# rest of a full record -- trading flags -- would only cost memory, several
# megabytes across the stock and ETF listings.
_CATALOGUE_FIELDS = ("id", "symbol", "name", "isin", "type", "group")


def _slim(asset: dict) -> dict:
    """A catalogue record reduced to _CATALOGUE_FIELDS."""
    return {key: asset[key] for key in _CATALOGUE_FIELDS if key in asset}


def _log_unexpected(step: str, err: Exception) -> None:
    """Log an unexpected error by its type alone.

    Its message or a traceback could carry request data, the API key among
    it, so neither is ever logged -- no exc_info either.
    """
    _LOGGER.error(
        "Unexpected %s while checking the API key in the %s step",
        type(err).__name__,
        step,
    )


def _multiselect_schema(field: str, options: list[dict]) -> vol.Schema:
    """A searchable multi-select, never pre-filled, always submittable empty.

    `mode=SelectSelectorMode.DROPDOWN` (not `"list"`, which the frontend
    renders as one unsearchable checkbox per option -- the wrong branch of
    `ha-selector-select` runs first for `"list"`) is what makes this a
    "type to search" picker, for every category including the 4-item
    metals.

    `vol.Optional(field, default=[])`, not `vol.Required`, is what lets the
    frontend seed an empty selection instead of a pre-ticked first option,
    and what lets an empty submission -- the escape hatch every "nothing to
    add" and every error re-render relies on -- validate at all.
    """
    return vol.Schema(
        {
            vol.Optional(field, default=[]): SelectSelector(
                SelectSelectorConfig(
                    options=options,
                    multiple=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )


def _api_error_code(err: BitpandaApiError) -> str:
    """Map a caught API exception to its `options.error` translation key.

    Every network call in the options flow funnels its failure through this,
    so a plain 5xx/timeout/undecodable body (`BitpandaApiError` on its own)
    gets a form error instead of escaping the step -- which Home Assistant's
    flow manager does not catch, closing the whole dialog and discarding the
    session when the escape happens from a menu-triggered step.
    """
    if isinstance(err, BitpandaAuthError):
        return "invalid_auth"
    if isinstance(err, BitpandaRateLimitError):
        return "rate_limited"
    return "cannot_connect"


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
            except Exception as err:  # noqa: BLE001 - a form error, never a traceback
                _log_unexpected("user", err)
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

    def _async_replace_key(
        self, entry: ConfigEntry, api_key: str, reason: str
    ) -> ConfigFlowResult:
        """Store a new key and get it into effect with exactly one reload.

        An entry that finished setup has an update listener that reloads it on
        any change; Home Assistant wants that listener to do the reloading and
        warns — breaking in 2026.12 — when async_update_reload_and_abort reloads
        a second time. An entry whose setup failed, the typical reauth case of a
        key rejected on the first portfolio refresh, never registered the
        listener, so there the explicit reload is the only one.
        async_update_and_abort would express the first branch directly but does
        not exist in the 2025.1 floor.
        """
        if entry.update_listeners:
            self.hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_API_KEY: api_key}
            )
            return self.async_abort(reason=reason)
        return self.async_update_reload_and_abort(
            entry, data_updates={CONF_API_KEY: api_key}, reason=reason
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"api_key_url": API_KEY_URL}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            try:
                errors, extra = await self._async_validate_key(api_key)
            except Exception as err:  # noqa: BLE001 - a form error, never a traceback
                _log_unexpected("reauth", err)
                errors, extra = {"base": "unknown"}, {}
            placeholders.update(extra)
            if not errors:
                return self._async_replace_key(
                    self._get_reauth_entry(), api_key, "reauth_successful"
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): cv.string}),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Replace the stored key. The currency is fixed once set.

        Changing it would change every sensor's unit and break long-term
        statistics, and the currency step already tells the user it cannot be
        changed after setup.
        """
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"api_key_url": API_KEY_URL}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            try:
                errors, extra = await self._async_validate_key(api_key)
            except Exception as err:  # noqa: BLE001 - a form error, never a traceback
                _log_unexpected("reconfigure", err)
                errors, extra = {"base": "unknown"}, {}
            placeholders.update(extra)
            if not errors:
                return self._async_replace_key(
                    self._get_reconfigure_entry(), api_key, "reconfigure_successful"
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): cv.string}),
            errors=errors,
            description_placeholders=placeholders,
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
        self._category: str | None = None

    def _load(self) -> None:
        if self._assets is None:
            options = self.config_entry.options
            self._assets = list(options.get(CONF_TRACKED_ASSETS, []))
            self._wallets = list(options.get(CONF_TRACKED_WALLETS, []))
            self._cache = dict(options.get(CONF_ASSET_CACHE, {}))

    def _client(self) -> BitpandaApiClient:
        return BitpandaApiClient(
            self.config_entry.data[CONF_API_KEY],
            async_get_clientsession(self.hass),
        )

    def _resolver(self) -> AssetResolver:
        return AssetResolver(self._client(), self._cache)

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        self._load()
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_asset", "add_wallet", "remove", "save"],
        )

    async def _async_category_listing(
        self, client: BitpandaApiClient, category: str
    ) -> list[dict]:
        """Every asset in one category, all pages, cached for 24 hours.

        Cached under the domain's OWN top-level `hass.data` key, never inside
        `hass.data[DOMAIN]`: `__init__.py`'s refresh service iterates
        `hass.data[DOMAIN].values()` expecting only per-entry stores, and its
        unload handler treats an empty `hass.data[DOMAIN]` as "last entry
        gone" -- a catalogue value under that key would break both. A
        separate key also survives entry reloads and serves every entry, so
        a category already fetched once for any entry is free for all.

        Nothing here catches an API error: an error partway through a
        multi-filter category (stocks merges two listings) must not cache a
        partial result, and every one is already mapped to a form error one
        level up, in `_try_category_listing`.

        Records are stored slimmed to _CATALOGUE_FIELDS, and every listing
        past its TTL is dropped on each call -- not only refreshed if its own
        category happens to be opened again -- so the cache holds at most a
        day's worth of what was actually browsed.
        """
        store: dict[str, tuple] = self.hass.data.setdefault(
            f"{DOMAIN}_asset_catalogue", {}
        )
        now = dt_util.utcnow()
        for expired in [
            key
            for key, (fetched_at, _) in store.items()
            if now - fetched_at >= _CATALOGUE_CACHE_TTL
        ]:
            del store[expired]

        cached = store.get(category)
        if cached is not None:
            return cached[1]

        assets: list[dict] = []
        seen_ids: set[str] = set()
        for type_, group in ASSET_CATEGORY_FILTERS[category]:
            for asset in await client.async_list_assets(type_, group):
                asset_id = asset.get("id")
                if asset_id and asset_id not in seen_ids:
                    seen_ids.add(asset_id)
                    assets.append(_slim(asset))

        store[category] = (now, assets)
        return assets

    async def async_step_asset_category(self, user_input=None) -> ConfigFlowResult:
        """Which kind of asset to track -- crypto, stock, etf, etc, index or
        metal. `translation_key` labels the bare option values below via
        `selector.asset_category.options.<value>` in the translation files.
        """
        if user_input is not None:
            self._category = user_input["category"]
            return await self.async_step_add_asset()

        return self.async_show_form(
            step_id="asset_category",
            data_schema=vol.Schema(
                {
                    vol.Required("category"): SelectSelector(
                        SelectSelectorConfig(
                            options=list(ASSET_CATEGORY_FILTERS),
                            translation_key="asset_category",
                        )
                    )
                }
            ),
        )

    async def async_step_add_asset(self, user_input=None) -> ConfigFlowResult:
        """Multi-select of one category's assets, minus those already tracked.

        Reached from the menu (`next_step_id == "add_asset"`) with no
        category chosen yet, in which case this hops straight to
        `asset_category` without rendering anything of its own; the category
        step then calls back in here once `self._category` is set.

        A submission is handled before anything touches the network: an
        empty selection -- the default, and what "nothing to add" and every
        listing error's own re-render both submit -- never needs the
        catalogue at all, so it always reaches the menu, never an escaping
        exception and never a retry-only dead end. Only a non-empty selection
        fetches the catalogue (cheap either way once cached) to look up the
        chosen records.
        """
        self._load()

        if self._category is None:
            return await self.async_step_asset_category()

        category = self._category

        if user_input is not None:
            chosen_ids = set(user_input.get("assets", []))
            if chosen_ids:
                catalogue, error = await self._try_category_listing(category)
                if error is not None:
                    return self.async_show_form(
                        step_id="add_asset",
                        data_schema=_multiselect_schema("assets", []),
                        errors={"base": error},
                    )
                resolver = self._resolver()
                for asset in catalogue:
                    if asset.get("id") in chosen_ids:
                        resolver.remember(asset)
                        if asset["id"] not in self._assets:
                            self._assets.append(asset["id"])
                self._cache = resolver.as_dict()
            self._category = None
            return await self.async_step_init()

        catalogue, error = await self._try_category_listing(category)
        if error is not None:
            return self.async_show_form(
                step_id="add_asset",
                data_schema=_multiselect_schema("assets", []),
                errors={"base": error},
            )

        options = sorted(
            (
                {"value": asset["id"], "label": asset_label(asset)}
                for asset in catalogue
                if asset.get("id") and asset["id"] not in self._assets
            ),
            key=lambda option: option["label"],
        )

        if not options:
            return self.async_show_form(
                step_id="add_asset",
                data_schema=_multiselect_schema("assets", []),
                errors={"base": "no_assets_available"},
            )

        return self.async_show_form(
            step_id="add_asset",
            data_schema=_multiselect_schema("assets", options),
        )

    async def _try_category_listing(
        self, category: str
    ) -> tuple[list[dict] | None, str | None]:
        """Fetch a category listing, or the `options.error` key to show.

        Wraps `_async_category_listing` so both call sites in
        `async_step_add_asset` -- the render and a non-empty submit -- handle
        a transport failure identically, instead of only the render path
        catching it.
        """
        try:
            return await self._async_category_listing(self._client(), category), None
        except BitpandaApiError as err:
            return None, _api_error_code(err)

    async def _async_held_asset_ids(self, client: BitpandaApiClient) -> list[str]:
        """Ids of every currently held asset -- never fiat, see PortfolioData.

        Reuses the running portfolio coordinator's last data when the entry
        is loaded, costing nothing beyond what refreshes already do. An
        entry that is not (or not yet) loaded -- mid-reload, or opened right
        after setup failed -- falls back to one direct /portfolio call.
        """
        store = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if store is not None:
            data = store["portfolio_coordinator"].data
            return list(data.holdings) if data else []

        entries = await client.async_get_portfolio()
        return list(parse_portfolio(entries, rate=None).holdings)

    async def async_step_add_wallet(self, user_input=None) -> ConfigFlowResult:
        """Multi-select of held assets, minus those already tracked as wallets.

        A submission never touches the network -- the chosen values are
        already asset ids, looked up during whichever render produced them
        -- so an empty selection always reaches the menu the same way
        add_asset's does.
        """
        self._load()

        if user_input is not None:
            for asset_id in user_input.get("wallets", []):
                if asset_id not in self._wallets:
                    self._wallets.append(asset_id)
            return await self.async_step_init()

        client = self._client()
        resolver = self._resolver()
        try:
            held_ids = await self._async_held_asset_ids(client)
            options: list[dict] = []
            for asset_id in held_ids:
                if asset_id in self._wallets:
                    continue
                asset = resolver.get_cached(asset_id)
                if asset is None:
                    # One UUID per request -- the API returns 500 for a
                    # comma-separated list, despite what the docs say.
                    found = await client.async_get_assets(asset_id=asset_id)
                    asset = found[0] if found else None
                    if asset is not None:
                        resolver.remember(asset)
                if asset is not None:
                    options.append(
                        {"value": asset_id, "label": asset_label(asset)}
                    )
        except BitpandaApiError as err:
            # Covers BitpandaAuthError/BitpandaRateLimitError too (both
            # subclass it), and a plain 5xx, timeout or undecodable body,
            # which would otherwise escape this step and close the dialog.
            return self.async_show_form(
                step_id="add_wallet",
                data_schema=_multiselect_schema("wallets", []),
                errors={"base": _api_error_code(err)},
            )

        self._cache = resolver.as_dict()

        if not options:
            return self.async_show_form(
                step_id="add_wallet",
                data_schema=_multiselect_schema("wallets", []),
                errors={"base": "no_wallets_available"},
            )

        options.sort(key=lambda option: option["label"])
        return self.async_show_form(
            step_id="add_wallet",
            data_schema=_multiselect_schema("wallets", options),
        )

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
            #
            # `asset_label`, not the bare symbol -- two assets sharing a
            # symbol (the stock category deliberately lists both Accenture
            # listings, one per stock family) would otherwise be
            # indistinguishable here.
            return [
                {
                    "value": i,
                    "label": asset_label(by_id[i]) if i in by_id else i,
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
