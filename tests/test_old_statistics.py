"""Statistics an earlier Portfolio left in another currency, through a real recorder."""
from collections.abc import Iterable

import pytest
from homeassistant.helpers import entity_registry as er
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
# What a template sensor named "Bitpanda Crypto Wallet Total" gets: no
# Portfolio's, yet an ID that has the Portfolio's pattern.
_LIVE = "sensor.bitpanda_crypto_wallet_total"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Replaces the shared fixture of the same name for this module: the
    recorder must be set up before Home Assistant itself, and this order of
    arguments is what guarantees it."""
    return


async def _record(
    hass, units: dict[str, str | None], *, deleted: Iterable[str] = ()
) -> None:
    """Leave long-term statistics under each ID of `units`, in its unit (none
    for None), as sensors would have.

    The sensors of `deleted` are gone afterwards, as a deleted Portfolio's
    are: in production its statistics outlive its entities and its states.
    The others stay in the state machine, like a sensor that exists.
    Everything is recorded in one go, since the recorder skips a 5-minute
    period it has compiled once. It reads the statistics back before it
    deletes anything, so a test that expects nothing to be found cannot pass
    on statistics that were never recorded.
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
    for entity_id in deleted:
        hass.states.async_remove(entity_id)
    await async_wait_recording_done(hass)


async def test_figures_and_wallets_in_another_currency_are_found(hass):
    units = {_TOTAL: "EUR", _CASH: "EUR", _RETURN_DAY: "%",
             _WALLET: "EUR", f"{_WALLET}_2": "EUR"}
    await _record(hass, units, deleted=units)
    assert await async_find_old_statistics(hass, "USD") == OldStatistics(
        entity_ids=sorted([_TOTAL, _CASH, _RETURN_DAY, _WALLET, f"{_WALLET}_2"]),
        currencies=["EUR"],
    )


async def test_mixed_units_name_only_the_other_currencies_and_delete_every_id(hass):
    units = {_TOTAL: "EUR", _RETURN_DAY: "%", _WALLET: "USD", _STAKING: "CHF"}
    await _record(hass, units, deleted=units)
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
    await _record(hass, units, deleted=units)
    assert await async_find_old_statistics(hass, "USD") == OldStatistics(entity_ids=[], currencies=[])


async def test_a_live_sensor_under_a_portfolio_id_is_left_alone(hass):
    """A template's or another integration's sensor can have an ID that
    matches the pattern. It still has a state -- a deleted Portfolio leaves
    none -- so its statistics are not the earlier Portfolio's: they count
    neither for the question nor for the deletion, whatever their unit."""
    await _record(hass, {_TOTAL: "EUR", _WALLET: "EUR", _LIVE: "CHF"}, deleted=[_TOTAL, _WALLET])
    assert await async_find_old_statistics(hass, "USD") == OldStatistics(
        entity_ids=sorted([_TOTAL, _WALLET]), currencies=["EUR"]
    )


async def test_a_live_sensor_alone_under_a_portfolio_id_asks_nothing(hass):
    await _record(hass, {_LIVE: "CHF"})
    assert await async_find_old_statistics(hass, "USD") == OldStatistics(entity_ids=[], currencies=[])


async def test_a_registered_entity_under_a_portfolio_id_is_left_alone(hass):
    """An entity that is registered but shows no state -- its integration is
    not loaded, say -- exists as well: a deleted Portfolio leaves no registry
    entry either."""
    entry = er.async_get(hass).async_get_or_create(
        "sensor", "template", "crypto_total", suggested_object_id="bitpanda_crypto_wallet_total"
    )
    assert entry.entity_id == _LIVE
    await _record(hass, {_LIVE: "CHF"}, deleted=[_LIVE])
    assert hass.states.get(_LIVE) is None
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
