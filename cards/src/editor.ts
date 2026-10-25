// The cards' visual editors: an element of each card's own that draws Home
// Assistant's form (ha-form) with the fields of forms.ts. Home Assistant hands
// it hass and the configuration (setConfig) and takes every change from its
// config-changed event, as for any custom card's editor (getConfigElement).
import { LitElement, html, nothing, type PropertyValues } from "lit";

import { bitpandaDevices, deviceLabel, findPriceAssets, priceCurrencies } from "./discovery";
import {
  assetFields,
  computeHelper,
  computeLabel,
  divider,
  expandable,
  groupFields,
  groupNames,
  limitField,
  select,
  sortField,
  timeframeField,
  titleField,
  booleanField,
  chooses,
  type DeviceModel,
  type FormField,
} from "./forms";
import { languageOf, rememberLocale, t, tCount, type TextKey } from "./i18n";
import {
  CURRENCIES,
  DEFAULT_WALLET_LIMIT,
  LAYOUTS,
  PRICE_SORTS,
  WALLET_SORTS,
  type BaseConfig,
  type Category,
  type Hass,
  type HassDevice,
  type PortfolioConfig,
  type PriceTrackerConfig,
} from "./types";

export const PORTFOLIO_EDITOR = "bitpanda-portfolio-card-editor";
export const PRICE_TRACKER_EDITOR = "bitpanda-price-tracker-card-editor";

/** Each selection and the list it chooses from. */
const LISTS = [
  ["asset_selection", "assets"],
  ["group_selection", "groups"],
] as const;

/** The choice that applies where a configuration makes none: shown in the
 * editor's empty select fields, and written only when the user picks
 * another. */
type Defaults = Record<string, string>;

const PORTFOLIO_DEFAULTS: Defaults = { timeframe: "day", sort: "value", group_selection: "all", asset_selection: "all" };
const PRICE_TRACKER_DEFAULTS: Defaults = {
  layout: "list",
  timeframe: "day",
  currency: "EUR",
  sort: "name",
  group_selection: "all",
  asset_selection: "all",
};

/** How Home Assistant's device IDs look: 32 hex digits, no dashes. Bitpanda's
 * asset IDs are dashed UUIDs. */
const DEVICE_ID = /^[0-9a-f]{32}$/;

/** What the configuration keeps of a device: its asset ID, else its device ID. */
const assetValue = (device: HassDevice): string => device.serial_number || device.id;

/** A field's help text, a full stop after it where it has none, and the
 * hint behind it. */
function withHint(help: string | undefined, hint: string): string {
  if (!help) return hint;
  return /[.!?…]$/.test(help) ? `${help} ${hint}` : `${help}. ${hint}`;
}

/** What an editor draws: the fields, and their labels and help texts. */
export interface EditorForm {
  schema: FormField[];
  computeLabel: (field: { name: string }) => string | undefined;
  computeHelper: (field: { name: string }) => string | undefined;
}

type Registry = Pick<CustomElementRegistry, "get" | "whenDefined">;
interface CardHelpers {
  createCardElement(config: Record<string, unknown>): Promise<HTMLElement>;
}
type HelperWindow = { loadCardHelpers?: () => Promise<CardHelpers> };

/** Home Assistant loads its form on demand: when no other editor has used
 * it yet, it is loaded through a built-in card's editor, as custom cards do.
 * Never throws; without the form after `timeout` ms the editor stays empty,
 * and Home Assistant's code editor still works. */
export async function ensureHaForm(
  registry: Registry = customElements,
  win: HelperWindow = window as HelperWindow,
  timeout = 10_000,
): Promise<void> {
  if (registry.get("ha-form")) return;
  try {
    const helpers = await win.loadCardHelpers?.();
    const card = await helpers?.createCardElement({ type: "entities", entities: [] });
    await (card?.constructor as { getConfigElement?: () => Promise<unknown> } | undefined)?.getConfigElement?.();
  } catch {
    // Left to the wait below.
  }
  let timer: ReturnType<typeof setTimeout> | undefined;
  await Promise.race([
    registry.whenDefined("ha-form"),
    new Promise<void>((resolve) => {
      timer = setTimeout(resolve, timeout);
    }),
  ]);
  clearTimeout(timer);
}

