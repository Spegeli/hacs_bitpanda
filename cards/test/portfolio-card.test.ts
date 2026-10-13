import { afterEach, describe, expect, it, vi } from "vitest";

import { PortfolioCard, blockLayout, groupReturn } from "../src/portfolio-card";
import { windowFor } from "../src/statistics";
import type { Timeframe } from "../src/types";
import { BTC, ETH, EUNL, XAU, makeHass, portfolioDevice, walletDevice, type FakeHass, type FakeWallet } from "./fixtures";

const HOUR = 3_600_000;
const TOTAL = "sensor.bitpanda_portfolio_total_value";

function portfolioHass(options: { language?: string } = {}): FakeHass {
  return makeHass({
    devices: [portfolioDevice(), walletDevice(BTC), walletDevice(ETH), walletDevice(EUNL), walletDevice(XAU)],
    callWS: async (message) => {
      // Bitpanda's value history of the timeframe, as the integration hands it on.
      const now = Date.now();
      const start = windowFor(message["timeframe"] as Timeframe, now).start;
      return { points: [[start, 12000], [start + (now - start) / 2, 12400], [now - HOUR, 12760.2]] };
    },
    ...options,
  });
}

async function mount(config: Record<string, unknown> = {}, hass: FakeHass = portfolioHass()): Promise<PortfolioCard> {
  const card = document.createElement("bitpanda-portfolio-card") as PortfolioCard;
  card.setConfig({ type: "custom:bitpanda-portfolio-card", ...config });
  card.hass = hass;
  document.body.append(card);
  await card.updateComplete;
  return card;
}

const root = (card: PortfolioCard): ShadowRoot => card.shadowRoot as ShadowRoot;
const textOf = (element: Element | null | undefined): string => (element?.textContent ?? "").replace(/\s+/g, " ").trim();
const all = (card: PortfolioCard, selector: string): HTMLElement[] => [...root(card).querySelectorAll<HTMLElement>(selector)];
const one = (card: PortfolioCard, selector: string): HTMLElement | null => root(card).querySelector<HTMLElement>(selector);

/** The detail's rows as "Label value", from its two-column grids. */
function detailRows(card: PortfolioCard): string[] {
  const cells = all(card, ".detail .grid > span").map((cell) => textOf(cell));
  return cells.filter((_, index) => index % 2 === 0).map((label, index) => `${label} ${cells[index * 2 + 1] ?? ""}`);
}

