import { describe, expect, it, vi } from "vitest";

import { ensureHaForm } from "../src/editor";
import "../src/index";
import { BTC, ETH, makeHass, openEditor, priceDevice, walletDevice } from "./fixtures";
import { rememberLocale } from "../src/i18n";

const TAGS = ["bitpanda-portfolio-card", "bitpanda-price-tracker-card"] as const;

describe("the cards' editors", () => {
  it("each card hands Home Assistant its own editor", async () => {
    const portfolio = await (customElements.get(TAGS[0]) as unknown as { getConfigElement(): Promise<HTMLElement> }).getConfigElement();
    const tracker = await (customElements.get(TAGS[1]) as unknown as { getConfigElement(): Promise<HTMLElement> }).getConfigElement();
    expect(portfolio.tagName.toLowerCase()).toBe("bitpanda-portfolio-card-editor");
    expect(tracker.tagName.toLowerCase()).toBe("bitpanda-price-tracker-card-editor");
    for (const tag of TAGS) expect((customElements.get(tag) as unknown as { getConfigForm?: unknown }).getConfigForm, tag).toBeUndefined();
  });

  it("draws Home Assistant's form with the configuration and Home Assistant's state", async () => {
    const hass = makeHass();
    for (const tag of TAGS) {
      const { form } = await openEditor(tag, { timeframe: "week" }, hass);
      expect(form, tag).toBeTruthy();
      expect(form.hass, tag).toBe(hass);
      expect(form.data, tag).toMatchObject({ type: `custom:${tag}`, timeframe: "week" });
      expect(form.schema.length, tag).toBeGreaterThan(1);
    }
  });

  it("tells Home Assistant every change as config-changed", async () => {
    for (const tag of TAGS) {
      const { editor, form } = await openEditor(tag, { timeframe: "week" }, makeHass());
      const seen: unknown[] = [];
      editor.addEventListener("config-changed", (ev) => seen.push((ev as CustomEvent<{ config: unknown }>).detail.config));
      const outside = vi.fn();
      document.body.addEventListener("value-changed", outside);
      form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { type: `custom:${tag}`, timeframe: "month" } }, bubbles: true, composed: true }));
      document.body.removeEventListener("value-changed", outside);
      expect(seen, tag).toEqual([{ type: `custom:${tag}`, timeframe: "month" }]);
      // Home Assistant's own form event stays inside the editor.
      expect(outside, tag).not.toHaveBeenCalled();
    }
  });
});

describe("ensureHaForm", () => {
  const registry = (defined: boolean) => {
    let resolve: () => void = () => undefined;
    const ready = new Promise<CustomElementConstructor>((done) => {
      resolve = () => done(HTMLElement);
    });
    const state = { defined };
    return {
      state,
      define: () => {
        state.defined = true;
        resolve();
      },
      get: (name: string) => (name === "ha-form" && state.defined ? HTMLElement : undefined),
      whenDefined: () => ready,
    };
  };

  it("does nothing when Home Assistant's form is loaded already", async () => {
    const fake = registry(true);
    const loadCardHelpers = vi.fn();
    await ensureHaForm(fake, { loadCardHelpers }, 50);
    expect(loadCardHelpers).not.toHaveBeenCalled();
  });

  it("loads Home Assistant's form through a built-in card's editor when it is not loaded yet", async () => {
    const fake = registry(false);
    const getConfigElement = vi.fn(async () => {
      fake.define();
      return document.createElement("div");
    });
    class Entities extends HTMLElement {
      static getConfigElement = getConfigElement;
    }
    const createCardElement = vi.fn(async () => Object.create(Entities.prototype) as HTMLElement);
    await ensureHaForm(fake, { loadCardHelpers: async () => ({ createCardElement }) }, 5000);
    expect(createCardElement).toHaveBeenCalledWith({ type: "entities", entities: [] });
    expect(getConfigElement).toHaveBeenCalledOnce();
    expect(fake.state.defined).toBe(true);
  });

  it("opens all the same when Home Assistant has no card helpers or they fail", async () => {
    await expect(ensureHaForm(registry(false), {}, 20)).resolves.toBeUndefined();
    const failing = { loadCardHelpers: async () => Promise.reject(new Error("no helpers")) };
    await expect(ensureHaForm(registry(false), failing, 20)).resolves.toBeUndefined();
  });
});

