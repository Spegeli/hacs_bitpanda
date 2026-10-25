// Bitpanda Portfolio: total value, return, the return since purchase and
// the value line, Cash and Cash Plus, the staking line, the allocation, and
// every wallet by category with its detail.
import { html, nothing, type PropertyValues, type TemplateResult } from "lit";

import { BitpandaCard, COMMON_OPTIONS } from "./base-card";
import { findPortfolio, selectAssets, selectGroups } from "./discovery";
import { PORTFOLIO_EDITOR, createEditor } from "./editor";
import { assetList, bool, editorHass, groupList, nonNegativeInt, oneOf, validateConfig } from "./forms";
import {
  arrow,
  formatAssetPrice,
  formatDayTime,
  formatLike,
  formatMoney,
  formatPrice,
  formatPercent,
  formatShare,
  formatState,
  formatUnits,
  numberAttribute,
  numericState,
  trendClass,
} from "./format";
import { categoryName, t, tCount, type TextKey } from "./i18n";
import {
  CHEVRONS,
  allFit,
  amount,
  emptyState,
  eyeButton,
  header,
  icon,
  matchesWallet,
  opener,
  onActivate,
  searchField,
  sortWallets,
  tapTarget,
  walletRow,
} from "./parts";
import { defineCard } from "./register";
import { PORTFOLIO_LINE, SeriesLoader, fetchPortfolioLine, windowFor, type StatWindow } from "./statistics";
import { portfolioCurrency, summary } from "./summary";
import {
  ASSET_SELECTIONS,
  CATEGORIES,
  DEFAULT_WALLET_LIMIT,
  TIMEFRAMES,
  WALLET_SORTS,
  type Category,
  type Hass,
  type PortfolioConfig,
  type PortfolioRefs,
  type WalletRefs,
} from "./types";

const TAG = "bitpanda-portfolio-card";

// Each part keeps its colour whatever its share: Home Assistant's named
// colours, with a fallback for themes that lack them.
const COLORS: Record<Category | "cash" | "cash_plus", string> = {
  crypto: "var(--blue-color, #4269d0)",
  stock: "var(--indigo-color, #3f51b5)",
  etf: "var(--amber-color, #efb118)",
  etc: "var(--cyan-color, #00bcd4)",
  index: "var(--purple-color, #a463f2)",
  metal: "var(--green-color, #3ca951)",
  other: "var(--pink-color, #ff8ab7)",
  cash_plus: "var(--deep-orange-color, #ff725c)",
  cash: "var(--teal-color, #6cc5b0)",
};

const categoryOf = (wallet: WalletRefs): Category => wallet.category ?? "other";

/** A part's share of the allocation, as Bitpanda's app shows it: from 1 %
 * up with two decimals, below it "<1 %". */
export function allocationShare(hass: Hass, value: number): string {
  return value < 1 ? `<${formatShare(hass, 1, 0)}` : formatShare(hass, value, 2, true);
}

/** The wallets a card shows: those of its asset groups, then of its assets. */
const shownWallets = (refs: PortfolioRefs, config: PortfolioConfig): WalletRefs[] =>
  selectAssets(selectGroups(refs.wallets, config.group_selection ?? "all", config.groups ?? []), config.asset_selection ?? "all", config.assets ?? []);

/** A group's return since purchase, in percent: the value of all its
 * wallets against what went into them, as Bitpanda reckons it. Undefined
 * when a wallet lacks its value or invested amount, or nothing went in. */
export function groupReturn(hass: Hass, wallets: readonly { total?: string | undefined }[]): number | undefined {
  let value = 0;
  let invested = 0;
  for (const wallet of wallets) {
    const worth = numericState(hass, wallet.total);
    const put = numberAttribute(wallet.total ? hass.states[wallet.total] : undefined, "invested_amount");
    if (worth === undefined || put === undefined) return undefined;
    value += worth;
    invested += put;
  }
  return invested > 0 ? ((value - invested) / invested) * 100 : undefined;
}

/** Where a group's chip and sum, or a wallet row's chip and value, stand:
 * the same in every group, and in every row. */
export type BlockLayout = "beside" | "row" | "stacked";

