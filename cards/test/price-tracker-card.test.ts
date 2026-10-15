import { afterEach, describe, expect, it, vi } from "vitest";

import { PriceTrackerCard, amountsFit, priceColumns, priceRowLayout } from "../src/price-tracker-card";
import { makeHass, openEditor, portfolioDevice, priceDevice, type FakeHass } from "./fixtures";

const HOUR = 3_600_000;
const DAY = 24 * HOUR;

const ASSETS = [
  priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { EUR: { state: "90200.77", change24h: 1.82, price24hAgo: 88588.4 }, USD: { state: "105312.09", change24h: 1.85, rateDate: "2026-10-10" } } }),
  priceDevice({ symbol: "ETH", name: "Ethereum", category: "crypto", prices: { EUR: { state: "2308.93", change24h: -0.64 }, USD: { state: "2695.68", change24h: -0.6, rateDate: "2026-10-10" } } }),
  priceDevice({ symbol: "EUNL", name: "iShares Core MSCI World UCITS ETF", category: "etf", isin: "IE00B4L5Y983", prices: { EUR: { state: "95.57", change24h: 0.21 }, USD: { state: "111.58", change24h: 0.25, rateDate: "2026-10-10" } } }),
  priceDevice({ symbol: "SUI", name: "Sui", category: "crypto", prices: { EUR: { state: "3.12" }, USD: { state: "3.64", rateDate: "2026-10-10" } } }),
];

/** Statistics: every asset a week back at a known price; Sui tracked for 3
 * days, so its statistics start then (Home Assistant returns rows from the
 * window's start on). */
function weekAgo(entityId: string): number {
  return entityId.includes("_btc_") ? 86600 : entityId.includes("_eth_") ? 2400 : entityId.includes("_eunl_") ? 94.68 : 3;
}

function trackerHass(options: { devices?: ReturnType<typeof priceDevice>[]; language?: string } = {}): FakeHass {
  return makeHass({
    devices: options.devices ?? ASSETS,
    ...(options.language ? { language: options.language } : {}),
    callWS: async (message) => {
      const start = Date.parse(String(message["start_time"]));
      const now = Date.now();
      const rows: Record<string, unknown[]> = {};
      for (const entityId of message["statistic_ids"] as string[]) {
        const first = entityId.includes("_sui_") ? Math.max(start, now - 3 * DAY) : start;
        rows[entityId] = [{ start: first, state: weekAgo(entityId) }, { start: now - HOUR, state: weekAgo(entityId) * 1.01 }];
      }
      return rows;
    },
  });
}

async function mount(config: Record<string, unknown> = {}, hass: FakeHass = trackerHass()): Promise<PriceTrackerCard> {
  const card = document.createElement("bitpanda-price-tracker-card") as PriceTrackerCard;
  card.setConfig({ type: "custom:bitpanda-price-tracker-card", ...config });
  card.hass = hass;
  document.body.append(card);
  await card.updateComplete;
  return card;
}

const all = (card: PriceTrackerCard, selector: string) => [...(card.shadowRoot as ShadowRoot).querySelectorAll<HTMLElement>(selector)];
const one = (card: PriceTrackerCard, selector: string) => (card.shadowRoot as ShadowRoot).querySelector<HTMLElement>(selector);
const textOf = (element: Element | null | undefined): string => (element?.textContent ?? "").replace(/\s+/g, " ").trim();
const rows = (card: PriceTrackerCard) =>
  all(card, ".price-row").map((row) => ({
    name: textOf(row.querySelector(".n")),
    sub: textOf(row.querySelector(".s")),
    price: textOf(row.querySelector(".p")),
    change: textOf(row.querySelector(".c .pct")),
  }));
/** Per row: the change's amount and the "Change since" line. */
const extras = (card: PriceTrackerCard) =>
  all(card, ".price-row").map((row) => ({ amount: textOf(row.querySelector(".c .a")), since: textOf(row.querySelector(".since")) }));

