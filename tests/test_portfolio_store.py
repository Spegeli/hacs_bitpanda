"""What the Portfolio remembers (portfolio_store.py): one file per entry in
Home Assistant's storage, a section per feature -- the assets it announced a
wallet for, and when the newest staking payout announced per asset was
credited."""
from datetime import timedelta
from unittest.mock import patch

from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE
from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.bitpanda import async_remove_entry
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.portfolio_store import (
    PortfolioStore,
    async_get_portfolio_store,
    async_remove_portfolio_store,
)

_KEY = "bitpanda.portfolio.eid"
_LOGGER_NAME = "custom_components.bitpanda.portfolio_store"
_WALLETS_LOST = (
    "Could not read which Bitpanda wallets were announced before ({}); "
    "the wallets held now count as known"
)
_REWARDS_LOST = (
    "Could not read which Bitpanda staking rewards were announced before ({}); "
    "the payouts listed now count as known"
)


def _file(**sections) -> dict:
    """A file as Home Assistant's storage holds it, with `sections`."""
    return {"version": 1, "key": _KEY, "data": sections}


def _stored(*asset_ids: str) -> dict:
    """A file holding a list of known wallets."""
    return _file(known_wallets=list(asset_ids))


async def _loaded(hass) -> PortfolioStore:
    store = PortfolioStore(hass, "eid")
    await store.async_load()
    return store


