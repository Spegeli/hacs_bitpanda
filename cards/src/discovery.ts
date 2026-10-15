// Finds the integration's sensors through Home Assistant's registries:
// platform "bitpanda", the device's model, the sensor's translation key.
// Never by entity ID, which users can rename.
import {
  CATEGORIES,
  type AssetInfo,
  type AssetSelection,
  type Category,
  type Hass,
  type HassDevice,
  type HassEntityRegistryEntry,
  type PortfolioRefs,
  type PriceRefs,
  type Timeframe,
  type WalletRefs,
} from "./types";

const PLATFORM = "bitpanda";

const RETURN_KEYS: Record<string, Timeframe> = {
  return_day: "day",
  return_week: "week",
  return_month: "month",
  return_six_month: "six_month",
  return_year: "year",
};

const squash = (text: string): string => text.replace(/\s+/g, "").toLowerCase();

/** "Name (SYMBOL)", or SYMBOL when the name only repeats it or is empty:
 * the integration's naming.asset_display_label, without the ISIN. */
export function assetLabel(name: string | undefined, symbol: string): string {
  const trimmed = (name ?? "").trim();
  return trimmed && squash(trimmed) !== squash(symbol) ? `${trimmed} (${symbol})` : symbol;
}

// The integration's entities by device, per entity registry: Home Assistant
// hands a card a new hass on every state change in the house, and a new
// entity registry object only when the registry changed.
const searched = new WeakMap<Hass["entities"], Map<string, HassEntityRegistryEntry[]>>();

function entitiesByDevice(hass: Hass): Map<string, HassEntityRegistryEntry[]> {
  const known = searched.get(hass.entities);
  if (known) return known;
  const byDevice = new Map<string, HassEntityRegistryEntry[]>();
  for (const entry of Object.values(hass.entities)) {
    if (!entry || entry.platform !== PLATFORM || !entry.device_id) continue;
    const list = byDevice.get(entry.device_id) ?? [];
    list.push(entry);
    byDevice.set(entry.device_id, list);
  }
  searched.set(hass.entities, byDevice);
  return byDevice;
}

/** The integration's entities by device, for devices of one model. */
function devicesOf(hass: Hass, model: string): [HassDevice, HassEntityRegistryEntry[]][] {
  const byDevice = entitiesByDevice(hass);
  const found: [HassDevice, HassEntityRegistryEntry[]][] = [];
  for (const [deviceId, entries] of byDevice) {
    const device = hass.devices[deviceId];
    if (device?.model === model) found.push([device, entries]);
  }
  return found;
}

const text = (value: unknown): string | undefined =>
  typeof value === "string" && value !== "" ? value : undefined;

type Known = Omit<AssetInfo, "deviceId" | "assetId">;

// What the cards last read about each asset, by device. A sensor that turns
// unavailable loses its attributes: the asset keeps its name and category
// until the integration removes the device.
const lastKnown = new Map<string, Known>();

// The integration's device names end in " Wallet" or " Price Tracker".
const DEVICE_SUFFIX = / (Wallet|Price Tracker)$/;

/** What the device's sensors say about their asset, else what they said
 * before, else the device's name. */
function assetInfo(hass: Hass, device: HassDevice, entries: HassEntityRegistryEntry[]): AssetInfo {
  const attributes = entries.map((entry) => hass.states[entry.entity_id]?.attributes).find((attrs) => attrs?.["asset"]);
  let known: Known;
  if (attributes) {
    const symbol = text(attributes["asset"]) ?? "";
    const isin = text(attributes["asset_isin"]);
    const category = text(attributes["asset_category"]);
    const assetName = text(attributes["asset_name"]);
    known = {
      name: assetLabel(assetName, symbol),
      shortName: assetName ?? symbol,
      symbol,
      ...(isin ? { isin } : {}),
      ...(category && (CATEGORIES as readonly string[]).includes(category) ? { category: category as Category } : {}),
    };
    lastKnown.set(device.id, known);
  } else {
    const base = (text(device.name) ?? "").replace(DEVICE_SUFFIX, "");
    known = lastKnown.get(device.id) ?? { name: base, shortName: base, symbol: "" };
  }
  const own = text(device.name_by_user);
  return {
    deviceId: device.id,
    assetId: device.serial_number ?? "",
    ...known,
    ...(own ? { name: own, shortName: own } : {}),
  };
}

