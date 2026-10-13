import { afterEach, describe, expect, it } from "vitest";

import "../src/index";
import { makeHass } from "./fixtures";

const TAGS = ["bitpanda-portfolio-card", "bitpanda-price-tracker-card"];

afterEach(() => {
  document.body.innerHTML = "";
});

describe("every card", () => {
  it("is defined by the bundle's entry point and listed in the card picker", () => {
    const listed = (window as unknown as { customCards: { type: string; name: string }[] }).customCards.map((entry) => entry.type);
    for (const tag of TAGS) {
      expect(customElements.get(tag), tag).toBeDefined();
      expect(listed, tag).toContain(tag);
    }
  });

  it("describes itself in the card picker in Home Assistant's language", () => {
    const entry = (tag: string) =>
      (window as unknown as { customCards: { type: string; description: string }[] }).customCards.find((item) => item.type === tag);
    expect(entry("bitpanda-portfolio-card")?.description).toBe(
      "Total value and return with a value line, Cash and Cash Plus, allocation and your wallets; each part can be left out.",
    );
    expect(entry("bitpanda-price-tracker-card")?.description).toBe("Prices and changes of the assets you track, each with a line, as a list or tiles.");
    // The picker reads the description when it opens: in the language of
    // Home Assistant's own state on the page's root element.
    const root = document.createElement("home-assistant") as HTMLElement & { hass?: unknown };
    root.hass = makeHass({ language: "de" });
    document.body.append(root);
    expect(entry("bitpanda-price-tracker-card")?.description).toBe("Preise und Änderungen deiner verfolgten Assets, je mit Verlauf, als Liste oder Kacheln.");
  });

  it("renders nothing before hass arrives, then its card", async () => {
    for (const tag of TAGS) {
      const card = document.createElement(tag) as HTMLElement & {
        setConfig(config: unknown): void;
        hass?: unknown;
        updateComplete: Promise<boolean>;
      };
      card.setConfig({ type: `custom:${tag}` });
      document.body.append(card);
      await card.updateComplete;
      expect(card.shadowRoot?.querySelector("ha-card"), tag).toBeNull();
      card.hass = makeHass();
      await card.updateComplete;
      expect(card.shadowRoot?.querySelector("ha-card .empty"), tag).not.toBeNull();
    }
  });

  it("the editor shows each toggle's, number's and title's default", async () => {
    // Home Assistant's form shows a field's default where the configuration
    // has no value (greyed for the title and numbers), and saves nothing.
    interface Field {
      name: string;
      default?: unknown;
      schema?: Field[];
    }
    const defaults = async (tag: string): Promise<Record<string, unknown>> => {
      const form = await (customElements.get(tag) as unknown as { getConfigForm(): Promise<{ schema: Field[] }> }).getConfigForm();
      const flat = (fields: Field[]): Field[] => fields.flatMap((field) => (field.schema ? flat(field.schema) : [field]));
      return Object.fromEntries(flat(form.schema).filter((field) => "default" in field).map((field) => [field.name, field.default]));
    };
    expect(await defaults("bitpanda-portfolio-card")).toEqual({
      title: "Bitpanda Portfolio",
      show_total: true,
      show_graph: true,
      show_cash: true,
      show_allocation: true,
      show_wallets: true,
      group_wallets: true,
      show_search: false,
      limit: 5,
      hide_amounts: false,
    });
    expect(await defaults("bitpanda-price-tracker-card")).toEqual({ title: "Bitpanda Price Tracker", limit: 0 });
  });

  it("a card added from the picker starts with its choices written out", () => {
    // Home Assistant's select fields cannot show a default: the picker's
    // card carries them, so the editor shows them selected.
    const stub = (tag: string): unknown => (customElements.get(tag) as unknown as { getStubConfig(): unknown }).getStubConfig();
    expect(stub("bitpanda-portfolio-card")).toEqual({ timeframe: "day", sort: "value", group_selection: "all", asset_selection: "all" });
    expect(stub("bitpanda-price-tracker-card")).toEqual({
      layout: "list",
      timeframe: "day",
      currency: "EUR",
      sort: "name",
      group_selection: "all",
      asset_selection: "all",
    });
    for (const tag of TAGS) {
      const card = document.createElement(tag) as HTMLElement & { setConfig(config: unknown): void };
      expect(() => card.setConfig({ type: `custom:${tag}`, ...(stub(tag) as object) }), tag).not.toThrow();
    }
  });

  it("rejects an invalid option with Home Assistant's error card reason", () => {
    for (const tag of TAGS) {
      const card = document.createElement(tag) as HTMLElement & { setConfig(config: unknown): void };
      expect(() => card.setConfig({ type: `custom:${tag}`, timeframe: "decade" }), tag).toThrowError(/Invalid value for “timeframe”/);
      expect(() => card.setConfig({ type: `custom:${tag}`, group_selection: "some" }), tag).toThrowError(/Invalid value for “group_selection”/);
      expect(() => card.setConfig({ type: `custom:${tag}`, groups: ["future"] }), tag).toThrowError(/Invalid value for “groups”/);
    }
  });

  it("every choice in the editors is a dropdown, one line each", async () => {
    type Field = { name: string; schema?: Field[]; selector?: { select?: { mode?: string } } };
    const flat = (fields: Field[]): Field[] => fields.flatMap((field) => (field.schema ? flat(field.schema) : [field]));
    for (const tag of TAGS) {
      const form = await (customElements.get(tag) as unknown as { getConfigForm(): Promise<{ schema: Field[] }> }).getConfigForm();
      const choices = flat(form.schema).filter((field) => field.selector?.select);
      expect(choices.length, tag).toBeGreaterThan(3);
      for (const field of choices) expect(field.selector?.select?.mode, `${tag} ${field.name}`).toBe("dropdown");
    }
  });

  it("the editors ask Home Assistant for the group names, and open with the groups' keys when that fails", async () => {
    // getConfigForm gets no hass: it takes Home Assistant's own from the
    // page's root element. A translation load replaces that hass with one
    // whose localize knows the names, so the names are asked for directly.
    type Field = { name: string; schema?: Field[]; selector?: { select?: { options: { value: string; label: string }[] } } };
    const flat = (fields: Field[]): Field[] => fields.flatMap((field) => (field.schema ? flat(field.schema) : [field]));
    const firstGroup = async (tag: string) => {
      const form = await (customElements.get(tag) as unknown as { getConfigForm(): Promise<{ schema: Field[] }> }).getConfigForm();
      return flat(form.schema).find((field) => field.name === "groups")?.selector?.select?.options[0];
    };
    const root = document.createElement("home-assistant") as HTMLElement & { hass?: unknown };
    document.body.append(root);
    root.hass = makeHass({
      callWS: async (message) => {
        if (message["type"] !== "frontend/get_translations") throw new Error("unexpected call");
        return { resources: { "component.bitpanda.selector.asset_group.options.crypto": "Cryptocurrencies" } };
      },
    });
    for (const tag of TAGS) expect(await firstGroup(tag), tag).toEqual({ value: "crypto", label: "Cryptocurrencies" });
    const failing = makeHass({
      callWS: async () => {
        throw new Error("connection lost");
      },
    });
    failing.loadBackendTranslation = async () => {
      throw new Error("connection lost");
    };
    root.hass = failing;
    for (const tag of TAGS) expect(await firstGroup(tag), tag).toEqual({ value: "crypto", label: "crypto" });
  });
});
