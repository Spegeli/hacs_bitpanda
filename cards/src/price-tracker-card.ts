// Bitpanda Price Tracker: the tracked assets as a list or as tiles, with a
// line and the change of the selected timeframe, in the selected currency.
import { css, html, nothing, type PropertyValues, type TemplateResult } from "lit";

import { BitpandaCard, COMMON_OPTIONS } from "./base-card";
import { findPriceAssets, priceCurrencies, selectAssets, selectGroups } from "./discovery";
import {
  assetFields,
  computeHelper,
  computeLabel,
  currencyCode,
  deviceList,
  divider,
  editorHass,
  expandable,
  groupFields,
  groupList,
  groupNames,
  limitField,
  nonNegativeInt,
  oneOf,
  select,
  sortField,
  timeframeField,
  titleField,
  validateConfig,
} from "./forms";
import { arrow, formatDay, formatLongDate, formatPercent, formatSignedLike, formatState, numericState, trendClass } from "./format";
import { languageOf, t, type TextKey } from "./i18n";
import { allFit, currencySwitch, emptyState, header, moreInfo, numberAttribute, onActivate, timeframeSwitch } from "./parts";
import { defineCard } from "./register";
import { renderSparkline } from "./sparkline";
import { SeriesLoader, changeFromSeries, lineStepMs, windowFor, type Point, type StatWindow } from "./statistics";
import { cardStyles } from "./styles";
import { ASSET_SELECTIONS, CURRENCIES, LAYOUTS, PRICE_SORTS, TIMEFRAMES, type Hass, type PriceRefs, type PriceTrackerConfig } from "./types";

interface Row {
  asset: PriceRefs;
  entityId: string | undefined;
  /** The change in percent and as an amount in the row's currency. */
  change: number | undefined;
  amount: number | undefined;
  points: Point[] | undefined;
  /** When the statistics start later than the window: the change and the
   * line count from here, and the row says so. */
  since: number | undefined;
}

const priceStyles = css`
  .price-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 96px auto minmax(78px, auto);
    grid-template-areas: "lead line price change";
    align-items: center;
    gap: 8px;
    padding: 9px 0;
    border-top: 1px solid var(--bp-divider);
    cursor: pointer;
  }
  .price-row .lead {
    grid-area: lead;
    min-width: 0;
  }
  /* A name over two lines takes two of about the same length: its first
     line keeps off the price. Longer names are still cut after two. */
  .price-row .n {
    text-wrap: balance;
  }
  .price-row .mini {
    grid-area: line;
  }
  /* Price and change only as wide as they are: the card measures them
     alike in either layout (fitLayout). */
  .price-row .p {
    grid-area: price;
    justify-self: end;
  }
  .price-row .c {
    grid-area: change;
    justify-self: end;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }
  /* Not room for the name in every row: the price above its change. */
  .rows.stacked .price-row {
    grid-template-columns: minmax(0, 1fr) 96px auto;
    grid-template-areas:
      "lead line price"
      "lead line change";
    row-gap: 2px;
  }
  .rows.stacked .price-row .p {
    align-self: end;
  }
  .rows.stacked .price-row .c {
    align-self: start;
  }
  .price-row:first-of-type {
    border-top: 0;
  }
  .price-row .s {
    font-size: 11px;
  }
  .p {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .c {
    text-align: right;
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
  }
  .c .a {
    font-size: 12px;
    font-weight: 400;
    margin-top: 2px;
  }
  .since {
    font-size: 11px;
    color: var(--bp-muted);
    margin-top: 2px;
  }
  .rows {
    margin-top: 10px;
  }
  .tiles {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(124px, 1fr));
    gap: 8px;
    margin-top: 12px;
  }
  .tile {
    border: 1px solid var(--bp-divider);
    border-radius: 10px;
    padding: 10px;
    cursor: pointer;
    min-width: 0;
  }
  .tile .n {
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
  }
  .tile .s {
    font-size: 11px;
  }
  .tile .p {
    text-align: left;
    font-size: 16px;
    margin-top: 6px;
  }
  .tile .c {
    text-align: left;
    font-size: 12px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }
  .tile .c .pct,
  .tile .c .a {
    flex-shrink: 0;
  }
  /* Every tile has room: the amount beside the chip (amountsFit). */
  .tiles.inline .tile .c {
    flex-direction: row;
    align-items: center;
    column-gap: 6px;
  }
  .tiles.inline .tile .c .a {
    margin-top: 0;
  }
  .tile svg.mini {
    width: 100%;
    height: 30px;
    margin-top: 6px;
  }
  .tile .since {
    margin-top: 4px;
  }
  .foot {
    font-size: 11px;
    color: var(--bp-muted);
    padding: 10px 16px 14px;
    border-top: 1px solid var(--bp-divider);
  }
  /* A narrow list, such as the card picker's preview: the names first. */
  @container (max-width: 380px) {
    .price-row {
      grid-template-columns: minmax(0, 1fr) auto auto;
      grid-template-areas: "lead price change";
    }
    .rows.stacked .price-row {
      grid-template-columns: minmax(0, 1fr) auto;
      grid-template-areas:
        "lead price"
        "lead change";
    }
    .price-row .mini {
      display: none;
    }
  }
  /* Not even room for the name beside the price above its change: name and
     category across the row, price, chip and amount right-aligned below. */
  .rows.below .price-row {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      "lead"
      "price"
      "change";
    row-gap: 2px;
  }
  .rows.below .price-row .lead {
    margin-bottom: 4px;
  }
  .rows.below .price-row .mini {
    display: none;
  }
`;

