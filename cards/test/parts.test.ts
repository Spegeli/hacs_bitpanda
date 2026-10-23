import { html, render, type TemplateResult } from "lit";
import { describe, expect, it, vi } from "vitest";

import { findPortfolio } from "../src/discovery";
import {
  matchesWallet,
  allFit,
  amount,
  currencySwitch,
  emptyState,
  header,
  moreInfo,
  onActivate,
  returnChip,
  timeframeSwitch,
  unbroken,
  walletRow,
} from "../src/parts";
import { BTC, ETH, EUNL, XAU, makeHass, portfolioDevice, walletDevice } from "./fixtures";

function mount(template: TemplateResult | null): HTMLElement {
  const host = document.createElement("div");
  document.body.append(host);
  render(template ?? html``, host);
  return host;
}

const textOf = (element: Element | null): string => (element?.textContent ?? "").replace(/\s+/g, " ").trim();

describe("header", () => {
  it("shows the title and an eye that toggles", () => {
    const toggle = vi.fn();
    const host = mount(header(makeHass(), "Bitpanda Portfolio", { hidden: false, toggle }));
    expect(textOf(host.querySelector(".title"))).toBe("Bitpanda Portfolio");
    const eye = host.querySelector<HTMLElement>(".eye");
    expect(eye?.getAttribute("aria-label")).toBe("Hide amounts");
    eye?.click();
    expect(toggle).toHaveBeenCalledOnce();
  });

  it("names the eye after what it does next", () => {
    const host = mount(header(makeHass(), "T", { hidden: true, toggle: () => undefined }));
    expect(host.querySelector(".eye")?.getAttribute("aria-label")).toBe("Show amounts");
  });

  it("has no eye where amounts are public", () => {
    expect(mount(header(makeHass(), "Prices")).querySelector(".eye")).toBeNull();
  });
});

describe("returnChip", () => {
  it("shows sign, arrow, colour and the timeframe in words", () => {
    const host = mount(returnChip(makeHass(), 2.31, "week", () => undefined));
    expect(textOf(host.querySelector(".chip"))).toBe("▲ +2.31%");
    expect(host.querySelector(".chip")?.classList.contains("up")).toBe(true);
    expect(textOf(host.querySelector(".chip-label"))).toBe("return over 1 week");
  });

  it("is a dash without a value", () => {
    const host = mount(returnChip(makeHass(), undefined, "day", () => undefined, { text: "+€1.00", hidden: false }));
    expect(textOf(host.querySelector(".chip"))).toBe("—");
  });

  it("is no button without something to open", () => {
    const chip = mount(returnChip(makeHass(), -0.42, "day", undefined)).querySelector(".chip") as HTMLElement;
    expect([chip.getAttribute("role"), chip.getAttribute("tabindex")]).toEqual([null, null]);
    const tappable = mount(returnChip(makeHass(), -0.42, "day", () => undefined)).querySelector(".chip") as HTMLElement;
    expect([tappable.getAttribute("role"), tappable.getAttribute("tabindex")]).toEqual(["button", "0"]);
  });

  it("shows the amount beside the chip in the chip's colour, which the eye blurs", () => {
    const shown = mount(returnChip(makeHass(), -0.42, "day", () => undefined, { text: "-€53.82", hidden: false }));
    expect(textOf(shown.querySelector(".chip"))).toBe("▼ -0.42%");
    expect(textOf(shown.querySelector(".chip + .chip-amount"))).toBe("-€53.82");
    expect(shown.querySelector(".chip-amount")?.classList.contains("down")).toBe(true);
    expect(textOf(shown.querySelector(".hero-line"))).toBe("▼ -0.42% -€53.82 return over 1 day");
    const hidden = mount(returnChip(makeHass(), -0.42, "day", () => undefined, { text: "-€53.82", hidden: true }));
    expect(hidden.querySelector(".chip-amount .amount")?.classList.contains("blur")).toBe(true);
    const without = mount(returnChip(makeHass(), -0.42, "day", () => undefined, { text: undefined, hidden: false }));
    expect(without.querySelector(".chip-amount")).toBeNull();
  });
});

