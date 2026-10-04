"""A Portfolio currency change end to end, through a real recorder.

Confirming the change deletes every Portfolio sensor with its history and
its long-term statistics, then recreates them in the new currency under the
same entity IDs -- with exactly one reload, and without the update listener
Home Assistant warns about. What the version 1 migration left in place keeps
its entity and its history. The history and statistics that sensors removed
earlier left -- a sold asset's wallet, a Staking sensor with nothing staked --
go too: such a sensor, back in the new currency, records statistics again.

A new Portfolio after a deleted one takes the integration's entity IDs
again, where the deleted one's statistics may wait in another currency:
setup offers to delete them, and deleting them lets the new sensors record
statistics in the new currency.
"""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from awesomeversion import AwesomeVersion
import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import __version__ as HAVERSION
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_purge_done,
    async_wait_recording_done,
    do_adhoc_statistics,
    get_start_time,
)

from custom_components.bitpanda.const import (
    DOMAIN,
    PORTFOLIO_UPDATE_INTERVAL,
    TROUBLESHOOTING_URL,
)

from tests.conftest import load_fixture, recorded_history, statistics_units

_CLIENT = "custom_components.bitpanda.api.BitpandaApiClient."
_EUR_ID = "b88b8466-efe3-11eb-b56f-0691764446a7"
_USD_ID = "b88b8879-efe3-11eb-b56f-0691764446a7"
_TOTAL = "sensor.bitpanda_portfolio_total"
_CASH = "sensor.bitpanda_portfolio_cash"
_WALLET = "sensor.bitpanda_vision_vsn_wallet_available"
_STAKING = "sensor.bitpanda_vision_vsn_wallet_staking"
_VSN_TOTAL = "sensor.bitpanda_vision_vsn_wallet_total"
_VSN_SENSORS = [_WALLET, _STAKING, _VSN_TOTAL]
# What a template sensor named "Bitpanda Crypto Wallet Total" gets: not the
# Portfolio's, yet an ID of the Portfolio's form.
_LOOK_ALIKE = "sensor.bitpanda_crypto_wallet_total"
# A fiat wallet the version 1 migration left in place: Portfolio Cash covers
# every fiat balance now.
_LEFTOVER = "sensor.bitpanda_wallets_usd_wallet"

