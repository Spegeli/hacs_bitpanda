"""API client for the Bitpanda Public API."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_TIMEOUT, MAX_PAGE_SIZE, REQUIRED_SCOPES

_LOGGER = logging.getLogger(__name__)


class BitpandaApiError(Exception):
    """Base error for API failures."""


class BitpandaAuthError(BitpandaApiError):
    """The API key is missing, invalid, or lacks the required scope."""


class BitpandaRateLimitError(BitpandaApiError):
    """The read rate limit was exceeded."""


# One cheap, read-only endpoint per required scope, used only to probe which
# scopes a key carries during setup. `/portfolio` needs no params; the other
# two accept `page_size` and 1 is the smallest page the API allows.
_SCOPE_PROBES: dict[str, tuple[str, dict[str, Any] | None]] = {
    "balance": ("/portfolio", None),
    "transaction": ("/operations", {"page_size": 1}),
    "earn": ("/earn/configs", {"page_size": 1}),
}


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
        except ValueError:
            # json.JSONDecodeError subclasses ValueError, and a body that
            # decodes to text but not JSON can also raise UnicodeDecodeError
            # here, another ValueError subclass — hence the general wording.
            # Without this the exception escapes to Home Assistant's
            # coordinator, whose final handler calls logger.exception() —
            # exc_info=True through this integration's own logger, which is
            # exactly what the API-key rule forbids.
            _LOGGER.error("Could not decode response from %s", path)
            raise BitpandaApiError(f"Could not decode response from {path}") from None

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
            for item in body.get("data") or []:
                key = item.get("id")
                if key is None:
                    key = item.get("operation_id")
                if key is not None:
                    if key in seen:
                        continue
                    seen.add(key)
                out.append(item)
            if not body.get("has_next_page"):
                return out
            next_cursor = body.get("next_cursor")
            # Stop on a missing cursor, and on one that has not moved. The
            # server is known to emit cursors it then ignores, returning the
            # same page again; without this guard the loop never terminates
            # and blocks the event loop.
            if not next_cursor or next_cursor == cursor:
                return out
            cursor = next_cursor

    async def async_get_currencies(self) -> list[dict]:
        """List all fiat currencies. Not paginated."""
        body = await self._request("/currencies")
        return body.get("data") or []

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

    async def async_list_assets(
        self, type_: str, group: str | None = None
    ) -> list[dict]:
        """List every asset of one catalogue type (and, optionally, group).

        Builds the options flow's category pickers (see config_flow.py's
        ASSET_CATEGORY_FILTERS) -- a handful of these calls cover the whole
        14000-asset catalogue, each cached there for 24 hours precisely
        because even one uncached listing is a meaningful slice of the
        hourly read budget.
        """
        params: dict[str, Any] = {"type": type_}
        if group is not None:
            params["group"] = group
        return await self._paginate("/assets", params)

    async def async_get_ticker(self, asset_id: str) -> dict:
        """Current price for one asset.

        Always returns EUR. Every currency parameter that could plausibly exist
        was probed and is silently ignored, so none is sent.
        """
        body = await self._request(f"/tickers/{asset_id}")
        return body.get("data") or {}

    async def async_get_portfolio(
        self, *, equivalent_currency_id: str | None = None
    ) -> list[dict]:
        """All non-zero holdings.

        The list mixes two shapes. Asset entries carry `asset_id` and
        `currency_balance`; fiat entries carry `currency_id` and no
        `currency_balance`. Branch on the presence of `asset_id`.
        """
        params: dict[str, Any] = {}
        if equivalent_currency_id:
            params["equivalent_currency_id"] = equivalent_currency_id
        body = await self._request("/portfolio", params or None)
        return body.get("data") or []

    async def async_get_portfolio_history(
        self,
        *,
        timeframe: str = "DAY",
        equivalent_currency_id: str | None = None,
    ) -> dict:
        """Portfolio value series and the return over the selected window.

        `timeframe` is one of DAY, WEEK, MONTH, SIX_MONTH, YEAR. It is absent
        from the published documentation but is validated server-side: an
        unknown value returns 400.
        """
        params: dict[str, Any] = {"timeframe": timeframe}
        if equivalent_currency_id:
            params["equivalent_currency_id"] = equivalent_currency_id
        body = await self._request("/portfolio-history", params)
        return body.get("data") or {}

    async def async_get_earn_configs(self) -> list[dict]:
        """Available Earn products and their rates.

        This is a catalog, not user positions. `annual_percentage_rate` is a
        JSON number and a fraction: 0.0544 means 5.44 %.
        """
        return await self._paginate("/earn/configs", {})

    async def async_get_operations(
        self, *, from_ts: str | None = None, to_ts: str | None = None
    ) -> list[dict]:
        """Operation history, optionally windowed by date.

        `from` and `to` are undocumented on the hosted docs but work, and are
        preferred over cursor paging: the server emits cursors without
        milliseconds and then ignores them, so a cursor loop can stall on
        page one. Requires a key with all read scopes; a portfolio-capable key
        gets 401.
        """
        params: dict[str, Any] = {}
        if from_ts:
            params["from"] = from_ts
        if to_ts:
            params["to"] = to_ts
        return await self._paginate("/operations", params)

    async def async_missing_scopes(self) -> list[str]:
        """Return the required scopes this key lacks, in REQUIRED_SCOPES order.

        One request per scope. Bitpanda answers a wrong key and a missing scope
        with the same 401, so the caller reads the pattern: every scope missing
        means the key itself is wrong or carries none of them. Rate-limit and
        connection errors propagate.
        """
        missing: list[str] = []
        for scope in REQUIRED_SCOPES:
            path, params = _SCOPE_PROBES[scope]
            try:
                await self._request(path, params)
            except BitpandaAuthError:
                missing.append(scope)
        return missing
