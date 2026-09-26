"""Tests for the Portfolio service coordinators."""
import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaApiError, BitpandaAuthError
from custom_components.bitpanda.const import DOMAIN, WALLET_REMOVAL_MISSES
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


# The coordinators run here with their update method only: no refresh is
# scheduled and nothing listens. The Portfolio coordinator needs a Home
# Assistant instance and its entry (it keeps the count of empty answers in
# hass.data and looks for registered wallets); the Earn coordinator needs
# neither.


def _entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "portfolio"})
    entry.add_to_hass(hass)
    return entry


def _coordinator(hass, client, directory=None, entry=None) -> PortfolioCoordinator:
    return PortfolioCoordinator(
        hass, entry or _entry(hass), client, "cur-id", directory or _Directory({VSN: _VSN_RECORD})
    )


async def test_portfolio_update_requests_the_portfolio_currency_and_names_holdings(hass):
    client = _Client(_ENTRIES)
    directory = _Directory({VSN: _VSN_RECORD})
    coordinator = _coordinator(hass, client, directory)

    data = await coordinator._async_update_data()

    assert client.currency_ids == ["cur-id"]
    assert directory.resolved == [[VSN]]
    assert data.assets == {VSN: _VSN_RECORD}
    assert data.cash == 5.0
    assert data.wallet_ids == [VSN]


async def test_portfolio_update_keeps_an_unnamed_holding_out_of_assets(hass):
    coordinator = _coordinator(hass, _Client(_ENTRIES), _Directory({}))
    data = await coordinator._async_update_data()
    assert VSN in data.holdings
    assert data.assets == {}


def _translation(err: Exception) -> tuple:
    """What the frontend translates an error from; its English text comes
    from the same entry of strings.json (see test_init.py)."""
    return err.translation_domain, err.translation_key, err.translation_placeholders


async def test_portfolio_401_starts_reauth_with_a_translated_message(hass):
    client = _Client(error=BitpandaAuthError("Unauthorized for /portfolio"))
    coordinator = _coordinator(hass, client, _Directory({}))
    with pytest.raises(ConfigEntryAuthFailed) as excinfo:
        await coordinator._async_update_data()
    assert _translation(excinfo.value) == ("bitpanda", "api_key_rejected", None)
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__


async def test_portfolio_error_fails_the_update_before_any_lookup(hass):
    directory = _Directory({})
    client = _Client(
        error=BitpandaApiError("Timeout for /portfolio", kind="timeout", path="/portfolio")
    )
    coordinator = _coordinator(hass, client, directory)
    with pytest.raises(UpdateFailed) as excinfo:
        await coordinator._async_update_data()
    assert _translation(excinfo.value) == (
        "bitpanda", "update_failed_timeout", {"path": "/portfolio"}
    )
    assert excinfo.value.__cause__ is None
    assert directory.resolved == []


@pytest.mark.parametrize(
    ("kind", "status", "key", "placeholders"),
    [
        ("timeout", None, "update_failed_timeout", {"path": "/portfolio"}),
        ("connection", None, "update_failed_connection", {"path": "/portfolio"}),
        ("http_status", 503, "update_failed_http_status", {"path": "/portfolio", "status": "503"}),
        ("rate_limited", 429, "update_failed_rate_limited", {"path": "/portfolio"}),
        ("unreadable", None, "update_failed_unreadable", {"path": "/portfolio"}),
        ("incomplete_listing", None, "update_failed_incomplete_listing", {"path": "/portfolio"}),
    ],
)
async def test_a_failed_request_is_translated_by_what_failed(hass, kind, status, key, placeholders):
    """One text per kind of failure; the placeholders carry no words -- the
    request path and an HTTP status -- so the whole message is in the
    reader's language. The client's English message never reaches it."""
    client = _Client(
        error=BitpandaApiError("English detail", kind=kind, path="/portfolio", status=status)
    )
    with pytest.raises(UpdateFailed) as excinfo:
        await _coordinator(hass, client)._async_update_data()
    assert _translation(excinfo.value) == ("bitpanda", key, placeholders)
    assert "English detail" not in str(excinfo.value.translation_placeholders)


@pytest.mark.parametrize(
    "error",
    [
        BitpandaApiError("raised without a kind"),
        BitpandaApiError("an HTTP status without one", kind="http_status", path="/portfolio"),
        BitpandaApiError("a kind without a path", kind="timeout"),
    ],
    ids=["no_kind", "no_status", "no_path"],
)
async def test_a_failure_that_says_too_little_gets_the_plain_text(hass, error):
    """Never a text with an empty placeholder, never the English message."""
    with pytest.raises(UpdateFailed) as excinfo:
        await _coordinator(hass, _Client(error=error))._async_update_data()
    assert _translation(excinfo.value) == ("bitpanda", "update_failed", None)


