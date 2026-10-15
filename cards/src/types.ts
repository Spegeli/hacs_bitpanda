// What the cards share: the subset of Home Assistant's frontend object they
// read, and the integration's sensors as the cards find them.

export type Timeframe = "day" | "week" | "month" | "six_month" | "year";
export const TIMEFRAMES: readonly Timeframe[] = ["day", "week", "month", "six_month", "year"];

export type Category = "crypto" | "stock" | "etf" | "etc" | "index" | "metal" | "other";
export const CATEGORIES: readonly Category[] = [
  "crypto",
  "stock",
  "etf",
  "etc",
  "index",
  "metal",
  "other",
];


export type AssetSelection = "all" | "all_except" | "only";
export const ASSET_SELECTIONS: readonly AssetSelection[] = ["all", "all_except", "only"];

export interface HassEntityState {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
  last_changed?: string;
  last_updated?: string;
}

export interface HassEntityRegistryEntry {
  entity_id: string;
  device_id?: string | null;
  platform: string;
  translation_key?: string | null;
  hidden?: boolean;
  /** The decimals Home Assistant shows: the user's, else the integration's. */
  display_precision?: number;
}

export interface HassDevice {
  id: string;
  model?: string | null;
  name?: string | null;
  name_by_user?: string | null;
  serial_number?: string | null;
  /** The (domain, identifier) pairs the integrations gave the device. */
  identifiers?: [string, string][];
}

export interface HassLocale {
  language: string;
  number_format: string;
  /** "language", "system", "12" or "24". */
  time_format?: string;
  /** "local" (the browser's) or "server". */
  time_zone?: string;
}

export interface Hass {
  states: Record<string, HassEntityState | undefined>;
  entities: Record<string, HassEntityRegistryEntry | undefined>;
  devices: Record<string, HassDevice | undefined>;
  locale: HassLocale;
  config?: { time_zone?: string };
  language: string;
  formatEntityState: (stateObj: HassEntityState, state?: string) => string;
  localize: (key: string, ...args: unknown[]) => string;
  loadBackendTranslation: (category: string, integration?: string) => Promise<unknown>;
  callWS: <T>(message: Record<string, unknown>) => Promise<T>;
}

/** An asset as a card shows it. `name` is the display name: the user's own
 * device name, else "Name (SYMBOL)" (discovery.assetLabel). */
export interface AssetInfo {
  deviceId: string;
  assetId: string;
  name: string;
  /** The name alone, for tiles: the user's device name, else the asset's
   * name, else its symbol. */
  shortName: string;
  symbol: string;
  isin?: string;
  category?: Category;
}

/** A wallet's sensors, by entity ID. */
export interface WalletRefs extends AssetInfo {
  available?: string;
  total?: string;
  staking?: string;
}

/** A tracked asset's price sensors: currency code -> entity ID. */
export interface PriceRefs extends AssetInfo {
  prices: Record<string, string>;
}

export interface PortfolioRefs {
  deviceId: string;
  totalValue?: string;
  cash?: string;
  cashPlus?: string;
  returns: Partial<Record<Timeframe, string>>;
  wallets: WalletRefs[];
}

// --- Card configurations (option keys are an interface: never renamed) -------

/** EUR and the extra currencies the Price Tracker offers (const.py,
 * SUPPORTED_CURRENCIES). */
export const CURRENCIES: readonly string[] = [
  "EUR",
  "CHF",
  "CZK",
  "DKK",
  "GBP",
  "HUF",
  "NOK",
  "PLN",
  "RON",
  "SEK",
  "TRY",
  "USD",
];

export type WalletSort = "value" | "return" | "name";
export const WALLET_SORTS: readonly WalletSort[] = ["value", "return", "name"];

/** Wallets listed before Show all, without groups. */
export const DEFAULT_WALLET_LIMIT = 5;

export type PriceSort = "selection" | "name" | "change_desc" | "change_asc";
export const PRICE_SORTS: readonly PriceSort[] = ["selection", "name", "change_desc", "change_asc"];

export type Layout = "list" | "tiles";
export const LAYOUTS: readonly Layout[] = ["list", "tiles"];

export interface BaseConfig {
  type: string;
  title?: string;
}

export interface PortfolioConfig extends BaseConfig {
  timeframe?: Timeframe;
  /** The total value and its return. */
  show_total?: boolean;
  show_graph?: boolean;
  show_cash?: boolean;
  show_allocation?: boolean;
  show_wallets?: boolean;
  group_wallets?: boolean;
  /** A search field above the wallets. */
  show_search?: boolean;
  sort?: WalletSort;
  /** Rows before "Show all" in the list without groups. */
  limit?: number;
  group_selection?: AssetSelection;
  groups?: Category[];
  asset_selection?: AssetSelection;
  assets?: string[];
  hide_amounts?: boolean;
}

export interface PriceTrackerConfig extends BaseConfig {
  layout?: Layout;
  timeframe?: Timeframe;
  currency?: string;
  sort?: PriceSort;
  group_selection?: AssetSelection;
  groups?: Category[];
  asset_selection?: AssetSelection;
  assets?: string[];
  limit?: number;
}
