import { describe, expect, it, vi } from "vitest";

import {
  PORTFOLIO_LINE,
  SeriesLoader,
  changeFromSeries,
  fetchPortfolioLine,
  fetchSeries,
  lineStepMs,
  periodMs,
  windowFor,
  type StatWindow,
} from "../src/statistics";
import { makeHass } from "./fixtures";

const HOUR = 3_600_000;
const DAY = 24 * HOUR;
const NOW = Date.UTC(2026, 9, 12, 12, 0);

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

describe("windowFor", () => {
  it("gives each timeframe its span and period", () => {
    expect(windowFor("day", NOW)).toEqual({ timeframe: "day", start: NOW - DAY, end: NOW, period: "5minute" });
    expect(windowFor("week", NOW)).toMatchObject({ start: NOW - 7 * DAY, period: "hour" });
    expect(windowFor("month", NOW)).toMatchObject({ start: NOW - 30 * DAY, period: "hour" });
    expect(windowFor("six_month", NOW)).toMatchObject({ start: NOW - 182 * DAY, period: "day" });
    expect(windowFor("year", NOW)).toMatchObject({ start: NOW - 365 * DAY, period: "day" });
    expect(periodMs("5minute")).toBe(300_000);
    expect(periodMs("hour")).toBe(HOUR);
    expect(periodMs("day")).toBe(DAY);
  });
});

describe("lineStepMs", () => {
  it("draws a month every 6 hours, as dense as Bitpanda's own month, every other timeframe point by point", () => {
    expect(lineStepMs(windowFor("month", NOW))).toBe(6 * HOUR);
    for (const timeframe of ["day", "week", "six_month", "year"] as const) expect(lineStepMs(windowFor(timeframe, NOW)), timeframe).toBe(0);
  });

  it("draws a young asset's month by the span it covers: about 120 points, never coarser than its week", () => {
    expect(lineStepMs({ ...windowFor("month", NOW), start: NOW - 3 * DAY })).toBe((3 * DAY) / 120);
  });
});

describe("fetchSeries", () => {
  const window = windowFor("week", NOW);

  it("asks for state over the window", async () => {
    const hass = makeHass({ callWS: async () => ({}) });
    await fetchSeries(hass, ["sensor.a", "sensor.b"], window);
    expect(hass.messages).toEqual([
      {
        type: "recorder/statistics_during_period",
        start_time: new Date(window.start).toISOString(),
        end_time: new Date(window.end).toISOString(),
        statistic_ids: ["sensor.a", "sensor.b"],
        period: "hour",
        types: ["state"],
      },
    ]);
  });

  it("returns points sorted by time, from epoch or ISO starts", async () => {
    const hass = makeHass({
      callWS: async () => ({
        "sensor.a": [
          { start: NOW - HOUR, end: NOW, state: 2 },
          { start: new Date(NOW - 2 * HOUR).toISOString(), end: NOW - HOUR, state: 1 },
        ],
      }),
    });
    expect(await fetchSeries(hass, ["sensor.a"], window)).toEqual({
      "sensor.a": [
        { t: NOW - 2 * HOUR, v: 1 },
        { t: NOW - HOUR, v: 2 },
      ],
    });
  });

  it("drops rows without a value", async () => {
    const hass = makeHass({
      callWS: async () => ({ "sensor.a": [{ start: NOW - HOUR, state: null }, { start: NOW, state: 3 }, { start: "nonsense", state: 4 }] }),
    });
    expect(await fetchSeries(hass, ["sensor.a"], window)).toEqual({ "sensor.a": [{ t: NOW, v: 3 }] });
  });

  it("a failed call yields nothing, which the loader tells from an empty answer", async () => {
    const hass = makeHass({ callWS: async () => Promise.reject(new Error("recorder not loaded")) });
    expect(await fetchSeries(hass, ["sensor.a"], window)).toBeUndefined();
  });

  it("no entities ask for nothing", async () => {
    const hass = makeHass();
    expect(await fetchSeries(hass, [], window)).toEqual({});
    expect(hass.messages).toEqual([]);
  });
});