VSN = next(a for a in load_fixture("assets-sample.json") if a["symbol"] == "VSN")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Replaces the shared fixture of the same name for this module: the
    recorder must be set up before Home Assistant itself, and this order of
    arguments is what guarantees it."""
    return


def _lookup(**kwargs):
    return [a for a in load_fixture("assets-sample.json") if a["id"] == kwargs.get("asset_id")]


@pytest.fixture
def portfolio_api():
    response = [
        {
            "asset_id": VSN["id"],
            "balance": {"value": "100.00000000"},
            "available_balance": {"value": "25.00000000"},
            "currency_balance": {"value": "200.00"},
        },
        {"currency_id": _EUR_ID, "balance": {"value": "10.00"}},
    ]
    with patch(f"{_CLIENT}async_get_portfolio", AsyncMock(return_value=response)) as portfolio, patch(
        f"{_CLIENT}async_get_portfolio_history", AsyncMock(return_value={"return_percentage": 1.5})
    ), patch(f"{_CLIENT}async_get_earn_configs", AsyncMock(return_value=[])), patch(
        f"{_CLIENT}async_get_operations", AsyncMock(return_value=[])
    ), patch(f"{_CLIENT}async_get_assets", AsyncMock(side_effect=_lookup)), patch(
        f"{_CLIENT}async_get_currencies", AsyncMock(return_value=load_fixture("currencies.json"))
    ):
        yield portfolio


def _entity_ids(hass, entry) -> list[str]:
    return sorted(
        reg_entry.entity_id
        for reg_entry in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    )


def _portfolio(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, unique_id="portfolio", title="Bitpanda Portfolio",
        data={"entry_type": "portfolio", "api_key": "key", "currency": "EUR",
              "currency_id": _EUR_ID},
    )
    entry.add_to_hass(hass)
    return entry


async def _change_currency_to_usd(hass, entry) -> None:
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"currency": "usd"})
    assert result["step_id"] == "confirm_currency"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "change_currency"}
    )
    assert result["reason"] == "currency_changed"
    await async_wait_purge_done(hass)


async def test_a_currency_change_clears_the_statistics_of_every_portfolio_sensor(
    hass, portfolio_api
):
    """Every Portfolio sensor keeps long-term statistics, in the Portfolio
    currency -- the returns in %. Old-currency statistics would sit beside
    the new currency's, so the change clears them, for every one."""
    entry = _portfolio(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await async_wait_recording_done(hass)
    sensors = _entity_ids(hass, entry)
    # Eight figures, and the staked VSN's Wallet, Staking and Total.
    assert len(sensors) == 11
    do_adhoc_statistics(hass, start=get_start_time(dt_util.utcnow()))
    await async_wait_recording_done(hass)
    assert await statistics_units(hass, sensors) == {
        entity_id: "%" if "_return_" in entity_id else "EUR" for entity_id in sensors
    }

    await _change_currency_to_usd(hass, entry)
    await async_wait_recording_done(hass)

    assert _entity_ids(hass, entry) == sensors
    assert await statistics_units(hass, sensors) == {}


async def test_a_currency_change_recreates_the_sensors_without_the_old_history(
    hass, portfolio_api, caplog
):
    entry = _portfolio(hass)
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_wallet_fiat_USD", config_entry=entry,
        suggested_object_id=_LEFTOVER.split(".", 1)[1],
    )
    hass.states.async_set(_LEFTOVER, "5.0", {"unit_of_measurement": "USD"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await async_wait_recording_done(hass)
    entity_ids = _entity_ids(hass, entry)
    assert {_WALLET, _LEFTOVER} <= set(entity_ids)
    assert await recorded_history(hass, _WALLET) == [("50.0", "EUR")]
    assert await recorded_history(hass, _LEFTOVER) == [("5.0", "USD")]
    calls = portfolio_api.call_count
    [group] = entry.subentries.values()

    await _change_currency_to_usd(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.data["currency"] == "USD"
    assert _entity_ids(hass, entry) == entity_ids
    # The purge (purge.py) removes entities and devices, not the wallet
    # group's subentry; the reload then refills the same group.
    [after] = entry.subentries.values()
    assert (after.subentry_id, after.title) == (group.subentry_id, group.title)
    assert er.async_get(hass).async_get(_WALLET).config_subentry_id == after.subentry_id
    assert hass.states.get(_WALLET).attributes["unit_of_measurement"] == "USD"
    # One reload: one more /portfolio request, now in the new currency.
    assert portfolio_api.call_count == calls + 1
    assert portfolio_api.call_args.kwargs == {"equivalent_currency_id": _USD_ID}
    # The EUR history is gone; the state the recreated sensor wrote is kept.
    assert await recorded_history(hass, _WALLET) == [("50.0", "USD")]
    # The leftover is not the Portfolio's own: the migration promised it
    # stays until the user deletes it, and so does its history.
    assert await recorded_history(hass, _LEFTOVER) == [("5.0", "USD")]
    assert "update listener" not in caplog.text


async def _next_refresh(hass, freezer) -> None:
    """The Portfolio's next regular refresh: Home Assistant's clock moves on
    past its update interval, and the refresh it scheduled runs to its end
    -- a background task, which only wait_background_tasks waits for."""
    freezer.tick(PORTFOLIO_UPDATE_INTERVAL + timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_an_empty_answer_right_after_a_currency_change_waits_for_confirmation(
    hass, portfolio_api, freezer
):
    """The purge has just removed the wallets when the reload asks, so none
    is registered; that the account listed something is remembered all the
    same. An empty answer then -- as likely a glitch at Bitpanda as ever --
    leaves the Portfolio unavailable until three answers in a row, at the
    usual pace, confirm it, rather than start the new currency's history
    with a 0."""
    entry = _portfolio(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await async_wait_recording_done(hass)
    portfolio_api.return_value = []

    await _change_currency_to_usd(hass, entry)

    assert er.async_get(hass).async_get(_WALLET) is None
    for _ in range(2):
        assert hass.states.get(_TOTAL).state == "unavailable"
        await _next_refresh(hass, freezer)
    assert float(hass.states.get(_TOTAL).state) == 0.0


# --- Sensors removed before the change ---------------------------------------------


async def _set_up_with_statistics(hass) -> MockConfigEntry:
    """The Portfolio, set up in EUR, with long-term statistics for VSN's
    wallet sensors."""
    entry = _portfolio(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await async_wait_recording_done(hass)
    do_adhoc_statistics(hass, start=get_start_time(dt_util.utcnow()))
    await async_wait_recording_done(hass)
    assert await statistics_units(hass, _VSN_SENSORS) == dict.fromkeys(_VSN_SENSORS, "EUR")
    return entry


async def _sell_vsn(hass, portfolio_api, freezer) -> dict:
    """VSN is sold: three refreshes without it remove its wallet (the pace of
    WALLET_REMOVAL_MISSES and WALLET_REMOVAL_TIME). Returns its position."""
    position, eur = portfolio_api.return_value
    portfolio_api.return_value = [eur]
    for _ in range(3):
        await _next_refresh(hass, freezer)
    ent_reg = er.async_get(hass)
    assert [entity_id for entity_id in _VSN_SENSORS if ent_reg.async_get(entity_id)] == []
    return position


async def test_a_currency_change_clears_the_statistics_of_a_sold_wallet(
    hass, portfolio_api, freezer
):
    """The wallet of an asset sold before the change is gone, its sensors
    with it -- not their statistics and their history, in the old currency.
    Both go, as the current sensors' do."""
    entry = await _set_up_with_statistics(hass)
    await _sell_vsn(hass, portfolio_api, freezer)
    # Its EUR state, then its removal.
    assert ("50.0", "EUR") in await recorded_history(hass, _WALLET)
    # Time passes before the change: the purge spares what is recorded at its
    # own moment, and the frozen clock would put the removal there.
    freezer.tick(timedelta(seconds=1))

    await _change_currency_to_usd(hass, entry)
    await async_wait_recording_done(hass)

    assert await statistics_units(hass, _VSN_SENSORS) == {}
    assert [await recorded_history(hass, entity_id) for entity_id in _VSN_SENSORS] == [[], [], []]


async def test_a_wallet_bought_again_after_a_currency_change_records_statistics(
    hass, portfolio_api, freezer
):
    """Bought again, the wallet comes back under the same entity IDs, in the
    new currency. Home Assistant cannot convert the old statistics, so it
    would record none while they are left."""
    entry = await _set_up_with_statistics(hass)
    position = await _sell_vsn(hass, portfolio_api, freezer)
    await _change_currency_to_usd(hass, entry)

    portfolio_api.return_value = [position, *portfolio_api.return_value]
    await _next_refresh(hass, freezer)
    await async_wait_recording_done(hass)
    # The periods follow the clock the refreshes moved on.
    do_adhoc_statistics(hass, start=get_start_time(dt_util.utcnow()))
    await async_wait_recording_done(hass)

    assert await statistics_units(hass, _VSN_SENSORS) == dict.fromkeys(_VSN_SENSORS, "USD")


# Home Assistant gives a re-created entity the entity ID its user chose only
# from 2025.7 on; before, it comes back under the integration's own ID
# (README, "Resetting names and entity IDs").
_RESTORES_ENTITY_IDS = AwesomeVersion(HAVERSION) >= AwesomeVersion("2025.7.0")


async def test_a_wallet_the_user_renamed_records_statistics_after_a_currency_change(
    hass, portfolio_api, freezer
):
    """Home Assistant 2025.7 and later give a returning sensor the entity ID
    the user gave it, which the Portfolio's form does not match. The entity
    registry remembers that ID for the sold wallet: the change clears the
    statistics under it too. Before 2025.7 the wallet comes back under the
    integration's ID, and records there."""
    renamed = "sensor.vsn_total"
    returned = renamed if _RESTORES_ENTITY_IDS else _VSN_TOTAL
    entry = _portfolio(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    er.async_get(hass).async_update_entity(_VSN_TOTAL, new_entity_id=renamed)
    await async_wait_recording_done(hass)
    do_adhoc_statistics(hass, start=get_start_time(dt_util.utcnow()))
    await async_wait_recording_done(hass)
    assert await statistics_units(hass, [renamed]) == {renamed: "EUR"}
    position = await _sell_vsn(hass, portfolio_api, freezer)
    assert er.async_get(hass).async_get(renamed) is None

    await _change_currency_to_usd(hass, entry)
    await async_wait_recording_done(hass)
    assert await statistics_units(hass, [renamed]) == {}

    portfolio_api.return_value = [position, *portfolio_api.return_value]
    await _next_refresh(hass, freezer)
    assert er.async_get(hass).async_get(returned) is not None
    await async_wait_recording_done(hass)
    do_adhoc_statistics(hass, start=get_start_time(dt_util.utcnow()))
    await async_wait_recording_done(hass)
    assert await statistics_units(hass, [returned]) == {returned: "USD"}


async def test_a_currency_change_clears_the_statistics_of_a_removed_staking_sensor(
    hass, portfolio_api, freezer
):
    """Nothing staked any more, and Earn offers nothing for the asset: the
    Staking sensor goes, its wallet stays. Its statistics, in the old
    currency, go with the change."""
    entry = await _set_up_with_statistics(hass)
    position, eur = portfolio_api.return_value
    portfolio_api.return_value = [{**position, "available_balance": position["balance"]}, eur]
    await _next_refresh(hass, freezer)
    ent_reg = er.async_get(hass)
    assert ent_reg.async_get(_STAKING) is None
    assert ent_reg.async_get(_WALLET) is not None

    await _change_currency_to_usd(hass, entry)
    await async_wait_recording_done(hass)

    assert await statistics_units(hass, [_STAKING]) == {}


async def test_a_live_look_alike_keeps_its_statistics_through_a_currency_change(
    hass, portfolio_api
):
    """A sensor with a state under an ID of the Portfolio's form -- a
    template's, say -- is not one the Portfolio removed: its statistics and
    its history stay."""
    entry = _portfolio(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    hass.states.async_set(
        _LOOK_ALIKE, "1.0", {"state_class": "measurement", "unit_of_measurement": "CHF"}
    )
    await async_wait_recording_done(hass)
    do_adhoc_statistics(hass, start=get_start_time(dt_util.utcnow()))
    await async_wait_recording_done(hass)
    assert await statistics_units(hass, [_LOOK_ALIKE]) == {_LOOK_ALIKE: "CHF"}

    await _change_currency_to_usd(hass, entry)
    await async_wait_recording_done(hass)

    assert await statistics_units(hass, [_LOOK_ALIKE]) == {_LOOK_ALIKE: "CHF"}
    assert await recorded_history(hass, _LOOK_ALIKE) == [("1.0", "CHF")]


# --- A new Portfolio after a deleted one -------------------------------------------


async def test_a_new_portfolio_takes_the_integrations_entity_ids_again(hass, portfolio_api):
    """A deleted Portfolio keeps its statistics under its sensors' IDs. A new
    setup is a new entry with new unique_ids, so Home Assistant restores none
    of the deleted entry's IDs -- not even one the user gave: the new sensors
    take the integration's own IDs, where async_find_old_statistics looks."""
    old = _portfolio(hass)
    assert await hass.config_entries.async_setup(old.entry_id)
    await hass.async_block_till_done()
    er.async_get(hass).async_update_entity(_CASH, new_entity_id="sensor.my_cash")
    ids = _entity_ids(hass, old)
    await hass.config_entries.async_remove(old.entry_id)

    new = _portfolio(hass)
    assert await hass.config_entries.async_setup(new.entry_id)
    await hass.async_block_till_done()

    assert _entity_ids(hass, new) == sorted(
        _CASH if entity_id == "sensor.my_cash" else entity_id for entity_id in ids
    )


async def _set_up_portfolio(hass, currency: str):
    """The Portfolio's setup dialog, up to what follows its currency step."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "portfolio"}
    )
    with patch(f"{_CLIENT}async_missing_scopes", AsyncMock(return_value=[])):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"api_key": "key"}
        )
    return await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "currency": {"currency": currency},
            "language": {"language": "en"},
            "notifications": {"notify_new_wallets": True},
        },
    )


async def test_a_new_setup_in_another_currency_deletes_the_old_statistics_when_asked(
    hass, portfolio_api
):
    old = _portfolio(hass)
    assert await hass.config_entries.async_setup(old.entry_id)
    await async_wait_recording_done(hass)
    sensors = _entity_ids(hass, old)
    start = get_start_time(dt_util.utcnow())
    do_adhoc_statistics(hass, start=start)
    await async_wait_recording_done(hass)
    await hass.config_entries.async_remove(old.entry_id)
    await async_wait_recording_done(hass)

    result = await _set_up_portfolio(hass, "usd")
    assert (result["type"], result["step_id"]) == (FlowResultType.MENU, "old_statistics")
    assert result["description_placeholders"] == {
        "old": "EUR", "new": "USD", "troubleshooting_url": TROUBLESHOOTING_URL,
    }
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "delete_statistics"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    await async_wait_purge_done(hass)
    await async_wait_recording_done(hass)

    assert _entity_ids(hass, result["result"]) == sensors
    # The old history is gone; what the new Portfolio wrote since is kept.
    assert await recorded_history(hass, _WALLET) == [("50.0", "USD")]
    # A later period: the first one counts as compiled.
    do_adhoc_statistics(hass, start=start + timedelta(minutes=5))
    await async_wait_recording_done(hass)
    assert await statistics_units(hass, sensors) == {
        entity_id: "%" if "_return_" in entity_id else "USD" for entity_id in sensors
    }