describe("timeframeSwitch", () => {
  it("marks the selected timeframe and selects another on a tap", () => {
    const select = vi.fn();
    const host = mount(timeframeSwitch(makeHass({ language: "de" }), "week", select));
    const buttons = [...host.querySelectorAll<HTMLElement>("[role=radio]")];
    expect(buttons.map((button) => button.textContent?.trim())).toEqual(["1T", "1W", "1M", "6M", "1J"]);
    expect(buttons.map((button) => button.getAttribute("aria-checked"))).toEqual(["false", "true", "false", "false", "false"]);
    expect(buttons.map((button) => button.tabIndex)).toEqual([-1, 0, -1, -1, -1]);
    buttons[3]?.click();
    expect(select).toHaveBeenCalledWith("six_month");
  });

  it("moves with the arrow keys", () => {
    const select = vi.fn();
    const host = mount(timeframeSwitch(makeHass(), "week", select));
    const group = host.querySelector<HTMLElement>("[role=radiogroup]");
    group?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    group?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    group?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    group?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
    group?.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));
    expect(select.mock.calls.map((call) => call[0])).toEqual(["month", "day", "month", "day"]);
  });

  it("is named, and the focus follows the arrow keys", () => {
    const host = mount(timeframeSwitch(makeHass({ language: "de" }), "week", () => undefined));
    expect(host.querySelector("[role=radiogroup]")?.getAttribute("aria-label")).toBe("Zeitraum");
    const radios = [...host.querySelectorAll<HTMLElement>("[role=radio]")];
    radios[1]?.focus();
    radios[1]?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    expect(document.activeElement).toBe(radios[2]);
  });

  it("Space and Enter select the focused option", () => {
    const select = vi.fn();
    const host = mount(timeframeSwitch(makeHass(), "week", select));
    const radios = [...host.querySelectorAll<HTMLElement>("[role=radio]")];
    radios[3]?.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    radios[4]?.dispatchEvent(new KeyboardEvent("keydown", { key: " ", bubbles: true }));
    expect(select.mock.calls.map((call) => call[0])).toEqual(["six_month", "year"]);
  });

  it("wraps around at the ends", () => {
    const select = vi.fn();
    const host = mount(timeframeSwitch(makeHass(), "year", select));
    host.querySelector("[role=radiogroup]")?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    expect(select).toHaveBeenCalledWith("day");
  });
});

describe("currencySwitch", () => {
  it("hides with one currency", () => {
    expect(currencySwitch(makeHass(), ["EUR"], "EUR", () => undefined)).toBeNull();
  });

  it("offers every currency and selects one", () => {
    const select = vi.fn();
    const host = mount(currencySwitch(makeHass({ language: "de" }), ["EUR", "USD"], "USD", select));
    expect(host.querySelector("[role=radiogroup]")?.getAttribute("aria-label")).toBe("Währung");
    const buttons = [...host.querySelectorAll<HTMLElement>("[role=radio]")];
    expect(buttons.map((button) => [button.textContent?.trim(), button.getAttribute("aria-checked")])).toEqual([
      ["EUR", "false"],
      ["USD", "true"],
    ]);
    buttons[0]?.click();
    host.querySelector("[role=radiogroup]")?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    expect(select.mock.calls.map((call) => call[0])).toEqual(["EUR", "EUR"]);
  });
});