/** An editor's element, its form ready to draw. */
export async function createEditor(tag: typeof PORTFOLIO_EDITOR | typeof PRICE_TRACKER_EDITOR): Promise<HTMLElement> {
  await ensureHaForm();
  if (!customElements.get(PORTFOLIO_EDITOR)) customElements.define(PORTFOLIO_EDITOR, PortfolioCardEditor);
  if (!customElements.get(PRICE_TRACKER_EDITOR)) customElements.define(PRICE_TRACKER_EDITOR, PriceTrackerCardEditor);
  return document.createElement(tag);
}

export abstract class BitpandaEditor<C extends BaseConfig> extends LitElement {
  static override properties = {
    hass: { attribute: false },
    config: { state: true },
    names: { state: true },
  };

  hass?: Hass;
  protected config?: C;
  /** The integration's group names in the user's language, once asked. */
  protected names: Partial<Record<Category, string>> = {};
  private namesAsked = false;
  /** The lists a selection of "all" took out, while the editor is open. */
  private heldBack: Record<string, unknown> = {};

  setConfig(config: C): void {
    this.config = config;
  }

  /** The fields for the configuration as it is now. */
  protected abstract form(): EditorForm;

  /** The choices that apply where the configuration makes none. */
  protected abstract readonly defaults: Defaults;

  /** The model of the devices the asset field lists. */
  protected abstract readonly model: DeviceModel;

  /** Whether the asset field is a select whose chips set the card's order,
   * holding asset IDs, instead of the device picker. */
  protected reorders(): boolean {
    return false;
  }

  /** The configuration's assets as the device picker shows them: the
   * devices they name -- by asset ID, or by device ID as configurations
   * from before hold them --, each once; and the entries that name none of
   * this card's devices right now, kept as they are, each once. A device ID that names
   * no device is no such entry: Home Assistant never gives a device ID
   * again, so it can never apply again -- not counted, and not kept.
   * `values`: the devices as a reorderable choice holds them. */
  private chosenAssets(): { devices: string[]; values: string[]; missing: string[] } {
    const assets = (this.config as { assets?: unknown } | undefined)?.assets;
    const devices = bitpandaDevices(this.hass, this.model);
    const shown: string[] = [];
    const values: string[] = [];
    const missing: string[] = [];
    for (const id of Array.isArray(assets) ? (assets as string[]) : []) {
      const device = devices.find((candidate) => candidate.id === id || (candidate.serial_number && candidate.serial_number === id));
      if (device) {
        if (!shown.includes(device.id)) {
          shown.push(device.id);
          values.push(assetValue(device));
        }
      } else if (!DEVICE_ID.test(id) && !missing.includes(id)) {
        missing.push(id);
      }
    }
    return { devices: shown, values, missing };
  }

  /** What the configuration keeps of the devices picked: their asset IDs
   * (a device without one keeps its device ID), in the order picked, then
   * the entries that name no device right now; each once. */
  private savedAssets(picked: string[]): string[] {
    const devices = bitpandaDevices(this.hass, this.model);
    const saved: string[] = [];
    for (const id of [...picked.map((deviceId) => devices.find((device) => device.id === deviceId)?.serial_number || deviceId), ...this.chosenAssets().missing]) {
      if (!saved.includes(id)) saved.push(id);
    }
    return saved;
  }