export function findPortfolio(hass: Hass): PortfolioRefs | undefined {
  const [portfolio] = devicesOf(hass, "Portfolio");
  if (!portfolio) return undefined;
  const [device, entries] = portfolio;
  const refs: PortfolioRefs = { deviceId: device.id, returns: {}, wallets: [] };
  for (const entry of entries) {
    const key = entry.translation_key ?? "";
    if (key === "total_value") refs.totalValue = entry.entity_id;
    else if (key === "cash") refs.cash = entry.entity_id;
    else if (key === "cash_plus") refs.cashPlus = entry.entity_id;
    else if (key in RETURN_KEYS) refs.returns[RETURN_KEYS[key] as Timeframe] = entry.entity_id;
  }
  for (const [wallet, walletEntries] of devicesOf(hass, "Wallet")) {
    const item: WalletRefs = assetInfo(hass, wallet, walletEntries);
    for (const entry of walletEntries) {
      if (entry.translation_key === "wallet") item.available = entry.entity_id;
      else if (entry.translation_key === "wallet_total") item.total = entry.entity_id;
      else if (entry.translation_key === "staking") item.staking = entry.entity_id;
    }
    refs.wallets.push(item);
  }
  return refs;
}

export function findPriceAssets(hass: Hass): PriceRefs[] {
  return devicesOf(hass, "Price Tracker").map(([device, entries]) => {
    const prices: Record<string, string> = {};
    for (const entry of entries) {
      if (entry.translation_key !== "price") continue;
      const currency = text(hass.states[entry.entity_id]?.attributes["unit_of_measurement"]);
      if (currency) prices[currency] = entry.entity_id;
    }
    return { ...assetInfo(hass, device, entries), prices };
  });
}

/** Every currency some asset has a price in: EUR first, then by code. */
export function priceCurrencies(assets: readonly PriceRefs[]): string[] {
  const codes = new Set(assets.flatMap((asset) => Object.keys(asset.prices)));
  const others = [...codes].filter((code) => code !== "EUR").sort();
  return codes.has("EUR") ? ["EUR", ...others] : others;
}

/** The assets of the asset groups a card shows: all, all but the picked, or
 * only the picked, in the assets' own order; an asset without a group
 * counts as "other". */
export function selectGroups<T extends AssetInfo>(items: readonly T[], mode: AssetSelection, picked: readonly string[]): T[] {
  if (mode === "all") return [...items];
  const keep = mode === "only";
  return items.filter((item) => picked.includes(item.category ?? "other") === keep);
}

/** Whether `id` names `item`: its Bitpanda asset ID -- what a card's
 * configuration holds -- or its device ID, as configurations from before
 * hold it. */
const names = (item: AssetInfo, id: string): boolean => id === item.deviceId || (id !== "" && id === item.assetId);

/** The assets a card shows: all, all but the picked, or only the picked in
 * the order picked, each once. A picked asset without a device right now is
 * skipped. */
export function selectAssets<T extends AssetInfo>(
  items: readonly T[],
  mode: AssetSelection,
  picked: readonly string[],
): T[] {
  if (mode === "all_except") return items.filter((item) => !picked.some((id) => names(item, id)));
  if (mode === "only") {
    const shown: T[] = [];
    for (const id of picked) {
      const item = items.find((candidate) => names(candidate, id));
      if (item && !shown.includes(item)) shown.push(item);
    }
    return shown;
  }
  return [...items];
}