/** Beside what is on the left (a group's name, a row's units), chip above
 * value, when every block has room for that; else below the name, side by
 * side, when every block has room for that; else below the name, chip above
 * value. Widths in pixels; `below` is the room under the name where it
 * differs (a wallet row's reaches under the chevron); a block without a chip
 * has nothing to stack. */
export function blockLayout(blocks: readonly { room: number; below?: number; left: number; chip?: number; value: number }[]): BlockLayout {
  const beside = blocks.map((block) => ({ room: block.room, first: block.left, second: Math.max(block.chip ?? 0, block.value) }));
  if (blocks.length === 0 || allFit(beside, BESIDE_GAP)) return "beside";
  const rows = blocks.flatMap((block) =>
    block.chip === undefined ? [] : [{ room: block.below ?? block.room, first: block.chip, second: block.value }],
  );
  return rows.length === 0 || allFit(rows, ROW_GAP) ? "row" : "stacked";
}

/** A sum of figures Bitpanda reported, undefined when one is missing; float
 * noise removed, the precision is Home Assistant's to show. */
export function sumOf(values: (number | undefined)[]): number | undefined {
  if (values.some((value) => value === undefined)) return undefined;
  return Math.round((values as number[]).reduce((total, value) => total + value, 0) * 1e8) / 1e8;
}

/** The middle dot between a value's parts: it stays with the part before
 * it, and a line breaks after it. */
const DOT = " · ";

/** The wallets with something staked, largest staked value first, over the
 * whole portfolio: the Balance (staking) sensors found (a disabled one is
 * not) whose value is above 0. `unknown`: one of them has no value. */
export function stakedWallets(hass: Hass, refs: PortfolioRefs): { counted: { wallet: WalletRefs; value: number }[]; unknown: boolean } {
  const counted: { wallet: WalletRefs; value: number }[] = [];
  let unknown = false;
  for (const wallet of refs.wallets) {
    if (!wallet.staking) continue;
    const value = numericState(hass, wallet.staking);
    if (value === undefined) unknown = true;
    else if (value > 0) counted.push({ wallet, value });
  }
  counted.sort((a, b) => b.value - a.value);
  return { counted, unknown };
}

/** Pixels between a group's name, or a row's units, and the chip and value
 * beside them. */
const BESIDE_GAP = 12;

/** Pixels between chip and value side by side below the name. */
const ROW_GAP = 8;

/** Pixels a wallet row gains below its name under the chevron: its width
 * and the gap before it, as far as the styles let the row out. */
const UNDER_CHEVRON = 30;

/** Pixels between the units and the staked share beside them. */
const STAKE_GAP = 8;

export class PortfolioCard extends BitpandaCard<PortfolioConfig> {
  static override properties = {
    ...BitpandaCard.properties,
    openGroups: { state: true },
    openWallets: { state: true },
    stakingOpen: { state: true },
    showAll: { state: true },
    query: { state: true },
    cursor: { state: true },
    stakeInline: { state: true },
    groupsLayout: { state: true },
    rowsLayout: { state: true },
  };

  private openGroups = new Set<Category>();
  /** The staking line's list of wallets: closed at every start, never saved. */
  private stakingOpen = false;
  private showAll = false;
  /** The wallet search as typed; kept while the page is open, not stored. */
  private query = "";
  /** The line's point under the mouse or finger, while there is one. */
  private cursor: number | undefined = undefined;
  private stakeInline = false;
  private groupsLayout: BlockLayout = "beside";
  private rowsLayout: BlockLayout = "beside";
  private openWallets = new Set<string>();
  private window: StatWindow = windowFor("day", Date.now());
  private readonly lines = new SeriesLoader(() => this.seriesArrived(), fetchPortfolioLine);

  static async getConfigElement(): Promise<HTMLElement> {
    return createEditor(PORTFOLIO_EDITOR);
  }

  static getStubConfig(): Record<string, unknown> {
    return { timeframe: "day", sort: "value", group_selection: "all", asset_selection: "all" };
  }

  protected validate(config: unknown): PortfolioConfig {
    return validateConfig<PortfolioConfig>(config, {
      ...COMMON_OPTIONS,
      timeframe: oneOf(TIMEFRAMES),
      show_total: bool,
      show_since_purchase: bool,
      show_graph: bool,
      show_cash: bool,
      show_staking: bool,
      show_allocation: bool,
      show_wallets: bool,
      group_wallets: bool,
      show_search: bool,
      sort: oneOf(WALLET_SORTS),
      limit: nonNegativeInt,
      group_selection: oneOf(ASSET_SELECTIONS),
      groups: groupList,
      asset_selection: oneOf(ASSET_SELECTIONS),
      assets: assetList,
      hide_amounts: bool,
    });
  }

