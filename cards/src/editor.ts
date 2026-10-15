// The cards' visual editors: an element of each card's own that draws Home
// Assistant's form (ha-form) with the fields of forms.ts. Home Assistant hands
// it hass and the configuration (setConfig) and takes every change from its
// config-changed event, as for any custom card's editor (getConfigElement).
import { LitElement, html, nothing, type PropertyValues } from "lit";

import { findPriceAssets, priceCurrencies } from "./discovery";
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
  type FormField,
} from "./forms";
import { rememberLocale, t, type TextKey } from "./i18n";
import {
  CURRENCIES,
  DEFAULT_WALLET_LIMIT,
  LAYOUTS,
  PRICE_SORTS,
  WALLET_SORTS,
  type BaseConfig,
  type Category,
  type Hass,
  type PortfolioConfig,
  type PriceTrackerConfig,
} from "./types";

export const PORTFOLIO_EDITOR = "bitpanda-portfolio-card-editor";
export const PRICE_TRACKER_EDITOR = "bitpanda-price-tracker-card-editor";

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

  setConfig(config: C): void {
    this.config = config;
  }

  /** The fields for the configuration as it is now. */
  protected abstract form(): EditorForm;

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
    return html`<ha-form
      .hass=${this.hass}
      .data=${this.config}
      .schema=${form.schema}
      .computeLabel=${form.computeLabel}
      .computeHelper=${form.computeHelper}
      @value-changed=${this.changed}
    ></ha-form>`;
  }

  private changed(ev: CustomEvent<{ value: C }>): void {
    ev.stopPropagation();
    const config = ev.detail.value;
    this.config = config;
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
  limit: "opt_limit_help_wallets",
  group_selection: "opt_group_selection_help",
  assets: "opt_assets_help_wallets",
};

export class PortfolioCardEditor extends BitpandaEditor<PortfolioConfig> {
  protected form(): EditorForm {
    return {
      schema: [
        titleField("Bitpanda Portfolio"),
        expandable("group_content", [
          timeframeField(),
          booleanField("show_total", true),
          booleanField("show_graph", true),
          booleanField("show_cash", true),
          booleanField("show_allocation", true),
          booleanField("show_wallets", true),
        ]),
        expandable("group_wallets", [
          booleanField("show_search", false),
          booleanField("group_wallets", true),
          sortField(WALLET_SORTS),
          limitField(DEFAULT_WALLET_LIMIT),
          divider(),
          ...groupFields(this.names),
          divider(),
          ...assetFields("Wallet"),
        ]),
        expandable("group_appearance", [booleanField("hide_amounts", false)]),
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
  protected form(): EditorForm {
    return {
      schema: [
        titleField("Bitpanda Price Tracker"),
        expandable("group_content", [
          { name: "layout", selector: select(LAYOUTS, (value) => t(undefined, `layout_${value}` as TextKey)) },
          timeframeField(),
          { name: "currency", selector: { select: { mode: "dropdown", options: editorCurrencies(this.hass).map((value) => ({ value, label: value })) } } },
        ]),
        // Like the Portfolio's Wallets: the list's order and length, then
        // the asset groups and the assets.
        expandable("group_assets", [sortField(PRICE_SORTS), limitField(0), divider(), ...groupFields(this.names), divider(), ...assetFields("Price Tracker")]),
      ],
      computeLabel,
      // "Order as chosen" needs assets chosen with "Only".
      computeHelper: (field) => (field.name === "sort" ? t(undefined, "opt_sort_help_tracker") : computeHelper(field)),
    };
  }
}
