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
    ConfigSubentryFlow,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import SectionConfig, section
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
from .asset_flow import PriceTrackerSubentryFlow
from .const import (
    API_KEY_URL,
    CONF_API_KEY,
    CONF_CURRENCY,
    CONF_CURRENCY_ID,
    CONF_EXTRA_CURRENCIES,
    CONF_LANGUAGE,
    CONF_LEGACY_ADOPT,
    DEFAULT_CURRENCY,
    DEFAULT_LANGUAGE,
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
    SUBENTRY_TYPE_PRICE_GROUP,
    SUPPORTED_CURRENCIES,
    entry_type,
)
from .groups import async_group_titles, price_group_subentries
from .language import async_shipped_languages, entry_language
from .purge import async_purge_portfolio

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


def _language_field(languages: list[str], current: str) -> dict:
    """The language of an entry's own texts (language.py), one of `languages`,
    each labelled with its own name through `selector.language`.

    `current` is the stored one; English stands in for a stored language no
    longer among `languages`, which the form would refuse to save unchanged.
    """
    return {
        vol.Required(
            CONF_LANGUAGE, default=current if current in languages else DEFAULT_LANGUAGE
        ): SelectSelector(
            SelectSelectorConfig(
                options=languages,
                translation_key="language",
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
    }


class BitpandaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up one of the two services."""

    VERSION = 3

    def __init__(self) -> None:
        self._api_key: str | None = None
        self._currency_ids: dict[str, str] = {}
        self._pending_currency: str | None = None

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
        """The Price Tracker of a migrated version 1 entry (see migration.py),
        its assets in one group per asset type -- titled in English: the new
        entry has no language option yet (language.entry_language)."""
        titles = await async_group_titles(self.hass, DEFAULT_LANGUAGE)
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
            subentries=price_group_subentries(import_data.get(IMPORT_ASSETS, []), titles),
        )

    # --- Reauth (Portfolio only: the Price Tracker has no key) -------------------

    def _async_replace_key(
        self, entry: ConfigEntry, api_key: str, reason: str
    ) -> ConfigFlowResult:
        """Store the key and get it into effect with exactly one reload.

        An entry that finished setup has an update listener that reloads it
        once its data changed; Home Assistant wants that listener to do the
        reloading and warns when async_update_reload_and_abort reloads a
        second time. A key re-entered unchanged changes nothing, though, so
        the listener never fires -- and a coordinator stopped by a 401 never
        restarts by itself -- so that case reloads explicitly. An entry whose
        setup failed -- the typical reauth case, a key rejected on the first
        portfolio refresh -- never registered the listener, so there the
        explicit reload is the only one.
        """
        if entry.update_listeners:
            if not self.hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_API_KEY: api_key}
            ):
                # Nothing changed, so no listener fires: reload explicitly, once.
                self.hass.config_entries.async_schedule_reload(entry.entry_id)
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

    def _reconfigure_schema(self, currency: str) -> vol.Schema:
        """Key optional and never pre-filled; currency pre-filled.

        `currency` arrives upper (stored form); the selector itself works in
        lowercase (hassfest), so the default passed here is lower-cased too --
        otherwise the pre-filled value would not match any option.
        """
        return vol.Schema(
            {
                vol.Optional(CONF_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
                vol.Required(CONF_CURRENCY, default=currency.lower()): _currency_select(
                    list(SUPPORTED_CURRENCIES)
                ),
            }
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Replace the key, change the currency, or both.

        A currency change goes through async_step_confirm_currency: it
        deletes every Portfolio sensor with its history.
        """
        entry = self._get_reconfigure_entry()
        if entry_type(entry) != ENTRY_TYPE_PORTFOLIO:
            return self.async_abort(reason="no_reconfigure")
        stored = entry.data[CONF_CURRENCY]
        # The currency the form shows: the stored one at first, the one just
        # submitted when the form comes back with an error.
        shown = stored
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {"api_key_url": API_KEY_URL}
        if user_input is not None:
            api_key = (user_input.get(CONF_API_KEY) or "").strip()
            # The form value travels lowercase (hassfest); stored upper again,
            # like every other currency in this flow.
            currency = user_input[CONF_CURRENCY].upper()
            try:
                if api_key:
                    errors, extra = await self._async_validate_key(api_key)
                    placeholders.update(extra)
                if not errors and currency != stored:
                    self._currency_ids = await self._async_currency_ids()
                    if currency not in self._currency_ids:
                        errors = {"base": "cannot_connect"}
            except BitpandaRateLimitError:
                errors = {"base": "rate_limited"}
            except BitpandaApiError:
                errors = {"base": "cannot_connect"}
            except Exception as err:  # noqa: BLE001 - a form error, never a traceback
                _log_unexpected("reconfigure", err)
                errors = {"base": "unknown"}
            if not errors:
                if currency != stored:
                    self._api_key = api_key or None
                    self._pending_currency = currency
                    return await self.async_step_confirm_currency()
                if api_key:
                    return self._async_replace_key(entry, api_key, "reconfigure_successful")
                return self.async_abort(reason="no_changes")
            shown = currency
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._reconfigure_schema(shown),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_confirm_currency(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Warn, then delete every Portfolio sensor with its history.

        Closing the dialog is the way back: nothing has changed until this
        step is submitted -- nor after it, when the Portfolio cannot be
        unloaded first (see async_purge_portfolio).
        """
        entry = self._get_reconfigure_entry()
        if user_input is None:
            return self.async_show_form(
                step_id="confirm_currency",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "old": entry.data[CONF_CURRENCY],
                    "new": self._pending_currency,
                },
            )
        updates: dict[str, Any] = {
            CONF_CURRENCY: self._pending_currency,
            CONF_CURRENCY_ID: self._currency_ids[self._pending_currency],
        }
        if self._api_key:
            updates[CONF_API_KEY] = self._api_key
        if not await async_purge_portfolio(self.hass, entry):
            return self.async_abort(reason="unload_failed")
        # The purge unloaded the entry, which removed its update listener:
        # this reload is the only one.
        return self.async_update_reload_and_abort(
            entry, data_updates=updates, reason="currency_changed"
        )

    # --- Options and subentries --------------------------------------------------------

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Both services have options (see BitpandaOptionsFlow): with this
        defined, Home Assistant's own async_supports_options_flow offers
        Configure on every entry."""
        return BitpandaOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """The Price Tracker's groups take assets through "+ Add price
        tracker"; the Portfolio has no user flow."""
        if entry_type(config_entry) != ENTRY_TYPE_PRICE_TRACKER:
            return {}
        return {SUBENTRY_TYPE_PRICE_GROUP: PriceTrackerSubentryFlow}


# The sections of the Configure forms: the Price Tracker's two, in their
# order, and the Portfolio's language, one of its own so that any later
# option gets a section of its own too. Their names and their fields' texts
# are `options.step.<step id>.sections`.
_SECTION_CURRENCIES = "currencies"
_SECTION_LANGUAGE = "language"
# Both open: a section is the only way a Home Assistant form sets fields
# apart, not a place to hide them.
_OPEN: SectionConfig = {"collapsed": False}


class BitpandaOptionsFlow(config_entries.OptionsFlow):
    """Configure, for both services.

    Each service shows its own form under a step id of its own, so each form
    has texts of its own (`options.step.price_tracker`, `.portfolio`): the
    Price Tracker's extra currencies -- EUR is always there -- and the
    language of its own texts, each in a section of its own; the Portfolio's
    language alone, in a section too, as its key and currency change through
    Reconfigure. Saving changes the entry's options -- flat, whatever
    sections the form shows -- and its update listener reloads it
    (__init__.py).
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if entry_type(self.config_entry) == ENTRY_TYPE_PRICE_TRACKER:
            return await self.async_step_price_tracker()
        return await self.async_step_portfolio()

    async def _async_language_section(self) -> dict:
        """The language of the entry's own texts, in its open section."""
        field = _language_field(
            await async_shipped_languages(self.hass), entry_language(self.config_entry)
        )
        return {vol.Required(_SECTION_LANGUAGE): section(vol.Schema(field), _OPEN)}

    async def async_step_price_tracker(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The extra currencies and the language, in two sections; their
        input arrives nested by section and is stored flat, as ever."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    **self.config_entry.options,
                    CONF_EXTRA_CURRENCIES: extra_currencies(
                        user_input[_SECTION_CURRENCIES].get(CONF_EXTRA_CURRENCIES)
                    ),
                    CONF_LANGUAGE: user_input[_SECTION_LANGUAGE][CONF_LANGUAGE],
                }
            )
        return self.async_show_form(
            step_id="price_tracker",
            data_schema=vol.Schema(
                {
                    vol.Required(_SECTION_CURRENCIES): section(
                        extra_currencies_schema(
                            self.config_entry.options.get(CONF_EXTRA_CURRENCIES, [])
                        ),
                        _OPEN,
                    ),
                    **await self._async_language_section(),
                }
            ),
        )

    async def async_step_portfolio(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The language in its section; the input arrives nested and is
        stored flat, as ever."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    **self.config_entry.options,
                    CONF_LANGUAGE: user_input[_SECTION_LANGUAGE][CONF_LANGUAGE],
                }
            )
        return self.async_show_form(
            step_id="portfolio", data_schema=vol.Schema(await self._async_language_section())
        )
