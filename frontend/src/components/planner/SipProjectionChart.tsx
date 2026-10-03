import { useMemo, useState } from "react";

import type { YearlyProjectionPoint } from "../../types/planning.types";
import { formatInr, formatInrCompact } from "../../utils/displayFormatters";

const WIDTH = 720;
const HEIGHT = 300;
const MARGIN = { top: 16, right: 16, bottom: 32, left: 64 };
const PLOT_W = WIDTH - MARGIN.left - MARGIN.right;
const PLOT_H = HEIGHT - MARGIN.top - MARGIN.bottom;

interface SipProjectionChartProps {
  points: YearlyProjectionPoint[];
  goalAmount: number | null;
}

/**
 * Fan chart: shaded bad–good range (10th–90th percentile), the typical (median)
 * line on top, and a dashed "money you put in" line for reference. One hue
 * family for the projection; the invested line stays neutral.
 */
export function SipProjectionChart({ points, goalAmount }: SipProjectionChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const series = useMemo(() => [{ year: 0, invested: 0, bad_case: 0, typical: 0, good_case: 0 }, ...points], [points]);

  const maxValue = Math.max(...series.map((p) => p.good_case), goalAmount ?? 0) * 1.05;
  const yTicks = niceTicks(maxValue, 5);
  const yMax = yTicks[yTicks.length - 1];
  const lastYear = series[series.length - 1].year;
  const x = (year: number) => MARGIN.left + (year / lastYear) * PLOT_W;
  const y = (value: number) => MARGIN.top + PLOT_H - (value / yMax) * PLOT_H;

  const line = (key: keyof YearlyProjectionPoint) => series.map((p, i) => `${i ? "L" : "M"}${x(p.year)},${y(p[key])}`).join(" ");
  const band =
    series.map((p, i) => `${i ? "L" : "M"}${x(p.year)},${y(p.good_case)}`).join(" ") +
    " " +
    [...series].reverse().map((p) => `L${x(p.year)},${y(p.bad_case)}`).join(" ") +
    " Z";
  const xTickEvery = lastYear <= 10 ? 1 : lastYear <= 20 ? 2 : 5;
  const active = hoverIndex !== null ? series[hoverIndex] : null;

  const handleMove = (event: React.PointerEvent<SVGRectElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const year = Math.round(((event.clientX - rect.left) / rect.width) * lastYear);
    setHoverIndex(Math.max(1, Math.min(series.length - 1, series.findIndex((p) => p.year === year))));
  };

  return (
    <figure className="fan-chart">
      <ul className="fan-chart__legend" aria-hidden="true">
        <li>
          <span className="fan-chart__key fan-chart__key--line" /> Typical
        </li>
        <li>
          <span className="fan-chart__key fan-chart__key--band" /> Bad – good range
        </li>
        <li>
          <span className="fan-chart__key fan-chart__key--invested" /> Money you put in
        </li>
        {goalAmount ? (
          <li>
            <span className="fan-chart__key fan-chart__key--goal" /> Goal
          </li>
        ) : null}
      </ul>

      <div className="fan-chart__frame">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Projected value of the SIP over time">
          {yTicks.map((tick) => (
            <g key={tick}>
              <line className="fan-chart__grid" x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={y(tick)} y2={y(tick)} />
              <text className="fan-chart__axis-label" x={MARGIN.left - 8} y={y(tick)} textAnchor="end" dominantBaseline="middle">
                {formatInrCompact(tick)}
              </text>
            </g>
          ))}
          {series
            .filter((p) => p.year > 0 && (p.year % xTickEvery === 0 || p.year === lastYear))
            .map((p) => (
              <text key={p.year} className="fan-chart__axis-label" x={x(p.year)} y={HEIGHT - 10} textAnchor="middle">
                {p.year}y
              </text>
            ))}

          <path className="fan-chart__band" d={band} />
          <path className="fan-chart__invested" d={line("invested")} />
          {goalAmount ? (
            <line className="fan-chart__goal" x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={y(goalAmount)} y2={y(goalAmount)} />
          ) : null}
          <path className="fan-chart__line" d={line("typical")} />

          {active && (
            <g>
              <line className="fan-chart__crosshair" x1={x(active.year)} x2={x(active.year)} y1={MARGIN.top} y2={MARGIN.top + PLOT_H} />
              <circle className="fan-chart__dot" cx={x(active.year)} cy={y(active.typical)} r={5} />
            </g>
          )}
          <rect
            x={MARGIN.left}
            y={MARGIN.top}
            width={PLOT_W}
            height={PLOT_H}
            fill="transparent"
            onPointerMove={handleMove}
            onPointerLeave={() => setHoverIndex(null)}
          />
        </svg>

        {active && (
          <div
            className="fan-chart__tooltip"
            style={{ left: `${(x(active.year) / WIDTH) * 100}%`, top: `${(y(active.good_case) / HEIGHT) * 100}%` }}
          >
            <strong>After {active.year} year{active.year > 1 ? "s" : ""}</strong>
            <span>Good case {formatInr(active.good_case)}</span>
            <span>Typical {formatInr(active.typical)}</span>
            <span>Bad case {formatInr(active.bad_case)}</span>
            <span className="muted">Invested {formatInr(active.invested)}</span>
          </div>
        )}
      </div>

      <details className="fan-chart__table">
        <summary>Show as table</summary>
        <div className="table-scroll">
          <table className="data-table data-table--compact">
            <thead>
              <tr>
                <th scope="col">Year</th>
                <th scope="col" className="num">Invested</th>
                <th scope="col" className="num">Bad case</th>
                <th scope="col" className="num">Typical</th>
                <th scope="col" className="num">Good case</th>
              </tr>
            </thead>
            <tbody>
              {points.map((p) => (
                <tr key={p.year}>
                  <td>{p.year}</td>
                  <td className="num">{formatInr(p.invested)}</td>
                  <td className="num">{formatInr(p.bad_case)}</td>
                  <td className="num">{formatInr(p.typical)}</td>
                  <td className="num">{formatInr(p.good_case)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

/** Round axis ticks (1, 2, 2.5, 5 × 10^n) covering 0..max. */
function niceTicks(max: number, count: number): number[] {
  if (max <= 0) return [0, 1];
  const rough = max / count;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= rough) ?? 10 * magnitude;
  const ticks = [];
  for (let value = 0; value <= max + step * 0.999; value += step) ticks.push(value);
  return ticks;
}