  /** What the configuration keeps of the chips of a reorderable choice:
   * their asset IDs in the chips' order, and each entry that names no
   * device right now where it stood -- after as many of the entries before
   * it as are still chosen; each once. */
  private orderedAssets(chips: string[]): string[] {
    const assets = (this.config as { assets?: unknown } | undefined)?.assets;
    const devices = bitpandaDevices(this.hass, this.model);
    const { missing } = this.chosenAssets();
    const saved = [...new Set(chips)];
    const kept = new Set<string>();
    let placed = 0;
    for (const id of Array.isArray(assets) ? (assets as string[]) : []) {
      if (missing.includes(id)) {
        if (saved.includes(id)) continue;
        saved.splice(Math.min(kept.size + placed, saved.length), 0, id);
        placed += 1;
        continue;
      }
      const device = devices.find((candidate) => candidate.id === id || (candidate.serial_number && candidate.serial_number === id));
      if (device && saved.includes(assetValue(device))) kept.add(assetValue(device));
    }
    return saved;
  }

  protected override willUpdate(changed: PropertyValues): void {
    super.willUpdate(changed);
    if (!this.hass) return;
    rememberLocale(this.hass);
    if (!this.namesAsked) {
      this.namesAsked = true;
      void groupNames(this.hass).then((names) => {
        this.names = names;
      });
    }
  }

  protected override render() {
    if (!this.config) return nothing;
    const form = this.form();
    const { devices, values, missing } = this.chosenAssets();
    const data: Record<string, unknown> = { ...this.defaults, ...this.config };
    // The reorderable select's chips are asset IDs, the device picker's devices.
    if ("assets" in data) data["assets"] = this.reorders() ? values : devices;
    // Below the asset field: how many chosen assets are missing right now.
    const computeHelper =
      missing.length === 0
        ? form.computeHelper
        : (field: { name: string }) =>
            field.name === "assets" ? withHint(form.computeHelper(field), tCount(undefined, "assets_missing", missing.length)) : form.computeHelper(field);
    return html`<ha-form
      .hass=${this.hass}
      .data=${data}
      .schema=${form.schema}
      .computeLabel=${form.computeLabel}
      .computeHelper=${computeHelper}
      @value-changed=${this.changed}
    ></ha-form>`;
  }

  private changed(ev: CustomEvent<{ value: C }>): void {
    ev.stopPropagation();
    const before = this.config ?? {};
    const raw = ev.detail.value as C & { assets?: unknown };
    // The field the change comes from is the one drawn for the configuration
    // before it.
    const picked = raw.assets as string[];
    const value = Array.isArray(raw.assets) ? { ...raw, assets: this.reorders() ? this.orderedAssets(picked) : this.savedAssets(picked) } : raw;
    // A shown default is written only once the user picks something else,
    // or where the configuration had it before. Fields hidden for now keep
    // what the configuration holds -- but the assets and groups to choose:
    // "all" chooses none, so they go, and come back while the editor is
    // open when the user switches back.
    const config: Record<string, unknown> = Object.fromEntries(
      Object.entries(value).filter(([key, value]) => key in before || this.defaults[key] === undefined || value !== this.defaults[key]),
    );
    for (const [selection, list] of LISTS) {
      if (!chooses(config[selection])) {
        if (list in config) this.heldBack[list] = config[list];
        delete config[list];
      } else if (!(list in config) && list in this.heldBack) {
        config[list] = this.heldBack[list];
      }
    }
    this.config = config as C;
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
  }
}

// The editor's shared fields in the Portfolio's own words: its list holds
// wallets, its limit holds without groups only, and its filters leave the
// total, Cash, Cash Plus and the allocation whole.
const WALLET_LABELS: Record<string, TextKey> = {
  limit: "opt_limit_wallets",
  asset_selection: "opt_asset_selection_wallets",
  assets: "opt_assets_wallets",
};
const WALLET_HELPERS: Record<string, TextKey> = {
  show_header: "opt_show_header_help_portfolio",
  show_timeframes: "opt_show_timeframes_help_portfolio",
  limit: "opt_limit_help_wallets",
  group_selection: "opt_group_selection_help",
  assets: "opt_assets_help_wallets",
};

export class PortfolioCardEditor extends BitpandaEditor<PortfolioConfig> {
  protected readonly defaults = PORTFOLIO_DEFAULTS;
  protected readonly model = "Wallet";

