import { describe, expect, it, vi } from "vitest";

import {
  assetFields,
  bool,
  booleanField,
  computeHelper,
  computeLabel,
  currencyCode,
  deviceList,
  divider,
  expandable,
  groupFields,
  groupList,
  groupNames,
  limitField,
  nonNegativeInt,
  oneOf,
  sortField,
  text,
  timeframeField,
  titleField,
  validateConfig,
} from "../src/forms";
import { rememberLocale } from "../src/i18n";
import { makeHass } from "./fixtures";

describe("validateConfig", () => {
  const options = { title: text, timeframe: oneOf(["day", "week"]), hide_amounts: bool, limit: nonNegativeInt, assets: deviceList, currency: currencyCode };

  it("accepts a valid configuration and leaves unknown keys alone", () => {
    const config = { type: "custom:x", title: "Mine", timeframe: "week", hide_amounts: true, limit: 0, assets: ["a"], currency: "USD", something: 1 };
    expect(validateConfig(config, options)).toEqual(config);
  });

  it("treats an option left empty in YAML (null) as not set", () => {
    expect(validateConfig({ type: "custom:x", title: null, timeframe: null, limit: null }, options)).toEqual({ type: "custom:x" });
  });

  it("rejects an unknown timeframe with a readable reason", () => {
    rememberLocale(makeHass());
    expect(() => validateConfig({ type: "custom:x", timeframe: "decade" }, options)).toThrowError(
      'Invalid value for “timeframe”: "decade". Allowed: day, week.',
    );
  });

  it("rejects wrong types for every kind of option", () => {
    for (const [key, value] of [
      ["title", 5],
      ["hide_amounts", "yes"],
      ["limit", -1],
      ["limit", 1.5],
      ["assets", "a"],
      ["assets", [1]],
      ["currency", "usd"],
    ] as const) {
      expect(() => validateConfig({ type: "custom:x", [key]: value }, options), key).toThrowError(/Invalid value/);
    }
  });

  it("rejects something that is no configuration at all", () => {
    expect(() => validateConfig(null, options)).toThrowError(/Invalid value/);
    expect(() => validateConfig("custom:x", options)).toThrowError(/Invalid value/);
  });

  it("takes asset groups by their keys only", () => {
    rememberLocale(makeHass());
    expect(validateConfig({ type: "custom:x", groups: ["crypto", "other"] }, { groups: groupList })).toEqual({ type: "custom:x", groups: ["crypto", "other"] });
    expect(() => validateConfig({ type: "custom:x", groups: ["future"] }, { groups: groupList })).toThrowError(
      'Invalid value for “groups”: ["future"]. Allowed: a list of crypto, stock, etf, etc, index, metal, other.',
    );
    expect(() => validateConfig({ type: "custom:x", groups: "crypto" }, { groups: groupList })).toThrowError(/Invalid value for “groups”/);
  });

  it("names the allowed values in the user's language", () => {
    rememberLocale(makeHass());
    expect(() => validateConfig({ type: "custom:x", assets: "Bitcoin" }, { assets: deviceList })).toThrowError(
      'Invalid value for “assets”: "Bitcoin". Allowed: a list of device IDs.',
    );
    expect(() => validateConfig({ type: "custom:x", title: 5 }, { title: text })).toThrowError('Invalid value for “title”: 5. Allowed: text.');
    rememberLocale(makeHass({ language: "de" }));
    expect(() => validateConfig({ type: "custom:x", groups: ["future"] }, { groups: groupList })).toThrowError(
      'Ungültiger Wert für „groups“: ["future"]. Erlaubt: eine Liste aus crypto, stock, etf, etc, index, metal, other.',
    );
    expect(() => validateConfig({ type: "custom:x", assets: "Bitcoin" }, { assets: deviceList })).toThrowError(/Erlaubt: eine Liste von Geräte-IDs\./);
    rememberLocale(makeHass());
  });

  it("speaks the language a card remembered", () => {
    rememberLocale(makeHass({ language: "de" }));
    expect(() => validateConfig({ type: "custom:x", limit: -1 }, options)).toThrowError(/Ungültiger Wert für „limit“/);
    rememberLocale(makeHass());
  });

  it("speaks Home Assistant's language before any card saw one", () => {
    // A card checks its configuration before it gets hass: the page's root
    // element carries Home Assistant's state, and with it the language.
    rememberLocale(makeHass());
    const root = document.createElement("home-assistant") as HTMLElement & { hass?: unknown };
    root.hass = makeHass({ language: "de" });
    document.body.append(root);
    try {
      expect(() => validateConfig({ type: "custom:x", limit: -1 }, options)).toThrowError(/Ungültiger Wert für „limit“/);
    } finally {
      root.remove();
    }
  });
});

