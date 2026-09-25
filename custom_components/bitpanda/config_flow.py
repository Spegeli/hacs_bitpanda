"""Config flow for the Bitpanda integration.

One integration, two services, one config entry each: Bitpanda Portfolio
(needs an API key) and Bitpanda Price Tracker (no key). Each entry carries
its service as its unique_id, so neither can exist twice -- not even when two
setup dialogs race each other.
"""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    ConfigSubentryData,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import BitpandaApiClient, BitpandaApiError, BitpandaRateLimitError
from .assets import slim_asset
from .const import (
    API_KEY_URL,
    CONF_API_KEY,
    CONF_ASSET,
    CONF_CURRENCY,
    CONF_CURRENCY_ID,
    CONF_EXTRA_CURRENCIES,
    CONF_LEGACY_ADOPT,
    DEFAULT_CURRENCY,
    DOMAIN,
    ENTRY_TYPE,
    ENTRY_TYPE_PORTFOLIO,
    ENTRY_TYPE_PRICE_TRACKER,
    EXTRA_CURRENCIES,
    IMPORT_ASSETS,
    PORTFOLIO_TITLE,
    PRICE_TRACKER_TITLE,
    REQUIRED_SCOPES,
    SCOPE_LABELS,
    SUBENTRY_TYPE_ASSET,
    SUPPORTED_CURRENCIES,
    entry_type,
)
from .naming import asset_display_label

_LOGGER = logging.getLogger(__name__)

_SERVICES = (ENTRY_TYPE_PORTFOLIO, ENTRY_TYPE_PRICE_TRACKER)

# The key is typed into a password field and never sent back to the browser:
# no form ever carries it as a default or a placeholder.
_KEY_SCHEMA = vol.Schema(
    {vol.Required(CONF_API_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))}
)


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


def _currency_select(options: list[str], *, multiple: bool = False) -> SelectSelector:
    """Currency codes labelled with their names through `selector.currency`.

    hassfest's translation-key validator accepts lowercase selector option
    keys only, so the options travel to and from the frontend lowercase;
    everything stored (entry data/options, `self._currency_ids`) stays
    uppercase -- see `async_step_currency` and `extra_currencies` below,
    which convert back at the boundary.
    """
    return SelectSelector(
        SelectSelectorConfig(
            options=[currency.lower() for currency in options],
            translation_key="currency",
            multiple=multiple,
            mode=SelectSelectorMode.LIST if multiple else SelectSelectorMode.DROPDOWN,
        )
    )


def extra_currencies(values) -> list[str]:
    """The supported extra currencies among `values`, in one fixed order.

    `values` arrives lowercase from the selector form; upper-cased here
    before matching EXTRA_CURRENCIES, which -- like every other stored
    currency -- stays uppercase.
    """
    chosen = {str(value).upper() for value in values or []}
    return [currency for currency in EXTRA_CURRENCIES if currency in chosen]


def extra_currencies_schema(selected: list[str]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_EXTRA_CURRENCIES,
                default=[currency.lower() for currency in selected],
            ): _currency_select(list(EXTRA_CURRENCIES), multiple=True)
        }
    )


def asset_subentry_data(asset: dict) -> ConfigSubentryData:
    """The subentry of one tracked asset: titled with its label, keyed by its id."""
    record = slim_asset(asset)
    return ConfigSubentryData(
        data={CONF_ASSET: record},
        subentry_type=SUBENTRY_TYPE_ASSET,
        title=asset_display_label(record),
        unique_id=record["id"],
    )


class BitpandaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up one of the two services."""

    VERSION = 3

    def __init__(self) -> None:
        self._api_key: str | None = None
        self._currency_ids: dict[str, str] = {}

    # --- Service menu -----------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        configured = {
            entry_type(entry)
            for entry in self._async_current_entries(include_ignore=False)
        }
        available = [service for service in _SERVICES if service not in configured]
        if not available:
            return self.async_abort(reason="all_configured")
        return self.async_show_menu(step_id="user", menu_options=available)

    # --- Shared helpers -----------------------------------------------------

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

    async def _async_currency_ids(self) -> dict[str, str]:
        """Symbol -> Bitpanda currency id. /currencies is public: no key sent."""
        client = BitpandaApiClient(None, async_get_clientsession(self.hass))
        return {
            currency["symbol"]: currency["id"]
            for currency in await client.async_get_currencies()
            if currency.get("symbol") in SUPPORTED_CURRENCIES and currency.get("id")
        }

    # --- Portfolio ------------------------------------------------------------

    async def async_step_portfolio(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(ENTRY_TYPE_PORTFOLIO)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            try:
                errors, placeholders = await self._async_validate_key(api_key)
                if not errors:
                    self._currency_ids = await self._async_currency_ids()
                    if not self._currency_ids:
                        errors = {"base": "cannot_connect"}
            except BitpandaRateLimitError:
                errors = {"base": "rate_limited"}
            except BitpandaApiError:
                errors = {"base": "cannot_connect"}
            except Exception as err:  # noqa: BLE001 - a form error, never a traceback
                _log_unexpected("portfolio", err)
                errors = {"base": "unknown"}
            if not errors:
                self._api_key = api_key
                return await self.async_step_currency()
        return self.async_show_form(
            step_id="portfolio",
            data_schema=_KEY_SCHEMA,
            errors=errors,
            description_placeholders={"api_key_url": API_KEY_URL, **placeholders},
        )

    async def async_step_currency(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            # Re-checked here: a second dialog may have finished in between.
            await self.async_set_unique_id(ENTRY_TYPE_PORTFOLIO)
            self._abort_if_unique_id_configured()
            # The form value travels lowercase (hassfest); stored upper again.
            currency = user_input[CONF_CURRENCY].upper()
            return self.async_create_entry(
                title=PORTFOLIO_TITLE,
                data={
                    ENTRY_TYPE: ENTRY_TYPE_PORTFOLIO,
                    CONF_API_KEY: self._api_key,
                    CONF_CURRENCY: currency,
                    CONF_CURRENCY_ID: self._currency_ids[currency],
                },
            )
        options = [c for c in SUPPORTED_CURRENCIES if c in self._currency_ids]
        return self.async_show_form(
            step_id="currency",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CURRENCY, default=DEFAULT_CURRENCY.lower()
                    ): _currency_select(options)
                }
            ),
        )

    # --- Price Tracker ------------------------------------------------------------

    async def async_step_price_tracker(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(ENTRY_TYPE_PRICE_TRACKER)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(
                title=PRICE_TRACKER_TITLE,
                data={ENTRY_TYPE: ENTRY_TYPE_PRICE_TRACKER},
                options={
                    CONF_EXTRA_CURRENCIES: extra_currencies(
                        user_input.get(CONF_EXTRA_CURRENCIES)
                    )
                },
            )
        return self.async_show_form(
            step_id="price_tracker", data_schema=extra_currencies_schema([])
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """The Price Tracker of a migrated version 1 entry (see migration.py)."""
        await self.async_set_unique_id(ENTRY_TYPE_PRICE_TRACKER)
        self._abort_if_unique_id_configured()
        data: dict[str, Any] = {ENTRY_TYPE: ENTRY_TYPE_PRICE_TRACKER}
        if import_data.get(CONF_LEGACY_ADOPT):
            data[CONF_LEGACY_ADOPT] = import_data[CONF_LEGACY_ADOPT]
        return self.async_create_entry(
            title=PRICE_TRACKER_TITLE,
            data=data,
            options={
                CONF_EXTRA_CURRENCIES: extra_currencies(
                    import_data.get(CONF_EXTRA_CURRENCIES)
                )
            },
            subentries=[
                asset_subentry_data(asset)
                for asset in import_data.get(IMPORT_ASSETS, [])
            ],
        )

    # --- Reauth (Portfolio only: the Price Tracker has no key) -------------------

    def _async_replace_key(
        self, entry: ConfigEntry, api_key: str, reason: str
    ) -> ConfigFlowResult:
        """Store a new key and get it into effect with exactly one reload.

        An entry that finished setup has an update listener that reloads it
        on any change; Home Assistant wants that listener to do the
        reloading and warns when async_update_reload_and_abort reloads a
        second time. An entry whose setup failed -- the typical reauth case,
        a key rejected on the first portfolio refresh -- never registered
        the listener, so there the explicit reload is the only one.
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
            data_schema=_KEY_SCHEMA,
            errors=errors,
            description_placeholders=placeholders,
        )

    # --- Reconfigure (Portfolio only) ------------------------------------------------

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        if entry_type(entry) != ENTRY_TYPE_PORTFOLIO:
            return self.async_abort(reason="no_reconfigure")
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
                return self._async_replace_key(entry, api_key, "reconfigure_successful")
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_KEY_SCHEMA,
            errors=errors,
            description_placeholders=placeholders,
        )

    # --- Options and subentries --------------------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return PriceTrackerOptionsFlow()

    @classmethod
    @callback
    def async_supports_options_flow(cls, config_entry: ConfigEntry) -> bool:
        """Only the Price Tracker has options: the Portfolio tracks everything."""
        return entry_type(config_entry) == ENTRY_TYPE_PRICE_TRACKER


class PriceTrackerOptionsFlow(config_entries.OptionsFlow):
    """Configure: the Price Tracker's extra currencies. EUR is always there."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={
                    **self.config_entry.options,
                    CONF_EXTRA_CURRENCIES: extra_currencies(
                        user_input.get(CONF_EXTRA_CURRENCIES)
                    ),
                }
            )
        return self.async_show_form(
            step_id="init",
            data_schema=extra_currencies_schema(
                self.config_entry.options.get(CONF_EXTRA_CURRENCIES, [])
            ),
        )