describe("walletRow", () => {
  const hass = makeHass({ devices: [portfolioDevice(), walletDevice(BTC), walletDevice(ETH), walletDevice(EUNL), walletDevice(XAU)] });
  const wallets = findPortfolio(hass)?.wallets ?? [];
  const wallet = (symbol: string) => wallets.find((item) => item.symbol === symbol) ?? wallets[0]!;

  it("shows the ISIN after the units for an ETF, and the name without its symbol", () => {
    const host = mount(walletRow({ hass, wallet: wallet("EUNL"), hidden: false, onTap: () => undefined }));
    expect(textOf(host.querySelector(".n"))).toBe("iShares Core MSCI World UCITS ETF");
    // The whole name on hover: a long one is cut after two lines.
    expect(host.querySelector(".n")?.getAttribute("title")).toBe("iShares Core MSCI World UCITS ETF");
    expect(textOf(host.querySelector(".s"))).toBe("21.4 shares · IE00B4L5Y983");
    // The units apart from the ISIN, which may take a line of its own.
    expect(textOf(host.querySelector(".s .units"))).toBe("21.4 shares");
    expect(textOf(host.querySelector(".s .isin"))).toBe("IE00B4L5Y983");
    expect(textOf(host.querySelector(".val"))).toBe("2045.10 EUR");
    expect(textOf(host.querySelector(".wchip"))).toBe("▲ +8.00%");
  });

  it("shows the return since purchase in a chip above the value, its amount only in the detail", () => {
    const shown = mount(walletRow({ hass, wallet: wallet("BTC"), hidden: false, onTap: () => undefined }));
    expect(textOf(shown.querySelector(".n"))).toBe("Bitcoin");
    expect(textOf(shown.querySelector(".right > .wchip:first-child"))).toBe("▲ +12.40%");
    expect(shown.querySelector(".wchip")?.classList.contains("up")).toBe(true);
    expect(shown.querySelector(".right .wchip + .val")).not.toBeNull();
    expect(shown.textContent).not.toContain("650.11");
    // The eye blurs the value and keeps the percentage.
    const hidden = mount(walletRow({ hass, wallet: wallet("BTC"), hidden: true, onTap: () => undefined }));
    expect(hidden.querySelector(".val .amount")?.classList.contains("blur")).toBe(true);
    expect(textOf(hidden.querySelector(".wchip"))).toBe("▲ +12.40%");
  });

  it("shows the staked share on a line of its own below the units, without the APR", () => {
    const host = mount(walletRow({ hass, wallet: wallet("ETH"), hidden: false, onTap: () => undefined }));
    expect(textOf(host.querySelector(".s"))).toBe("0.55 ETH");
    expect(textOf(host.querySelector(".s + .stake .badge"))).toBe("40% staked");
    expect(host.querySelector(".sub")?.classList.contains("staked")).toBe(true);
    const unstaked = mount(walletRow({ hass, wallet: wallet("BTC"), hidden: false, onTap: () => undefined }));
    expect(unstaked.querySelector(".stake")).toBeNull();
    expect(unstaked.querySelector(".sub")?.classList.contains("staked")).toBe(false);
  });

  it("counts metals in grams and masks amounts and units when hidden", () => {
    expect(textOf(mount(walletRow({ hass, wallet: wallet("XAU"), hidden: false, onTap: () => undefined })).querySelector(".s"))).toBe("0.56 g");
    const host = mount(walletRow({ hass, wallet: wallet("XAU"), hidden: true, onTap: () => undefined }));
    expect(textOf(host.querySelector(".s"))).toBe("••••••");
    expect(host.querySelectorAll(".amount.blur")).toHaveLength(2);
    expect(textOf(host.querySelector(".wchip"))).toBe("▲ +4.20%");
  });

  it("is no button while hidden, its chevron still is", () => {
    const tapped: string[] = [];
    const host = mount(walletRow({ hass, wallet: wallet("BTC"), hidden: true, onTap: () => tapped.push("row"), chevron: { open: false, toggle: () => tapped.push("chevron") } }));
    const tap = host.querySelector(".tap") as HTMLElement;
    expect([tap.getAttribute("role"), tap.getAttribute("tabindex")]).toEqual([null, null]);
    tap.click();
    tap.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    (host.querySelector(".chevron") as HTMLElement).click();
    expect(tapped).toEqual(["chevron"]);
  });

  it("has a chevron when it can open, and taps open the sensor", () => {
    const toggle = vi.fn();
    const tap = vi.fn();
    const host = mount(
      walletRow({ hass, wallet: wallet("BTC"), hidden: false, onTap: tap, chevron: { open: true, toggle } }),
    );
    const chevron = host.querySelector<HTMLElement>(".chevron");
    expect(chevron?.getAttribute("aria-expanded")).toBe("true");
    chevron?.click();
    expect(toggle).toHaveBeenCalledOnce();
    expect(tap).not.toHaveBeenCalled();
    host.querySelector<HTMLElement>(".wallet .tap")?.click();
    expect(tap).toHaveBeenCalledOnce();
  });

  it("the chevron is a button beside the row's button, not inside it", () => {
    const tap = vi.fn();
    const host = mount(
      walletRow({ hass, wallet: wallet("BTC"), hidden: false, onTap: tap, chevron: { open: false, toggle: () => undefined } }),
    );
    expect(host.querySelector(".chevron")?.parentElement?.closest("[role=button]")).toBeNull();
    const row = host.querySelector<HTMLElement>(".wallet .tap");
    expect(row?.getAttribute("role")).toBe("button");
    row?.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(tap).toHaveBeenCalledOnce();
  });

  it("the chevron opens by keyboard without tapping the row", () => {
    const toggle = vi.fn();
    const tap = vi.fn();
    const host = mount(
      walletRow({ hass, wallet: wallet("BTC"), hidden: false, onTap: tap, chevron: { open: false, toggle } }),
    );
    const chevron = host.querySelector<HTMLElement>(".chevron");
    expect(chevron?.getAttribute("aria-expanded")).toBe("false");
    chevron?.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(toggle).toHaveBeenCalledOnce();
    expect(tap).not.toHaveBeenCalled();
  });

  it("no change since purchase shows 0.00% without an arrow", () => {
    const flat = makeHass({ devices: [portfolioDevice(), walletDevice({ ...BTC, returnPercent: 0, totalReturn: 0 })] });
    const [row] = findPortfolio(flat)?.wallets ?? [];
    const host = mount(walletRow({ hass: flat, wallet: row!, hidden: false, onTap: () => undefined }));
    expect(textOf(host.querySelector(".wchip"))).toBe("0.00%");
    expect(host.querySelector(".wchip")?.className.trim()).toBe("wchip");
  });

  it("staked without an APR shows the share alone", () => {
    const noApr = makeHass({ devices: [portfolioDevice(), walletDevice({ ...ETH, staked: { units: 0.22, value: "507.91" } })] });
    const [row] = findPortfolio(noApr)?.wallets ?? [];
    const host = mount(walletRow({ hass: noApr, wallet: row!, hidden: false, onTap: () => undefined }));
    expect(textOf(host.querySelector(".badge"))).toBe("40% staked");
  });

  it("a wallet without a total sensor shows dashes", () => {
    const bare = { deviceId: "x", assetId: "x", name: "X", shortName: "X", symbol: "X" };
    const host = mount(walletRow({ hass, wallet: bare, hidden: false, onTap: () => undefined }));
    expect(textOf(host.querySelector(".val"))).toBe("—");
    expect(textOf(host.querySelector(".s"))).toBe("—");
  });

  it("renders dashes when the wallet's sensors are unavailable", () => {
    const broken = hass.withState("sensor.bitpanda_btc_wallet_total", "unavailable", {});
    const host = mount(walletRow({ hass: broken, wallet: wallet("BTC"), hidden: false, onTap: () => undefined }));
    expect(textOf(host.querySelector(".val"))).toBe("—");
    expect(textOf(host.querySelector(".s"))).toBe("—");
    // No return known: a dash in place of the chip, without its background.
    expect(textOf(host.querySelector(".wchip.none"))).toBe("—");
    expect(host.textContent).not.toMatch(/NaN|undefined|null/);
  });
});