describe("fetchPortfolioLine", () => {
  it("asks the integration for Bitpanda's value history of the timeframe", async () => {
    const hass = makeHass({ callWS: async () => ({ points: [[NOW, 2], [NOW - HOUR, 1], ["x", 3], [NOW, null]] }) });
    expect(await fetchPortfolioLine(hass, [], windowFor("week", NOW))).toEqual({
      [PORTFOLIO_LINE]: [
        { t: NOW - HOUR, v: 1 },
        { t: NOW, v: 2 },
      ],
    });
    expect(hass.messages).toEqual([{ type: "bitpanda/portfolio_history", timeframe: "week" }]);
  });

  it("a failed call yields nothing, so the loader asks again", async () => {
    const hass = makeHass({ callWS: async () => Promise.reject(new Error("unknown command")) });
    expect(await fetchPortfolioLine(hass, [], windowFor("day", NOW))).toBeUndefined();
  });

  it("an answer without points draws no line", async () => {
    const hass = makeHass({ callWS: async () => ({}) });
    expect(await fetchPortfolioLine(hass, [], windowFor("day", NOW))).toEqual({ [PORTFOLIO_LINE]: [] });
  });
});

describe("SeriesLoader", () => {
  it("fetches with the fetcher it was given", async () => {
    const hass = makeHass({ callWS: async () => ({ points: [[NOW, 5]] }) });
    const onUpdate = vi.fn();
    const loader = new SeriesLoader(onUpdate, fetchPortfolioLine);
    loader.request(hass, [PORTFOLIO_LINE], windowFor("month", NOW));
    await vi.waitFor(() => expect(onUpdate).toHaveBeenCalledTimes(1));
    expect(loader.series(PORTFOLIO_LINE)).toEqual([{ t: NOW, v: 5 }]);
  });

  it("refetches only when the window or the entities change", async () => {
    const hass = makeHass({ callWS: async () => ({ "sensor.a": [{ start: NOW, state: 1 }] }) });
    const onUpdate = vi.fn();
    const loader = new SeriesLoader(onUpdate);
    loader.request(hass, ["sensor.a"], windowFor("week", NOW));
    await vi.waitFor(() => expect(onUpdate).toHaveBeenCalledTimes(1));
    expect(loader.series("sensor.a")).toEqual([{ t: NOW, v: 1 }]);
    loader.request(hass, ["sensor.a"], windowFor("week", NOW + 10 * 60_000));
    expect(hass.messages).toHaveLength(1);
    loader.request(hass, ["sensor.a"], windowFor("week", NOW + HOUR));
    loader.request(hass, ["sensor.a", "sensor.b"], windowFor("week", NOW + HOUR));
    loader.request(hass, ["sensor.a", "sensor.b"], windowFor("month", NOW + HOUR));
    expect(hass.messages).toHaveLength(4);
  });

  it("does not refetch when only the order of the entities changes", () => {
    // A list sorted by change reorders its rows with every price tick.
    const hass = makeHass({ callWS: async () => ({}) });
    const loader = new SeriesLoader(() => undefined);
    loader.request(hass, ["sensor.a", "sensor.b"], windowFor("week", NOW));
    loader.request(hass, ["sensor.b", "sensor.a"], windowFor("week", NOW));
    expect(hass.messages).toHaveLength(1);
  });

  it("ignores an answer for a superseded window", async () => {
    const slow = deferred<unknown>();
    const fast = deferred<unknown>();
    const answers = [slow.promise, fast.promise];
    const hass = makeHass({ callWS: async () => answers.shift() });
    const onUpdate = vi.fn();
    const loader = new SeriesLoader(onUpdate);
    loader.request(hass, ["sensor.a"], windowFor("week", NOW));
    loader.request(hass, ["sensor.a"], windowFor("year", NOW));
    fast.resolve({ "sensor.a": [{ start: NOW, state: 2 }] });
    await vi.waitFor(() => expect(onUpdate).toHaveBeenCalledTimes(1));
    slow.resolve({ "sensor.a": [{ start: NOW, state: 1 }] });
    await new Promise((done) => setTimeout(done, 0));
    expect(onUpdate).toHaveBeenCalledTimes(1);
    expect(loader.series("sensor.a")).toEqual([{ t: NOW, v: 2 }]);
  });

  it("asks again with the next request after a failed call", async () => {
    let calls = 0;
    const hass = makeHass({
      callWS: async () => {
        calls += 1;
        if (calls === 1) throw new Error("recorder not loaded");
        return { "sensor.a": [{ start: NOW, state: 1 }] };
      },
    });
    const onUpdate = vi.fn();
    const loader = new SeriesLoader(onUpdate);
    loader.request(hass, ["sensor.a"], windowFor("year", NOW));
    await vi.waitFor(() => expect(calls).toBe(1));
    await new Promise((done) => setTimeout(done, 0));
    expect(onUpdate).not.toHaveBeenCalled();
    loader.request(hass, ["sensor.a"], windowFor("year", NOW + 60_000));
    await vi.waitFor(() => expect(onUpdate).toHaveBeenCalledTimes(1));
    expect(loader.series("sensor.a")).toEqual([{ t: NOW, v: 1 }]);
  });

  it("drops the old timeframe's series as soon as the timeframe changes", async () => {
    const pending = deferred<unknown>();
    const answers: Promise<unknown>[] = [Promise.resolve({ "sensor.a": [{ start: NOW, state: 1 }] }), pending.promise];
    const hass = makeHass({ callWS: async () => answers.shift() });
    const onUpdate = vi.fn();
    const loader = new SeriesLoader(onUpdate);
    loader.request(hass, ["sensor.a"], windowFor("day", NOW));
    await vi.waitFor(() => expect(onUpdate).toHaveBeenCalledTimes(1));
    loader.request(hass, ["sensor.a"], windowFor("year", NOW));
    expect(loader.series("sensor.a")).toBeUndefined();
  });

  it("keeps the series of entities still shown when only the rows change", async () => {
    const pending = deferred<unknown>();
    const answers: Promise<unknown>[] = [Promise.resolve({ "sensor.a": [{ start: NOW, state: 1 }] }), pending.promise];
    const hass = makeHass({ callWS: async () => answers.shift() });
    const onUpdate = vi.fn();
    const loader = new SeriesLoader(onUpdate);
    loader.request(hass, ["sensor.a"], windowFor("week", NOW));
    await vi.waitFor(() => expect(onUpdate).toHaveBeenCalledTimes(1));
    loader.request(hass, ["sensor.a", "sensor.b"], windowFor("week", NOW));
    expect(loader.series("sensor.a")).toEqual([{ t: NOW, v: 1 }]);
  });

  it("has no series before its first answer", () => {
    expect(new SeriesLoader(() => undefined).series("sensor.a")).toBeUndefined();
  });
});

