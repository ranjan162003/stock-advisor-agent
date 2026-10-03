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

export function formatDateTime(isoString: string): string {
  return dateTimeFormatter.format(new Date(isoString));
}

/** "TCS.NS" -> "TCS" for compact labels. */
export function shortTicker(ticker: string): string {
  return ticker.replace(/\.(NS|BO)$/, "");
}
