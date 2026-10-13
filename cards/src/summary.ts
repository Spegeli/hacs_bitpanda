// The top of the Portfolio card: total value, the return of the
// selected timeframe, the timeframe switch and the value line.
import { html, nothing, type TemplateResult } from "lit";

import { formatDay, formatDayTime, formatMoney, formatPercent, formatState, numericState, trendClass } from "./format";
import { t } from "./i18n";
import { amount, moreInfo, onActivate, returnChip, timeframeSwitch } from "./parts";
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
  line: boolean;
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
 * a cursor on the nearest point with its time and value above it, and the
 * highest, middle and lowest value at the right. */
function plot(options: SummaryOptions, points: Point[], lineClass: string): TemplateResult {
  const { hass, refs, window, hidden, cursor, onCursor } = options;
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
  const point = cursor === undefined ? undefined : points[cursor];
  let marks: TemplateResult | typeof nothing = nothing;
  if (point) {
    const x = (point.t - window.start) / span;
    const when = window.timeframe === "day" || window.timeframe === "week" ? formatDayTime(hass, point.t) : formatDay(hass, point.t);
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
  return html`<div class="plot" @pointerdown=${show} @pointermove=${show} @pointerup=${lift} @pointercancel=${hide} @pointerleave=${hide}>
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

/** What the return of `timeframe` means in money on today's total value:
 * Bitpanda's percentage leaves deposits and withdrawals out, so the amount
 * is taken from it, not from the value's history. */
function returnAmount(hass: Hass, refs: PortfolioRefs, timeframe: Timeframe): string | undefined {
  const total = numericState(hass, refs.totalValue);
  const percent = numericState(hass, refs.returns[timeframe]);
  const unit = refs.totalValue ? hass.states[refs.totalValue]?.attributes["unit_of_measurement"] : undefined;
  if (total === undefined || percent === undefined || percent <= -100 || typeof unit !== "string") return undefined;
  return formatMoney(hass, (total * percent) / (100 + percent), unit, true);
}

export function summary(options: SummaryOptions): TemplateResult {
  const { host, hass, refs, timeframe, hidden, window, points } = options;
  const value = numericState(hass, refs.returns[timeframe]);
  // The line takes the colour of the return beside it; grey when it is
  // unchanged or unknown.
  const lineClass = trendClass(formatPercent(hass, value).direction) || "flat";
  const open = (entityId: string | undefined) => () => {
    if (entityId) moreInfo(host, entityId);
  };
  // The timeframe buttons stay while the return or the line uses them.
  return html`${options.total
      ? html`<div class="hero" role="button" tabindex="0" @click=${open(refs.totalValue)} @keydown=${onActivate(open(refs.totalValue))}>
            ${amount(formatState(hass, refs.totalValue), hidden)}
          </div>
          ${returnChip(hass, value, timeframe, open(refs.returns[timeframe]), {
            text: returnAmount(hass, refs, timeframe),
            hidden,
          })}`
      : nothing}
    ${options.total || options.line ? timeframeSwitch(hass, timeframe, options.onTimeframe) : nothing}
    ${options.line && points && points.length > 0
      ? html`${plot(options, points, lineClass)}
          <div class="caption">${caption(hass, window, points)}</div>`
      : nothing}`;
}
