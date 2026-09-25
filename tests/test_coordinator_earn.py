"""Tests for earn APR mapping and reward aggregation."""
import asyncio
import base64

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client

from custom_components.bitpanda.api import (
    BitpandaApiClient,
    BitpandaApiError,
    BitpandaAuthError,
)
from custom_components.bitpanda.const import API_BASE_URL, DOMAIN
from custom_components.bitpanda.coordinator import (
    EarnCoordinator,
    Holding,
    PortfolioData,
    RewardsCoordinator,
    _is_later,
    map_earn_configs,
    sum_rewards,
)
from custom_components.bitpanda.sensor import BitpandaWalletSensor


def _reward(asset_id, gross, fee, credited_at, owner="staking-service"):
    return {
        "operation_id": f"op-{credited_at}-{asset_id}",
        "operation_type": "reward",
        "transactions": [
            {
                "asset_id": asset_id,
                "wallet_owner": owner,
                "asset_amount": {"value": gross},
                "fee_amount": {"value": fee},
                "credited_at": credited_at,
            }
        ],
    }


def test_map_earn_configs_keys_by_asset():
    configs = [
        {"asset_id": "a1", "annual_percentage_rate": 0.0544, "enabled": True,
         "soldout": False},
        {"asset_id": "a2", "annual_percentage_rate": 0.07, "enabled": True,
         "soldout": False},
    ]
    assert map_earn_configs(configs) == {"a1": 0.0544, "a2": 0.07}


def test_map_earn_configs_keeps_soldout_products():
    """soldout and enabled are separate flags; a soldout product still has a rate."""
    configs = [{"asset_id": "a1", "annual_percentage_rate": 0.0857,
                "enabled": True, "soldout": True}]
    assert map_earn_configs(configs) == {"a1": 0.0857}


def test_sum_rewards_totals_gross_fee_and_net():
    ops = [
        _reward("vsn", "20.68994769", "4.13798954", "2026-09-22T17:16:35Z"),
        _reward("vsn", "20.67399483", "4.13479897", "2026-09-15T17:16:25Z"),
    ]
    totals = sum_rewards(ops)["vsn"]
    assert abs(totals.gross - 41.36394252) < 1e-8
    assert abs(totals.fee - 8.27278851) < 1e-8
    assert abs(totals.net - (41.36394252 - 8.27278851)) < 1e-8
    assert totals.count == 2


def test_sum_rewards_rounds_to_eight_decimals():
    """Summing floats leaves noise such as 751.4920099999999 or
    0.30000000000000004; the amounts come from 8-decimal strings.
    """
    ops = [
        _reward("vsn", "0.1", "0.01", "2026-09-15T17:16:25Z"),
        _reward("vsn", "0.2", "0.02", "2026-09-22T17:16:35Z"),
    ]
    totals = sum_rewards(ops)["vsn"]
    assert totals.gross == 0.3
    assert totals.fee == 0.03
    assert totals.net == 0.27


def test_sum_rewards_records_latest_timestamp():
    ops = [
        _reward("vsn", "1", "0", "2026-09-15T17:16:25Z"),
        _reward("vsn", "1", "0", "2026-09-22T17:16:35Z"),
    ]
    assert sum_rewards(ops)["vsn"].last_at == "2026-09-22T17:16:35Z"


def test_sum_rewards_ignores_non_reward_operations():
    ops = [
        _reward("vsn", "1", "0", "2026-09-22T17:16:35Z"),
        {"operation_id": "o2", "operation_type": "buy",
         "transactions": [{"asset_id": "vsn", "asset_amount": {"value": "999"},
                           "fee_amount": {"value": "0"},
                           "credited_at": "2026-09-01T00:00:00Z"}]},
    ]
    assert sum_rewards(ops)["vsn"].gross == 1.0


def test_sum_rewards_ignores_cash_plus_interest():
    """earn_on_fiat_reward is Cash Plus interest, a different product."""
    ops = [{"operation_id": "o1", "operation_type": "earn_on_fiat_reward",
            "transactions": [{"asset_id": "eur", "wallet_owner": "shared-default",
                              "asset_amount": {"value": "0.01"},
                              "fee_amount": {"value": "0"},
                              "credited_at": "2026-01-05T17:46:04Z"}]}]
    assert sum_rewards(ops) == {}


