"""The language of the integration's own texts.

Home Assistant picks the language of most of this integration's texts
itself: dialogs, attribute names and repair issues follow each user's
profile language, sensor names its system language. Three kinds of text
the integration writes out itself, and Home Assistant shows as they are: the
titles of its groups, its refusals to delete a device, and the Portfolio's
notification about a new wallet. Those follow one setting per entry instead
-- CONF_LANGUAGE, chosen among the languages this integration ships when a
service is set up (Home Assistant's system language offered first) and
changed under Configure -- so in a household of several users nobody meets
them in a language nobody chose. An entry that never had the choice, one
upgraded from version 1, uses English.
"""
from __future__ import annotations

from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_LANGUAGE, DEFAULT_LANGUAGE

# The file names under here are this integration's own shipped languages and
# do not change at runtime, but the path being fixed does not make the read
# itself a one-time cost: async_shipped_languages() globs this directory in
# the executor at every call -- every setup of either service, every opened
# Configure dialog -- not once per process.
_TRANSLATIONS_DIR = Path(__file__).parent / "translations"


def entry_language(entry: ConfigEntry) -> str:
    """The language of `entry`'s own texts: its CONF_LANGUAGE option,
    English for an entry that has none."""
    language: str = entry.options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    return language


def preselected_language(hass: HomeAssistant, languages: list[str]) -> str:
    """The language a setup dialog offers first, one of `languages`: Home
    Assistant's system language -- a regional variant such as "en-GB" by
    its base language -- or English where this integration does not ship
    it."""
    system = hass.config.language
    for candidate in (system, system.split("-")[0]):
        if candidate in languages:
            return candidate
    return DEFAULT_LANGUAGE


def _shipped_languages() -> list[str]:
    """Blocking I/O -- see async_shipped_languages."""
    return sorted(path.stem for path in _TRANSLATIONS_DIR.glob("*.json"))


async def async_shipped_languages(hass: HomeAssistant) -> list[str]:
    """Language codes this integration ships a translations file for, from
    the file names in translations/ (English is en.json).

    Discovered from disk, in the executor, rather than hard-coded: a
    language added under translations/ is offered, and its group titles
    recognised, without a code change.
    """
    return await hass.async_add_executor_job(_shipped_languages)
