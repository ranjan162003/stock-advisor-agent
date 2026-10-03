import { useState } from "react";

import type { BacktestPoint } from "../../types/planning.types";
import { formatInr, formatInrCompact, parseCalendarDate } from "../../utils/displayFormatters";

const WIDTH = 720;
const HEIGHT = 280;
const MARGIN = { top: 16, right: 16, bottom: 32, left: 64 };
const PLOT_W = WIDTH - MARGIN.left - MARGIN.right;
const PLOT_H = HEIGHT - MARGIN.top - MARGIN.bottom;
const DATE_FORMAT = new Intl.DateTimeFormat("en-IN", { month: "short", year: "numeric" });

interface SipBacktestChartProps {
  points: BacktestPoint[];
}

/** What the SIP was actually worth each month vs. the money put in so far. */
export function SipBacktestChart({ points }: SipBacktestChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const maxValue = Math.max(...points.map((p) => Math.max(p.value, p.invested))) * 1.05;
  const yTicks = niceTicks(maxValue, 5);
  const yMax = yTicks[yTicks.length - 1];
  const x = (i: number) => MARGIN.left + (i / (points.length - 1)) * PLOT_W;
  const y = (value: number) => MARGIN.top + PLOT_H - (value / yMax) * PLOT_H;

  const path = (key: "value" | "invested") => points.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p[key])}`).join(" ");
  // Shade the gap between value and invested: gains above, losses below.
  const gapArea =
    points.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.value)}`).join(" ") +
    " " +
    [...points].reverse().map((p, ri) => `L${x(points.length - 1 - ri)},${y(p.invested)}`).join(" ") +
    " Z";
  // One label per January, skipping any that would crowd the previous label.
  const minGap = Math.max(1, Math.round(points.length / 14));
  const yearTicks: { i: number; date: Date }[] = [];
  points.forEach((p, i) => {
    const date = parseCalendarDate(p.date);
    const isNewYear = i === 0 || date.getFullYear() !== parseCalendarDate(points[i - 1].date).getFullYear();
    const last = yearTicks[yearTicks.length - 1];
    if (isNewYear && (!last || i - last.i >= minGap)) yearTicks.push({ i, date });
  });
  const everyOther = yearTicks.length > 12;
  const active = hoverIndex !== null ? points[hoverIndex] : null;

  const handleMove = (event: React.PointerEvent<SVGRectElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const index = Math.round(((event.clientX - rect.left) / rect.width) * (points.length - 1));
    setHoverIndex(Math.max(0, Math.min(points.length - 1, index)));
  };

  return (
    <figure className="fan-chart">
      <ul className="fan-chart__legend" aria-hidden="true">
        <li>
          <span className="fan-chart__key fan-chart__key--line" /> Value of your SIP
        </li>
        <li>
          <span className="fan-chart__key fan-chart__key--invested" /> Money you put in
        </li>
      </ul>
      <div className="fan-chart__frame">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Historical value of the SIP over time">
          {yTicks.map((tick) => (
            <g key={tick}>
              <line className="fan-chart__grid" x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={y(tick)} y2={y(tick)} />
              <text className="fan-chart__axis-label" x={MARGIN.left - 8} y={y(tick)} textAnchor="end" dominantBaseline="middle">
                {formatInrCompact(tick)}
              </text>
            </g>
          ))}
          {yearTicks.filter((_, idx) => !everyOther || idx % 2 === 0).map(({ i, date }) => (
            <text key={i} className="fan-chart__axis-label" x={x(i)} y={HEIGHT - 10} textAnchor="middle">
              {date.getFullYear()}
            </text>
          ))}
          <path className="fan-chart__band" d={gapArea} />
          <path className="fan-chart__invested" d={path("invested")} />
          <path className="fan-chart__line" d={path("value")} />
          {active && hoverIndex !== null && (
            <g>
              <line className="fan-chart__crosshair" x1={x(hoverIndex)} x2={x(hoverIndex)} y1={MARGIN.top} y2={MARGIN.top + PLOT_H} />
              <circle className="fan-chart__dot" cx={x(hoverIndex)} cy={y(active.value)} r={5} />
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
        {active && hoverIndex !== null && (
          <div
            className="fan-chart__tooltip"
            style={{ left: `${(x(hoverIndex) / WIDTH) * 100}%`, top: `${(y(Math.max(active.value, active.invested)) / HEIGHT) * 100}%` }}
          >
            <strong>{DATE_FORMAT.format(parseCalendarDate(active.date))}</strong>
            <span>Worth {formatInr(active.value)}</span>
            <span className="muted">Invested {formatInr(active.invested)}</span>
          </div>
        )}
      </div>
    </figure>
  );
}

function niceTicks(max: number, count: number): number[] {
  if (max <= 0) return [0, 1];
  const rough = max / count;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= rough) ?? 10 * magnitude;
  const ticks = [];
  for (let value = 0; value <= max + step * 0.999; value += step) ticks.push(value);
  return ticks;
}
