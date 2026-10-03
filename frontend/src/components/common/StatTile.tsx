interface StatTileProps {
  label: string;
  value: string;
  hint?: string;
  tone?: "emphasis" | "good" | "critical";
}

/** Big-number tile used across the planner and rebalance pages. */
export function StatTile({ label, value, hint, tone }: StatTileProps) {
  return (
    <div className={`stat-tile${tone ? ` stat-tile--${tone}` : ""}`}>
      <span className="stat-tile__label">{label}</span>
      <span className="stat-tile__value">{value}</span>
      {hint && <span className="stat-tile__hint">{hint}</span>}
    </div>
  );
}
