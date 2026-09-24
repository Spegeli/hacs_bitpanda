"""API client for the Bitpanda Public API."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_TIMEOUT, MAX_PAGE_SIZE

_LOGGER = logging.getLogger(__name__)


class BitpandaApiError(Exception):
    """Base error for API failures."""


class BitpandaAuthError(BitpandaApiError):
    """The API key is missing, invalid, or lacks the required scope."""


class BitpandaRateLimitError(BitpandaApiError):
    """The read rate limit was exceeded."""


class BitpandaApiClient:
    """Client for the Bitpanda Public API.

    Read-only. No method here may call a write endpoint.
    """

    def __init__(self, api_key: str, session: aiohttp.ClientSession) -> None:
        self._api_key = api_key
        self._session = session
        self._headers = {"x-api-key": api_key}

    async def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Perform one GET and return the decoded body.

        Never attach the exception chain to the log record: tracebacks can carry
        the API key.
        """
        url = f"{API_BASE_URL}{path}"
        try:
            async with self._session.get(
                url,
                headers=self._headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
            ) as response:
                if response.status in (401, 403):
                    raise BitpandaAuthError(f"Unauthorized for {path}")
                if response.status == 429:
                    raise BitpandaRateLimitError(f"Rate limited on {path}")
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as err:
            _LOGGER.error("HTTP %s from %s", err.status, path)
            raise BitpandaApiError(f"HTTP {err.status} from {path}") from None
        except aiohttp.ClientError as err:
            _LOGGER.error("Connection error for %s: %s", path, type(err).__name__)
            raise BitpandaApiError(f"Connection error for {path}") from None
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout for %s", path)
            raise BitpandaApiError(f"Timeout for {path}") from None

    async def _paginate(self, path: str, params: dict[str, Any]) -> list[dict]:
        """Collect every page of a cursor-paginated endpoint.

        Deduplicates by id: pages can overlap by one record.
        """
        params = dict(params)
        params.setdefault("page_size", MAX_PAGE_SIZE)
        out: list[dict] = []
        seen: set[str] = set()
        cursor: str | None = None

        while True:
            if cursor:
                params["cursor"] = cursor
            body = await self._request(path, params)
            for item in body.get("data", []):
                key = item.get("id") or item.get("operation_id")
                if key is not None and key in seen:
                    continue
                if key is not None:
                    seen.add(key)
                out.append(item)
            if not body.get("has_next_page"):
                return out
            cursor = body.get("next_cursor")
            if not cursor:
                return out

    async def async_get_currencies(self) -> list[dict]:
        """List all fiat currencies. Not paginated."""
        body = await self._request("/currencies")
        return body.get("data", [])

    async def async_get_assets(
        self,
        *,
        symbol: str | None = None,
        asset_id: str | None = None,
        page_size: int = MAX_PAGE_SIZE,
    ) -> list[dict]:
        """List assets, optionally filtered.

        `asset_id` takes a single UUID only. A comma-separated list returns 500,
        despite what the published documentation says.
        """
        params: dict[str, Any] = {"page_size": min(page_size, MAX_PAGE_SIZE)}
        if symbol:
            params["symbol"] = symbol
        if asset_id:
            params["id"] = asset_id
        return await self._paginate("/assets", params)
