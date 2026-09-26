"""The "Add price tracker" config subentry flow of the Price Tracker.

Category first, then one searchable pick from that category's catalogue --
public data, fetched without a key and cached for 24 hours. The asset joins
the group of its asset type, which the flow creates when there is none yet.
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
from .assets import (
    ASSET_CATEGORY_FILTERS,
    asset_category,
    asset_label_map,
    resolve_asset,
    slim_asset,
)
from .const import DOMAIN, SUBENTRY_TYPE_PRICE_GROUP
from .groups import (
    async_add_asset_to_group,
    async_group_titles,
    group_of_category,
    price_group_data,
    tracked_assets,
)
from .naming import asset_display_label

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


class PriceTrackerSubentryFlow(ConfigSubentryFlow):
    """Track one more asset: it joins the group of its asset type (a
    price_group subentry), or starts that group. One device per asset, one
    sensor per asset and currency."""

    def __init__(self) -> None:
        self._category: str | None = None

    def _tracked_ids(self) -> set[str]:
        """Assets tracked in any group.

        Not ConfigSubentryFlow._get_entry(): that raises UnknownEntry when the
        entry was removed while this dialog was open. Looked up here, a
        removed entry simply tracks nothing.
        """
        entry = self.hass.config_entries.async_get_entry(self.handler[0])
        return set() if entry is None else set(tracked_assets(entry))

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Which kind of asset. The options are labelled via
        `selector.asset_category.options.<value>`. Coming back from the asset
        step, the category picked before is pre-selected."""
        if user_input is not None:
            self._category = user_input["category"]
            return await self.async_step_asset()
        category = (
            vol.Required("category")
            if self._category is None
            else vol.Required("category", default=self._category)
        )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    category: SelectSelector(
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
            return await self.async_step_user()

        catalogue, error = await self._async_listing()
        if error is not None:
            return self._show_assets([], error)
        tracked = self._tracked_ids()
        # Built once per listing and used for both the options below and for
        # resolving what gets submitted, so a picked option's value is always
        # the label the user saw and searched, never a bare id (the picker's
        # ha-picker-field has no way to render a label for a raw value it
        # wasn't given).
        label_map = asset_label_map(catalogue)
        options = sorted(
            (
                {"value": label, "label": label}
                for label, asset in label_map.items()
                if asset["id"] not in tracked
            ),
            key=lambda option: option["label"].casefold(),
        )

        if user_input is not None:
            chosen = resolve_asset(user_input["asset"], label_map, catalogue)
            if chosen is None:
                return self._show_assets(options, "unknown_asset")
            if chosen["id"] in tracked:
                return self.async_abort(reason="already_configured")
            return await self._async_track(slim_asset(chosen))

        if not options:
            return self._show_assets([], "no_assets_available")
        return self._show_assets(options, None)

    async def _async_track(self, record: dict) -> SubentryFlowResult:
        """Add `record` to the group of its asset type, or start that group.

        Joining ends the dialog with a message naming the group: no subentry
        is created, so Home Assistant's own confirmation would not fit.
        """
        category = asset_category(record)
        titles = await async_group_titles(self.hass)
        # Looked up after the last await, so no other dialog can start the
        # same group before this step ends. Raises UnknownEntry if the Price
        # Tracker was removed while the dialog was open, as Home Assistant
        # itself does when a group is created then.
        entry = self._get_entry()
        group = group_of_category(entry, SUBENTRY_TYPE_PRICE_GROUP, category)
        if group is None:
            return self.async_create_entry(
                title=titles[category],
                data=price_group_data(category, [record]),
                unique_id=category,
            )
        async_add_asset_to_group(self.hass, entry, group, record)
        return self.async_abort(
            reason="asset_added",
            description_placeholders={
                "asset": asset_display_label(record),
                "group": group.title,
            },
        )