/** Pixels between a tile's chip and the amount beside it. */
const CHIP_GAP = 6;

/** The least room a list row leaves its name before its price goes above
 * its change, and before both go below the name. */
const NAME_ROOM = 120;
const NAME_ROOM_STACKED = 90;

/** As the styles have them: pixels between a list row's columns, the least
 * width of its change column, the line's width, and the card width up to
 * which a list hides its lines. */
const ROW_GAP = 8;
const CHANGE_LEAST = 78;
const LINE_WIDTH = 96;
const NARROW_LIST = 380;

/** Where a list row's price and change stand, the same in every row. */
export type PriceRowLayout = "beside" | "stacked" | "below";

/** Beside each other while every row leaves its name NAME_ROOM; the price
 * above the change while every row leaves it NAME_ROOM_STACKED; else both
 * below the name. `room` is a row's width without its line; widths in
 * pixels. */
export function priceRowLayout(rows: readonly { room: number; price: number; change: number }[]): PriceRowLayout {
  const beside = (row: { room: number; price: number; change: number }) =>
    row.room - row.price - ROW_GAP - Math.max(CHANGE_LEAST, row.change) - ROW_GAP >= NAME_ROOM;
  const stacked = (row: { room: number; price: number; change: number }) => row.room - Math.max(row.price, row.change) - ROW_GAP >= NAME_ROOM_STACKED;
  if (rows.every(beside)) return "beside";
  return rows.every(stacked) ? "stacked" : "below";
}

/** Whether every tile that shows an amount has room for it beside the
 * percentage (widths in pixels); tiles without one do not count. */
export function amountsFit(cells: readonly { room: number; pct: number; amount?: number }[]): boolean {
  return allFit(
    cells.map((cell) => ({ room: cell.room, first: cell.pct, ...(cell.amount === undefined ? {} : { second: cell.amount }) })),
    CHIP_GAP,
  );
}

/** The currencies the editor offers: those the Price Tracker has prices in;
 * every supported currency when there is no state to read them from. */
function editorCurrencies(hass: Hass | undefined): readonly string[] {
  const offered = hass ? priceCurrencies(findPriceAssets(hass)) : [];
  return offered.length > 0 ? offered : CURRENCIES;
}

export class PriceTrackerCard extends BitpandaCard<PriceTrackerConfig> {
  static override properties = {
    ...BitpandaCard.properties,
    currency: { state: true },
    showAll: { state: true },
    amountsInline: { state: true },
    rowsLayout: { state: true },
  };

  static override styles = [cardStyles, priceStyles];

  private currency?: string;
  private showAll = false;
  private amountsInline = false;
  private rowsLayout: PriceRowLayout = "beside";
  private window: StatWindow = windowFor("day", Date.now());
  private readonly lines = new SeriesLoader(() => this.seriesArrived());

