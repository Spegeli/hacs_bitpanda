import { afterEach, describe, expect, it, vi } from "vitest";

import { PortfolioCard, allocationShare, blockLayout, groupReturn } from "../src/portfolio-card";
import { windowFor } from "../src/statistics";
import type { Timeframe } from "../src/types";
import { BTC, ETH, EUNL, XAU, makeHass, openEditor, portfolioDevice, walletDevice, type FakeHass, type FakeWallet } from "./fixtures";

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

/** The value cells of an opened wallet's detail, both grids. */
function valueCells(card: PortfolioCard): HTMLElement[] {
  return all(card, ".detail .grid > span:nth-child(even)");
}

/** The rows of the staking block, "label value". */
function stakingRows(card: PortfolioCard): string[] {
  const cells = [...(all(card, ".detail .grid")[1]?.querySelectorAll(":scope > span") ?? [])].map((cell) => textOf(cell as HTMLElement));
  return cells.filter((_, index) => index % 2 === 0).map((label, index) => `${label} ${cells[index * 2 + 1] ?? ""}`);
}

// Ethereum's price and its 24 hours on Balance (total).
const ETH_DAY: Partial<FakeWallet> = { price: 2309.09, return24h: -12.5, change24h: -1.62 };

/** A card of `wallet` alone, in one list, the wallet opened. */
async function openWallet(wallet: FakeWallet, config: Record<string, unknown> = {}, language?: string): Promise<PortfolioCard> {
  const card = await mount({ group_wallets: false, ...config }, makeHass({ devices: [portfolioDevice(), walletDevice(wallet)], ...(language ? { language } : {}) }));
  (one(card, ".wallet .chevron") as HTMLElement | null)?.click();
  await card.updateComplete;
  return card;
}

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

  it("re-renders when the invested amount or the total return changes", async () => {
    const card = await mount();
    const watched = (card as unknown as { watchedEntities(): string[] }).watchedEntities();
    expect(watched).toEqual(
      expect.arrayContaining([
        "sensor.bitpanda_portfolio_invested",
        "sensor.bitpanda_portfolio_total_return",
        "sensor.bitpanda_portfolio_total_return_percent",
      ]),
    );
  });

  it("shows the return sensor's return_amount beside the chip", async () => {
    // Not what the card would reckon from the total: the sensor's own figure.
    const hass = portfolioHass();
    const day = "sensor.bitpanda_portfolio_return_day";
    const card = await mount({}, hass.withState(day, "-0.42", { unit_of_measurement: "%", return_amount: -61.5 }));
    expect(textOf(one(card, ".chip-amount"))).toBe("-€61.50");
  });

  it("shows no amount without the return sensor's return_amount", async () => {
    const day = "sensor.bitpanda_portfolio_return_day";
    const card = await mount({}, portfolioHass().withState(day, "-0.42", { unit_of_measurement: "%" }));
    expect(one(card, ".chip-amount")).toBeNull();
    expect(textOf(one(card, ".chip"))).toBe("▼ -0.42%");
  });

  it("takes the amount's currency from invested or a wallet when Total value is not found", async () => {
    const withoutTotal = (devices: ReturnType<typeof portfolioDevice>[]) => {
      const [portfolio, ...rest] = devices as [ReturnType<typeof portfolioDevice>, ...ReturnType<typeof portfolioDevice>[]];
      portfolio.sensors = portfolio.sensors.filter((sensor) => sensor.translationKey !== "total_value");
      return makeHass({ devices: [portfolio, ...rest] });
    };
    const fromInvested = await mount({}, withoutTotal([portfolioDevice({ currency: "USD" })]));
    expect(textOf(one(fromInvested, ".chip-amount"))).toBe("-$53.82");
    const fromWallet = await mount({}, withoutTotal([portfolioDevice({ invested: null }), walletDevice({ ...BTC, currency: "CHF" })]));
    expect(textOf(one(fromWallet, ".chip-amount"))).toMatch(/^-CHF\s?53\.82$/);
    const none = await mount({}, withoutTotal([portfolioDevice({ invested: null })]));
    expect(one(none, ".chip-amount")).toBeNull();
  });

  it("shows the return since purchase under the return row, without the invested amount", async () => {
    const card = await mount();
    const since = one(card, ".since");
    expect(textOf(since)).toBe("Since purchase ▲ +14.10% +€3,700.00");
    expect(one(card, ".since-invested")).toBeNull();
    expect(one(card, ".since-chip")?.classList.contains("up")).toBe(true);
    expect(one(card, ".since-amount")?.classList.contains("up")).toBe(true);
    // Under the return row: after it in the card.
    const order = all(card, ".hero-line, .since").map((element) => element.className.split(" ")[0]);
    expect(order).toEqual(["hero-line", "since"]);
  });

  it("colours a loss since purchase as a loss", async () => {
    const card = await mount({}, makeHass({ devices: [portfolioDevice({ totalReturn: "-500.00", totalReturnPercent: "-1.86" })] }));
    expect(textOf(one(card, ".since"))).toBe("Since purchase ▼ -1.86% -€500.00");
    expect(one(card, ".since-amount")?.classList.contains("down")).toBe(true);
  });

  it("shows a dash for a part of the since-purchase line whose sensor is missing or has no value", async () => {
    const noPercent = await mount({}, makeHass({ devices: [portfolioDevice({ totalReturnPercent: null })] }));
    expect(textOf(one(noPercent, ".since"))).toBe("Since purchase — +€3,700.00");
    expect(one(noPercent, ".since-chip")?.classList.contains("none")).toBe(true);
    const unknown = makeHass({ devices: [portfolioDevice({ invested: null })] }).withState("sensor.bitpanda_portfolio_total_return", "unknown", {});
    const noAmounts = await mount({}, unknown);
    expect(textOf(one(noAmounts, ".since"))).toBe("Since purchase ▲ +14.10% —");
  });

  it("leaves the since-purchase line out without both its sensors, Invested found or not", async () => {
    const card = await mount({}, makeHass({ devices: [portfolioDevice({ totalReturn: null, totalReturnPercent: null })] }));
    expect(one(card, ".since")).toBeNull();
  });

  it("leaves the since-purchase line out when switched off, or without the total value", async () => {
    expect(one(await mount({ show_since_purchase: false }), ".since")).toBeNull();
    expect(one(await mount({ show_total: false }), ".since")).toBeNull();
  });

  it("breaks the since-purchase line after its label, never inside a figure", async () => {
    // Label, chip and amount in one piece are wider than a 240 px card.
    const card = await mount();
    expect(all(card, ".since > .part").map((part) => textOf(part))).toEqual(["Since purchase", "▲ +14.10% +€3,700.00"]);
    const css = (await import("../src/styles")).cardStyles.cssText;
    expect(css).toMatch(/\.since \.part\s*\{[^}]*white-space:\s*nowrap/);
  });

  it("the since-purchase chip opens Total return %, its amount Total return", async () => {
    const card = await mount();
    const opened: string[] = [];
    card.addEventListener("hass-more-info", (event) => opened.push((event as CustomEvent).detail.entityId));
    for (const selector of [".since-chip", ".since-amount"]) one(card, selector)?.click();
    one(card, ".since-chip")?.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    expect(opened).toEqual([
      "sensor.bitpanda_portfolio_total_return_percent",
      "sensor.bitpanda_portfolio_total_return",
      "sensor.bitpanda_portfolio_total_return_percent",
    ]);
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
    expect(legend).toEqual(["crypto 59.25%", "etf 16.92%", "Cash Plus 16.55%", "Cash 6.72%", "metal <1%"]);
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

  it("the wallet detail lists price, average buy price, invested, 24-hour and total return, then staking", async () => {
    const card = await openWallet({ ...ETH, ...ETH_DAY });
    const rows = detailRows(card);
    expect(rows.slice(0, 5)).toEqual([
      "Current price €2,309.09",
      "Average buy price €2,377.00",
      "Invested €1,307.35",
      "Return (24 h) -€12.50 (-1.62%)",
      "Total return -€37.44 (-3.10%)",
    ]);
    expect(textOf(one(card, ".detail h4"))).toBe("Staking");
    expect(rows.slice(5, 9)).toEqual([
      "Staked 0.22 ETH · 507.91 EUR",
      "Staking APR 2.9%",
      "Earned (30 days) 0.00061234 ETH · €1.41",
      "Earned (total) 0.0041 ETH · €9.47",
    ]);
    expect(rows[9]).toMatch(/^Payouts 12 · last .+/);
    expect(rows).toHaveLength(10);
    // A value breaks only between its parts, after the middle dot, which
    // stays with the part before it.
    const staked = valueCells(card)[5]!;
    expect(staked.textContent).toContain(" · ");
    const parts = (index: number): string[] => [...valueCells(card)[index]!.querySelectorAll(".part")].map((part) => textOf(part));
    expect(parts(5)).toEqual(["0.22 ETH", "507.91 EUR"]);
    expect(parts(8)).toEqual(["0.0041 ETH", "€9.47"]);
    expect(parts(9)[0]).toBe("12");
    expect(parts(9)[1]).toMatch(/^last .+/);
    expect(parts(3)).toEqual(["-€12.50", "(-1.62%)"]);
    expect(parts(4)).toEqual(["-€37.44", "(-3.10%)"]);
    expect(valueCells(card)[3]?.className).toContain("down");
  });

  it("keeps the staking rows with nothing staked", async () => {
    const card = await openWallet({ ...ETH, staked: { ...ETH.staked!, units: 0, value: "0" } });
    const rows = stakingRows(card);
    expect(rows[0]).toMatch(/^Staked 0 ETH · /);
    expect(rows.slice(1, 4)).toEqual(["Staking APR 2.9%", "Earned (30 days) 0.00061234 ETH · €1.41", "Earned (total) 0.0041 ETH · €9.47"]);
    expect(rows[4]).toMatch(/^Payouts 12 · last .+/);
  });

  /** ETH without one of its rewards' attributes. */
  const ethWithout = (key: "net30d" | "netValue30d" | "netValue"): FakeWallet => {
    const rewards = { ...ETH.staked!.rewards! };
    delete rewards[key];
    return { ...ETH, staked: { ...ETH.staked!, rewards } };
  };
  /** The value cell of the staking block's row `index`. */
  const stakingCell = (card: PortfolioCard, index: number): HTMLElement =>
    all(card, ".detail .grid")[1]!.querySelectorAll(":scope > span")[index * 2 + 1] as HTMLElement;

  it("shows what was earned in the last 30 days before what was earned in all", async () => {
    const card = await openWallet(ETH);
    expect(stakingRows(card).slice(1, 4)).toEqual(["Staking APR 2.9%", "Earned (30 days) 0.00061234 ETH · €1.41", "Earned (total) 0.0041 ETH · €9.47"]);
    // It breaks only at its middle dot.
    expect([...stakingCell(card, 2).querySelectorAll(".part")].map((part) => textOf(part as HTMLElement))).toEqual(["0.00061234 ETH", "€1.41"]);
  });

  it("shows a dash for the value of the last 30 days without it", async () => {
    const card = await openWallet(ethWithout("netValue30d"));
    expect(stakingRows(card)[2]).toBe("Earned (30 days) 0.00061234 ETH · —");
  });

  it("leaves the row of the last 30 days out without their rewards", async () => {
    const card = await openWallet(ethWithout("net30d"));
    expect(stakingRows(card).some((row) => row.startsWith("Earned (30 days)"))).toBe(false);
    expect(stakingRows(card)[2]).toBe("Earned (total) 0.0041 ETH · €9.47");
  });

  it("shows a dash for the value of what was earned in all without it", async () => {
    const card = await openWallet(ethWithout("netValue"));
    expect(stakingRows(card)[3]).toBe("Earned (total) 0.0041 ETH · —");
  });

  it("hides the units and the values earned behind the eye", async () => {
    const card = await openWallet(ETH, { hide_amounts: true });
    for (const index of [2, 3]) {
      expect(stakingCell(card, index).querySelectorAll(".amount.blur")).toHaveLength(2);
      expect(textOf(stakingCell(card, index))).toContain(" · ");
    }
  });

  it("a wallet never staked shows staked and the APR only", async () => {
    const card = await openWallet({ ...ETH, staked: { units: 0, value: "0", apr: 6.2 } });
    expect(textOf(one(card, ".detail h4"))).toBe("Staking");
    const rows = stakingRows(card);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatch(/^Staked 0 ETH · /);
    expect(rows[1]).toBe("Staking APR 6.2%");
  });

  it("leaves the 24-hour row out without its attributes", async () => {
    const card = await openWallet({ ...ETH, price: 2309.09 });
    expect(detailRows(card).slice(0, 4)).toEqual([
      "Current price €2,309.09",
      "Average buy price €2,377.00",
      "Invested €1,307.35",
      "Total return -€37.44 (-3.10%)",
    ]);
  });

  it("the eye blurs the 24-hour amount and the rewards, never the price or a percentage", async () => {
    const card = await openWallet({ ...ETH, ...ETH_DAY }, { hide_amounts: true });
    const cells = valueCells(card);
    expect(cells[0]?.querySelector(".blur")).toBeNull();
    expect(textOf(cells[0])).toBe("€2,309.09");
    expect(cells[3]?.querySelector(".amount")?.classList.contains("blur")).toBe(true);
    expect(textOf(cells[3])).toContain("(-1.62%)");
    expect(cells[6]?.querySelector(".blur")).toBeNull();
    expect(cells[7]?.querySelectorAll(".amount.blur")).toHaveLength(2);
    expect(cells[8]?.querySelectorAll(".amount.blur")).toHaveLength(2);
  });

  it("names the detail rows in German", async () => {
    const card = await openWallet({ ...ETH, ...ETH_DAY }, {}, "de");
    const labels = all(card, ".detail .grid > span:nth-child(odd)").map((cell) => textOf(cell));
    expect(labels).toEqual([
      "Aktueller Preis", "Ø Kaufpreis", "Investiert", "Rendite (24 h)", "Gesamtrendite",
      "Im Staking", "Staking-APR", "Verdient (30 Tage)", "Verdient (gesamt)", "Gutschriften",
    ]);
    expect(textOf(one(card, ".detail h4"))).toBe("Staking");
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

  it("no staking block without a staking sensor", async () => {
    const card = await mount({ group_wallets: false });
    const btc = all(card, ".wallet").find((row) => textOf(row.querySelector(".n")) === "Bitcoin");
    (btc?.querySelector(".chevron") as HTMLElement | null)?.click();
    await card.updateComplete;
    expect(one(card, ".detail h4")).toBeNull();
    expect(all(card, ".detail .grid")).toHaveLength(1);
    expect(detailRows(card)).toEqual([
      "Current price —",
      "Average buy price €80,200.00",
      "Invested €5,240.00",
      "Total return +€650.11 (+12.40%)",
    ]);
    expect(textOf(one(card, ".detail"))).not.toContain("Available");
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

  it("shows invested, the total return and the rewards' value in cents, prices in full", async () => {
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
    expect(rows.slice(1, 4)).toEqual(["Average buy price €0.36012", "Invested €4.32", "Total return -€0.12 (-2.86%)"]);
    expect(rows).toContain("Earned (total) 0.05 ADA · €0.02");
  });

  it("makes no button of a part whose sensor is not found", async () => {
    const portfolio = portfolioDevice({ totalReturnPercent: null });
    portfolio.sensors = portfolio.sensors.filter((sensor) => !["total_value", "cash_plus"].includes(sensor.translationKey));
    const card = await mount({}, makeHass({ devices: [portfolio] }));
    for (const selector of [".hero", ".pair > .end", ".since-chip"]) {
      expect(one(card, selector)?.getAttribute("role"), selector).toBeNull();
      expect(one(card, selector)?.getAttribute("tabindex"), selector).toBeNull();
    }
    // Its neighbours, found, stay buttons.
    expect(one(card, ".pair > div:not(.end)")?.getAttribute("role")).toBe("button");
    expect(one(card, ".since-amount")?.getAttribute("role")).toBe("button");
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

  it("opens a wallet whose Balance (total) is disabled without NaN", async () => {
    const eth = walletDevice({ ...ETH, ...ETH_DAY });
    eth.sensors = eth.sensors.filter((sensor) => sensor.translationKey !== "wallet_total");
    const card = await mount({ group_wallets: false }, makeHass({ devices: [portfolioDevice(), eth] }));
    all(card, ".chevron").forEach((chevron) => chevron.click());
    await card.updateComplete;
    expect(root(card).textContent ?? "").not.toMatch(/NaN|undefined|null|Invalid/);
    expect(detailRows(card)[0]).toBe("Current price —");
    expect(detailRows(card).some((row) => row.startsWith("Return (24 h)"))).toBe(false);
  });

  it("no portfolio asks to set it up or enable it, without the eye", async () => {
    const german = await mount({}, makeHass({ language: "de" }));
    expect(textOf(one(german, ".empty"))).toBe("Richte das Bitpanda Portfolio ein oder aktiviere es, dann erscheint es hier.");
    const card = await mount({}, makeHass());
    expect(textOf(one(card, ".empty"))).toBe("Set up the Bitpanda Portfolio or enable it to see it here.");
    // Nothing to hide: no eye.
    expect(one(card, ".eye")).toBeNull();
  });

  it("no wallets says so", async () => {
    const card = await mount({}, makeHass({ devices: [portfolioDevice()] }));
    expect(textOf(one(card, ".empty"))).toBe("No wallets yet.");
  });

  it("the editor form lists exactly the card's options", async () => {
    const names = (fields: { name: string; type?: string; schema?: { name: string; type?: string }[] }[]): string[] =>
      fields.flatMap((field) => (field.schema ? names(field.schema) : field.type === "divider" ? [] : [field.name]));
    // Every field: the groups and assets to choose show while some are chosen.
    const { form } = await openEditor("bitpanda-portfolio-card", { group_selection: "only", asset_selection: "only" });
    expect(names(form.schema).sort()).toEqual(
      ["asset_selection", "assets", "group_selection", "group_wallets", "groups", "hide_amounts", "limit", "show_allocation", "show_cash", "show_graph", "show_header", "show_search", "show_since_purchase", "show_staking", "show_timeframes", "show_total", "show_wallets", "sort", "timeframe", "title"].sort(),
    );
    expect(form.computeLabel({ name: "show_cash" })).toBe("Cash and Cash Plus");
    // The title on top, then Content, Wallets and Appearance.
    expect(form.schema.map((field) => (field as { name?: string; title?: string }).title ?? (field as { name: string }).name)).toEqual([
      "title", "Content", "Wallets", "Appearance",
    ]);
    // Content: what the card shows, the total and its return first.
    const content = form.schema.find((field) => (field as { title?: string }).title === "Content") as unknown as { schema: { name: string }[] };
    expect(content.schema.map((field) => field.name)).toEqual(["show_total", "show_since_purchase", "show_graph", "show_cash", "show_staking", "show_allocation", "show_wallets"]);
    // The line since purchase: right under the total, on unless chosen.
    expect((content.schema as { name: string; default?: unknown }[]).find((field) => field.name === "show_since_purchase")?.default).toBe(true);
    expect(form.computeLabel({ name: "show_since_purchase" })).toBe("Return since purchase");
    expect(form.computeHelper({ name: "show_since_purchase" })).toBe("Only with the total value and its return");
    expect(form.computeLabel({ name: "show_total" })).toBe("Total value and return");
    expect(form.computeHelper({ name: "show_total" })).toBe("The timeframe buttons stay while the line is shown, unless “Appearance” hides them");
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
    const { form } = await openEditor("bitpanda-portfolio-card");
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

describe("allocationShare", () => {
  it("reads a share from 1 % up with two decimals and one under 1 % as <1 %, as Bitpanda's app does", () => {
    const en = makeHass();
    expect(allocationShare(en, 99.76)).toBe("99.76%");
    expect(allocationShare(en, 99.997)).toBe("100.00%");
    expect(allocationShare(en, 100)).toBe("100.00%");
    expect(allocationShare(en, 1)).toBe("1.00%");
    expect(allocationShare(en, 0.999)).toBe("<1%");
    const de = makeHass({ language: "de" });
    expect(allocationShare(de, 99.76)).toBe("99,76 %");
    expect(allocationShare(de, 0.2)).toBe("<1 %");
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
  it("are measured in layout pixels, units included, while a dialog shows the card scaled down", async () => {
    // As the Price Tracker's columns: Home Assistant's card dialog scales
    // the card in, and the units' line boxes are screen pixels too.
    const scale = 0.9;
    const room = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(221);
    const layoutWidth = vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockImplementation(function (this: HTMLElement) {
      return this.tagName === "BITPANDA-PORTFOLIO-CARD" ? 400 : 0;
    });
    const rect = vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      const own = this.tagName === "BITPANDA-PORTFOLIO-CARD" ? 400 : this.classList.contains("wchip") ? 80 : this.classList.contains("val") ? 70 : 0;
      const width = own * scale;
      return { width, height: 0, x: 0, y: 0, top: 0, left: 0, right: width, bottom: 0, toJSON: () => ({}) } as DOMRect;
    });
    const lines = vi.spyOn(Element.prototype, "getClientRects").mockImplementation(function (this: Element) {
      const widths = this.classList.contains("units") ? [90 * scale, 40 * scale] : [];
      return widths.map((width) => ({ width }) as DOMRect) as unknown as DOMRectList;
    });
    try {
      const card = await mount({ group_wallets: false });
      // 130 units + 12 + 80 = 222 layout pixels: one more than the row has.
      await vi.waitFor(() => expect(one(card, ".wallets")?.classList.contains("rows-wrapped")).toBe(true));
    } finally {
      room.mockRestore();
      layoutWidth.mockRestore();
      rect.mockRestore();
      lines.mockRestore();
    }
  });

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
describe("the compact options", () => {
  it("show_header: false leaves the header out, title and all", async () => {
    const card = await mount({ show_header: false });
    expect(one(card, ".head")).toBeNull();
    expect(one(card, ".content")?.classList.contains("headless")).toBe(true);
    expect(one(await mount(), ".content")?.classList.contains("headless")).toBe(false);
    const empty = await mount({ show_header: false }, makeHass({ devices: [] }));
    expect(one(empty, ".head")).toBeNull();
    expect(one(empty, ".empty")).not.toBeNull();
  });

  it("without the header the eye sits beside the total value, not inside it", async () => {
    const card = await mount({ show_header: false });
    const row = one(card, ".hero-row") as HTMLElement;
    expect([...row.children].map((child) => child.className.split(" ")[0])).toEqual(["hero", "icon-btn"]);
    expect(row.children[1]?.classList.contains("eye")).toBe(true);
    expect(one(card, ".hero .eye")).toBeNull();
    (one(card, ".hero-row .eye") as HTMLElement).click();
    await card.updateComplete;
    expect(textOf(one(card, ".hero .amount"))).toBe("••••••");
    // With the header the eye stays in it.
    const headed = await mount();
    expect(one(headed, ".hero-row")).toBeNull();
    expect(one(headed, ".head .eye")).not.toBeNull();
  });

  it("without header and total the eye has a row of its own at the top", async () => {
    const card = await mount({ show_header: false, show_total: false });
    expect(one(card, ".content")?.firstElementChild?.classList.contains("eye-row")).toBe(true);
    expect(one(card, ".eye-row .eye")).not.toBeNull();
    expect(all(card, ".eye")).toHaveLength(1);
    const css = (await import("../src/styles")).cardStyles.cssText;
    expect(css).toMatch(/\.eye-row\s*\{[^}]*justify-content:\s*flex-end/);
    // With the header, the header's eye alone.
    expect(one(await mount({ show_total: false }), ".eye-row")).toBeNull();
  });

  it("the eye keeps its size beside the total, at every width", async () => {
    const css = (await import("../src/styles")).cardStyles.cssText;
    expect(css).toMatch(/\.hero-row\s*\{[^}]*display:\s*flex/);
    expect(css).toMatch(/\.hero-row \.hero\s*\{[^}]*min-width:\s*0/);
    expect(css).toMatch(/\.hero-row \.eye\s*\{[^}]*flex:\s*none/);
    // No narrow card shrinks it.
    const narrow = (css.match(/@container[^{]*\{[\s\S]*?\n  \}/g) ?? []).join("\n");
    expect(narrow).toContain(".hero");
    expect(narrow).not.toMatch(/\.eye|\.icon-btn/);
  });

  it("show_timeframes: false leaves the timeframe buttons out; return and line keep the timeframe", async () => {
    const card = await mount({ show_timeframes: false, timeframe: "week" });
    expect(one(card, ".seg")).toBeNull();
    expect(textOf(one(card, ".chip-label"))).toBe("return over 1 week");
    await settled(card);
    expect(textOf(one(card, ".caption"))).toMatch(/^Total value, .+ – today$/);
    expect(one(await mount(), ".seg")).not.toBeNull();
  });

  it("counts one row less without the header", async () => {
    expect((await mount({ show_header: false })).getCardSize()).toBe(7);
  });

  it("puts header, default timeframe, timeframe buttons and the eye's start under Appearance", async () => {
    const { form } = await openEditor("bitpanda-portfolio-card");
    const appearance = form.schema.find((field) => (field as { title?: string }).title === "Appearance") as unknown as {
      schema: { name: string; default?: unknown }[];
    };
    expect(appearance.schema.map((field) => field.name)).toEqual(["show_header", "timeframe", "show_timeframes", "hide_amounts"]);
    // The switches on unless chosen; the timeframe shows the card's own default.
    expect(appearance.schema.map((field) => field.default)).toEqual([true, undefined, true, false]);
    expect(form.computeLabel({ name: "timeframe" })).toBe("Default timeframe");
    expect(form.computeLabel({ name: "show_header" })).toBe("Header");
    expect(form.computeHelper({ name: "show_header" })).toBe("Title and eye; without it the eye stands beside the total value, or in a row of its own without that");
    expect(form.computeLabel({ name: "show_timeframes" })).toBe("Timeframe buttons");
    expect(form.computeHelper({ name: "show_timeframes" })).toBe("Only while the total value or the line is shown; without them the card keeps the timeframe chosen above");
    expect(form.computeHelper({ name: "hide_amounts" })).toBe("Percentages stay visible; the eye on the card shows the amounts only temporarily");
  });
});

describe("the eye", () => {
  /** A card with every part present and opened: the since-purchase line,
   * the staking list and every wallet's detail. */
  async function opened(hidden: boolean): Promise<PortfolioCard> {
    const card = await mount({ group_wallets: false, hide_amounts: hidden });
    one(card, ".staking")?.click();
    await card.updateComplete;
    all(card, ".wallet .chevron").forEach((chevron) => chevron.click());
    await card.updateComplete;
    return card;
  }
  /** Every text and every attribute value in the card. */
  const everything = (card: PortfolioCard): string =>
    [...root(card).querySelectorAll("*")].flatMap((element) => [...element.attributes].map((attribute) => attribute.value)).join("\n") +
    (root(card).textContent ?? "");
  /** What a tap on the card's parts opens. */
  const dialogs = (card: PortfolioCard): string[] => {
    const seen: string[] = [];
    card.addEventListener("hass-more-info", (event) => seen.push((event as CustomEvent).detail.entityId));
    return seen;
  };
  const HIDDEN_TAPS = [".hero", ".chip", ".pair > div", ".wallet .tap", ".staking-row", ".since-amount"];

  it("hides amounts behind a fixed mask with no real text in the DOM", async () => {
    const shown = await opened(false);
    const amounts = [...new Set(all(shown, ".amount").map((element) => textOf(element)))].filter((text) => /\d/.test(text));
    // Every part is there: the since-purchase line, the staking list, the details.
    expect(amounts).toEqual(expect.arrayContaining(["+€3,700.00", "€507.91", "0.00061234 ETH", "€1.41", "€9.47", "€2,377.00"]));
    const hidden = await opened(true);
    const text = everything(hidden);
    for (const value of amounts) expect(text, value).not.toContain(value);
    const masks = all(hidden, ".amount");
    expect(masks.length).toBe(all(shown, ".amount").length);
    expect(new Set(masks.map((mask) => textOf(mask)))).toEqual(new Set(["••••••"]));
  });

  it("reads the mask as \"Amount hidden\"", async () => {
    const masks = all(await opened(true), ".amount");
    for (const mask of masks) expect([mask.getAttribute("role"), mask.getAttribute("aria-label")]).toEqual(["img", "Amount hidden"]);
    const german = await mount({ hide_amounts: true }, portfolioHass({ language: "de" }));
    expect(one(german, ".hero .amount")?.getAttribute("aria-label")).toBe("Betrag verborgen");
  });

  it("a hidden total value, cash, cash plus, wallet row, staking row, since-purchase amount and return chip open nothing", async () => {
    const card = await opened(true);
    const seen = dialogs(card);
    for (const selector of HIDDEN_TAPS) {
      const targets = all(card, selector);
      expect(targets.length, selector).toBeGreaterThan(0);
      for (const target of targets) {
        target.click();
        target.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
      }
    }
    expect(seen).toEqual([]);
  });

  it("they are no buttons while hidden, and buttons again once the eye opens", async () => {
    const card = await opened(true);
    const button = (element: HTMLElement): (string | null)[] => [element.getAttribute("role"), element.getAttribute("tabindex")];
    for (const selector of HIDDEN_TAPS) for (const element of all(card, selector)) expect(button(element), selector).toEqual([null, null]);
    one(card, ".eye")?.click();
    await card.updateComplete;
    for (const selector of HIDDEN_TAPS) for (const element of all(card, selector)) expect(button(element), selector).toEqual(["button", "0"]);
  });

  it("the since-purchase chip still opens while hidden", async () => {
    const card = await opened(true);
    const seen = dialogs(card);
    const chip = one(card, ".since-chip") as HTMLElement;
    expect(chip.getAttribute("role")).toBe("button");
    chip.click();
    chip.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    expect(seen).toEqual(["sensor.bitpanda_portfolio_total_return_percent", "sensor.bitpanda_portfolio_total_return_percent"]);
  });

  it("group headers, the staking line and the chevrons still open and close while hidden", async () => {
    const card = await mount({ hide_amounts: true });
    const group = one(card, ".group") as HTMLElement;
    const before = group.getAttribute("aria-expanded");
    group.click();
    await card.updateComplete;
    expect(group.getAttribute("aria-expanded")).not.toBe(before);
    if (!one(card, ".wallet .chevron")) {
      group.click();
      await card.updateComplete;
    }
    one(card, ".wallet .chevron")?.click();
    await card.updateComplete;
    expect(one(card, ".detail")).not.toBeNull();
    const staking = one(card, ".staking") as HTMLElement;
    staking.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    await card.updateComplete;
    expect(staking.getAttribute("aria-expanded")).toBe("true");
    expect(one(card, ".staking-row")).not.toBeNull();
  });

  it("the allocation bar names its parts and shares; the legend is hidden from screen readers", async () => {
    const card = await mount();
    const legend = all(card, ".legend > span").map((item) => textOf(item));
    expect(legend.length).toBeGreaterThan(1);
    const bar = one(card, ".bar") as HTMLElement;
    expect(bar.getAttribute("role")).toBe("img");
    expect(bar.getAttribute("aria-label")).toBe(`Allocation: ${legend.join(", ")}`);
    expect(one(card, ".legend")?.getAttribute("aria-hidden")).toBe("true");
    const german = await mount({}, portfolioHass({ language: "de" }));
    expect(one(german, ".bar")?.getAttribute("aria-label")).toMatch(/^Verteilung: /);
  });
});

describe("the staking line", () => {
  const VSN: FakeWallet = {
    symbol: "VSN", name: "Vision", category: "crypto", units: 12000, total: "410.33",
    staked: { units: 12000, value: "410.33", apr: 7.5 }, returnPercent: -24.6,
  };
  const staked = (...wallets: FakeWallet[]): FakeHass => makeHass({ devices: [portfolioDevice(), ...wallets.map(walletDevice)] });
  const line = (card: PortfolioCard): string => textOf(one(card, ".staking"));

  it("sums the staked value of the whole portfolio, not the card's selection", async () => {
    const card = await mount({ asset_selection: "only", assets: ["id-btc"] }, staked(BTC, ETH, VSN));
    expect(line(card)).toBe("Staking · €918.24 in 2 wallets");
  });

  it("names no rewards, which the wallets' details show", async () => {
    const card = await mount({}, staked(ETH, VSN));
    expect(line(card)).toBe("Staking · €918.24 in 2 wallets");
    expect(all(card, ".staking > .part").map((part) => textOf(part))).toEqual(["Staking", "€918.24 in 2 wallets"]);
  });

  it("counts one wallet as one", async () => {
    expect(line(await mount({}, staked(BTC, VSN)))).toBe("Staking · €410.33 in 1 wallet");
  });

  it("shows a dash for value and count while a staking sensor has no value", async () => {
    const hass = staked(ETH, VSN).withState("sensor.bitpanda_vsn_staking", "unavailable", {});
    expect(line(await mount({}, hass))).toBe("Staking · — in — wallets");
  });

  it("has no line while nothing is staked or no staking sensor is found", async () => {
    expect(one(await mount({}, staked(BTC)), ".staking")).toBeNull();
    const zero = staked(BTC, { ...VSN, staked: { units: 0, value: "0.0", apr: 7.5 } });
    expect(one(await mount({}, zero), ".staking")).toBeNull();
    const gone = staked(VSN).withState("sensor.bitpanda_vsn_staking", "unavailable", {});
    expect(one(await mount({}, gone), ".staking")).toBeNull();
    expect(one(await mount({ show_staking: false }, staked(ETH)), ".staking")).toBeNull();
  });

  it("opens the staking wallets inline, largest first, with their APR", async () => {
    const card = await mount({}, staked(BTC, VSN, ETH));
    const toggle = one(card, ".staking") as HTMLElement;
    expect([toggle.getAttribute("role"), toggle.getAttribute("aria-expanded")]).toEqual(["button", "false"]);
    expect(one(card, ".staking-row")).toBeNull();
    toggle.click();
    await card.updateComplete;
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(all(card, ".staking-row").map((row) => textOf(row))).toEqual([
      "Ethereum 507.91 EUR · APR 2.9%",
      "Vision 410.33 EUR · APR 7.5%",
    ]);
    toggle.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    await card.updateComplete;
    expect(one(card, ".staking-row")).toBeNull();
  });

  it("leaves a staking row's APR out without one", async () => {
    const card = await mount({}, staked({ ...VSN, staked: { units: 12000, value: "410.33" } }));
    one(card, ".staking")?.click();
    await card.updateComplete;
    expect(textOf(one(card, ".staking-row"))).toBe("Vision 410.33 EUR");
  });

  it("a staking row opens its Balance (staking) dialog", async () => {
    const card = await mount({}, staked(ETH, VSN));
    const opened: string[] = [];
    card.addEventListener("hass-more-info", (event) => opened.push((event as CustomEvent).detail.entityId));
    one(card, ".staking")?.click();
    await card.updateComplete;
    all(card, ".staking-row")[1]?.click();
    expect(opened).toEqual(["sensor.bitpanda_vsn_staking"]);
  });

  it("starts closed in every new card, and lays out with its list open", async () => {
    const first = await mount({}, staked(ETH));
    one(first, ".staking")?.click();
    await first.updateComplete;
    const layout = (first as unknown as { groupsLayout: string }).groupsLayout;
    expect(() => (first as unknown as { fitLayout(): void }).fitLayout()).not.toThrow();
    expect((first as unknown as { groupsLayout: string }).groupsLayout).toBe(layout);
    const second = await mount({}, staked(ETH));
    expect(one(second, ".staking")?.getAttribute("aria-expanded")).toBe("false");
  });

  it("blurs its amount behind the eye", async () => {
    const card = await mount({ hide_amounts: true }, staked(ETH));
    expect(all(card, ".staking .amount.blur")).toHaveLength(1);
  });

  it("shows a dash for the sum while no currency is known", async () => {
    let hass = staked(ETH);
    for (const [entityId, state] of Object.entries(hass.states)) {
      if (!state) continue;
      const attributes = { ...state.attributes };
      delete attributes["unit_of_measurement"];
      hass = hass.withState(entityId, state.state, attributes);
    }
    expect(line(await mount({}, hass))).toBe("Staking · — in 1 wallet");
  });

  it("sits right after Cash in the editor, on unless chosen", async () => {
    const { form } = await openEditor("bitpanda-portfolio-card");
    const content = form.schema.find((field) => (field as { title?: string }).title === "Content") as unknown as {
      schema: { name: string; default?: unknown }[];
    };
    const names = content.schema.map((field) => field.name);
    expect(names.indexOf("show_staking")).toBe(names.indexOf("show_cash") + 1);
    expect(content.schema.find((field) => field.name === "show_staking")?.default).toBe(true);
    expect(form.computeLabel({ name: "show_staking" })).toBe("Staking");
  });
});

describe("the dividers", () => {
  // What follows each divider: a part's first element.
  const after = (card: PortfolioCard): string[] =>
    all(card, ".content > .divider").map((divider) => divider.nextElementSibling?.classList[0] ?? "");

  it("stand once before each shown part after the total: cash and allocation as one, then the wallets", async () => {
    expect(after(await mount())).toEqual(["pair", "wallets"]);
    expect(after(await mount({ group_wallets: false }))).toEqual(["pair", "wallets"]);
    const off = { show_staking: false };
    expect(after(await mount({ ...off, show_cash: false }))).toEqual(["bar", "wallets"]);
    expect(after(await mount({ ...off, show_graph: false, show_cash: false }))).toEqual(["bar", "wallets"]);
    expect(after(await mount({ ...off, show_graph: false, show_cash: false, show_allocation: false }))).toEqual(["wallets"]);
    expect(after(await mount({ show_wallets: false }))).toEqual(["pair"]);
    expect(after(await mount({ ...off, show_cash: false, show_allocation: false, show_wallets: false }))).toEqual([]);
  });

  it("count the staking line as part of the cash section, while it is drawn", async () => {
    expect(after(await mount({ show_cash: false }))).toEqual(["staking", "wallets"]);
    expect(after(await mount({ show_cash: false, show_allocation: false, show_wallets: false }))).toEqual(["staking"]);
    // Nothing staked: no line, and no divider for it.
    const unstaked = makeHass({ devices: [portfolioDevice(), walletDevice(BTC)] });
    expect(after(await mount({ show_cash: false, show_allocation: false }, unstaked))).toEqual(["wallets"]);
  });

  it("leave no line at the top when neither the total nor its line is shown", async () => {
    const first = (card: PortfolioCard): string => one(card, ".content")?.firstElementChild?.classList[0] ?? "";
    const top = { show_total: false, show_graph: false };
    expect(first(await mount(top))).toBe("pair");
    expect(after(await mount(top))).toEqual(["wallets"]);
    // Only the wallets with their search field: the field comes first.
    expect(first(await mount({ ...top, show_cash: false, show_staking: false, show_allocation: false, show_search: true }))).toBe("search");
    expect(after(await mount({ ...top, show_cash: false, show_staking: false, show_allocation: false, show_search: true }))).toEqual([]);
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

  /** Presses `key` on the line; whether the press was taken from the page. */
  const press = async (card: PortfolioCard, key: string): Promise<boolean> => {
    const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
    one(card, ".plot")?.dispatchEvent(event);
    await card.updateComplete;
    return event.defaultPrevented;
  };
  const now = (card: PortfolioCard): string | null | undefined => one(card, ".plot")?.getAttribute("aria-valuenow");

  it("the line is a slider named by its caption", async () => {
    const card = await mount({ timeframe: "day" });
    await settled(card);
    const plot = one(card, ".plot") as HTMLElement;
    expect([plot.getAttribute("role"), plot.getAttribute("tabindex")]).toEqual(["slider", "0"]);
    expect(plot.getAttribute("aria-label")).toBe("Total value, last 24 hours");
    expect(plot.getAttribute("aria-label")).toBe(textOf(one(card, ".caption")));
    expect([plot.getAttribute("aria-valuemin"), plot.getAttribute("aria-valuemax"), now(card)]).toEqual(["0", "2", "2"]);
    expect(plot.hasAttribute("aria-live")).toBe(false);
    const css = (await import("../src/styles")).cardStyles.cssText;
    expect(css).toMatch(/\.plot\[role="slider"\]:focus-visible[^{]*\{[^}]*box-shadow:/);
  });

  it("arrow keys move the cursor point by point, Home and End to the ends", async () => {
    const card = await mount({ timeframe: "day" });
    await settled(card);
    // The first left arrow from no cursor goes one point back from the
    // newest, which the slider reports already.
    expect(await press(card, "ArrowLeft")).toBe(true);
    expect([now(card), shown(card).tip]).toEqual(["1", expect.stringMatching(/ · €12,400\.00$/)]);
    expect(shown(card).tags).toEqual(["€12,760.20", "€12,380.10", "€12,000.00"]);
    await press(card, "ArrowLeft");
    expect([now(card), shown(card).tip]).toEqual(["0", expect.stringMatching(/ · €12,000\.00$/)]);
    await press(card, "ArrowLeft");
    expect(now(card)).toBe("0");
    expect(await press(card, "End")).toBe(true);
    expect([now(card), shown(card).tip]).toEqual(["2", expect.stringMatching(/ · €12,760\.20$/)]);
    expect(await press(card, "Home")).toBe(true);
    expect(now(card)).toBe("0");
    expect(await press(card, "ArrowRight")).toBe(true);
    expect(now(card)).toBe("1");
    expect(await press(card, "End")).toBe(true);
    await press(card, "ArrowRight");
    expect(now(card)).toBe("2");
    // Other keys are left to the page.
    expect(await press(card, "a")).toBe(false);
  });

  it("the first right arrow from no cursor goes to the newest point too", async () => {
    const card = await mount({ timeframe: "day" });
    await settled(card);
    await press(card, "ArrowRight");
    expect(now(card)).toBe("2");
    expect(shown(card).cursor).toBe(true);
  });

  it("Escape and blur clear the cursor", async () => {
    const card = await mount({ timeframe: "day" });
    await settled(card);
    await press(card, "Home");
    await press(card, "Escape");
    expect(shown(card).cursor).toBe(false);
    expect(now(card)).toBe("2");
    await press(card, "Home");
    one(card, ".plot")?.dispatchEvent(new FocusEvent("blur"));
    await card.updateComplete;
    expect(shown(card).cursor).toBe(false);
  });

  it("focus alone sets no cursor", async () => {
    const card = await mount({ timeframe: "day" });
    await settled(card);
    one(card, ".plot")?.dispatchEvent(new FocusEvent("focus"));
    await card.updateComplete;
    expect(shown(card).cursor).toBe(false);
  });

  it("a pointer takes over and clears a cursor a key set", async () => {
    const rect = box();
    try {
      const card = await mount({ timeframe: "day" });
      await settled(card);
      await press(card, "End");
      await point(card, "pointermove", 0.02);
      expect(shown(card).tip).toMatch(/ · €12,000\.00$/);
      await point(card, "pointerleave", 0.02);
      expect(shown(card).cursor).toBe(false);
    } finally {
      rect.mockRestore();
    }
  });

  it("the value text gives value and time, only the time while hidden", async () => {
    const card = await mount({ timeframe: "day" });
    await settled(card);
    const text = (): string | null | undefined => one(card, ".plot")?.getAttribute("aria-valuetext");
    // Without a cursor: the newest point.
    expect(text()).toMatch(/^€12,760\.20, .*\d:\d\d/);
    await press(card, "Home");
    expect(text()).toMatch(/^€12,000\.00, .*\d:\d\d/);
    expect(text()).toBe(`€12,000.00, ${shown(card).tip.split(" · ")[0]}`);
    const hidden = await mount({ timeframe: "day", hide_amounts: true });
    await settled(hidden);
    await press(hidden, "Home");
    const time = one(hidden, ".plot")?.getAttribute("aria-valuetext");
    expect(time).not.toContain("€");
    expect(time).toBe(shown(hidden).tip);
    const german = await mount({ timeframe: "day" }, portfolioHass({ language: "de" }));
    await settled(german);
    expect(one(german, ".plot")?.getAttribute("aria-label")).toBe("Gesamtwert, letzte 24 Stunden");
  });

  it("the line is not focusable while it is not interactive", async () => {
    const recent = Date.now() - 2 * HOUR;
    const hass = makeHass({ devices: [portfolioDevice()], callWS: async () => ({ points: [[recent, 1], [recent + HOUR, 2]] }) });
    const card = await mount({ timeframe: "week" }, hass);
    await vi.waitFor(() => expect(one(card, ".plot svg.spark")).not.toBeNull());
    const plot = one(card, ".plot") as HTMLElement;
    expect([plot.getAttribute("role"), plot.getAttribute("tabindex")]).toEqual([null, null]);
  });

  it("keeps rendering when a shorter line arrives under a keyed cursor", async () => {
    // A refetch can bring fewer points: Bitpanda's history leaves out a
    // point without a value.
    let points = [[Date.now() - 20 * HOUR, 1], [Date.now() - 10 * HOUR, 2], [Date.now() - HOUR, 3]];
    const hass = makeHass({ devices: [portfolioDevice()], callWS: async () => ({ points }) });
    const card = await mount({ timeframe: "day" }, hass);
    await settled(card);
    await press(card, "End");
    expect(now(card)).toBe("2");
    points = points.slice(0, 2);
    card.hass = hass.withState("sensor.bitpanda_portfolio_return_day", "-0.50", { unit_of_measurement: "%" });
    await vi.waitFor(() => expect(one(card, ".plot")?.getAttribute("aria-valuemax")).toBe("1"));
    expect(now(card)).toBe("1");
    expect(one(card, ".plot")?.getAttribute("aria-valuetext")).toMatch(/^€2\.00, /);
  });

  it("a key press does not remeasure the layout", async () => {
    const card = await mount({ timeframe: "day" });
    await settled(card);
    const fit = vi.spyOn(card as unknown as { fitLayout(): void }, "fitLayout");
    await press(card, "End");
    await press(card, "ArrowLeft");
    await press(card, "Escape");
    expect(fit).not.toHaveBeenCalled();
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