"""The README: its automation examples copyable as they stand, and its
Home Assistant badge in step with hacs.json.

Each YAML block of the "Automation examples" section is what a user pastes
into a new automation's YAML editor, so each must load as a valid
automation, and use the entity IDs the integration creates.
"""
from datetime import timedelta
import json
from pathlib import Path
import re

from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service
import yaml

from custom_components.bitpanda.naming import (
    portfolio_entity_id,
    price_entity_id,
    return_key,
    staking_entity_id,
)

from tests.conftest import load_fixture

_ROOT = Path(__file__).parent.parent
_README = (_ROOT / "README.md").read_text(encoding="utf-8")
_SECTION = "\n## \U0001f916 Automation examples\n"


def _examples() -> list[dict]:
    """The section's YAML blocks, in order."""
    start = _README.index(_SECTION)
    end = _README.index("\n## ", start + len(_SECTION))
    return [
        yaml.safe_load(block)
        for block in re.findall(r"```yaml\n(.*?)```", _README[start:end], re.DOTALL)
    ]


_PRICE = "sensor.bitpanda_bitcoin_btc_price_tracker_eur"
_TOTAL = "sensor.bitpanda_portfolio_total"
_DAY = "sensor.bitpanda_portfolio_return_day"
_STAKING = "sensor.bitpanda_ethereum_eth_wallet_staking"


def test_the_examples_are_an_alert_a_big_move_a_report_and_a_reward():
    alert, move, report, reward = _examples()
    [trigger] = alert["triggers"]
    assert (trigger["trigger"], set(trigger) & {"above", "below"}) == ("numeric_state", {"above"})
    assert [
        (each["trigger"], each["attribute"], set(each) & {"above", "below"})
        for each in move["triggers"]
    ] == [
        ("numeric_state", "change_24h_pct", {"above"}),
        ("numeric_state", "change_24h_pct", {"below"}),
    ]
    refreshed, notified = report["actions"]
    assert refreshed == {"action": "bitpanda.refresh", "continue_on_error": True}
    # The step the example exists for: it runs even when the refresh failed,
    # and then shows the last figures.
    assert notified["action"] == "persistent_notification.create"
    [counted] = reward["triggers"]
    assert (counted["trigger"], counted["attribute"]) == ("state", "rewards_count")


def test_the_examples_watch_the_sensors_the_integration_creates():
    btc = next(asset for asset in load_fixture("assets-sample.json") if asset["symbol"] == "BTC")
    assert price_entity_id(btc, "EUR") == _PRICE
    assert portfolio_entity_id("total") == _TOTAL
    assert portfolio_entity_id(return_key("DAY")) == _DAY
    assert staking_entity_id({"symbol": "ETH", "name": "Ethereum"}) == _STAKING
    alert, move, report, reward = _examples()
    assert [each["entity_id"] for each in (*alert["triggers"], *move["triggers"])] == [_PRICE] * 3
    message = report["actions"][1]["data"]["message"]
    assert f"states('{_TOTAL}', with_unit=True)" in message
    assert f"states('{_DAY}', with_unit=True)" in message
    assert reward["triggers"][0]["entity_id"] == _STAKING


async def _set_up(hass, example: dict) -> list:
    """`example` as an automation; the notifications it sends."""
    assert await async_setup_component(hass, "automation", {"automation": [example]})
    await hass.async_block_till_done()
    return async_mock_service(hass, "persistent_notification", "create")


async def _set(hass, entity_id: str, state: str, **attributes) -> None:
    hass.states.async_set(entity_id, state, attributes)
    await hass.async_block_till_done()


async def _price(hass, state: str) -> None:
    await _set(hass, _PRICE, state, unit_of_measurement="EUR")


async def _turn_off(hass) -> None:
    await hass.services.async_call("automation", "turn_off", {"entity_id": "all"}, blocking=True)


def _messages(notifications: list) -> list[str]:
    return [call.data["message"] for call in notifications]


async def test_the_price_alert_fires_when_the_price_crosses_the_threshold(hass):
    """Once per crossing -- not again while the price stays above, and not
    when it merely comes back above after an outage. The message carries
    the sensor's own currency."""
    await _price(hass, "90000")
    notifications = await _set_up(hass, _examples()[0])

    await _price(hass, "100500")
    await _price(hass, "101000")
    assert _messages(notifications) == ["Bitcoin is at 100500 EUR."]

    for outage in ("unavailable", "unknown"):
        await _price(hass, outage)
        await _price(hass, "101500")
    assert len(notifications) == 1
    await _turn_off(hass)


async def test_the_price_alert_sends_at_most_one_message_an_hour(hass, freezer):
    """A price swinging around the threshold: a crossing within the hour of
    the last message stays quiet, the first one after it is reported."""
    await _price(hass, "90000")
    notifications = await _set_up(hass, _examples()[0])
    await _price(hass, "100500")

    freezer.tick(timedelta(minutes=59))
    await _price(hass, "99000")
    await _price(hass, "100200")
    assert len(notifications) == 1

    freezer.tick(timedelta(minutes=2))
    await _price(hass, "99500")
    await _price(hass, "100300")
    assert _messages(notifications) == ["Bitcoin is at 100500 EUR.", "Bitcoin is at 100300 EUR."]
    await _turn_off(hass)


