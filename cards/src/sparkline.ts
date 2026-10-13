// Value and price lines as plain SVG, the way Home Assistant draws its own
// sparklines: on the window's time axis, broken where statistics are
// missing, no chart library.
import { svg, type TemplateResult } from "lit";

import { periodMs, type Point, type StatWindow } from "./statistics";

const MARGIN = 2;

const round = (value: number): number => Math.round(value * 100) / 100;

/** Where the line puts `value` in a box `height` high, from the top: the
 * highest value MARGIN below it, the lowest MARGIN above the bottom. */
export function lineTop(value: number, min: number, max: number, height: number): number {
  return max === min ? round(height / 2) : round(height - MARGIN - ((value - min) / (max - min)) * (height - 2 * MARGIN));
}

/** The index of the point nearest to `time`; of two as near, the earlier. */
export function nearestIndex(points: readonly Point[], time: number): number {
  let best = 0;
  points.forEach((point, index) => {
    if (Math.abs(point.t - time) < Math.abs((points[best] as Point).t - time)) best = index;
  });
  return best;
}

/** A run's first point, the first point of each `stepMs` slot after it and
 * its last point. The slots count from a fixed start, so the drawn points
 * keep their times when the window moves on. */
function thin(run: Point[], stepMs: number): Point[] {
  if (stepMs <= 0 || run.length < 3) return run;
  const slot = (point: Point): number => Math.floor(point.t / stepMs);
  const kept: Point[] = [];
  for (const point of run.slice(0, -1)) {
    const last = kept[kept.length - 1];
    if (!last || slot(point) !== slot(last)) kept.push(point);
  }
  kept.push(run[run.length - 1] as Point);
  return kept;
}

/** The points split where two neighbours lie more than 1.5 periods apart,
 * each run thinned to `stepMs`, as x/y coordinates in a width x height box. */
function segments(points: readonly Point[], window: StatWindow, width: number, height: number, gapMs?: number, stepMs = 0): [number, number][][] {
  const gap = gapMs ?? 1.5 * periodMs(window.period);
  const runs: Point[][] = [];
  let previous: Point | undefined;
  for (const point of points) {
    if (!previous || point.t - previous.t > gap) runs.push([]);
    runs[runs.length - 1]?.push(point);
    previous = point;
  }
  const drawn = runs.map((run) => thin(run, stepMs));
  const values = drawn.flat().map((point) => point.v);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = window.end - window.start;
  const x = (t: number): number => round(((t - window.start) / span) * width);
  const y = (v: number): number => lineTop(v, min, max, height);
  return drawn.map((run) => run.map((point): [number, number] => [x(point.t), y(point.v)]));
}

export function sparklinePath(points: readonly Point[], window: StatWindow, width: number, height: number, gapMs?: number, stepMs = 0): string {
  return segments(points, window, width, height, gapMs, stepMs)
    .map((segment) =>
      segment.length === 1
        ? `M${segment[0]?.[0]},${segment[0]?.[1]}l0.01,0`
        : segment.map(([px, py], index) => `${index === 0 ? "M" : "L"}${px},${py}`).join(""),
    )
    .join("");
}

export function sparklineArea(points: readonly Point[], window: StatWindow, width: number, height: number, gapMs?: number, stepMs = 0): string {
  return segments(points, window, width, height, gapMs, stepMs)
    .map((segment) => {
      const first = segment[0] as [number, number];
      const last = segment[segment.length - 1] as [number, number];
      return `M${first[0]},${height}${segment.map(([px, py]) => `L${px},${py}`).join("")}L${last[0]},${height}Z`;
    })
    .join("");
}

export interface SparklineOptions {
  width: number;
  height: number;
  fill: boolean;
  className: string;
  /** How far apart two points may lie and still be joined; 1.5 periods
   * when not given. A series without gaps passes Infinity. */
  gapMs?: number;
  /** How far apart drawn points lie at least; every point when not given. */
  stepMs?: number;
}

/** Whether the points cover a tenth of the window at least, enough to read
 * as a line: an asset tracked for minutes would draw a vertical stroke. */
export const longEnough = (points: readonly Point[], window: StatWindow): boolean =>
  points.length > 0 && (points[points.length - 1] as Point).t - (points[0] as Point).t >= (window.end - window.start) / 10;

export function renderSparkline(points: readonly Point[], window: StatWindow, options: SparklineOptions): TemplateResult {
  const { width, height, fill, className, gapMs, stepMs } = options;
  if (!longEnough(points, window)) {
    return svg`<svg class=${className} viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true"></svg>`;
  }
  return svg`<svg class=${className} viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">${
    fill ? svg`<path class="area" d=${sparklineArea(points, window, width, height, gapMs, stepMs)}></path>` : null
  }<path class="line" d=${sparklinePath(points, window, width, height, gapMs, stepMs)} vector-effect="non-scaling-stroke"></path></svg>`;
}
