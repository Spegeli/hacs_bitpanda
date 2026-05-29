"""Config flow for Bitpanda integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig
import homeassistant.helpers.config_validation as cv

from .api import BitpandaApiClient
from .const import (
    CONF_API_KEY,
    CONF_CURRENCY,
    CONF_TRACKED_ASSETS,
    CONF_TRACKED_WALLETS,
    DEFAULT_CURRENCY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


_METAL_NAMES: dict[str, str] = {
    "XAU": "Gold (XAU)",
    "XAG": "Silver (XAG)",
    "XPT": "Platinum (XPT)",
    "XPD": "Palladium (XPD)",
}

_CATEGORY_PREFIXES: dict[str, str] = {
    "crypto": "cryptocoin_",
    "fiat": "fiat_",
    "metal": "commodity_metal_",
    "index": "index_",
}


async def _async_build_wallet_options(client: BitpandaApiClient, category: str | None = None) -> list[dict]:
    """Build wallet options list from Bitpanda API."""
    wallet_options = []

    def process_wallet_collection(
        parent_category: str, sub_category: str | None, wallets_data: list
    ) -> None:
        if not isinstance(wallets_data, list):
            return
        for wallet in wallets_data:
            if "attributes" not in wallet:
                continue
            symbol = wallet["attributes"].get("cryptocoin_symbol", "")
            if not symbol:
                continue
            full_category = (
                f"{parent_category}_{sub_category}" if sub_category else parent_category
            )
            if parent_category == "commodity" and sub_category == "metal":
                label = _METAL_NAMES.get(symbol, symbol)
            else:
                label = symbol
            wallet_options.append({"value": f"{full_category}_{symbol}", "label": label})

    try:
        asset_wallets = await client.async_get_asset_wallets()
        if "data" in asset_wallets and "attributes" in asset_wallets["data"]:
            for cat, data in asset_wallets["data"]["attributes"].items():
                if cat in ("security", "equity_security"):
                    _LOGGER.debug("Skipping category: %s (no prices available)", cat)
                    continue
                if isinstance(data, dict) and "attributes" in data and "wallets" in data["attributes"]:
                    process_wallet_collection(cat, None, data["attributes"]["wallets"])
                elif isinstance(data, dict):
                    for sub_category, sub_data in data.items():
                        if isinstance(sub_data, dict) and "attributes" in sub_data and "wallets" in sub_data["attributes"]:
                            process_wallet_collection(cat, sub_category, sub_data["attributes"]["wallets"])

        fiat_wallets = await client.async_get_fiat_wallets()
        if "data" in fiat_wallets:
            for wallet in fiat_wallets["data"]:
                if "attributes" not in wallet:
                    continue
                symbol = wallet["attributes"].get("fiat_symbol", "")
                if symbol:
                    wallet_options.append({"value": f"fiat_{symbol}", "label": symbol})

    except Exception as err:
        _LOGGER.error("Error fetching wallets: %s", err)

    wallet_options.sort(key=lambda x: x["label"])

    if category is not None:
        prefix = _CATEGORY_PREFIXES.get(category, "")
        wallet_options = [o for o in wallet_options if o["value"].startswith(prefix)]

    _LOGGER.debug("Found %s wallet options (category: %s)", len(wallet_options), category or "all")
    return wallet_options


class BitpandaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Bitpanda."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_key: str | None = None
        self._currency: str | None = None
        self._available_currencies: list[str] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]
            session = async_get_clientsession(self.hass)
            client = BitpandaApiClient(self._api_key, session)

            try:
                await client.async_get_fiat_wallets()
                self._available_currencies = await client.get_available_currencies()
                return await self.async_step_currency()
            except aiohttp.ClientResponseError as err:
                errors["base"] = "invalid_auth" if err.status in (401, 403) else "cannot_connect"
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): cv.string}),
            errors=errors,
            description_placeholders={"api_key_url": "https://web.bitpanda.com/apikey"},
        )

    async def async_step_currency(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle currency selection."""
        if user_input is not None:
            self._currency = user_input[CONF_CURRENCY]
            return self.async_create_entry(
                title=f"Bitpanda ({self._currency})",
                data={
                    CONF_API_KEY: self._api_key,
                    CONF_CURRENCY: self._currency,
                },
                options={
                    CONF_TRACKED_ASSETS: [],
                    CONF_TRACKED_WALLETS: [],
                },
            )

        return self.async_show_form(
            step_id="currency",
            data_schema=vol.Schema({
                vol.Required(CONF_CURRENCY, default=DEFAULT_CURRENCY): SelectSelector(
                    SelectSelectorConfig(
                        options=self._available_currencies,
                        mode="dropdown",
                    )
                ),
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return BitpandaOptionsFlowHandler()


class BitpandaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Bitpanda options."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._tracked_assets: list[str] | None = None
        self._tracked_wallets: list[str] | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if self._tracked_assets is None:
            self._tracked_assets = list(self.config_entry.options.get(CONF_TRACKED_ASSETS, []))
            self._tracked_wallets = list(self.config_entry.options.get(CONF_TRACKED_WALLETS, []))

        return self.async_show_menu(
            step_id="init",
            menu_options=["price_tracker", "crypto_wallets", "fiat_wallets", "metal_wallets", "index_wallets", "save"],
        )

    async def async_step_price_tracker(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle price tracker options."""
        if user_input is not None:
            self._tracked_assets = user_input.get(CONF_TRACKED_ASSETS, [])
            return await self.async_step_init()

        session = async_get_clientsession(self.hass)
        client = BitpandaApiClient(self.config_entry.data[CONF_API_KEY], session)

        try:
            available_assets = await client.get_available_assets()
        except Exception as err:
            _LOGGER.error("Error fetching assets: %s", err)
            available_assets = []

        return self.async_show_form(
            step_id="price_tracker",
            data_schema=vol.Schema({
                vol.Optional(CONF_TRACKED_ASSETS, default=self._tracked_assets): SelectSelector(
                    SelectSelectorConfig(
                        options=available_assets,
                        multiple=True,
                        mode="dropdown",
                    )
                ),
            }),
        )

    async def _async_wallet_step(
        self,
        step_id: str,
        category: str,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Generic handler for per-category wallet steps."""
        if self._tracked_wallets is None:
            self._tracked_wallets = list(self.config_entry.options.get(CONF_TRACKED_WALLETS, []))
        prefix = _CATEGORY_PREFIXES.get(category, "")
        if user_input is not None:
            other = [w for w in self._tracked_wallets if not w.startswith(prefix)]
            self._tracked_wallets = other + user_input.get(CONF_TRACKED_WALLETS, [])
            return await self.async_step_init()

        session = async_get_clientsession(self.hass)
        client = BitpandaApiClient(self.config_entry.data[CONF_API_KEY], session)
        wallet_options = await _async_build_wallet_options(client, category)
        current = [w for w in self._tracked_wallets if w.startswith(prefix)]

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({
                vol.Optional(CONF_TRACKED_WALLETS, default=current): SelectSelector(
                    SelectSelectorConfig(
                        options=wallet_options,
                        multiple=True,
                        mode="dropdown",
                    )
                ),
            }),
        )

    async def async_step_crypto_wallets(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle crypto wallet options."""
        return await self._async_wallet_step("crypto_wallets", "crypto", user_input)

    async def async_step_fiat_wallets(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle fiat wallet options."""
        return await self._async_wallet_step("fiat_wallets", "fiat", user_input)

    async def async_step_metal_wallets(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle metal wallet options."""
        return await self._async_wallet_step("metal_wallets", "metal", user_input)

    async def async_step_index_wallets(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle index wallet options."""
        return await self._async_wallet_step("index_wallets", "index", user_input)

    async def async_step_save(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Save all options and close."""
        return self.async_create_entry(
            title="",
            data={
                CONF_TRACKED_ASSETS: self._tracked_assets or [],
                CONF_TRACKED_WALLETS: self._tracked_wallets or [],
            },
        )