def test_sum_rewards_tolerates_unknown_operation_type():
    """29 types were observed in one account. The enum is open."""
    ops = [{"operation_id": "o1", "operation_type": "brand_new_type",
            "transactions": []}]
    assert sum_rewards(ops) == {}


def test_sum_rewards_picks_the_later_timestamp_across_formats():
    """Same second, one with a fraction and one without — string compare fails here."""
    ops = [
        _reward("vsn", "1", "0", "2026-09-22T17:16:35Z"),
        _reward("vsn", "1", "0", "2026-09-22T17:16:35.500Z"),
    ]
    assert sum_rewards(ops)["vsn"].last_at == "2026-09-22T17:16:35.500Z"


def test_sum_rewards_ignores_a_reward_from_another_wallet_owner():
    """Both conditions are required: operation_type AND wallet_owner."""
    ops = [
        _reward("vsn", "5", "1", "2026-09-22T17:16:35Z"),
        _reward("vsn", "99", "0", "2026-09-21T00:00:00Z", owner="shared-default"),
    ]
    totals = sum_rewards(ops)["vsn"]
    assert totals.count == 1
    assert abs(totals.gross - 5.0) < 1e-9


def test_is_later_ignores_empty_timestamps():
    """The pre-fix code guarded with `if credited`; an empty string must not win."""
    assert _is_later("", None) is False
    assert _is_later("", "2026-09-22T17:16:35Z") is False
    assert _is_later("2026-09-22T17:16:35Z", "") is True


def test_is_later_survives_a_mixed_timezone_batch():
    """A zone-less timestamp must not raise out of a coordinator refresh."""
    result = _is_later("2026-09-22T17:16:35", "2026-09-21T00:00:00Z")
    assert isinstance(result, bool)


def test_is_later_survives_a_non_string():
    result = _is_later(12345, "2026-09-21T00:00:00Z")
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# RewardsCoordinator._async_update_data
#
# Same construction trick as PriceCoordinator (see test_coordinator_price.py):
# DataUpdateCoordinator.__init__ only stores `hass`, so hass=None/entry=None
# is enough to drive _async_update_data() directly, without a running Home
# Assistant instance.
# ---------------------------------------------------------------------------


class _FakeClient:
    """Fake API client with a controllable async_get_operations."""

    def __init__(self, operations=None, error=None):
        self._operations = operations or []
        self._error = error
        self.calls = 0

    async def async_get_operations(self):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._operations


async def test_rewards_coordinator_returns_totals_from_operations():
    client = _FakeClient(
        operations=[_reward("vsn", "1", "0", "2026-09-22T17:16:35Z")]
    )
    coordinator = RewardsCoordinator(hass=None, entry=None, client=client)

    data = await coordinator._async_update_data()

    assert data["vsn"].gross == 1.0


async def test_rewards_coordinator_raises_config_entry_auth_failed_on_401():
    """Task 21 requires every scope at setup, so a 401 here means the key
    expired, was revoked, or predates that requirement (a migrated legacy
    key). Every case is answered by a new key, so this must raise
    ConfigEntryAuthFailed and let Home Assistant start the reauth flow --
    not degrade silently, which is what this coordinator used to do.
    """
    client = _FakeClient(error=BitpandaAuthError("Unauthorized for /operations"))
    coordinator = RewardsCoordinator(hass=None, entry=None, client=client)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_rewards_coordinator_raises_update_failed_on_other_errors():
    client = _FakeClient(error=BitpandaApiError("simulated outage"))
    coordinator = RewardsCoordinator(hass=None, entry=None, client=client)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


# ---------------------------------------------------------------------------
# A paging failure reaches the wallet sensor as absent or stale rewards --
# never as totals recounted over whichever pages happened to arrive. Driven
# through the real client, the real coordinator refresh and the real sensor.
# ---------------------------------------------------------------------------