describe("the editors' fields", () => {
  const names = (fields: { name: string; schema?: unknown[] }[]): string[] =>
    fields.flatMap((field) => (field.schema ? names(field.schema as { name: string }[]) : [field.name]));

  for (const tag of TAGS) {
    it(`${tag}: shows the asset groups to choose only while groups are chosen`, async () => {
      expect(names((await openEditor(tag, {}, makeHass())).form.schema)).not.toContain("groups");
      expect(names((await openEditor(tag, { group_selection: "all" }, makeHass())).form.schema)).not.toContain("groups");
      expect(names((await openEditor(tag, { group_selection: "only" }, makeHass())).form.schema)).toContain("groups");
      expect(names((await openEditor(tag, { group_selection: "all_except" }, makeHass())).form.schema)).toContain("groups");
    });

    it(`${tag}: shows the assets to choose only while assets are chosen`, async () => {
      expect(names((await openEditor(tag, {}, makeHass())).form.schema)).not.toContain("assets");
      expect(names((await openEditor(tag, { asset_selection: "only" }, makeHass())).form.schema)).toContain("assets");
      expect(names((await openEditor(tag, { asset_selection: "all_except" }, makeHass())).form.schema)).toContain("assets");
    });

    it(`${tag}: saves no chosen assets or groups with "all", but brings them back while the editor is open`, async () => {
      const { editor, form } = await openEditor(tag, { asset_selection: "only", assets: ["x"], group_selection: "only", groups: ["crypto"] }, makeHass());
      const seen: Record<string, unknown>[] = [];
      editor.addEventListener("config-changed", (ev) => seen.push((ev as CustomEvent<{ config: Record<string, unknown> }>).detail.config));
      form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, asset_selection: "all", group_selection: "all" } } }));
      // "All" names nothing: saved like this, the choices are gone.
      expect(seen.at(-1)).toEqual({ type: `custom:${tag}`, asset_selection: "all", group_selection: "all" });
      await editor.updateComplete;
      // Switched back in the same editor: the choices made before.
      form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, asset_selection: "all_except", group_selection: "only" } } }));
      expect(seen.at(-1)).toEqual({ type: `custom:${tag}`, asset_selection: "all_except", assets: ["x"], group_selection: "only", groups: ["crypto"] });
    });

    it(`${tag}: drops chosen assets that no selection uses at the next change`, async () => {
      // A configuration from before, its assets left behind with "all" -- or
      // with no selection at all, which means "all".
      for (const config of [{ asset_selection: "all", assets: ["x"] }, { assets: ["x"], groups: ["crypto"] }]) {
        const { editor, form } = await openEditor(tag, config, makeHass());
        const seen: Record<string, unknown>[] = [];
        editor.addEventListener("config-changed", (ev) => seen.push((ev as CustomEvent<{ config: Record<string, unknown> }>).detail.config));
        form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, timeframe: "week" } } }));
        expect(seen.at(-1)?.["assets"], JSON.stringify(config)).toBeUndefined();
        expect(seen.at(-1)?.["groups"], JSON.stringify(config)).toBeUndefined();
      }
    });
  }

  it("shows the default of a choice left empty", async () => {
    expect((await openEditor(TAGS[0], {}, makeHass())).form.data).toEqual({
      type: `custom:${TAGS[0]}`, timeframe: "day", sort: "value", group_selection: "all", asset_selection: "all",
    });
    expect((await openEditor(TAGS[1], {}, makeHass())).form.data).toEqual({
      type: `custom:${TAGS[1]}`, layout: "list", timeframe: "day", currency: "EUR", sort: "name", group_selection: "all", asset_selection: "all",
    });
    // A choice made stays as made.
    expect((await openEditor(TAGS[1], { timeframe: "week", currency: "USD" }, makeHass())).form.data).toMatchObject({ timeframe: "week", currency: "USD" });
  });

  it("writes a shown default only when the user picks something else", async () => {
    for (const tag of TAGS) {
      const { editor, form } = await openEditor(tag, { show_total: true }, makeHass());
      const seen: Record<string, unknown>[] = [];
      editor.addEventListener("config-changed", (ev) => seen.push((ev as CustomEvent<{ config: Record<string, unknown> }>).detail.config));
      form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, show_total: false } } }));
      await editor.updateComplete;
      expect(seen.at(-1), tag).toEqual({ type: `custom:${tag}`, show_total: false });
      form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, timeframe: "month" } } }));
      expect(seen.at(-1), tag).toEqual({ type: `custom:${tag}`, show_total: false, timeframe: "month" });
    }
    // A choice written out before -- a card added from the picker -- stays written out.
    const { editor, form } = await openEditor(TAGS[0], { timeframe: "day", sort: "value" }, makeHass());
    const seen: Record<string, unknown>[] = [];
    editor.addEventListener("config-changed", (ev) => seen.push((ev as CustomEvent<{ config: Record<string, unknown> }>).detail.config));
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, hide_amounts: true } } }));
    expect(seen.at(-1)).toEqual({ type: `custom:${TAGS[0]}`, timeframe: "day", sort: "value", hide_amounts: true });
  });
});

