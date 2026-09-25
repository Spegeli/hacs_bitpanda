"""Groups: config subentries that sort an entry's devices by asset type."""
from unittest.mock import AsyncMock, patch

from custom_components.bitpanda.groups import async_group_titles

_TRANSLATIONS = "custom_components.bitpanda.groups.async_get_translations"


async def test_group_titles_are_in_the_language_home_assistant_runs_in(hass):
    assert await async_group_titles(hass) == {
        "crypto": "Cryptocurrencies",
        "stock": "Stocks",
        "etf": "ETFs",
        "etc": "ETCs",
        "index": "Crypto indices",
        "metal": "Precious metals",
        "other": "Other",
    }
    hass.config.language = "de"
    assert await async_group_titles(hass) == {
        "crypto": "Kryptowährungen",
        "stock": "Aktien",
        "etf": "ETFs",
        "etc": "ETCs",
        "index": "Krypto-Indizes",
        "metal": "Edelmetalle",
        "other": "Sonstige",
    }


async def test_a_category_without_a_translation_is_titled_with_its_key(hass):
    translations = AsyncMock(
        return_value={"component.bitpanda.selector.asset_group.options.crypto": "Krypto"}
    )
    with patch(_TRANSLATIONS, translations):
        titles = await async_group_titles(hass)
    translations.assert_awaited_once_with(hass, "en", "selector", {"bitpanda"})
    assert titles["crypto"] == "Krypto"
    assert titles["metal"] == "metal"
    assert titles["other"] == "other"
