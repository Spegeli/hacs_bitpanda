"""Tests for the Portfolio service coordinators."""
import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.bitpanda.api import BitpandaApiError, BitpandaAuthError
from custom_components.bitpanda.const import WALLET_REMOVAL_MISSES
from custom_components.bitpanda.portfolio_coordinator import (
    EarnCoordinator,
    PortfolioCoordinator,
)
from custom_components.bitpanda.portfolio_model import EarnData

VSN = "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb"
EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"
_ENTRIES = [
    {
        "asset_id": VSN,
        "balance": {"value": "10.00000000"},
        "available_balance": {"value": "4.00000000"},
        "currency_balance": {"value": "20.00"},
    },
    {"currency_id": EUR_ID, "balance": {"value": "5.00"}},
]
_VSN_RECORD = {"id": VSN, "symbol": "VSN", "name": "Vision", "group": "token"}


class _Client:
    def __init__(self, entries=None, error=None):
        self.entries = entries or []
        self.error = error
        self.currency_ids: list = []

    async def async_get_portfolio(self, *, equivalent_currency_id=None):
        self.currency_ids.append(equivalent_currency_id)
        if self.error:
            raise self.error
        return self.entries


class _Directory:
    def __init__(self, records):
        self.records = records
        self.resolved: list = []

    async def async_resolve(self, asset_ids):
        self.resolved.append(list(asset_ids))

    def get(self, asset_id):
        return self.records.get(asset_id)


class _EarnClient:
    def __init__(self, configs=None, error=None):
        self.configs = configs or []
        self.error = error

    async def async_get_earn_configs(self):
        if self.error:
            raise self.error
        return self.configs


# DataUpdateCoordinator only stores hass and the entry at construction, so the
# coordinators run here without a Home Assistant instance, update method only.


async def test_portfolio_update_requests_the_portfolio_currency_and_names_holdings():
    client = _Client(_ENTRIES)
    directory = _Directory({VSN: _VSN_RECORD})
    coordinator = PortfolioCoordinator(None, None, client, "cur-id", directory)

    data = await coordinator._async_update_data()

    assert client.currency_ids == ["cur-id"]
    assert directory.resolved == [[VSN]]
    assert data.assets == {VSN: _VSN_RECORD}
    assert data.cash == 5.0
    assert data.wallet_ids == [VSN]


async def test_portfolio_update_keeps_an_unnamed_holding_out_of_assets():
    coordinator = PortfolioCoordinator(None, None, _Client(_ENTRIES), "c", _Directory({}))
    data = await coordinator._async_update_data()
    assert VSN in data.holdings
    assert data.assets == {}


def _translation(err: Exception) -> tuple:
    """What the frontend translates an error from; its English text comes
    from the same entry of strings.json (see test_init.py)."""
    return err.translation_domain, err.translation_key, err.translation_placeholders


async def test_portfolio_401_starts_reauth_with_a_translated_message():
    client = _Client(error=BitpandaAuthError("Unauthorized for /portfolio"))
    coordinator = PortfolioCoordinator(None, None, client, "c", _Directory({}))
    with pytest.raises(ConfigEntryAuthFailed) as excinfo:
        await coordinator._async_update_data()
    assert _translation(excinfo.value) == ("bitpanda", "api_key_rejected", None)
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__


async def test_portfolio_error_fails_the_update_before_any_lookup():
    directory = _Directory({})
    client = _Client(error=BitpandaApiError("Timeout for /portfolio"))
    coordinator = PortfolioCoordinator(None, None, client, "c", directory)
    with pytest.raises(UpdateFailed) as excinfo:
        await coordinator._async_update_data()
    assert _translation(excinfo.value) == (
        "bitpanda", "update_failed", {"error": "Timeout for /portfolio"}
    )
    assert excinfo.value.__cause__ is None
    assert directory.resolved == []


# --- A completely empty /portfolio ----------------------------------------------