describe("the editors' asset choice", () => {
  const wallets = () => makeHass({ devices: [walletDevice(BTC), walletDevice(ETH)] });
  const prices = () =>
    makeHass({
      devices: [
        priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { EUR: { state: "70000" } } }),
        priceDevice({ symbol: "SOL", name: "Solana", category: "crypto", prices: { EUR: { state: "150" } } }),
        walletDevice(ETH),
      ],
    });
  const changes = (editor: HTMLElement): Record<string, unknown>[] => {
    const seen: Record<string, unknown>[] = [];
    editor.addEventListener("config-changed", (ev) => seen.push((ev as CustomEvent<{ config: Record<string, unknown> }>).detail.config));
    return seen;
  };
  const helper = (form: { computeHelper: (field: { name: string }) => string | undefined }) => form.computeHelper({ name: "assets" }) ?? "";

  it("shows the devices of stored asset IDs and of old device IDs", async () => {
    const { form } = await openEditor(TAGS[0], { asset_selection: "only", assets: ["id-eth", "dev-wallet-btc"] }, wallets());
    expect(form.data["assets"]).toEqual(["dev-wallet-eth", "dev-wallet-btc"]);
  });

  it("saves the asset IDs of the devices picked, in the order picked", async () => {
    const { editor, form } = await openEditor(TAGS[1], { asset_selection: "only", assets: [] }, prices());
    const seen = changes(editor);
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, assets: ["dev-price-sol", "dev-price-btc"] } } }));
    expect(seen.at(-1)?.["assets"]).toEqual(["id-sol", "id-btc"]);
  });

  it("converts old device IDs to asset IDs once the card is edited", async () => {
    const { editor, form } = await openEditor(TAGS[0], { asset_selection: "only", assets: ["dev-wallet-btc"] }, wallets());
    const seen = changes(editor);
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, hide_amounts: true } } }));
    expect(seen.at(-1)).toMatchObject({ assets: ["id-btc"], hide_amounts: true });
  });

  it("shows an asset named twice, as device and as asset ID, once, and saves it once", async () => {
    const { editor, form } = await openEditor(TAGS[0], { asset_selection: "only", assets: ["dev-wallet-btc", "id-btc"] }, wallets());
    expect(form.data["assets"]).toEqual(["dev-wallet-btc"]);
    const seen = changes(editor);
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data } } }));
    expect(seen.at(-1)?.["assets"]).toEqual(["id-btc"]);
  });

  it("keeps an asset without a device and says so", async () => {
    const { editor, form } = await openEditor(TAGS[1], { asset_selection: "all_except", assets: ["id-gone", "id-btc"] }, prices());
    expect(form.data["assets"]).toEqual(["dev-price-btc"]);
    expect(helper(form)).toBe(
      "An asset from a hidden asset group stays hidden, even when chosen here. This includes a chosen asset that is not there right now. It stays saved and applies again once it is back.",
    );
    const seen = changes(editor);
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, assets: ["dev-price-sol"] } } }));
    expect(seen.at(-1)?.["assets"]).toEqual(["id-sol", "id-gone"]);
  });

  it("says in German how many chosen assets are missing", async () => {
    const hass = makeHass({ devices: [walletDevice(BTC)], language: "de" });
    const one = await openEditor(TAGS[0], { asset_selection: "only", assets: ["id-gone"] }, hass);
    expect(helper(one.form)).toContain("Dazu gehört ein gewähltes Asset, das es gerade nicht gibt. Es bleibt gespeichert und gilt wieder, sobald es wieder da ist.");
    const two = await openEditor(TAGS[0], { asset_selection: "only", assets: ["id-gone", "id-away"] }, hass);
    expect(helper(two.form)).toContain(
      "Dazu gehören 2 gewählte Assets, die es gerade nicht gibt. Sie bleiben gespeichert und gelten wieder, sobald sie wieder da sind.",
    );
    rememberLocale(makeHass());
  });

  it("counts a device of the other card's model as missing, and keeps it", async () => {
    const { editor, form } = await openEditor(TAGS[1], { asset_selection: "only", assets: ["dev-wallet-eth"] }, prices());
    expect(form.data["assets"]).toEqual([]);
    expect(helper(form)).toContain("not there right now");
    const seen = changes(editor);
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, timeframe: "week" } } }));
    expect(seen.at(-1)?.["assets"]).toEqual(["dev-wallet-eth"]);
  });

  it("drops nothing while Home Assistant has no devices yet", async () => {
    const { editor, form } = await openEditor(TAGS[0], { asset_selection: "only", assets: ["id-btc", "dev-wallet-eth"] }, makeHass());
    const seen = changes(editor);
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, timeframe: "week" } } }));
    expect(seen.at(-1)?.["assets"]).toEqual(["id-btc", "dev-wallet-eth"]);
  });

  it("knows a wallet whose sensors are all disabled by its device, and saves its asset ID", async () => {
    // Disabled entities are not in Home Assistant's frontend registry, the
    // device is: the device picker offers it.
    const hass = wallets();
    for (const [entityId, entry] of Object.entries(hass.entities)) if (entry?.device_id === "dev-wallet-eth") delete hass.entities[entityId];
    const { editor, form } = await openEditor(TAGS[0], { asset_selection: "only", assets: ["id-eth"] }, hass);
    expect(form.data["assets"]).toEqual(["dev-wallet-eth"]);
    expect(helper(form)).toBe("A wallet from a hidden asset group stays hidden, even when chosen here");
    const seen = changes(editor);
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, assets: ["dev-wallet-eth", "dev-wallet-btc"] } } }));
    expect(seen.at(-1)?.["assets"]).toEqual(["id-eth", "id-btc"]);
  });

  it("does not take another integration's device of the same model for a Bitpanda one", async () => {
    const hass = wallets();
    hass.devices["foreign-wallet"] = { id: "foreign-wallet", model: "Wallet", name: "Other", serial_number: "id-eth-foreign", identifiers: [["other", "x"]] };
    const { form } = await openEditor(TAGS[0], { asset_selection: "only", assets: ["id-eth-foreign"] }, hass);
    expect(form.data["assets"]).toEqual([]);
    expect(helper(form)).toContain("not there right now");
  });

  it("counts a missing asset named twice once", async () => {
    const { editor, form } = await openEditor(TAGS[0], { asset_selection: "only", assets: ["id-gone", "id-btc", "id-gone"] }, wallets());
    expect(helper(form)).toContain("This includes a chosen asset that is not there right now.");
    const seen = changes(editor);
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, timeframe: "week" } } }));
    expect(seen.at(-1)?.["assets"]).toEqual(["id-btc", "id-gone"]);
  });

  it("drops the hint once the chosen assets' devices are there", async () => {
    const { editor, form } = await openEditor(TAGS[0], { asset_selection: "only", assets: ["id-btc"] }, makeHass());
    expect(helper(form)).toContain("not there right now");
    editor.hass = wallets();
    await editor.updateComplete;
    expect(form.data["assets"]).toEqual(["dev-wallet-btc"]);
    expect(helper(form)).toBe("A wallet from a hidden asset group stays hidden, even when chosen here");
  });

  it("gives no hint when every chosen asset is there", async () => {
    const { form } = await openEditor(TAGS[0], { asset_selection: "only", assets: ["id-btc"] }, wallets());
    expect(helper(form)).toBe("A wallet from a hidden asset group stays hidden, even when chosen here");
  });
});

