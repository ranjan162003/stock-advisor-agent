import { ArrowDownRight, ArrowUpRight, Minus, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { recommendationApi } from "../../api/recommendationApi";
import type { RecommendationPerformance, RecommendationResponse } from "../../types/recommendation.types";
import {
  formatDateTime,
  formatInr,
  formatInrPrecise,
  formatSignedPercent,
  parseTimestamp,
} from "../../utils/displayFormatters";
import { CountUp } from "../common/CountUp";
import { Skeleton } from "../common/Skeleton";

/**
 * "Since this recommendation": each holding's price/NAV then vs now, weighted into
 * one number. Direction is shown with an arrow icon + sign, not colour alone.
 */
export function PerformanceSincePanel({ recommendation: rec }: { recommendation: RecommendationResponse }) {
  const [performance, setPerformance] = useState<RecommendationPerformance | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(() => {
    setIsLoading(true);
    setError(null);
    recommendationApi
      .getPerformance(rec.id)
      .then(setPerformance)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setIsLoading(false));
  }, [rec.id]);

  useEffect(load, [load]);

  const madeToday = parseTimestamp(rec.created_at).toDateString() === new Date().toDateString();
  const change = performance?.portfolio_change_percent ?? null;
  const largestMove = Math.max(1, ...(performance?.holdings.map((h) => Math.abs(h.change_percent ?? 0)) ?? [0]));
  const isRecurring = rec.investment_mode === "recurring";

  return (
    <section className="card performance">
      <div className="card__title-row">
        <h2 className="card__title">Since this recommendation</h2>
        <button
          type="button"
          className="icon-button icon-button--subtle no-print"
          onClick={load}
          disabled={isLoading}
          aria-label="Refresh prices"
          title="Refresh prices"
        >
          <RefreshCw size={15} className={isLoading ? "spin" : undefined} />
        </button>
      </div>

      {isLoading && !performance ? (
        <div className="performance__loading" role="status" aria-label="Checking today's prices">
          <Skeleton width="40%" height={30} />
          <Skeleton width="70%" height={12} />
          {rec.allocations.map((a) => (
            <Skeleton key={a.ticker} height={18} />
          ))}
        </div>
      ) : error ? (
        <p className="field__hint field__hint--warning">Couldn't check today's prices: {error}</p>
      ) : performance ? (
        <>
          <div className="performance__headline">
            <span className={`performance__change performance__change--${direction(change)}`}>
              <DirectionIcon value={change} size={22} />
              {change === null ? "—" : <CountUp value={change} format={(v) => formatSignedPercent(v)} />}
            </span>
            <span className="performance__summary">
              {change === null
                ? "Today's prices aren't available yet."
                : isRecurring
                  ? `on the recommended split since ${formatDateTime(rec.created_at)}`
                  : `${formatInr(performance.amount)} invested then would be about `}
              {!isRecurring && performance.value_now !== null && <strong>{formatInr(performance.value_now)}</strong>}
              {!isRecurring && change !== null && " now"}
            </span>
          </div>
          {madeToday && (
            <p className="field__hint">Made today — check back after the market has moved for a meaningful number.</p>
          )}

          <ul className="performance__rows">
            {performance.holdings.map((h) => (
              <li key={h.ticker} className="performance__row">
                <span className="performance__name">{h.display_name}</span>
                <span className="performance__prices">
                  {formatInrPrecise(h.price_then)} → {h.price_now === null ? "—" : formatInrPrecise(h.price_now)}
                </span>
                <span className="performance__bar" aria-hidden="true">
                  <span
                    className={`performance__bar-fill performance__bar-fill--${direction(h.change_percent)}`}
                    style={{ width: `${(Math.abs(h.change_percent ?? 0) / largestMove) * 50}%` }}
                  />
                </span>
                <span className={`performance__value performance__value--${direction(h.change_percent)}`}>
                  <DirectionIcon value={h.change_percent} size={14} />
                  {formatSignedPercent(h.change_percent)}
                </span>
              </li>
            ))}
          </ul>
          <p className="field__hint">
            Price change only — before brokerage, expense ratios and taxes, and not counting dividends. Checked{" "}
            {formatDateTime(performance.checked_at)}; market data refreshes every few hours.
          </p>
        </>
      ) : null}
    </section>
  );
}

function direction(value: number | null | undefined): "up" | "down" | "flat" {
  if (value === null || value === undefined || Math.abs(value) < 0.005) return "flat";
  return value > 0 ? "up" : "down";
}

function DirectionIcon({ value, size }: { value: number | null | undefined; size: number }) {
  const dir = direction(value);
  const Icon = dir === "up" ? ArrowUpRight : dir === "down" ? ArrowDownRight : Minus;
  return <Icon size={size} aria-hidden="true" />;
}
