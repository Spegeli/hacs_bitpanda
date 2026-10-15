import { describe, expect, it } from "vitest";

import {
  arrow,
  formatDay,
  formatDayTime,
  formatLike,
  formatLongDate,
  formatMoney,
  formatPrice,
  formatNumber,
  formatPercent,
  formatShare,
  formatSignedLike,
  formatState,
  formatUnits,
  numericState,
  trendClass,
} from "../src/format";
import type { Category } from "../src/types";
import { makeHass, portfolioDevice } from "./fixtures";

describe("formatUnits", () => {
  it("formats units with at most 8 decimals, trailing zeros removed", () => {
    expect(formatUnits(makeHass(), 0.065300001234, "crypto", "BTC")).toBe("0.0653 BTC");
    expect(formatUnits(makeHass(), 0.00000812, "crypto", "PEPE")).toBe("0.00000812 PEPE");
    expect(formatUnits(makeHass(), 0.5, "crypto", "ETH")).toBe("0.5 ETH");
    expect(formatUnits(makeHass(), 12000, "crypto", "VSN")).toBe("12,000 VSN");
  });

  it("formats units in the user's number format", () => {
    expect(formatUnits(makeHass({ numberFormat: "decimal_comma" }), 21.4, "crypto", "BTC")).toBe("21,4 BTC");
    expect(formatUnits(makeHass({ language: "de" }), 1234.5, "crypto", "BTC")).toBe("1.234,5 BTC");
    expect(formatUnits(makeHass({ language: "de", numberFormat: "comma_decimal" }), 1234.5, "crypto", "BTC")).toBe("1,234.5 BTC");
    expect(formatUnits(makeHass({ numberFormat: "none" }), 1234.5, "crypto", "BTC")).toBe("1234.5 BTC");
  });

  it("counts shares of stocks, ETFs and ETCs", () => {
    expect(formatUnits(makeHass(), 21.4, "etf", "EUNL")).toBe("21.4 shares");
    expect(formatUnits(makeHass(), 1, "stock", "AAPL")).toBe("1 share");
    expect(formatUnits(makeHass({ language: "de" }), 21.4, "etc", "PPFB")).toBe("21,4 Stück");
  });

  it("counts a fraction of a share just above one by the decimals it shows", () => {
    expect(formatUnits(makeHass(), 1.0004, "stock", "AAPL")).toBe("1.0004 shares");
    expect(formatUnits(makeHass(), 1.00000001, "etf", "EUNL")).toBe("1.00000001 shares");
    // French counts everything below 2 in the singular, fractions too.
    expect(formatUnits(makeHass({ language: "fr" }), 1.0004, "stock", "AAPL")).toBe("1,0004 titre");
    // Polish: fractions take the form "sztuki", whole numbers their own.
    expect(formatUnits(makeHass({ language: "pl" }), 1.5, "stock", "AAPL")).toBe("1,5 sztuki");
    expect(formatUnits(makeHass({ language: "pl" }), 5, "stock", "AAPL")).toBe("5 sztuk");
  });

  it("counts metals in grams", () => {
    expect(formatUnits(makeHass(), 0.56, "metal", "XAU")).toBe("0.56 g");
  });

  it("keeps the symbol for crypto, indices and unknown categories", () => {
    expect(formatUnits(makeHass(), 3, "index", "BCI5")).toBe("3 BCI5");
    expect(formatUnits(makeHass(), 3, undefined, "XYZ")).toBe("3 XYZ");
  });
});