# Carries milliseconds already, so the /operations cursor workaround cannot
# repair a server that keeps handing it back: the pager must raise.
_REPEATING_CURSOR = base64.b64encode(b"2026-09-09T18:31:22.080Z").decode("ascii")


def _register_repeating_operations(mocker, operations: list[dict]) -> None:
    page = {
        "data": operations,
        "next_cursor": _REPEATING_CURSOR,
        "has_next_page": True,
    }
    mocker.get(f"{API_BASE_URL}/operations?cursor={_REPEATING_CURSOR}", json=page)
    mocker.get(f"{API_BASE_URL}/operations", json=page)


class _Coordinator:
    def __init__(self, data):
        self.data = data
        self.last_update_success = True


def _vsn_wallet_sensor(rewards) -> BitpandaWalletSensor:
    portfolio = _Coordinator(
        PortfolioData(
            holdings={
                "vsn": Holding(asset_id="vsn", balance=100.0, available=0.0,
                               staked=100.0, value=4.0)
            }
        )
    )

    class _Entry:
        entry_id = "entry1"

    return BitpandaWalletSensor(
        portfolio, _Coordinator({}), rewards, _Entry(),
        asset={"id": "vsn", "symbol": "VSN"}, currency="EUR",
    )


@pytest.mark.timeout(10)
async def test_rewards_paging_failure_leaves_rewards_attributes_absent(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"api_key": "key", "currency": "EUR"})
    entry.add_to_hass(hass)

    with mock_aiohttp_client() as mocker:
        _register_repeating_operations(
            mocker, [_reward("vsn", "20.68994769", "4.13798954", "2026-09-22T17:16:35Z")]
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            rewards = RewardsCoordinator(hass, entry, BitpandaApiClient("key", session))
            await rewards.async_refresh()

    assert rewards.last_update_success is False
    assert rewards.data is None
    attrs = _vsn_wallet_sensor(rewards).extra_state_attributes
    assert attrs["balance"] == 100.0
    assert not [key for key in attrs if key.startswith("rewards_")]


@pytest.mark.timeout(10)
async def test_rewards_paging_failure_keeps_the_last_complete_totals(hass):
    """Stale is honest; a recount over a partial history is not."""
    entry = MockConfigEntry(domain=DOMAIN, data={"api_key": "key", "currency": "EUR"})
    entry.add_to_hass(hass)
    older = _reward("vsn", "20.67399483", "4.13479897", "2026-09-15T17:16:25Z")
    newer = _reward("vsn", "20.68994769", "4.13798954", "2026-09-22T17:16:35Z")

    with mock_aiohttp_client() as mocker:
        mocker.get(
            f"{API_BASE_URL}/operations",
            json={"data": [newer, older], "has_next_page": False},
        )
        async with mocker.create_session(asyncio.get_running_loop()) as session:
            rewards = RewardsCoordinator(hass, entry, BitpandaApiClient("key", session))
            await rewards.async_refresh()
            assert rewards.last_update_success is True
            assert rewards.data["vsn"].count == 2

            # Next hour the listing breaks down after one page holding only
            # the newer reward.
            mocker.clear_requests()
            _register_repeating_operations(mocker, [newer])
            await rewards.async_refresh()

    assert rewards.last_update_success is False
    attrs = _vsn_wallet_sensor(rewards).extra_state_attributes
    assert attrs["rewards_count"] == 2
    assert abs(attrs["rewards_gross"] - (20.67399483 + 20.68994769)) < 1e-8


# ---------------------------------------------------------------------------
# EarnCoordinator._async_update_data
# ---------------------------------------------------------------------------


class _FakeEarnClient:
    """Fake API client with a controllable async_get_earn_configs."""

    def __init__(self, configs=None, error=None):
        self._configs = configs or []
        self._error = error

    async def async_get_earn_configs(self):
        if self._error is not None:
            raise self._error
        return self._configs


async def test_earn_coordinator_raises_config_entry_auth_failed_on_401():
    client = _FakeEarnClient(
        error=BitpandaAuthError("Unauthorized for /earn/configs")
    )
    coordinator = EarnCoordinator(hass=None, entry=None, client=client)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()
