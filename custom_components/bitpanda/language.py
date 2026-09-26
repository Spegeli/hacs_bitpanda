"""The language of the integration's own texts.

Home Assistant picks the language of most of this integration's texts
itself: dialogs, attribute names and repair issues follow each user's
profile language, sensor names its system language. Two kinds of text the
integration writes out itself, and Home Assistant shows as they are: the
titles of its groups, and its refusals to delete a device. Those follow one
setting per entry instead -- CONF_LANGUAGE under Configure, English by
default, chosen among the languages this integration ships -- so in a
household of several users nobody meets them in a language nobody chose.
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
    English until the user picks another."""
    language: str = entry.options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    return language


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
