"""Groups: config subentries that sort an entry's devices by asset type.

Home Assistant shows every config subentry of an entry as a group on the
integration page, with the subentry's devices inside. A group stands for one
asset category (assets.asset_category) and carries it as its unique_id. Its
title is set once, in Home Assistant's language, when the group is created;
the user may rename it afterwards.

The Price Tracker keeps its tracked assets in its groups (type price_group):
each group's data holds the slim records of its assets by asset id.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry, ConfigSubentryData
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.translation import async_get_translations

from .assets import ASSET_CATEGORY_FILTERS, CATEGORY_OTHER, asset_category, slim_asset
from .const import CONF_ASSETS, CONF_CATEGORY, DOMAIN, SUBENTRY_TYPE_PRICE_GROUP

_TITLE_KEY = f"component.{DOMAIN}.selector.asset_group.options."


async def async_group_titles(hass: HomeAssistant) -> dict[str, str]:
    """Category -> group title, in the language Home Assistant runs in.

    Read from the `selector.asset_group` translations, English where the
    language has none; a category without any is titled with its own key.
    """
    translations = await async_get_translations(
        hass, hass.config.language, "selector", {DOMAIN}
    )
    return {
        category: translations.get(f"{_TITLE_KEY}{category}", category)
        for category in (*ASSET_CATEGORY_FILTERS, CATEGORY_OTHER)
    }


def groups_of_type(entry: ConfigEntry, subentry_type: str) -> list[ConfigSubentry]:
    """The groups of `entry` that are config subentries of `subentry_type`."""
    return [sub for sub in entry.subentries.values() if sub.subentry_type == subentry_type]


def group_of_category(
    entry: ConfigEntry, subentry_type: str, category: str
) -> ConfigSubentry | None:
    """The group of `category` among the `subentry_type` groups, or None."""
    return next(
        (group for group in groups_of_type(entry, subentry_type) if group.unique_id == category),
        None,
    )


def price_group_data(category: str, records: Iterable[dict]) -> dict[str, Any]:
    """What a Price Tracker group stores: its category and its assets'
    records by asset id."""
    return {CONF_CATEGORY: category, CONF_ASSETS: {record["id"]: record for record in records}}


def price_group_subentries(
    assets: Iterable[dict], titles: dict[str, str]
) -> list[ConfigSubentryData]:
    """New Price Tracker groups tracking `assets`: one per asset category,
    titled from `titles` (see async_group_titles)."""
    by_category: dict[str, list[dict]] = {}
    for asset in assets:
        record = slim_asset(asset)
        by_category.setdefault(asset_category(record), []).append(record)
    return [
        ConfigSubentryData(
            data=price_group_data(category, records),
            subentry_type=SUBENTRY_TYPE_PRICE_GROUP,
            title=titles[category],
            unique_id=category,
        )
        for category, records in by_category.items()
    ]


def tracked_assets(entry: ConfigEntry) -> dict[str, dict]:
    """Asset id -> record of every asset the Price Tracker tracks, in any group."""
    return {
        asset_id: record
        for group in groups_of_type(entry, SUBENTRY_TYPE_PRICE_GROUP)
        for asset_id, record in group.data[CONF_ASSETS].items()
    }


def price_group_of_asset(entry: ConfigEntry, asset_id: str) -> ConfigSubentry | None:
    """The Price Tracker group that tracks `asset_id`, or None."""
    return next(
        (
            group
            for group in groups_of_type(entry, SUBENTRY_TYPE_PRICE_GROUP)
            if asset_id in group.data[CONF_ASSETS]
        ),
        None,
    )


@callback
def async_add_asset_to_group(
    hass: HomeAssistant, entry: ConfigEntry, group: ConfigSubentry, record: dict
) -> None:
    """Track `record` in the Price Tracker group `group`; its title stays.

    Written as new data, never changed in place: Home Assistant saves the
    change, and tells the update listener, only when the data differs.
    """
    hass.config_entries.async_update_subentry(
        entry,
        group,
        data={**group.data, CONF_ASSETS: {**group.data[CONF_ASSETS], record["id"]: record}},
    )
