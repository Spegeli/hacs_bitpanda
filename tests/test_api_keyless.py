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


class _Answer:
    """A 200 answer holding one record."""

    status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    def raise_for_status(self):
        pass

    async def json(self):
        return {"data": {"price": "1.00000000"}}


class _TimingSession:
    """Answers every GET and notes how long each one may take."""

    closed = False

    def __init__(self):
        self.waits = {}

    def get(self, url, **kwargs):
        self.waits[url.removeprefix(API_BASE_URL)] = kwargs["timeout"].total
        return _Answer()


async def test_a_price_request_gives_up_after_five_seconds():
    """A ticker answers in well under a second; one that hangs holds up the
    whole round of prices, so it is given up on after 5 seconds. Every other
    request keeps 15: a history or a page of operations may take longer."""
    session = _TimingSession()
    client = BitpandaApiClient(None, session)
    await client.async_get_ticker("uuid-btc")
    await client.async_get_portfolio_history(timeframe="DAY")
    assert session.waits == {"/tickers/uuid-btc": 5, "/portfolio-history": 15}
