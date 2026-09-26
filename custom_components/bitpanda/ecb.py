"""European Central Bank daily reference rates.

The Price Tracker converts Bitpanda's EUR ticker prices into other currencies
with these rates. The ECB publishes them once per working day around 16:00
CET; weekends and holidays carry the last working day's rates.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import math
import xml.etree.ElementTree as ET

import aiohttp

from .const import (
    API_TIMEOUT,
    ECB_RATES_URL,
    ERROR_CONNECTION,
    ERROR_HTTP_STATUS,
    ERROR_TIMEOUT,
    ERROR_UNREADABLE,
)

_NS = {"eurofxref": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}


class EcbError(Exception):
    """The ECB rates could not be fetched or read.

    The message is English, for the log. What failed is carried without
    words too, for a translated text (price_coordinator._ecb_failed):
    `kind`, one of const.API_ERROR_KINDS, and `status`, the HTTP status of
    an ERROR_HTTP_STATUS.
    """

    def __init__(
        self, message: str, *, kind: str | None = None, status: int | None = None
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status = status


@dataclass(frozen=True)
class EcbRates:
    """One day's reference rates: units of each currency per 1 EUR."""

    date: str
    rates: dict[str, float]


def parse_ecb_rates(document: str | bytes) -> EcbRates:
    """Read eurofxref-daily.xml. A rate that is not a positive number is skipped."""
    try:
        root = ET.fromstring(document)
    except ET.ParseError:
        raise EcbError("The ECB response is not valid XML", kind=ERROR_UNREADABLE) from None
    day = root.find(".//eurofxref:Cube[@time]", _NS)
    if day is None:
        raise EcbError("The ECB response carries no rate date", kind=ERROR_UNREADABLE)
    rates: dict[str, float] = {}
    for cube in day.findall("eurofxref:Cube[@currency]", _NS):
        try:
            rate = float(cube.get("rate", ""))
        except ValueError:
            continue
        if math.isfinite(rate) and rate > 0:
            rates[cube.get("currency")] = rate
    if not rates:
        raise EcbError("The ECB response carries no rates", kind=ERROR_UNREADABLE)
    return EcbRates(date=day.get("time"), rates=rates)


async def async_fetch_ecb_rates(session: aiohttp.ClientSession) -> EcbRates:
    """Fetch and parse today's rates. Every failure is an EcbError."""
    try:
        async with session.get(
            ECB_RATES_URL, timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
        ) as response:
            response.raise_for_status()
            document = await response.read()
    except aiohttp.ClientResponseError as err:
        raise EcbError(
            f"HTTP {err.status} from the ECB", kind=ERROR_HTTP_STATUS, status=err.status
        ) from None
    except aiohttp.ClientError as err:
        raise EcbError(
            f"Connection error for the ECB rates: {type(err).__name__}", kind=ERROR_CONNECTION
        ) from None
    except asyncio.TimeoutError:
        raise EcbError("Timeout fetching the ECB rates", kind=ERROR_TIMEOUT) from None
    return parse_ecb_rates(document)