async function settled(card: PortfolioCard): Promise<void> {
  await vi.waitFor(() => expect(one(card, "svg.spark .line")?.getAttribute("d")).toBeTruthy());
  await card.updateComplete;
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("the Bitpanda Portfolio card", () => {
  it("shows total value, the return of the start timeframe and its line", async () => {
    const card = await mount({ timeframe: "week" });
    await settled(card);
    expect(textOf(one(card, ".title"))).toBe("Bitpanda Portfolio");
    expect(textOf(one(card, ".hero"))).toBe("12760.20 EUR");
    // The amount is what the percentage means on today's total value.
    expect(textOf(one(card, ".chip"))).toBe("▲ +2.31%");
    expect(textOf(one(card, ".chip-amount"))).toBe("+€288.11");
    expect(textOf(one(card, ".chip-label"))).toBe("return over 1 week");
    expect(textOf(one(card, "[aria-checked=true]"))).toBe("1W");
    expect(textOf(one(card, ".caption"))).toMatch(/^Total value, .+ – today$/);
  });

  it("fetches the line again once the return of the timeframe arrives, as after a restart", async () => {
    // Starting up, Total value can arrive before the returns, whose refresh
    // brings Bitpanda's value history: the first answer has no points.
    let ready = false;
    const hass = makeHass({
      devices: [portfolioDevice()],
      callWS: async () => ({ points: ready ? [[Date.now() - 20 * HOUR, 1], [Date.now() - HOUR, 2]] : [] }),
    });
    const starting = hass.withState("sensor.bitpanda_portfolio_return_day", "unavailable", {});
    const card = await mount({}, starting);
    await vi.waitFor(() => expect(hass.messages).toHaveLength(1));
    expect(one(card, "svg.spark .line")).toBeNull();
    ready = true;
    card.hass = starting.withState("sensor.bitpanda_portfolio_return_day", "-0.42", { unit_of_measurement: "%" });
    await settled(card);
    expect(hass.messages).toHaveLength(2);
  });

  it("draws its line from Bitpanda's value history, not the recorder", async () => {
    const hass = portfolioHass();
    const card = await mount({ timeframe: "month" }, hass);
    await settled(card);
    expect(hass.messages).toEqual([{ type: "bitpanda/portfolio_history", timeframe: "month" }]);
    // Six-hourly points over a month are one stroke, not dots.
    expect(one(card, "svg.spark .line")?.getAttribute("d")?.match(/M/g)).toHaveLength(1);
  });

  it("the line takes the colour of the return beside it", async () => {
    const down = await mount({ timeframe: "day" });
    await settled(down);
    expect(one(down, "svg.spark")?.getAttribute("class")).toBe("spark down");
    const up = await mount({ timeframe: "week" });
    await settled(up);
    expect(one(up, "svg.spark")?.getAttribute("class")).toBe("spark up");
    const flat = await mount({ timeframe: "week" }, makeHass({
      devices: [portfolioDevice({ returns: { week: "0.001" } })],
      callWS: async () => ({ points: [[Date.now() - 6 * 24 * HOUR, 1], [Date.now() - HOUR, 1]] }),
    }));
    await settled(flat);
    expect(one(flat, "svg.spark")?.getAttribute("class")).toBe("spark flat");
    const css = (await import("../src/styles")).cardStyles.cssText;
    expect(css).toMatch(/svg\.spark\.up \.line\s*\{[^}]*stroke:\s*var\(--bp-up\)/);
    expect(css).toMatch(/svg\.spark\.down \.line\s*\{[^}]*stroke:\s*var\(--bp-down\)/);
    expect(css).toMatch(/svg\.spark\.flat \.line\s*\{[^}]*stroke:\s*var\(--bp-muted\)/);
  });

  it("switching the timeframe changes chip, line and caption", async () => {
    const hass = portfolioHass();
    const card = await mount({}, hass);
    await settled(card);
    expect(textOf(one(card, ".chip"))).toBe("▼ -0.42%");
    expect(textOf(one(card, ".chip-amount"))).toBe("-€53.82");
    expect(textOf(one(card, ".caption"))).toBe("Total value, last 24 hours");
    all(card, "[role=radio]")[4]?.click();
    await card.updateComplete;
    await vi.waitFor(() => expect(hass.messages.at(-1)).toEqual({ type: "bitpanda/portfolio_history", timeframe: "year" }));
    expect(textOf(one(card, ".chip"))).toBe("▲ +18.65%");
    expect(textOf(one(card, ".chip-amount"))).toBe("+€2,005.71");
    expect(textOf(one(card, ".chip-label"))).toBe("return over 1 year");
  });

  it("the caption names where Bitpanda's value history starts inside the window", async () => {
    const start = Date.now() - 2 * 24 * HOUR;
    const hass = makeHass({
      devices: [portfolioDevice()],
      callWS: async () => ({ points: [[start, 1], [Date.now() - HOUR, 2]] }),
    });
    const card = await mount({ timeframe: "week" }, hass);
    await settled(card);
    const day = new Intl.DateTimeFormat("en", { day: "numeric", month: "short" }).format(start);
    expect(textOf(one(card, ".caption"))).toBe(`Total value, ${day} – today`);
  });

  it("without a total value sensor a tap opens nothing", async () => {
    const device = portfolioDevice();
    device.sensors = device.sensors.filter((sensor) => sensor.translationKey !== "total_value");
    const card = await mount({}, makeHass({ devices: [device] }));
    const opened = vi.fn();
    card.addEventListener("hass-more-info", opened);
    one(card, ".hero")?.click();
    expect(opened).not.toHaveBeenCalled();
    expect(textOf(one(card, ".hero"))).toBe("—");
  });

  it("a custom title replaces the card's name", async () => {
    const card = await mount({ title: "Mein Depot" });
    expect(textOf(one(card, ".title"))).toBe("Mein Depot");
  });

  it("hides cash and allocation when switched off but keeps the total", async () => {
    const card = await mount({ show_cash: false, show_allocation: false });
    expect(one(card, ".pair")).toBeNull();
    expect(one(card, ".bar")).toBeNull();
    expect(textOf(one(card, ".hero"))).toBe("12760.20 EUR");
  });

  it("allocation sums categories, cash and cash plus, largest first", async () => {
    const card = await mount();
    const legend = all(card, ".legend > span").map((item) => textOf(item));
    // crypto 5890.11 + 1269.91, etf 2045.10, cash plus 2000, cash 812.40, metal 67.01 of 12084.53;
    // without translations a category shows its key.
    expect(legend).toEqual(["crypto 59%", "etf 17%", "Cash Plus 17%", "Cash 7%", "metal <1%"]);
    expect(all(card, ".bar > span")).toHaveLength(5);
  });

  it("category names come from the integration's translations", async () => {
    const hass = makeHass({
      devices: [portfolioDevice(), walletDevice(BTC)],
      translations: { "component.bitpanda.selector.asset_group.options.crypto": "Kryptowährungen" },
      language: "de",
    });
    const card = await mount({}, hass);
    expect(textOf(one(card, ".group .name"))).toBe("Kryptowährungen");
  });

  it("groups start closed with count badge and sum", async () => {
    const card = await mount();
    const groups = all(card, ".group");
    expect(groups.map((group) => textOf(group.querySelector(".name")))).toEqual(["crypto", "etf", "metal"]);
    expect(groups.map((group) => textOf(group.querySelector(".count")))).toEqual(["2", "1", "1"]);
    expect(textOf(groups[0]?.querySelector(".sum"))).toBe("7160.02 EUR");
    // The group's return since purchase above its sum: what all its wallets
    // made on what went into them.
    expect(textOf(groups[0]?.querySelector(".gright .gchip"))).toBe("▲ +9.36%");
    expect(groups[0]?.querySelector(".gright .gchip + .sum")).not.toBeNull();
    expect(groups[0]?.querySelector(".gchip")?.classList.contains("up")).toBe(true);
    // No invested amount known for the ETF: a muted dash in place of the
    // chip, as a wallet row shows.
    expect(textOf(groups[1]?.querySelector(".gright .gchip.none"))).toBe("—");
    expect(groups[1]?.querySelector(".gchip")?.classList.contains("up")).toBe(false);
    expect(groups.map((group) => group.getAttribute("aria-expanded"))).toEqual(["false", "false", "false"]);
    expect(all(card, ".wallet")).toHaveLength(0);
  });

  it("opening a group shows its wallets sorted by value", async () => {
    const card = await mount();
    all(card, ".group")[0]?.click();
    await card.updateComplete;
    expect(all(card, ".wallet .n").map((name) => textOf(name))).toEqual(["Bitcoin", "Ethereum"]);
    all(card, ".group")[0]?.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await card.updateComplete;
    expect(all(card, ".wallet")).toHaveLength(0);
  });

  it("sorts by return and by name", async () => {
    const byReturn = await mount({ group_wallets: false, sort: "return" });
    expect(all(byReturn, ".wallet .n").map((name) => textOf(name))).toEqual([
      "Bitcoin",
      "iShares Core MSCI World UCITS ETF",
      "Gold",
      "Ethereum",
    ]);
    const byName = await mount({ group_wallets: false, sort: "name" });
    expect(all(byName, ".wallet .n").map((name) => textOf(name))).toEqual([
      "Bitcoin",
      "Ethereum",
      "Gold",
      "iShares Core MSCI World UCITS ETF",
    ]);
  });

  it("a flat list shows every wallet without headings", async () => {
    const card = await mount({ group_wallets: false });
    expect(all(card, ".group")).toHaveLength(0);
    expect(all(card, ".wallet .n").map((name) => textOf(name))).toEqual([
      "Bitcoin",
      "iShares Core MSCI World UCITS ETF",
      "Ethereum",
      "Gold",
    ]);
  });

  it("a group sum is a dash when one wallet value is missing", async () => {
    const hass = portfolioHass().withState("sensor.bitpanda_eth_wallet_total", "unavailable", {});
    const card = await mount({}, hass);
    expect(textOf(all(card, ".group")[0]?.querySelector(".sum"))).toBe("—");
    expect(one(card, ".bar")).toBeNull();
    expect(textOf(one(card, ".allocation-missing"))).toBe("—");
  });

  it("hidden wallets leave the total and the allocation whole; a group counts, sums and returns the wallets it shows", async () => {
    const whole = textOf(one(await mount(), ".legend"));
    const card = await mount({ asset_selection: "all_except", assets: ["dev-wallet-eth"] });
    const crypto = all(card, ".group")[0];
    expect(textOf(crypto?.querySelector(".count"))).toBe("1");
    expect(textOf(crypto?.querySelector(".sum"))).toBe("5890.11 EUR");
    // Bitcoin's own return: 5890.11 on 5240.00 invested.
    expect(textOf(crypto?.querySelector(".gchip"))).toBe("▲ +12.41%");
    crypto?.click();
    await card.updateComplete;
    expect(all(card, ".wallet .n").map((name) => textOf(name))).toEqual(["Bitcoin"]);
    expect(textOf(one(card, ".hero"))).toBe("12760.20 EUR");
    expect(textOf(one(card, ".legend"))).toBe(whole);
  });

  it("shows the picked asset groups only, and in them the assets picked", async () => {
    const names = (card: PortfolioCard): string[] => all(card, ".wallet .n").map((name) => textOf(name));
    const crypto = await mount({ group_selection: "only", groups: ["crypto"] });
    expect(all(crypto, ".group .name").map((name) => textOf(name))).toEqual(["crypto"]);
    const flat = await mount({ group_wallets: false, group_selection: "only", groups: ["crypto"] });
    expect(names(flat)).toEqual(["Bitcoin", "Ethereum"]);
    const rest = await mount({ group_wallets: false, group_selection: "all_except", groups: ["crypto"], asset_selection: "all_except", assets: ["dev-wallet-xau"] });
    expect(names(rest)).toEqual(["iShares Core MSCI World UCITS ETF"]);
    // A wallet picked outside the groups shown stays out.
    const outside = await mount({ group_wallets: false, group_selection: "only", groups: ["crypto"], asset_selection: "only", assets: ["dev-wallet-eunl", "dev-wallet-btc"] });
    expect(names(outside)).toEqual(["Bitcoin"]);
  });

  it("hides the total value and its return; the timeframe buttons stay while the line needs them", async () => {
    const lineOnly = await mount({ show_total: false });
    expect(one(lineOnly, ".hero")).toBeNull();
    expect(one(lineOnly, ".hero-line")).toBeNull();
    expect(one(lineOnly, ".seg")).not.toBeNull();
    await vi.waitFor(() => expect(one(lineOnly, ".plot")).not.toBeNull());
    const neither = await mount({ show_total: false, show_graph: false });
    expect(one(neither, ".seg")).toBeNull();
    expect(one(neither, ".plot")).toBeNull();
    expect(one(neither, ".pair")).not.toBeNull();
  });

  it("says so when the card's selection leaves no wallet, and drops the search field", async () => {
    const none = await mount({ show_search: true, group_selection: "only", groups: [] });
    expect(textOf(one(none, ".empty"))).toBe("No wallets in this card's selection.");
    expect(one(none, ".search")).toBeNull();
    // Groups held by none, without grouping.
    const flat = await mount({ group_wallets: false, group_selection: "only", groups: ["stock"] });
    expect(textOf(one(flat, ".empty"))).toBe("No wallets in this card's selection.");
    const german = await mount({ asset_selection: "only", assets: [] }, portfolioHass({ language: "de" }));
    expect(textOf(one(german, ".empty"))).toBe("Keine Wallets in der Auswahl dieser Karte.");
  });

  it("only shows the picked wallets", async () => {
    const card = await mount({ group_wallets: false, asset_selection: "only", assets: ["dev-wallet-xau", "dev-wallet-btc"] });
    expect(all(card, ".wallet .n").map((name) => textOf(name))).toEqual(["Bitcoin", "Gold"]);
  });

  it("the chevron opens the wallet detail with rewards", async () => {
    const card = await mount({ group_wallets: false });
    const eth = all(card, ".wallet").find((row) => textOf(row.querySelector(".n")) === "Ethereum");
    (eth?.querySelector(".chevron") as HTMLElement | null)?.click();
    await card.updateComplete;
    const rows = detailRows(card);
    expect(rows.slice(0, 6)).toEqual([
      "Available 0.33 ETH · 762.00 EUR",
      "Staked 0.22 ETH · 507.91 EUR",
      "Staking APR 2.9%",
      "Average buy price €2,377.00",
      "Invested €1,307.35",
      "Profit / loss -€37.44 (-3.10%)",
    ]);
    expect(textOf(one(card, ".detail h4"))).toBe("Staking rewards");
    expect(rows[6]).toBe("Net, all time 0.0041 ETH · worth €9.47 today");
    expect(rows[7]).toMatch(/^Payouts 12 · last .+/);
    // A value breaks only between its parts, after the middle dot, which
    // stays with the part before it.
    const staked = all(card, ".detail .grid > span:nth-child(even)")[1]!;
    expect(staked.textContent).toContain(" · ");
    const parts = (index: number): string[] =>
      [...all(card, ".detail .grid > span:nth-child(even)")[index]!.querySelectorAll(".part")].map((part) => textOf(part));
    expect(parts(1)).toEqual(["0.22 ETH", "507.91 EUR"]);
    expect(parts(6)).toEqual(["0.0041 ETH", "worth €9.47 today"]);
    expect(parts(7)[0]).toBe("12");
    expect(parts(7)[1]).toMatch(/^last .+/);
    expect(parts(5)).toEqual(["-€37.44", "(-3.10%)"]);
  });

  it("a wallet row shows its units to 4 decimals, its detail all of them", async () => {
    const vision: FakeWallet = {
      symbol: "VSN", name: "Vision", category: "crypto", units: 21500.09377247, total: "823.63",
      staked: { units: 21500.09377247, value: "823.63" }, returnPercent: -68.47,
    };
    const card = await mount({ group_wallets: false }, makeHass({ devices: [portfolioDevice(), walletDevice(vision)] }));
    const row = all(card, ".wallet")[0];
    expect(textOf(row?.querySelector(".s"))).toBe("21,500.0937 VSN");
    (row?.querySelector(".chevron") as HTMLElement | null)?.click();
    await card.updateComplete;
    expect(detailRows(card)).toContain("Staked 21,500.09377247 VSN · 823.63 EUR");
  });

  it("no rewards line without a staking sensor", async () => {
    const card = await mount({ group_wallets: false });
    const btc = all(card, ".wallet").find((row) => textOf(row.querySelector(".n")) === "Bitcoin");
    (btc?.querySelector(".chevron") as HTMLElement | null)?.click();
    await card.updateComplete;
    expect(one(card, ".detail h4")).toBeNull();
    expect(detailRows(card)).toEqual([
      "Available 0.0653 BTC · 5890.11 EUR",
      "Average buy price €80,200.00",
      "Invested €5,240.00",
      "Profit / loss +€650.11 (+12.40%)",
    ]);
  });

  it("names the allocation bar for screen readers", async () => {
    const card = await mount();
    expect(one(card, ".bar")?.getAttribute("aria-label")).toBe("Allocation bar");
  });

  it("an option left empty in YAML shows the default, not an error", async () => {
    const card = await mount({ title: null, timeframe: null, sort: null });
    expect(textOf(one(card, ".title"))).toBe("Bitpanda Portfolio");
  });

  it("keeps the Portfolio's currency and the group sums when Total value is disabled", async () => {
    const portfolio = portfolioDevice({ currency: "CHF" });
    portfolio.sensors = portfolio.sensors.filter((sensor) => sensor.translationKey !== "total_value");
    const hass = makeHass({ devices: [portfolio, walletDevice({ ...BTC, currency: "CHF" }), walletDevice({ ...ETH, currency: "CHF" })] });
    const card = await mount({}, hass);
    expect(textOf(all(card, ".group")[0]?.querySelector(".sum"))).toBe("7160.02 CHF");
    (all(card, ".group")[0] as HTMLElement).click();
    await card.updateComplete;
    (one(card, ".wallet .chevron") as HTMLElement | null)?.click();
    await card.updateComplete;
    expect(detailRows(card)[1]).toBe("Average buy price CHF 80,200.00");
  });

  it("shows invested, profit / loss and the rewards' worth in cents, prices in full", async () => {
    const small: FakeWallet = {
      symbol: "ADA", name: "Cardano", category: "crypto", units: 12, total: "4.20", available: "3.50",
      staked: { units: 2, value: "0.70", apr: 2.5, rewards: { net: 0.05, netValue: 0.01734, count: 3, lastAt: "2026-10-06T16:12:00Z" } },
      returnPercent: -2.86, averageBuyPrice: 0.36012, invested: 4.3215, totalReturn: -0.12345678,
    };
    const hass = makeHass({ devices: [portfolioDevice(), walletDevice(small)] });
    const card = await mount({ group_wallets: false }, hass);
    (one(card, ".wallet .chevron") as HTMLElement | null)?.click();
    await card.updateComplete;
    const rows = detailRows(card);
    expect(rows.slice(3, 6)).toEqual(["Average buy price €0.36012", "Invested €4.32", "Profit / loss -€0.12 (-2.86%)"]);
    expect(rows[6]).toBe("Net, all time 0.05 ADA · worth €0.02 today");
  });

  it("tapping total value, chip, cash, cash plus and a row opens more-info", async () => {
    const card = await mount({ group_wallets: false });
    const opened: string[] = [];
    card.addEventListener("hass-more-info", (event) => opened.push((event as CustomEvent).detail.entityId));
    one(card, ".hero")?.click();
    one(card, ".chip")?.click();
    all(card, ".pair [role=button]").forEach((item) => item.click());
    all(card, ".wallet .tap")[0]?.click();
    expect(opened).toEqual([
      TOTAL,
      "sensor.bitpanda_portfolio_return_day",
      "sensor.bitpanda_portfolio_cash",
      "sensor.bitpanda_portfolio_cash_plus",
      "sensor.bitpanda_btc_wallet_total",
    ]);
  });

  it("the eye blurs every amount and unit and keeps the percentages", async () => {
    const card = await mount({ hide_amounts: true, group_wallets: false });
    expect(one(card, ".hero .amount")?.classList.contains("blur")).toBe(true);
    expect(all(card, ".pair .amount.blur")).toHaveLength(2);
    expect(one(card, ".chip-amount .amount")?.classList.contains("blur")).toBe(true);
    expect(textOf(one(card, ".chip"))).toBe("▼ -0.42%");
    one(card, ".eye")?.click();
    await card.updateComplete;
    expect(all(card, ".amount.blur")).toHaveLength(0);
  });

  it("renders dashes and never NaN when every sensor is unavailable", async () => {
    let hass = portfolioHass();
    for (const entityId of Object.keys(hass.states)) hass = hass.withState(entityId, "unavailable", {});
    const card = await mount({ group_wallets: false }, hass);
    all(card, ".chevron").forEach((chevron) => chevron.click());
    await card.updateComplete;
    const shown = root(card).textContent ?? "";
    expect(shown).not.toMatch(/NaN|undefined|null|Invalid/);
    expect(textOf(one(card, ".hero"))).toBe("—");
    expect(textOf(one(card, ".chip"))).toBe("—");
  });

  it("no portfolio shows the empty state", async () => {
    const card = await mount({}, makeHass());
    expect(textOf(one(card, ".empty"))).toBe("Set up the Bitpanda Portfolio to see it here.");
  });

  it("no wallets says so", async () => {
    const card = await mount({}, makeHass({ devices: [portfolioDevice()] }));
    expect(textOf(one(card, ".empty"))).toBe("No wallets yet.");
  });

  it("the editor form lists exactly the card's options", async () => {
    const names = (fields: { name: string; type?: string; schema?: { name: string; type?: string }[] }[]): string[] =>
      fields.flatMap((field) => (field.schema ? names(field.schema) : field.type === "divider" ? [] : [field.name]));
    const form = await PortfolioCard.getConfigForm();
    expect(names(form.schema).sort()).toEqual(
      ["asset_selection", "assets", "group_selection", "group_wallets", "groups", "hide_amounts", "limit", "show_allocation", "show_cash", "show_graph", "show_search", "show_total", "show_wallets", "sort", "timeframe", "title"].sort(),
    );
    expect(form.computeLabel({ name: "show_cash" })).toBe("Cash and Cash Plus");
    // The total and its return: the first toggle under Content.
    const content = form.schema.find((field) => (field as { title?: string }).title === "Content") as unknown as { schema: { name: string }[] };
    expect(content.schema.map((field) => field.name)).toEqual(["timeframe", "show_total", "show_graph", "show_cash", "show_allocation", "show_wallets"]);
    expect(form.computeLabel({ name: "show_total" })).toBe("Total value and return");
    expect(form.computeHelper({ name: "show_total" })).toBe("The timeframe buttons stay while the line is shown");
    // The search field: under Wallets, off unless chosen.
    const wallets = form.schema.find((field) => (field as { title?: string }).title === "Wallets") as unknown as { schema: { name: string; type?: string; default?: unknown }[] };
    expect(wallets.schema.find((field) => field.name === "show_search")?.default).toBe(false);
    expect(form.computeLabel({ name: "show_search" })).toBe("Search field");
    expect(form.computeHelper({ name: "show_search" })).toBe("Finds wallets by name, symbol or ISIN");
    // The asset groups: under Wallets, right above the assets.
    // The search field comes first: it stands above the wallets.
    // Lines set the asset groups apart from the list's options and from the assets.
    expect(wallets.schema.map((field) => (field.type === "divider" ? "—" : field.name))).toEqual(
      ["show_search", "group_wallets", "sort", "limit", "—", "group_selection", "groups", "—", "asset_selection", "assets"],
    );
    expect(form.computeLabel({ name: "group_selection" })).toBe("Asset groups shown");
    expect(form.computeLabel({ name: "groups" })).toBe("Choose asset groups");
    // The Portfolio's list holds wallets: its fields say so.
    expect(form.computeHelper({ name: "group_selection" })).toBe("Applies to the wallets only; total value, Cash, Cash Plus and allocation always show the whole portfolio");
    expect(form.computeLabel({ name: "asset_selection" })).toBe("Wallets shown");
    expect(form.computeLabel({ name: "assets" })).toBe("Choose wallets");
    expect(form.computeHelper({ name: "assets" })).toBe("A wallet from a hidden asset group stays hidden, even when chosen here");
    expect(form.computeLabel({ name: "limit" })).toBe("Wallets before “Show all”");
    expect(PortfolioCard.getStubConfig()).toEqual({ timeframe: "day", sort: "value", group_selection: "all", asset_selection: "all" });
  });

  it("has a size for both kinds of dashboard view", async () => {
    const card = await mount();
    expect(card.getCardSize()).toBe(8);
    expect(card.getGridOptions()).toEqual({ columns: 12, min_columns: 6 });
  });
});

describe("what the Portfolio card shows, by choice", () => {
  const VSN: FakeWallet = {
    symbol: "VSN", name: "Vision", category: "crypto", units: 12000, total: "410.33",
    staked: { units: 12000, value: "410.33", apr: 7.5 }, returnPercent: -24.6,
  };
  const AEEM: FakeWallet = {
    symbol: "AEEM", name: "Amundi MSCI Emerging Markets UCITS ETF", category: "etf", isin: "LU1681045370",
    units: 52.3, total: "265.34", returnPercent: 2.2,
  };
  const sixWallets = (): FakeHass => makeHass({ devices: [portfolioDevice(), ...[BTC, ETH, EUNL, XAU, VSN, AEEM].map(walletDevice)] });

  it("leaves the line out, and does not ask for it", async () => {
    const hass = portfolioHass();
    const card = await mount({ show_graph: false }, hass);
    expect(one(card, "svg.spark")).toBeNull();
    expect(one(card, ".caption")).toBeNull();
    expect(hass.messages).toEqual([]);
  });

  it("leaves the wallets out", async () => {
    const card = await mount({ show_wallets: false });
    expect(all(card, ".group")).toHaveLength(0);
    expect(all(card, ".wallet")).toHaveLength(0);
    expect(one(card, ".empty")).toBeNull();
  });

  it("without grouping, lists five wallets with Show all and Show less", async () => {
    const card = await mount({ group_wallets: false }, sixWallets());
    expect(all(card, ".wallet")).toHaveLength(5);
    expect(textOf(one(card, ".show-all"))).toBe("Show all (6)");
    one(card, ".show-all")?.click();
    await card.updateComplete;
    expect(all(card, ".wallet")).toHaveLength(6);
    expect(textOf(one(card, ".show-all"))).toBe("Show less");
    one(card, ".show-all")?.click();
    await card.updateComplete;
    expect(all(card, ".wallet")).toHaveLength(5);
    expect(all(await mount({ group_wallets: false, limit: 0 }, sixWallets()), ".wallet")).toHaveLength(6);
  });

  it("grouped, shows every wallet of an open group, whatever the limit", async () => {
    const card = await mount({ limit: 1 }, sixWallets());
    expect(one(card, ".show-all")).toBeNull();
    all(card, ".group")[0]?.click();
    await card.updateComplete;
    expect(all(card, ".members .wallet")).toHaveLength(3);
  });

  it("explains that the limit holds without grouping only", async () => {
    const form = await PortfolioCard.getConfigForm();
    expect(form.computeHelper({ name: "limit" })).toBe("Only while “Wallets in asset groups” is off; 0 shows all");
    expect(form.computeLabel({ name: "group_wallets" })).toBe("Wallets in asset groups");
    expect(form.computeHelper({ name: "show_graph" })).toBeUndefined();
    expect(form.computeLabel({ name: "show_graph" })).toBe("Total value line");
    expect(form.computeLabel({ name: "show_wallets" })).toBe("Wallets");
  });

  it("is suggested for the Portfolio's entities and a wallet's", () => {
    const entry = (window as unknown as { customCards: { type: string; getEntitySuggestion?: (hass: unknown, id: string) => unknown }[] }).customCards.find(
      (item) => item.type === "bitpanda-portfolio-card",
    );
    const hass = sixWallets();
    expect(entry?.getEntitySuggestion?.(hass, "sensor.bitpanda_portfolio_total_value")).toMatchObject({ config: { type: "custom:bitpanda-portfolio-card" } });
    expect(entry?.getEntitySuggestion?.(hass, "sensor.bitpanda_btc_wallet_total")).toMatchObject({ config: { type: "custom:bitpanda-portfolio-card" } });
  });
});

describe("the staked share beside the units", () => {
  it("stands right of the units in every row when all have room, below them in every row otherwise", async () => {
    const room = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(300);
    const rect = vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      const width = this.classList.contains("s") ? 150 : this.classList.contains("badge") ? 100 : 0;
      return { width, height: 0, x: 0, y: 0, top: 0, left: 0, right: width, bottom: 0, toJSON: () => ({}) } as DOMRect;
    });
    try {
      const card = await mount({ group_wallets: false });
      await vi.waitFor(() => expect(one(card, ".wallets")?.classList.contains("stake-inline")).toBe(true));
      room.mockReturnValue(240);
      card.requestUpdate();
      await card.updateComplete;
      await vi.waitFor(() => expect(one(card, ".wallets")?.classList.contains("stake-inline")).toBe(false));
    } finally {
      room.mockRestore();
      rect.mockRestore();
    }
  });
});

