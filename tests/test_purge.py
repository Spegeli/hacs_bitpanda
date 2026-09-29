"""Deleting what the Portfolio manages, with its history, on a currency change,
and looking for the statistics an earlier Portfolio left -- the cases that need
no real recorder (test_old_statistics.py has one)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.naming import (
    PORTFOLIO_KEYS,
    portfolio_device_identifier,
    portfolio_unique_id,
    staking_unique_id,
    total_unique_id,
    wallet_device_identifier,
    wallet_unique_id,
)
from custom_components.bitpanda.purge import (
    OldStatistics,
    async_find_old_statistics,
    async_purge_portfolio,
    async_purge_recorded,
)

VSN = "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb"


def _entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "portfolio"})
    entry.add_to_hass(hass)
    return entry


def _device(hass, entry, identifier: str) -> str:
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, identifier)}
    ).id


def _register(hass, entry, unique_id: str, device_id: str | None = None) -> str:
    return er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, unique_id, config_entry=entry, device_id=device_id
    ).entity_id


def _managed(hass, entry) -> list[str]:
    """What the Portfolio creates: every figure on its device, and a wallet
    with its Staking and Total sensors on the wallet's device."""
    eid = entry.entry_id
    portfolio = _device(hass, entry, portfolio_device_identifier(eid))
    wallet = _device(hass, entry, wallet_device_identifier(eid, VSN))
    return sorted(
        [
            *(_register(hass, entry, portfolio_unique_id(eid, key), portfolio) for key in PORTFOLIO_KEYS),
            _register(hass, entry, wallet_unique_id(eid, VSN), wallet),
            _register(hass, entry, staking_unique_id(eid, VSN), wallet),
            _register(hass, entry, total_unique_id(eid, VSN), wallet),
        ]
    )


def _fake_recorder(hass, calls: list):
    hass.config.components.add("recorder")

    async def _purge(call):
        calls.append(("purge", sorted(call.data["entity_id"]), call.data["keep_days"]))

    hass.services.async_register("recorder", "purge_entities", _purge)
    instance = MagicMock()
    instance.async_clear_statistics = MagicMock(
        side_effect=lambda ids: calls.append(("clear", sorted(ids)))
    )
    return instance


async def test_purge_removes_what_the_portfolio_manages_with_history_and_statistics(hass):
    entry = _entry(hass)
    other = MockConfigEntry(domain=DOMAIN, version=3, data={"entry_type": "price_tracker"})
    other.add_to_hass(hass)
    managed = _managed(hass, entry)
    kept = _register(hass, other, "c")
    calls: list = []
    instance = _fake_recorder(hass, calls)

    with patch("custom_components.bitpanda.purge.get_instance", return_value=instance):
        assert await async_purge_portfolio(hass, entry) is True

    ent_reg = er.async_get(hass)
    assert er.async_entries_for_config_entry(ent_reg, entry.entry_id) == []
    assert dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id) == []
    assert ent_reg.async_get(kept) is not None
    # keep_days 0: everything recorded before this moment goes. Both are
    # queued before the caller reloads the entry.
    assert calls == [("purge", managed, 0), ("clear", managed)]


async def test_purge_leaves_the_legacy_leftovers_with_their_devices_and_history(hass):
    """What the version 1 migration left in place -- an unresolved wallet,
    another fiat wallet, a legacy price sensor, each on its legacy device --
    was promised to stay until the user deletes it. It is not the
    Portfolio's own, so a currency change leaves it alone."""
    entry = _entry(hass)
    eid = entry.entry_id
    managed = _managed(hass, entry)
    wallets = _device(hass, entry, f"{eid}_wallets")
    prices = _device(hass, entry, f"{eid}_price_tracker")
    leftovers = sorted(
        [
            _register(hass, entry, f"{eid}_wallet_cryptocoin_GONE", wallets),
            _register(hass, entry, f"{eid}_wallet_fiat_USD", wallets),
            _register(hass, entry, f"{eid}_BTC_price_EUR", prices),
        ]
    )
    calls: list = []
    instance = _fake_recorder(hass, calls)

    with patch("custom_components.bitpanda.purge.get_instance", return_value=instance):
        await async_purge_portfolio(hass, entry)

    ent_reg = er.async_get(hass)
    assert sorted(
        reg_entry.entity_id
        for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    ) == leftovers
    assert {
        device.id for device in dr.async_entries_for_config_entry(dr.async_get(hass), eid)
    } == {wallets, prices}
    assert calls == [("purge", managed, 0), ("clear", managed)]