describe("changeFromSeries", () => {
  const window: StatWindow = windowFor("week", NOW);

  it("over a full window, in percent and in the currency", () => {
    const points = [
      { t: window.start, v: 100 },
      { t: window.start + DAY, v: 110 },
    ];
    const measured = changeFromSeries(points, 104.18, window);
    expect(measured?.change).toBeCloseTo(4.18, 6);
    expect(measured?.amount).toBeCloseTo(4.18, 6);
    expect(measured?.since).toBeUndefined();
  });

  it("starts at the first point inside the window, or at most a period before it", () => {
    expect(changeFromSeries([{ t: window.start - HOUR, v: 100 }], 110, window)?.change).toBeCloseTo(10, 6);
    const points = [
      { t: window.start - 2 * HOUR, v: 50 },
      { t: window.start + 30 * 60_000, v: 100 },
    ];
    expect(changeFromSeries(points, 110, window)?.change).toBeCloseTo(10, 6);
  });

  it("measures from the first point when the statistics start inside the window, and says since when", () => {
    const measured = changeFromSeries([{ t: window.start + 2 * HOUR, v: 100 }], 110, window);
    expect(measured?.change).toBeCloseTo(10, 6);
    expect(measured?.amount).toBeCloseTo(10, 6);
    expect(measured?.since).toBe(window.start + 2 * HOUR);
  });

  it("is undefined without a current value, a base or any point", () => {
    expect(changeFromSeries([{ t: window.start, v: 100 }], undefined, window)).toBeUndefined();
    expect(changeFromSeries([{ t: window.start, v: 0 }], 5, window)).toBeUndefined();
    expect(changeFromSeries([], 5, window)).toBeUndefined();
  });
});
