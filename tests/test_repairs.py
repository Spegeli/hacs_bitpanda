"""The upgrade's repair issue for the entities it could not migrate.

Its dialog lists them as they are when it opens and, after a
confirmation, deletes them with each old device they leave empty. Only
entities of the old version count: its wallets and prices that are still
entities of the Portfolio -- never a sensor the Portfolio manages, an
entity of another entry, or a price the Price Tracker has yet to adopt.
The issue exists while such entities do: every start of the Portfolio
raises it, keeps its list current and deletes it once nothing is left.
"""
import json
import logging
from pathlib import Path

from homeassistant.components.repairs import ConfirmRepairFlow, repairs_flow_manager
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bitpanda import migration, repairs
from custom_components.bitpanda.const import DOMAIN
from custom_components.bitpanda.devices import find_entry_device
from custom_components.bitpanda.naming import (
    PORTFOLIO_KEYS,
    portfolio_device_identifier,
    portfolio_unique_id,
    price_unique_id,
    staking_unique_id,
    total_unique_id,
    wallet_device_identifier,
    wallet_unique_id,
)

_ISSUE = "entities_not_migrated"
_VSN = "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb"


def _portfolio(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR",
              "currency_id": "b88b8466-efe3-11eb-b56f-0691764446a7"},
    )
    entry.add_to_hass(hass)
    return entry


def _device(hass, entry, identifier: str, name: str) -> dr.DeviceEntry:
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, identifier)}, name=name
    )


def _entity(hass, entry, unique_id: str, object_id: str, device: dr.DeviceEntry) -> str:
    return er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, unique_id, config_entry=entry, device_id=device.id,
        suggested_object_id=object_id,
    ).entity_id


def _upgraded(hass) -> tuple[MockConfigEntry, list[str]]:
    """A Portfolio after the upgrade: its own figure and wallet on their
    devices, and two wallets of the old version on an old device."""
    entry = _portfolio(hass)
    eid = entry.entry_id
    portfolio = _device(hass, entry, portfolio_device_identifier(eid), "Portfolio")
    _entity(hass, entry, portfolio_unique_id(eid, "total"), "bitpanda_portfolio_total", portfolio)
    wallet = _device(hass, entry, wallet_device_identifier(eid, _VSN), "Vision (VSN) Wallet")
    _entity(hass, entry, wallet_unique_id(eid, _VSN), "bitpanda_vision_vsn_wallet_available", wallet)
    old = _device(hass, entry, f"{eid}_wallets", "Bitpanda Wallets (old version, not migrated)")
    left = [
        _entity(hass, entry, f"{eid}_wallet_cryptocoin_STONKBROKER",
                "bitpanda_wallets_stonkbroker_wallet", old),
        _entity(hass, entry, f"{eid}_wallet_fiat_USD", "bitpanda_wallets_usd_wallet", old),
    ]
    return entry, left


async def _open(hass) -> dict:
    """The issue's dialog, as Repairs opens it. Repairs takes the dialog
    from repairs.py only while the integration is loaded -- otherwise it
    shows a plain confirmation that deletes nothing -- so it counts as
    loaded here, without a setup that would call Bitpanda."""
    hass.config.components.add(DOMAIN)
    assert await async_setup_component(hass, "repairs", {})
    manager = repairs_flow_manager(hass)
    assert manager is not None
    return await manager.async_init(DOMAIN, data={"issue_id": _ISSUE})


async def _confirm(hass) -> dict:
    """Open the dialog and confirm it."""
    result = await _open(hass)
    return await repairs_flow_manager(hass).async_configure(result["flow_id"], {})


def _issue(hass) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, _ISSUE)


def _registered(hass) -> set[str]:
    return set(er.async_get(hass).entities)


def _devices(hass, entry) -> set[str]:
    return {
        device.name
        for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    }


# --- The dialog ------------------------------------------------------------------


