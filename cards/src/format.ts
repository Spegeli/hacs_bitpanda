// Numbers, units, changes and dates as the viewer reads them: Home
// Assistant's own formatting for sensor states, its number format setting
// for everything the cards compute.
import { speaksLanguageOf, tCount } from "./i18n";
import type { Category, Hass, HassEntityState } from "./types";

export type Direction = "up" | "down" | "flat" | "none";

// Home Assistant's number_format setting, as its own frontend reads it.
function numberLocale(hass: Hass): string | undefined {
  switch (hass.locale.number_format) {
    case "comma_decimal":
      return "en-US";
    case "decimal_comma":
      return "de";
    case "space_comma":
      return "fr";
    case "quote_decimal":
      return "de-CH";
    case "system":
      return undefined;
    default:
      return hass.locale.language;
  }
}

export function formatNumber(hass: Hass, value: number, maximumFractionDigits: number, minimumFractionDigits = 0): string {
  return new Intl.NumberFormat(numberLocale(hass), {
    maximumFractionDigits,
    minimumFractionDigits,
    useGrouping: hass.locale.number_format !== "none",
  }).format(value);
}

/** The digits of units short, as the Bitpanda app lists them: up to 4
 * decimals, rounded down; below 0.0001 the first two digits, so that a
 * holding never reads 0. */
function shortUnitDigits(units: number): Intl.NumberFormatOptions {
  const tiny = units !== 0 && Math.abs(units) < 0.0001;
  return { ...(tiny ? { maximumSignificantDigits: 2 } : { maximumFractionDigits: 4 }), roundingMode: "trunc" };
}

function formatShortUnits(hass: Hass, units: number): string {
  return new Intl.NumberFormat(numberLocale(hass), {
    ...shortUnitDigits(units),
    useGrouping: hass.locale.number_format !== "none",
  }).format(units);
}

const LONG_UNIT_DIGITS = 8;

/** "0.0653 BTC", "21.4 shares" for stocks, ETFs and ETCs, "0.56 g" for
 * metals, which Bitpanda counts in grams; all decimals, or `short` for a
 * wallet row. */
export function formatUnits(hass: Hass, units: number, category: Category | undefined, symbol: string, short = false): string {
  const amount = short ? formatShortUnits(hass, units) : formatNumber(hass, units, LONG_UNIT_DIGITS);
  if (category === "stock" || category === "etf" || category === "etc") {
    // The count word follows the number as shown: 1.0004 shares, 1 share.
    const digits = short ? shortUnitDigits(units) : { maximumFractionDigits: LONG_UNIT_DIGITS };
    return `${amount} ${tCount(hass, "shares", units, digits)}`;
  }
  return `${amount} ${category === "metal" ? "g" : symbol}`;
}

const MISSING = new Set(["unavailable", "unknown"]);

/** A sensor's state as Home Assistant shows it; undefined when there is
 * none to show. */
export function formatState(hass: Hass, entityId: string | undefined): string | undefined {
  const state = entityId ? hass.states[entityId] : undefined;
  return state && !MISSING.has(state.state) ? hass.formatEntityState(state) : undefined;
}

/** `value`, which the card added up, formatted as Home Assistant formats
 * the sensor `entityId`: its unit, precision and the user's format. */
export function formatLike(hass: Hass, entityId: string | undefined, value: number | undefined): string | undefined {
  const state = entityId ? hass.states[entityId] : undefined;
  return state && value !== undefined ? hass.formatEntityState({ ...state, state: String(value) }) : undefined;
}

/** A money amount in `currency` with 2 decimals, as the sensors show it. */
export function formatMoney(hass: Hass, value: number, currency: string, signed = false): string {
  return formatCurrency(hass, value, currency, 2, signed);
}

/** A price in `currency`, with as many decimals as its size needs: 2 from
 * 10 up, 4 from 1, 8 below. Used for the average buy price, it allows more
 * decimals below 1 than the price sensors show (5 to 7). */
export function formatPrice(hass: Hass, value: number, currency: string): string {
  const size = Math.abs(value);
  return formatCurrency(hass, value, currency, size >= 10 || size === 0 ? 2 : size >= 1 ? 4 : 8, false);
}

/** An asset's price in `currency`, with the decimals the Price Tracker
 * gives a price of its size (priceDigits): a wallet's current price beside
 * the Price Tracker's prices. */
export function formatAssetPrice(hass: Hass, value: number, currency: string): string {
  return formatCurrency(hass, value, currency, priceDigits(value), false);
}

function formatCurrency(hass: Hass, value: number, currency: string, digits: number, signed: boolean): string {
  try {
    return new Intl.NumberFormat(numberLocale(hass), {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: digits,
      useGrouping: hass.locale.number_format !== "none",
      ...(signed ? { signDisplay: "exceptZero" as const } : {}),
    }).format(value);
  } catch {
    return `${formatNumber(hass, value, digits)} ${currency}`;
  }
}

/** The decimals the integration gives a price of this size (price_sensor's
 * display_precision), for a sensor whose display precision is unknown. */
function priceDigits(price: number): number {
  const size = Math.abs(price);
  if (size === 0 || size >= 10) return 2;
  if (size >= 1) return 4;
  if (size >= 0.1) return 5;
  if (size >= 0.001) return 6;
  return size >= 0.0001 ? 7 : 8;
}