describe("a group's return", () => {
  it("is the value of all its wallets against what went into them", () => {
    const hass = makeHass({ devices: [portfolioDevice(), walletDevice(BTC), walletDevice(ETH)] });
    const wallets = [
      { total: "sensor.bitpanda_btc_wallet_total" },
      { total: "sensor.bitpanda_eth_wallet_total" },
    ];
    expect(groupReturn(hass, wallets)).toBeCloseTo(9.3575, 3);
  });

  it("is unknown when a wallet lacks its value or invested amount, or nothing went in", () => {
    const hass = makeHass({
      devices: [portfolioDevice(), walletDevice(BTC), walletDevice(EUNL), walletDevice({ ...XAU, invested: 0 })],
    });
    expect(groupReturn(hass, [{ total: "sensor.bitpanda_btc_wallet_total" }, { total: "sensor.bitpanda_eunl_wallet_total" }])).toBeUndefined();
    expect(groupReturn(hass, [{ total: "sensor.bitpanda_xau_wallet_total" }])).toBeUndefined();
    expect(groupReturn(hass, [{ total: undefined }])).toBeUndefined();
  });

  it("chip and sum stand beside the name, below it side by side, or below it stacked: the same in every group", () => {
    const crypto = { room: 300, left: 150, chip: 80, value: 100 };
    const etf = { room: 300, left: 100, value: 60 };
    // Stacked beside the name, the wider of chip and sum decides.
    expect(blockLayout([crypto, etf])).toBe("beside");
    expect(blockLayout([{ ...crypto, room: 261 }, etf])).toBe("row");
    // One group without room even for the row below its name: all stack.
    expect(blockLayout([{ ...crypto, room: 187 }, { ...etf, room: 187 }])).toBe("stacked");
    expect(blockLayout([{ ...crypto, room: 188 }, { ...etf, room: 188 }])).toBe("row");
    // Without a chip there is nothing to stack.
    expect(blockLayout([{ ...etf, room: 100 }])).toBe("row");
    expect(blockLayout([])).toBe("beside");
    // Below the name a block may have more room than beside it: a wallet
    // row's reaches under the chevron.
    expect(blockLayout([{ ...crypto, room: 187, below: 188 }])).toBe("row");
    expect(blockLayout([{ ...crypto, room: 188, below: 187 }])).toBe("stacked");
  });

  it("chip and sum move below the name, side by side, then stacked, in every group once one lacks room", async () => {
    const room = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(300);
    const rect = vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      // Chip and sum are measured one by one: stacked, the wider decides.
      const width = this.classList.contains("gleft") ? 150 : this.classList.contains("sum") ? 100 : this.classList.contains("gchip") ? 80 : 0;
      return { width, height: 0, x: 0, y: 0, top: 0, left: 0, right: width, bottom: 0, toJSON: () => ({}) } as DOMRect;
    });
    const layout = (card: PortfolioCard) => {
      const wallets = one(card, ".wallets")?.classList;
      return [wallets?.contains("groups-wrapped"), wallets?.contains("groups-stacked")];
    };
    try {
      const card = await mount();
      await vi.waitFor(() => expect(layout(card)).toEqual([false, false]));
      room.mockReturnValue(240);
      card.requestUpdate();
      await card.updateComplete;
      await vi.waitFor(() => expect(layout(card)).toEqual([true, false]));
      room.mockReturnValue(170);
      card.requestUpdate();
      await card.updateComplete;
      await vi.waitFor(() => expect(layout(card)).toEqual([true, true]));
      room.mockReturnValue(300);
      card.requestUpdate();
      await card.updateComplete;
      await vi.waitFor(() => expect(layout(card)).toEqual([false, false]));
    } finally {
      room.mockRestore();
      rect.mockRestore();
    }
    const css = (await import("../src/styles")).cardStyles.cssText;
    expect(css.match(/\.group \.gright\s*\{([^}]*)\}/)?.[1]).toMatch(/flex-direction:\s*column/);
    expect(css.match(/\.wallets\.groups-wrapped \.group \.gright\s*\{([^}]*)\}/)?.[1]).toMatch(/flex-direction:\s*row/);
    // Not even room for the row: chip above sum again, right-aligned, after
    // (and so over) the row rule.
    const stacked = css.match(/\.wallets\.groups-stacked \.group \.gright\s*\{([^}]*)\}/);
    expect(stacked?.[1]).toMatch(/flex-direction:\s*column/);
    expect(stacked?.[1]).toMatch(/align-items:\s*flex-end/);
    expect(css.indexOf(".wallets.groups-stacked .group .gright")).toBeGreaterThan(css.indexOf(".wallets.groups-wrapped .group .gright"));
    // Wrapped, name and count keep their own width (cut only when even a
    // line of their own is too narrow): grown to the line, they would be
    // measured as never fitting again, and the groups would stay wrapped.
    expect(css.match(/\.wallets\.groups-wrapped \.group \.gleft\s*\{([^}]*)\}/)?.[1]).not.toMatch(/flex:\s*1|flex-grow:\s*1/);
    expect(css.match(/\.wallets\.groups-wrapped \.group \.gleft\s*\{([^}]*)\}/)?.[1]).toMatch(/max-width:\s*100%/);
  });
});

