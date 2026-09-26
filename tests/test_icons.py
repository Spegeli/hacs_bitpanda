"""Icons come from icons.json, by translation key -- never from code.

Home Assistant's frontend picks an entity's icon from the integration's
icon translations by the entity's translation key (and an action's icon by
its name), so no icon is part of any state. The icons themselves are the
ones the sensors always had; Staking's and the wallet Total's were chosen by
the maintainer.
"""
import json
from pathlib import Path

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.icon import async_get_icons

from custom_components.bitpanda import portfolio_sensor, price_sensor
from custom_components.bitpanda.const import DOMAIN

_DIR = Path(__file__).parent.parent / "custom_components" / "bitpanda"

_SENSOR_ICONS = {
    "total_value": "mdi:chart-pie",
    "cash": "mdi:cash",
    "cash_plus": "mdi:piggy-bank",
    "return_day": "mdi:chart-line",
    "return_week": "mdi:chart-line",
    "return_month": "mdi:chart-line",
    "return_six_month": "mdi:chart-line",
    "return_year": "mdi:chart-line",
    "wallet": "mdi:wallet",
    "staking": "mdi:lock-clock",
    "wallet_total": "mdi:sigma",
    "price": "mdi:chart-line",
}


def _icons() -> dict:
    return json.loads((_DIR / "icons.json").read_text(encoding="utf-8"))


def test_icons_json_has_no_bom():
    assert not (_DIR / "icons.json").read_bytes().startswith(b"\xef\xbb\xbf")


def test_every_sensor_keeps_its_icon():
    assert {
        key: icons["default"] for key, icons in _icons()["entity"]["sensor"].items()
    } == _SENSOR_ICONS


def test_every_sensor_translation_key_has_an_icon():
    """A sensor's icon is found by its translation key: every key a sensor
    can carry (entity.sensor in strings.json) has one."""
    strings = json.loads((_DIR / "strings.json").read_text(encoding="utf-8"))
    assert set(_icons()["entity"]["sensor"]) == set(strings["entity"]["sensor"])


def test_the_refresh_action_has_an_icon():
    assert _icons()["services"] == {"refresh": {"service": "mdi:refresh"}}


def _sensor_classes() -> list[type]:
    return [
        value
        for module in (portfolio_sensor, price_sensor)
        for value in vars(module).values()
        if isinstance(value, type)
        and value.__module__ == module.__name__
        and issubclass(value, SensorEntity)
    ]


def test_no_sensor_sets_an_icon_in_code():
    """An icon set in code would override the icon translation and show up
    as an `icon` attribute of the state."""
    classes = _sensor_classes()
    assert len(classes) >= 8
    for cls in classes:
        for klass in cls.__mro__:
            if klass.__module__.startswith("custom_components."):
                assert "_attr_icon" not in vars(klass), cls.__name__


async def test_home_assistant_reads_the_icons(hass):
    """Through Home Assistant's own loader, as the frontend receives them."""
    entity = await async_get_icons(hass, "entity", {DOMAIN})
    assert {
        key: icons["default"] for key, icons in entity[DOMAIN]["sensor"].items()
    } == _SENSOR_ICONS
    services = await async_get_icons(hass, "services", {DOMAIN})
    assert services[DOMAIN] == {"refresh": {"service": "mdi:refresh"}}
