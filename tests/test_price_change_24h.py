"""The Price Tracker's 24 h change, read from a real recorder.

Every price sensor looks up its own state of about 24 hours before, every
15 minutes (price_sensor.PriceSensor._async_update_24h_change), and its next
price publishes it with the change since. The lookup turns any failure into
a missing attribute -- the attributes are optional -- so only a real
recorder shows that it works.
"""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.bitpanda.const import DOMAIN, PRICE_UPDATE_INTERVAL_BASE

from tests.conftest import load_fixture, price_group

_TICKER = "custom_components.bitpanda.api.BitpandaApiClient.async_get_ticker"
_PRICE = "sensor.bitpanda_bitcoin_btc_price_tracker_eur"

BTC = next(a for a in load_fixture("assets-sample.json") if a["symbol"] == "BTC")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Replaces the shared fixture of the same name for this module: the
    recorder must be set up before Home Assistant itself, and this order of
    arguments is what guarantees it."""
    return


async def _later(hass, freezer, delta: timedelta) -> None:
    """Home Assistant's clock moves on by `delta`, and what is due runs to
    its end. Background tasks included: Home Assistant runs the 24 h lookup,
    a time-interval action, as one -- and a coordinator's scheduled refresh
    too -- and the lookup waits for the recorder's executor, however long
    that takes on the machine at hand."""
    freezer.tick(delta)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_the_24h_change_compares_with_the_price_recorded_a_day_before(hass, freezer):
    ticker = AsyncMock(return_value={"price": "100.00000000"})
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="price_tracker", title="Bitpanda Price Tracker",
        data={"entry_type": "price_tracker"}, options={"extra_currencies": []},
        subentries_data=[price_group("crypto", BTC)],
    )
    entry.add_to_hass(hass)
    with patch(_TICKER, ticker):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await async_wait_recording_done(hass)
        state = hass.states.get(_PRICE)
        assert float(state.state) == 100.0
        # Nothing was recorded a day before.
        assert "price_24h_ago" not in state.attributes

        # A day later the price has moved, and the 24 h lookup runs...
        ticker.return_value = {"price": "110.00000000"}
        await _later(hass, freezer, timedelta(days=1))
        # ...which the next price publishes.
        await _later(hass, freezer, PRICE_UPDATE_INTERVAL_BASE)

    state = hass.states.get(_PRICE)
    assert float(state.state) == 110.0
    assert (state.attributes["price_24h_ago"], state.attributes["change_24h_pct"]) == (
        100.0, 10.0,
    )
