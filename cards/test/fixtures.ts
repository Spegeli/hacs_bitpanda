// A fake Home Assistant for the card tests: registries and states the way the
// integration creates them, built from a few lines per device.
import type { Hass, HassDevice, HassEntityRegistryEntry, HassEntityState } from "../src/types";

export interface FakeSensor {
  entityId: string;
  translationKey: string;
  state: string;
  attributes?: Record<string, unknown>;
  platform?: string;
}

export interface FakeDevice {
  id: string;
  model: string;
  name: string;
  nameByUser?: string;
  serial?: string;
  sensors: FakeSensor[];
}

export interface FakeHassOptions {
  devices?: FakeDevice[];
  foreign?: FakeSensor[];
  language?: string;
  numberFormat?: string;
  /** Home Assistant's profile settings: "language", "system", "12", "24". */
  timeFormat?: string;
  /** "local" or "server". */
  timeZone?: string;
  serverTimeZone?: string;
  callWS?: (message: Record<string, unknown>) => Promise<unknown>;
  translations?: Record<string, string>;
}

export type FakeHass = Hass & {
  /** A new hass object with one state replaced, as Home Assistant hands a
   * card after a state change: unchanged states keep their identity. */
  withState(entityId: string, state: string, attributes?: Record<string, unknown>): FakeHass;
  messages: Record<string, unknown>[];
};

function stateOf(sensor: FakeSensor): HassEntityState {
  return { entity_id: sensor.entityId, state: sensor.state, attributes: { ...(sensor.attributes ?? {}) } };
}

export function makeHass(options: FakeHassOptions = {}): FakeHass {
  const states: Record<string, HassEntityState> = {};
  const entities: Record<string, HassEntityRegistryEntry> = {};
  const devices: Record<string, HassDevice> = {};
  for (const device of options.devices ?? []) {
    devices[device.id] = {
      id: device.id,
      model: device.model,
      name: device.name,
      name_by_user: device.nameByUser ?? null,
      serial_number: device.serial ?? null,
    };
    for (const sensor of device.sensors) {
      entities[sensor.entityId] = {
        entity_id: sensor.entityId,
        device_id: device.id,
        platform: sensor.platform ?? "bitpanda",
        translation_key: sensor.translationKey,
      };
      states[sensor.entityId] = stateOf(sensor);
    }
  }
  for (const sensor of options.foreign ?? []) {
    entities[sensor.entityId] = {
      entity_id: sensor.entityId,
      device_id: null,
      platform: sensor.platform ?? "other",
      translation_key: sensor.translationKey,
    };
    states[sensor.entityId] = stateOf(sensor);
  }
  const translations = options.translations ?? {};
  const messages: Record<string, unknown>[] = [];
  // Like Home Assistant, only the states change between two hass objects:
  // the registries, the locale and the functions keep their identity.
  const locale = {
    language: options.language ?? "en",
    number_format: options.numberFormat ?? "language",
    time_format: options.timeFormat ?? "language",
    time_zone: options.timeZone ?? "local",
  };
  const config = { time_zone: options.serverTimeZone ?? "Europe/Vienna" };
  const formatEntityState = (stateObj: HassEntityState): string => {
    const unit = stateObj.attributes["unit_of_measurement"];
    return unit === undefined ? stateObj.state : `${stateObj.state} ${String(unit)}`;
  };
  const localize = (key: string): string => translations[key] ?? "";
  const loadBackendTranslation = async (): Promise<undefined> => undefined;
  const callWS = async <T>(message: Record<string, unknown>): Promise<T> => {
    messages.push(message);
    return (options.callWS ? await options.callWS(message) : {}) as T;
  };
  const build = (current: Record<string, HassEntityState>): FakeHass => ({
    states: current,
    entities,
    devices,
    language: locale.language,
    locale,
    config,
    formatEntityState,
    localize,
    loadBackendTranslation,
    callWS,
    withState(entityId, state, attributes) {
      const previous = current[entityId];
      return build({
        ...current,
        [entityId]: { entity_id: entityId, state, attributes: attributes ?? previous?.attributes ?? {} },
      });
    },
    messages,
  });
  return build(states);
}

// --- The integration's devices -------------------------------------------------

export function portfolioDevice(values: {
  total?: string;
  cash?: string;
  cashPlus?: string;
  returns?: Partial<Record<"day" | "week" | "month" | "six_month" | "year", string>>;
  currency?: string;
} = {}): FakeDevice {
  const unit = values.currency ?? "EUR";
  const money = (entityId: string, key: string, state: string): FakeSensor => ({
    entityId,
    translationKey: key,
    state,
    attributes: { unit_of_measurement: unit, device_class: "monetary" },
  });
  const returns = values.returns ?? { day: "-0.42", week: "2.31", month: "5.87", six_month: "11.2", year: "18.65" };
  return {
    id: "dev-portfolio",
    model: "Portfolio",
    name: "Bitpanda Portfolio",
    sensors: [
      money("sensor.bitpanda_portfolio_total_value", "total_value", values.total ?? "12760.20"),
      money("sensor.bitpanda_portfolio_cash", "cash", values.cash ?? "812.40"),
      money("sensor.bitpanda_portfolio_cash_plus", "cash_plus", values.cashPlus ?? "2000.00"),
      ...Object.entries(returns).map(([timeframe, state]) => ({
        entityId: `sensor.bitpanda_portfolio_return_${timeframe}`,
        translationKey: `return_${timeframe}`,
        state,
        attributes: { unit_of_measurement: "%" },
      })),
    ],
  };
}

