"""The "Add price tracker" config subentry flow of the Price Tracker.

Category first, then one searchable pick from that category's catalogue --
public data, fetched without a key and kept for an hour. The asset joins the
group of its asset type, which the flow creates when there is none yet.

The pick shows under one of two step ids, each with texts of its own:
`security` for stocks, ETFs and ETCs, whose labels carry their ISIN, and
`asset` for every other type, whose help text leaves the ISIN out.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, cast

import voluptuous as vol
from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.core import HassJob, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import BitpandaApiClient, BitpandaApiError, BitpandaRateLimitError
from .assets import (
    ASSET_CATEGORY_FILTERS,
    ISIN_CATEGORIES,
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
from .language import entry_language
from .naming import asset_display_label

# The stock listing alone is ~103 requests: kept for an hour, it serves a
# round of picks, and an asset Bitpanda adds shows within the hour.
_CATALOGUE_CACHE_TTL = timedelta(hours=1)

# Its own top-level hass.data key, never inside hass.data[DOMAIN]: it serves
# every flow and survives entry reloads.
_CATALOGUE_KEY = f"{DOMAIN}_asset_catalogue"


async def async_category_listing(
    hass: HomeAssistant, client: BitpandaApiClient, category: str
) -> list[dict[str, Any]]:
    """Every asset of one category, all pages, slimmed, kept for an hour.

    A timer drops each listing an hour after it was loaded, whether or not
    the dialog is opened again: no listing outstays its hour in memory --
    the stocks alone take about 6 MB. Only the timer ends a listing; no
    clock is read here, so a clock set forward cannot end one early. A
    timer drops only the listing it was started for: two dialogs can load
    the same category at once, the later listing replacing the earlier one.
    Home Assistant cancels the timers when it stops.

    Nothing here catches an API error: an error partway through a
    multi-filter category must not cache a partial listing.
    """
    store: dict[str, list[dict[str, Any]]] = hass.data.setdefault(_CATALOGUE_KEY, {})
    cached = store.get(category)
    if cached is not None:
        return cached

    assets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for type_, group in ASSET_CATEGORY_FILTERS[category]:
        for asset in await client.async_list_assets(type_, group):
            asset_id = asset.get("id")
            if asset_id and asset_id not in seen:
                seen.add(asset_id)
                assets.append(slim_asset(asset))
    store[category] = assets

    @callback
    def _async_drop(_: datetime) -> None:
        if store.get(category) is assets:
            del store[category]

    async_call_later(
        hass, _CATALOGUE_CACHE_TTL, HassJob(_async_drop, cancel_on_shutdown=True)
    )
    return assets


class PriceTrackerSubentryFlow(ConfigSubentryFlow):
    """Track one more asset: it joins the group of its asset type (a
    price_group subentry), or starts that group. One device per asset, one
    sensor per asset and currency."""

    def __init__(self) -> None:
        self._category: str | None = None
        # Category -> the listing this dialog got: kept until the dialog
        # ends, whatever the store's timer does meanwhile.
        self._listings: dict[str, list[dict[str, Any]]] = {}

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

    def _show_assets(
        self, options: list[SelectOptionDict], error: str | None
    ) -> SubentryFlowResult:
        """One pick from `options`.

        `custom_value=True` is what makes the frontend render a single select
        as a searchable combo box (without it: a plain, unsearchable list).
        The field is optional: submitting it empty goes back to the categories,
        the way out of every error and of an empty listing. Stocks, ETFs and
        ETCs show under the step id `security`, whose help text names the
        ISIN they can be searched by (see the module docstring).
        """
        return self.async_show_form(
            step_id="security" if self._category in ISIN_CATEGORIES else "asset",
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

    async def _async_listing(self) -> tuple[list[dict[str, Any]], str | None]:
        """The listing of the category picked, once per dialog: showing it and
        resolving the pick use the same one, even when the store's hour ends
        in between."""
        # Set by the user step: this step is only ever reached through it.
        category = cast(str, self._category)
        kept = self._listings.get(category)
        if kept is not None:
            return kept, None
        client = BitpandaApiClient(None, async_get_clientsession(self.hass))
        try:
            listing = await async_category_listing(self.hass, client, category)
        except BitpandaRateLimitError:
            return [], "rate_limited"
        except BitpandaApiError:
            return [], "cannot_connect"
        self._listings[category] = listing
        return listing, None

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
        options: list[SelectOptionDict] = sorted(
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

    async def async_step_security(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """The asset step of stocks, ETFs and ETCs: the same pick, under its
        own step id only for texts that name the ISIN."""
        return await self.async_step_asset(user_input)

    async def _async_track(self, record: dict[str, Any]) -> SubentryFlowResult:
        """Add `record` to the group of its asset type, or start that group.

        Joining ends the dialog with a message naming the group: no subentry
        is created, so Home Assistant's own confirmation would not fit.
        """
        category = asset_category(record)
        # A new group is titled in the entry's language. _get_entry() raises
        # UnknownEntry if the Price Tracker was removed while the dialog was
        # open, as Home Assistant itself does when a group is created then.
        titles = await async_group_titles(self.hass, entry_language(self._get_entry()))
        # Looked up again after the last await, so no other dialog can start
        # the same group before this step ends.
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
