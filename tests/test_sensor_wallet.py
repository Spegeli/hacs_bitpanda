"""Tests for the wallet sensor."""
from custom_components.bitpanda.coordinator import (
    Holding,
    PortfolioData,
    RewardTotals,
)
from custom_components.bitpanda.sensor import (
    BitpandaWalletSensor,
    wallet_attributes,
    wallet_value,
)


def _holding(**kw):
    base = dict(asset_id="a1", balance=10.0, available=10.0, staked=0.0, value=25.5)
    base.update(kw)
    return Holding(**base)


def test_wallet_value_is_the_server_computed_amount():
    data = PortfolioData(holdings={"a1": _holding()})
    assert wallet_value(data, "a1") == 25.5


def test_wallet_value_for_index_is_not_multiplied_by_price():
    """Regression for issue #7: 431.44 EUR, never 431.44 * 21442.30."""
    data = PortfolioData(holdings={"bci5": _holding(asset_id="bci5",
                                                    balance=0.0201209758,
                                                    available=0.0201209758,
                                                    value=431.44)})
    assert wallet_value(data, "bci5") == 431.44


def test_wallet_value_is_none_when_position_was_sold():
    """Sold-out assets vanish from /portfolio; the sensor goes unavailable."""
    assert wallet_value(PortfolioData(), "gone") is None


def test_wallet_attributes_include_performance():
    data = PortfolioData(holdings={"a1": _holding(invested=100.0,
                                                  avg_buy_price=1.2345,
                                                  total_return=10.0,
                                                  total_return_pct=-67.98)})
    attrs = wallet_attributes(data, "a1", asset={"symbol": "VSN"},
                              apr=None, rewards=None)
    assert attrs["invested_amount"] == 100.0
    assert attrs["average_buy_price"] == 1.2345
    assert attrs["total_return"] == 10.0
    assert attrs["total_return_percent"] == -67.98


def test_wallet_attributes_expose_staked_amount_and_apr():
    data = PortfolioData(holdings={"a1": _holding(balance=21466.95,
                                                  available=0.0,
                                                  staked=21466.95)})
    attrs = wallet_attributes(data, "a1", asset={"symbol": "VSN"},
                              apr=0.041, rewards=None)
    assert attrs["staked"] == 21466.95
    assert attrs["earn_apr_percent"] == 4.1


def test_wallet_attributes_omit_apr_when_asset_has_no_earn_product():
    data = PortfolioData(holdings={"a1": _holding()})
    attrs = wallet_attributes(data, "a1", asset={"symbol": "XAU"},
                              apr=None, rewards=None)
    assert "earn_apr_percent" not in attrs


def test_wallet_attributes_include_reward_totals():
    data = PortfolioData(holdings={"a1": _holding()})
    totals = RewardTotals(gross=2136.649131, fee=371.12351,
                          net=1765.525621, count=62,
                          last_at="2026-09-22T17:16:35Z")
    attrs = wallet_attributes(data, "a1", asset={"symbol": "VSN"},
                              apr=0.041, rewards=totals)
    assert attrs["rewards_net"] == 1765.525621
    assert attrs["rewards_count"] == 62
    assert attrs["rewards_last_at"] == "2026-09-22T17:16:35Z"


# ---------------------------------------------------------------------------
# wallet_attributes with an incomplete asset dict
#
# AssetResolver caches raw /assets catalogue entries. Nothing guarantees every
# entry carries a "name" key, so wallet_attributes must degrade gracefully
# instead of raising KeyError, and the rest of the attribute dict must stay
# useful even when it does.
# ---------------------------------------------------------------------------


def test_wallet_attributes_handles_asset_without_name_key():
    data = PortfolioData(holdings={"a1": _holding()})
    attrs = wallet_attributes(data, "a1", asset={"symbol": "VSN"},
                              apr=None, rewards=None)
    assert attrs["asset"] == "VSN"
    assert attrs["asset_name"] is None
    assert attrs["balance"] == 10.0
    assert attrs["available"] == 10.0
    assert attrs["staked"] == 0.0


# ---------------------------------------------------------------------------
# BitpandaWalletSensor construction
#
# BaseCoordinatorEntity.__init__ only stores the coordinator, and
# CoordinatorEntity.available reads coordinator.last_update_success — neither
# touches self.hass. That means the entity can be built and probed with
# duck-typed coordinator stand-ins and no running Home Assistant instance,
# the same trick the previous task used to construct PriceCoordinator with
# hass=None. That keeps this a fast regression guard instead of a full
# hass-fixture test.
# ---------------------------------------------------------------------------


class _FakeCoordinator:
    """Duck-typed stand-in exposing what CoordinatorEntity/the entity read."""

    def __init__(self, data=None, last_update_success=True):
        self.data = data
        self.last_update_success = last_update_success


class _FakeConfigEntry:
    entry_id = "entry1"


def test_wallet_sensor_available_is_false_when_asset_not_in_portfolio():
    """Sold-out assets vanish from /portfolio; the entity must go unavailable."""
    portfolio = _FakeCoordinator(data=PortfolioData())
    earn = _FakeCoordinator(data={})
    rewards = _FakeCoordinator(data={})
    sensor = BitpandaWalletSensor(
        portfolio, earn, rewards, _FakeConfigEntry(),
        asset={"id": "gone", "symbol": "GONE"}, currency="EUR",
    )

    assert sensor.available is False


def test_wallet_sensor_available_is_true_when_asset_is_held():
    data = PortfolioData(holdings={"a1": _holding()})
    portfolio = _FakeCoordinator(data=data)
    earn = _FakeCoordinator(data={})
    rewards = _FakeCoordinator(data={})
    sensor = BitpandaWalletSensor(
        portfolio, earn, rewards, _FakeConfigEntry(),
        asset={"id": "a1", "symbol": "VSN"}, currency="EUR",
    )

    assert sensor.available is True
    assert sensor.native_value == 25.5