def _portfolio(entries=_ENTRIES) -> tuple[_Client, PortfolioCoordinator]:
    client = _Client(entries)
    return client, PortfolioCoordinator(None, None, client, "c", _Directory({VSN: _VSN_RECORD}))


async def _refused(coordinator: PortfolioCoordinator) -> None:
    with pytest.raises(UpdateFailed) as excinfo:
        await coordinator._async_update_data()
    assert _translation(excinfo.value) == ("bitpanda", "portfolio_empty", None)


async def test_an_empty_first_answer_is_the_truth():
    """A new, empty account: setup must work."""
    _, coordinator = _portfolio([])
    data = await coordinator._async_update_data()
    assert data.holdings == {}
    assert data.total == 0.0


async def test_a_sudden_empty_answer_fails_until_answers_in_a_row_confirm_it():
    """A Bitpanda glitch must not read as a sale of everything. The answer
    that makes WALLET_REMOVAL_MISSES empty ones in a row is the truth, and
    so is every empty one after it."""
    client, coordinator = _portfolio()
    await coordinator._async_update_data()
    client.entries = []
    for _ in range(WALLET_REMOVAL_MISSES - 1):
        await _refused(coordinator)
    assert (await coordinator._async_update_data()).total == 0.0
    assert (await coordinator._async_update_data()).total == 0.0


async def test_an_answer_that_lists_something_starts_the_count_again():
    client, coordinator = _portfolio()
    await coordinator._async_update_data()
    client.entries = []
    await _refused(coordinator)
    client.entries = _ENTRIES
    await coordinator._async_update_data()
    client.entries = []
    for _ in range(WALLET_REMOVAL_MISSES - 1):
        await _refused(coordinator)


async def test_a_failed_request_neither_counts_nor_resets_the_empty_answers():
    client, coordinator = _portfolio()
    await coordinator._async_update_data()
    client.entries = []
    for _ in range(WALLET_REMOVAL_MISSES - 1):
        client.error = BitpandaApiError("Timeout for /portfolio")
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        client.error = None
        await _refused(coordinator)
    assert (await coordinator._async_update_data()).total == 0.0


async def test_only_a_fiat_entry_is_not_an_empty_answer():
    client, coordinator = _portfolio()
    await coordinator._async_update_data()
    client.entries = [{"currency_id": EUR_ID, "balance": {"value": "5.00"}}]
    assert (await coordinator._async_update_data()).total == 5.0


async def test_only_entries_of_no_known_shape_are_an_empty_answer():
    """parse_portfolio ignores an entry with neither asset_id nor
    currency_id, the same as one that never existed."""
    client, coordinator = _portfolio()
    await coordinator._async_update_data()
    client.entries = [{"something": "else"}]
    await _refused(coordinator)


async def test_earn_update_returns_the_catalogue():
    configs = [{"asset_id": VSN, "annual_percentage_rate": 0.05, "enabled": True}]
    coordinator = EarnCoordinator(None, None, _EarnClient(configs))
    assert await coordinator._async_update_data() == EarnData(
        apr={VSN: 0.05}, offered=frozenset({VSN})
    )


async def test_earn_401_starts_reauth():
    coordinator = EarnCoordinator(None, None, _EarnClient(error=BitpandaAuthError("x")))
    with pytest.raises(ConfigEntryAuthFailed) as excinfo:
        await coordinator._async_update_data()
    assert _translation(excinfo.value) == ("bitpanda", "api_key_rejected", None)


async def test_earn_error_fails_the_update():
    coordinator = EarnCoordinator(
        None, None, _EarnClient(error=BitpandaApiError("HTTP 503 from /earn/configs"))
    )
    with pytest.raises(UpdateFailed) as excinfo:
        await coordinator._async_update_data()
    assert _translation(excinfo.value) == (
        "bitpanda", "update_failed", {"error": "HTTP 503 from /earn/configs"}
    )