describe("small parts", () => {
  it("emptyState says what to do", () => {
    expect(textOf(mount(emptyState("Set it up.")).querySelector(".empty"))).toBe("Set it up.");
  });

  it("amount shows a fixed, blurred mask while hidden, read out as \"Amount hidden\"", () => {
    const hass = makeHass();
    const hidden = mount(amount(hass, "€1,234.56", true)).querySelector(".amount") as HTMLElement;
    expect(hidden.classList.contains("blur")).toBe(true);
    expect(textOf(hidden)).toBe("••••••");
    expect([hidden.getAttribute("role"), hidden.getAttribute("aria-label")]).toEqual(["img", "Amount hidden"]);
    expect(textOf(mount(amount(hass, undefined, true)).querySelector(".amount"))).toBe("••••••");
    const shown = mount(amount(hass, "€1", false)).querySelector(".amount") as HTMLElement;
    expect(shown.classList.contains("blur")).toBe(false);
    expect([shown.hasAttribute("role"), shown.hasAttribute("aria-label"), textOf(shown)]).toEqual([false, false, "€1"]);
    expect(textOf(mount(amount(hass, undefined, false)).querySelector(".amount"))).toBe("—");
    expect(mount(amount(makeHass({ language: "de" }), "1 €", true)).querySelector(".amount")?.getAttribute("aria-label")).toBe("Betrag verborgen");
  });

  it("moreInfo fires hass-more-info with the entity", () => {
    const element = document.createElement("div");
    const heard = vi.fn();
    document.body.append(element);
    document.addEventListener("hass-more-info", (event) => heard((event as CustomEvent).detail), { once: true });
    moreInfo(element, "sensor.x");
    expect(heard).toHaveBeenCalledWith({ entityId: "sensor.x" });
  });

  it("tappable elements are focusable and act on Enter and Space", () => {
    const handler = vi.fn();
    const host = mount(html`<div role="button" tabindex="0" @keydown=${onActivate(handler)}></div>`);
    const target = host.querySelector("div");
    for (const key of ["Enter", " ", "a"]) target?.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    expect(handler).toHaveBeenCalledTimes(2);
  });
});

