// Lines and changes from Home Assistant's long-term statistics, which any
// user may read (recorder/statistics_during_period). An hour in which a
// sensor had no valid value has no row: lines get a gap there.
import type { Hass, Timeframe } from "./types";

export type Period = "5minute" | "hour" | "day";

export interface StatWindow {
  timeframe: Timeframe;
  start: number;
  end: number;
  period: Period;
}

export interface Point {
  t: number;
  v: number;
}

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

const SPANS: Record<Timeframe, [number, Period]> = {
  day: [DAY, "5minute"],
  week: [7 * DAY, "hour"],
  month: [30 * DAY, "hour"],
  six_month: [182 * DAY, "day"],
  year: [365 * DAY, "day"],
};

export function periodMs(period: Period): number {
  return period === "5minute" ? 5 * MINUTE : period === "hour" ? HOUR : DAY;
}

/** How far apart a line's drawn points lie at least: a month of hourly
 * statistics is drawn in 120 steps across the span it covers (every 6 hours
 * for a whole month, as in Bitpanda's own month); every other timeframe
 * point by point (0). Changes count from every point. */
export function lineStepMs(window: StatWindow): number {
  return window.timeframe === "month" ? (window.end - window.start) / 120 : 0;
}

export function windowFor(timeframe: Timeframe, now: number): StatWindow {
  const [span, period] = SPANS[timeframe];
  return { timeframe, start: now - span, end: now, period };
}

interface StatisticRow {
  start: number | string;
  state?: number | null;
}

const toTime = (start: number | string): number => (typeof start === "number" ? start : Date.parse(start));

/** The series of `entityIds` in `window`; undefined when the call failed
 * (the recorder still starting, the connection lost). */
export async function fetchSeries(
  hass: Hass,
  entityIds: readonly string[],
  window: StatWindow,
): Promise<Record<string, Point[]> | undefined> {
  if (entityIds.length === 0) return {};
  let answer: Record<string, StatisticRow[]>;
  try {
    answer = await hass.callWS<Record<string, StatisticRow[]>>({
      type: "recorder/statistics_during_period",
      start_time: new Date(window.start).toISOString(),
      end_time: new Date(window.end).toISOString(),
      statistic_ids: [...entityIds],
      period: window.period,
      types: ["state"],
    });
  } catch {
    return undefined;
  }
  const series: Record<string, Point[]> = {};
  for (const [entityId, rows] of Object.entries(answer)) {
    series[entityId] = rows
      .map((row) => ({ t: toTime(row.start), v: row.state }))
      .filter((point): point is Point => typeof point.v === "number" && Number.isFinite(point.t))
      .sort((a, b) => a.t - b.t);
  }
  return series;
}

/** The key of the Portfolio's line among a loader's series. */
export const PORTFOLIO_LINE = "portfolio";

/** The Portfolio's value over the window's timeframe: Bitpanda's own
 * history, which the integration keeps from its returns and hands on with
 * bitpanda/portfolio_history. Undefined when the call failed. */
export async function fetchPortfolioLine(
  hass: Hass,
  _entityIds: readonly string[],
  window: StatWindow,
): Promise<Record<string, Point[]> | undefined> {
  let answer: { points?: unknown } | undefined;
  try {
    answer = await hass.callWS<{ points?: unknown }>({ type: "bitpanda/portfolio_history", timeframe: window.timeframe });
  } catch {
    return undefined;
  }
  const pairs: unknown[] = Array.isArray(answer?.points) ? answer.points : [];
  const points = pairs
    .filter(
      (pair): pair is [number, number] =>
        Array.isArray(pair) && typeof pair[0] === "number" && typeof pair[1] === "number" && Number.isFinite(pair[0]) && Number.isFinite(pair[1]),
    )
    .map(([t, v]) => ({ t, v }))
    .sort((a, b) => a.t - b.t);
  return { [PORTFOLIO_LINE]: points };
}

type Fetcher = (hass: Hass, entityIds: readonly string[], window: StatWindow) => Promise<Record<string, Point[]> | undefined>;

/** Keeps the series of one card. Fetches again only when the set of
 * entities, the timeframe or the caller's `version` changes, or the window
 * has moved by a period, and with the next request after a failed call; an answer for a request
 * that a newer one replaced is dropped. A new timeframe drops the old
 * timeframe's series at once: no line beats a line on the wrong axis. */
export class SeriesLoader {
  private key = "";
  private timeframe?: Timeframe;
  private end = 0;
  private latest = 0;
  private current: Record<string, Point[]> = {};

  constructor(
    private readonly onUpdate: () => void,
    private readonly fetch: Fetcher = fetchSeries,
  ) {}

  request(hass: Hass, entityIds: readonly string[], window: StatWindow, version = ""): void {
    const key = `${window.timeframe}|${[...entityIds].sort().join(",")}|${version}`;
    if (key === this.key && window.end - this.end < periodMs(window.period)) return;
    if (window.timeframe !== this.timeframe) this.current = {};
    this.key = key;
    this.timeframe = window.timeframe;
    this.end = window.end;
    const ticket = ++this.latest;
    void this.fetch(hass, entityIds, window).then((series) => {
      if (ticket !== this.latest) return;
      if (series === undefined) {
        this.key = "";
        return;
      }
      this.current = series;
      this.onUpdate();
    });
  }

  series(entityId: string): Point[] | undefined {
    return this.current[entityId];
  }
}

/** The change from the window's first point to `current`, in percent and
 * as an amount; `since` is that point's time when the statistics start
 * later than the window does (tracked for less than the window). Undefined
 * when a value is missing. A point up to one period before the window's
 * start counts: series are fetched again only once the window has moved by
 * a period. */
export function changeFromSeries(
  points: readonly Point[],
  current: number | undefined,
  window: StatWindow,
): { change: number; amount: number; since?: number } | undefined {
  const period = periodMs(window.period);
  const first = points.find((point) => point.t >= window.start - period);
  if (current === undefined || first === undefined || first.v === 0) return undefined;
  return {
    change: ((current - first.v) / first.v) * 100,
    amount: current - first.v,
    ...(first.t > window.start + period ? { since: first.t } : {}),
  };
}
