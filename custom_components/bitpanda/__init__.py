"""The Bitpanda integration."""
from __future__ import annotations

from contextlib import suppress
import logging
from time import monotonic

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import migration
from .api import BitpandaApiClient
from .assets import AssetDirectory
from .const import (
    CONF_API_KEY,
    CONF_ASSETS,
    CONF_CURRENCY_ID,
    CONF_EXTRA_CURRENCIES,
    CONF_LEGACY_ADOPT,
    DOMAIN,
    ENTRY_TYPE_PRICE_TRACKER,
    REFRESH_MIN_COOLDOWN,
    SUBENTRY_TYPE_PRICE_GROUP,
    SUBENTRY_TYPE_WALLET_GROUP,
    entry_type,
)
from .devices import device_identifier
from .groups import (
    async_group_titles,
    async_remove_asset_from_group,
    async_retitle_groups_to_current_language,
    groups_of_type,
    tracked_assets,
)
from .naming import (
    asset_display_label,
    portfolio_device_identifier,
    price_device_asset_id,
    wallet_device_asset_id,
)
from .portfolio_coordinator import (
    EarnCoordinator,
    HistoryCoordinator,
    PortfolioCoordinator,
    PortfolioRuntime,
    RewardsCoordinator,
)
from .price_coordinator import EcbCoordinator, PriceTrackerRuntime, TickerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Records of held assets, shared across reloads of the Portfolio entry.
_ASSET_DIRECTORY_KEY = f"{DOMAIN}_asset_directory"


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an entry to version 3 (see migration.py)."""
    return await migration.async_migrate_entry(hass, entry)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one of the two services."""
    is_price_tracker = entry_type(entry) == ENTRY_TYPE_PRICE_TRACKER
    # Before anything else, and before the update listener below: the Price
    # Tracker's listener reloads on any change to the entry, subentries
    # included, so retitling after it existed would reload the entry this
    # same call is setting up.
    await async_retitle_groups_to_current_language(
        hass,
        entry,
        SUBENTRY_TYPE_PRICE_GROUP if is_price_tracker else SUBENTRY_TYPE_WALLET_GROUP,
    )
    if is_price_tracker:
        entry.runtime_data = await _async_start_price_tracker(hass, entry)
        # Options, groups and data all change what it tracks: rebuild on any change.
        reload_listener = _async_reload
    else:
        entry.runtime_data = await _async_start_portfolio(hass, entry)
        reload_listener = _async_reload_on_new_data_or_options
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(reload_listener))
    _async_register_refresh_service(hass)
    return True


async def _async_start_portfolio(hass: HomeAssistant, entry: ConfigEntry) -> PortfolioRuntime:
    session = async_get_clientsession(hass)
    client = BitpandaApiClient(entry.data[CONF_API_KEY], session)
    # Asset lookups are public: keyless, and the records outlive reloads.
    directory = AssetDirectory(
        BitpandaApiClient(None, session), hass.data.setdefault(_ASSET_DIRECTORY_KEY, {})
    )
    currency_id = entry.data[CONF_CURRENCY_ID]
    runtime = PortfolioRuntime(
        portfolio=PortfolioCoordinator(hass, entry, client, currency_id, directory),
        history=HistoryCoordinator(hass, entry, client, currency_id),
        earn=EarnCoordinator(hass, entry, client),
        rewards=RewardsCoordinator(hass, entry, client),
        group_titles=await async_group_titles(hass),
        data_at_setup=dict(entry.data),
        options_at_setup=dict(entry.options),
    )
    await _async_first_refresh(runtime.portfolio)
    # Earn, rewards and history are additive: a failure there must not block
    # setup, so they refresh with async_refresh(), which never raises
    # ConfigEntryNotReady. A 401 from any of them still reaches the reauth
    # dialog: DataUpdateCoordinator catches the ConfigEntryAuthFailed each
    # raises and starts reauth itself.
    await runtime.earn.async_refresh()
    await runtime.rewards.async_refresh()
    await runtime.history.async_refresh()
    return runtime