describe("the editors' stale device IDs", () => {
  // A device ID as Home Assistant makes them: 32 hex digits without dashes.
  // Bitpanda's asset IDs are dashed UUIDs.
  const STALE = "0123456789abcdef0123456789abcdef";
  const wallets = () => makeHass({ devices: [walletDevice(BTC), walletDevice(ETH)] });
  const helper = (form: { computeHelper: (field: { name: string }) => string | undefined }) => form.computeHelper({ name: "assets" }) ?? "";

  it("counts no device ID that names no device, and drops it when the card is saved", async () => {
    const { editor, form } = await openEditor(TAGS[0], { asset_selection: "only", assets: [STALE, "id-gone", "id-btc"] }, wallets());
    // Only the missing asset ID counts: one.
    expect(helper(form)).toContain("This includes a chosen asset that is not there right now.");
    const seen: Record<string, unknown>[] = [];
    editor.addEventListener("config-changed", (ev) => seen.push((ev as CustomEvent<{ config: Record<string, unknown> }>).detail.config));
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, timeframe: "week" } } }));
    expect(seen.at(-1)?.["assets"]).toEqual(["id-btc", "id-gone"]);
  });

  it("gives no hint when only stale device IDs are missing", async () => {
    const { form } = await openEditor(TAGS[0], { asset_selection: "only", assets: [STALE, "id-btc"] }, wallets());
    expect(helper(form)).toBe("A wallet from a hidden asset group stays hidden, even when chosen here");
  });

  it("keeps a device ID that names a device, saved as its asset ID", async () => {
    const hass = wallets();
    const device = { ...hass.devices["dev-wallet-btc"]!, id: STALE };
    hass.devices[STALE] = device;
    delete hass.devices["dev-wallet-btc"];
    const { editor, form } = await openEditor(TAGS[0], { asset_selection: "only", assets: [STALE] }, hass);
    expect(form.data["assets"]).toEqual([STALE]);
    const seen: Record<string, unknown>[] = [];
    editor.addEventListener("config-changed", (ev) => seen.push((ev as CustomEvent<{ config: Record<string, unknown> }>).detail.config));
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, timeframe: "week" } } }));
    expect(seen.at(-1)?.["assets"]).toEqual(["id-btc"]);
  });
});