/** A change of the sensor `entityId`'s value, signed, formatted as Home
 * Assistant formats that sensor, with the decimals it shows: never counted
 * from the state, which Home Assistant writes without trailing zeros and,
 * below 0.0001, as an exponent. */
export function formatSignedLike(hass: Hass, entityId: string | undefined, value: number | undefined): string | undefined {
  const state = entityId ? hass.states[entityId] : undefined;
  if (!state || MISSING.has(state.state) || value === undefined || !Number.isFinite(value)) return undefined;
  const precision = hass.entities[state.entity_id]?.display_precision;
  const digits = typeof precision === "number" ? precision : priceDigits(Number(state.state));
  const rounded = Number(value.toFixed(digits)) === 0 ? (0).toFixed(digits) : value.toFixed(digits);
  const text = hass.formatEntityState({ ...state, state: rounded });
  return Number(rounded) > 0 ? `+${text}` : text;
}

/** A numeric attribute of a state that has its value. */
export function numberAttribute(state: HassEntityState | undefined, key: string): number | undefined {
  if (!state || MISSING.has(state.state)) return undefined;
  const value = state.attributes[key];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

export function numericState(hass: Hass, entityId: string | undefined): number | undefined {
  const state = entityId ? hass.states[entityId] : undefined;
  if (!state || MISSING.has(state.state) || state.state.trim() === "") return undefined;
  const value = Number(state.state);
  return Number.isFinite(value) ? value : undefined;
}

// Languages that write a space before %, as Home Assistant's frontend does
// (by the profile's language, whatever language the cards fall back to).
const SPACE_BEFORE_PERCENT = new Set(["cs", "de", "fi", "fr", "sk", "sv"]);
// A no-break space: "59 %" never splits across lines.
const percentSpace = (hass: Hass): string => (SPACE_BEFORE_PERCENT.has(hass.locale.language) ? " " : "");

export function formatPercent(hass: Hass, value: number | undefined): { text: string; direction: Direction } {
  if (value === undefined || !Number.isFinite(value)) return { text: "—", direction: "none" };
  const number = new Intl.NumberFormat(numberLocale(hass), {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    signDisplay: "exceptZero",
    useGrouping: hass.locale.number_format !== "none",
  }).format(value);
  const space = percentSpace(hass);
  // A change that rounds to 0.00 is no change: no arrow, no colour.
  const hundredths = Math.round(Math.abs(value) * 100);
  const direction: Direction = hundredths === 0 ? "flat" : value > 0 ? "up" : "down";
  return { text: `${number}${space}%`, direction };
}

/** A share or a rate without a sign: "40%", "2.9%", "59 %" in German; with
 * `fixed` always `digits` decimals ("99.76%", "100.00%"). */
export function formatShare(hass: Hass, value: number, digits: number, fixed = false): string {
  const space = percentSpace(hass);
  return `${formatNumber(hass, value, digits, fixed ? digits : 0)}${space}%`;
}

/** The class that colours a change: gains in the theme's success colour,
 * losses in its error colour, nothing else. */
export function trendClass(direction: Direction): "up" | "down" | "" {
  return direction === "up" || direction === "down" ? direction : "";
}

export function arrow(direction: Direction): "▲" | "▼" | "" {
  return direction === "up" ? "▲" : direction === "down" ? "▼" : "";
}

// Dates as Home Assistant writes them: in the viewer's language where the
// cards speak it (else English, like the texts), in the profile's time zone
// and with its 12 or 24 hours.
function dateLanguage(hass: Hass): string {
  return speaksLanguageOf(hass) ? hass.locale.language : "en";
}

function timeZone(hass: Hass): string | undefined {
  return hass.locale.time_zone === "server" ? hass.config?.time_zone : undefined;
}

function amPm(hass: Hass): boolean {
  const format = hass.locale.time_format;
  if (format === "12" || format === "24") return format === "12";
  const test = new Date("January 1, 2023 22:00:00").toLocaleString(format === "system" ? undefined : hass.locale.language);
  return test.includes("10");
}

/** "5 Oct", and "17 Oct 2025" for a day outside the current year. */
export function formatDay(hass: Hass, time: number): string {
  const zone = timeZone(hass);
  const yearOf = (moment: number): string => new Intl.DateTimeFormat("en", { year: "numeric", timeZone: zone }).format(moment);
  const year = yearOf(time) === yearOf(Date.now()) ? {} : { year: "numeric" as const };
  return new Intl.DateTimeFormat(dateLanguage(hass), { day: "numeric", month: "short", ...year, timeZone: zone }).format(time);
}

/** A calendar date given as "2026-10-09", the same day for every viewer:
 * "9 October", "9. Oktober" (the month in full, for the end of a sentence,
 * where an abbreviated month's dot would double the full stop). */
export function formatLongDate(hass: Hass, date: string): string | undefined {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  if (!match) return undefined;
  const day = Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return new Intl.DateTimeFormat(dateLanguage(hass), { day: "numeric", month: "long", timeZone: "UTC" }).format(day);
}

export function formatDayTime(hass: Hass, time: number): string {
  const twelve = amPm(hass);
  return new Intl.DateTimeFormat(dateLanguage(hass), {
    day: "numeric",
    month: "short",
    hour: twelve ? "numeric" : "2-digit",
    minute: "2-digit",
    hourCycle: twelve ? "h12" : "h23",
    timeZone: timeZone(hass),
  }).format(time);
}
