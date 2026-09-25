"""Groups: config subentries that sort an entry's devices by asset type.

Home Assistant shows every config subentry of an entry as a group on the
integration page, with the subentry's devices inside. A group stands for one
asset category (assets.asset_category) and carries it as its unique_id. Its
title is set once, in Home Assistant's language, when the group is created;
the user may rename it afterwards.
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations

from .assets import ASSET_CATEGORY_FILTERS, CATEGORY_OTHER
from .const import DOMAIN

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