@pytest.mark.parametrize("at_start", [None, "unavailable"], ids=["no_state", "restored"])
async def test_the_price_alert_stays_quiet_when_the_price_appears_after_a_restart(
    hass, at_start
):
    """After a restart the automation may start before the sensor has a
    value -- with no state at all, or with the `unavailable` placeholder
    Home Assistant restores for it: the first price above the threshold is
    no crossing."""
    if at_start is not None:
        hass.states.async_set(_PRICE, at_start, {"restored": True})
    notifications = await _set_up(hass, _examples()[0])
    await _price(hass, "102000")
    assert notifications == []
    await _turn_off(hass)


async def _change(hass, change: float | None) -> None:
    await _set(hass, _PRICE, "100000", unit_of_measurement="EUR", change_24h_pct=change)


async def test_the_big_move_alert_reports_a_rise_or_a_fall_at_most_once_an_hour(hass, freezer):
    await _change(hass, 4.0)
    notifications = await _set_up(hass, _examples()[1])
    await _change(hass, 10.5)
    assert _messages(notifications) == ["Bitcoin moved 10.5 % in 24 hours."]

    freezer.tick(timedelta(minutes=61))
    await _change(hass, 3.0)
    await _change(hass, -11.0)
    assert _messages(notifications)[1:] == ["Bitcoin moved -11.0 % in 24 hours."]

    await _change(hass, -9.0)
    await _change(hass, 10.2)
    assert len(notifications) == 2
    await _turn_off(hass)


async def test_the_big_move_alert_stays_quiet_when_the_change_first_appears(hass):
    """After a restart the 24-hour change is missing until the recorder has
    answered: its first value is no move."""
    await _change(hass, None)
    notifications = await _set_up(hass, _examples()[1])
    await _change(hass, 12.0)
    assert notifications == []
    await _turn_off(hass)


async def test_the_morning_report_comes_even_when_the_refresh_fails(hass):
    """The refresh fails, the report still comes, with the last figures and
    their units."""

    async def refresh(call) -> None:
        raise HomeAssistantError("Bitpanda could not be reached")

    hass.services.async_register("bitpanda", "refresh", refresh)
    await _set(hass, _TOTAL, "12345.67", unit_of_measurement="EUR")
    await _set(hass, _DAY, "1.25", unit_of_measurement="%")
    notifications = await _set_up(hass, _examples()[2])
    await hass.services.async_call(
        "automation", "trigger", {"entity_id": "automation.bitpanda_morning_report"}, blocking=True
    )
    await hass.async_block_till_done()
    assert _messages(notifications) == ["Portfolio: 12345.67 EUR, today 1.25 %"]
    await _turn_off(hass)


async def _rewards(hass, count: int | None, net: float = 0.1, units: str = "1.0") -> None:
    await _set(
        hass, _STAKING, units, unit_of_measurement="ETH", rewards_count=count, rewards_net=net
    )


async def test_the_staking_reward_alert_reports_each_new_payout(hass):
    """A higher payout count is reported; the same count -- even with other
    figures changed -- and a lower one are not."""
    await _rewards(hass, 3, 0.10)
    notifications = await _set_up(hass, _examples()[3])
    await _rewards(hass, 4, 0.12)
    await _rewards(hass, 4, 0.12, units="1.1")
    await _rewards(hass, 2, 0.12)
    assert _messages(notifications) == ["New reward: 0.12 ETH net so far."]
    await _turn_off(hass)


async def test_the_staking_reward_alert_stays_quiet_when_the_count_first_appears(hass):
    await _rewards(hass, None)
    notifications = await _set_up(hass, _examples()[3])
    await _rewards(hass, 5, 0.2)
    assert notifications == []
    await _turn_off(hass)


async def test_the_staking_reward_alert_stays_quiet_through_an_outage(hass, caplog):
    """The staking sensor turns unavailable, without its attributes, at every
    reload of the Portfolio and in an outage, and it can be removed: no
    message and no condition error then -- the next new payout is reported."""
    await _rewards(hass, 3, 0.10)
    notifications = await _set_up(hass, _examples()[3])
    await _set(hass, _STAKING, "unavailable")
    await _rewards(hass, 3, 0.10)
    await _rewards(hass, 4, 0.12)
    hass.states.async_remove(_STAKING)
    await hass.async_block_till_done()
    assert _messages(notifications) == ["New reward: 0.12 ETH net so far."]
    assert "Error evaluating condition" not in caplog.text
    await _turn_off(hass)


async def test_every_example_loads_as_an_automation(hass):
    """An automation Home Assistant cannot validate is set up unavailable."""
    examples = _examples()
    assert await async_setup_component(hass, "automation", {"automation": examples})
    await hass.async_block_till_done()
    states = hass.states.async_all("automation")
    assert len(states) == len(examples) == 4
    assert [state.state for state in states] == ["on"] * 4
    # Off again, so no trigger -- the schedule's timer -- outlives the test.
    await _turn_off(hass)


# --- The badges under the title --------------------------------------------------


def test_the_home_assistant_badge_names_the_minimum_version_of_hacs_json():
    """The badge says which Home Assistant the integration needs; hacs.json
    states it for HACS. A new minimum turns this red until the badge
    follows."""
    minimum = json.loads((_ROOT / "hacs.json").read_text(encoding="utf-8"))["homeassistant"]
    major, minor, *_ = minimum.split(".")
    assert f"https://img.shields.io/badge/Home%20Assistant-{major}.{minor}%2B-" in _README
