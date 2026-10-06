"""The client can run without a key for the public endpoints."""
import asyncio

from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda.api import BitpandaApiClient
from custom_components.bitpanda.const import API_BASE_URL


async def _ticker_headers(api_key):
    with mock_aiohttp_client() as mocker:
        mocker.get(f"{API_BASE_URL}/tickers/uuid-btc", json={"data": {"price": "1.00000000"}})
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            await BitpandaApiClient(api_key, session).async_get_ticker("uuid-btc")
    # AiohttpClientMocker records (method, url, data, headers).
    return mocker.mock_calls[0][3] or {}


async def test_keyless_client_sends_no_key_header():
    headers = await _ticker_headers(None)
    assert "x-api-key" not in {name.lower() for name in headers}


async def test_keyed_client_still_sends_its_key():
    assert (await _ticker_headers("key"))["x-api-key"] == "key"


def test_client_keeps_no_second_copy_of_the_key():
    client = BitpandaApiClient("secret", None)
    assert not hasattr(client, "_api_key")