# --- A completely empty /portfolio ----------------------------------------------


def _portfolio(hass, entries=_ENTRIES, entry=None) -> tuple[_Client, PortfolioCoordinator]:
    client = _Client(entries)
    return client, _coordinator(hass, client, entry=entry)


def _register_wallet(hass, entry) -> None:
    """A wallet of `entry` in the entity registry: the account listed
    something before this coordinator's time -- before a restart or a
    reload."""
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_wallet_{VSN}", config_entry=entry
    )


async def _refused(coordinator: PortfolioCoordinator) -> None:
    with pytest.raises(UpdateFailed) as excinfo:
        await coordinator._async_update_data()
    assert _translation(excinfo.value) == ("bitpanda", "portfolio_empty", None)


async def test_an_empty_first_answer_of_a_new_account_is_the_truth(hass):
    """No wallet registered: a new, empty account, whose setup must work."""
    _, coordinator = _portfolio(hass, [])
    data = await coordinator._async_update_data()
    assert data.holdings == {}
    assert data.total == 0.0


async def test_an_empty_first_answer_waits_while_wallets_are_registered(hass):
    """After a restart or a reload of an account that listed something, an
    empty first answer counts like any sudden empty answer."""
    entry = _entry(hass)
    _register_wallet(hass, entry)
    _, coordinator = _portfolio(hass, [], entry)
    for _ in range(WALLET_REMOVAL_MISSES - 1):
        await _refused(coordinator)
    assert (await coordinator._async_update_data()).total == 0.0


async def test_the_count_of_empty_answers_goes_on_across_coordinators(hass):
    """A reload, or a setup that is retried, starts a new coordinator: the
    count does not start over with it."""
    entry = _entry(hass)
    _register_wallet(hass, entry)
    for _ in range(WALLET_REMOVAL_MISSES - 1):
        await _refused(_portfolio(hass, [], entry)[1])
    assert (await _portfolio(hass, [], entry)[1]._async_update_data()).total == 0.0


async def test_an_answer_taken_as_the_truth_clears_the_count(hass):
    entry = _entry(hass)
    _register_wallet(hass, entry)
    await _refused(_portfolio(hass, [], entry)[1])
    await _portfolio(hass, _ENTRIES, entry)[1]._async_update_data()
    _, coordinator = _portfolio(hass, [], entry)
    for _ in range(WALLET_REMOVAL_MISSES - 1):
        await _refused(coordinator)


async def test_a_sudden_empty_answer_fails_until_answers_in_a_row_confirm_it(hass):
    """A Bitpanda glitch must not read as a sale of everything. The answer
    that makes WALLET_REMOVAL_MISSES empty ones in a row is the truth, and
    so is every empty one after it."""
    client, coordinator = _portfolio(hass)
    await coordinator._async_update_data()
    client.entries = []
    for _ in range(WALLET_REMOVAL_MISSES - 1):
        await _refused(coordinator)
    assert (await coordinator._async_update_data()).total == 0.0
    assert (await coordinator._async_update_data()).total == 0.0


async def test_an_answer_that_lists_something_starts_the_count_again(hass):
    client, coordinator = _portfolio(hass)
    await coordinator._async_update_data()
    client.entries = []
    await _refused(coordinator)
    client.entries = _ENTRIES
    await coordinator._async_update_data()
    client.entries = []
    for _ in range(WALLET_REMOVAL_MISSES - 1):
        await _refused(coordinator)


async def test_a_failed_request_neither_counts_nor_resets_the_empty_answers(hass):
    client, coordinator = _portfolio(hass)
    await coordinator._async_update_data()
    client.entries = []
    for _ in range(WALLET_REMOVAL_MISSES - 1):
        client.error = BitpandaApiError("Timeout for /portfolio")
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        client.error = None
        await _refused(coordinator)
    assert (await coordinator._async_update_data()).total == 0.0


async def test_only_a_fiat_entry_is_not_an_empty_answer(hass):
    client, coordinator = _portfolio(hass)
    await coordinator._async_update_data()
    client.entries = [{"currency_id": EUR_ID, "balance": {"value": "5.00"}}]
    assert (await coordinator._async_update_data()).total == 5.0


async def test_only_entries_of_no_known_shape_are_an_empty_answer(hass):
    """parse_portfolio ignores an entry with neither asset_id nor
    currency_id, the same as one that never existed."""
    client, coordinator = _portfolio(hass)
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
    error = BitpandaApiError(
        "HTTP 503 from /earn/configs", kind="http_status", path="/earn/configs", status=503
    )
    coordinator = EarnCoordinator(None, None, _EarnClient(error=error))
    with pytest.raises(UpdateFailed) as excinfo:
        await coordinator._async_update_data()
    assert _translation(excinfo.value) == (
        "bitpanda", "update_failed_http_status", {"path": "/earn/configs", "status": "503"}
    )