async def test_confirming_deletes_the_entities_and_the_old_device_they_leave_empty(hass):
    entry, left = _upgraded(hass)
    migration.async_raise_not_migrated_issue(hass, entry.entry_id, left)
    issue = _issue(hass)
    assert (issue.is_fixable, issue.is_persistent) == (True, True)
    assert issue.data == {"entry_id": entry.entry_id}

    result = await _open(hass)
    assert (result["type"], result["step_id"]) == (FlowResultType.FORM, "confirm")
    assert result["description_placeholders"] == {
        "entities": f"- `{left[0]}`\n- `{left[1]}`"
    }
    result = await repairs_flow_manager(hass).async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert _registered(hass) == {
        "sensor.bitpanda_portfolio_total", "sensor.bitpanda_vision_vsn_wallet_available",
    }
    assert _devices(hass, entry) == {"Portfolio", "Vision (VSN) Wallet"}
    assert _issue(hass) is None


async def test_closing_the_dialog_deletes_nothing(hass):
    entry, left = _upgraded(hass)
    migration.async_raise_not_migrated_issue(hass, entry.entry_id, left)
    result = await _open(hass)
    repairs_flow_manager(hass).async_abort(result["flow_id"])
    assert set(left) <= _registered(hass)
    assert "Bitpanda Wallets (old version, not migrated)" in _devices(hass, entry)
    assert _issue(hass) is not None


async def test_the_dialog_lists_the_entities_as_they_are_when_it_opens(hass):
    """Since the last start, the user deleted one entity by hand and gave
    another an ID of their own: the dialog lists the second under its new
    ID, and deletes it."""
    entry, left = _upgraded(hass)
    migration.async_raise_not_migrated_issue(hass, entry.entry_id, left)
    ent_reg = er.async_get(hass)
    ent_reg.async_remove(left[1])
    ent_reg.async_update_entity(left[0], new_entity_id="sensor.my_stonkbroker")

    result = await _open(hass)
    assert result["description_placeholders"] == {"entities": "- `sensor.my_stonkbroker`"}
    await repairs_flow_manager(hass).async_configure(result["flow_id"], {})
    assert not {"sensor.my_stonkbroker", *left} & _registered(hass)
    assert "Bitpanda Wallets (old version, not migrated)" not in _devices(hass, entry)


async def test_the_dialog_closes_the_issue_when_nothing_is_left(hass):
    entry, left = _upgraded(hass)
    migration.async_raise_not_migrated_issue(hass, entry.entry_id, left)
    for entity_id in left:
        er.async_get(hass).async_remove(entity_id)
    result = await _open(hass)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert _issue(hass) is None


async def test_only_entities_of_the_old_version_are_ever_deleted(hass):
    """A sensor the Portfolio manages, one of a kind the old version never
    had, and an entity of another entry -- even with an ID shaped like an
    old price -- are never listed, and never deleted."""
    entry, left = _upgraded(hass)
    eid = entry.entry_id
    portfolio = find_entry_device(dr.async_get(hass), eid, portfolio_device_identifier(eid))
    newer = _entity(hass, entry, f"{eid}_some_later_figure", "bitpanda_portfolio_later", portfolio)
    tracker = MockConfigEntry(domain=DOMAIN, unique_id="price_tracker",
                              data={"entry_type": "price_tracker"})
    tracker.add_to_hass(hass)
    foreign = er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{eid}_STONKBROKER_price_EUR", config_entry=tracker,
        suggested_object_id="bitpanda_stonkbroker_price",
    ).entity_id
    migration.async_raise_not_migrated_issue(hass, eid, left)

    result = await _open(hass)
    assert result["description_placeholders"] == {
        "entities": f"- `{left[0]}`\n- `{left[1]}`"
    }
    await repairs_flow_manager(hass).async_configure(result["flow_id"], {})
    assert {
        "sensor.bitpanda_portfolio_total", "sensor.bitpanda_vision_vsn_wallet_available",
        newer, foreign,
    } <= _registered(hass)