  protected watchedEntities(): string[] {
    const refs = this.hass ? findPortfolio(this.hass) : undefined;
    if (!refs) return [];
    return [
      refs.totalValue,
      refs.cash,
      refs.cashPlus,
      refs.invested,
      refs.totalReturn,
      refs.totalReturnPercent,
      ...Object.values(refs.returns),
      ...refs.wallets.flatMap((wallet) => [wallet.available, wallet.total, wallet.staking]),
    ].filter((entityId): entityId is string => entityId !== undefined);
  }

  protected override willUpdate(changed: PropertyValues): void {
    super.willUpdate(changed);
    const refs = this.hass ? findPortfolio(this.hass) : undefined;
    this.window = windowFor(this.timeframe, Date.now());
    // Bitpanda's value history comes with the returns: a new return of the
    // timeframe brings a new line (and the first one after a restart).
    const version = this.hass?.states[refs?.returns[this.timeframe] ?? ""]?.state ?? "";
    if (this.hass && refs && this.config?.show_graph !== false) this.lines.request(this.hass, [PORTFOLIO_LINE], this.window, version);
  }

  override getCardSize(): number {
    return this.config?.show_header === false ? 7 : 8;
  }

  /** A cursor moving along the line changes nothing fitLayout measures: its
   * marks lie over the line. */
  protected override remeasures(changed: PropertyValues): boolean {
    return !(changed.size === 1 && changed.has("cursor"));
  }

  /** Settles, for all rows and groups alike, where the staked share stands
   * (right of the units when every staked row has room for it, below them
   * otherwise) and where a group's and a row's chip and value stand
   * (blockLayout). */
  protected override fitLayout(): void {
    const all = (selector: string): HTMLElement[] => [...this.renderRoot.querySelectorAll<HTMLElement>(selector)];
    // A part every row or group renders, and one it may lack.
    const part = (parent: Element, selector: string): Element => parent.querySelector(selector) as Element;
    const measure = this.widthMeter();
    const width = (element: Element | null): number | undefined => (element ? measure(element) : undefined);
    const cells = all(".wallet .sub").map((sub) => {
      const badge = width(sub.querySelector(".stake .badge"));
      return { room: sub.clientWidth, first: measure(part(sub, ".s")), ...(badge === undefined ? {} : { second: badge }) };
    });
    const inline = allFit(cells, STAKE_GAP);
    if (inline !== this.stakeInline) this.stakeInline = inline;
    // Chip and value measured one by one: the same widths in every layout.
    const groups = all(".group").map((group) => {
      const chip = width(group.querySelector(".gchip"));
      return {
        room: group.clientWidth,
        left: measure(part(group, ".gleft")),
        ...(chip === undefined ? {} : { chip }),
        value: measure(part(group, ".sum")),
      };
    });
    const groupsLayout = blockLayout(groups);
    if (groupsLayout !== this.groupsLayout) this.groupsLayout = groupsLayout;
    // The units may wrap: their lines add up to their width on one line.
    const rows = all(".wallet .tap").map((tap) => ({
      room: tap.clientWidth,
      // Below the name, the row reaches under the chevron. Not the whole
      // row's width: in an open group that counts its indent.
      below: tap.clientWidth + UNDER_CHEVRON,
      left: measure(part(tap, ".s .units"), true),
      chip: measure(part(tap, ".wchip")),
      value: measure(part(tap, ".val")),
    }));
    const rowsLayout = blockLayout(rows);
    if (rowsLayout !== this.rowsLayout) this.rowsLayout = rowsLayout;
  }

  private groupChip(hass: Hass, wallets: readonly WalletRefs[]): TemplateResult | typeof nothing {
    const { text, direction } = formatPercent(hass, groupReturn(hass, wallets));
    // Unknown: a muted dash in place of the chip, as a wallet row shows.
    if (direction === "none") return html`<span class="gchip none">—</span>`;
    const mark = arrow(direction);
    return html`<span class="gchip ${trendClass(direction)}">${mark ? `${mark} ` : ""}${text}</span>`;
  }

