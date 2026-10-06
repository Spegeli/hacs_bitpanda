"""Tests for the ECB daily reference rates."""
import asyncio
from pathlib import Path

import aiohttp
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda.const import ECB_RATES_URL
from custom_components.bitpanda.ecb import (
    EcbError,
    EcbRates,
    async_fetch_ecb_rates,
    parse_ecb_rates,
)

_XML = (Path(__file__).parent / "fixtures" / "ecb-daily.xml").read_bytes()


def test_parse_reads_date_and_rates():
    rates = parse_ecb_rates(_XML)
    assert rates == EcbRates(
        date="2026-09-24",
        rates={"USD": 1.1367, "JPY": 171.53, "CHF": 0.9357, "GBP": 0.8621},
    )


def test_parse_accepts_text_as_well_as_bytes():
    assert parse_ecb_rates(_XML.decode("utf-8")).rates["USD"] == 1.1367


def test_parse_skips_an_unreadable_or_non_positive_rate():
    document = _XML.replace(b"rate='171.53'", b"rate='n/a'").replace(
        b"rate='0.9357'", b"rate='0'"
    )
    assert set(parse_ecb_rates(document).rates) == {"USD", "GBP"}


def _what_failed(err: EcbError) -> tuple:
    """What a failure says without words, for its translated message: its
    kind and an HTTP status."""
    return err.kind, err.status


@pytest.mark.parametrize(
    "document",
    [
        b"<not xml",
        _XML.replace(b"time='2026-09-24'", b"day='2026-09-24'"),
        _XML.replace(b"currency=", b"kind="),
    ],
    ids=["invalid_xml", "no_rate_date", "no_rates"],
)
def test_parse_rejects_a_document_it_cannot_read(document):
    with pytest.raises(EcbError) as excinfo:
        parse_ecb_rates(document)
    assert _what_failed(excinfo.value) == ("unreadable", None)


async def test_fetch_returns_parsed_rates():
    with mock_aiohttp_client() as mocker:
        mocker.get(ECB_RATES_URL, content=_XML)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            rates = await async_fetch_ecb_rates(session)
    assert rates.date == "2026-09-24"


async def test_fetch_maps_http_errors():
    with mock_aiohttp_client() as mocker:
        mocker.get(ECB_RATES_URL, status=503)
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            with pytest.raises(EcbError, match="503") as excinfo:
                await async_fetch_ecb_rates(session)
    assert _what_failed(excinfo.value) == ("http_status", 503)


async def test_fetch_maps_a_timeout():
    with mock_aiohttp_client() as mocker:
        mocker.get(ECB_RATES_URL, exc=asyncio.TimeoutError())
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            with pytest.raises(EcbError, match="Timeout") as excinfo:
                await async_fetch_ecb_rates(session)
    assert _what_failed(excinfo.value) == ("timeout", None)


async def test_fetch_maps_a_connection_error_by_its_type_alone():
    with mock_aiohttp_client() as mocker:
        mocker.get(ECB_RATES_URL, exc=aiohttp.ClientConnectionError("details of the request"))
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            with pytest.raises(EcbError) as excinfo:
                await async_fetch_ecb_rates(session)
    assert str(excinfo.value) == "Connection error for the ECB rates: ClientConnectionError"
    assert _what_failed(excinfo.value) == ("connection", None)
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__


async def test_fetch_maps_an_unreadable_answer():
    with mock_aiohttp_client() as mocker:
        mocker.get(ECB_RATES_URL, content=b"<html>maintenance</html>")
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            with pytest.raises(EcbError) as excinfo:
                await async_fetch_ecb_rates(session)
    assert _what_failed(excinfo.value) == ("unreadable", None)
