import { CountUp } from "./CountUp";

interface StatTileProps {
  label: string;
  value: string;
  /** Optional: count up to this number on first show, formatted with `format` (falls back to `value`). */
  countTo?: number;
  format?: (value: number) => string;
  hint?: string;
  tone?: "emphasis" | "good" | "critical";
}

/** Big-number tile used on the SIP planner. */
export function StatTile({ label, value, countTo, format, hint, tone }: StatTileProps) {
  return (
    <div className={`stat-tile${tone ? ` stat-tile--${tone}` : ""}`}>
      <span className="stat-tile__label">{label}</span>
      <span className="stat-tile__value">
        {countTo !== undefined && format ? <CountUp value={countTo} format={format} /> : value}
      </span>
      {hint && <span className="stat-tile__hint">{hint}</span>}
    </div>
  );
}