async def _async_start_price_tracker(
    hass: HomeAssistant, entry: ConfigEntry
) -> PriceTrackerRuntime:
    if entry.data.get(CONF_LEGACY_ADOPT):
        # Before any entity exists -- see migration.async_adopt_legacy_prices.
        migration.async_adopt_legacy_prices(hass, entry)
    # A group that tracks nothing shows up empty on the integration page. No
    # update listener exists yet, so dropping it triggers no reload.
    for group in groups_of_type(entry, SUBENTRY_TYPE_PRICE_GROUP):
        if not group.data[CONF_ASSETS]:
            hass.config_entries.async_remove_subentry(entry, group.subentry_id)
    session = async_get_clientsession(hass)
    tracked = {
        asset_id: asset_display_label(record)
        for asset_id, record in tracked_assets(entry).items()
    }
    tickers = TickerCoordinator(hass, entry, BitpandaApiClient(None, session), tracked)
    ecb = (
        EcbCoordinator(hass, entry, session)
        if entry.options.get(CONF_EXTRA_CURRENCIES)
        else None
    )
    await _async_first_refresh(tickers)
    if ecb is not None:
        # Not a first refresh: without rates the EUR sensors still work and
        # the other currencies say why they have no value.
        await ecb.async_refresh()
    return PriceTrackerRuntime(tickers=tickers, ecb=ecb)


