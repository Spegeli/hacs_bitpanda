"""Tests for earn APR mapping and reward aggregation."""
from custom_components.bitpanda.api import BitpandaApiError, BitpandaAuthError
from custom_components.bitpanda.coordinator import (
    RewardsCoordinator,
    _is_later,
    map_earn_configs,
    sum_rewards,
)


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
    assert coordinator.unauthorized is False


async def test_rewards_coordinator_latches_unauthorized_on_401():
    """A 401 must set `unauthorized` and return empty without raising.

    Once latched, a later cycle must return empty without issuing another
    request — the rest of the integration keeps working for a key that
    cannot read /operations.
    """
    client = _FakeClient(error=BitpandaAuthError("Unauthorized for /operations"))
    coordinator = RewardsCoordinator(hass=None, entry=None, client=client)

    first = await coordinator._async_update_data()

    assert first == {}
    assert coordinator.unauthorized is True
    assert client.calls == 1

    second = await coordinator._async_update_data()

    assert second == {}
    assert client.calls == 1


async def test_rewards_coordinator_raises_update_failed_on_other_errors():
    client = _FakeClient(error=BitpandaApiError("simulated outage"))
    coordinator = RewardsCoordinator(hass=None, entry=None, client=client)

    try:
        await coordinator._async_update_data()
    except Exception as err:  # noqa: BLE001 - asserting the HA type below
        from homeassistant.helpers.update_coordinator import UpdateFailed

        assert isinstance(err, UpdateFailed)
    else:
        raise AssertionError("expected UpdateFailed")