describe("formatUnits, short for a wallet row", () => {
  const short = (units: number, category: Category, symbol: string, hass = makeHass()) => formatUnits(hass, units, category, symbol, true);

  it("shows at most 4 decimals, rounded down as the Bitpanda app shows them", () => {
    expect(short(21500.09377247, "crypto", "VSN")).toBe("21,500.0937 VSN");
    expect(short(3.42289, "crypto", "CT")).toBe("3.4228 CT");
    expect(short(0.01699275, "metal", "XAU")).toBe("0.0169 g");
    expect(short(39.65402, "crypto", "STONKBROKER")).toBe("39.654 STONKBROKER");
    expect(short(1.0003, "crypto", "BTC")).toBe("1.0003 BTC");
    expect(short(2, "crypto", "BTC")).toBe("2 BTC");
    expect(short(0, "crypto", "BTC")).toBe("0 BTC");
    expect(short(21500.09377247, "crypto", "VSN", makeHass({ language: "de" }))).toBe("21.500,0937 VSN");
    expect(short(1234.56789, "crypto", "VSN", makeHass({ numberFormat: "none" }))).toBe("1234.5678 VSN");
  });

  it("shows a holding below 0.0001 by its first two digits, rounded down, never as 0", () => {
    expect(short(0.00004123, "crypto", "BTC")).toBe("0.000041 BTC");
    expect(short(0.00000812, "crypto", "PEPE")).toBe("0.0000081 PEPE");
    expect(short(0.000099999, "crypto", "BTC")).toBe("0.000099 BTC");
    expect(short(0.0001, "crypto", "BTC")).toBe("0.0001 BTC");
  });

  it("counts the shares it shows", () => {
    expect(short(1.00004, "stock", "AAPL")).toBe("1 share");
    expect(short(1.00009, "stock", "AAPL")).toBe("1 share");
    expect(short(1.0004, "stock", "AAPL")).toBe("1.0004 shares");
    expect(short(21.40009, "etf", "EUNL")).toBe("21.4 shares");
  });
});

describe("formatSignedLike", () => {
  // Home Assistant writes a float state with up to 15 significant digits:
  // trailing zeros dropped, an exponent below 0.0001.
  const price = (state: string, precision?: number) => {
    const hass = makeHass().withState("sensor.p", state, { unit_of_measurement: "EUR" });
    if (precision !== undefined) hass.entities["sensor.p"] = { entity_id: "sensor.p", platform: "bitpanda", display_precision: precision };
    return hass;
  };

  it("rounds a change to the decimals Home Assistant shows for the sensor, not to the state's", () => {
    expect(formatSignedLike(price("3.2e-07", 8), "sensor.p", 1.6e-8)).toBe("+0.00000002 EUR");
    expect(formatSignedLike(price("90.9", 2), "sensor.p", 1.25)).toBe("+1.25 EUR");
    expect(formatSignedLike(price("90.9", 2), "sensor.p", -1.25)).toBe("-1.25 EUR");
  });

  it("without a display precision takes the integration's rule by the price's size", () => {
    expect(formatSignedLike(price("9e-05"), "sensor.p", 4.5e-6)).toBe("+0.00000450 EUR");
    expect(formatSignedLike(price("90.9"), "sensor.p", 1.25)).toBe("+1.25 EUR");
    expect(formatSignedLike(price("3.12"), "sensor.p", 0.0456789)).toBe("+0.0457 EUR");
    expect(formatSignedLike(price("0"), "sensor.p", 0.5)).toBe("+0.50 EUR");
  });

  it("shows a change that rounds to nothing without a sign, and nothing for a missing state or change", () => {
    expect(formatSignedLike(price("90.9", 2), "sensor.p", -0.004)).toBe("0.00 EUR");
    expect(formatSignedLike(price("90.9", 2), "sensor.p", undefined)).toBeUndefined();
    expect(formatSignedLike(price("unavailable", 2), "sensor.p", 1)).toBeUndefined();
    expect(formatSignedLike(price("90.9", 2), undefined, 1)).toBeUndefined();
  });
});

describe("formatNumber", () => {
  it("follows the system's format when asked", () => {
    expect(formatNumber(makeHass({ numberFormat: "system" }), 1.5, 2)).toBe(new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(1.5));
  });

  it("writes the Swiss format for quote_decimal", () => {
    expect(formatNumber(makeHass({ language: "de", numberFormat: "quote_decimal" }), 1234567.5, 2)).toBe(
      new Intl.NumberFormat("de-CH", { maximumFractionDigits: 2 }).format(1234567.5),
    );
  });

  it("uses a space before the comma in space_comma", () => {
    expect(formatNumber(makeHass({ numberFormat: "space_comma" }), 1234.5, 2).replace(/\s/g, " ")).toBe("1 234,5");
  });
});

