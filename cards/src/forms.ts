// Configuration: what setConfig accepts, and the fields of the visual editor
// (Home Assistant's own form, drawn by each card's editor, editor.ts). Toggles,
// numbers and the title show their default where the configuration has none,
// and nothing is saved for them; the editor shows a select field's default
// itself (editor.ts). A card added from the picker still starts with its
// choices written out (each card's getStubConfig).
import { t, type TextKey } from "./i18n";
import { ASSET_SELECTIONS, CATEGORIES, TIMEFRAMES, type BaseConfig, type Category, type Hass } from "./types";

export interface Validator {
  /** The allowed values, in the language a card remembered. */
  allowed: () => string;
  check: (value: unknown) => boolean;
}

export const oneOf = (values: readonly string[]): Validator => ({
  allowed: () => values.join(", "),
  check: (value) => typeof value === "string" && values.includes(value),
});

export const bool: Validator = { allowed: () => "true, false", check: (value) => typeof value === "boolean" };

export const text: Validator = { allowed: () => t(undefined, "allowed_text"), check: (value) => typeof value === "string" };

export const nonNegativeInt: Validator = {
  allowed: () => "0, 1, 2, …",
  check: (value) => typeof value === "number" && Number.isInteger(value) && value >= 0,
};

export const assetList: Validator = {
  allowed: () => t(undefined, "allowed_assets"),
  check: (value) => Array.isArray(value) && value.every((item) => typeof item === "string"),
};

export const groupList: Validator = {
  allowed: () => t(undefined, "allowed_groups", { values: CATEGORIES.join(", ") }),
  check: (value) => Array.isArray(value) && value.every((item) => (CATEGORIES as readonly unknown[]).includes(item)),
};

export const currencyCode: Validator = {
  allowed: () => "EUR, USD, …",
  check: (value) => typeof value === "string" && /^[A-Z]{3}$/.test(value),
};

/** The configuration, checked option by option; an invalid value throws
 * with a reason Home Assistant shows on its error card. Unknown keys are
 * ignored; an option left empty in YAML (null) counts as not set. */
export function validateConfig<C extends BaseConfig>(config: unknown, options: Record<string, Validator>): C {
  if (config === null || typeof config !== "object" || Array.isArray(config)) {
    throw new Error(t(undefined, "invalid_option", { option: "type", value: JSON.stringify(config), allowed: "custom:…" }));
  }
  const given = Object.fromEntries(Object.entries(config).filter(([, value]) => value !== null));
  for (const [key, validator] of Object.entries(options)) {
    const value = given[key];
    if (value !== undefined && !validator.check(value)) {
      throw new Error(t(undefined, "invalid_option", { option: key, value: JSON.stringify(value), allowed: validator.allowed() }));
    }
  }
  return given as C;
}

// --- Editor fields ------------------------------------------------------------

export interface FormField {
  name: string;
  [key: string]: unknown;
}

export type DeviceModel = "Wallet" | "Price Tracker";

/** A choice: a dropdown, one line in the editor, where Home Assistant would
 * show fewer than six options as radio buttons, one line each. */
export const select = (values: readonly string[], label: (value: string) => string) => ({
  select: { mode: "dropdown", options: values.map((value) => ({ value, label: label(value) })) },
});

export const titleField = (name: string): FormField => ({ name: "title", default: name, selector: { text: {} } });

export const timeframeField = (): FormField => ({
  name: "timeframe",
  selector: select(TIMEFRAMES, (value) => t(undefined, `tfo_${value}` as TextKey)),
});

export const booleanField = (name: string, fallback: boolean): FormField => ({ name, default: fallback, selector: { boolean: {} } });

export const limitField = (fallback: number): FormField => ({
  name: "limit",
  default: fallback,
  selector: { number: { min: 0, max: 100, mode: "box" } },
});

export const sortField = (values: readonly string[]): FormField => ({
  name: "sort",
  selector: select(values, (value) => t(undefined, `sort_${value}` as TextKey)),
});

/** Home Assistant's state where nothing hands it over -- the card picker's
 * texts: read from the page's root element. */
export function editorHass(): Hass | undefined {
  return (document.querySelector("home-assistant") as { hass?: Hass } | null)?.hass;
}

