"""Tests for diagnostics redaction."""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.coordinator import Holding, PortfolioData
from custom_components.bitpanda.diagnostics import (
    async_get_config_entry_diagnostics,
    build_diagnostics,
)


class _Coordinator:
    def __init__(self, data, success=True):
        self.data = data
        self.last_update_success = success


def test_api_key_is_never_included():
    result = build_diagnostics(
        entry_data={"api_key": "super-secret", "currency": "EUR"},
        options={"tracked_assets": [], "tracked_wallets": [], "asset_cache": {}},
        portfolio=_Coordinator(None),
        prices=_Coordinator({}),
        earn=_Coordinator({}),
        rewards=_Coordinator({}),
        rewards_unauthorized=False,
        history=_Coordinator({}),
    )
    assert "super-secret" not in repr(result)
    assert result["config"]["api_key"] == "**REDACTED**"


def test_reports_rewards_scope_problem():
    result = build_diagnostics(
        entry_data={"api_key": "k", "currency": "EUR"},
        options={"tracked_assets": [], "tracked_wallets": [], "asset_cache": {}},
        portfolio=_Coordinator(None),
        prices=_Coordinator({}),
        earn=_Coordinator({}),
        rewards=_Coordinator({}),
        rewards_unauthorized=True,
        history=_Coordinator({}),
    )
    assert result["coordinators"]["rewards"]["unauthorized"] is True


# --- Fix round 1 --------------------------------------------------------
#
# Findings from the task 17 review. See task-17-report.md, "Fix round 1",
# for the full writeup.


def test_portfolio_truthy_branches_with_real_dataclasses():
    """Populated portfolio data, using the real dataclasses from coordinator.py.

    Both pre-existing tests above pass `portfolio=_Coordinator(None)`, so
    `portfolio.data.holdings` and `portfolio.data.rate` never execute. This
    uses the real `PortfolioData`/`Holding` shape (not a fake) so a rename in
    coordinator.py breaks this test instead of going unnoticed.

    `rate=0.0` is deliberately not just "any" non-None value: it is falsy, so
    the old `bool(portfolio.data and portfolio.data.rate)` computation would
    have reported `rate_derived=False` for a rate that had, in fact, been
    derived. This test fails under that old expression and passes under the
    `is not None` fix, pinning the exact regression fixed in this round.
    """
    data = PortfolioData(
        holdings={
            "BTC": Holding(
                asset_id="BTC", balance=1.0, available=1.0, staked=0.0, value=100.0
            ),
            "ETH": Holding(
                asset_id="ETH", balance=2.0, available=2.0, staked=0.0, value=200.0
            ),
        },
        fiat={},
        rate=0.0,
        total=300.0,
    )
    result = build_diagnostics(
        entry_data={"api_key": "k", "currency": "EUR"},
        options={"tracked_assets": [], "tracked_wallets": [], "asset_cache": {}},
        portfolio=_Coordinator(data),
        prices=_Coordinator({}),
        earn=_Coordinator({}),
        rewards=_Coordinator({}),
        rewards_unauthorized=False,
        history=_Coordinator({}),
    )
    assert result["coordinators"]["portfolio"]["holdings_count"] == 2
    assert result["coordinators"]["portfolio"]["rate_derived"] is True


def test_redaction_survives_extra_entry_data_fields():
    """A future careless `**entry_data` spread must not leak anything either.

    `entry_data` here carries a second secret-looking field beyond `api_key`
    -- only `build_diagnostics` deciding what to copy out of `entry_data`
    (rather than spreading it wholesale) keeps this safe.
    """
    result = build_diagnostics(
        entry_data={
            "api_key": "super-secret",
            "currency": "EUR",
            "currency_id": "some-currency-id",
            "refresh_token": "also-secret",
        },
        options={"tracked_assets": [], "tracked_wallets": [], "asset_cache": {}},
        portfolio=_Coordinator(None),
        prices=_Coordinator({}),
        earn=_Coordinator({}),
        rewards=_Coordinator({}),
        rewards_unauthorized=False,
        history=_Coordinator({}),
    )
    assert "super-secret" not in repr(result)
    assert "also-secret" not in repr(result)


async def test_async_get_config_entry_diagnostics_reads_the_real_store(hass):
    """Exercises the async wrapper against a full seven-key store.

    This is the test that would have caught the exact bug reported after
    task 16: `diagnostics.py` used to read `wallet_coordinator`, a key the
    store no longer has, and nothing exercised
    `async_get_config_entry_diagnostics` until now.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "super-secret", "currency": "EUR"},
        options={
            "tracked_assets": ["a"],
            "tracked_wallets": [],
            "asset_cache": {},
        },
    )
    rewards = _Coordinator({})
    rewards.unauthorized = False
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "portfolio_coordinator": _Coordinator(None),
        "price_coordinator": _Coordinator({}),
        "earn_coordinator": _Coordinator({}),
        "rewards_coordinator": rewards,
        "history_coordinator": _Coordinator({}),
        "resolver": object(),
        "currency": "EUR",
    }

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert "super-secret" not in repr(result)
    assert result["config"]["currency"] == "EUR"
    assert result["options"]["tracked_assets_count"] == 1
    assert set(result["coordinators"]) == {
        "portfolio",
        "prices",
        "earn",
        "rewards",
        "history",
    }
    assert result["coordinators"]["rewards"]["unauthorized"] is False
