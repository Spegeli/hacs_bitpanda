"""Config flow for Bitpanda integration."""
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


class BitpandaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Bitpanda."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._api_key: str | None = None
        self._currency: str | None = None
        self._available_currencies: list[str] = []
        self._available_assets: list[str] = []
        self._client: BitpandaApiClient | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]

            session = async_get_clientsession(self.hass)
            client = BitpandaApiClient(self._api_key, session)

            if await client.async_test_connection():
                self._available_currencies = await client.get_available_currencies()
                self._available_assets = await client.get_available_assets()
                self._client = client
                return await self.async_step_currency()
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): cv.string,
                }
            ),
            errors=errors,
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
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CURRENCY, default=DEFAULT_CURRENCY): SelectSelector(
                        SelectSelectorConfig(
                            options=self._available_currencies,
                            mode="dropdown",
                        )
                    ),
                }
            ),
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
        self._available_assets: list[str] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["price_tracker", "wallets"],
        )

    async def async_step_price_tracker(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle price tracker options."""
        if user_input is not None:
            new_options = {**self.config_entry.options}
            new_options[CONF_TRACKED_ASSETS] = user_input.get(CONF_TRACKED_ASSETS, [])
            return self.async_create_entry(title="", data=new_options)

        session = async_get_clientsession(self.hass)
        api_key = self.config_entry.data[CONF_API_KEY]
        client = BitpandaApiClient(api_key, session)

        try:
            self._available_assets = await client.get_available_assets()
        except Exception as err:
            _LOGGER.error("Error fetching assets: %s", err)
            self._available_assets = []

        current_tracked = self.config_entry.options.get(CONF_TRACKED_ASSETS, [])

        return self.async_show_form(
            step_id="price_tracker",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TRACKED_ASSETS,
                        default=current_tracked,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=self._available_assets,
                            multiple=True,
                            mode="dropdown",
                        )
                    ),
                }
            ),
        )

    async def async_step_wallets(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle wallet options."""
        if user_input is not None:
            new_options = {**self.config_entry.options}
            new_options[CONF_TRACKED_WALLETS] = user_input.get(CONF_TRACKED_WALLETS, [])
            return self.async_create_entry(title="", data=new_options)

        session = async_get_clientsession(self.hass)
        api_key = self.config_entry.data[CONF_API_KEY]
        client = BitpandaApiClient(api_key, session)

        wallet_options = []

        def process_wallet_collection(parent_category: str, sub_category: str | None, wallets_data: list) -> None:
            """Process a collection of wallets."""
            if not isinstance(wallets_data, list):
                return

            for wallet in wallets_data:
                if "attributes" not in wallet:
                    continue

                symbol = wallet["attributes"].get("cryptocoin_symbol", "")
                if not symbol:
                    continue

                full_category = f"{parent_category}_{sub_category}" if sub_category else parent_category

                if parent_category == "commodity" and sub_category == "metal":
                    metal_names = {
                        "XAU": "Gold (XAU)",
                        "XAG": "Silver (XAG)",
                        "XPT": "Platinum (XPT)",
                        "XPD": "Palladium (XPD)",
                    }
                    label = f"Metal: {metal_names.get(symbol, symbol)}"
                elif parent_category == "index":
                    label = f"Index: {symbol}"
                elif parent_category == "cryptocoin":
                    label = f"Crypto: {symbol}"
                else:
                    label = f"{parent_category.title()}: {symbol}"

                wallet_options.append({
                    "value": f"{full_category}_{symbol}",
                    "label": label,
                })

        try:
            asset_wallets = await client.async_get_asset_wallets()

            if "data" in asset_wallets and "attributes" in asset_wallets["data"]:
                for category, data in asset_wallets["data"]["attributes"].items():
                    if category in ("security", "equity_security"):
                        _LOGGER.debug("Skipping category: %s (no prices available)", category)
                        continue

                    if isinstance(data, dict) and "attributes" in data and "wallets" in data["attributes"]:
                        process_wallet_collection(category, None, data["attributes"]["wallets"])
                    elif isinstance(data, dict):
                        for sub_category, sub_data in data.items():
                            if isinstance(sub_data, dict) and "attributes" in sub_data and "wallets" in sub_data["attributes"]:
                                process_wallet_collection(category, sub_category, sub_data["attributes"]["wallets"])

            fiat_wallets = await client.async_get_fiat_wallets()
            if "data" in fiat_wallets:
                for wallet in fiat_wallets["data"]:
                    symbol = wallet["attributes"].get("fiat_symbol", "")
                    if symbol:
                        wallet_options.append({
                            "value": f"fiat_{symbol}",
                            "label": f"Fiat: {symbol}",
                        })

        except Exception as err:
            _LOGGER.error("Error fetching wallets: %s", err, exc_info=True)

        _LOGGER.info("Found %s wallet options", len(wallet_options))

        wallet_options.sort(key=lambda x: x["label"])
        current_tracked = self.config_entry.options.get(CONF_TRACKED_WALLETS, [])

        return self.async_show_form(
            step_id="wallets",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TRACKED_WALLETS,
                        default=current_tracked,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=wallet_options,
                            multiple=True,
                            mode="dropdown",
                        )
                    ),
                }
            ),
        )
