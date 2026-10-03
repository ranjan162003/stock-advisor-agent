import { useState } from "react";

import type { PortfolioAllocation } from "../../types/recommendation.types";
import { formatInr, formatPercent, holdingLabel } from "../../utils/displayFormatters";

/** CSS variable for the categorical slot at `index` (slots are defined in global.css). */
export function seriesColorVar(index: number): string {
  return `var(--series-${(index % 6) + 1})`;
}

interface AllocationStackedBarProps {
  allocations: PortfolioAllocation[];
  amountLabel: string;
}

/**
 * Part-to-whole as one 100% horizontal bar. Identity is carried by the legend
 * (name + %) underneath, never by color alone; AllocationTable is the table view.
 */
export function AllocationStackedBar({ allocations, amountLabel }: AllocationStackedBarProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const active = activeIndex !== null ? allocations[activeIndex] : null;

  return (
    <figure className="allocation-bar" aria-label="Allocation split">
      <div className="allocation-bar__track" onMouseLeave={() => setActiveIndex(null)}>
        {allocations.map((allocation, index) => (
          <div
            key={allocation.ticker}
            className={`allocation-bar__segment${activeIndex === index ? " allocation-bar__segment--active" : ""}`}
            style={{ flexGrow: allocation.weight_percent, background: seriesColorVar(index) }}
            tabIndex={0}
            role="img"
            aria-label={`${allocation.company_name}: ${formatPercent(allocation.weight_percent)}, ${formatInr(allocation.amount)}`}
            onMouseEnter={() => setActiveIndex(index)}
            onFocus={() => setActiveIndex(index)}
            onBlur={() => setActiveIndex(null)}
          />
        ))}
      </div>

      <div className="allocation-bar__tooltip" aria-hidden={!active}>
        {active ? (
          <>
            <strong>{active.company_name}</strong>
            <span>
              {formatPercent(active.weight_percent)} · {formatInr(active.amount)} {amountLabel}
            </span>
          </>
        ) : (
          <span className="muted">Hover or tab through the bar for details</span>
        )}
      </div>

      <figcaption>
        <ul className="allocation-bar__legend">
          {allocations.map((allocation, index) => (
            <li
              key={allocation.ticker}
              className="allocation-bar__legend-item"
              onMouseEnter={() => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
            >
              <span className="swatch" style={{ background: seriesColorVar(index) }} aria-hidden="true" />
              <span className="allocation-bar__legend-ticker">{holdingLabel(allocation)}</span>
              <span className="allocation-bar__legend-value">{formatPercent(allocation.weight_percent)}</span>
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}
