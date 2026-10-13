import { render } from "lit";
import { describe, expect, it } from "vitest";

import { lineTop, nearestIndex, renderSparkline, sparklineArea, sparklinePath } from "../src/sparkline";
import type { StatWindow } from "../src/statistics";

const HOUR = 3_600_000;
// Points 5 hours apart count as neighbours in a window of daily statistics,
// and as a gap in one of hourly statistics.
const window: StatWindow = { timeframe: "week", start: 0, end: 10 * HOUR, period: "day" };
const hourly: StatWindow = { ...window, period: "hour" };

describe("nearestIndex", () => {
  it("finds the point nearest in time, the earlier of two as near", () => {
    const points = [{ t: 0, v: 1 }, { t: 10, v: 2 }, { t: 20, v: 3 }];
    expect(nearestIndex(points, -5)).toBe(0);
    expect(nearestIndex(points, 4)).toBe(0);
    expect(nearestIndex(points, 6)).toBe(1);
    expect(nearestIndex(points, 15)).toBe(1);
    expect(nearestIndex(points, 99)).toBe(2);
  });
});

describe("lineTop", () => {
  it("places a value as the line does: the highest 2 units below the top, the lowest 2 above the bottom", () => {
    expect(lineTop(10, 0, 10, 72)).toBe(2);
    expect(lineTop(0, 0, 10, 72)).toBe(70);
    expect(lineTop(5, 0, 10, 72)).toBe(36);
    expect(lineTop(3, 3, 3, 72)).toBe(36);
    // The same place sparklinePath draws the point at.
    expect(sparklinePath([{ t: 0, v: 0 }, { t: 10 * HOUR, v: 10 }], window, 100, 72)).toBe(`M0,${lineTop(0, 0, 10, 72)}L100,${lineTop(10, 0, 10, 72)}`);
  });
});

describe("sparklinePath", () => {
  it("places points on the window's time axis", () => {
    const path = sparklinePath(
      [
        { t: 0, v: 1 },
        { t: 5 * HOUR, v: 3 },
        { t: 10 * HOUR, v: 2 },
      ],
      window,
      100,
      24,
    );
    expect(path).toBe("M0,22L50,2L100,12");
  });

  it("starts where the statistics start, leaving the earlier window empty", () => {
    const path = sparklinePath(
      [
        { t: 8 * HOUR, v: 1 },
        { t: 9 * HOUR, v: 2 },
      ],
      window,
      100,
      24,
    );
    expect(path).toBe("M80,22L90,2");
  });

  it("breaks the line at a gap", () => {
    const path = sparklinePath(
      [
        { t: 0, v: 1 },
        { t: HOUR, v: 2 },
        { t: 5 * HOUR, v: 1 },
        { t: 6 * HOUR, v: 2 },
      ],
      hourly,
      100,
      24,
    );
    expect(path).toBe("M0,22L10,2M50,22L60,2");
  });

  it("with a step, draws a run's points no closer than the step, keeping its first and last point and its gaps", () => {
    const run = (from: number, count: number) => Array.from({ length: count }, (_, index) => ({ t: (from + index) * HOUR, v: (from + index) % 2 }));
    // Hours 0 to 13, a gap, hours 20 to 23; x is ten times the hour.
    const points = [...run(0, 14), ...run(20, 4)];
    const day: StatWindow = { timeframe: "month", start: 0, end: 24 * HOUR, period: "hour" };
    const xs = (path: string): number[] => [...path.matchAll(/[ML](-?\d+(?:\.\d+)?),/g)].map((match) => Number(match[1]));
    const path = sparklinePath(points, day, 240, 24, undefined, 6 * HOUR);
    expect(xs(path)).toEqual([0, 60, 120, 130, 200, 230]);
    expect(path.match(/M/g)).toHaveLength(2);
    // Without a step, every point.
    expect(xs(sparklinePath(points, day, 240, 24))).toHaveLength(18);
  });

  it("with a step, keeps the drawn points' times when the window moves on: the step's slots count from a fixed start", () => {
    // Hours 1 to 13: hour 1 opens the run, 6 and 12 open their 6-hour slots, 13 ends the run.
    const points = Array.from({ length: 13 }, (_, index) => ({ t: (1 + index) * HOUR, v: index % 2 }));
    const day: StatWindow = { timeframe: "month", start: 0, end: 24 * HOUR, period: "hour" };
    const xs = [...sparklinePath(points, day, 240, 24, undefined, 6 * HOUR).matchAll(/[ML](-?\d+(?:\.\d+)?),/g)].map((match) => Number(match[1]));
    expect(xs).toEqual([10, 60, 120, 130]);
  });

  it("a single point draws a dot-length segment", () => {
    expect(sparklinePath([{ t: 5 * HOUR, v: 3 }], window, 100, 24)).toBe("M50,12l0.01,0");
  });

  it("a series covering under a tenth of the window draws nothing", () => {
    const host = document.createElement("div");
    const late = [
      { t: 9.1 * HOUR, v: 1 },
      { t: 9.95 * HOUR, v: 3 },
    ];
    render(renderSparkline(late, window, { width: 100, height: 24, fill: true, className: "mini" }), host);
    expect(host.querySelectorAll("path")).toHaveLength(0);
  });

  it("no points draw nothing", () => {
    expect(sparklinePath([], window, 100, 24)).toBe("");
    expect(sparklineArea([], window, 100, 24)).toBe("");
  });

  it("a flat series sits in the middle", () => {
    expect(
      sparklinePath(
        [
          { t: 0, v: 5 },
          { t: 10 * HOUR, v: 5 },
        ],
        window,
        100,
        24,
      ),
    ).toBe("M0,12L100,12");
  });

  it("fills the area under each segment down to the bottom", () => {
    expect(
      sparklineArea(
        [
          { t: 0, v: 1 },
          { t: 5 * HOUR, v: 3 },
        ],
        window,
        100,
        24,
      ),
    ).toBe("M0,24L0,22L50,2L50,24Z");
  });
});

