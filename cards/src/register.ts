// Defines a card's element and lists it in the dashboard's card picker, with
// a preview and, from Home Assistant 2026.6 on, as a suggestion for the
// integration's entities. A module loaded twice defines nothing twice.
import type { Hass } from "./types";

// Home Assistant's frontend (2025.5 on) replaces window.customElements with a
// registry of its own once its app has loaded, and it loads that app and this
// module side by side: an element defined in the browser's registry before
// the swap stays unknown to the frontend ("Custom element doesn't exist").
const LOADED_WITH = window.customElements;
const READY_TIMEOUT = 10_000;

/** The registry to define in: the one Home Assistant put in place, or the
 * current one once its app element is defined there; after ten seconds the
 * current one in any case. */
export function whenRegistryReady(
  current: () => CustomElementRegistry = () => window.customElements,
  loadedWith: CustomElementRegistry = LOADED_WITH,
  timeout = READY_TIMEOUT,
): Promise<CustomElementRegistry> {
  const started = Date.now();
  return new Promise((resolve) => {
    const check = (): void => {
      const registry = current();
      if (registry !== loadedWith || registry.get("home-assistant") || Date.now() - started >= timeout) resolve(registry);
      else setTimeout(check, 50);
    };
    check();
  });
}

export const DOCS_URL = "https://github.com/Spegeli/hacs_bitpanda#-dashboard-cards";

export type SuggestingModel = "Portfolio" | "Wallet" | "Price Tracker";

export interface CardInfo {
  name: string;
  /** Read each time the card picker opens: in the language of that moment. */
  description: () => string;
  /** The devices whose entities suggest the card. */
  model?: SuggestingModel | readonly SuggestingModel[];
}

interface PickerEntry {
  type: string;
  name: string;
  description: string;
  preview: boolean;
  documentationURL: string;
  getEntitySuggestion?: (hass: Hass, entityId: string) => { config: { type: string } } | null;
}

/** A suggestion of the card `tag` for an entity of a Bitpanda device of
 * `model`, or null for any other entity. */
export function suggestCard(
  hass: Hass,
  entityId: string,
  model: SuggestingModel | readonly SuggestingModel[],
  tag: string,
  start: Record<string, unknown> = {},
): { config: { type: string } } | null {
  const entry = hass.entities[entityId];
  if (!entry || entry.platform !== "bitpanda" || !entry.device_id) return null;
  const models: readonly string[] = typeof model === "string" ? [model] : model;
  return models.includes(hass.devices[entry.device_id]?.model ?? "") ? { config: { type: `custom:${tag}`, ...start } } : null;
}

export function defineCard(tag: string, element: CustomElementConstructor, info: CardInfo): void {
  void whenRegistryReady().then((registry) => {
    if (!registry.get(tag)) registry.define(tag, element);
  });
  const picker = window as Window & { customCards?: PickerEntry[] };
  picker.customCards ??= [];
  if (picker.customCards.some((entry) => entry.type === tag)) return;
  const { model } = info;
  picker.customCards.push({
    type: tag,
    name: info.name,
    get description() {
      return info.description();
    },
    preview: true,
    documentationURL: DOCS_URL,
    ...(model
      ? {
          // The suggested card starts like one added from the picker.
          getEntitySuggestion: (hass: Hass, entityId: string) =>
            suggestCard(hass, entityId, model, tag, (element as { getStubConfig?: () => Record<string, unknown> }).getStubConfig?.()),
        }
      : {}),
  });
}
