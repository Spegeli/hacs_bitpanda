import { describe, expect, it } from "vitest";

import {
  LANGUAGES,
  categoryName,
  languageOf,
  loadCategoryNames,
  rememberLocale,
  t,
  tCount,
} from "../src/i18n";
import { en } from "../src/translations/en";
import { makeHass } from "./fixtures";

const placeholders = (text: string): string[] => [...text.matchAll(/\{(\w+)\}/g)].map((match) => match[1] ?? "").sort();
const COUNTED = ["shares", "assets_missing", "staking_wallets"] as const;
const PLURAL_EXTRAS = /^(shares|assets_missing|staking_wallets)_(zero|two|few|many)$/;

describe("the card texts", () => {
  it("come in the integration's seven languages", () => {
    expect(Object.keys(LANGUAGES).sort()).toEqual(["de", "en", "es", "fr", "it", "nl", "pl"]);
  });

  it("every language has every key", () => {
    const keys = Object.keys(en).filter((key) => !PLURAL_EXTRAS.test(key)).sort();
    for (const [language, texts] of Object.entries(LANGUAGES)) {
      const own = Object.keys(texts).filter((key) => !PLURAL_EXTRAS.test(key)).sort();
      expect(own, language).toEqual(keys);
    }
  });

  it("every language has the plural forms Intl.PluralRules asks for", () => {
    for (const [language, texts] of Object.entries(LANGUAGES)) {
      for (const rule of new Intl.PluralRules(language).resolvedOptions().pluralCategories) {
        for (const key of COUNTED) expect((texts as Record<string, string>)[`${key}_${rule}`], `${language} ${key} ${rule}`).toBeTruthy();
      }
    }
  });

  it("every text keeps the placeholders of its English original", () => {
    for (const [language, texts] of Object.entries(LANGUAGES)) {
      for (const [key, text] of Object.entries(texts as Record<string, string>)) {
        const counted = COUNTED.find((name) => key.startsWith(`${name}_`));
        const original = (en as Record<string, string>)[key] ?? (counted ? (en as Record<string, string>)[`${counted}_other`] : undefined) ?? "";
        expect(placeholders(text), `${language} ${key}`).toEqual(placeholders(original));
      }
    }
  });

  it("French keeps ; : ! ? and » with the word before them, « with the word after it", () => {
    // A no-break space, as French typography sets them: a narrow card never
    // starts a line with the mark.
    const noBreak = /[  ]/;
    for (const [key, text] of Object.entries(LANGUAGES.fr as Record<string, string>)) {
      for (let index = 0; index < text.length; index++) {
        const char = text.charAt(index);
        if (";:!?»".includes(char)) expect(noBreak.test(text.charAt(index - 1)), `${key}: ${text}`).toBe(true);
        if (char === "«") expect(noBreak.test(text.charAt(index + 1)), `${key}: ${text}`).toBe(true);
      }
    }
  });
});

describe("t", () => {
  it("fills in the placeholders", () => {
    expect(t(makeHass(), "show_all", { count: 6 })).toBe("Show all (6)");
  });

  it("keeps a placeholder it has no value for", () => {
    expect(t(makeHass(), "show_all")).toBe("Show all ({count})");
  });

  it("speaks the viewer's language", () => {
    expect(t(makeHass({ language: "de" }), "show_all", { count: 6 })).toBe("Alle anzeigen (6)");
  });

  it("falls back to the base language, then English", () => {
    expect(languageOf(makeHass({ language: "de-AT" }))).toBe("de");
    expect(t(makeHass({ language: "de-AT" }), "cash")).toBe("Bargeld");
    expect(languageOf(makeHass({ language: "ja" }))).toBe("en");
    expect(t(makeHass({ language: "ja" }), "cash")).toBe("Cash");
  });

  it("without hass uses the language a card remembered last", () => {
    rememberLocale(makeHass({ language: "fr" }));
    expect(t(undefined, "opt_title")).toBe("Titre");
    rememberLocale(makeHass({ language: "en" }));
    expect(t(undefined, "opt_title")).toBe("Title");
  });
});

describe("tCount", () => {
  it("picks the plural form", () => {
    expect(tCount(makeHass(), "shares", 1)).toBe("share");
    expect(tCount(makeHass(), "shares", 21.4)).toBe("shares");
    expect(tCount(makeHass({ language: "de" }), "shares", 21.4)).toBe("Stück");
    expect(tCount(makeHass({ language: "pl" }), "shares", 1)).toBe("sztuka");
    expect(tCount(makeHass({ language: "pl" }), "shares", 2)).toBe("sztuki");
    expect(tCount(makeHass({ language: "pl" }), "shares", 5)).toBe("sztuk");
    expect(tCount(makeHass({ language: "pl" }), "shares", 21.4)).toBe("sztuki");
  });
});

describe("category names", () => {
  it("use the integration's translation", async () => {
    const hass = makeHass({
      translations: { "component.bitpanda.selector.asset_group.options.etf": "ETFs" },
    });
    let loaded: unknown[] = [];
    hass.loadBackendTranslation = async (...args: unknown[]) => {
      loaded = args;
    };
    await loadCategoryNames(hass);
    expect(loaded).toEqual(["selector", "bitpanda"]);
    expect(categoryName(hass, "etf")).toBe("ETFs");
  });

  it("fall back to the key", () => {
    expect(categoryName(makeHass(), "metal")).toBe("metal");
  });
});

describe("the staking line's count", () => {
  const as = (language: string) => makeHass({ language });
  it("takes every plural form a language has", () => {
    expect(tCount(as("en"), "staking_wallets", 1)).toBe("in 1 wallet");
    expect(tCount(as("en"), "staking_wallets", 3)).toBe("in 3 wallets");
    expect(tCount(as("pl"), "staking_wallets", 1)).toBe("w 1 portfelu");
    expect(tCount(as("pl"), "staking_wallets", 3)).toBe("w 3 portfelach");
    expect(tCount(as("pl"), "staking_wallets", 5)).toBe("w 5 portfelach");
    expect(tCount(as("fr"), "staking_wallets", 1000000)).toBe("dans 1000000 wallets");
  });
});
