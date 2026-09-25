"""The "Add price tracker" config subentry flow of the Price Tracker.

Category first, then one searchable pick from that category's catalogue --
public data, fetched without a key and cached for 24 hours.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util import dt as dt_util

from .api import BitpandaApiClient, BitpandaApiError, BitpandaRateLimitError
from .assets import asset_label, slim_asset
from .const import CONF_ASSET, DOMAIN
from .naming import asset_display_label

# Every filter was verified live on 2026-09-24. Together they cover 14,051 of
# 14,054 catalogue assets -- the three left out are security/fiat_earn (Cash
# Plus), a cash equivalent. Stocks exist in two families, equity_security/
# equity_stock and security/stock, often the same company twice; both are
# genuine, priced listings, so a category can merge several filters.
ASSET_CATEGORY_FILTERS: dict[str, list[tuple[str, str | None]]] = {
    "crypto": [("cryptocoin", None)],
    "stock": [("equity_security", "equity_stock"), ("security", "stock")],
    "etf": [
        ("equity_security", "equity_etf"),
        ("equity_security", "equity_complex_etf"),
        ("security", "etf"),
    ],
    "etc": [("equity_security", "equity_complex_etc"), ("security", "etc")],
    "index": [("index", None)],
    "metal": [("commodity", "metal")],
}

# The stock listing alone is ~103 requests; a day-old catalogue is current
# enough for picking an asset.
_CATALOGUE_CACHE_TTL = timedelta(hours=24)

# Its own top-level hass.data key, never inside hass.data[DOMAIN]: it serves
# every flow and survives entry reloads.
_CATALOGUE_KEY = f"{DOMAIN}_asset_catalogue"


async def async_category_listing(
    hass: HomeAssistant, client: BitpandaApiClient, category: str
) -> list[dict]:
    """Every asset of one category, all pages, slimmed, cached for 24 hours.

    Nothing here catches an API error: an error partway through a
    multi-filter category must not cache a partial listing. Every listing
    past its TTL is dropped on each call, so the cache holds at most a day's
    worth of what was actually browsed.
    """
    store: dict[str, tuple] = hass.data.setdefault(_CATALOGUE_KEY, {})
    now = dt_util.utcnow()
    for expired in [
        key for key, (fetched_at, _) in store.items() if now - fetched_at >= _CATALOGUE_CACHE_TTL
    ]:
        del store[expired]

    cached = store.get(category)
    if cached is not None:
        return cached[1]

    assets: list[dict] = []
    seen: set[str] = set()
    for type_, group in ASSET_CATEGORY_FILTERS[category]:
        for asset in await client.async_list_assets(type_, group):
            asset_id = asset.get("id")
            if asset_id and asset_id not in seen:
                seen.add(asset_id)
                assets.append(slim_asset(asset))
    store[category] = (now, assets)
    return assets


class AssetSubentryFlow(ConfigSubentryFlow):
    """Track one more asset: one subentry, one device, one sensor per currency."""

    def __init__(self) -> None:
        self._category: str | None = None

    def _tracked_ids(self) -> set[str]:
        # ConfigSubentryFlow._get_entry() does not exist at the 2025.3 floor.
        entry = self.hass.config_entries.async_get_entry(self.handler[0])
        if entry is None:
            return set()
        return {sub.unique_id for sub in entry.subentries.values() if sub.unique_id}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Which kind of asset. The options are labelled via
        `selector.asset_category.options.<value>`."""
        if user_input is not None:
            self._category = user_input["category"]
            return await self.async_step_asset()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("category"): SelectSelector(
                        SelectSelectorConfig(
                            options=list(ASSET_CATEGORY_FILTERS),
                            translation_key="asset_category",
                        )
                    )
                }
            ),
        )

    def _show_assets(self, options: list[dict], error: str | None) -> SubentryFlowResult:
        """One pick from `options`.

        `custom_value=True` is what makes the frontend render a single select
        as a searchable combo box (without it: a plain, unsearchable list).
        The field is optional: submitting it empty goes back to the categories,
        the way out of every error and of an empty listing.
        """
        return self.async_show_form(
            step_id="asset",
            data_schema=vol.Schema(
                {
                    vol.Optional("asset"): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                            custom_value=True,
                        )
                    )
                }
            ),
            errors={"base": error} if error else None,
        )

    async def _async_listing(self) -> tuple[list[dict], str | None]:
        client = BitpandaApiClient(None, async_get_clientsession(self.hass))
        try:
            return await async_category_listing(self.hass, client, self._category), None
        except BitpandaRateLimitError:
            return [], "rate_limited"
        except BitpandaApiError:
            return [], "cannot_connect"

    async def async_step_asset(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None and not user_input.get("asset"):
            self._category = None
            return await self.async_step_user()

        tracked = self._tracked_ids()
        catalogue, error = await self._async_listing()
        if error is not None:
            return self._show_assets([], error)
        options = sorted(
            (
                {"value": asset["id"], "label": asset_label(asset)}
                for asset in catalogue
                if asset["id"] not in tracked
            ),
            key=lambda option: option["label"].casefold(),
        )

        if user_input is not None:
            chosen = next((a for a in catalogue if a["id"] == user_input["asset"]), None)
            if chosen is None:
                return self._show_assets(options, "unknown_asset")
            if chosen["id"] in tracked:
                return self.async_abort(reason="already_configured")
            return self.async_create_entry(
                title=asset_display_label(chosen),
                data={CONF_ASSET: slim_asset(chosen)},
                unique_id=chosen["id"],
            )

        if not options:
            return self._show_assets([], "no_assets_available")
        return self._show_assets(options, None)