describe("the Price Tracker editor's order as chosen", () => {
  const prices = () =>
    makeHass({
      devices: [
        priceDevice({ symbol: "SOL", name: "Solana", category: "crypto", prices: { EUR: { state: "150" } } }),
        priceDevice({ symbol: "BTC", name: "Bitcoin", category: "crypto", prices: { EUR: { state: "70000" } } }),
        walletDevice(ETH),
      ],
    });
  const ORDERED = { asset_selection: "only", sort: "selection" };
  type Field = { name: string; schema?: Field[]; selector?: Record<string, { multiple?: boolean; reorder?: boolean; mode?: string; options?: { value: string; label: string }[] }> };
  const flat = (fields: Field[]): Field[] => fields.flatMap((field) => (field.schema ? flat(field.schema) : [field]));
  const assetField = (form: { schema: unknown[] }): Field | undefined => flat(form.schema as Field[]).find((field) => field.name === "assets");
  const changes = (editor: HTMLElement): Record<string, unknown>[] => {
    const seen: Record<string, unknown>[] = [];
    editor.addEventListener("config-changed", (ev) => seen.push((ev as CustomEvent<{ config: Record<string, unknown> }>).detail.config));
    return seen;
  };
  const pick = (form: HTMLElement & { data: Record<string, unknown> }, value: Record<string, unknown>): void => {
    form.dispatchEvent(new CustomEvent("value-changed", { detail: { value: { ...form.data, ...value } } }));
  };

  it("uses a reorderable select for “Order as chosen” with “Only the ones chosen”", async () => {
    const { form } = await openEditor(TAGS[1], { ...ORDERED, assets: [] }, prices());
    expect(assetField(form)?.selector?.["select"]).toMatchObject({ multiple: true, reorder: true, mode: "dropdown" });
    expect(assetField(form)?.selector?.["device"]).toBeUndefined();
  });

  it("keeps the device picker otherwise", async () => {
    for (const config of [
      { asset_selection: "only", sort: "name" },
      { asset_selection: "all_except", sort: "selection" },
    ]) {
      const { form } = await openEditor(TAGS[1], { ...config, assets: [] }, prices());
      expect(assetField(form)?.selector?.["device"], JSON.stringify(config)).toBeDefined();
    }
  });

  it("lists the tracked assets by label, a device with all sensors disabled included", async () => {
    const hass = prices();
    hass.devices["dev-price-btc"] = { ...hass.devices["dev-price-btc"]!, name_by_user: "My Bitcoin" };
    for (const [entityId, entry] of Object.entries(hass.entities)) if (entry?.device_id === "dev-price-sol") delete hass.entities[entityId];
    const { form } = await openEditor(TAGS[1], { ...ORDERED, assets: [] }, hass);
    expect(assetField(form)?.selector?.["select"]?.options).toEqual([
      { value: "id-btc", label: "My Bitcoin" },
      { value: "id-sol", label: "Solana (SOL)" },
    ]);
  });

  it("shows the chosen assets in the saved order, and saves the order of the chips", async () => {
    const { editor, form } = await openEditor(TAGS[1], { ...ORDERED, assets: ["id-sol", "id-btc"] }, prices());
    expect(form.data["assets"]).toEqual(["id-sol", "id-btc"]);
    const seen = changes(editor);
    pick(form, { assets: ["id-btc", "id-sol"] });
    expect(seen.at(-1)?.["assets"]).toEqual(["id-btc", "id-sol"]);
  });

  it("keeps a missing asset at its place in the saved order", async () => {
    const { editor, form } = await openEditor(TAGS[1], { ...ORDERED, assets: ["id-btc", "id-gone", "id-sol"] }, prices());
    expect(form.data["assets"]).toEqual(["id-btc", "id-sol"]);
    const seen = changes(editor);
    pick(form, { assets: ["id-sol", "id-btc"] });
    expect(seen.at(-1)?.["assets"]).toEqual(["id-sol", "id-gone", "id-btc"]);
    // The chip before it taken out: it moves up.
    const second = await openEditor(TAGS[1], { ...ORDERED, assets: ["id-btc", "id-gone", "id-sol"] }, prices());
    const after = changes(second.editor);
    pick(second.form, { assets: ["id-sol"] });
    expect(after.at(-1)?.["assets"]).toEqual(["id-gone", "id-sol"]);
  });

  it("maps device IDs of an older configuration to their asset IDs", async () => {
    const { editor, form } = await openEditor(TAGS[1], { ...ORDERED, assets: ["dev-price-sol", "id-btc"] }, prices());
    expect(form.data["assets"]).toEqual(["id-sol", "id-btc"]);
    const seen = changes(editor);
    pick(form, { timeframe: "week" });
    expect(seen.at(-1)?.["assets"]).toEqual(["id-sol", "id-btc"]);
  });

  it("keeps the choice when the order is switched away and back", async () => {
    const { editor, form } = await openEditor(TAGS[1], { ...ORDERED, assets: ["id-sol", "id-gone", "id-btc"] }, prices());
    const seen = changes(editor);
    pick(form, { sort: "name" });
    expect(seen.at(-1)?.["assets"]).toEqual(["id-sol", "id-gone", "id-btc"]);
    await editor.updateComplete;
    expect(assetField(form)?.selector?.["device"]).toBeDefined();
    expect(form.data["assets"]).toEqual(["dev-price-sol", "dev-price-btc"]);
    pick(form, { sort: "selection" });
    await editor.updateComplete;
    expect(assetField(form)?.selector?.["select"]).toBeDefined();
    expect(form.data["assets"]).toEqual(["id-sol", "id-btc"]);
    expect(seen.at(-1)?.["assets"]).toEqual(["id-sol", "id-btc", "id-gone"]);
  });

  it("starts a choice from none", async () => {
    const { editor, form } = await openEditor(TAGS[1], ORDERED, prices());
    const seen = changes(editor);
    pick(form, { assets: ["id-btc"] });
    expect(seen.at(-1)?.["assets"]).toEqual(["id-btc"]);
  });

  it("keeps a missing asset named twice once, at its first place", async () => {
    const { editor, form } = await openEditor(TAGS[1], { ...ORDERED, assets: ["id-gone", "id-btc", "id-gone"] }, prices());
    const seen = changes(editor);
    pick(form, { timeframe: "week" });
    expect(seen.at(-1)?.["assets"]).toEqual(["id-gone", "id-btc"]);
  });

  it("offers and keeps a device without an asset ID by its device ID", async () => {
    const hass = prices();
    hass.devices["dev-price-sol"] = { ...hass.devices["dev-price-sol"]!, serial_number: null };
    const { editor, form } = await openEditor(TAGS[1], { ...ORDERED, assets: ["dev-price-sol"] }, hass);
    expect(assetField(form)?.selector?.["select"]?.options).toContainEqual({ value: "dev-price-sol", label: "Solana (SOL)" });
    expect(form.data["assets"]).toEqual(["dev-price-sol"]);
    const seen = changes(editor);
    pick(form, { assets: ["id-btc", "dev-price-sol"] });
    expect(seen.at(-1)?.["assets"]).toEqual(["id-btc", "dev-price-sol"]);
  });

  it("leaves the Portfolio editor's device picker as it is", async () => {
    const { form } = await openEditor(TAGS[0], { asset_selection: "only", assets: [] }, makeHass({ devices: [walletDevice(BTC)] }));
    expect(assetField(form)?.selector?.["device"]).toBeDefined();
  });
});
