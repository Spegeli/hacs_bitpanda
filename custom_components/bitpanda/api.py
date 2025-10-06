"""API client for Bitpanda."""
import asyncio
import logging
from typing import Any, Dict, Optional
import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_BASE_URL, API_TICKER_URL

_LOGGER = logging.getLogger(__name__)


class BitpandaApiClient:
    """Bitpanda API Client."""

    def __init__(self, api_key: str, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._api_key = api_key
        self._session = session
        self._headers = {"X-Api-Key": api_key}

    async def async_get_ticker(self) -> Dict[str, Any]:
        """Get price ticker data."""
        try:
            async with self._session.get(API_TICKER_URL, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching ticker data: %s", err)
            raise
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout fetching ticker data: %s", err)
            raise

    async def async_get_asset_wallets(self) -> Dict[str, Any]:
        """Get asset wallets."""
        try:
            url = f"{API_BASE_URL}/asset-wallets"
            async with self._session.get(
                url, headers=self._headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching asset wallets: %s", err)
            raise
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout fetching asset wallets: %s", err)
            raise

    async def async_get_fiat_wallets(self) -> Dict[str, Any]:
        """Get fiat wallets."""
        try:
            url = f"{API_BASE_URL}/fiatwallets"
            async with self._session.get(
                url, headers=self._headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching fiat wallets: %s", err)
            raise
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout fetching fiat wallets: %s", err)
            raise

    async def async_get_crypto_wallets(self) -> Dict[str, Any]:
        """Get crypto wallets."""
        try:
            url = f"{API_BASE_URL}/wallets"
            async with self._session.get(
                url, headers=self._headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching crypto wallets: %s", err)
            raise
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout fetching crypto wallets: %s", err)
            raise

    async def async_test_connection(self) -> bool:
        """Test the API connection."""
        try:
            await self.async_get_fiat_wallets()
            return True
        except Exception:
            return False

    async def get_available_currencies(self) -> list[str]:
        """Get available currencies from ticker."""
        try:
            ticker = await self.async_get_ticker()
            if ticker:
                # Get first asset to find available currencies
                first_asset = next(iter(ticker.values()))
                return list(first_asset.keys())
            return ["EUR", "USD", "CHF", "GBP"]
        except Exception as err:
            _LOGGER.error("Error getting available currencies: %s", err)
            return ["EUR", "USD", "CHF", "GBP"]

    async def get_available_assets(self) -> list[str]:
        """Get available assets from ticker."""
        try:
            ticker = await self.async_get_ticker()
            return list(ticker.keys()) if ticker else []
        except Exception as err:
            _LOGGER.error("Error getting available assets: %s", err)
            return []
