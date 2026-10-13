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
const PLURAL_EXTRAS = /^shares_(zero|two|few|many)$/;

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
        expect((texts as Record<string, string>)[`shares_${rule}`], `${language} ${rule}`).toBeTruthy();
      }
    }
  });

  it("every text keeps the placeholders of its English original", () => {
    for (const [language, texts] of Object.entries(LANGUAGES)) {
      for (const [key, text] of Object.entries(texts as Record<string, string>)) {
        const original = (en as Record<string, string>)[key] ?? (en as Record<string, string>)["shares_other"] ?? "";
        expect(placeholders(text), `${language} ${key}`).toEqual(placeholders(original));
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