export interface FakeWallet {
  symbol: string;
  name: string;
  category: string;
  isin?: string;
  units: number;
  total: string;
  available?: string;
  staked?: { units: number; value: string; apr?: number; rewards?: { net: number; netValue: number; count: number; lastAt: string } };
  returnPercent?: number;
  averageBuyPrice?: number;
  invested?: number;
  totalReturn?: number;
  nameByUser?: string;
  currency?: string;
}

export function walletDevice(wallet: FakeWallet): FakeDevice {
  const slug = wallet.symbol.toLowerCase();
  const unit = wallet.currency ?? "EUR";
  const asset: Record<string, unknown> = {
    asset: wallet.symbol,
    asset_name: wallet.name,
    asset_category: wallet.category,
    ...(wallet.isin ? { asset_isin: wallet.isin } : {}),
  };
  const stakedUnits = wallet.staked?.units ?? 0;
  const sensors: FakeSensor[] = [
    {
      entityId: `sensor.bitpanda_${slug}_wallet`,
      translationKey: "wallet",
      state: wallet.available ?? wallet.total,
      attributes: { ...asset, units: wallet.units - stakedUnits, unit_of_measurement: unit },
    },
    {
      entityId: `sensor.bitpanda_${slug}_wallet_total`,
      translationKey: "wallet_total",
      state: wallet.total,
      attributes: {
        ...asset,
        units: wallet.units,
        unit_of_measurement: unit,
        ...(wallet.averageBuyPrice !== undefined ? { average_buy_price: wallet.averageBuyPrice } : {}),
        ...(wallet.invested !== undefined ? { invested_amount: wallet.invested } : {}),
        ...(wallet.totalReturn !== undefined ? { total_return: wallet.totalReturn } : {}),
        ...(wallet.returnPercent !== undefined ? { total_return_percent: wallet.returnPercent } : {}),
      },
    },
  ];
  if (wallet.staked) {
    const rewards = wallet.staked.rewards;
    sensors.push({
      entityId: `sensor.bitpanda_${slug}_staking`,
      translationKey: "staking",
      state: wallet.staked.value,
      attributes: {
        ...asset,
        units: wallet.staked.units,
        unit_of_measurement: unit,
        ...(wallet.staked.apr !== undefined ? { apr_percent: wallet.staked.apr } : {}),
        ...(rewards
          ? {
              rewards_net: rewards.net,
              rewards_net_value: rewards.netValue,
              rewards_count: rewards.count,
              rewards_last_at: rewards.lastAt,
            }
          : {}),
      },
    });
  }
  return {
    id: `dev-wallet-${slug}`,
    model: "Wallet",
    name: `${wallet.name} (${wallet.symbol}) Wallet`,
    ...(wallet.nameByUser ? { nameByUser: wallet.nameByUser } : {}),
    serial: `id-${slug}`,
    sensors,
  };
}

export interface FakePriceAsset {
  symbol: string;
  name: string;
  category: string;
  isin?: string;
  prices: Record<string, { state: string; change24h?: number; price24hAgo?: number; rateDate?: string }>;
  nameByUser?: string;
}

export function priceDevice(asset: FakePriceAsset): FakeDevice {
  const slug = asset.symbol.toLowerCase();
  return {
    id: `dev-price-${slug}`,
    model: "Price Tracker",
    name: `${asset.name} (${asset.symbol}) Price Tracker`,
    ...(asset.nameByUser ? { nameByUser: asset.nameByUser } : {}),
    serial: `id-${slug}`,
    sensors: Object.entries(asset.prices).map(([currency, price]) => ({
      entityId: `sensor.bitpanda_${slug}_price_tracker_${currency.toLowerCase()}`,
      translationKey: "price",
      state: price.state,
      attributes: {
        asset: asset.symbol,
        asset_name: asset.name,
        asset_category: asset.category,
        ...(asset.isin ? { asset_isin: asset.isin } : {}),
        unit_of_measurement: currency,
        ...(price.change24h !== undefined ? { change_24h_pct: price.change24h } : {}),
        ...(price.price24hAgo !== undefined ? { price_24h_ago: price.price24hAgo } : {}),
        ...(price.rateDate ? { rate_date: price.rateDate, rate_source: "ECB" } : {}),
      },
    })),
  };
}

// --- A made-up portfolio ------------------------------------------------------------

export const BTC: FakeWallet = {
  symbol: "BTC", name: "Bitcoin", category: "crypto", units: 0.0653, total: "5890.11",
  returnPercent: 12.4, averageBuyPrice: 80200, invested: 5240.0, totalReturn: 650.11,
};
export const ETH: FakeWallet = {
  symbol: "ETH", name: "Ethereum", category: "crypto", units: 0.55, total: "1269.91", available: "762.00",
  staked: { units: 0.22, value: "507.91", apr: 2.9, rewards: { net: 0.0041, netValue: 9.47, count: 12, lastAt: "2026-10-06T16:12:00Z" } },
  returnPercent: -3.1, averageBuyPrice: 2377, invested: 1307.35, totalReturn: -37.44,
};
export const EUNL: FakeWallet = {
  symbol: "EUNL", name: "iShares Core MSCI World UCITS ETF", category: "etf", isin: "IE00B4L5Y983",
  units: 21.4, total: "2045.10", returnPercent: 8.0,
};
export const XAU: FakeWallet = {
  symbol: "XAU", name: "Gold", category: "metal", units: 0.56, total: "67.01", returnPercent: 4.2,
};