  static async getConfigForm() {
    const hass = editorHass();
    const names = await groupNames(hass);
    return {
      schema: [
        titleField("Bitpanda Price Tracker"),
        expandable("group_content", [
          { name: "layout", selector: select(LAYOUTS, (value) => t(undefined, `layout_${value}` as TextKey)) },
          timeframeField(),
          { name: "currency", selector: { select: { mode: "dropdown", options: editorCurrencies(hass).map((value) => ({ value, label: value })) } } },
        ]),
        // Like the Portfolio's Wallets: the list's order and length, then
        // the asset groups and the assets.
        expandable("group_assets", [sortField(PRICE_SORTS), limitField(0), divider(), ...groupFields(names), divider(), ...assetFields("Price Tracker")]),
      ],
      computeLabel,
      // "Order as chosen" needs assets chosen with "Only".
      computeHelper: (field: { name: string }) => (field.name === "sort" ? t(undefined, "opt_sort_help_tracker") : computeHelper(field)),
    };
  }

  static getStubConfig(): Record<string, unknown> {
    return { layout: "list", timeframe: "day", currency: "EUR", sort: "name", group_selection: "all", asset_selection: "all" };
  }

  override setConfig(config: unknown): void {
    super.setConfig(config);
    this.currency = undefined;
  }

  protected validate(config: unknown): PriceTrackerConfig {
    return validateConfig<PriceTrackerConfig>(config, {
      ...COMMON_OPTIONS,
      layout: oneOf(LAYOUTS),
      timeframe: oneOf(TIMEFRAMES),
      currency: currencyCode,
      sort: oneOf(PRICE_SORTS),
      group_selection: oneOf(ASSET_SELECTIONS),
      groups: groupList,
      asset_selection: oneOf(ASSET_SELECTIONS),
      assets: deviceList,
      limit: nonNegativeInt,
    });
  }

  protected watchedEntities(): string[] {
    return this.hass ? findPriceAssets(this.hass).flatMap((asset) => Object.values(asset.prices)) : [];
  }

  /** The switched currency, else the configured one, if a price exists in
   * it; else EUR, or the first currency offered when no EUR price is
   * enabled. The configuration is never changed. */
  private shownCurrency(assets: PriceRefs[]): string {
    const offered = priceCurrencies(assets);
    const wanted = this.currency ?? this.config?.currency ?? "EUR";
    return offered.includes(wanted) ? wanted : (offered.includes("EUR") ? "EUR" : (offered[0] ?? "EUR"));
  }

  private visible(
    hass: Hass,
    config: PriceTrackerConfig,
  ): { rows: Row[]; ranked: Row[]; total: number; folds: boolean; currency: string; currencies: string[] } {
    const assets = findPriceAssets(hass);
    const currency = this.shownCurrency(assets);
    const grouped = selectGroups(assets, config.group_selection ?? "all", config.groups ?? []);
    const selected = selectAssets(grouped, config.asset_selection ?? "all", config.assets ?? []);
    const rows: Row[] = selected.map((asset) => {
      const entityId = asset.prices[currency];
      const state = entityId ? hass.states[entityId] : undefined;
      const points = entityId ? this.lines.series(entityId) : undefined;
      const current = numericState(hass, entityId);
      // 1D: the sensor's own 24 h change while it has one; otherwise, and
      // beyond a day, the statistics from the window's start or, when they
      // start later, from their first point.
      const dayChange = this.timeframe === "day" ? numberAttribute(state, "change_24h_pct") : undefined;
      if (dayChange !== undefined) {
        const before = numberAttribute(state, "price_24h_ago");
        const amount = current !== undefined && before !== undefined ? current - before : undefined;
        return { asset, entityId, change: dayChange, amount, points, since: undefined };
      }
      const measured = changeFromSeries(points ?? [], current, this.window);
      return { asset, entityId, change: measured?.change, amount: measured?.amount, points, since: measured?.since };
    });
    const sort = config.sort ?? "name";
    const byName = (a: Row, b: Row): number => a.asset.name.localeCompare(b.asset.name, languageOf(hass));
    if (sort === "name" || (sort === "selection" && config.asset_selection !== "only")) {
      rows.sort(byName);
    } else if (sort === "change_desc" || sort === "change_asc") {
      const sign = sort === "change_desc" ? -1 : 1;
      rows.sort((a, b) => {
        if (a.change === undefined || b.change === undefined) return a.change === undefined ? (b.change === undefined ? byName(a, b) : 1) : -1;
        return sign * (a.change - b.change) || byName(a, b);
      });
    }
    const limit = config.limit ?? 0;
    const folds = limit > 0 && rows.length > limit;
    const shown = folds && !this.showAll ? rows.slice(0, limit) : rows;
    return { rows: shown, ranked: rows, total: rows.length, folds, currency, currencies: priceCurrencies(assets) };
  }