  private walletsClass(): string {
    return [
      "wallets",
      this.stakeInline ? "stake-inline" : "",
      this.groupsLayout === "beside" ? "" : "groups-wrapped",
      this.groupsLayout === "stacked" ? "groups-stacked" : "",
      this.rowsLayout === "beside" ? "" : "rows-wrapped",
      this.rowsLayout === "stacked" ? "rows-stacked" : "",
    ]
      .filter(Boolean)
      .join(" ");
  }

  private toggle<T>(set: Set<T>, item: T): Set<T> {
    const next = new Set(set);
    if (next.has(item)) next.delete(item);
    else next.add(item);
    return next;
  }


  protected override render(): TemplateResult | typeof nothing {
    const hass = this.hass;
    const config = this.config;
    if (!hass || !config) return nothing;
    const refs = findPortfolio(hass);
    const eye = { hidden: this.amountsHidden, toggle: () => this.toggleAmounts() };
    const title = config.title || "Bitpanda Portfolio";
    const head = config.show_header !== false;
    // Without a Portfolio there is nothing to hide: no eye.
    if (!refs) return html`<ha-card>${head ? header(hass, title) : nothing}${emptyState(t(hass, "empty_portfolio"))}</ha-card>`;
    // A divider stands between two shown parts, never at the top.
    const top = config.show_total !== false || config.show_graph !== false;
    // The staking line belongs to the cash section, while it is drawn.
    const staking = config.show_staking !== false && stakedWallets(hass, refs).counted.length > 0;
    const pair = config.show_cash !== false || staking || config.show_allocation !== false;
    const shown = shownWallets(refs, config);
    // Without the header the eye goes beside the total value, or, without
    // that too, into a row of its own at the top.
    return html`<ha-card>
      ${head ? header(hass, title, eye) : nothing}
      <div class="content ${head ? "" : "headless"}">
        ${!head && config.show_total === false ? html`<div class="eye-row">${eyeButton(hass, eye)}</div>` : nothing}
        ${summary({
          host: this,
          hass,
          refs,
          timeframe: this.timeframe,
          hidden: this.amountsHidden,
          window: this.window,
          points: this.lines.series(PORTFOLIO_LINE),
          total: config.show_total !== false,
          since: config.show_since_purchase !== false,
          line: config.show_graph !== false,
          timeframes: config.show_timeframes !== false,
          eye: head ? undefined : eye,
          onTimeframe: (timeframe) => {
            this.cursor = undefined;
            this.selectTimeframe(timeframe);
          },
          cursor: this.cursor,
          onCursor: (index) => {
            if (index !== this.cursor) this.cursor = index;
          },
        })}
        ${pair
          ? html`${top ? html`<div class="divider"></div>` : nothing}
              ${config.show_cash === false ? nothing : this.renderCash(hass, refs)}
              ${staking ? this.renderStaking(hass, refs) : nothing}
              ${config.show_allocation === false ? nothing : this.renderAllocation(hass, refs)}`
          : nothing}
        ${config.show_wallets === false
          ? nothing
          : html`${top || pair ? html`<div class="divider"></div>` : nothing}${config.show_search && shown.length > 0
                ? searchField(hass, this.query, (query) => (this.query = query))
                : nothing}${this.renderWallets(hass, refs, shown, config)}`}
      </div>
    </ha-card>`;
  }

  private renderCash(hass: Hass, refs: PortfolioRefs): TemplateResult {
    const item = (label: string, entityId: string | undefined, end: boolean) => {
      const tap = tapTarget(this.amountsHidden ? undefined : opener(this, entityId));
      return html`<div class=${end ? "end" : ""} role=${tap.role} tabindex=${tap.tabindex} @click=${tap.click} @keydown=${tap.keydown}>
        <span class="k">${label}</span><span class="v">${amount(hass, formatState(hass, entityId), this.amountsHidden)}</span>
      </div>`;
    };
    return html`<div class="pair">${item(t(hass, "cash"), refs.cash, false)}${item(t(hass, "cash_plus"), refs.cashPlus, true)}</div>`;
  }

