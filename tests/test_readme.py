"""The README: its automation examples copyable as they stand, and its
Home Assistant badge in step with hacs.json.

Each YAML block of the "Automation examples" section is what a user pastes
into a new automation's YAML editor, so each must load as a valid
automation, and use the entity IDs the integration creates and the event
it fires.
"""
from datetime import timedelta
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote

from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service
import yaml

from custom_components.bitpanda.const import (
    EVENT_STAKING_REWARD_RECEIVED,
    EVENT_WALLET_ADDED,
)
from custom_components.bitpanda.naming import (
    portfolio_entity_id,
    price_entity_id,
    return_key,
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


def test_the_examples_are_an_alert_a_big_move_a_report_a_reward_and_a_new_wallet():
    alert, move, report, reward, wallet = _examples()
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
    [received] = reward["triggers"]
    assert (received["trigger"], received["event_type"]) == (
        "event", EVENT_STAKING_REWARD_RECEIVED,
    )
    [pushed] = reward["actions"]
    assert pushed["action"] == "notify.mobile_app_your_phone"
    [added] = wallet["triggers"]
    assert (added["trigger"], added["event_type"]) == ("event", EVENT_WALLET_ADDED)
    [pushed] = wallet["actions"]
    assert pushed["action"] == "notify.mobile_app_your_phone"


def test_the_examples_watch_the_sensors_the_integration_creates():
    btc = next(asset for asset in load_fixture("assets-sample.json") if asset["symbol"] == "BTC")
    assert price_entity_id(btc, "EUR") == _PRICE
    assert portfolio_entity_id("total") == _TOTAL
    assert portfolio_entity_id(return_key("DAY")) == _DAY
    alert, move, report, _reward, _wallet = _examples()
    assert [each["entity_id"] for each in (*alert["triggers"], *move["triggers"])] == [_PRICE] * 3
    message = report["actions"][1]["data"]["message"]
    assert f"states('{_TOTAL}', with_unit=True)" in message
    assert f"states('{_DAY}', with_unit=True)" in message


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


async def test_the_staking_reward_example_sends_the_net_amount_and_the_count(hass):
    """One push message per announcement, with what it adds up: one payout,
    or several after a pause."""
    assert await async_setup_component(hass, "automation", {"automation": [_examples()[3]]})
    await hass.async_block_till_done()
    pushed = async_mock_service(hass, "notify", "mobile_app_your_phone")
    for count, net in ((1, 9.87654312), (3, 29.62962936)):
        hass.bus.async_fire(
            EVENT_STAKING_REWARD_RECEIVED,
            {
                "device_id": "wallet-device",
                "asset_id": "vision-asset",
                "symbol": "VSN",
                "name": "Vision",
                "wallet": "Vision (VSN) Wallet",
                "count": count,
                "gross": net * 1.25,
                "fee": net * 0.25,
                "net": net,
                "value": 0.07,
                "currency": "EUR",
                "credited_at": "2026-09-22T16:20:00Z",
            },
        )
        await hass.async_block_till_done()
    assert [(call.data["title"], call.data["message"]) for call in pushed] == [
        ("Staking reward", "Vision (VSN) Wallet received 9.87654312 VSN from 1 payout."),
        ("Staking reward", "Vision (VSN) Wallet received 29.62962936 VSN from 3 payouts."),
    ]


async def test_the_new_wallet_example_sends_the_wallets_name(hass):
    """One push message per announced wallet, named as the event names it."""
    assert await async_setup_component(hass, "automation", {"automation": [_examples()[4]]})
    await hass.async_block_till_done()
    pushed = async_mock_service(hass, "notify", "mobile_app_your_phone")
    hass.bus.async_fire(
        EVENT_WALLET_ADDED,
        {
            "device_id": "wallet-device",
            "asset_id": "vision-asset",
            "symbol": "VSN",
            "name": "Vision",
            "wallet": "Vision (VSN) Wallet",
            "category": "crypto",
        },
    )
    await hass.async_block_till_done()
    assert [(call.data["title"], call.data["message"]) for call in pushed] == [
        ("New Bitpanda wallet", "Vision (VSN) Wallet was added to your Portfolio.")
    ]


async def test_every_example_loads_as_an_automation(hass):
    """An automation Home Assistant cannot validate is set up unavailable."""
    examples = _examples()
    assert await async_setup_component(hass, "automation", {"automation": examples})
    await hass.async_block_till_done()
    states = hass.states.async_all("automation")
    assert len(states) == len(examples) == 5
    assert [state.state for state in states] == ["on"] * 5
    # Off again, so no trigger -- the schedule's timer -- outlives the test.
    await _turn_off(hass)


# --- Links within the README ----------------------------------------------------


def _github_anchor(heading: str) -> str:
    """The anchor GitHub gives `heading`, as a link writes it: lower case;
    letters, digits, marks, "_", "-" and spaces kept, a space becoming a
    dash; everything else -- punctuation, an emoji -- dropped. The emoji's
    invisible variation selector is a mark, so "⬆️ Upgrading" keeps it, and
    a link writes it percent-encoded: "%EF%B8%8F-upgrading"."""
    kept = "".join(
        char for char in heading.strip().lower()
        if char in " -_" or unicodedata.category(char)[0] in "LMN"
    )
    return quote(kept.replace(" ", "-"), safe="-_")


def test_every_link_within_the_readme_finds_its_section():
    """A renamed heading breaks every link to it without a warning on
    GitHub: the new-wallet and the staking reward sections, for one, link
    the automation examples by their headings."""
    text = re.sub(r"```.*?```", "", _README, flags=re.DOTALL)
    sections = {
        _github_anchor(heading) for heading in re.findall(r"^#{1,6} (.+)$", text, re.MULTILINE)
    }
    links = set(re.findall(r"\]\(#([^)\s]+)\)", text))
    assert {"staking-rewards", "4-staking-reward-a-push-message-for-each-payout"} <= links
    assert sorted(links - sections) == []


# --- The badges under the title --------------------------------------------------


def test_the_home_assistant_badge_names_the_minimum_version_of_hacs_json():
    """The badge says which Home Assistant the integration needs; hacs.json
    states it for HACS. A new minimum turns this red until the badge
    follows."""
    minimum = json.loads((_ROOT / "hacs.json").read_text(encoding="utf-8"))["homeassistant"]
    major, minor, *_ = minimum.split(".")
    assert f"https://img.shields.io/badge/Home%20Assistant-{major}.{minor}%2B-" in _README


def test_the_license_badge_names_the_license_of_the_license_file_and_opens_it():
    """The badge says which license the LICENSE file grants, and links to
    that file."""
    granted = (_ROOT / "LICENSE").read_text(encoding="utf-8").split(" License", 1)[0]
    assert granted == "MIT"
    assert (
        f'<a href="LICENSE"><img src="https://img.shields.io/badge/license-{granted}-yellow" '
        f'alt="License: {granted}"></a>'
    ) in _README


def test_the_release_badge_opens_the_release_it_shows():
    """The badge shows the newest stable release -- pre-releases left out,
    as include_prereleases is not set -- and GitHub's /releases/latest
    forwards to that same release, whichever it is."""
    [(link, badge)] = re.findall(
        r'<a href="([^"]*)"><img src="(https://img\.shields\.io/github/v/release/[^"]*)"', _README
    )
    assert link == "https://github.com/Spegeli/hacs_bitpanda/releases/latest"
    assert "include_prereleases" not in badge
