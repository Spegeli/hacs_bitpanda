"""Tests for earn configs and operations."""
import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.bitpanda.api import BitpandaApiClient, BitpandaAuthError
from custom_components.bitpanda.const import API_BASE_URL


async def test_get_earn_configs_paginates():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/earn/configs?page_size=100",
                payload={
                    "data": [{"id": "c1", "asset_id": "a1",
                              "annual_percentage_rate": 0.0544}],
                    "next_cursor": "CUR",
                    "has_next_page": True,
                },
            )
            m.get(
                f"{API_BASE_URL}/earn/configs?cursor=CUR&page_size=100",
                payload={
                    "data": [{"id": "c2", "asset_id": "a2",
                              "annual_percentage_rate": 0.07}],
                    "has_next_page": False,
                },
            )
            result = await client.async_get_earn_configs()
    assert [c["id"] for c in result] == ["c1", "c2"]
    assert result[0]["annual_percentage_rate"] == 0.0544


async def test_get_operations_uses_date_window():
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/operations?from=2026-09-01T00%3A00%3A00Z&page_size=100",
                payload={
                    "data": [{"operation_id": "o1", "operation_type": "reward"}],
                    "has_next_page": False,
                },
            )
            result = await client.async_get_operations(from_ts="2026-09-01T00:00:00Z")
    assert result[0]["operation_id"] == "o1"


async def test_get_operations_uses_both_date_bounds():
    """`from_ts`/`to_ts` are Python names; the wire names are bare `from`/`to`."""
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/operations"
                f"?from=2025-01-01T00%3A00%3A00Z"
                f"&page_size=100"
                f"&to=2025-03-31T23%3A59%3A59Z",
                payload={
                    "data": [{"operation_id": "o1"}],
                    "has_next_page": False,
                },
            )
            result = await client.async_get_operations(
                from_ts="2025-01-01T00:00:00Z", to_ts="2025-03-31T23:59:59Z"
            )
    assert result[0]["operation_id"] == "o1"


async def test_get_operations_deduplicates_overlapping_pages():
    """Pages overlap by one record, so the same id can arrive twice."""
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(
                f"{API_BASE_URL}/operations?page_size=100",
                payload={
                    "data": [{"operation_id": "o1"}, {"operation_id": "o2"}],
                    "next_cursor": "CUR",
                    "has_next_page": True,
                },
            )
            m.get(
                f"{API_BASE_URL}/operations?cursor=CUR&page_size=100",
                payload={
                    "data": [{"operation_id": "o2"}, {"operation_id": "o3"}],
                    "has_next_page": False,
                },
            )
            result = await client.async_get_operations()
    assert [o["operation_id"] for o in result] == ["o1", "o2", "o3"]


async def test_operations_401_raises_auth_error():
    """A portfolio-capable key is not sufficient for /operations."""
    async with aiohttp.ClientSession() as session:
        client = BitpandaApiClient("key", session)
        with aioresponses() as m:
            m.get(f"{API_BASE_URL}/operations?page_size=100", status=401)
            with pytest.raises(BitpandaAuthError):
                await client.async_get_operations()
