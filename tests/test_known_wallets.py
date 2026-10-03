"""The Portfolio's memory of the assets it announced a wallet for
(known_wallets.py), in Home Assistant's storage."""
from datetime import timedelta
from unittest.mock import patch

from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.bitpanda import async_remove_entry
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.known_wallets import (
    KnownWallets,
    async_get_known_wallets,
    async_remove_known_wallets,
)

_KEY = "bitpanda.portfolio.eid"
_LOGGER_NAME = "custom_components.bitpanda.known_wallets"


def _stored(*asset_ids: str) -> dict:
    """A list as Home Assistant's storage holds it."""
    return {"version": 1, "key": _KEY, "data": {"known_wallets": list(asset_ids)}}


async def _flush(hass, freezer) -> None:
    """Let a delayed save run. The clock matters: a save changed twice waits
    until the event loop's clock passes the second change's delay, and only
    the freezer moves that clock."""
    freezer.tick(timedelta(seconds=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_without_a_file_it_is_a_first_run(hass, hass_storage):
    known = KnownWallets(hass, "eid")
    await known.async_load()
    assert known.first_run is True
    assert "a" not in known


async def test_a_seeded_list_is_stored_sorted_and_loaded_again(hass, hass_storage, freezer):
    known = KnownWallets(hass, "eid")
    await known.async_load()
    known.seed({"b", "a"})
    await _flush(hass, freezer)
    assert hass_storage[_KEY]["version"] == 1
    assert hass_storage[_KEY]["data"] == {"known_wallets": ["a", "b"]}
    again = KnownWallets(hass, "eid")
    await again.async_load()
    assert again.first_run is False
    assert "a" in again and "c" not in again


async def test_add_and_keep_only_change_the_stored_list(hass, hass_storage, freezer):
    hass_storage[_KEY] = _stored("a", "b")
    known = KnownWallets(hass, "eid")
    await known.async_load()
    known.add("c")
    await _flush(hass, freezer)
    assert hass_storage[_KEY]["data"] == {"known_wallets": ["a", "b", "c"]}
    known.keep_only({"a", "c", "x"})
    await _flush(hass, freezer)
    assert hass_storage[_KEY]["data"] == {"known_wallets": ["a", "c"]}


async def test_before_the_list_begins_add_and_keep_only_change_nothing(
    hass, hass_storage, freezer
):
    """Only seed begins the list: an add that began it with one asset would
    have the next start announce every other held wallet."""
    known = KnownWallets(hass, "eid")
    await known.async_load()
    known.add("a")
    known.keep_only({"a"})
    await _flush(hass, freezer)
    assert known.first_run is True
    assert "a" not in known
    assert _KEY not in hass_storage


async def test_an_unchanged_list_is_not_written_again(hass, hass_storage, freezer):
    """Every refresh ends with keep_only: no write without a change."""
    hass_storage[_KEY] = _stored("a")
    known = KnownWallets(hass, "eid")
    await known.async_load()
    del hass_storage[_KEY]
    known.keep_only({"a", "b"})
    known.add("a")
    await _flush(hass, freezer)
    assert _KEY not in hass_storage


async def test_an_unreadable_file_counts_as_a_first_run_with_a_warning(
    hass, hass_storage, caplog
):
    """Rather a wallet not announced than every held wallet announced: the
    first refresh then counts what is held as known."""
    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        side_effect=HomeAssistantError("detail from the file"),
    ):
        known = KnownWallets(hass, "eid")
        await known.async_load()
    assert known.first_run is True
    [record] = [r for r in caplog.records if r.name == _LOGGER_NAME]
    assert (record.levelname, record.getMessage()) == (
        "WARNING",
        "Could not read which Bitpanda wallets were announced before (HomeAssistantError); "
        "the wallets held now count as known",
    )
    assert record.exc_info is None and "detail from the file" not in caplog.text


@pytest.mark.parametrize(
    "data", [{"known_wallets": "a"}, {"known_wallets": [1]}, {"other": []}],
    ids=["text", "number", "no_list"],
)
async def test_a_list_of_the_wrong_shape_counts_as_a_first_run(hass, hass_storage, caplog, data):
    hass_storage[_KEY] = {"version": 1, "key": _KEY, "data": data}
    known = KnownWallets(hass, "eid")
    await known.async_load()
    assert known.first_run is True
    [record] = [r for r in caplog.records if r.name == _LOGGER_NAME]
    assert record.levelname == "WARNING" and "(ValueError)" in record.getMessage()


async def test_one_list_per_entry_outlives_its_reloads(hass, hass_storage):
    """Loaded once: a reload never reads a file whose last change still
    waits to be saved."""
    hass_storage[_KEY] = _stored("a")
    first = await async_get_known_wallets(hass, "eid")
    second = await async_get_known_wallets(hass, "eid")
    assert first is second and "a" in first


async def test_removing_the_list_deletes_its_file(hass, hass_storage, freezer):
    known = await async_get_known_wallets(hass, "eid")
    known.seed({"a"})
    await _flush(hass, freezer)
    await async_remove_known_wallets(hass, "eid")
    assert _KEY not in hass_storage
    fresh = await async_get_known_wallets(hass, "eid")
    assert fresh is not known and fresh.first_run is True


async def test_deleting_a_portfolio_not_set_up_since_the_start_deletes_its_list(
    hass, hass_storage
):
    """A disabled Portfolio never loads its list: the file still goes."""
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", entry_id="eid",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR"},
    )
    entry.add_to_hass(hass)
    hass_storage[_KEY] = _stored("a")
    await async_remove_entry(hass, entry)
    assert _KEY not in hass_storage


async def test_deleting_the_price_tracker_leaves_the_portfolios_list(hass, hass_storage):
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="price_tracker", entry_id="tracker",
        data={"entry_type": "price_tracker"},
    )
    entry.add_to_hass(hass)
    hass_storage[_KEY] = _stored("a")
    await async_remove_entry(hass, entry)
    assert hass_storage[_KEY]["data"] == {"known_wallets": ["a"]}
