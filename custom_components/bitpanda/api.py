"""API client for the Bitpanda Public API."""
from __future__ import annotations

import asyncio
import base64
from collections.abc import Callable
from datetime import datetime
import logging
import re
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_TIMEOUT, MAX_PAGE_SIZE, REQUIRED_SCOPES

_LOGGER = logging.getLogger(__name__)

# Hard stop for one paginated listing. The largest real walk is the whole
# 14,054-asset catalogue, 141 pages of 100; a five-year operation history took
# 13. 500 pages (50,000 records) leaves a wide margin above both, and even an
# /operations history that long, re-read at the hourly rewards cadence, stays
# inside the hourly read budget next to the share reserved for prices.
_MAX_PAGES = 500

# The only cursor shape /operations mishandles: a whole-second UTC timestamp.
_WHOLE_SECOND_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def normalize_operations_cursor(cursor: str) -> str:
    """Return an /operations cursor in the form the server honours.

    /operations cursors are base64 of an ISO-8601 timestamp meaning "records
    strictly older than this". The server silently ignores a cursor whose
    timestamp has no fractional seconds and answers with page 1 and a 200 --
    yet it emits exactly such cursors itself whenever a page boundary falls on
    a whole second. The same instant with ".000" added is honoured.

    Anything that does not decode to such a timestamp is returned unchanged.
    The rewritten cursor is 24 ASCII bytes of digits, "-", ":", "T", "." and
    "Z", which always base64-encode to 32 plain letters and digits: no padding,
    and none of the characters on which the standard and URL-safe alphabets
    differ, so it takes the same form whichever of them the server uses.
    """
    if not isinstance(cursor, str):
        return cursor
    try:
        decoded = base64.b64decode(
            cursor + "=" * (-len(cursor) % 4), validate=True
        ).decode("ascii")
        # Shape first: fromisoformat alone would also accept forms (no
        # seconds, an offset) where appending ".000" makes no sense.
        if not _WHOLE_SECOND_TIMESTAMP.fullmatch(decoded):
            return cursor
        datetime.fromisoformat(decoded)
    except ValueError:
        # binascii.Error (not base64), UnicodeDecodeError (not text) and an
        # impossible date all subclass ValueError.
        return cursor
    return base64.b64encode(f"{decoded[:-1]}.000Z".encode("ascii")).decode("ascii")


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

    def __init__(self, api_key: str | None, session: aiohttp.ClientSession) -> None:
        """`api_key=None` builds a keyless client for the public endpoints.

        /currencies, /assets and /tickers answer without a key. A keyless
        client sends no x-api-key header at all, so public lookups never
        carry the key and never count against its read budget. The key lives
        only inside the header dict -- no second copy on the instance.
        """
        self._session = session
        self._headers = {"x-api-key": api_key} if api_key else {}

    async def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Perform one GET and return the decoded body.

        Failures are logged at DEBUG only: every caller either reports an
        outage once itself (the coordinators) or turns it into a form error,
        and a line per failed request would flood the log during an outage.
        Never attach the exception chain to the log record: tracebacks can
        carry the API key.
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
            _LOGGER.debug("HTTP %s from %s", err.status, path)
            raise BitpandaApiError(f"HTTP {err.status} from {path}") from None
        except aiohttp.ClientError as err:
            _LOGGER.debug("Connection error for %s: %s", path, type(err).__name__)
            raise BitpandaApiError(f"Connection error for {path}") from None
        except asyncio.TimeoutError:
            _LOGGER.debug("Timeout for %s", path)
            raise BitpandaApiError(f"Timeout for {path}") from None
        except ValueError:
            # json.JSONDecodeError subclasses ValueError, and a body that
            # decodes to text but not JSON can also raise UnicodeDecodeError
            # here, another ValueError subclass — hence the general wording.
            # Without this the exception escapes to Home Assistant's
            # coordinator, whose final handler calls logger.exception() —
            # exc_info=True through this integration's own logger, which is
            # exactly what the API-key rule forbids.
            _LOGGER.debug("Could not decode response from %s", path)
            raise BitpandaApiError(f"Could not decode response from {path}") from None

    async def _paginate(
        self,
        path: str,
        params: dict[str, Any],
        *,
        cursor_fix: Callable[[str], str] | None = None,
    ) -> list[dict]:
        """Collect every page of a cursor-paginated endpoint, or raise.

        Deduplicates by id: pages can overlap by one record. `cursor_fix`
        rewrites each `next_cursor` before it is sent (see
        `normalize_operations_cursor`).

        Never returns a partial listing. A cursor that was already sent means
        the server is re-serving pages it has answered before -- /operations
        does exactly that for cursors it ignores -- so following it loops until
        rate-limited, and stopping there quietly would pass off the pages so
        far as the whole listing. That, a listing longer than _MAX_PAGES, and a
        page that announces another without a cursor all raise instead: a
        failed update is honest, a truncated total published as fact is not.
        """
        params = dict(params)
        params.setdefault("page_size", MAX_PAGE_SIZE)
        out: list[dict] = []
        seen: set[str] = set()
        sent_cursors: set[str] = set()

        for _ in range(_MAX_PAGES):
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
            cursor = body.get("next_cursor")
            if not cursor:
                raise BitpandaApiError(
                    f"{path} announced another page but sent no cursor"
                )
            if cursor_fix is not None:
                cursor = cursor_fix(cursor)
            if cursor in sent_cursors:
                raise BitpandaApiError(
                    f"{path} repeated a page cursor; its listing is incomplete"
                )
            sent_cursors.add(cursor)
            params["cursor"] = cursor

        raise BitpandaApiError(f"{path} returned more than {_MAX_PAGES} pages")

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

        `from` and `to` are undocumented on the hosted docs but work. Every
        cursor goes through `normalize_operations_cursor`: this endpoint emits
        whole-second cursors that it then ignores, which without the rewrite
        stalls or cycles on the first pages.

        Needs the Transaktion (Transaction) scope; a key without it gets 401.
        """
        params: dict[str, Any] = {}
        if from_ts:
            params["from"] = from_ts
        if to_ts:
            params["to"] = to_ts
        return await self._paginate(
            "/operations", params, cursor_fix=normalize_operations_cursor
        )

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
