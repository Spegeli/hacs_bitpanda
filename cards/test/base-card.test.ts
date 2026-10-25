import { html } from "lit";
import { describe, expect, it, vi } from "vitest";

import { BitpandaCard, COMMON_OPTIONS } from "../src/base-card";
import { findPortfolio } from "../src/discovery";
import { bool, oneOf, validateConfig } from "../src/forms";
import { languageOf } from "../src/i18n";
import { DOCS_URL, defineCard, suggestCard } from "../src/register";
import { TIMEFRAMES, type BaseConfig, type Timeframe } from "../src/types";
import { BTC, makeHass, portfolioDevice, priceDevice, walletDevice } from "./fixtures";

interface TestConfig extends BaseConfig {
  timeframe?: Timeframe;
  hide_amounts?: boolean;
}

class TestCard extends BitpandaCard<TestConfig> {
  renders = 0;

  protected validate(config: unknown): TestConfig {
    return validateConfig<TestConfig>(config, { ...COMMON_OPTIONS, timeframe: oneOf(TIMEFRAMES), hide_amounts: bool });
  }

  protected watchedEntities(): string[] {
    const refs = this.hass ? findPortfolio(this.hass) : undefined;
    return refs?.totalValue ? [refs.totalValue] : [];
  }

  get shownTimeframe(): Timeframe {
    return this.timeframe;
  }

  get isHidden(): boolean {
    return this.amountsHidden;
  }

  toggle(): void {
    this.toggleAmounts();
  }

  pick(timeframe: Timeframe): void {
    this.selectTimeframe(timeframe);
  }

  get currentConfig(): TestConfig | undefined {
    return this.config;
  }

  protected override render() {
    this.renders += 1;
    return html`<div class="t">${this.timeframe}</div>`;
  }
}
customElements.define("bitpanda-test-card", TestCard);

async function mounted(config: Record<string, unknown> = {}) {
  const card = document.createElement("bitpanda-test-card") as TestCard;
  card.setConfig({ type: "custom:bitpanda-test-card", ...config });
  const hass = makeHass({
    devices: [portfolioDevice(), walletDevice(BTC)],
    foreign: [{ entityId: "sensor.kitchen", translationKey: "temperature", state: "21" }],
  });
  card.hass = hass;
  document.body.append(card);
  await card.updateComplete;
  return { card, hass };
}

describe("BitpandaCard", () => {
  it("does not re-render for a foreign entity", async () => {
    const { card, hass } = await mounted();
    const before = card.renders;
    const next = hass.withState("sensor.kitchen", "22");
    card.hass = next;
    await card.updateComplete;
    card.hass = next.withState("sensor.bitpanda_btc_wallet", "1");
    await card.updateComplete;
    expect(card.renders).toBe(before);
  });

  it("renders once hass arrives after the configuration", async () => {
    const card = document.createElement("bitpanda-test-card") as TestCard;
    card.setConfig({ type: "custom:bitpanda-test-card" });
    document.body.append(card);
    await card.updateComplete;
    const before = card.renders;
    card.hass = makeHass({ devices: [portfolioDevice()] });
    await card.updateComplete;
    expect(card.renders).toBe(before + 1);
  });

  it("re-renders when a watched entity changes", async () => {
    const { card, hass } = await mounted();
    const before = card.renders;
    card.hass = hass.withState("sensor.bitpanda_portfolio_total_value", "13000");
    await card.updateComplete;
    expect(card.renders).toBe(before + 1);
  });

  it("re-renders when the registries or the language change", async () => {
    const { card, hass } = await mounted();
    const before = card.renders;
    card.hass = { ...hass, entities: { ...hass.entities } };
    await card.updateComplete;
    card.hass = { ...hass, locale: { ...hass.locale, language: "de" } };
    await card.updateComplete;
    expect(card.renders).toBe(before + 2);
  });

  it("starts with the configured timeframe, and the switch is not written to the config", async () => {
    const { card } = await mounted({ timeframe: "week" });
    expect(card.shownTimeframe).toBe("week");
    card.pick("year");
    await card.updateComplete;
    expect(card.shownTimeframe).toBe("year");
    expect(card.currentConfig?.timeframe).toBe("week");
  });

  it("hide_amounts starts the card blurred and the eye toggles it, without touching the config", async () => {
    const { card } = await mounted({ hide_amounts: true });
    expect(card.isHidden).toBe(true);
    card.toggle();
    expect(card.isHidden).toBe(false);
    expect(card.currentConfig?.hide_amounts).toBe(true);
    const plain = await mounted();
    expect(plain.card.isHidden).toBe(false);
    expect(plain.card.shownTimeframe).toBe("day");
  });

  it("setConfig rejects an invalid value", () => {
    const card = document.createElement("bitpanda-test-card") as TestCard;
    expect(() => card.setConfig({ type: "custom:bitpanda-test-card", title: 5 })).toThrowError(/title/);
  });

  it("remembers the viewer's language and loads category names once per language", async () => {
    const { card, hass } = await mounted();
    const load = vi.fn(async () => undefined);
    card.hass = { ...hass, loadBackendTranslation: load, locale: { ...hass.locale, language: "fr" } };
    await card.updateComplete;
    card.hass = { ...card.hass, entities: { ...hass.entities } };
    await card.updateComplete;
    expect(load).toHaveBeenCalledTimes(1);
    expect(languageOf()).toBe("fr");
    card.hass = hass;
    await card.updateComplete;
  });

  it("has a size for masonry and sections views", async () => {
    const { card } = await mounted();
    expect(card.getCardSize()).toBe(3);
    expect(card.getGridOptions()).toEqual({ columns: 12, min_columns: 6 });
  });
});