  protected override willUpdate(changed: PropertyValues): void {
    super.willUpdate(changed);
    this.window = windowFor(this.timeframe, Date.now());
    if (!this.hass || !this.config) return;
    const { rows, ranked } = this.visible(this.hass, this.config);
    // Beyond a day the change comes from the statistics: sorting by it needs
    // them for every row, not only for the rows shown.
    const sort = this.config.sort ?? "name";
    const needed = this.timeframe !== "day" && (sort === "change_desc" || sort === "change_asc") ? ranked : rows;
    const entityIds = needed.map((row) => row.entityId).filter((entityId): entityId is string => entityId !== undefined);
    this.lines.request(this.hass, entityIds, this.window);
  }

  /** Tiles show the amount beside the percentage only when every tile has
   * room for it, below it otherwise. */
  protected override fitLayout(): void {
    const width = (element: Element | null): number | undefined => element?.getBoundingClientRect().width;
    const cells = [...(this.shadowRoot?.querySelectorAll<HTMLElement>(".tile .c") ?? [])].map((cell) => {
      const amount = width(cell.querySelector(".a"));
      return { room: cell.clientWidth, pct: width(cell.querySelector(".pct")) ?? 0, ...(amount === undefined ? {} : { amount }) };
    });
    const inline = amountsFit(cells);
    if (inline !== this.amountsInline) this.amountsInline = inline;
    // A list row's price and change (priceRowLayout). Price and change are
    // only as wide as they are, and the line's room comes from the card's
    // width, not from the line, which the last layout hides: the same
    // widths in every layout.
    const lineRoom = this.clientWidth > NARROW_LIST ? LINE_WIDTH + ROW_GAP : 0;
    const rows = [...this.renderRoot.querySelectorAll<HTMLElement>(".price-row")].map((row) => {
      const part = (selector: string): number => (row.querySelector(selector) as Element).getBoundingClientRect().width;
      return { room: row.clientWidth - lineRoom, price: part(".p"), change: Math.max(part(".c .pct"), width(row.querySelector(".c .a")) ?? 0) };
    });
    const layout = priceRowLayout(rows);
    if (layout !== this.rowsLayout) this.rowsLayout = layout;
  }

  override getCardSize(): number {
    return 6;
  }

  private open(entityId: string | undefined): () => void {
    return () => {
      if (entityId) moreInfo(this, entityId);
    };
  }

  /** The row's line: on the window's axis, or from the statistics' start
   * when they start later, the span its change covers. */
  private line(row: Row, direction: string): TemplateResult | typeof nothing {
    const window = row.since === undefined ? this.window : { ...this.window, start: row.since };
    return row.points && row.points.length > 0
      ? renderSparkline(row.points, window, { width: 96, height: 28, fill: false, className: `mini ${direction}`, stepMs: lineStepMs(window) })
      : html`<span class="mini"></span>`;
  }

  private change(hass: Hass, row: Row): { cell: TemplateResult; className: string; lineClass: string } {
    const { text, direction } = formatPercent(hass, row.change);
    const mark = arrow(direction);
    const className = trendClass(direction);
    const amount = direction === "none" ? undefined : formatSignedLike(hass, row.entityId, row.amount);
    // The percentage in a chip, as the Portfolio card shows its own; the
    // amount beside or below it, never in it.
    const cell = html`<div class="pct pchip ${direction === "none" ? "none" : ""}">${direction === "none" ? "—" : `${mark ? `${mark} ` : ""}${text}`}</div>${amount
        ? html`<div class="a">${amount}</div>`
        : nothing}`;
    return { cell, className, lineClass: className || "flat" };
  }

