// What every card shares: its configuration, the timeframe and the eye
// (both start as configured and are never saved), the viewer's language,
// and a render only when one of the card's own sensors changed -- Home
// Assistant hands a card a new hass on every state change in the house.
import { LitElement, type CSSResultGroup, type PropertyValues } from "lit";

import { oneOf, text, type Validator } from "./forms";
import { languageOf, loadCategoryNames, rememberLocale } from "./i18n";
import { cardStyles } from "./styles";
import type { BaseConfig, Hass, Timeframe } from "./types";

export const COMMON_OPTIONS: Record<string, Validator> = { title: text };

export abstract class BitpandaCard<C extends BaseConfig> extends LitElement {
  static override properties = {
    hass: { attribute: false },
    config: { state: true },
    timeframe: { state: true },
    amountsHidden: { state: true },
    seriesRevision: { state: true },
  };

  static override styles: CSSResultGroup = cardStyles;

  hass?: Hass;
  protected config?: C;
  protected timeframe: Timeframe = "day";
  protected amountsHidden = false;
  /** Counts the statistics answers drawn: a reactive change, so an answer
   * is drawn even when a foreign entity's change arrives in the same update. */
  protected seriesRevision = 0;
  private watched: string[] = [];
  private categoryLanguage?: string;

  setConfig(config: unknown): void {
    const valid = this.validate(config);
    const options = valid as BaseConfig & { timeframe?: Timeframe; hide_amounts?: boolean };
    this.config = valid;
    this.timeframe = options.timeframe ?? "day";
    this.amountsHidden = options.hide_amounts ?? false;
  }

  /** The configuration, checked; throws with a readable reason. */
  protected abstract validate(config: unknown): C;

  /** The entities whose changes this card shows. */
  protected abstract watchedEntities(): string[];

  protected toggleAmounts(): void {
    this.amountsHidden = !this.amountsHidden;
  }

  protected seriesArrived(): void {
    this.seriesRevision += 1;
  }

  protected selectTimeframe(timeframe: Timeframe): void {
    this.timeframe = timeframe;
  }

  protected override shouldUpdate(changed: PropertyValues): boolean {
    if (changed.size !== 1 || !changed.has("hass")) return true;
    const previous = changed.get("hass") as Hass | undefined;
    const hass = this.hass;
    if (!previous || !hass) return true;
    if (
      previous.entities !== hass.entities ||
      previous.devices !== hass.devices ||
      previous.locale !== hass.locale ||
      previous.localize !== hass.localize
    ) {
      return true;
    }
    return this.watched.some((entityId) => previous.states[entityId] !== hass.states[entityId]);
  }

  private resizer?: ResizeObserver;

  override connectedCallback(): void {
    super.connectedCallback();
    if (typeof ResizeObserver !== "undefined") {
      this.resizer = new ResizeObserver(() => this.fitLayout());
      this.resizer.observe(this);
    }
  }

  override disconnectedCallback(): void {
    this.resizer?.disconnect();
    this.resizer = undefined;
    super.disconnectedCallback();
  }

  protected override updated(changed: PropertyValues): void {
    super.updated(changed);
    if (this.remeasures(changed)) this.fitLayout();
  }

  /** Measures what the browser laid out and settles a layout that depends
   * on room: after each update that can change it, and when the card's
   * width changes. */
  protected fitLayout(): void {}

  /** Whether an update can change what fitLayout measures: any, unless a
   * card knows better. */
  protected remeasures(_changed: PropertyValues): boolean {
    return true;
  }

  protected override willUpdate(_changed: PropertyValues): void {
    const hass = this.hass;
    if (!hass) return;
    rememberLocale(hass);
    const language = languageOf(hass);
    if (language !== this.categoryLanguage) {
      this.categoryLanguage = language;
      void loadCategoryNames(hass);
    }
    this.watched = this.watchedEntities();
  }

  getCardSize(): number {
    return 3;
  }

  getGridOptions(): { columns: number; min_columns: number } {
    return { columns: 12, min_columns: 6 };
  }
}
