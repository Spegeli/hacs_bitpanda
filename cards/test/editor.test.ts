import { describe, expect, it, vi } from "vitest";

import { ensureHaForm } from "../src/editor";
import "../src/index";
import { makeHass, openEditor } from "./fixtures";

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
      expect(form.data, tag).toEqual({ type: `custom:${tag}`, timeframe: "week" });
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
