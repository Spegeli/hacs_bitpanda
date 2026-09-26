"""The README's automation examples: copyable as they stand.

Each YAML block of the "Automation examples" section is what a user pastes
into a new automation's YAML editor, so each must load as a valid
automation, and use the entity IDs the integration creates.
"""
from pathlib import Path
import re

from homeassistant.setup import async_setup_component
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
    assert trigger["entity_id"] == price_entity_id(btc, "EUR") == "sensor.bitpanda_bitcoin_btc_eur"


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
