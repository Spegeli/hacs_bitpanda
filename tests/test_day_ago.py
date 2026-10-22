"""The 24-hour references (day_ago.DayAgoPrices): one lookup for every joined
sensor, its last result kept per key -- a wallet's asset -- for the actions
that answer without a sensor (services.py)."""
from custom_components.bitpanda.day_ago import DayAgoPrices


class _Sensor:
    def __init__(self, entity_id: str) -> None:
        self.entity_id = entity_id
        self.price_24h_ago: float | None = None

    def set_price_24h_ago(self, value: float | None) -> None:
        self.price_24h_ago = value


async def _found(hass, entity_ids, now):
    return {entity_id: 1.5 for entity_id in entity_ids if entity_id.endswith("_a")}


async def test_the_day_ago_lookup_keeps_its_last_result_per_key(hass):
    """By the key a sensor joined with -- its asset, whatever its entity ID
    -- or by its entity ID; a sensor that leaves takes its result along."""
    prices = DayAgoPrices(hass, _found)
    renamed, other, plain = _Sensor("sensor.renamed_a"), _Sensor("sensor.other_b"), _Sensor("sensor.plain_a")
    leave_renamed = prices.join(renamed, "asset-a")
    leave_other = prices.join(other, "asset-b")
    leave_plain = prices.join(plain)
    assert prices.last == {}
    await prices.async_look_up()
    assert (renamed.price_24h_ago, other.price_24h_ago) == (1.5, None)
    assert prices.last == {"asset-a": 1.5, "asset-b": None, "sensor.plain_a": 1.5}
    leave_renamed()
    assert prices.last == {"asset-b": None, "sensor.plain_a": 1.5}
    leave_other()
    leave_plain()
    assert prices.last == {}