async def _flush(hass, freezer) -> None:
    """Let a delayed save run. The clock matters: a save changed twice waits
    until the event loop's clock passes the second change's delay, and only
    the freezer moves that clock."""
    freezer.tick(timedelta(seconds=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _warnings(caplog) -> list[str]:
    records = [r for r in caplog.records if r.name == _LOGGER_NAME]
    assert all(r.levelname == "WARNING" and r.exc_info is None for r in records)
    return [r.getMessage() for r in records]


# --- The known wallets -----------------------------------------------------


async def test_without_a_file_it_is_a_first_run(hass, hass_storage):
    known = (await _loaded(hass)).known_wallets
    assert known.first_run is True
    assert "a" not in known


async def test_a_seeded_list_is_stored_sorted_and_loaded_again(hass, hass_storage, freezer):
    known = (await _loaded(hass)).known_wallets
    known.seed({"b", "a"})
    await _flush(hass, freezer)
    assert hass_storage[_KEY]["version"] == 1
    assert hass_storage[_KEY]["data"] == {"known_wallets": ["a", "b"]}
    again = (await _loaded(hass)).known_wallets
    assert again.first_run is False
    assert "a" in again and "c" not in again


async def test_add_and_keep_only_change_the_stored_list(hass, hass_storage, freezer):
    hass_storage[_KEY] = _stored("a", "b")
    known = (await _loaded(hass)).known_wallets
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
    known = (await _loaded(hass)).known_wallets
    known.add("a")
    known.keep_only({"a"})
    await _flush(hass, freezer)
    assert known.first_run is True
    assert "a" not in known
    assert _KEY not in hass_storage


async def test_an_unchanged_list_is_not_written_again(hass, hass_storage, freezer):
    """Every refresh ends with keep_only: no write without a change."""
    hass_storage[_KEY] = _stored("a")
    known = (await _loaded(hass)).known_wallets
    del hass_storage[_KEY]
    known.keep_only({"a", "b"})
    known.add("a")
    await _flush(hass, freezer)
    assert _KEY not in hass_storage


async def test_an_unreadable_file_warns_once_per_section(hass, hass_storage, caplog):
    """Rather a wallet or a payout not announced than every one announced:
    each section begins anew, and says so."""
    with patch(
        "homeassistant.helpers.storage.Store.async_load",
        side_effect=HomeAssistantError("detail from the file"),
    ):
        store = await _loaded(hass)
    assert store.known_wallets.first_run is True
    assert store.reward_marks.first_run is True
    assert _warnings(caplog) == [
        _WALLETS_LOST.format("HomeAssistantError"),
        _REWARDS_LOST.format("HomeAssistantError"),
    ]
    assert "detail from the file" not in caplog.text


@pytest.mark.parametrize(
    "value", ["a", [1]], ids=["text", "number"],
)
async def test_a_list_of_the_wrong_shape_counts_as_a_first_run(hass, hass_storage, caplog, value):
    hass_storage[_KEY] = _file(known_wallets=value)
    known = (await _loaded(hass)).known_wallets
    assert known.first_run is True
    assert _warnings(caplog) == [_WALLETS_LOST.format("ValueError")]


async def test_a_file_without_the_wallet_section_is_a_quiet_first_run(
    hass, hass_storage, caplog
):
    """The rewards may have begun the file: no section, no warning."""
    hass_storage[_KEY] = _file(known_rewards={"vsn": "2026-09-22T17:16:35Z"})
    known = (await _loaded(hass)).known_wallets
    assert known.first_run is True
    assert _warnings(caplog) == []


# --- The staking reward marks ----------------------------------------------


async def test_without_a_file_both_sections_are_a_first_run(hass, hass_storage, caplog):
    store = await _loaded(hass)
    assert (store.known_wallets.first_run, store.reward_marks.first_run) == (True, True)
    assert store.reward_marks.mark_of("vsn") is None
    assert _warnings(caplog) == []


async def test_a_file_without_the_rewards_section_keeps_its_wallets(hass, hass_storage, caplog):
    """A Portfolio updated from a version without the marks: their first
    run, the wallets as they were."""
    hass_storage[_KEY] = _stored("a")
    store = await _loaded(hass)
    assert "a" in store.known_wallets
    assert store.reward_marks.first_run is True
    assert _warnings(caplog) == []


@pytest.mark.parametrize(
    "value", [[], {"vsn": 1}, {"vsn": None}], ids=["list", "number", "none"],
)
async def test_a_malformed_rewards_section_warns_and_leaves_the_wallets(
    hass, hass_storage, caplog, value
):
    hass_storage[_KEY] = _file(known_wallets=["a"], known_rewards=value)
    store = await _loaded(hass)
    assert store.reward_marks.first_run is True
    assert "a" in store.known_wallets
    assert _warnings(caplog) == [_REWARDS_LOST.format("ValueError")]


async def test_seeded_marks_are_stored_and_read_again(hass, hass_storage, freezer):
    marks = (await _loaded(hass)).reward_marks
    marks.seed({"vsn": "2026-09-22T17:16:35Z", "ada": "2024-06-25T16:28:00Z"})
    await _flush(hass, freezer)
    assert hass_storage[_KEY]["data"] == {
        "known_rewards": {"ada": "2024-06-25T16:28:00Z", "vsn": "2026-09-22T17:16:35Z"}
    }
    again = (await _loaded(hass)).reward_marks
    assert again.first_run is False
    assert len(again) == 2
    assert again.mark_of("vsn") == "2026-09-22T17:16:35Z"
    assert again.mark_of("eth") is None


async def test_advance_moves_a_mark_and_does_nothing_before_the_seed(
    hass, hass_storage, freezer
):
    marks = (await _loaded(hass)).reward_marks
    marks.advance("vsn", "2026-09-29T16:20:00Z")
    await _flush(hass, freezer)
    assert (marks.first_run, len(marks), _KEY in hass_storage) == (True, 0, False)

    marks.seed({"vsn": "2026-09-22T17:16:35Z"})
    marks.advance("vsn", "2026-09-29T16:20:00Z")
    marks.advance("eth", "2026-09-29T16:30:00Z")
    await _flush(hass, freezer)
    assert hass_storage[_KEY]["data"]["known_rewards"] == {
        "eth": "2026-09-29T16:30:00Z",
        "vsn": "2026-09-29T16:20:00Z",
    }


async def test_an_unchanged_mark_is_not_written_again(hass, hass_storage, freezer):
    hass_storage[_KEY] = _file(known_rewards={"vsn": "2026-09-22T17:16:35Z"})
    marks = (await _loaded(hass)).reward_marks
    del hass_storage[_KEY]
    marks.advance("vsn", "2026-09-22T17:16:35Z")
    await _flush(hass, freezer)
    assert _KEY not in hass_storage


# --- One file, one writer --------------------------------------------------


async def test_one_save_writes_both_sections(hass, hass_storage, freezer):
    """A new wallet and an advanced mark in the same moment: one write
    holding both."""
    store = await _loaded(hass)
    store.known_wallets.seed({"a"})
    store.reward_marks.seed({"vsn": "2026-09-22T17:16:35Z"})
    await _flush(hass, freezer)
    assert hass_storage[_KEY]["data"] == {
        "known_wallets": ["a"],
        "known_rewards": {"vsn": "2026-09-22T17:16:35Z"},
    }


async def test_saving_keeps_a_section_the_code_does_not_know(hass, hass_storage, freezer):
    """A newer version's section survives a downgrade's saves."""
    hass_storage[_KEY] = _file(known_wallets=["a"], future={"x": 1})
    store = await _loaded(hass)
    store.known_wallets.add("b")
    await _flush(hass, freezer)
    assert hass_storage[_KEY]["data"] == {"known_wallets": ["a", "b"], "future": {"x": 1}}


async def test_a_change_waiting_to_be_saved_is_written_when_home_assistant_stops(
    hass, hass_storage
):
    """A mark advanced just before a stop is there at the next start: Home
    Assistant writes the delayed saves at its final write."""
    hass_storage[_KEY] = _file(known_rewards={"vsn": "2026-09-22T17:16:35Z"})
    store = await _loaded(hass)
    store.reward_marks.advance("vsn", "2026-09-29T16:20:00Z")
    hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)
    await hass.async_block_till_done()
    assert hass_storage[_KEY]["data"]["known_rewards"] == {"vsn": "2026-09-29T16:20:00Z"}


async def test_one_store_per_entry_outlives_its_reloads(hass, hass_storage):
    """Loaded once: a reload never reads a file whose last change still
    waits to be saved, and never makes a second writer."""
    hass_storage[_KEY] = _stored("a")
    first = await async_get_portfolio_store(hass, "eid")
    second = await async_get_portfolio_store(hass, "eid")
    assert first is second and "a" in first.known_wallets


async def test_removing_the_store_deletes_its_file(hass, hass_storage, freezer):
    store = await async_get_portfolio_store(hass, "eid")
    store.known_wallets.seed({"a"})
    store.reward_marks.seed({"vsn": "2026-09-22T17:16:35Z"})
    await _flush(hass, freezer)
    await async_remove_portfolio_store(hass, "eid")
    assert _KEY not in hass_storage
    fresh = await async_get_portfolio_store(hass, "eid")
    assert fresh is not store
    assert (fresh.known_wallets.first_run, fresh.reward_marks.first_run) == (True, True)


async def test_deleting_a_portfolio_not_set_up_since_the_start_deletes_its_file(
    hass, hass_storage
):
    """A disabled Portfolio never loads its store: the file still goes."""
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", entry_id="eid",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR"},
    )
    entry.add_to_hass(hass)
    hass_storage[_KEY] = _stored("a")
    await async_remove_entry(hass, entry)
    assert _KEY not in hass_storage


async def test_deleting_the_price_tracker_leaves_the_portfolios_file(hass, hass_storage):
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="price_tracker", entry_id="tracker",
        data={"entry_type": "price_tracker"},
    )
    entry.add_to_hass(hass)
    hass_storage[_KEY] = _stored("a")
    await async_remove_entry(hass, entry)
    assert hass_storage[_KEY]["data"] == {"known_wallets": ["a"]}
