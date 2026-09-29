"""Statistics an earlier Portfolio left in another currency, through a real recorder."""
import pytest
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_purge_done,
    async_wait_recording_done,
    do_adhoc_statistics,
    get_start_time,
)

from custom_components.bitpanda.naming import portfolio_entity_id, return_key
from custom_components.bitpanda.purge import (
    OldStatistics,
    async_find_old_statistics,
    async_purge_recorded,
)

from tests.conftest import recorded_history, statistics_units

_TOTAL = portfolio_entity_id("total")
_CASH = portfolio_entity_id("cash")
_RETURN_DAY = portfolio_entity_id(return_key("DAY"))
_RETURN_YEAR = portfolio_entity_id(return_key("YEAR"))
_WALLET = "sensor.bitpanda_vision_vsn_wallet_available"
_STAKING = "sensor.bitpanda_bitcoin_btc_wallet_staking"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Replaces the shared fixture of the same name for this module: the
    recorder must be set up before Home Assistant itself, and this order of
    arguments is what guarantees it."""
    return


async def _record(hass, units: dict[str, str | None]) -> None:
    """Leave long-term statistics under each ID of `units`, in its unit (none
    for None), as an earlier Portfolio's sensors would have.

    The sensors stay in the state machine afterwards; the listing prefers
    what the database holds. It ends by reading the statistics back, so a
    test that expects nothing to be found cannot pass on statistics that
    were never recorded.
    """
    assert await async_setup_component(hass, "sensor", {})
    # The sensor's recorder platform is registered once Home Assistant settles.
    await hass.async_block_till_done()
    for entity_id, unit in units.items():
        attributes = {"state_class": "measurement"}
        if unit is not None:
            attributes["unit_of_measurement"] = unit
        hass.states.async_set(entity_id, "1.0", attributes)
    await async_wait_recording_done(hass)
    do_adhoc_statistics(hass, start=get_start_time(dt_util.utcnow()))
    await async_wait_recording_done(hass)
    assert await statistics_units(hass, units) == units


async def test_figures_and_wallets_in_another_currency_are_found(hass):
    await _record(hass, {_TOTAL: "EUR", _CASH: "EUR", _RETURN_DAY: "%",
                         _WALLET: "EUR", f"{_WALLET}_2": "EUR"})
    assert await async_find_old_statistics(hass, "USD") == OldStatistics(
        entity_ids=sorted([_TOTAL, _CASH, _RETURN_DAY, _WALLET, f"{_WALLET}_2"]),
        currencies=["EUR"],
    )


async def test_mixed_units_name_only_the_other_currencies_and_delete_every_id(hass):
    await _record(hass, {_TOTAL: "EUR", _RETURN_DAY: "%", _WALLET: "USD", _STAKING: "CHF"})
    assert await async_find_old_statistics(hass, "USD") == OldStatistics(
        entity_ids=sorted([_TOTAL, _RETURN_DAY, _WALLET, _STAKING]),
        currencies=["CHF", "EUR"],
    )


@pytest.mark.parametrize(
    "units",
    [
        {_RETURN_DAY: "%", _RETURN_YEAR: "%"},
        {_TOTAL: "USD", _WALLET: "USD"},
        {_TOTAL: None},
        {"sensor.my_cash": "EUR", "sensor.bitpanda_bitcoin_btc_price_tracker_eur": "EUR"},
    ],
    ids=["returns_only", "same_currency", "no_unit", "not_the_portfolios"],
)
async def test_nothing_is_found_without_portfolio_statistics_in_another_currency(hass, units):
    await _record(hass, units)
    assert await async_find_old_statistics(hass, "USD") == OldStatistics(entity_ids=[], currencies=[])


async def test_the_recorded_purge_removes_exactly_the_given_history_and_statistics(hass):
    await _record(hass, {_TOTAL: "EUR", _WALLET: "EUR", "sensor.other_total": "EUR"})
    await async_purge_recorded(hass, [_TOTAL, _WALLET])
    await async_wait_purge_done(hass)
    await async_wait_recording_done(hass)
    assert await statistics_units(hass, [_TOTAL, _WALLET, "sensor.other_total"]) == {
        "sensor.other_total": "EUR"
    }
    assert await recorded_history(hass, _TOTAL) == []
    assert await recorded_history(hass, _WALLET) == []
    assert await recorded_history(hass, "sensor.other_total") == [("1.0", "EUR")]