  private since(hass: Hass, row: Row): TemplateResult | typeof nothing {
    return row.since === undefined ? nothing : html`<div class="since">${t(hass, "change_since", { date: formatDay(hass, row.since) })}</div>`;
  }

  private renderList(hass: Hass, rows: Row[]): TemplateResult {
    return html`<div class="rows ${this.rowsLayout === "beside" ? "" : this.rowsLayout}">
      ${rows.map((row) => {
        const change = this.change(hass, row);
        // As in the tiles: the name, and below it the symbol, or a
        // security's ISIN.
        return html`<div class="price-row" role="button" tabindex="0" @click=${this.open(row.entityId)} @keydown=${onActivate(this.open(row.entityId))}>
          <div class="lead"><div class="n" title=${row.asset.shortName}>${row.asset.shortName}</div><div class="s">${row.asset.isin ?? row.asset.symbol}</div>${this.since(hass, row)}</div>
          ${this.line(row, change.lineClass)}
          <div class="p">${formatState(hass, row.entityId) ?? "—"}</div>
          <div class="c ${change.className}">${change.cell}</div>
        </div>`;
      })}
    </div>`;
  }

  private renderTiles(hass: Hass, rows: Row[]): TemplateResult {
    return html`<div class="tiles ${this.amountsInline ? "inline" : ""}">
      ${rows.map((row) => {
        const change = this.change(hass, row);
        return html`<div class="tile" role="button" tabindex="0" @click=${this.open(row.entityId)} @keydown=${onActivate(this.open(row.entityId))}>
          <div class="n" title=${row.asset.shortName}>${row.asset.shortName}</div>
          <div class="s">${row.asset.isin ?? row.asset.symbol}</div>
          <div class="p">${formatState(hass, row.entityId) ?? "—"}</div>
          <div class="c ${change.className}">${change.cell}</div>
          ${this.line(row, change.lineClass)}${this.since(hass, row)}
        </div>`;
      })}
    </div>`;
  }

  private footer(hass: Hass, rows: Row[], currency: string): TemplateResult | typeof nothing {
    if (currency === "EUR") return nothing;
    const date = rows
      .map((row) => (row.entityId ? hass.states[row.entityId]?.attributes["rate_date"] : undefined))
      .map((value) => (typeof value === "string" ? formatLongDate(hass, value) : undefined))
      .find((value): value is string => value !== undefined);
    return date ? html`<div class="foot">${t(hass, "ecb_footer", { currency, date })}</div>` : nothing;
  }

  protected override render(): TemplateResult | typeof nothing {
    const hass = this.hass;
    const config = this.config;
    if (!hass || !config) return nothing;
    const head = header(hass, config.title || "Bitpanda Price Tracker");
    if (findPriceAssets(hass).length === 0) return html`<ha-card>${head}${emptyState(t(hass, "empty_price_tracker"))}</ha-card>`;
    const { rows, total, folds, currency, currencies } = this.visible(hass, config);
    return html`<ha-card>
      ${head}
      <div class="content">
        <div class="switches">
          ${timeframeSwitch(hass, this.timeframe, (timeframe) => this.selectTimeframe(timeframe))}
          ${currencySwitch(hass, currencies, currency, (picked) => (this.currency = picked))}
        </div>
        ${rows.length === 0
          ? emptyState(t(hass, "empty_selection_assets"))
          : config.layout === "tiles"
            ? this.renderTiles(hass, rows)
            : this.renderList(hass, rows)}
        ${folds
          ? html`<button class="show-all" @click=${() => (this.showAll = !this.showAll)}>
              ${this.showAll ? t(hass, "show_less") : t(hass, "show_all", { count: total })}
            </button>`
          : nothing}
      </div>
      ${this.footer(hass, rows, currency)}
    </ha-card>`;
  }
}

defineCard("bitpanda-price-tracker-card", PriceTrackerCard, {
  name: "Bitpanda Price Tracker",
  description: () => t(editorHass(), "picker_price_tracker"),
  model: "Price Tracker",
});
