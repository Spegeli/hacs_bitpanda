"""Tests for the Portfolio service coordinators."""
from datetime import timedelta
import logging

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.api import BitpandaApiError, BitpandaAuthError
from custom_components.bitpanda.const import (
    DOMAIN,
    EARN_UPDATE_INTERVAL,
    FIRST_LOAD_RETRY_INTERVAL,
    PORTFOLIO_UPDATE_INTERVAL,
    WALLET_REMOVAL_MISSES,
)
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

    def is_unlisted(self, asset_id):
        return False


class _EarnClient:
    def __init__(self, configs=None, error=None):
        self.configs = configs or []
        self.error = error

    async def async_get_earn_configs(self):
        if self.error:
            raise self.error
        return self.configs


# The coordinators run here with their update method only: no refresh is
# scheduled and nothing listens. The Portfolio coordinator is built as setup
# builds it, with a Home Assistant instance and its entry; the Earn
# coordinator, with neither.


def _entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "portfolio"})
    entry.add_to_hass(hass)
    return entry


def _coordinator(hass, client, directory=None) -> PortfolioCoordinator:
    return PortfolioCoordinator(
        hass, _entry(hass), client, "cur-id", directory or _Directory({VSN: _VSN_RECORD})
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


# --- A Portfolio figure whose entry vanishes ------------------------------------


def _portfolio(hass, entries=_ENTRIES) -> tuple[_Client, PortfolioCoordinator]:
    client = _Client(entries)
    return client, _coordinator(hass, client)


# Every successful answer is taken as it is. A figure whose entry the answers
# no longer list waits (PortfolioData.waiting) until WALLET_REMOVAL_MISSES of
# them in a row span the time the regular pace takes for them: two update
# intervals from the first. Home Assistant's clock is frozen here (freezer),
# and moves on by one update interval before each regular answer -- by a
# cooldown before each answer brought by hand (bitpanda.refresh).
_REGULAR = PORTFOLIO_UPDATE_INTERVAL
_BY_HAND = timedelta(seconds=20)


async def test_figures_missing_from_the_first_answer_do_not_wait(hass):
    """No fiat entry in the first answer: nothing vanished, so Cash shows 0
    at once and nothing waits."""
    _, coordinator = _portfolio(hass, [_ENTRIES[0]])
    data = await coordinator._async_update_data()
    assert data.waiting == frozenset()
    assert data.cash == 0.0


async def test_an_empty_first_answer_of_a_new_account_is_the_truth(hass):
    """A new, empty account, whose setup must work: every figure 0 at once."""
    _, coordinator = _portfolio(hass, [])
    data = await coordinator._async_update_data()
    assert data.holdings == {}
    assert data.total == 0.0
    assert data.waiting == frozenset()


async def test_an_empty_answer_is_the_truth_at_once(hass, freezer):
    """No failed update: the answer is taken as it is, and Total value and
    Cash, whose entries it no longer lists, wait. Cash Plus was never
    there."""
    client, coordinator = _portfolio(hass)
    await coordinator._async_update_data()
    client.entries = []
    freezer.tick(_REGULAR)
    data = await coordinator._async_update_data()
    assert data.total == 0.0
    assert data.waiting == {"total", "cash"}


async def test_vanished_fiat_makes_cash_wait_three_answers(hass, freezer):
    """All fiat withdrawn, the holding kept: Cash waits through two answers
    and shows 0 with the third, ten minutes after the first, while Total
    value follows the answer at once."""
    client, coordinator = _portfolio(hass)
    await coordinator._async_update_data()
    client.entries = [_ENTRIES[0]]
    for _ in range(2):
        freezer.tick(_REGULAR)
        data = await coordinator._async_update_data()
        assert data.waiting == {"cash"}
        assert data.total == 20.0
    freezer.tick(_REGULAR)
    data = await coordinator._async_update_data()
    assert data.waiting == frozenset()
    assert data.cash == 0.0


async def test_a_failed_request_while_cash_waits_neither_counts_nor_clears(hass, freezer):
    """Failed requests go through the failure tolerance alone -- here three
    in a row, as many as end it at the regular pace. The next answer without
    fiat is only the second miss, still waiting although the first was asked
    for long ago, and the one after it the third, which shows 0."""
    client, coordinator = _portfolio(hass)
    await coordinator._async_update_data()
    client.entries = [_ENTRIES[0]]
    freezer.tick(_REGULAR)
    assert (await coordinator._async_update_data()).waiting == {"cash"}
    for _ in range(3):
        freezer.tick(_REGULAR)
        client.error = BitpandaApiError("Timeout for /portfolio")
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
    client.error = None
    freezer.tick(_REGULAR)
    assert (await coordinator._async_update_data()).waiting == {"cash"}
    freezer.tick(_REGULAR)
    assert (await coordinator._async_update_data()).waiting == frozenset()


async def test_an_unreadable_fiat_entry_while_cash_waits_clears_the_count(hass, freezer):
    """A fiat entry that cannot be read is a fiat entry all the same, only
    its amount in doubt: Cash is there -- unknown, nothing waits -- and the
    next answer without fiat starts the count afresh."""
    client, coordinator = _portfolio(hass)
    await coordinator._async_update_data()
    client.entries = [_ENTRIES[0]]
    freezer.tick(_REGULAR)
    assert (await coordinator._async_update_data()).waiting == {"cash"}
    client.entries = [_ENTRIES[0], {"currency_id": EUR_ID, "balance": {"value": "x"}}]
    freezer.tick(_REGULAR)
    data = await coordinator._async_update_data()
    assert data.waiting == frozenset()
    assert data.cash is None
    client.entries = [_ENTRIES[0]]
    for _ in range(2):
        freezer.tick(_REGULAR)
        assert (await coordinator._async_update_data()).waiting == {"cash"}
    freezer.tick(_REGULAR)
    assert (await coordinator._async_update_data()).waiting == frozenset()


_BCPEUR = "1edf9721-e545-644c-9796-ae5b69a774d7"
_BCPEUR_RECORD = {"id": _BCPEUR, "symbol": "BCPEUR", "name": "Cash Plus", "group": "fiat_earn"}
_CASH_PLUS = {
    "asset_id": _BCPEUR,
    "balance": {"value": "50.00000000"},
    "available_balance": {"value": "50.00000000"},
    "currency_balance": {"value": "50.00"},
}
# A holding the directory has no record of: it might be Cash Plus.
_UNCLASSIFIED = {**_CASH_PLUS, "asset_id": "unclassified-asset-id"}


async def test_doubt_about_cash_plus_while_it_waits_clears_the_count(hass, freezer):
    """A holding no record classifies yet might be the Cash Plus that
    vanished: no miss, and the count starts afresh -- Cash Plus unknown,
    nothing waits. Cash Plus was there before, so the answers without it
    after the doubt wait again, from the first."""
    client = _Client([*_ENTRIES, _CASH_PLUS])
    coordinator = _coordinator(
        hass, client, _Directory({VSN: _VSN_RECORD, _BCPEUR: _BCPEUR_RECORD})
    )
    await coordinator._async_update_data()
    client.entries = _ENTRIES
    freezer.tick(_REGULAR)
    assert (await coordinator._async_update_data()).waiting == {"cash_plus"}
    client.entries = [*_ENTRIES, _UNCLASSIFIED]
    freezer.tick(_REGULAR)
    data = await coordinator._async_update_data()
    assert data.waiting == frozenset()
    assert data.cash_plus is None
    client.entries = _ENTRIES
    for _ in range(2):
        freezer.tick(_REGULAR)
        assert (await coordinator._async_update_data()).waiting == {"cash_plus"}
    freezer.tick(_REGULAR)
    assert (await coordinator._async_update_data()).waiting == frozenset()


async def test_a_change_of_the_waiting_figures_is_logged(hass, freezer, caplog):
    """For whoever wonders why Cash shows unavailable: each change of the
    waiting figures is one debug line, and none follows while nothing
    changes."""
    caplog.set_level(logging.DEBUG, logger="custom_components.bitpanda.portfolio_coordinator")
    client, coordinator = _portfolio(hass)
    await coordinator._async_update_data()
    client.entries = [_ENTRIES[0]]
    for _ in range(WALLET_REMOVAL_MISSES + 1):
        freezer.tick(PORTFOLIO_UPDATE_INTERVAL)
        await coordinator._async_update_data()
    assert [
        record.getMessage()
        for record in caplog.records
        if record.getMessage().startswith("Portfolio figures missing")
    ] == [
        "Portfolio figures missing from Bitpanda's answer, unavailable until confirmed: cash",
        "Portfolio figures missing from Bitpanda's answer, unavailable until confirmed: none",
    ]


async def test_misses_by_hand_never_end_the_wait_sooner(hass, freezer):
    """Answers by hand come far faster than the regular pace. However many
    there are, Cash waits until ten minutes have passed since the first
    miss; the first answer then shows 0."""
    client, coordinator = _portfolio(hass)
    await coordinator._async_update_data()
    client.entries = [_ENTRIES[0]]
    freezer.tick(_REGULAR)
    assert (await coordinator._async_update_data()).waiting == {"cash"}
    for _ in range(5):
        freezer.tick(_BY_HAND)
        assert (await coordinator._async_update_data()).waiting == {"cash"}
    freezer.tick(2 * _REGULAR - 5 * _BY_HAND)
    assert (await coordinator._async_update_data()).waiting == frozenset()


async def test_only_a_fiat_entry_is_not_an_empty_answer(hass):
    """Everything sold, the money kept: Total value -- whose entry is any
    entry at all -- is the cash at once, and nothing waits."""
    client, coordinator = _portfolio(hass)
    await coordinator._async_update_data()
    client.entries = [{"currency_id": EUR_ID, "balance": {"value": "5.00"}}]
    data = await coordinator._async_update_data()
    assert data.total == 5.0
    assert data.waiting == frozenset()


async def test_only_entries_of_no_known_shape_are_an_empty_answer(hass):
    """parse_portfolio ignores an entry with neither asset_id nor
    currency_id, the same as one that never existed: Total value and Cash
    wait as after any empty answer."""
    client, coordinator = _portfolio(hass)
    await coordinator._async_update_data()
    client.entries = [{"something": "else"}]
    assert (await coordinator._async_update_data()).waiting == {"total", "cash"}


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


async def test_earn_is_retried_sooner_until_it_first_loads():
    """Until the Earn catalogue first loads, no Staking sensor shows its APR,
    so a failure then is retried after 15 minutes, not after a day. Once it
    loaded, a failure keeps the daily interval: the last catalogue stays."""
    error = BitpandaApiError(
        "HTTP 503 from /earn/configs", kind="http_status", path="/earn/configs", status=503
    )
    client = _EarnClient(error=error)
    coordinator = EarnCoordinator(None, None, client)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator.update_interval == FIRST_LOAD_RETRY_INTERVAL
    client.error = None
    coordinator.data = await coordinator._async_update_data()
    assert coordinator.update_interval == EARN_UPDATE_INTERVAL
    client.error = error
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator.update_interval == EARN_UPDATE_INTERVAL
