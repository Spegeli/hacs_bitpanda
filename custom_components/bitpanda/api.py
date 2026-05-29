"""API client for Bitpanda."""
import asyncio
import logging
from typing import Any
import aiohttp

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class BitpandaApiClient:
    """Bitpanda API Client."""

    def __init__(self, api_key: str, session: aiohttp.ClientSession) -> None:
        self._api_key = api_key
        self._session = session
        self._headers = {"X-Api-Key": api_key}

    async def _request(self, url: str, headers: dict | None = None) -> Any:
        try:
            async with self._session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error during request to %s: %s", url, err)
            raise
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout during request to %s", url)
            raise

    async def async_get_ticker(self) -> dict[str, Any]:
        """Get price ticker data."""
        return await self._request(f"{API_BASE_URL}/ticker")

    async def async_get_asset_wallets(self) -> dict[str, Any]:
        """Get asset wallets."""
        return await self._request(f"{API_BASE_URL}/asset-wallets", headers=self._headers)

    async def async_get_fiat_wallets(self) -> dict[str, Any]:
        """Get fiat wallets."""
        return await self._request(f"{API_BASE_URL}/fiatwallets", headers=self._headers)

    async def get_available_currencies(self) -> list[str]:
        """Get available currencies from ticker."""
        try:
            ticker = await self.async_get_ticker()
            if ticker:
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
