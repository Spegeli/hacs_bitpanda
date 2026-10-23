// The top of the Portfolio card: total value, the return of the
// selected timeframe, the timeframe switch and the value line.
import { html, nothing, type TemplateResult } from "lit";

import { arrow, formatDay, formatDayTime, formatMoney, formatPercent, formatState, numberAttribute, numericState, trendClass } from "./format";
import { t } from "./i18n";
import { amount, eyeButton, opener, returnChip, tapTarget, timeframeSwitch, type Eye } from "./parts";
import { lineTop, longEnough, nearestIndex, renderSparkline } from "./sparkline";
import type { Point, StatWindow } from "./statistics";
import type { Hass, PortfolioRefs, Timeframe } from "./types";

export interface SummaryOptions {
  host: HTMLElement;
  hass: Hass;
  refs: PortfolioRefs;
  timeframe: Timeframe;
  hidden: boolean;
  window: StatWindow;
  points: Point[] | undefined;
  /** The total value and its return. */
  total: boolean;
  /** The return since purchase and the invested amount, under the return. */
  since: boolean;
  line: boolean;
  /** The timeframe buttons. */
  timeframes: boolean;
  /** The eye, beside the total value: given while the card has no header. */
  eye?: Eye | undefined;
  onTimeframe: (timeframe: Timeframe) => void;
  /** The point the cursor stands on, while the line is pointed at. */
  cursor: number | undefined;
  onCursor: (index: number | undefined) => void;
}

/** The line's box, as renderSparkline draws it. */
const LINE_WIDTH = 480;
const LINE_HEIGHT = 72;

const percent = (fraction: number): string => `${(fraction * 100).toFixed(2)}%`;

/** The value line with its dashed middle; pointed at by mouse or finger,
 * or moved along by the arrow keys, a cursor on the nearest point with its
 * time and value above it, and the highest, middle and lowest value at the
 * right. For a screen reader it is a slider named `name`, over the points. */
function plot(options: SummaryOptions, points: Point[], lineClass: string, name: string): TemplateResult {
  const { hass, refs, window, hidden, cursor, onCursor } = options;
  // The cursor stays on the points: a line fetched again can bring fewer
  // than it stood on.
  const last = points.length - 1;
  const index = cursor === undefined ? undefined : Math.min(cursor, last);
  const values = points.map((point) => point.v);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = window.end - window.start;
  const at = (event: PointerEvent): number => {
    const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
    const fraction = Math.min(Math.max((event.clientX - box.left) / box.width, 0), 1);
    return nearestIndex(points, window.start + fraction * span);
  };
  const show = (event: PointerEvent) => onCursor(at(event));
  const hide = () => onCursor(undefined);
  // A mouse button let go leaves the cursor where the mouse still is.
  const lift = (event: PointerEvent) => {
    if (event.pointerType !== "mouse") hide();
  };
  // Amounts in cents, in the Portfolio's currency, as the chip's amount;
  // none while the eye hides them or the currency is unknown.
  const unit = refs.totalValue ? hass.states[refs.totalValue]?.attributes["unit_of_measurement"] : undefined;
  const money = typeof unit === "string" && !hidden ? (value: number) => formatMoney(hass, value, unit) : undefined;
  const whenOf = (time: number): string =>
    window.timeframe === "day" || window.timeframe === "week" ? formatDayTime(hass, time) : formatDay(hass, time);
  const point = index === undefined ? undefined : points[index];
  let marks: TemplateResult | typeof nothing = nothing;
  if (point) {
    const x = (point.t - window.start) / span;
    const when = whenOf(point.t);
    // Near an edge the label ends, or starts, at the cursor.
    const side = x < 0.25 ? "start" : x > 0.75 ? "end" : "";
    marks = html`${money
        ? html`<span class="tag high">${money(max)}</span><span class="tag middle">${money((max + min) / 2)}</span
            ><span class="tag low">${money(min)}</span>`
        : nothing}
      <div class="cursor" style="left:${percent(x)}"></div>
      <div class="dot" style="left:${percent(x)};top:${percent(lineTop(point.v, min, max, LINE_HEIGHT) / LINE_HEIGHT)}"></div>
      <div class="tip ${side}" style="left:${percent(x)}">${money ? `${when} · ${money(point.v)}` : when}</div>`;
  }
  const line = renderSparkline(points, window, {
    width: LINE_WIDTH,
    height: LINE_HEIGHT,
    fill: true,
    className: `spark ${lineClass}`,
    // Bitpanda's value history has no gaps, only coarser steps on longer
    // timeframes.
    gapMs: Number.POSITIVE_INFINITY,
  });
  // A history too short to draw has no middle and nothing to point at.
  if (!longEnough(points, window)) return html`<div class="plot">${line}</div>`;
  // The keys move the one cursor the pointer moves too; focus alone sets
  // none. Without one, the slider reports the newest point: the first left
  // arrow goes one point back from it, the first right arrow to it.
  const step = (event: KeyboardEvent): void => {
    const next =
      event.key === "ArrowLeft"
        ? Math.max(0, (index ?? last) - 1)
        : event.key === "ArrowRight"
          ? index === undefined ? last : Math.min(last, index + 1)
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? last
              : undefined;
    if (next !== undefined) {
      event.preventDefault();
      onCursor(next);
    } else if (event.key === "Escape") hide();
  };
  // Value and time of the cursor's point, else of the newest; the time
  // alone while the eye hides amounts.
  const read = points[index ?? last] as Point;
  const valueText = money ? t(hass, "line_point", { value: money(read.v), time: whenOf(read.t) }) : whenOf(read.t);
  return html`<div
    class="plot"
    role="slider"
    tabindex="0"
    aria-label=${name}
    aria-valuemin="0"
    aria-valuemax=${last}
    aria-valuenow=${index ?? last}
    aria-valuetext=${valueText}
    @keydown=${step}
    @blur=${hide}
    @pointerdown=${show}
    @pointermove=${show}
    @pointerup=${lift}
    @pointercancel=${hide}
    @pointerleave=${hide}
  >
    ${line}
    <div class="mid"></div>
    ${marks}
  </div>`;
}