async def _async_first_refresh(coordinator: DataUpdateCoordinator) -> None:
    """`async_config_entry_first_refresh`, its failure translated on every
    supported Home Assistant version.

    A failed first refresh raises ConfigEntryNotReady, and the integration
    page shows its message as the reason setup is being retried. From Home
    Assistant 2026.9 on it carries the translation of the UpdateFailed that
    caused it; before -- the 2025.5 floor included -- it carries none, and
    the page shows that UpdateFailed's English text instead. So it is raised
    again here with that translation. Its cause stays that UpdateFailed, as
    Home Assistant links it too: raised from None, with no request data.
    """
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady as err:
        cause = err.__cause__
        if (
            err.translation_key is not None
            or not isinstance(cause, HomeAssistantError)
            or cause.translation_key is None
        ):
            raise
        raise ConfigEntryNotReady(
            translation_domain=cause.translation_domain,
            translation_key=cause.translation_key,
            translation_placeholders=cause.translation_placeholders,
        ) from cause


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_reload_on_new_data_or_options(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Reload the Portfolio once its data or options differ from setup's.

    Its subentries, the wallet groups, change without a reload: the wallet
    manager adds and removes them itself, and brings the wallets of a group
    the user deleted back with the next refresh (portfolio_sensor.py).
    """
    runtime: PortfolioRuntime = entry.runtime_data
    if (dict(entry.data), dict(entry.options)) != (
        runtime.data_at_setup,
        runtime.options_at_setup,
    ):
        await hass.config_entries.async_reload(entry.entry_id)


def _loaded_runtimes(hass: HomeAssistant) -> list:
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]


def _refresh_cooldown(runtimes: list) -> float:
    """Seconds between two accepted `bitpanda.refresh` calls: the ticker
    interval, never below REFRESH_MIN_COOLDOWN. A shorter cooldown would let
    an automation drive ticker requests above the budgeted polling rate."""
    seconds = REFRESH_MIN_COOLDOWN.total_seconds()
    for runtime in runtimes:
        if isinstance(runtime, PriceTrackerRuntime):
            interval = runtime.tickers.update_interval
            if interval is not None:
                seconds = max(seconds, interval.total_seconds())
    return seconds


@callback
def _async_register_refresh_service(hass: HomeAssistant) -> None:
    """Register `bitpanda.refresh` once, shared by both services."""
    if hass.services.has_service(DOMAIN, "refresh"):
        return

    # Empty until the first accepted call: the monotonic clock can start near
    # zero after a boot.
    last_accepted: dict[str, float] = {}

    async def handle_refresh(call: ServiceCall) -> None:
        runtimes = _loaded_runtimes(hass)
        now = monotonic()
        previous = last_accepted.get("time")
        if previous is not None and now - previous < _refresh_cooldown(runtimes):
            _LOGGER.debug("Refresh cooldown active, ignoring call")
            return
        last_accepted["time"] = now
        for runtime in runtimes:
            if isinstance(runtime, PortfolioRuntime):
                await runtime.portfolio.async_request_refresh()
            else:
                await runtime.tickers.async_request_refresh()

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an entry; the refresh service goes with the last one.

    Some tests mark an entry LOADED (or patch its setup) without going
    through _async_register_refresh_service, so the service was never
    registered; has_service avoids Home Assistant's own "Unable to remove
    unknown service" warning for those.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if (
        unload_ok
        and hass.services.has_service(DOMAIN, "refresh")
        and not any(
            other.entry_id != entry.entry_id and other.state is ConfigEntryState.LOADED
            for other in hass.config_entries.async_entries(DOMAIN)
        )
    ):
        hass.services.async_remove(DOMAIN, "refresh")
    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Whether "Delete" on a device page may remove `device_entry`.

    Refused only where the device would come straight back: the Portfolio
    device, and the wallet of an asset the Portfolio holds. Deleting a price
    device stops tracking its asset.

    Both refusals raise a translated HomeAssistantError instead of returning
    False. Home Assistant's device-removal websocket handler
    (websocket_remove_config_entry_from_device in
    components/config/device_registry.py) awaits this hook with no
    try/except of its own, so the exception propagates to
    ActiveConnection.async_handle_exception, which sends the error's message
    and its translation_domain/translation_key/translation_placeholders to
    the frontend, and the device page shows the message -- identical at
    this integration's 2025.5.0 floor and in a 2026.9.3 test image. The
    message is in Home Assistant's language (see _async_refusal).
    """
    identifier = device_identifier(device_entry)
    if identifier is None:
        return True
    entry_id = config_entry.entry_id
    if entry_type(config_entry) == ENTRY_TYPE_PRICE_TRACKER:
        asset_id = price_device_asset_id(entry_id, identifier)
        if asset_id is not None:
            async_remove_asset_from_group(hass, config_entry, asset_id)
        return True
    if identifier == portfolio_device_identifier(entry_id):
        raise await _async_refusal(hass, "portfolio_device_not_removable")
    asset_id = wallet_device_asset_id(entry_id, identifier)
    if asset_id is None or config_entry.state is not ConfigEntryState.LOADED:
        return True
    runtime: PortfolioRuntime = config_entry.runtime_data
    if asset_id in runtime.portfolio.data.held:
        record = runtime.portfolio.data.assets.get(asset_id)
        asset_label = (
            asset_display_label(record) if record is not None else device_entry.name
        )
        raise await _async_refusal(hass, "held_wallet_not_removable", {"asset": asset_label})
    # The wallet manager keeps a wallet until its asset has been missing from
    # several refreshes, and would not create it again if the asset were
    # bought back in that time. A reload starts it afresh, and its emptied
    # group -- once the websocket handler's device removal above has run --
    # follows at the reload's first reconcile.
    hass.config_entries.async_schedule_reload(entry_id)
    return True


async def _async_refusal(
    hass: HomeAssistant, key: str, placeholders: dict[str, str] | None = None
) -> HomeAssistantError:
    """A refusal to delete a device, its message in Home Assistant's language.

    The device page shows the error's message as it arrives, and Home
    Assistant renders a translated exception's message in English only
    (translation.async_get_exception_message, at 2025.5 as at 2026.9). So
    the message is written here in Home Assistant's own language, from the
    `exceptions` translations -- cached for that language since the
    integration was set up, loaded now if the language changed since;
    English stands in for a missing text -- the way Home Assistant renders
    one: trailing full stop dropped, placeholders filled. The translation
    fields stay, for a frontend that translates them itself. Without any
    text, Home Assistant renders its English message as before.
    """
    translations = await async_get_translations(
        hass, hass.config.language, "exceptions", {DOMAIN}
    )
    message = translations.get(f"component.{DOMAIN}.exceptions.{key}.message")
    if message:
        message = message.rstrip(".")
        if placeholders:
            with suppress(KeyError):
                message = message.format(**placeholders)
    return HomeAssistantError(
        *([message] if message else []),
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders=placeholders,
    )
