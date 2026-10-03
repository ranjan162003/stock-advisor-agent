import { useMemo, useState } from "react";

import type { PortfolioAllocation } from "../../types/recommendation.types";
import { formatPercent, holdingLabel } from "../../utils/displayFormatters";
import { seriesColorVar } from "./AllocationStackedBar";

const SIZE = 220;
const CENTER = SIZE / 2;
const OUTER = { outer: 104, inner: 78 }; // holdings ring
const INNER = { outer: 72, inner: 52 }; // sectors ring

interface SectorGroup {
  name: string;
  weight: number;
  holdings: { allocation: PortfolioAllocation; index: number }[];
}

type Hover = { kind: "holding"; index: number } | { kind: "sector"; name: string } | null;

/**
 * Two-ring donut. Outer ring = each holding, in the same colour as the allocation
 * bar (colour follows the holding). Inner ring = the sector / fund category those
 * holdings belong to, in neutral tones so it never competes with holding colours.
 * The sector list beside it carries every label and value as text.
 */
export function AllocationDonut({ allocations }: { allocations: PortfolioAllocation[] }) {
  const [hover, setHover] = useState<Hover>(null);

  // Holdings ordered by sector so each sector's slices sit together over its inner arc.
  const sectors = useMemo<SectorGroup[]>(() => {
    const groups = new Map<string, SectorGroup>();
    allocations.forEach((allocation, index) => {
      const name = allocation.sector?.trim() || "Other";
      const group = groups.get(name) ?? { name, weight: 0, holdings: [] };
      group.weight += allocation.weight_percent;
      group.holdings.push({ allocation, index });
      groups.set(name, group);
    });
    return [...groups.values()].sort((a, b) => b.weight - a.weight);
  }, [allocations]);

  const total = allocations.reduce((sum, a) => sum + a.weight_percent, 0) || 100;
  const holdingArcs: { index: number; start: number; end: number; allocation: PortfolioAllocation }[] = [];
  const sectorArcs: { name: string; start: number; end: number }[] = [];
  let angle = 0;
  for (const sector of sectors) {
    const sectorStart = angle;
    for (const { allocation, index } of sector.holdings) {
      const sweep = (allocation.weight_percent / total) * 360;
      holdingArcs.push({ index, start: angle, end: angle + sweep, allocation });
      angle += sweep;
    }
    sectorArcs.push({ name: sector.name, start: sectorStart, end: angle });
  }

  const activeHolding = hover?.kind === "holding" ? allocations[hover.index] : null;
  const activeSector = hover?.kind === "sector" ? sectors.find((s) => s.name === hover.name) : null;
  const isDimmed = (holdingIndex: number, sectorName: string) => {
    if (!hover) return false;
    return hover.kind === "holding" ? hover.index !== holdingIndex : hover.name !== sectorName;
  };
  const sectorOf = (index: number) => sectors.find((s) => s.holdings.some((h) => h.index === index))?.name ?? "";

  return (
    <figure className="allocation-donut" aria-label="Allocation by holding and sector">
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="allocation-donut__chart"
        role="img"
        aria-label={sectors.map((s) => `${s.name} ${formatPercent(s.weight)}`).join(", ")}
        onMouseLeave={() => setHover(null)}
      >
        {holdingArcs.map((arc) => (
          <path
            key={arc.allocation.ticker}
            d={ringPath(arc.start, arc.end, OUTER.outer, OUTER.inner)}
            fill={seriesColorVar(arc.index)}
            className={`allocation-donut__arc${isDimmed(arc.index, sectorOf(arc.index)) ? " allocation-donut__arc--dim" : ""}`}
            onMouseEnter={() => setHover({ kind: "holding", index: arc.index })}
          />
        ))}
        {sectorArcs.map((arc, i) => (
          <path
            key={arc.name}
            d={ringPath(arc.start, arc.end, INNER.outer, INNER.inner)}
            className={`allocation-donut__sector allocation-donut__sector--${i % 2 ? "b" : "a"}${
              hover && !(hover.kind === "sector" ? hover.name === arc.name : sectorOf(hover.index) === arc.name)
                ? " allocation-donut__arc--dim"
                : ""
            }`}
            onMouseEnter={() => setHover({ kind: "sector", name: arc.name })}
          />
        ))}
        <text x={CENTER} y={CENTER - 4} className="allocation-donut__center-value">
          {activeHolding
            ? formatPercent(activeHolding.weight_percent)
            : activeSector
              ? formatPercent(activeSector.weight)
              : allocations.length}
        </text>
        <text x={CENTER} y={CENTER + 14} className="allocation-donut__center-label">
          {activeHolding
            ? truncate(holdingLabel(activeHolding), 16)
            : activeSector
              ? truncate(activeSector.name, 16)
              : `holdings · ${sectors.length} ${sectors.length === 1 ? "group" : "groups"}`}
        </text>
      </svg>

      <figcaption className="allocation-donut__sectors">
        <span className="allocation-donut__caption">By {allocations.some((a) => a.asset_type === "mutual_fund") ? "sector / category" : "sector"}</span>
        <ul>
          {sectors.map((sector) => (
            <li
              key={sector.name}
              className={activeSector?.name === sector.name ? "allocation-donut__row--active" : undefined}
              onMouseEnter={() => setHover({ kind: "sector", name: sector.name })}
              onMouseLeave={() => setHover(null)}
            >
              <div className="allocation-donut__row-head">
                <span className="allocation-donut__sector-name">{sector.name}</span>
                <span className="allocation-donut__sector-value">{formatPercent(sector.weight)}</span>
              </div>
              <div className="allocation-donut__meter" aria-hidden="true">
                <span style={{ width: `${(sector.weight / total) * 100}%` }} />
              </div>
              <span className="allocation-donut__members">
                {sector.holdings.map(({ allocation, index }) => (
                  <span key={allocation.ticker}>
                    <span className="swatch" style={{ background: seriesColorVar(index) }} aria-hidden="true" />
                    {holdingLabel(allocation)}
                  </span>
                ))}
              </span>
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}

/** SVG path for a ring slice from `start`° to `end`° (0° = 12 o'clock, clockwise). */
function ringPath(start: number, end: number, outerRadius: number, innerRadius: number): string {
  const sweep = Math.min(end - start, 359.99);
  const large = sweep > 180 ? 1 : 0;
  const point = (deg: number, r: number) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return `${(CENTER + r * Math.cos(rad)).toFixed(2)},${(CENTER + r * Math.sin(rad)).toFixed(2)}`;
  };
  const stop = start + sweep;
  return [
    `M${point(start, outerRadius)}`,
    `A${outerRadius},${outerRadius} 0 ${large} 1 ${point(stop, outerRadius)}`,
    `L${point(stop, innerRadius)}`,
    `A${innerRadius},${innerRadius} 0 ${large} 0 ${point(start, innerRadius)}`,
    "Z",
  ].join(" ");
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}