async function linesDrawn(card: PriceTrackerCard): Promise<void> {
  await vi.waitFor(() => expect(all(card, "svg.mini .line").some((line) => line.getAttribute("d"))).toBe(true));
  await card.updateComplete;
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("the Bitpanda Price Tracker card", () => {
  it("lists assets by name with their symbol, or a security's ISIN, line, price and change", async () => {
    const card = await mount();
    await linesDrawn(card);
    expect(textOf(one(card, ".title"))).toBe("Bitpanda Price Tracker");
    expect(one(card, ".eye")).toBeNull();
    expect(rows(card)).toEqual([
      { name: "Bitcoin", sub: "BTC", price: "90200.77 EUR", change: "▲ +4.16%" },
      { name: "Ethereum", sub: "ETH", price: "2308.93 EUR", change: "▼ -3.79%" },
      { name: "iShares Core MSCI World UCITS ETF", sub: "IE00B4L5Y983", price: "95.57 EUR", change: "▲ +0.94%" },
      { name: "Sui", sub: "SUI", price: "3.12 EUR", change: "▲ +4.00%" },
    ]);
    expect(all(card, ".price-row svg.mini")).toHaveLength(4);
  });

  it("takes 1D from the statistics, whatever the sensor's own 24-hour change says", async () => {
    const coin = priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { EUR: { state: "110", change24h: 10, price24hAgo: 100 } } });
    const hass = makeHass({
      devices: [coin],
      callWS: async (message) => ({
        "sensor.bitpanda_btc_price_tracker_eur": [{ start: Date.parse(String(message["start_time"])), state: 105 }, { start: Date.now() - HOUR, state: 108 }],
      }),
    });
    const card = await mount({}, hass);
    await linesDrawn(card);
    expect(rows(card)[0]?.change).toBe("▲ +4.76%");
    expect(extras(card)[0]).toEqual({ amount: "+5.00 EUR", since: "" });
  });

  it("asks the statistics of every row to sort 1D by change", async () => {
    const hass = trackerHass();
    await mount({ sort: "change_desc", limit: 1 }, hass);
    await vi.waitFor(() => expect(hass.messages.length).toBeGreaterThan(0));
    expect(hass.messages[0]?.["statistic_ids"]).toHaveLength(4);
  });

  it("1D of a fresh asset counts from the statistics' start", async () => {
    const fresh = priceDevice({ symbol: "NEW", name: "Newcoin", category: "crypto", prices: { EUR: { state: "110.50" } } });
    const firstSeen = Date.now() - 5 * HOUR;
    const hass = makeHass({
      devices: [fresh],
      callWS: async () => ({ "sensor.bitpanda_new_price_tracker_eur": [{ start: firstSeen, state: 100 }, { start: Date.now() - HOUR, state: 108 }] }),
    });
    const card = await mount({}, hass);
    await linesDrawn(card);
    expect(rows(card)[0]?.change).toBe("▲ +10.50%");
    const day = new Intl.DateTimeFormat("en", { day: "numeric", month: "short" }).format(firstSeen);
    expect(extras(card)[0]).toEqual({ amount: "+10.50 EUR", since: `Change since ${day}` });
  });

  it("keeps the date of 'change since' in one piece, in every language", async () => {
    const fresh = priceDevice({ symbol: "NEW", name: "Newcoin", category: "crypto", prices: { EUR: { state: "110.50" } } });
    const firstSeen = Date.now() - 5 * HOUR;
    for (const language of ["en", "de"]) {
      const hass = makeHass({
        devices: [fresh],
        language,
        callWS: async () => ({ "sensor.bitpanda_new_price_tracker_eur": [{ start: firstSeen, state: 100 }, { start: Date.now() - HOUR, state: 108 }] }),
      });
      const card = await mount({}, hass);
      await linesDrawn(card);
      const day = new Intl.DateTimeFormat(language, { day: "numeric", month: "short" }).format(firstSeen);
      const date = one(card, ".since .nw");
      expect(textOf(date), language).toBe(day);
      expect(textOf(one(card, ".since")), language).toBe(language === "de" ? `Änderung seit ${day}` : `Change since ${day}`);
    }
    const css = (PriceTrackerCard.styles as unknown as { cssText: string }[]).map((sheet) => sheet.cssText).join("\n");
    expect(css.match(/\.nw\s*\{([^}]*)\}/)?.[1]).toMatch(/white-space:\s*nowrap/);
  });

  it("never breaks a name inside a word: a word too long for its line ends in an ellipsis", () => {
    const css = (PriceTrackerCard.styles as unknown as { cssText: string }[]).map((sheet) => sheet.cssText).join("\n");
    const rule = css.match(/(?:^|\n)\s*\.n\s*\{([^}]*)\}/)?.[1] ?? "";
    expect(rule).not.toMatch(/overflow-wrap:\s*anywhere/);
    expect(rule).toMatch(/overflow-wrap:\s*normal/);
    expect(rule).toMatch(/text-overflow:\s*ellipsis/);
  });

  it("a change that rounds to 0.00 % shows neither arrow nor colour, nor does its amount", async () => {
    const still = priceDevice({ symbol: "EUNL", name: "iShares Core MSCI World UCITS ETF", category: "etf", prices: { EUR: { state: "132.21" } } });
    const hass = makeHass({
      devices: [still],
      callWS: async (message) => ({
        "sensor.bitpanda_eunl_price_tracker_eur": [{ start: Date.parse(String(message["start_time"])), state: 132.215 }, { start: Date.now() - HOUR, state: 132.21 }],
      }),
    });
    const card = await mount({}, hass);
    await linesDrawn(card);
    expect(rows(card)[0]?.change).toBe("0.00%");
    expect(extras(card)[0]?.amount).toBe("0.00 EUR");
    expect(one(card, ".price-row .c")?.className.trim()).toBe("c");
  });

  it("longer changes come from statistics", async () => {
    const card = await mount({ timeframe: "week" });
    await linesDrawn(card);
    // 90200.77 against 86600 a week ago
    expect(rows(card)[0]?.change).toBe("▲ +4.16%");
    expect(rows(card)[1]?.change).toBe("▼ -3.79%");
    expect(extras(card).slice(0, 2).map((extra) => extra.amount)).toEqual(["+3600.77 EUR", "-91.07 EUR"]);
  });

  it("an asset with statistics shorter than the window shows its change since they start, on a line of its own", async () => {
    const card = await mount({ timeframe: "month" });
    await linesDrawn(card);
    const index = rows(card).findIndex((row) => row.name === "Sui");
    expect(rows(card)[index]).toMatchObject({ sub: "SUI", change: "▲ +4.00%" });
    const since = new Intl.DateTimeFormat("en", { day: "numeric", month: "short" }).format(Date.now() - 3 * DAY);
    // 4 decimals, as Home Assistant shows a price of this size.
    expect(extras(card)[index]).toEqual({ amount: "+0.1200 EUR", since: `Change since ${since}` });
    expect(extras(card)[0]?.since).toBe("");
  });

  it("draws a month's line every 6 hours, while its change counts from the first hourly point", async () => {
    const hourly = makeHass({
      devices: ASSETS,
      callWS: async (message) => {
        const now = Date.now();
        const answer: Record<string, unknown[]> = {};
        for (const entityId of message["statistic_ids"] as string[]) {
          // 720 hours; the first at 50, the rest between 100 and 106.
          answer[entityId] = Array.from({ length: 720 }, (_, index) => ({ start: now - (720 - index) * HOUR, state: index === 0 ? 50 : 100 + (index % 7) }));
        }
        return answer;
      },
    });
    const card = await mount({ timeframe: "month" }, hourly);
    await linesDrawn(card);
    const drawn = (one(card, "svg.mini .line")?.getAttribute("d") ?? "").match(/[ML]/g) ?? [];
    // The first point, the first of each later 6-hour slot (the slots count
    // from a fixed start, so 119 or 120 of them by the time of day) and the
    // last point: 121 or 122.
    expect(drawn.length).toBeGreaterThanOrEqual(121);
    expect(drawn.length).toBeLessThanOrEqual(122);
    // Bitcoin at 90200.77 against the first point's 50.
    expect(rows(card)[0]?.change).toBe("▲ +180,301.54%");
  });

  it("its line then spans the width, from the statistics' start like its change", async () => {
    const card = await mount({ timeframe: "year" });
    await linesDrawn(card);
    const index = rows(card).findIndex((row) => row.name === "Sui");
    const line = all(card, ".price-row")[index]?.querySelector("svg.mini .line");
    expect(line?.getAttribute("d")).toMatch(/^M0,/);
  });

  it("the currency switch offers exactly the configured currencies", async () => {
    const card = await mount();
    const switches = all(card, "[role=radiogroup]");
    expect(switches).toHaveLength(2);
    expect([...switches[1]!.querySelectorAll("[role=radio]")].map((radio) => radio.textContent?.trim())).toEqual(["EUR", "USD"]);
    (switches[1]!.querySelectorAll<HTMLElement>("[role=radio]")[1])?.click();
    await card.updateComplete;
    expect(rows(card)[0]?.price).toBe("105312.09 USD");
    // 105312.09 against the USD sensor's statistics, at 86600 a day back here.
    await vi.waitFor(() => expect(rows(card)[0]?.change).toBe("▲ +21.61%"));
  });

  it("hides the currency switch with EUR alone", async () => {
    const only = [priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { EUR: { state: "1" } } })];
    const card = await mount({}, trackerHass({ devices: only }));
    expect(all(card, "[role=radiogroup]")).toHaveLength(1);
    expect(one(card, ".foot")).toBeNull();
  });

  it("a removed start currency falls back to EUR without touching the config", async () => {
    const eurOnly = ASSETS.map((device) => ({ ...device, sensors: device.sensors.filter((sensor) => !sensor.entityId.endsWith("_usd")) }));
    const card = await mount({ currency: "USD" }, trackerHass({ devices: eurOnly }));
    expect(rows(card)[0]?.price).toBe("90200.77 EUR");
    expect((card as unknown as { config: { currency?: string } }).config.currency).toBe("USD");
    card.hass = trackerHass();
    await card.updateComplete;
    expect(rows(card)[0]?.price).toBe("105312.09 USD");
  });

  it("falls back to an offered currency when no EUR price is enabled", async () => {
    const devices = [
      priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { USD: { state: "105312.09", change24h: 1.85, rateDate: "2026-10-10" } } }),
    ];
    const card = await mount({}, trackerHass({ devices }));
    expect(rows(card)[0]?.price).toBe("105312.09 USD");
  });

  it("the footer names the ECB date outside EUR, and that the change in that currency includes the rate's", async () => {
    // German first: the last card mounted sets the editors' language.
    const german = await mount({ currency: "USD" }, trackerHass({ language: "de" }));
    expect(textOf(one(german, ".foot"))).toBe(
      "Preise in USD: Bitpandas Euro-Preise, umgerechnet zum EZB-Referenzkurs vom 10. Oktober. Die Prozente und Beträge in USD enthalten deshalb auch die Bewegung des Wechselkurses.",
    );
    const card = await mount({ currency: "USD" });
    expect(textOf(one(card, ".foot"))).toBe(
      "Prices in USD: Bitpanda's EUR prices converted at the ECB reference rate of October 10. The percentages and amounts in USD therefore also include the exchange rate's move.",
    );
  });

  it("sorts by change, dashes last, and by the picked order", async () => {
    const desc = await mount({ sort: "change_desc" });
    await linesDrawn(desc);
    expect(rows(desc).map((row) => row.name)).toEqual(["Bitcoin", "Sui", "iShares Core MSCI World UCITS ETF", "Ethereum"]);
    const asc = await mount({ sort: "change_asc" });
    await linesDrawn(asc);
    expect(rows(asc).map((row) => row.name)).toEqual(["Ethereum", "iShares Core MSCI World UCITS ETF", "Sui", "Bitcoin"]);
    const picked = await mount({ sort: "selection", asset_selection: "only", assets: ["dev-price-sui", "dev-price-btc"] });
    expect(rows(picked).map((row) => row.name)).toEqual(["Sui", "Bitcoin"]);
    const unpicked = await mount({ sort: "selection" });
    expect(rows(unpicked)[0]?.name).toBe("Bitcoin");
  });

  it("shows the picked asset groups only, and in them the assets picked", async () => {
    const etfs = await mount({ group_selection: "only", groups: ["etf"] });
    expect(rows(etfs).map((row) => row.name)).toEqual(["iShares Core MSCI World UCITS ETF"]);
    const crypto = await mount({ group_selection: "all_except", groups: ["etf"], asset_selection: "all_except", assets: ["dev-price-eth"] });
    expect(rows(crypto).map((row) => row.name)).toEqual(["Bitcoin", "Sui"]);
  });

  it("says so when the card's selection leaves no asset, as a list and as tiles", async () => {
    const list = await mount({ group_selection: "only", groups: ["metal"] });
    expect(rows(list)).toEqual([]);
    expect(textOf(one(list, ".empty"))).toBe("No assets in this card's selection.");
    const tiles = await mount({ layout: "tiles", asset_selection: "only", assets: [] });
    expect(all(tiles, ".tile")).toEqual([]);
    expect(textOf(one(tiles, ".empty"))).toBe("No assets in this card's selection.");
  });

  it("finds the chosen assets by their asset IDs, in the order chosen", async () => {
    const card = await mount({ asset_selection: "only", assets: ["id-sui", "id-btc"], sort: "selection" });
    expect(rows(card).map((row) => row.name)).toEqual(["Sui", "Bitcoin"]);
    const except = await mount({ asset_selection: "all_except", assets: ["id-eth"] });
    expect(rows(except).map((row) => row.name)).not.toContain("Ethereum");
  });

  it("keeps a choice by asset ID when the Price Tracker was set up again, a choice by device ID not", async () => {
    // Deleted and set up again, the service creates its devices anew: new
    // device IDs, the same asset IDs.
    const again = ASSETS.map((device) => ({ ...device, id: `${device.id}-new` }));
    const byAsset = await mount({ asset_selection: "only", assets: ["id-btc"] }, trackerHass({ devices: again }));
    expect(rows(byAsset).map((row) => row.name)).toEqual(["Bitcoin"]);
    const byDevice = await mount({ asset_selection: "only", assets: ["dev-price-btc"] }, trackerHass({ devices: again }));
    expect(rows(byDevice)).toEqual([]);
  });

  it("all except leaves the picked out", async () => {
    const card = await mount({ asset_selection: "all_except", assets: ["dev-price-eth"] });
    expect(rows(card).map((row) => row.name)).not.toContain("Ethereum");
  });

  it("tiles show the ISIN instead of the symbol for stocks, ETFs and ETCs", async () => {
    const card = await mount({ layout: "tiles" });
    const tiles = all(card, ".tile").map((tile) => [textOf(tile.querySelector(".n")), textOf(tile.querySelector(".s"))]);
    expect(tiles).toEqual([
      ["Bitcoin", "BTC"],
      ["Ethereum", "ETH"],
      ["iShares Core MSCI World UCITS ETF", "IE00B4L5Y983"],
      ["Sui", "SUI"],
    ]);
    expect(all(card, ".price-row")).toHaveLength(0);
  });

  it("tiles show the amount below the change and the start of a shorter statistic below the line", async () => {
    const card = await mount({ layout: "tiles", timeframe: "month" });
    await linesDrawn(card);
    const sui = all(card, ".tile")[3] as HTMLElement;
    expect(textOf(sui.querySelector(".c .pct"))).toBe("▲ +4.00%");
    expect(textOf(sui.querySelector(".c .a"))).toBe("+0.1200 EUR");
    const since = new Intl.DateTimeFormat("en", { day: "numeric", month: "short" }).format(Date.now() - 3 * DAY);
    expect(textOf(sui.lastElementChild)).toBe(`Change since ${since}`);
    expect(sui.querySelector("svg.mini + .since")).not.toBeNull();
    expect((all(card, ".tile")[0] as HTMLElement).querySelector(".since")).toBeNull();
  });

  it("tiles put the amount beside the percentage when every tile has room, below it otherwise", async () => {
    const room = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(200);
    const rect = vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      const width = this.classList.contains("pct") ? 60 : this.classList.contains("a") ? 70 : 0;
      return { width, height: 0, x: 0, y: 0, top: 0, left: 0, right: width, bottom: 0, toJSON: () => ({}) } as DOMRect;
    });
    try {
      const card = await mount({ layout: "tiles" });
      await linesDrawn(card);
      await vi.waitFor(() => expect(one(card, ".tiles")?.classList.contains("inline")).toBe(true));
      // The chip sets the percentage apart: no middle dot between them.
      expect(one(card, ".tile .c .sep")).toBeNull();
      expect(textOf(one(card, ".tile .c .pct"))).toBe("▲ +4.16%");
      expect(textOf(one(card, ".tile .c .pct + .a"))).toBe("+3600.77 EUR");
      room.mockReturnValue(130);
      card.requestUpdate();
      await card.updateComplete;
      await vi.waitFor(() => expect(one(card, ".tiles")?.classList.contains("inline")).toBe(false));
    } finally {
      room.mockRestore();
      rect.mockRestore();
    }
  });

  it("side by side, the tiles' chip and amount read as one line", () => {
    const css = (PriceTrackerCard.styles as unknown as { cssText: string }[]).map((sheet) => sheet.cssText).join("\n");
    expect(css.match(/\.tiles\.inline \.tile \.c\s*\{([^}]*)\}/)?.[1]).toMatch(/flex-direction:\s*row/);
    expect(css.match(/\.tiles\.inline \.tile \.c\s*\{([^}]*)\}/)?.[1]).toMatch(/column-gap:\s*6px/);
    expect(css).not.toMatch(/\.sep\b/);
  });

  it("the change's percentage stands in a chip, in the list and in tiles, like the Portfolio card's", async () => {
    for (const layout of ["list", "tiles"]) {
      const card = await mount({ layout });
      await linesDrawn(card);
      const chip = one(card, ".c .pct");
      expect(chip?.classList.contains("pchip")).toBe(true);
      // The colour comes from the change around it.
      expect(chip?.closest(".c")?.classList.contains("up")).toBe(true);
    }
    // No change known: a dash without the chip's background.
    const css = (PriceTrackerCard.styles as unknown as { cssText: string }[]).map((sheet) => sheet.cssText).join("\n");
    expect(css.match(/\.gchip,\s*\.wchip,\s*\.pchip\s*\{([^}]*)\}/)?.[1]).toMatch(/background:\s*var\(--bp-chip\)/);
    expect(css.match(/\.wchip\.none,\s*\.pchip\.none\s*\{([^}]*)\}/)?.[1]).toMatch(/background:\s*none/);
    const devices = [...ASSETS, priceDevice({ symbol: "ODD", name: "Oddity", category: "unknown", prices: { EUR: { state: "1" } } })];
    const odd = all(await mount({ currency: "USD" }, trackerHass({ devices })), ".price-row").find((row) => textOf(row.querySelector(".n")) === "Oddity");
    expect(textOf(odd?.querySelector(".c .pct"))).toBe("—");
    expect(odd?.querySelector(".c .pct")?.classList.contains("none")).toBe(true);
  });

  it("amountsFit wants room for every tile with an amount, 6 px apart", () => {
    expect(amountsFit([{ room: 200, pct: 60, amount: 70 }, { room: 200, pct: 62, amount: 90 }])).toBe(true);
    expect(amountsFit([{ room: 136, pct: 60, amount: 70 }, { room: 200, pct: 62, amount: 90 }])).toBe(true);
    expect(amountsFit([{ room: 135, pct: 60, amount: 70 }, { room: 200, pct: 62, amount: 90 }])).toBe(false);
    expect(amountsFit([{ room: 150, pct: 60, amount: 70 }, { room: 150, pct: 40 }])).toBe(true);
    expect(amountsFit([{ room: 150, pct: 40 }])).toBe(false);
    expect(amountsFit([])).toBe(false);
  });

  it("tiles wrap by width", async () => {
    const card = await mount({ layout: "tiles" });
    const css = (PriceTrackerCard.styles as unknown as { cssText: string }[]).map((sheet) => sheet.cssText).join("\n");
    expect(css).toMatch(/\.tiles\s*\{[^}]*grid-template-columns:\s*repeat\(auto-fill,\s*minmax\(/);
    expect(one(card, ".tiles")).not.toBeNull();
  });

  it("a narrow list drops its lines, and the place of a line not drawn yet, so the names keep their room", async () => {
    const css = (PriceTrackerCard.styles as unknown as { cssText: string }[]).map((sheet) => sheet.cssText).join("\n");
    const narrow = css.match(/@container\s*\(max-width:\s*(\d+)px\)\s*\{([\s\S]*?)\n  \}/g) ?? [];
    const rules = narrow.join("\n");
    expect(rules).toMatch(/\.price-row\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)\s*auto\s*auto/);
    expect(rules).toMatch(/\.price-row \.mini\s*\{[^}]*display:\s*none/);
    // Before its statistics arrive a row holds the line's place with an
    // empty one of the same class.
    const card = await mount();
    expect(all(card, ".price-row span.mini")).toHaveLength(4);
  });

  it("a list row keeps its parts in named areas: price beside its change, or above it", () => {
    const css = (PriceTrackerCard.styles as unknown as { cssText: string }[]).map((sheet) => sheet.cssText).join("\n");
    const rule = (selector: string, within = css): string | undefined =>
      within.match(new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\{([^}]*)\\}`))?.[1];
    expect(rule(".price-row")).toMatch(/grid-template-areas:\s*"lead line price change"/);
    expect(rule(".rows.stacked .price-row")).toMatch(/grid-template-areas:\s*"lead line price"\s*"lead line change"/);
    expect(rule(".price-row .lead")).toMatch(/grid-area:\s*lead/);
    expect(rule(".price-row .mini")).toMatch(/grid-area:\s*line/);
    expect(rule(".price-row .p")).toMatch(/grid-area:\s*price/);
    expect(rule(".price-row .c")).toMatch(/grid-area:\s*change/);
    // Price and change only as wide as they are, so that the card can measure
    // them alike in either layout.
    expect(rule(".price-row .p")).toMatch(/justify-self:\s*end/);
    expect(rule(".price-row .c")).toMatch(/justify-self:\s*end/);
    expect(rule(".price-row .c")).toMatch(/flex-direction:\s*column/);
    expect(rule(".price-row .c")).toMatch(/align-items:\s*flex-end/);
    const narrow = (css.match(/@container\s*\(max-width:\s*(\d+)px\)\s*\{([\s\S]*?)\n  \}/g) ?? []).join("\n");
    expect(rule(".price-row", narrow)).toMatch(/grid-template-areas:\s*"lead price change"/);
    expect(rule(".rows.stacked .price-row", narrow)).toMatch(/grid-template-areas:\s*"lead price"\s*"lead change"/);
  });

  it("a list row puts its price above its change, then both below its name, in every row alike", async () => {
    // The card's width and its rows' are one here. The line is measured as
    // nothing: its room comes from the card's width (above 380 px), never
    // from the line itself, which the last layout hides.
    const room = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(393);
    const rect = vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      const list = this.classList;
      const width = list.contains("p") ? 75 : list.contains("pct") ? 60 : list.contains("a") ? 65 : 0;
      return { width, height: 0, x: 0, y: 0, top: 0, left: 0, right: width, bottom: 0, toJSON: () => ({}) } as DOMRect;
    });
    const layout = (card: PriceTrackerCard) => {
      const rows = one(card, ".rows")?.classList;
      return [rows?.contains("stacked"), rows?.contains("below")];
    };
    const resize = async (card: PriceTrackerCard, width: number) => {
      room.mockReturnValue(width);
      card.requestUpdate();
      await card.updateComplete;
    };
    try {
      const card = await mount();
      // 96 line + 8 + 120 name + 8 + 75 price + 8 + 78, the change's least.
      await vi.waitFor(() => expect(layout(card)).toEqual([false, false]));
      await resize(card, 392);
      await vi.waitFor(() => expect(layout(card)).toEqual([true, false]));
      // A narrow card hides the line: its room goes to the name.
      await resize(card, 289);
      await vi.waitFor(() => expect(layout(card)).toEqual([false, false]));
      await resize(card, 288);
      await vi.waitFor(() => expect(layout(card)).toEqual([true, false]));
      // 90 name + 8 + 75, the wider of price and change.
      await resize(card, 173);
      await vi.waitFor(() => expect(layout(card)).toEqual([true, false]));
      await resize(card, 172);
      await vi.waitFor(() => expect(layout(card)).toEqual([false, true]));
      await resize(card, 393);
      await vi.waitFor(() => expect(layout(card)).toEqual([false, false]));
    } finally {
      room.mockRestore();
      rect.mockRestore();
    }
  });

  it("priceRowLayout: beside while every name keeps 120 px, stacked while every name keeps 90 px, else below", () => {
    const row = { room: 289, price: 75, change: 65 };
    expect(priceRowLayout([row])).toBe("beside");
    expect(priceRowLayout([row, { ...row, room: 288 }])).toBe("stacked");
    // A change wider than the column's least counts as it is.
    expect(priceRowLayout([{ ...row, change: 79 }])).toBe("stacked");
    expect(priceRowLayout([{ ...row, room: 173 }])).toBe("stacked");
    expect(priceRowLayout([{ ...row, room: 173 }, { ...row, room: 173, change: 76 }])).toBe("below");
    expect(priceRowLayout([])).toBe("beside");
  });

  it("priceRowLayout: every row gets the widest price and change, so a name keeps its room beside both", () => {
    // Each row alone leaves its name 120 px (289 - 75 - 8 - 78 - 8, and
    // 289 - 40 - 8 - 90 - 8), but the shared columns take 75 and 90.
    const rows = [
      { room: 289, price: 75, change: 60 },
      { room: 289, price: 40, change: 90 },
    ];
    expect(priceRowLayout(rows)).toBe("stacked");
  });

  it("priceColumns: the widest price, the widest change but at least 78 px, and the wider of both, rounded up", () => {
    expect(priceColumns([{ price: 74.2, change: 60 }, { price: 40, change: 65.5 }])).toEqual({ price: 75, change: 78, figures: 75 });
    expect(priceColumns([{ price: 40, change: 90.1 }])).toEqual({ price: 40, change: 91, figures: 91 });
    expect(priceColumns([])).toEqual({ price: 0, change: 78, figures: 0 });
  });

  it("every list row takes the widest price and change as its columns, so the lines stand one under another", async () => {
    const room = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(393);
    // A price as wide as its text: rows of different widths.
    const rect = vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      const list = this.classList;
      const width = list.contains("p") ? (this.textContent ?? "").trim().length * 7 : list.contains("pct") ? 60 : list.contains("a") ? 65 : 0;
      return { width, height: 0, x: 0, y: 0, top: 0, left: 0, right: width, bottom: 0, toJSON: () => ({}) } as DOMRect;
    });
    try {
      const card = await mount();
      const prices = all(card, ".price-row .p").map((price) => (price.textContent ?? "").trim().length * 7);
      expect(new Set(prices).size).toBeGreaterThan(1);
      const widest = Math.max(...prices);
      const rows = one(card, ".rows") as HTMLElement;
      await vi.waitFor(() => expect(rows.style.getPropertyValue("--bp-price")).toBe(`${widest}px`));
      expect(rows.style.getPropertyValue("--bp-change")).toBe("78px");
      expect(rows.style.getPropertyValue("--bp-figures")).toBe(`${Math.max(widest, 65)}px`);
    } finally {
      room.mockRestore();
      rect.mockRestore();
    }
  });

  it("measures the columns in layout pixels, also while a dialog shows the card scaled down", async () => {
    // Home Assistant's card dialog opens with a scale animation: the boxes
    // the browser reports are smaller than the layout, and a column set from
    // them would be too narrow for its widest price.
    const scale = 0.9;
    const room = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(393);
    const layout = vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockImplementation(function (this: HTMLElement) {
      return this.tagName === "BITPANDA-PRICE-TRACKER-CARD" ? 393 : 0;
    });
    const rect = vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      const list = this.classList;
      const own = this.tagName === "BITPANDA-PRICE-TRACKER-CARD" ? 393 : list.contains("p") ? (this.textContent ?? "").trim().length * 7 : list.contains("pct") ? 60 : list.contains("a") ? 65 : 0;
      const width = own * scale;
      return { width, height: 0, x: 0, y: 0, top: 0, left: 0, right: width, bottom: 0, toJSON: () => ({}) } as DOMRect;
    });
    try {
      const card = await mount();
      const widest = Math.max(...all(card, ".price-row .p").map((price) => (price.textContent ?? "").trim().length * 7));
      const rows = one(card, ".rows") as HTMLElement;
      await vi.waitFor(() => expect(rows.style.getPropertyValue("--bp-price")).toBe(`${widest}px`));
      expect(rows.style.getPropertyValue("--bp-change")).toBe("78px");
    } finally {
      room.mockRestore();
      layout.mockRestore();
      rect.mockRestore();
    }
  });

  it("a list row's columns are the shared widths, before the first measurement as wide as their contents", () => {
    const css = (PriceTrackerCard.styles as unknown as { cssText: string }[]).map((sheet) => sheet.cssText).join("\n");
    const rule = (selector: string): string | undefined =>
      css.match(new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\{([^}]*)\\}`))?.[1];
    expect(rule(".price-row")).toMatch(
      /grid-template-columns:\s*minmax\(0,\s*1fr\)\s*96px\s*var\(--bp-price,\s*auto\)\s*var\(--bp-change,\s*minmax\(78px,\s*auto\)\)/,
    );
    expect(rule(".rows.stacked .price-row")).toMatch(/grid-template-columns:\s*minmax\(0,\s*1fr\)\s*96px\s*var\(--bp-figures,\s*auto\)/);
  });

  it("below its name, a row's price, chip and amount stand right-aligned, without the line", () => {
    const css = (PriceTrackerCard.styles as unknown as { cssText: string }[]).map((sheet) => sheet.cssText).join("\n");
    const below = css.match(/\.rows\.below \.price-row\s*\{([^}]*)\}/)?.[1];
    expect(below).toMatch(/grid-template-columns:\s*minmax\(0,\s*1fr\)/);
    expect(below).toMatch(/grid-template-areas:\s*"lead"\s*"price"\s*"change"/);
    expect(css.match(/\.rows\.below \.price-row \.mini\s*\{([^}]*)\}/)?.[1]).toMatch(/display:\s*none/);
  });

  it("a list row shows a security's ISIN below its name, not its asset type", async () => {
    const card = await mount();
    const etf = all(card, ".price-row")[2];
    // The ISIN alone, without the asset type, as in the tiles.
    expect(textOf(etf?.querySelector(".s"))).toBe("IE00B4L5Y983");
  });

  it("long names wrap in the list and are cut in tiles with a title", async () => {
    // The whole name on hover, in the list as in the tiles: both cut it.
    const list = await mount();
    expect(all(list, ".price-row .n")[2]?.getAttribute("title")).toBe("iShares Core MSCI World UCITS ETF");
    const tiles = await mount({ layout: "tiles" });
    expect(all(tiles, ".tile .n")[2]?.getAttribute("title")).toBe("iShares Core MSCI World UCITS ETF");
    // In the list, two lines at most, cut with "…" after that, and a name
    // that takes two lines takes two of about the same length, which keeps
    // its first line off the price.
    const css = (PriceTrackerCard.styles as unknown as { cssText: string }[]).map((sheet) => sheet.cssText).join("\n");
    expect(css.match(/\n  \.n\s*\{([^}]*)\}/)?.[1]).toMatch(/-webkit-line-clamp:\s*2/);
    expect(css.match(/\.price-row \.n\s*\{([^}]*)\}/)?.[1]).toMatch(/text-wrap:\s*balance/);
  });

  it("Show all after the limit", async () => {
    const card = await mount({ limit: 2 });
    expect(rows(card)).toHaveLength(2);
    expect(textOf(one(card, ".show-all"))).toBe("Show all (4)");
    one(card, ".show-all")?.click();
    await card.updateComplete;
    expect(rows(card)).toHaveLength(4);
    expect(textOf(one(card, ".show-all"))).toBe("Show less");
    one(card, ".show-all")?.click();
    await card.updateComplete;
    expect(rows(card)).toHaveLength(2);
    expect(textOf(one(card, ".show-all"))).toBe("Show all (4)");
  });

  it("fetches statistics only for the rows shown", async () => {
    const hass = trackerHass();
    await mount({ limit: 2 }, hass);
    await vi.waitFor(() => expect(hass.messages.length).toBeGreaterThan(0));
    expect(hass.messages[0]?.["statistic_ids"]).toEqual(["sensor.bitpanda_btc_price_tracker_eur", "sensor.bitpanda_eth_price_tracker_eur"]);
  });

  it("sorts by the timeframe's change before it cuts to the limit", async () => {
    // By name, Bitcoin and Ethereum come first; Bitcoin (+4.16 % over the
    // week) and Sui (+4.00 % since its statistics start, three days ago)
    // rose most, ahead of the ETF (+0.94 %) and Ethereum (-3.79 %).
    const card = await mount({ timeframe: "week", sort: "change_desc", limit: 2 });
    await linesDrawn(card);
    expect(rows(card).map((row) => row.name)).toEqual(["Bitcoin", "Sui"]);
  });

  it("draws the lines when a foreign entity's change arrives with them", async () => {
    // Home Assistant may hand the card a new hass for another entity before
    // the card has drawn the statistics' answer.
    let open = (): void => undefined;
    const gate = new Promise<void>((done) => {
      open = done;
    });
    const inner = trackerHass();
    const hass: FakeHass = {
      ...inner,
      callWS: async <T>(message: Record<string, unknown>): Promise<T> => {
        await gate;
        return inner.callWS<T>(message);
      },
    };
    const card = await mount({}, hass);
    const foreign = inner.withState("light.somewhere_else", "on");
    const requestUpdate = card.requestUpdate.bind(card);
    let armed = true;
    vi.spyOn(card, "requestUpdate").mockImplementation((...args: Parameters<PriceTrackerCard["requestUpdate"]>) => {
      requestUpdate(...args);
      if (armed && args[0] !== "hass") {
        armed = false;
        card.hass = foreign;
      }
    });
    open();
    await linesDrawn(card);
  });

  it("a tap opens the price in the selected currency", async () => {
    const card = await mount({ currency: "USD" });
    const opened: string[] = [];
    card.addEventListener("hass-more-info", (event) => opened.push((event as CustomEvent).detail.entityId));
    all(card, ".price-row")[0]?.click();
    expect(opened).toEqual(["sensor.bitpanda_btc_price_tracker_usd"]);
  });

  it("renders dashes and never NaN when every sensor is unavailable", async () => {
    let hass = trackerHass();
    for (const entityId of Object.keys(hass.states)) hass = hass.withState(entityId, "unavailable", {});
    const card = await mount({}, hass);
    expect(card.shadowRoot?.textContent ?? "").not.toMatch(/NaN|undefined|null|Invalid/);
    expect(textOf(one(card, ".price-row .p"))).toBe("—");
  });

  it("an asset without a price in the selected currency, or without a category, shows dashes", async () => {
    const devices = [
      ...ASSETS,
      priceDevice({ symbol: "ODD", name: "Oddity", category: "unknown", prices: { EUR: { state: "1" } } }),
    ];
    const card = await mount({ currency: "USD" }, trackerHass({ devices }));
    const odd = rows(card).find((row) => row.name === "Oddity");
    expect(odd).toEqual({ name: "Oddity", sub: "ODD", price: "—", change: "—" });
  });

  it("two dashes sort by name", async () => {
    const devices = [
      ...ASSETS,
      priceDevice({ symbol: "ADA", name: "Cardano", category: "crypto", prices: { EUR: { state: "0.56" } } }),
    ];
    const base = trackerHass({ devices });
    const hass: FakeHass = {
      ...base,
      callWS: async <T>(message: Record<string, unknown>): Promise<T> => {
        const answer = await base.callWS<Record<string, unknown>>(message);
        delete answer["sensor.bitpanda_ada_price_tracker_eur"];
        delete answer["sensor.bitpanda_sui_price_tracker_eur"];
        return answer as T;
      },
    };
    const card = await mount({ sort: "change_asc" }, hass);
    await linesDrawn(card);
    expect(rows(card).slice(-2).map((row) => row.name)).toEqual(["Cardano", "Sui"]);
  });

  it("the footer writes the month in full, so no abbreviation's dot doubles the sentence's", async () => {
    const card = await mount({ currency: "USD" }, trackerHass({ language: "de" }));
    const footer = textOf(one(card, ".foot"));
    expect(footer).toContain("vom 10. Oktober.");
    expect(footer).not.toContain("..");
  });

  it("no ECB date, no footer", async () => {
    const devices = [priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { EUR: { state: "1" }, USD: { state: "1.1" } } })];
    const card = await mount({ currency: "USD" }, trackerHass({ devices }));
    expect(one(card, ".foot")).toBeNull();
  });

  it("the timeframe switch changes the changes", async () => {
    const card = await mount();
    all(card, "[role=radiogroup]")[0]?.querySelectorAll<HTMLElement>("[role=radio]")[1]?.click();
    await card.updateComplete;
    await vi.waitFor(() => expect(rows(card)[0]?.change).toBe("▲ +4.16%"));
  });

  it("no tracked asset shows the empty state, for a Price Tracker not set up or set up without assets", async () => {
    // German first: the last card mounted sets the editors' language.
    const german = await mount({}, makeHass({ devices: [portfolioDevice()], language: "de" }));
    expect(textOf(one(german, ".empty"))).toBe(
      "Richte den Bitpanda Price Tracker ein oder aktiviere ihn und füge Assets hinzu, dann erscheinen sie hier.",
    );
    const card = await mount({}, makeHass({ devices: [portfolioDevice()] }));
    expect(textOf(one(card, ".empty"))).toBe("Set up the Bitpanda Price Tracker or enable it and add assets to it to see them here.");
  });

  it("the editor form lists exactly the card's options", async () => {
    const fieldNames = (fields: { name: string; type?: string; schema?: { name: string; type?: string }[] }[]): string[] =>
      fields.flatMap((field) => (field.schema ? fieldNames(field.schema) : field.type === "divider" ? [] : [field.name]));
    // Every field: the groups and assets to choose show while some are chosen.
    const { form } = await openEditor("bitpanda-price-tracker-card", { group_selection: "only", asset_selection: "only" });
    expect(fieldNames(form.schema).sort()).toEqual(
      ["asset_selection", "assets", "currency", "group_selection", "groups", "layout", "limit", "sort", "timeframe", "title"].sort(),
    );
    // The asset groups: under Assets, right above the assets.
    const assets = form.schema.find((field) => (field as { title?: string }).title === "Assets") as unknown as { schema: { name: string; type?: string }[] };
    // Like the Portfolio's Wallets: the list's order and length, then the
    // asset groups and the assets, each set apart by a line.
    expect(assets.schema.map((field) => (field.type === "divider" ? "—" : field.name))).toEqual(
      ["sort", "limit", "—", "group_selection", "groups", "—", "asset_selection", "assets"],
    );
    const content = form.schema.find((field) => (field as { title?: string }).title === "Content") as unknown as { schema: { name: string }[] };
    expect(content.schema.map((field) => field.name)).toEqual(["layout", "timeframe", "currency"]);
    expect(form.computeLabel({ name: "assets" })).toBe("Choose assets");
    expect(form.computeHelper({ name: "assets" })).toBe("An asset from a hidden asset group stays hidden, even when chosen here");
    expect(form.computeHelper({ name: "timeframe" })).toBe("The 1D to 1Y buttons on the card change it only temporarily");
    expect(form.computeLabel({ name: "layout" })).toBe("Show as");
    expect(form.computeLabel({ name: "currency" })).toBe("Default currency");
    expect(form.computeHelper({ name: "currency" })).toBe("The buttons on the card change it only temporarily; more currencies via “Configure” on the Price Tracker");
    expect(form.computeLabel({ name: "limit" })).toBe("Assets before “Show all”");
    expect(form.computeHelper({ name: "limit" })).toBe("0 shows every asset");
    expect(form.computeHelper({ name: "sort" })).toBe("“Order as chosen” applies only when assets are set to “Only the ones chosen”; otherwise by name");
    expect(form.computeLabel({ name: "asset_selection" })).toBe("Assets shown");
    expect(JSON.stringify(form.schema)).toContain('"value":"CHF"');
    expect(PriceTrackerCard.getStubConfig()).toMatchObject({ layout: "list", currency: "EUR", sort: "name" });
  });

  it("the editor offers the currencies the Price Tracker has prices in, else every supported one", async () => {
    type Field = { name: string; schema?: Field[]; selector?: { select?: { options: { value: string }[] } } };
    const flat = (fields: Field[]): Field[] => fields.flatMap((field) => (field.schema ? flat(field.schema) : [field]));
    const options = async (hass?: FakeHass): Promise<string[]> =>
      (flat((await openEditor("bitpanda-price-tracker-card", {}, hass)).form.schema as Field[]).find((field) => field.name === "currency")?.selector?.select?.options ?? []).map(
        (option) => option.value,
      );
    const supported = ["EUR", "CHF", "CZK", "DKK", "GBP", "HUF", "NOK", "PLN", "RON", "SEK", "TRY", "USD"];
    // Before Home Assistant hands the editor its state, and without a Price
    // Tracker: every supported currency.
    expect(await options()).toEqual(supported);
    expect(await options(trackerHass())).toEqual(["EUR", "USD"]);
    expect(await options(makeHass({ devices: [portfolioDevice()] }))).toEqual(supported);
  });

  it("has a size for both kinds of dashboard view", async () => {
    const card = await mount();
    expect(card.getCardSize()).toBe(6);
    expect(card.getGridOptions()).toEqual({ columns: 12, min_columns: 6 });
  });
});