async def test_purge_without_a_recorder_still_clears_the_registries(hass):
    entry = _entry(hass)
    _managed(hass, entry)
    await async_purge_portfolio(hass, entry)
    assert er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id) == []


async def test_purge_unloads_a_loaded_entry_first(hass):
    entry = _entry(hass)
    entry.mock_state(hass, ConfigEntryState.LOADED)
    with patch.object(hass.config_entries, "async_unload", AsyncMock(return_value=True)) as unload:
        assert await async_purge_portfolio(hass, entry) is True
    unload.assert_awaited_once_with(entry.entry_id)


def _registered(hass, entry) -> tuple[list[str], int]:
    """The entry's entity IDs and its number of devices."""
    return (
        sorted(
            reg_entry.entity_id
            for reg_entry in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        ),
        len(dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)),
    )


async def test_a_failed_unload_changes_nothing(hass):
    """Purging under sensors that still run would race them, and the reload
    that follows a purge cannot bring back an entry whose unload failed."""
    entry = _entry(hass)
    managed = _managed(hass, entry)
    entry.mock_state(hass, ConfigEntryState.LOADED)
    calls: list = []
    instance = _fake_recorder(hass, calls)

    with patch.object(
        hass.config_entries, "async_unload", AsyncMock(return_value=False)
    ), patch("custom_components.bitpanda.purge.get_instance", return_value=instance):
        assert await async_purge_portfolio(hass, entry) is False

    assert _registered(hass, entry) == (managed, 2)
    assert calls == []


@pytest.mark.parametrize(
    "state", [ConfigEntryState.FAILED_UNLOAD, ConfigEntryState.MIGRATION_ERROR]
)
async def test_an_entry_home_assistant_cannot_reload_changes_nothing(hass, state):
    """An entry whose unload failed earlier, or whose migration did, cannot
    be reloaded until Home Assistant restarts: the currency change would be
    left half done."""
    entry = _entry(hass)
    managed = _managed(hass, entry)
    entry.mock_state(hass, state)

    with patch.object(hass.config_entries, "async_unload", AsyncMock()) as unload:
        assert await async_purge_portfolio(hass, entry) is False

    unload.assert_not_called()
    assert _registered(hass, entry) == (managed, 2)


async def test_the_recorded_purge_deletes_history_then_statistics_of_the_given_ids(hass):
    calls: list = []
    instance = _fake_recorder(hass, calls)
    with patch("custom_components.bitpanda.purge.get_instance", return_value=instance):
        await async_purge_recorded(hass, ["sensor.b", "sensor.a"])
    assert calls == [("purge", ["sensor.a", "sensor.b"], 0), ("clear", ["sensor.a", "sensor.b"])]


async def test_the_recorded_purge_without_ids_does_nothing(hass):
    calls: list = []
    instance = _fake_recorder(hass, calls)
    with patch("custom_components.bitpanda.purge.get_instance", return_value=instance):
        await async_purge_recorded(hass, [])
    assert calls == []


async def test_the_recorded_purge_without_a_recorder_does_nothing(hass):
    # No recorder.purge_entities service: a call would raise ServiceNotFound.
    await async_purge_recorded(hass, ["sensor.a"])


_LIST = "custom_components.bitpanda.purge.async_list_statistic_ids"
_NOTHING = OldStatistics(entity_ids=[], currencies=[])