async def test_only_the_old_versions_ids_are_ever_left_over(hass):
    """Every unique_id the integration builds today -- the Portfolio's
    figures, wallets, staking and totals, the Price Tracker's prices -- and
    a later figure with "_price_" in its key are never taken for an entity
    of the old version, whose wallet and price IDs are."""
    entry, left = _upgraded(hass)
    eid = entry.entry_id
    portfolio = find_entry_device(dr.async_get(hass), eid, portfolio_device_identifier(eid))
    ours = [
        *(portfolio_unique_id(eid, key) for key in PORTFOLIO_KEYS),
        wallet_unique_id(eid, _VSN), staking_unique_id(eid, _VSN), total_unique_id(eid, _VSN),
        price_unique_id(eid, _VSN, "EUR"), f"{eid}_avg_buy_price_{_VSN}",
    ]
    for number, unique_id in enumerate(ours):
        if er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id) is None:
            _entity(hass, entry, unique_id, f"bitpanda_ours_{number}", portfolio)
    old_prices = _device(hass, entry, f"{eid}_price_tracker", "Bitpanda Price Tracker")
    price = _entity(hass, entry, f"{eid}_BTC_price_EUR", "bitpanda_price_tracker_btc_eur", old_prices)
    assert migration.left_over_entity_ids(hass, eid) == sorted([*left, price])


async def test_every_start_names_an_old_device_that_keeps_an_entity(hass):
    """An upgrade by 2.0.0-beta.1 left the old devices under their old
    names: the next start of the Portfolio names them as not migrated."""
    entry, left = _upgraded(hass)
    dev_reg = dr.async_get(hass)
    old = find_entry_device(dev_reg, entry.entry_id, f"{entry.entry_id}_wallets")
    dev_reg.async_update_device(old.id, name="Bitpanda Wallets")
    migration.async_update_left_overs(hass, entry)
    assert dev_reg.async_get(old.id).name == "Bitpanda Wallets (old version, not migrated)"


async def test_every_start_deletes_an_old_device_left_empty(hass):
    """The user deleted the old entities by hand: their old device goes at
    the next start of the Portfolio, with the issue."""
    entry, left = _upgraded(hass)
    old = find_entry_device(dr.async_get(hass), entry.entry_id, f"{entry.entry_id}_wallets")
    for entity_id in left:
        er.async_get(hass).async_remove(entity_id)
    migration.async_update_left_overs(hass, entry)
    assert dr.async_get(hass).async_get(old.id) is None
    assert _issue(hass) is None


async def test_a_price_the_price_tracker_has_yet_to_adopt_is_never_listed(hass):
    """An old price the new Price Tracker is still to take over -- its setup
    stopped before it did -- is no entity left over. It stays, disabled or
    not, and so does the old device that holds it."""
    entry, left = _upgraded(hass)
    eid = entry.entry_id
    old_prices = _device(hass, entry, f"{eid}_price_tracker", "Bitpanda Price Tracker")
    waiting = _entity(hass, entry, f"{eid}_BTC_price_EUR", "bitpanda_price_tracker_btc_eur",
                      old_prices)
    er.async_get(hass).async_update_entity(
        waiting, disabled_by=er.RegistryEntryDisabler.USER
    )
    MockConfigEntry(
        domain=DOMAIN, unique_id="price_tracker",
        data={"entry_type": "price_tracker",
              "legacy_adopt": {"source_entry_id": eid,
                               "entities": [{"unique_id": f"{eid}_BTC_price_EUR"}]}},
    ).add_to_hass(hass)
    migration.async_raise_not_migrated_issue(hass, eid, left)

    result = await _open(hass)
    assert waiting not in result["description_placeholders"]["entities"]
    await repairs_flow_manager(hass).async_configure(result["flow_id"], {})
    assert waiting in _registered(hass)
    assert dr.async_get(hass).async_get(old_prices.id) is not None


async def test_the_portfolios_own_devices_stay_even_without_entities(hass):
    """The dialog deletes old devices only: a device of the Portfolio's own
    stays, empty or not -- the Portfolio itself looks after it."""
    entry, left = _upgraded(hass)
    er.async_get(hass).async_remove("sensor.bitpanda_vision_vsn_wallet_available")
    migration.async_raise_not_migrated_issue(hass, entry.entry_id, left)
    await _confirm(hass)
    assert _devices(hass, entry) == {"Portfolio", "Vision (VSN) Wallet"}


