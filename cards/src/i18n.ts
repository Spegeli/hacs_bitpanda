// The cards' texts in the viewer's language: the language of their Home
// Assistant profile, its base language for a regional one (de-AT -> de),
// English for any other. Category names are the integration's own group
// titles, which Home Assistant loads for any user.
import { de } from "./translations/de";
import { en, type Texts } from "./translations/en";
import { es } from "./translations/es";
import { fr } from "./translations/fr";
import { it } from "./translations/it";
import { nl } from "./translations/nl";
import { pl } from "./translations/pl";
import type { Category, Hass } from "./types";

export type TextKey = keyof typeof en;
export type CountKey = "shares" | "assets_missing";

export const LANGUAGES = { en, de, fr, nl, it, es, pl } satisfies Record<string, Texts>;
type Language = keyof typeof LANGUAGES;

const isLanguage = (code: string): code is Language => code in LANGUAGES;

// The editors' forms and a card's configuration check get no hass: they
// speak Home Assistant's language from the page's root element, else the
// language a card saw last (rememberLocale).
let remembered: Language = "en";

const baseLanguage = (language: string): Language => {
  const base = language.toLowerCase().replace(/[-_].*$/, "");
  return isLanguage(base) ? base : "en";
};

export function languageOf(hass?: Hass): Language {
  const root = hass ?? (document.querySelector("home-assistant") as { hass?: Hass } | null)?.hass;
  return root ? baseLanguage(root.locale.language) : remembered;
}

/** Whether the cards have texts in the viewer's language (or its base). */
export function speaksLanguageOf(hass: Hass): boolean {
  return isLanguage(hass.locale.language.toLowerCase().replace(/[-_].*$/, ""));
}

export function rememberLocale(hass: Hass): void {
  remembered = languageOf(hass);
}

const table = (hass?: Hass): Texts => LANGUAGES[languageOf(hass)];

export function t(hass: Hass | undefined, key: TextKey, vars: Record<string, string | number> = {}): string {
  return table(hass)[key].replace(/\{(\w+)\}/g, (whole, name: string) =>
    name in vars ? String(vars[name]) : whole,
  );
}

/** The text for `count`, in the plural form the language asks for, with
 * `count` in place of its {count}; test/i18n.test.ts holds every language
 * to every form it has. `digits` are the decimals `count` is shown with,
 * which decide the form too: 1 share, 1.0004 shares. */
export function tCount(hass: Hass | undefined, key: CountKey, count: number, digits: Intl.NumberFormatOptions = {}): string {
  const rule = new Intl.PluralRules(languageOf(hass), digits as Intl.PluralRulesOptions).select(count);
  return ((table(hass) as Record<string, string>)[`${key}_${rule}`] as string).replace("{count}", String(count));
}

export async function loadCategoryNames(hass: Hass): Promise<void> {
  await hass.loadBackendTranslation("selector", "bitpanda");
}

export function categoryName(hass: Hass, category: Category): string {
  return hass.localize(`component.bitpanda.selector.asset_group.options.${category}`) || category;
}