/** "Total value, 5 Oct – today": the line shows value, not return, from
 * where the statistics start. */
function caption(hass: Hass, window: StatWindow, points: Point[]): string {
  if (window.timeframe === "day") return t(hass, "value_line_day");
  const first = points[0]?.t ?? window.start;
  return t(hass, "value_line", { start: formatDay(hass, Math.max(window.start, first)) });
}

/** The Portfolio's currency: the unit of Total value, else of Invested,
 * else of any wallet's Balance (total) -- one of them may be disabled. */
export function portfolioCurrency(hass: Hass, refs: PortfolioRefs): string | undefined {
  for (const entityId of [refs.totalValue, refs.invested, ...refs.wallets.map((wallet) => wallet.total)]) {
    const unit = entityId ? hass.states[entityId]?.attributes["unit_of_measurement"] : undefined;
    if (typeof unit === "string" && unit) return unit;
  }
  return undefined;
}

/** What the return of `timeframe` means in money on today's total value,
 * as its sensor gives it (`return_amount`): Bitpanda's percentage leaves
 * deposits and withdrawals out, so the amount is taken from it, not from
 * the value's history. None without it. */
function returnAmount(hass: Hass, refs: PortfolioRefs, timeframe: Timeframe): string | undefined {
  const entityId = refs.returns[timeframe];
  const value = numberAttribute(entityId ? hass.states[entityId] : undefined, "return_amount");
  const unit = portfolioCurrency(hass, refs);
  return value === undefined || unit === undefined ? undefined : formatMoney(hass, value, unit, true);
}

/** The middle dot between a line's parts: it stays with the part before
 * it, and the line breaks only after it. */
const DOT = " · ";

/** The positions' return since purchase, under the return row: "Since
 * purchase ▲ +14.10% +€3,700.00" -- a dash for a part whose sensor is
 * missing or has no value, nothing without both. The chip opens Total
 * return %, the amount Total return. */
function sinceLine(options: SummaryOptions): TemplateResult | typeof nothing {
  const { host, hass, refs, hidden } = options;
  if (!refs.totalReturn && !refs.totalReturnPercent) return nothing;
  const { text, direction } = formatPercent(hass, numericState(hass, refs.totalReturnPercent));
  const mark = arrow(direction);
  const trend = trendClass(direction);
  const unit = portfolioCurrency(hass, refs);
  const value = numericState(hass, refs.totalReturn);
  const money = value === undefined || unit === undefined ? undefined : formatMoney(hass, value, unit, true);
  // The amounts open nothing while the eye hides them; the chip does.
  const tap = (className: string, entityId: string | undefined, content: unknown, gated: boolean): TemplateResult => {
    const target = tapTarget(gated && hidden ? undefined : opener(host, entityId));
    return html`<span class=${className} role=${target.role} tabindex=${target.tabindex} @click=${target.click} @keydown=${target.keydown}
      >${content}</span
    >`;
  };
  const chip =
    direction === "none"
      ? tap("since-chip none", refs.totalReturnPercent, "—", false)
      : tap(`since-chip ${trend}`, refs.totalReturnPercent, `${mark ? `${mark} ` : ""}${text}`, false);
  // It breaks after the label, never inside a figure: label, chip and
  // amount in one piece are wider than a narrow card.
  return html`<div class="since">
    <span class="part since-label">${t(hass, "since_purchase")}</span>
    <span class="part">${chip} ${tap(`since-amount ${trend}`, refs.totalReturn, amount(hass, money, hidden), true)}</span>
  </div>`;
}

export function summary(options: SummaryOptions): TemplateResult {
  const { host, hass, refs, timeframe, hidden, window, points } = options;
  const value = numericState(hass, refs.returns[timeframe]);
  // The line takes the colour of the return beside it; grey when it is
  // unchanged or unknown.
  const lineClass = trendClass(formatPercent(hass, value).direction) || "flat";
  // While the eye is closed, neither the total value nor the return chip
  // opens its dialog: both show an amount the eye hides.
  const open = (entityId: string | undefined) => (hidden ? undefined : opener(host, entityId));
  const hero = tapTarget(open(refs.totalValue));
  const total = html`<div class="hero" role=${hero.role} tabindex=${hero.tabindex} @click=${hero.click} @keydown=${hero.keydown}>
    ${amount(hass, formatState(hass, refs.totalValue), hidden)}
  </div>`;
  // The line is named by its caption, shown under it.
  const drawn = options.line && points !== undefined && points.length > 0;
  const name = drawn ? caption(hass, window, points) : "";
  // The timeframe buttons stay while the return or the line uses them.
  return html`${options.total
      ? html`${options.eye ? html`<div class="hero-row">${total}${eyeButton(hass, options.eye)}</div>` : total}
          ${returnChip(hass, value, timeframe, open(refs.returns[timeframe]), {
            text: returnAmount(hass, refs, timeframe),
            hidden,
          })}
          ${options.since ? sinceLine(options) : nothing}`
      : nothing}
    ${options.timeframes && (options.total || options.line) ? timeframeSwitch(hass, timeframe, options.onTimeframe) : nothing}
    ${drawn
      ? html`${plot(options, points, lineClass, name)}
          <div class="caption">${name}</div>`
      : nothing}`;
}