const NAMES_WAIT = 3000;

/** The integration's group names in the user's language, asked of Home
 * Assistant directly: loading them through hass would hand the names to a
 * new hass object, not to the one the editor read. None after a failed
 * call or NAMES_WAIT without an answer: the editor opens all the same. */
export async function groupNames(hass: Hass | undefined): Promise<Partial<Record<Category, string>>> {
  if (!hass) return {};
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const answer = await Promise.race([
      hass.callWS<{ resources?: Record<string, unknown> }>({
        type: "frontend/get_translations",
        language: hass.language,
        category: "selector",
        integration: ["bitpanda"],
      }),
      new Promise<undefined>((resolve) => {
        timer = setTimeout(() => resolve(undefined), NAMES_WAIT);
      }),
    ]);
    const resources = answer?.resources ?? {};
    const names: Partial<Record<Category, string>> = {};
    for (const category of CATEGORIES) {
      const name = resources[`component.bitpanda.selector.asset_group.options.${category}`];
      if (typeof name === "string" && name) names[category] = name;
    }
    return names;
  } catch {
    return {};
  } finally {
    clearTimeout(timer);
  }
}

/** Whether a selection names groups or assets to choose: "all" chooses none. */
export const chooses = (selection: unknown): boolean => selection === "only" || selection === "all_except";

/** The asset groups a card shows, by their names; a group without one
 * shows its key. The groups to choose only while the selection asks for
 * them. */
export const groupFields = (names: Partial<Record<Category, string>>, selection: unknown): FormField[] => [
  { name: "group_selection", selector: select(ASSET_SELECTIONS, (value) => t(undefined, `sel_${value}` as TextKey)) },
  ...(chooses(selection)
    ? [
        {
          name: "groups",
          selector: {
            select: { multiple: true, mode: "dropdown", options: CATEGORIES.map((value) => ({ value, label: names[value] ?? value })) },
          },
        },
      ]
    : []),
];

/** The assets a card shows; the assets to choose only while the selection
 * asks for them. */
export const assetFields = (model: DeviceModel, selection: unknown): FormField[] => [
  { name: "asset_selection", selector: select(ASSET_SELECTIONS, (value) => t(undefined, `sel_${value}` as TextKey)) },
  ...(chooses(selection) ? [{ name: "assets", selector: { device: { multiple: true, filter: [{ integration: "bitpanda", model }] } } }] : []),
];

/** A line between fields. Home Assistant releases without one (2025.5
 * among them) leave the usual space between fields in its place. */
export const divider = (): FormField => ({ type: "divider", name: "" });

export const expandable = (title: TextKey, schema: FormField[]): FormField => ({
  type: "expandable",
  name: "",
  flatten: true,
  title: t(undefined, title),
  schema,
});

const LABELS: Record<string, TextKey> = {
  title: "opt_title",
  timeframe: "opt_timeframe",
  show_total: "opt_show_total",
  show_graph: "opt_show_line",
  show_cash: "opt_show_cash",
  show_allocation: "opt_show_allocation",
  show_wallets: "opt_show_wallets",
  group_wallets: "opt_group_wallets",
  show_search: "opt_show_search",
  sort: "opt_sort",
  group_selection: "opt_group_selection",
  groups: "opt_groups",
  asset_selection: "opt_asset_selection",
  assets: "opt_assets",
  hide_amounts: "opt_hide_amounts",
  limit: "opt_limit",
  layout: "opt_layout",
  currency: "opt_currency",
};

const HELPERS: Record<string, TextKey> = {
  title: "opt_title_help",
  timeframe: "opt_timeframe_help",
  show_total: "opt_show_total_help",
  show_allocation: "opt_show_allocation_help",
  hide_amounts: "opt_hide_amounts_help",
  show_search: "opt_show_search_help",
  assets: "opt_assets_help",
  limit: "opt_limit_help",
  currency: "opt_currency_help",
};

export function computeLabel(field: { name: string }): string | undefined {
  const key = LABELS[field.name];
  return key ? t(undefined, key) : undefined;
}

export function computeHelper(field: { name: string }): string | undefined {
  const key = HELPERS[field.name];
  return key ? t(undefined, key) : undefined;
}