describe("a wallet row's chip and value", () => {
  it("stand beside the units, below the name side by side, or below it stacked: the same in every row", async () => {
    const room = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(300);
    const rect = vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      const width = this.classList.contains("wchip") ? 80 : this.classList.contains("val") ? 70 : 0;
      return { width, height: 0, x: 0, y: 0, top: 0, left: 0, right: width, bottom: 0, toJSON: () => ({}) } as DOMRect;
    });
    // The units may wrap: their lines add up to what they need on one line,
    // in every layout alike.
    const lines = vi.spyOn(Element.prototype, "getClientRects").mockImplementation(function (this: Element) {
      const widths = this.classList.contains("units") ? [90, 40] : [];
      return widths.map((width) => ({ width }) as DOMRect) as unknown as DOMRectList;
    });
    const layout = (card: PortfolioCard) => {
      const wallets = one(card, ".wallets")?.classList;
      return [wallets?.contains("rows-wrapped"), wallets?.contains("rows-stacked")];
    };
    const resize = async (card: PortfolioCard, width: number) => {
      room.mockReturnValue(width);
      card.requestUpdate();
      await card.updateComplete;
    };
    try {
      const card = await mount({ group_wallets: false });
      // 130 units + 12 + 80 (the wider of chip and value) = 222.
      await vi.waitFor(() => expect(layout(card)).toEqual([false, false]));
      await resize(card, 221);
      // 80 chip + 8 + 70 value = 158, in the row's width plus the 30 px
      // under the chevron.
      await vi.waitFor(() => expect(layout(card)).toEqual([true, false]));
      await resize(card, 128);
      await vi.waitFor(() => expect(layout(card)).toEqual([true, false]));
      await resize(card, 127);
      await vi.waitFor(() => expect(layout(card)).toEqual([true, true]));
      await resize(card, 300);
      await vi.waitFor(() => expect(layout(card)).toEqual([false, false]));
    } finally {
      room.mockRestore();
      rect.mockRestore();
      lines.mockRestore();
    }
  });
});
describe("a wallet row below its name", () => {
  it("reaches under the chevron, to where a group's sum ends", async () => {
    // Vision at 216 px in an open group: 128 px beside the chevron, 158 px
    // with the room under it.
    const room = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockImplementation(function (this: HTMLElement) {
      return this.classList.contains("wallet") ? 158 : 128;
    });
    const rect = vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      const width = this.classList.contains("wchip") ? 72.5 : this.classList.contains("val") ? 53.4 : 0;
      return { width, height: 0, x: 0, y: 0, top: 0, left: 0, right: width, bottom: 0, toJSON: () => ({}) } as DOMRect;
    });
    const lines = vi.spyOn(Element.prototype, "getClientRects").mockImplementation(function (this: Element) {
      return (this.classList.contains("units") ? [{ width: 92.4 } as DOMRect] : []) as unknown as DOMRectList;
    });
    try {
      const card = await mount({ group_wallets: false });
      await vi.waitFor(() => expect(one(card, ".wallets")?.classList.contains("rows-wrapped")).toBe(true));
      expect(one(card, ".wallets")?.classList.contains("rows-stacked")).toBe(false);
    } finally {
      room.mockRestore();
      rect.mockRestore();
      lines.mockRestore();
    }
    // In an open group a row is indented by its own padding, which its
    // width counts: the room under the chevron is the row's beside it plus
    // the chevron's, never the whole row's.
    const indented = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockImplementation(function (this: HTMLElement) {
      return this.classList.contains("wallet") ? 182 : 128;
    });
    const wide = vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      const width = this.classList.contains("wchip") ? 72.5 : this.classList.contains("val") ? 80 : 0;
      return { width, height: 0, x: 0, y: 0, top: 0, left: 0, right: width, bottom: 0, toJSON: () => ({}) } as DOMRect;
    });
    const units = vi.spyOn(Element.prototype, "getClientRects").mockImplementation(function (this: Element) {
      return (this.classList.contains("units") ? [{ width: 92.4 } as DOMRect] : []) as unknown as DOMRectList;
    });
    try {
      const card = await mount({ group_wallets: false });
      // 72.5 + 8 + 80 = 160.5: more than 128 + 30, less than 182.
      await vi.waitFor(() => expect(one(card, ".wallets")?.classList.contains("rows-wrapped")).toBe(true));
      expect(one(card, ".wallets")?.classList.contains("rows-stacked")).toBe(true);
    } finally {
      indented.mockRestore();
      wide.mockRestore();
      units.mockRestore();
    }
    // The CSS lets the row out by the chevron's width and the gap before it.
    const css = (await import("../src/styles")).cardStyles.cssText;
    const chevron = Number(css.match(/\.chevron\s*\{[^}]*width:\s*(\d+)px/)?.[1]);
    const gap = Number(css.match(/\.wallet\s*\{[^}]*gap:\s*(\d+)px/)?.[1]);
    // As wide as the row plus that, so that its right edge is the card's.
    const below = css.match(/\.wallets\.rows-wrapped \.wallet \.right\s*\{([^}]*)\}/)?.[1];
    expect(below).toMatch(new RegExp(`flex-basis:\\s*calc\\(100% \\+ ${chevron + gap}px\\)`));
    expect(below).toMatch(new RegExp(`margin-right:\\s*-${chevron + gap}px`));
  });
});
describe("the dividers", () => {
  // What follows each divider: a part's first element.
  const after = (card: PortfolioCard): string[] =>
    all(card, ".content > .divider").map((divider) => divider.nextElementSibling?.classList[0] ?? "");

  it("stand once before each shown part after the total: cash and allocation as one, then the wallets", async () => {
    expect(after(await mount())).toEqual(["pair", "wallets"]);
    expect(after(await mount({ group_wallets: false }))).toEqual(["pair", "wallets"]);
    expect(after(await mount({ show_cash: false }))).toEqual(["bar", "wallets"]);
    expect(after(await mount({ show_graph: false, show_cash: false }))).toEqual(["bar", "wallets"]);
    expect(after(await mount({ show_graph: false, show_cash: false, show_allocation: false }))).toEqual(["wallets"]);
    expect(after(await mount({ show_wallets: false }))).toEqual(["pair"]);
    expect(after(await mount({ show_cash: false, show_allocation: false, show_wallets: false }))).toEqual([]);
  });

  it("leave no line at the top when neither the total nor its line is shown", async () => {
    const first = (card: PortfolioCard): string => one(card, ".content")?.firstElementChild?.classList[0] ?? "";
    const top = { show_total: false, show_graph: false };
    expect(first(await mount(top))).toBe("pair");
    expect(after(await mount(top))).toEqual(["wallets"]);
    // Only the wallets with their search field: the field comes first.
    expect(first(await mount({ ...top, show_cash: false, show_allocation: false, show_search: true }))).toBe("search");
    expect(after(await mount({ ...top, show_cash: false, show_allocation: false, show_search: true }))).toEqual([]);
  });

  it("stand before the hint when there are no wallets", async () => {
    expect(after(await mount({}, makeHass({ devices: [portfolioDevice()] })))).toEqual(["pair", "empty"]);
  });

  it("are the only lines between parts: none of the cash row's own, none above the first group", async () => {
    const css = (await import("../src/styles")).cardStyles.cssText;
    expect(css.match(/\.pair\s*\{([^}]*)\}/)?.[1]).not.toMatch(/border-top/);
    const first = css.match(/\.wallets > \.group:first-child\s*\{([^}]*)\}/)?.[1];
    expect(first).toMatch(/border-top:\s*none/);
    expect(first).toMatch(/margin-top:\s*0/);
  });
});
describe("the wallet search", () => {
  const names = (card: PortfolioCard): string[] => all(card, ".wallet .n").map((name) => textOf(name));
  const type = async (card: PortfolioCard, text: string): Promise<void> => {
    const input = one(card, ".search input") as HTMLInputElement;
    input.value = text;
    input.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
    await card.updateComplete;
  };

  it("is off unless chosen, and only there with wallets to search", async () => {
    expect(one(await mount(), ".search")).toBeNull();
    expect(one(await mount({ show_search: true, show_wallets: false }), ".search")).toBeNull();
    expect(one(await mount({ show_search: true }, makeHass({ devices: [portfolioDevice()] })), ".search")).toBeNull();
    const card = await mount({ show_search: true });
    const input = one(card, ".search input");
    expect(input?.getAttribute("placeholder")).toBe("Name, symbol or ISIN");
    expect(input?.getAttribute("aria-label")).toBe("Search wallets");
    expect(one(card, ".search")?.getAttribute("role")).toBe("search");
    // Right below the divider before the wallets, with nothing to clear yet.
    expect(one(card, ".divider + .search")).not.toBeNull();
    expect(one(card, ".search .clear")).toBeNull();
    expect(all(card, ".group")).toHaveLength(3);
  });

  it("finds wallets by name, symbol or ISIN, in any case, as one list without groups", async () => {
    const card = await mount({ show_search: true, sort: "name" });
    await type(card, "ETHER");
    expect(names(card)).toEqual(["Ethereum"]);
    await type(card, " btc ");
    expect(names(card)).toEqual(["Bitcoin"]);
    await type(card, "ie00b4");
    expect(names(card)).toEqual(["iShares Core MSCI World UCITS ETF"]);
    await type(card, "o");
    expect(names(card)).toEqual(["Bitcoin", "Gold", "iShares Core MSCI World UCITS ETF"]);
    expect(all(card, ".group")).toHaveLength(0);
    // Word by word, in any order.
    await type(card, "world ishares");
    expect(names(card)).toEqual(["iShares Core MSCI World UCITS ETF"]);
  });

  it("shows every match, past the limit, and only among the assets the card shows", async () => {
    const flat = await mount({ show_search: true, group_wallets: false, limit: 1, sort: "name" });
    await type(flat, "o");
    expect(names(flat)).toEqual(["Bitcoin", "Gold", "iShares Core MSCI World UCITS ETF"]);
    expect(one(flat, ".show-all")).toBeNull();
    const picked = await mount({ show_search: true, sort: "name", asset_selection: "only", assets: ["dev-wallet-btc", "dev-wallet-xau"] });
    await type(picked, "o");
    expect(names(picked)).toEqual(["Bitcoin", "Gold"]);
  });

  it("says so when nothing matches", async () => {
    const card = await mount({ show_search: true });
    await type(card, "  xyz ");
    expect(names(card)).toEqual([]);
    expect(textOf(one(card, ".search-none"))).toBe("No wallet matches “xyz”.");
  });

  it("clears with the cross, which brings the groups back", async () => {
    const card = await mount({ show_search: true });
    await type(card, "btc");
    const clear = one(card, ".search .clear");
    expect(clear?.getAttribute("role")).toBe("button");
    expect(clear?.getAttribute("aria-label")).toBe("Clear search");
    clear?.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    await card.updateComplete;
    expect((one(card, ".search input") as HTMLInputElement).value).toBe("");
    expect(all(card, ".group")).toHaveLength(3);
    expect(one(card, ".search .clear")).toBeNull();
    // Ready for the next search: the field has the focus again.
    expect(card.shadowRoot?.activeElement).toBe(one(card, ".search input"));
    await type(card, "eth");
    one(card, ".search .clear")?.click();
    await card.updateComplete;
    expect(card.shadowRoot?.activeElement).toBe(one(card, ".search input"));
  });

  it("keeps its field while typing, so it keeps the focus", async () => {
    const card = await mount({ show_search: true });
    const input = one(card, ".search input");
    await type(card, "b");
    await type(card, "xyz");
    await type(card, "");
    expect(one(card, ".search input")).toBe(input);
  });
});
describe("the line's middle and cursor", () => {
  // The line's box: 480 px wide from the left edge.
  const box = () =>
    vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      const width = this.classList.contains("plot") ? 480 : 0;
      return { width, height: 0, x: 0, y: 0, top: 0, left: 0, right: width, bottom: 0, toJSON: () => ({}) } as DOMRect;
    });
  const point = async (card: PortfolioCard, type: string, fraction: number, pointerType = "mouse"): Promise<void> => {
    one(card, ".plot")?.dispatchEvent(new PointerEvent(type, { clientX: fraction * 480, pointerType, bubbles: true }));
    await card.updateComplete;
  };
  const shown = (card: PortfolioCard) => ({
    tags: all(card, ".plot .tag").map((tag) => textOf(tag)),
    tip: textOf(one(card, ".plot .tip")),
    cursor: one(card, ".plot .cursor") !== null,
  });

  it("draws a dashed middle line, and nothing more until pointed at", async () => {
    const card = await mount();
    await settled(card);
    expect(one(card, ".plot > svg.spark")).not.toBeNull();
    expect(one(card, ".plot .mid")).not.toBeNull();
    expect(shown(card)).toEqual({ tags: [], tip: "", cursor: false });
    const css = (await import("../src/styles")).cardStyles.cssText;
    expect(css.match(/\.plot \.mid\s*\{([^}]*)\}/)?.[1]).toMatch(/border-top:\s*1px dashed/);
    expect(css.match(/\.plot \.mid\s*\{([^}]*)\}/)?.[1]).toMatch(/top:\s*50%/);
    // A finger moving up or down still scrolls the page.
    expect(css.match(/\.plot\s*\{([^}]*)\}/)?.[1]).toMatch(/touch-action:\s*pan-y/);
  });

  it("pointed at, shows high, middle and low, and the nearest point's time and value above a cursor", async () => {
    const rect = box();
    try {
      const card = await mount({ timeframe: "day" });
      await settled(card);
      await point(card, "pointermove", 0.97);
      expect(shown(card).tags).toEqual(["€12,760.20", "€12,380.10", "€12,000.00"]);
      expect(shown(card).tip).toMatch(/^.+\d:\d\d.* · €12,760\.20$/);
      // The dot on the line: the highest value 2 of 72 units below the top.
      expect(one(card, ".plot .dot")?.getAttribute("style")).toContain("top:2.78%");
      // Near the right edge the label ends at the cursor.
      expect(one(card, ".plot .tip")?.classList.contains("end")).toBe(true);
      await point(card, "pointermove", 0.02);
      expect(shown(card).tip).toMatch(/ · €12,000\.00$/);
      expect(one(card, ".plot .dot")?.getAttribute("style")).toContain("top:97.22%");
      expect(one(card, ".plot .tip")?.classList.contains("start")).toBe(true);
      await point(card, "pointerleave", 0.5);
      expect(shown(card)).toEqual({ tags: [], tip: "", cursor: false });
    } finally {
      rect.mockRestore();
    }
  });

  it("from a month on names the day without the time", async () => {
    const rect = box();
    try {
      const card = await mount({ timeframe: "month" });
      await settled(card);
      await point(card, "pointermove", 0.5);
      expect(shown(card).tip).toMatch(/^[^:]+ · €12,400\.00$/);
    } finally {
      rect.mockRestore();
    }
  });

  it("with amounts hidden shows the time alone, without high, middle and low", async () => {
    const rect = box();
    try {
      const card = await mount({ timeframe: "day", hide_amounts: true });
      await settled(card);
      await point(card, "pointermove", 0.5);
      expect(shown(card).tags).toEqual([]);
      expect(shown(card).cursor).toBe(true);
      expect(shown(card).tip).not.toContain("€");
    } finally {
      rect.mockRestore();
    }
  });

  it("follows a finger and goes when it lifts or the page scrolls", async () => {
    const rect = box();
    try {
      const card = await mount();
      await settled(card);
      await point(card, "pointerdown", 0.5, "touch");
      expect(shown(card).cursor).toBe(true);
      await point(card, "pointerup", 0.5, "touch");
      expect(shown(card).cursor).toBe(false);
      await point(card, "pointerdown", 0.5, "touch");
      await point(card, "pointercancel", 0.5, "touch");
      expect(shown(card).cursor).toBe(false);
      // A mouse button let go leaves the cursor where the mouse still is.
      await point(card, "pointermove", 0.5);
      await point(card, "pointerup", 0.5);
      expect(shown(card).cursor).toBe(true);
    } finally {
      rect.mockRestore();
    }
  });

  it("measures nothing anew while only the cursor moves", async () => {
    const rect = box();
    try {
      const card = await mount();
      await settled(card);
      const fit = vi.spyOn(card as unknown as { fitLayout(): void }, "fitLayout");
      await point(card, "pointermove", 0.3);
      await point(card, "pointermove", 0.7);
      expect(shown(card).cursor).toBe(true);
      expect(fit).not.toHaveBeenCalled();
      // Anything else still measures: a group opened, say.
      one(card, ".group")?.click();
      await card.updateComplete;
      expect(fit).toHaveBeenCalled();
    } finally {
      rect.mockRestore();
    }
  });

  it("leaves a history too short to draw without a middle and without a cursor", async () => {
    const rect = box();
    try {
      const recent = Date.now() - 2 * HOUR;
      const hass = makeHass({ devices: [portfolioDevice()], callWS: async () => ({ points: [[recent, 1], [recent + HOUR, 2]] }) });
      const card = await mount({ timeframe: "week" }, hass);
      await vi.waitFor(() => expect(one(card, ".plot svg.spark")).not.toBeNull());
      await point(card, "pointermove", 0.99);
      expect(one(card, ".plot .mid")).toBeNull();
      expect(shown(card)).toEqual({ tags: [], tip: "", cursor: false });
    } finally {
      rect.mockRestore();
    }
  });

  it("starts afresh with another timeframe", async () => {
    const rect = box();
    try {
      const card = await mount();
      await settled(card);
      await point(card, "pointermove", 0.5);
      expect(shown(card).cursor).toBe(true);
      (all(card, ".seg [role=radio]")[1] as HTMLElement).click();
      await card.updateComplete;
      // Once the new timeframe's line is there, no cursor stands on it.
      await vi.waitFor(() => expect(one(card, ".plot .mid")).not.toBeNull());
      expect(shown(card).cursor).toBe(false);
    } finally {
      rect.mockRestore();
    }
  });
});