async def test_without_a_recorder_no_old_statistics_are_found(hass):
    # A failed listing finds nothing too, so the result alone cannot tell the
    # two apart: the listing must not be asked at all.
    with patch(_LIST, AsyncMock()) as listing:
        assert await async_find_old_statistics(hass, "EUR") == _NOTHING
    listing.assert_not_called()


async def test_a_failed_listing_finds_nothing_and_logs_the_error_type_only(hass, caplog):
    hass.config.components.add("recorder")
    with patch(_LIST, AsyncMock(side_effect=RuntimeError("detail from the database"))):
        assert await async_find_old_statistics(hass, "EUR") == _NOTHING
    [record] = [r for r in caplog.records if r.name == "custom_components.bitpanda.purge"]
    assert record.levelname == "WARNING" and record.getMessage() == (
        "Could not look for long-term statistics of an earlier Bitpanda Portfolio"
        " (RuntimeError); setup continues without asking about them"
    )
    assert record.exc_info is None and "detail from the database" not in caplog.text


async def test_a_listing_of_an_unexpected_shape_finds_nothing_and_logs_the_error_type(hass, caplog):
    """Home Assistant could rename what an entry holds: setup must go on
    without the question, not fail with it."""
    hass.config.components.add("recorder")
    with patch(_LIST, AsyncMock(return_value=[{"statistic_id": "sensor.bitpanda_portfolio_total"}])):
        assert await async_find_old_statistics(hass, "EUR") == _NOTHING
    [record] = [r for r in caplog.records if r.name == "custom_components.bitpanda.purge"]
    assert record.levelname == "WARNING" and "KeyError" in record.getMessage()


@pytest.mark.timeout(10)
async def test_a_listing_that_takes_too_long_finds_nothing_and_logs_a_timeout(hass, caplog):
    """A recorder that answers late -- a database migration, a locked file --
    must not hold the setup dialog: after the timeout, setup goes on without
    the question."""
    hass.config.components.add("recorder")

    async def never_answers(*_: object) -> None:
        await asyncio.Event().wait()

    with patch(_LIST, AsyncMock(side_effect=never_answers)), patch(
        "custom_components.bitpanda.purge._LISTING_TIMEOUT", 0.01
    ):
        assert await async_find_old_statistics(hass, "EUR") == _NOTHING
    [record] = [r for r in caplog.records if r.name == "custom_components.bitpanda.purge"]
    assert "(TimeoutError)" in record.getMessage()


async def test_statistics_of_another_source_do_not_count(hass):
    """Home Assistant gives every sensor.* statistic the source "recorder"
    (async_import_statistics refuses another; external statistics are keyed
    domain:id), so this listing does not occur: the test pins the source
    check the spec asks for."""
    hass.config.components.add("recorder")
    listed = [{"statistic_id": "sensor.bitpanda_portfolio_total", "source": "other",
               "statistics_unit_of_measurement": "USD"}]
    with patch(_LIST, AsyncMock(return_value=listed)):
        assert await async_find_old_statistics(hass, "EUR") == _NOTHING


async def test_the_ids_and_the_other_currencies_come_out_sorted(hass):
    """The dialog names the currencies as they come: a set's order would
    change from one start of Home Assistant to the next."""
    hass.config.components.add("recorder")
    # Listed neither sorted by ID nor by currency.
    units = {
        "sensor.bitpanda_portfolio_total": "SEK",
        "sensor.bitpanda_portfolio_cash": "PLN",
        "sensor.bitpanda_portfolio_cash_plus": "CZK",
        "sensor.bitpanda_vision_vsn_wallet_available": "GBP",
        "sensor.bitpanda_vision_vsn_wallet_staking": "CHF",
    }
    listed = [
        {"statistic_id": entity_id, "source": "recorder", "statistics_unit_of_measurement": unit}
        for entity_id, unit in units.items()
    ]
    with patch(_LIST, AsyncMock(return_value=listed)):
        found = await async_find_old_statistics(hass, "USD")
    assert found == OldStatistics(
        entity_ids=sorted(units), currencies=["CHF", "CZK", "GBP", "PLN", "SEK"]
    )
