"""Tests for diagnostics redaction."""
from custom_components.bitpanda.diagnostics import build_diagnostics


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
    )
    assert result["coordinators"]["rewards"]["unauthorized"] is True