describe("renderSparkline", () => {
  const points = [
    { t: 0, v: 1 },
    { t: 5 * HOUR, v: 3 },
  ];

  it("draws an svg with the line, and the area when asked", () => {
    const host = document.createElement("div");
    render(renderSparkline(points, window, { width: 100, height: 24, fill: true, className: "spark" }), host);
    const svg = host.querySelector("svg");
    expect(svg?.getAttribute("class")).toBe("spark");
    expect(svg?.getAttribute("viewBox")).toBe("0 0 100 24");
    expect(svg?.getAttribute("preserveAspectRatio")).toBe("none");
    expect([...host.querySelectorAll("path")].map((path) => path.getAttribute("class"))).toEqual(["area", "line"]);
  });

  it("draws one stroke when told the series has no gaps", () => {
    const sparse = [
      { t: 0, v: 1 },
      { t: 5 * HOUR, v: 2 },
      { t: 10 * HOUR, v: 3 },
    ];
    const host = document.createElement("div");
    render(renderSparkline(sparse, hourly, { width: 100, height: 24, fill: false, className: "mini" }), host);
    expect(host.querySelector("path")?.getAttribute("d")?.match(/M/g)).toHaveLength(3);
    render(renderSparkline(sparse, hourly, { width: 100, height: 24, fill: false, className: "mini", gapMs: Number.POSITIVE_INFINITY }), host);
    expect(host.querySelector("path")?.getAttribute("d")?.match(/M/g)).toHaveLength(1);
  });

  it("draws the line alone without fill", () => {
    const host = document.createElement("div");
    render(renderSparkline(points, window, { width: 100, height: 24, fill: false, className: "mini" }), host);
    expect([...host.querySelectorAll("path")].map((path) => path.getAttribute("class"))).toEqual(["line"]);
    expect(host.querySelector("path")?.getAttribute("d")).toBe("M0,22L50,2");
  });
});