  protected form(): EditorForm {
    const config: Partial<PortfolioConfig> = this.config ?? {};
    return {
      schema: [
        titleField("Bitpanda Portfolio"),
        // As in the Price Tracker card's editor: what the card shows, which
        // of it, and how it looks.
        expandable("group_content", [
          booleanField("show_total", true),
          booleanField("show_since_purchase", true),
          booleanField("show_graph", true),
          booleanField("show_cash", true),
          booleanField("show_staking", true),
          booleanField("show_allocation", true),
          booleanField("show_wallets", true),
        ]),
        expandable("group_wallets", [
          booleanField("show_search", false),
          booleanField("group_wallets", true),
          sortField(WALLET_SORTS),
          limitField(DEFAULT_WALLET_LIMIT),
          divider(),
          ...groupFields(this.names, config.group_selection ?? "all"),
          divider(),
          ...assetFields("Wallet", config.asset_selection ?? "all"),
        ]),
        expandable("group_appearance", [
          booleanField("show_header", true),
          timeframeField(),
          booleanField("show_timeframes", true),
          booleanField("hide_amounts", false),
        ]),
      ],
      computeLabel: (field) => {
        const key = WALLET_LABELS[field.name];
        return key ? t(undefined, key) : computeLabel(field);
      },
      computeHelper: (field) => {
        const key = WALLET_HELPERS[field.name];
        return key ? t(undefined, key) : computeHelper(field);
      },
    };
  }
}

/** The currencies the editor offers: those the Price Tracker has prices in;
 * every supported currency when there is no state to read them from. */
function editorCurrencies(hass: Hass | undefined): readonly string[] {
  const offered = hass ? priceCurrencies(findPriceAssets(hass)) : [];
  return offered.length > 0 ? offered : CURRENCIES;
}

export class PriceTrackerCardEditor extends BitpandaEditor<PriceTrackerConfig> {
  protected readonly defaults = PRICE_TRACKER_DEFAULTS;
  protected readonly model = "Price Tracker";

  /** "Order as chosen" with "Only the ones chosen": the chips set the order. */
  protected override reorders(): boolean {
    return this.config?.asset_selection === "only" && this.config.sort === "selection";
  }

  /** The tracked assets to choose from, by name: a device with all its
   * sensors disabled included, as in the device picker. */
  private assetOptions(): { value: string; label: string }[] {
    return bitpandaDevices(this.hass, this.model)
      .map((device) => ({ value: assetValue(device), label: deviceLabel(device) }))
      .sort((a, b) => a.label.localeCompare(b.label, languageOf(this.hass)));
  }

  protected form(): EditorForm {
    const config: Partial<PriceTrackerConfig> = this.config ?? {};
    return {
      schema: [
        titleField("Bitpanda Price Tracker"),
        // As in the Portfolio card's editor: what the card shows, which of
        // it, and how it looks.
        expandable("group_content", [booleanField("show_lines", true), booleanField("show_amounts", true)]),
        // Like the Portfolio's Wallets: the list's order and length, then
        // the asset groups and the assets.
        expandable("group_assets", [sortField(PRICE_SORTS), limitField(0), divider(), ...groupFields(this.names, config.group_selection ?? "all"), divider(), ...assetFields("Price Tracker", config.asset_selection ?? "all", this.reorders() ? this.assetOptions() : undefined)]),
        expandable("group_appearance", [
          { name: "layout", selector: select(LAYOUTS, (value) => t(undefined, `layout_${value}` as TextKey)) },
          booleanField("show_header", true),
          timeframeField(),
          booleanField("show_timeframes", true),
          { name: "currency", selector: { select: { mode: "dropdown", options: editorCurrencies(this.hass).map((value) => ({ value, label: value })) } } },
          booleanField("show_currencies", true),
        ]),
      ],
      computeLabel,
      // "Order as chosen" needs assets chosen with "Only".
      computeHelper: (field) => (field.name === "sort" ? t(undefined, "opt_sort_help_tracker") : computeHelper(field)),
    };
  }
}