  /** "Staking · €918.24 in 2 wallets", over the whole portfolio; a tap
   * opens the wallets with something staked. The rewards are in the
   * wallets' details. */
  private renderStaking(hass: Hass, refs: PortfolioRefs): TemplateResult {
    const hidden = this.amountsHidden;
    const { counted, unknown } = stakedWallets(hass, refs);
    const stateOf = (wallet: WalletRefs) => (wallet.staking ? hass.states[wallet.staking] : undefined);
    // The staking sensors are in the Portfolio's currency; without any
    // currency known, the sum is a dash.
    const first = counted[0] ? stateOf(counted[0].wallet)?.attributes["unit_of_measurement"] : undefined;
    const unit = typeof first === "string" && first ? first : portfolioCurrency(hass, refs);
    // A staking sensor without a value leaves the sum and the count open.
    const total = unknown ? undefined : sumOf(counted.map((item) => item.value));
    const money = total === undefined || unit === undefined ? undefined : formatMoney(hass, total, unit);
    const count = unknown ? t(hass, "staking_wallets_other").replace("{count}", "—") : tCount(hass, "staking_wallets", counted.length);
    const open = this.stakingOpen;
    const toggle = () => {
      this.stakingOpen = !this.stakingOpen;
    };
    return html`<div class="staking" role="button" tabindex="0" aria-expanded=${open ? "true" : "false"} @click=${toggle} @keydown=${onActivate(toggle)}>
        ${icon(open ? CHEVRONS.down : CHEVRONS.right)}<span class="part"><span class="k">${t(hass, "staking_line")}</span></span>${DOT}<span class="part"
          >${amount(hass, money, hidden)} ${count}</span
        >
      </div>
      ${open
        ? html`<div class="staking-list">
            ${counted.map(({ wallet }) => {
              const apr = numberAttribute(stateOf(wallet), "apr_percent");
              const tap = tapTarget(hidden ? undefined : opener(this, wallet.staking));
              return html`<div class="staking-row" role=${tap.role} tabindex=${tap.tabindex} @click=${tap.click} @keydown=${tap.keydown}>
                <span class="staking-name">${wallet.shortName}</span>
                <span class="staking-value">${amount(hass, formatState(hass, wallet.staking), hidden)}${apr === undefined ? nothing : html`${DOT}${t(hass, "staking_apr", { apr: formatShare(hass, apr, 1) })}`}</span>
              </div>`;
            })}
          </div>`
        : nothing}`;
  }

  private renderAllocation(hass: Hass, refs: PortfolioRefs): TemplateResult {
    const parts: { key: Category | "cash" | "cash_plus"; label: string; value: number | undefined }[] = [];
    for (const category of CATEGORIES) {
      const wallets = refs.wallets.filter((wallet) => categoryOf(wallet) === category);
      if (wallets.length > 0) {
        parts.push({ key: category, label: categoryName(hass, category), value: sumOf(wallets.map((wallet) => numericState(hass, wallet.total))) });
      }
    }
    if (refs.cashPlus) parts.push({ key: "cash_plus", label: t(hass, "cash_plus"), value: numericState(hass, refs.cashPlus) });
    if (refs.cash) parts.push({ key: "cash", label: t(hass, "cash"), value: numericState(hass, refs.cash) });
    const total = sumOf(parts.map((part) => part.value));
    if (total === undefined) return html`<div class="allocation-missing muted">—</div>`;
    const shown = parts
      .map((part) => ({ ...part, share: total > 0 ? ((part.value as number) / total) * 100 : 0 }))
      .filter((part) => part.share > 0)
      .sort((a, b) => b.share - a.share);
    // The bar names its parts for a screen reader; the legend says the same
    // to the eye only.
    const label = t(hass, "allocation_label", { parts: shown.map((part) => `${part.label} ${allocationShare(hass, part.share)}`).join(", ") });
    return html`<div class="bar" role="img" aria-label=${label}>
        ${shown.map((part) => html`<span style="width:${part.share}%;background:${COLORS[part.key]}"></span>`)}
      </div>
      <div class="legend" aria-hidden="true">
        ${shown.map((part) => html`<span><i style="background:${COLORS[part.key]}"></i>${part.label} ${allocationShare(hass, part.share)}</span>`)}
      </div>`;
  }

