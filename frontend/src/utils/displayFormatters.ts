const inrFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const inrPreciseFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});

// No `timeZone` option: dates and times show in the computer's own time zone.
const dateTimeFormatter = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" });

/** ₹50,000 -- Indian digit grouping (₹1,20,000). */
export function formatInr(amount: number): string {
  return inrFormatter.format(amount);
}

/** ₹2,075.40 -- for share prices. */
export function formatInrPrecise(amount: number): string {
  return inrPreciseFormatter.format(amount);
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  return value === null || value === undefined ? "—" : `${value.toFixed(digits)}%`;
}

export function formatSignedPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

/** "3 Oct 2026, 5:07 pm" in the viewer's local time. */
export function formatDateTime(isoString: string): string {
  return dateTimeFormatter.format(parseTimestamp(isoString));
}

/**
 * A backend timestamp. The API sends UTC ("…Z" / "+00:00"); a value with no zone is
 * also UTC (older saved rows), so it must not be read as local time.
 */
export function parseTimestamp(isoString: string): Date {
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/i.test(isoString);
  return new Date(hasZone ? isoString : `${isoString}Z`);
}

/** A calendar date like "2026-10-01" (NAV dates) as that local day — `new Date()` would read it as UTC midnight. */
export function parseCalendarDate(isoDate: string): Date {
  const [year, month, day] = isoDate.slice(0, 10).split("-").map(Number);
  return new Date(year, month - 1, day);
}

/** "TCS.NS" -> "TCS" for compact labels. */
export function shortTicker(ticker: string): string {
  return ticker.replace(/\.(NS|BO)$/, "");
}

/** Label for any holding: the ticker for stocks, the short scheme name for funds. */
export function holdingLabel(item: { ticker: string; display_name?: string | null }): string {
  return item.display_name || shortTicker(item.ticker);
}

export function formatUnits(units: number): string {
  return units.toLocaleString("en-IN", { maximumFractionDigits: 3 });
}

/** Indian short form for chart axes and tiles: ₹8.4K, ₹12.5L, ₹1.2Cr. */
export function formatInrCompact(amount: number): string {
  const abs = Math.abs(amount);
  const trim = (n: number) => n.toFixed(n >= 100 ? 0 : 1).replace(/\.0$/, "");
  if (abs >= 1e7) return `₹${trim(amount / 1e7)}Cr`;
  if (abs >= 1e5) return `₹${trim(amount / 1e5)}L`;
  if (abs >= 1e3) return `₹${trim(amount / 1e3)}K`;
  return `₹${Math.round(amount)}`;
}
