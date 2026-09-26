"""Groups: config subentries that sort an entry's devices by asset type.

Home Assistant shows every config subentry of an entry as a group on the
integration page, with the subentry's devices inside. A group stands for one
asset category (assets.asset_category) and carries it as its unique_id. Its
title is set once, in Home Assistant's language, when the group is created.
At every later setup, a group still titled one of this integration's own
default titles for its category -- in any language it ships -- but not the
one for the current language, is retitled to the current language
(async_retitle_groups_to_current_language). A title the user chose is never
touched; newer Home Assistant versions also let the user rename a group.

The Price Tracker keeps its tracked assets in its groups (type price_group):
each group's data holds the slim records of its assets by asset id.

The Portfolio's wallet manager keeps its wallet devices in groups of type
wallet_group, which hold nothing but their category: the manager creates
them as wallets arrive and removes them once they hold nothing.
"""
from __future__ import annotations

from collections.abc import Iterable
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry, ConfigSubentryData
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations

from .assets import ASSET_CATEGORY_FILTERS, CATEGORY_OTHER, asset_category, slim_asset
from .const import (
    CONF_ASSETS,
    CONF_CATEGORY,
    DOMAIN,
    SUBENTRY_TYPE_PRICE_GROUP,
    SUBENTRY_TYPE_WALLET_GROUP,
)
from .language import async_shipped_languages

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


async def async_known_group_titles(hass: HomeAssistant) -> dict[str, set[str]]:
    """Category -> every group title this integration has ever shipped as its
    default, in any language it ships (language.async_shipped_languages).
    Tells a shipped default title apart from one the user chose.
    """
    languages = await async_shipped_languages(hass)
    known: dict[str, set[str]] = {
        category: set() for category in (*ASSET_CATEGORY_FILTERS, CATEGORY_OTHER)
    }
    for language in languages:
        translations = await async_get_translations(hass, language, "selector", {DOMAIN})
        for category in known:
            title = translations.get(f"{_TITLE_KEY}{category}")
            if title is not None:
                known[category].add(title)
    return known


async def async_retitle_groups_to_current_language(
    hass: HomeAssistant, entry: ConfigEntry, subentry_type: str, current: dict[str, str]
) -> None:
    """Retitle every `subentry_type` group of `entry` that is still titled one
    of this integration's own default group titles for its category -- in any
    language it ships -- to its title in `current`, the titles for Home
    Assistant's current language (async_group_titles), which the caller
    reads once and reuses. A title the user chose, one that is not a shipped
    default for the group's category, is never touched.

    Call this once at every setup of the Price Tracker and the Portfolio,
    before the entry's update listener is registered: the Price Tracker
    reloads on any change to the entry, subentries included, so retitling
    after that listener exists would reload the entry it just finished
    setting up.

    Accepted edge case: a user who renamed a group to exactly a shipped
    default title of the same category, in another language, ends up
    retitled too -- from the group's own data there is no way to tell that
    apart from a default title that simply predates a later language change.
    """
    known = await async_known_group_titles(hass)
    for group in groups_of_type(entry, subentry_type):
        target = current.get(group.unique_id)
        if target is None or group.title == target:
            continue
        if group.title in known.get(group.unique_id, set()):
            hass.config_entries.async_update_subentry(entry, group, title=target)


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


def entities_by_group(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, list[er.RegistryEntry]]:
    """Subentry id -> the entity registry entries of `entry` in that group,
    disabled ones included; entries in no group are left out.

    What a group holds is read from the entity registry: every supported
    Home Assistant version records an entity's subentry there, while the
    device registry changed how it records a device's -- from 2026.9 the
    older form is only a deprecated compatibility property.
    """
    out: dict[str, list[er.RegistryEntry]] = {}
    for reg_entry in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        if reg_entry.config_subentry_id is not None:
            out.setdefault(reg_entry.config_subentry_id, []).append(reg_entry)
    return out


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


@callback
def async_remove_asset_from_group(hass: HomeAssistant, entry: ConfigEntry, asset_id: str) -> None:
    """Stop tracking `asset_id`: it leaves its group, and a group left without
    assets goes altogether. Exactly one change either way, so the update
    listener reloads the entry once; nothing changes for an untracked asset."""
    group = price_group_of_asset(entry, asset_id)
    if group is None:
        return
    assets = {key: record for key, record in group.data[CONF_ASSETS].items() if key != asset_id}
    if assets:
        hass.config_entries.async_update_subentry(
            entry, group, data={**group.data, CONF_ASSETS: assets}
        )
    else:
        hass.config_entries.async_remove_subentry(entry, group.subentry_id)


@callback
def async_get_or_create_wallet_group(
    hass: HomeAssistant, entry: ConfigEntry, category: str, titles: dict[str, str]
) -> ConfigSubentry:
    """The Portfolio's wallet group of `category`; created, titled from
    `titles` (see async_group_titles), when there is none yet."""
    group = group_of_category(entry, SUBENTRY_TYPE_WALLET_GROUP, category)
    if group is None:
        group = ConfigSubentry(
            data=MappingProxyType({CONF_CATEGORY: category}),
            subentry_type=SUBENTRY_TYPE_WALLET_GROUP,
            title=titles[category],
            unique_id=category,
        )
        hass.config_entries.async_add_subentry(entry, group)
    return group