  private renderWallets(hass: Hass, refs: PortfolioRefs, shown: WalletRefs[], config: PortfolioConfig): TemplateResult {
    if (refs.wallets.length === 0) return emptyState(t(hass, "empty_wallets"));
    if (shown.length === 0) return emptyState(t(hass, "empty_selection_wallets"));
    const sort = config.sort ?? "value";
    // While searching: every match, as one list without groups or limit.
    const query = config.show_search ? this.query.trim() : "";
    if (query) {
      const matches = sortWallets(
        hass,
        shown.filter((wallet) => matchesWallet(wallet, query)),
        sort,
      );
      return matches.length > 0
        ? html`<div class=${this.walletsClass()}>${matches.map((wallet) => this.renderWallet(hass, refs, wallet))}</div>`
        : html`<div class="search-none">${t(hass, "search_none", { query })}</div>`;
    }
    if (config.group_wallets === false) {
      // Without groups, the list stops at the limit, with Show all and
      // Show less.
      const sorted = sortWallets(hass, shown, sort);
      const limit = config.limit ?? DEFAULT_WALLET_LIMIT;
      const folds = limit > 0 && sorted.length > limit;
      const rows = folds && !this.showAll ? sorted.slice(0, limit) : sorted;
      return html`<div class=${this.walletsClass()}>${rows.map((wallet) => this.renderWallet(hass, refs, wallet))}</div>
        ${folds
          ? html`<button class="show-all" @click=${() => (this.showAll = !this.showAll)}>
              ${this.showAll ? t(hass, "show_less") : t(hass, "show_all", { count: sorted.length })}
            </button>`
          : nothing}`;
    }
    return html`<div class=${this.walletsClass()}>${CATEGORIES.map((category) => {
      // The group's count, return and sum cover the wallets it shows; the
      // total and the allocation above cover the whole portfolio.
      const members = shown.filter((wallet) => categoryOf(wallet) === category);
      if (members.length === 0) return nothing;
      const sum = sumOf(members.map((wallet) => numericState(hass, wallet.total)));
      const open = this.openGroups.has(category);
      const toggle = () => {
        this.openGroups = this.toggle(this.openGroups, category);
      };
      return html`<div class="group" role="button" tabindex="0" aria-expanded=${open ? "true" : "false"} @click=${toggle} @keydown=${onActivate(toggle)}>
          <span class="gleft"
            >${icon(open ? CHEVRONS.down : CHEVRONS.right)}<span class="name">${categoryName(hass, category)}</span
            ><span class="count">${members.length}</span></span
          >
          <span class="gright">${this.groupChip(hass, members)}<span class="sum">${amount(hass, formatLike(hass, members[0]?.total, sum), this.amountsHidden)}</span></span>
        </div>
        ${open ? html`<div class="members">${sortWallets(hass, members, sort).map((wallet) => this.renderWallet(hass, refs, wallet))}</div>` : nothing}`;
    })}</div>`;
  }

  private renderWallet(hass: Hass, refs: PortfolioRefs, wallet: WalletRefs): TemplateResult {
    const open = this.openWallets.has(wallet.deviceId);
    return html`${walletRow({
      hass,
      wallet,
      hidden: this.amountsHidden,
      onTap: opener(this, wallet.total),
      chevron: {
        open,
        toggle: () => {
          this.openWallets = this.toggle(this.openWallets, wallet.deviceId);
        },
      },
    })}${open ? this.renderDetail(hass, refs, wallet) : nothing}`;
  }