describe("states", () => {
  const hass = makeHass({ devices: [portfolioDevice({ total: "12760.20", cash: "unavailable", cashPlus: "unknown" })] });

  it("formatState uses Home Assistant's own formatting", () => {
    expect(formatState(hass, "sensor.bitpanda_portfolio_total_value")).toBe("12760.20 EUR");
  });

  it("formatState is undefined for unavailable, unknown and missing", () => {
    expect(formatState(hass, "sensor.bitpanda_portfolio_cash")).toBeUndefined();
    expect(formatState(hass, "sensor.bitpanda_portfolio_cash_plus")).toBeUndefined();
    expect(formatState(hass, "sensor.nothing")).toBeUndefined();
    expect(formatState(hass, undefined)).toBeUndefined();
  });

  it("numericState reads numbers only", () => {
    expect(numericState(hass, "sensor.bitpanda_portfolio_total_value")).toBe(12760.2);
    expect(numericState(hass, "sensor.bitpanda_portfolio_cash")).toBeUndefined();
    expect(numericState(hass, undefined)).toBeUndefined();
    expect(numericState(hass.withState("sensor.bitpanda_portfolio_cash", ""), "sensor.bitpanda_portfolio_cash")).toBeUndefined();
    expect(numericState(hass.withState("sensor.bitpanda_portfolio_cash", "abc"), "sensor.bitpanda_portfolio_cash")).toBeUndefined();
  });
});

describe("computed amounts", () => {
  const hass = makeHass({ devices: [portfolioDevice({ total: "12760.20" })] });

  it("formatLike formats a sum as Home Assistant formats the sensor it belongs to", () => {
    expect(formatLike(hass, "sensor.bitpanda_portfolio_total_value", 7570.35)).toBe("7570.35 EUR");
    expect(formatLike(hass, "sensor.nothing", 1)).toBeUndefined();
    expect(formatLike(hass, undefined, 1)).toBeUndefined();
    expect(formatLike(hass, "sensor.bitpanda_portfolio_total_value", undefined)).toBeUndefined();
  });

  it("formatPrice writes a price with as many decimals as its size needs", () => {
    expect(formatPrice(makeHass(), 2377, "EUR")).toBe(new Intl.NumberFormat("en", { style: "currency", currency: "EUR", maximumFractionDigits: 2, minimumFractionDigits: 2 }).format(2377));
    expect(formatPrice(makeHass(), 1.2345, "EUR")).toContain("1.2345");
    expect(formatPrice(makeHass(), 0.00000812, "EUR")).toContain("0.00000812");
    expect(formatPrice(makeHass(), 5, "not a currency")).toBe("5 not a currency");
  });

  it("formatMoney writes an amount in cents, as the sensors do", () => {
    expect(formatMoney(makeHass(), 1.2345, "EUR")).toBe("€1.23");
    expect(formatMoney(makeHass(), -37.44, "EUR", true)).toBe(new Intl.NumberFormat("en", { style: "currency", currency: "EUR", signDisplay: "exceptZero", maximumFractionDigits: 2, minimumFractionDigits: 2 }).format(-37.44));
    expect(formatMoney(makeHass(), 5, "not a currency")).toBe("5 not a currency");
  });
});

describe("formatPercent", () => {
  it("signs and arrows", () => {
    expect(formatPercent(makeHass(), 2.314)).toEqual({ text: "+2.31%", direction: "up" });
    expect(formatPercent(makeHass(), -0.42)).toEqual({ text: "-0.42%", direction: "down" });
    expect(formatPercent(makeHass(), 0)).toEqual({ text: "0.00%", direction: "flat" });
  });

  it("puts a space before % where the language does", () => {
    expect(formatPercent(makeHass({ language: "de" }), 2.31).text).toBe("+2,31 %");
  });

  it("spaces % by the viewer's language even where the cards fall back to English", () => {
    expect(formatPercent(makeHass({ language: "sv" }), 2.31).text).toBe("+2,31 %");
    expect(formatShare(makeHass({ language: "cs" }), 59.3, 0)).toBe("59 %");
    expect(formatShare(makeHass({ language: "nl" }), 59.3, 0)).toBe("59%");
  });

  it("a change that rounds to 0.00 is flat: no sign, no arrow, no colour", () => {
    expect(formatPercent(makeHass(), -0.004)).toEqual({ text: "0.00%", direction: "flat" });
    expect(formatPercent(makeHass(), 0.004)).toEqual({ text: "0.00%", direction: "flat" });
    expect(formatPercent(makeHass(), -0.005).direction).toBe("down");
  });

  it("of undefined is a dash", () => {
    expect(formatPercent(makeHass(), undefined)).toEqual({ text: "—", direction: "none" });
  });
});