async def test_the_deletion_is_logged(hass, caplog):
    entry, left = _upgraded(hass)
    migration.async_raise_not_migrated_issue(hass, entry.entry_id, left)
    with caplog.at_level(logging.INFO, logger="custom_components.bitpanda.migration"):
        await _confirm(hass)
    assert "Deleted what the upgrade left in place -- entities: 2, old devices: 1" in caplog.text


async def test_only_this_issue_has_this_dialog(hass):
    """Another issue, should one ever be fixable, gets Home Assistant's
    plain confirmation, never the dialog that deletes."""
    assert isinstance(await repairs.async_create_fix_flow(hass, "another", None), ConfirmRepairFlow)


def test_the_dialog_has_its_texts_in_every_language():
    """A fixable issue's text is its dialog's: the issue itself has a title
    only (hassfest allows a description or a dialog, never both)."""
    files = [
        Path(migration.__file__).parent / "strings.json",
        *sorted((Path(migration.__file__).parent / "translations").glob("*.json")),
    ]
    assert len(files) == 8
    for path in files:
        issue = json.loads(path.read_text(encoding="utf-8"))["issues"][_ISSUE]
        assert set(issue) == {"title", "fix_flow"}, path.name
        confirm = issue["fix_flow"]["step"]["confirm"]
        assert set(confirm) == {"title", "description", "submit"}, path.name
        assert "\n\n{entities}\n\n" in confirm["description"], path.name


# --- Every start of the Portfolio ---------------------------------------------------


async def test_every_start_lists_what_is_left(hass):
    entry, left = _upgraded(hass)
    migration.async_raise_not_migrated_issue(hass, entry.entry_id, left)
    er.async_get(hass).async_remove(left[1])
    migration.async_update_left_overs(hass, entry)
    issue = _issue(hass)
    assert issue.translation_placeholders == {"entities": f"- `{left[0]}`"}
    assert issue.data == {"entry_id": entry.entry_id}


async def test_the_issue_goes_once_nothing_is_left(hass):
    entry, left = _upgraded(hass)
    migration.async_raise_not_migrated_issue(hass, entry.entry_id, left)
    for entity_id in left:
        er.async_get(hass).async_remove(entity_id)
    migration.async_update_left_overs(hass, entry)
    assert _issue(hass) is None


async def test_the_issue_of_the_first_beta_gets_the_dialog(hass):
    """2.0.0-beta.1 raised the issue without a dialog: the next start makes
    it the issue that deletes."""
    entry, left = _upgraded(hass)
    ir.async_create_issue(
        hass, DOMAIN, _ISSUE, is_fixable=False, is_persistent=True,
        severity=ir.IssueSeverity.WARNING, translation_key=_ISSUE,
        translation_placeholders={"entities": f"- `{left[0]}`\n- `{left[1]}`"},
    )
    migration.async_update_left_overs(hass, entry)
    issue = _issue(hass)
    assert issue.is_fixable
    assert issue.data == {"entry_id": entry.entry_id}


async def test_a_start_raises_the_issue_while_old_entities_remain(hass):
    """Home Assistant's plain confirmation -- all it shows while the
    integration is not loaded -- deletes the issue but nothing else: the
    next start raises it again."""
    entry, left = _upgraded(hass)
    migration.async_update_left_overs(hass, entry)
    issue = _issue(hass)
    assert issue.is_fixable
    assert issue.translation_placeholders == {"entities": f"- `{left[0]}`\n- `{left[1]}`"}


async def test_a_portfolio_without_old_entities_raises_none(hass):
    entry, left = _upgraded(hass)
    for entity_id in left:
        er.async_get(hass).async_remove(entity_id)
    migration.async_update_left_overs(hass, entry)
    assert _issue(hass) is None


async def test_an_ignored_issue_stays_ignored(hass):
    entry, left = _upgraded(hass)
    migration.async_raise_not_migrated_issue(hass, entry.entry_id, left)
    ir.async_ignore_issue(hass, DOMAIN, _ISSUE, True)
    er.async_get(hass).async_remove(left[1])
    migration.async_update_left_overs(hass, entry)
    issue = _issue(hass)
    assert issue.dismissed_version is not None
    assert issue.translation_placeholders == {"entities": f"- `{left[0]}`"}