  private renderDetail(hass: Hass, refs: PortfolioRefs, wallet: WalletRefs): TemplateResult {
    const hidden = this.amountsHidden;
    // The wallet's own sensors are in the Portfolio's currency, Total value
    // enabled or not.
    const unitOf = (entityId: string | undefined) => (entityId ? hass.states[entityId]?.attributes["unit_of_measurement"] : undefined);
    const currency = String(unitOf(wallet.total) ?? unitOf(refs.totalValue) ?? "EUR");
    const totalState = wallet.total ? hass.states[wallet.total] : undefined;
    const stakingState = wallet.staking ? hass.states[wallet.staking] : undefined;
    const units = (entityId: string | undefined): string | undefined => {
      const value = numberAttribute(entityId ? hass.states[entityId] : undefined, "units");
      return value === undefined ? undefined : formatUnits(hass, value, wallet.category, wallet.symbol);
    };
    const money = (value: number | undefined, signed = false): string | undefined =>
      value === undefined ? undefined : formatMoney(hass, value, currency, signed);
    const price = (value: number | undefined): string | undefined =>
      value === undefined ? undefined : formatPrice(hass, value, currency);
    // A value breaks only between its parts, at the middle dot.
    const part = (content: unknown): TemplateResult => html`<span class="part">${content}</span>`;
    const position = (entityId: string | undefined) =>
      html`${part(amount(hass, units(entityId), hidden))}${DOT}${part(amount(hass, formatState(hass, entityId), hidden))}`;
    const profit = numberAttribute(totalState, "total_return");
    const percent = formatPercent(hass, numberAttribute(totalState, "total_return_percent"));
    // The price is a market price, not the user's amount: never blurred.
    const current = numberAttribute(totalState, "price");
    const dayReturn = numberAttribute(totalState, "return_24h");
    const dayChange = numberAttribute(totalState, "change_24h_pct");
    const day = formatPercent(hass, dayChange);
    const apr = numberAttribute(stakingState, "apr_percent");
    const count = numberAttribute(stakingState, "rewards_count");
    const lastAt = stakingState?.attributes["rewards_last_at"];
    const last = typeof lastAt === "string" && Number.isFinite(Date.parse(lastAt)) ? formatDayTime(hass, Date.parse(lastAt)) : "—";
    const recent = numberAttribute(stakingState, "rewards_net_30d");
    // What was earned, net of fees: its units and their value today.
    const earned = (units: number | undefined, value: number | undefined) =>
      html`${part(amount(hass, units === undefined ? undefined : formatUnits(hass, units, wallet.category, wallet.symbol), hidden))}${DOT}${part(
        amount(hass, money(value), hidden),
      )}`;
    // The staking block keeps its rows whether something is staked or not;
    // the rewards' rows come with the first payout.
    return html`<div class="detail">
      <div class="grid">
        <span>${t(hass, "detail_price")}</span><span>${current === undefined ? "—" : formatAssetPrice(hass, current, currency)}</span>
        <span>${t(hass, "detail_average_buy_price")}</span><span>${amount(hass, price(numberAttribute(totalState, "average_buy_price")), hidden)}</span>
        <span>${t(hass, "detail_invested")}</span><span>${amount(hass, money(numberAttribute(totalState, "invested_amount")), hidden)}</span>
        ${dayReturn !== undefined && dayChange !== undefined
          ? html`<span>${t(hass, "detail_return_24h")}</span
              ><span class=${trendClass(day.direction)}>${part(amount(hass, money(dayReturn, true), hidden))} ${part(`(${day.text})`)}</span>`
          : nothing}
        <span>${t(hass, "detail_total_return")}</span
        ><span class=${trendClass(percent.direction)}>${part(amount(hass, money(profit, true), hidden))} ${part(`(${percent.text})`)}</span>
      </div>
      ${wallet.staking
        ? html`<h4>${t(hass, "detail_staking")}</h4>
            <div class="grid">
              <span>${t(hass, "detail_staked")}</span><span>${position(wallet.staking)}</span>
              ${apr !== undefined ? html`<span>${t(hass, "detail_staking_apr")}</span><span>${formatShare(hass, apr, 1)}</span>` : nothing}
              ${count !== undefined && count > 0
                ? html`${recent === undefined
                      ? nothing
                      : html`<span>${t(hass, "detail_earned_30d")}</span
                          ><span>${earned(recent, numberAttribute(stakingState, "rewards_net_value_30d"))}</span>`}
                    <span>${t(hass, "detail_earned_total")}</span
                    ><span>${earned(numberAttribute(stakingState, "rewards_net"), numberAttribute(stakingState, "rewards_net_value"))}</span>
                    <span>${t(hass, "detail_payouts")}</span
                    ><span
                      >${t(hass, "detail_payouts_value", { count, date: last })
                        .split(" · ")
                        .map((text, index) => html`${index > 0 ? DOT : ""}${part(text)}`)}</span
                    >`
                : nothing}
            </div>`
        : nothing}
    </div>`;
  }
}

defineCard(TAG, PortfolioCard, {
  name: "Bitpanda Portfolio",
  description: () => t(editorHass(), "picker_portfolio"),
  model: ["Portfolio", "Wallet"],
});