describe("registration", () => {
  it("defineCard registers once and lists the card for the picker once", async () => {
    class One extends HTMLElement {}
    class Two extends HTMLElement {}
    defineCard("bitpanda-once-card", One, { name: "Once", description: () => "Shown once." });
    defineCard("bitpanda-once-card", Two, { name: "Once", description: () => "Shown once." });
    await customElements.whenDefined("bitpanda-once-card");
    await Promise.resolve();
    expect(customElements.get("bitpanda-once-card")).toBe(One);
    const entries = (window as unknown as { customCards: Record<string, unknown>[] }).customCards.filter(
      (entry) => entry["type"] === "bitpanda-once-card",
    );
    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({ name: "Once", description: "Shown once.", preview: true, documentationURL: DOCS_URL });
    expect(DOCS_URL).toBe("https://github.com/Spegeli/hacs_bitpanda#-dashboard-cards");
  });

  it("a card with a model suggests itself through its picker entry, with its picker start", () => {
    class Three extends HTMLElement {
      static getStubConfig(): Record<string, unknown> {
        return { timeframe: "day" };
      }
    }
    defineCard("bitpanda-suggesting-card", Three, { name: "S", description: () => "S.", model: "Wallet" });
    const entry = (window as unknown as { customCards: Record<string, unknown>[] }).customCards.find(
      (item) => item["type"] === "bitpanda-suggesting-card",
    ) as { getEntitySuggestion: (hass: unknown, entityId: string) => unknown };
    const hass = makeHass({ devices: [portfolioDevice(), walletDevice(BTC)] });
    expect(entry.getEntitySuggestion(hass, "sensor.bitpanda_btc_wallet_total")).toEqual({
      config: { type: "custom:bitpanda-suggesting-card", timeframe: "day" },
    });
  });

  it("suggestCard answers only for its model", () => {
    const hass = makeHass({
      devices: [
        portfolioDevice(),
        walletDevice(BTC),
        priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { EUR: { state: "1" } } }),
      ],
      foreign: [{ entityId: "sensor.kitchen", translationKey: "temperature", state: "21" }],
    });
    expect(suggestCard(hass, "sensor.bitpanda_portfolio_total_value", "Portfolio", "bitpanda-portfolio-card")).toEqual({
      config: { type: "custom:bitpanda-portfolio-card" },
    });
    expect(suggestCard(hass, "sensor.bitpanda_btc_wallet", "Portfolio", "bitpanda-portfolio-card")).toBeNull();
    expect(suggestCard(hass, "sensor.bitpanda_btc_price_tracker_eur", "Price Tracker", "bitpanda-price-tracker-card")).not.toBeNull();
    expect(suggestCard(hass, "sensor.kitchen", "Wallet", "bitpanda-wallets-card")).toBeNull();
    expect(suggestCard(hass, "sensor.nothing", "Wallet", "bitpanda-wallets-card")).toBeNull();
  });
});
