"""The README's automation examples: copyable as they stand.

Each YAML block of the "Automation examples" section is what a user pastes
into a new automation's YAML editor, so each must load as a valid
automation, and use the entity IDs the integration creates.
"""
from pathlib import Path
import re

from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service
import yaml

from custom_components.bitpanda.naming import price_entity_id

from tests.conftest import load_fixture

_README = (Path(__file__).parent.parent / "README.md").read_text(encoding="utf-8")
_SECTION = "\n## \U0001f916 Automation examples\n"


def _examples() -> list[dict]:
    """The section's YAML blocks, in order."""
    start = _README.index(_SECTION)
    end = _README.index("\n## ", start + len(_SECTION))
    return [
        yaml.safe_load(block)
        for block in re.findall(r"```yaml\n(.*?)```", _README[start:end], re.DOTALL)
    ]


def test_there_is_a_price_alert_and_a_refresh_that_goes_on_after_a_failure():
    alert, refresh = _examples()
    [trigger] = alert["triggers"]
    assert (trigger["trigger"], set(trigger) & {"above", "below"}) == ("numeric_state", {"above"})
    [step] = refresh["actions"]
    assert step == {"action": "bitpanda.refresh", "continue_on_error": True}


def test_the_price_alert_watches_the_price_sensor_the_integration_creates():
    btc = next(asset for asset in load_fixture("assets-sample.json") if asset["symbol"] == "BTC")
    alert, _ = _examples()
    [trigger] = alert["triggers"]
    assert trigger["entity_id"] == price_entity_id(btc, "EUR") == "sensor.bitpanda_bitcoin_btc_price_tracker_eur"


_PRICE = "sensor.bitpanda_bitcoin_btc_price_tracker_eur"


async def _set_up_the_alert(hass) -> list:
    """The price alert as an automation; the notifications it sends."""
    alert, _ = _examples()
    assert await async_setup_component(hass, "automation", {"automation": [alert]})
    await hass.async_block_till_done()
    return async_mock_service(hass, "persistent_notification", "create")


async def _price(hass, state: str) -> None:
    hass.states.async_set(_PRICE, state)
    await hass.async_block_till_done()


async def _turn_off(hass) -> None:
    await hass.services.async_call("automation", "turn_off", {"entity_id": "all"}, blocking=True)


async def test_the_price_alert_fires_when_the_price_crosses_the_threshold(hass):
    """Once per crossing -- not again while the price stays above, and not
    when it merely comes back above after an outage."""
    hass.states.async_set(_PRICE, "90000")
    notifications = await _set_up_the_alert(hass)

    await _price(hass, "100500")
    await _price(hass, "101000")
    assert len(notifications) == 1
    assert notifications[0].data["message"] == "Bitcoin is at 100500 EUR."

    for outage in ("unavailable", "unknown"):
        await _price(hass, outage)
        await _price(hass, "101500")
    assert len(notifications) == 1

    await _price(hass, "95000")
    await _price(hass, "100100")
    assert len(notifications) == 2
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
    notifications = await _set_up_the_alert(hass)
    await _price(hass, "102000")
    assert notifications == []
    await _turn_off(hass)


async def test_every_example_loads_as_an_automation(hass):
    """An automation Home Assistant cannot validate is set up unavailable."""
    examples = _examples()
    assert await async_setup_component(hass, "automation", {"automation": examples})
    await hass.async_block_till_done()
    states = hass.states.async_all("automation")
    assert len(states) == len(examples) == 2
    assert [state.state for state in states] == ["on", "on"]
    # Off again, so no trigger -- the schedule's timer -- outlives the test.
    await hass.services.async_call(
        "automation", "turn_off", {"entity_id": "all"}, blocking=True
    )