describe("matchesWallet", () => {
  const sp500 = { name: "iShares Core S&P 500 UCITS ETF", symbol: "SXR8", isin: "IE00B5BMR087" };
  const allWorld = { name: "Vanguard FTSE All-World UCITS ETF", symbol: "VWCE", isin: "IE00BK5BQT80" };
  const gold = { name: "iShares Physical Gold ETC", symbol: "PPFB", isin: "IE00B4ND3602" };

  it("finds a wallet when every word of the search lies in its name, symbol or ISIN, in any order and case", () => {
    expect(matchesWallet(sp500, "ishare 500")).toBe(true);
    expect(matchesWallet(sp500, "500 ishares")).toBe(true);
    expect(matchesWallet(sp500, "  SXR8 ")).toBe(true);
    expect(matchesWallet(sp500, "ie00b5")).toBe(true);
    expect(matchesWallet(gold, "ishare gold")).toBe(true);
    // Every word must match: one more word only ever narrows the list.
    expect(matchesWallet(sp500, "ishare gold")).toBe(false);
    expect(matchesWallet(gold, "ishare silver")).toBe(false);
  });

  it("leaves out punctuation and accents, in the search and in the name", () => {
    expect(matchesWallet(sp500, "sp 500")).toBe(true);
    expect(matchesWallet(sp500, "s&p")).toBe(true);
    expect(matchesWallet(allWorld, "all world")).toBe(true);
    expect(matchesWallet(allWorld, "all-world")).toBe(true);
    expect(matchesWallet({ name: "LVMH Moët Hennessy", symbol: "MC" }, "moet")).toBe(true);
    expect(matchesWallet({ name: "Nestlé", symbol: "NESN" }, "NESTLÉ")).toBe(true);
  });

  it("reads letters without an accent to strip as their plain spelling: ø, æ, œ, ß, ł, đ, ð, þ, ı", () => {
    expect(matchesWallet({ name: "Ørsted", symbol: "DNNGY" }, "orsted")).toBe(true);
    expect(matchesWallet({ name: "A.P. Møller - Mærsk", symbol: "AMKBY" }, "maersk moller")).toBe(true);
    expect(matchesWallet({ name: "Œuvre", symbol: "OV" }, "oeuvre")).toBe(true);
    expect(matchesWallet({ name: "Łódź", symbol: "LDZ" }, "lodz")).toBe(true);
    expect(matchesWallet({ name: "Đuro Đaković", symbol: "DDJH" }, "duro")).toBe(true);
    expect(matchesWallet({ name: "Þór Íslandsbanki", symbol: "ISB" }, "thor")).toBe(true);
    expect(matchesWallet({ name: "Yapı Kredi", symbol: "YKBNK" }, "yapi")).toBe(true);
    // Both ways round.
    expect(matchesWallet({ name: "Straße AG", symbol: "STR" }, "strasse")).toBe(true);
    expect(matchesWallet({ name: "Strasse AG", symbol: "STR" }, "straße")).toBe(true);
    expect(matchesWallet({ name: "Ørsted", symbol: "DNNGY" }, "ØRSTED")).toBe(true);
  });

  it("finds nothing for a search without a letter or a digit", () => {
    expect(matchesWallet(sp500, "&")).toBe(false);
    expect(matchesWallet(sp500, "")).toBe(false);
  });
});