describe("groupNames", () => {
  const KEY = "component.bitpanda.selector.asset_group.options.";

  it("asks Home Assistant for the integration's group names in the user's language", async () => {
    const hass = makeHass({
      language: "de",
      callWS: async () => ({ resources: { [`${KEY}crypto`]: "Kryptowährungen", [`${KEY}etf`]: "ETFs", [`${KEY}future`]: "Zukunft", other: "x" } }),
    });
    expect(await groupNames(hass)).toEqual({ crypto: "Kryptowährungen", etf: "ETFs" });
    expect(hass.messages).toEqual([{ type: "frontend/get_translations", language: "de", category: "selector", integration: ["bitpanda"] }]);
  });

  it("gives no names without Home Assistant's state, after a failed call, or after 3 seconds without an answer", async () => {
    expect(await groupNames(undefined)).toEqual({});
    expect(
      await groupNames(
        makeHass({
          callWS: async () => {
            throw new Error("connection lost");
          },
        }),
      ),
    ).toEqual({});
    vi.useFakeTimers();
    try {
      const waiting = groupNames(makeHass({ callWS: () => new Promise(() => undefined) }));
      await vi.advanceTimersByTimeAsync(3000);
      expect(await waiting).toEqual({});
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("editor fields", () => {
  it("the device field filters to the integration and model", () => {
    const [selection, assets] = assetFields("Wallet");
    expect(selection).toMatchObject({ name: "asset_selection" });
    expect(assets).toEqual({
      name: "assets",
      selector: { device: { multiple: true, filter: [{ integration: "bitpanda", model: "Wallet" }] } },
    });
    expect(assetFields("Price Tracker")[1]).toMatchObject({
      selector: { device: { filter: [{ integration: "bitpanda", model: "Price Tracker" }] } },
    });
  });

  it("the asset group fields offer every group, named as the integration names them", () => {
    rememberLocale(makeHass());
    const [selection, groups] = groupFields({ crypto: "Cryptocurrencies", etf: "ETFs" });
    expect(selection).toEqual({
      name: "group_selection",
      selector: {
        select: {
          mode: "dropdown",
          options: [
            { value: "all", label: "All" },
            { value: "all_except", label: "All except the ones chosen" },
            { value: "only", label: "Only the ones chosen" },
          ],
        },
      },
    });
    expect(groups).toMatchObject({ name: "groups", selector: { select: { multiple: true, mode: "dropdown" } } });
    const options = (groups.selector as { select: { options: { value: string; label: string }[] } }).select.options;
    expect(options.map((option) => option.value)).toEqual(["crypto", "stock", "etf", "etc", "index", "metal", "other"]);
    expect(options[0]).toEqual({ value: "crypto", label: "Cryptocurrencies" });
    expect(options[2]).toEqual({ value: "etf", label: "ETFs" });
    // A group without a name shows its key.
    expect(options[1]).toEqual({ value: "stock", label: "stock" });
  });

  it("the form sets no defaults", () => {
    const schema = [timeframeField(), ...groupFields({}), ...assetFields("Wallet"), expandable("group_content", [timeframeField()])];
    expect(JSON.stringify(schema)).not.toContain('"default"');
  });

  it("select options carry translated labels", () => {
    rememberLocale(makeHass());
    expect(timeframeField()).toEqual({
      name: "timeframe",
      selector: {
        select: {
          mode: "dropdown",
          options: [
            { value: "day", label: "1 day" },
            { value: "week", label: "1 week" },
            { value: "month", label: "1 month" },
            { value: "six_month", label: "6 months" },
            { value: "year", label: "1 year" },
          ],
        },
      },
    });
  });

  it("groups are flat expandables with a translated title", () => {
    expect(expandable("group_appearance", [timeframeField()])).toMatchObject({
      type: "expandable",
      name: "",
      flatten: true,
      title: "Appearance",
    });
  });

  it("labels and helpers come from the card texts", () => {
    rememberLocale(makeHass());
    expect(computeLabel({ name: "hide_amounts" })).toBe("Hide amounts initially");
    expect(computeHelper({ name: "hide_amounts" })).toBe("Percentages stay visible; the eye at the top of the card shows the amounts only temporarily");
    // A section's toggle explains itself; only the allocation says what it is.
    for (const name of ["show_graph", "show_cash", "show_wallets"]) expect(computeHelper({ name }), name).toBeUndefined();
    expect(computeHelper({ name: "show_allocation" })).toBe("The coloured bar showing the share of each asset group and of cash");
    expect(computeHelper({ name: "title" })).toBe("Leave empty for the name shown in grey");
    expect(computeLabel({ name: "timeframe" })).toBe("Default timeframe");
    expect(computeHelper({ name: "timeframe" })).toBe("The 1D to 1Y buttons on the card change it only temporarily");
    expect(computeHelper({ name: "sort" })).toBeUndefined();
    expect(computeLabel({ name: "unknown_option" })).toBeUndefined();
  });

  it("a divider is Home Assistant's form line; a release without it leaves only space", () => {
    expect(divider()).toEqual({ type: "divider", name: "" });
  });

  it("the simple fields use Home Assistant's selectors", () => {
    expect(titleField("Bitpanda Wallets")).toEqual({ name: "title", default: "Bitpanda Wallets", selector: { text: {} } });
    expect(booleanField("show_cash", true)).toEqual({ name: "show_cash", default: true, selector: { boolean: {} } });
    expect(limitField(5)).toEqual({ name: "limit", default: 5, selector: { number: { min: 0, max: 100, mode: "box" } } });
    expect(sortField(["value", "name"])).toEqual({
      name: "sort",
      selector: { select: { mode: "dropdown", options: [{ value: "value", label: "Value" }, { value: "name", label: "Name" }] } },
    });
  });

});