describe("formatShare", () => {
  it("writes a share without a sign, spaced as the language does", () => {
    expect(formatShare(makeHass(), 40.04, 0)).toBe("40%");
    expect(formatShare(makeHass(), 2.9, 1)).toBe("2.9%");
    // The space before % never breaks.
    expect(formatShare(makeHass({ language: "de" }), 59.3, 0)).toBe("59 %");
  });
});

describe("trend colours", () => {
  it("colours gains and losses, nothing else", () => {
    expect(trendClass("up")).toBe("up");
    expect(trendClass("down")).toBe("down");
    expect(trendClass("flat")).toBe("");
    expect(trendClass("none")).toBe("");
  });

  it("arrows point the way", () => {
    expect(arrow("up")).toBe("▲");
    expect(arrow("down")).toBe("▼");
    expect(arrow("flat")).toBe("");
    expect(arrow("none")).toBe("");
  });
});

describe("dates", () => {
  const moment = Date.UTC(2026, 9, 6, 16, 12);

  it("formatDay gives day and month in the viewer's language", () => {
    expect(formatDay(makeHass(), moment)).toBe(new Intl.DateTimeFormat("en", { day: "numeric", month: "short" }).format(moment));
    expect(formatDay(makeHass({ language: "de" }), moment)).toBe(new Intl.DateTimeFormat("de", { day: "numeric", month: "short" }).format(moment));
  });

  it("formatDay adds the year to a day outside the current year", () => {
    const year = new Date().getUTCFullYear();
    const earlier = Date.UTC(year - 1, 9, 17, 12);
    const thisYear = Date.UTC(year, 0, 15, 12);
    expect(formatDay(makeHass({ language: "de" }), earlier)).toBe(
      new Intl.DateTimeFormat("de", { day: "numeric", month: "short", year: "numeric" }).format(earlier),
    );
    expect(formatDay(makeHass({ language: "de" }), thisYear)).toBe(new Intl.DateTimeFormat("de", { day: "numeric", month: "short" }).format(thisYear));
  });

  it("formatLongDate writes a calendar date with the month in full, the same day everywhere", () => {
    expect(formatLongDate(makeHass({ language: "de" }), "2026-10-09")).toBe("9. Oktober");
    expect(formatLongDate(makeHass({ timeZone: "server", serverTimeZone: "America/New_York" }), "2026-10-09")).toBe("October 9");
    expect(formatLongDate(makeHass(), "9 October")).toBeUndefined();
  });

  it("dates follow the profile's time zone setting", () => {
    const server = makeHass({ timeZone: "server", serverTimeZone: "Asia/Tokyo", timeFormat: "24" });
    expect(formatDay(server, Date.UTC(2026, 9, 6, 20, 0))).toBe("Oct 7");
    expect(formatDayTime(server, moment)).toBe("Oct 7, 01:12");
  });

  it("times follow the profile's 12 or 24 hours", () => {
    expect(formatDayTime(makeHass({ timeFormat: "24", timeZone: "server", serverTimeZone: "UTC" }), moment)).toBe("Oct 6, 16:12");
    expect(formatDayTime(makeHass({ language: "de", timeFormat: "12", timeZone: "server", serverTimeZone: "UTC" }), moment)).toBe(
      new Intl.DateTimeFormat("de", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", hourCycle: "h12", timeZone: "UTC" }).format(moment),
    );
    expect(formatDayTime(makeHass({ language: "de", timeFormat: "12", timeZone: "server", serverTimeZone: "UTC" }), moment)).toMatch(/4:12/);
  });

  it("dates are English where the cards do not speak the viewer's language, like the texts", () => {
    expect(formatDay(makeHass({ language: "ja" }), moment)).toBe(new Intl.DateTimeFormat("en", { day: "numeric", month: "short" }).format(moment));
    expect(formatDay(makeHass({ language: "de-AT" }), moment)).toBe(new Intl.DateTimeFormat("de-AT", { day: "numeric", month: "short" }).format(moment));
  });

  it("formatDayTime adds the time, as the language writes it", () => {
    expect(formatDayTime(makeHass(), moment)).toBe(
      new Intl.DateTimeFormat("en", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", hourCycle: "h12" }).format(moment),
    );
    expect(formatDayTime(makeHass({ language: "de" }), moment)).toBe(
      new Intl.DateTimeFormat("de", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(moment),
    );
  });
});