describe("allFit", () => {
  it("wants room for both parts of every cell that has a second", () => {
    expect(allFit([{ room: 200, first: 60, second: 70 }, { room: 200, first: 62, second: 90 }], 14)).toBe(true);
    expect(allFit([{ room: 140, first: 60, second: 70 }, { room: 200, first: 62, second: 90 }], 14)).toBe(false);
    expect(allFit([{ room: 150, first: 60, second: 70 }, { room: 150, first: 140 }], 14)).toBe(true);
    expect(allFit([{ room: 150, first: 40 }], 14)).toBe(false);
    expect(allFit([], 14)).toBe(false);
  });
});

describe("the shared styles", () => {
  it("mix the chips' background from the theme's text colour, not from its RGB variable", async () => {
    // A theme that sets its text colour as a var() -- Noctis does -- leaves
    // Home Assistant nothing to derive --rgb-primary-text-color from: it stays
    // the light default, near black, and a chip on a dark card vanished.
    const { cardStyles } = await import("../src/styles");
    const css = cardStyles.cssText.replace(/\/\*[\s\S]*?\*\//g, "");
    expect(css.match(/--bp-chip:\s*([^;]*);/)?.[1]).toBe("color-mix(in srgb, var(--primary-text-color, #212121) 6%, transparent)");
    expect(css).not.toMatch(/--rgb-/);
  });

  it("set the staked share right below the units and the detail as wide as its row", async () => {
    const { cardStyles } = await import("../src/styles");
    const css = cardStyles.cssText;
    // A flex line leaves no line gap above the badge.
    expect(css.match(/\.stake\s*\{([^}]*)\}/)?.[1]).toMatch(/display:\s*flex/);
    // Beside the units when every staked row has room: right after them in
    // a wide card, where the return has a column of its own; at the right
    // edge in a narrow one, where the return goes below.
    expect(css.match(/\.wallets\.stake-inline \.sub\.staked\s*\{([^}]*)\}/)?.[1]).toMatch(/flex-direction:\s*row/);
    expect(css.match(/\.wallets\.stake-inline \.sub\.staked\s*\{([^}]*)\}/)?.[1]).toMatch(/justify-content:\s*flex-start/);
    // Never at the right edge, where a row's value usually stands.
    expect(css).not.toMatch(/\.wallets\.stake-inline \.sub(\.staked)?\s*\{[^}]*space-between/);
    // Only rows with a staked share: a row without one keeps its units free
    // to wrap, such as an ETF's units and ISIN.
    expect(css).not.toMatch(/\.wallets\.stake-inline \.sub\s*\{/);
    expect(css).not.toMatch(/\.wallets\.stake-inline \.sub > \*/);
    expect(css.match(/\.wallets\.stake-inline \.sub\.staked > \*\s*\{([^}]*)\}/)?.[1]).toMatch(/flex-shrink:\s*0/);
    // Full width in the list, indented like its row inside an open group.
    expect(css.match(/\.detail\s*\{([^}]*)\}/)?.[1]).toMatch(/margin:\s*0 0 8px;/);
    expect(css.match(/\.members \.detail\s*\{([^}]*)\}/)?.[1]).toMatch(/margin-left:\s*24px/);
    // Labels stay on one line; a long value wraps instead.
    expect(css.match(/\.detail \.grid > span:nth-child\(odd\)\s*\{([^}]*)\}/)?.[1]).toMatch(/white-space:\s*nowrap/);
    expect(css.match(/\.detail \.grid\s*\{([^}]*)\}/)?.[1]).toMatch(/grid-template-columns:\s*auto minmax\(0, 1fr\)/);
    // A detail value breaks only at its middle dots, except in very narrow
    // cards, where a part may not fit a line on its own.
    expect(css.match(/\.detail \.part\s*\{([^}]*)\}/)?.[1]).toMatch(/white-space:\s*nowrap/);
    const tiny = css.slice(css.indexOf("@container (max-width: 240px)"));
    // From 280 px down each detail label stands above its value, which then
    // has the whole width for its parts.
    const stacked = css.slice(css.indexOf("@container (max-width: 280px)"), css.indexOf("@container (max-width: 240px)"));
    expect(stacked).toMatch(/\.detail \.grid\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)/);
    expect(tiny).toMatch(/\.detail \.part\s*\{[^}]*white-space:\s*normal/);
  });

  it("put a row's chip above its value, beside the units, below the name side by side, or below it stacked", async () => {
    const { cardStyles } = await import("../src/styles");
    const css = cardStyles.cssText;
    const rule = (selector: string): string | undefined =>
      css.match(new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\{([^}]*)\\}`))?.[1];
    // A wallet's name: two lines at most, then "…"; over two lines, two of
    // about the same length, as in the Price Tracker's list.
    expect(rule(".n")).toMatch(/-webkit-line-clamp:\s*2/);
    expect(rule(".wallet .n")).toMatch(/text-wrap:\s*balance/);
    expect(rule(".wallet .right")).toMatch(/flex-direction:\s*column/);
    expect(rule(".wallet .right")).toMatch(/align-items:\s*flex-end/);
    expect(rule(".wallets.rows-wrapped .wallet .tap")).toMatch(/flex-wrap:\s*wrap/);
    expect(rule(".wallets.rows-wrapped .wallet .main")).toMatch(/flex-basis:\s*100%/);
    expect(rule(".wallets.rows-wrapped .wallet")).toMatch(/align-items:\s*flex-start/);
    expect(rule(".wallets.rows-wrapped .wallet .right")).toMatch(/flex-direction:\s*row/);
    expect(rule(".wallets.rows-wrapped .wallet .right")).toMatch(/justify-content:\s*flex-end/);
    expect(rule(".wallets.rows-stacked .wallet .right")).toMatch(/flex-direction:\s*column/);
    expect(css.indexOf(".wallets.rows-stacked .wallet .right")).toBeGreaterThan(css.indexOf(".wallets.rows-wrapped .wallet .right"));
    // The card measures; no fixed width moves a row any more.
    for (const block of css.match(/@container[^{]*\{[\s\S]*?\n  \}/g) ?? []) expect(block).not.toMatch(/\.wallet\b/);
    // Chip, value and ISIN hold together; the units may wrap.
    expect(css.match(/\.gchip,\s*\.wchip,\s*\.pchip\s*\{([^}]*)\}/)?.[1]).toMatch(/white-space:\s*nowrap/);
    expect(css.match(/\.gchip\.none,\s*\.wchip\.none,\s*\.pchip\.none\s*\{([^}]*)\}/)?.[1]).toMatch(/background:\s*none/);
    expect(rule(".val")).toMatch(/white-space:\s*nowrap/);
    expect(rule(".s .isin")).toMatch(/white-space:\s*nowrap/);
    expect(css).not.toMatch(/\.units\s*\{[^}]*nowrap/);
  });

  it("never wrap a return chip and adapt to narrow cards", async () => {
    const { cardStyles } = await import("../src/styles");
    const css = cardStyles.cssText;
    expect(css.match(/\.chip\s*\{([^}]*)\}/)?.[1]).toMatch(/white-space:\s*nowrap/);
    expect(css.match(/\.chip-label\s*\{([^}]*)\}/)?.[1]).toMatch(/white-space:\s*nowrap/);
    expect(css.match(/\.chip-amount\s*\{([^}]*)\}/)?.[1]).toMatch(/white-space:\s*nowrap/);
    expect(css.match(/\.hero-line\s*\{([^}]*)\}/)?.[1]).toMatch(/flex-wrap:\s*wrap/);
    expect(css).toMatch(/container-type:\s*inline-size/);
    expect(css).toMatch(/@container\s*\(max-width:\s*\d+px\)/);
    // A half-width card in a four-column dashboard: about 170 px.
    const tiny = css.match(/@container\s*\(max-width:\s*(\d+)px\)\s*\{([\s\S]*?)\n  \}/g)?.find((rule) => /max-width:\s*240px/.test(rule)) ?? "";
    expect(tiny).toMatch(/\.seg \[role="radio"\]\s*\{[^}]*padding:\s*4px 4px/);
  });
});

describe("the pointer", () => {
  it("follows what is a button, not a class: a piece the eye or a missing sensor makes no button gets none", async () => {
    const { PriceTrackerCard } = await import("../src/price-tracker-card");
    const css = (PriceTrackerCard.styles as { cssText: string }[])
      .map((sheet) => sheet.cssText)
      .join("\n")
      .replace(/\/\*[\s\S]*?\*\//g, "");
    const rules = [...css.matchAll(/([^{}]+)\{([^}]*)\}/g)].map((match) => ({
      selectors: (match[1] ?? "").split(",").map((selector) => selector.trim()),
      body: match[2] ?? "",
    }));
    expect(rules.some((rule) => rule.selectors.includes('[role="button"]') && /cursor:\s*pointer/.test(rule.body))).toBe(true);
    const pieces = [".hero", ".chip", ".pair > div", ".wallet .tap", ".staking", ".staking-row", ".since-chip", ".since-amount", ".price-row", ".tile"];
    for (const selector of pieces) {
      const pointed = rules.filter((rule) => rule.selectors.includes(selector) && /cursor/.test(rule.body));
      expect(pointed, selector).toEqual([]);
    }
  });
});

describe("unbroken", () => {
  it("keeps the placeholder's value in one piece and the text around it as it is", () => {
    const host = mount(unbroken("Change since {date} here", "date", "Oct 14"));
    expect(textOf(host)).toBe("Change since Oct 14 here");
    expect(textOf(host.querySelector(".nw"))).toBe("Oct 14");
  });

  it("leaves a text without the placeholder as it is", () => {
    const host = mount(unbroken("No date", "date", "Oct 14"));
    expect(textOf(host)).toBe("No date");
    expect(host.querySelector(".nw")).toBeNull();
  });
});
