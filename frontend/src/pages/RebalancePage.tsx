import { Scale } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";

import { planningApi } from "../api/planningApi";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { RecommendationPicker } from "../components/common/RecommendationPicker";
import { PageHeader } from "../components/layout/PageHeader";
import { HoldingsEditor, newHoldingRow, type HoldingRow } from "../components/rebalance/HoldingsEditor";
import { RebalanceResults } from "../components/rebalance/RebalanceResults";
import type { RebalanceResponse } from "../types/planning.types";

export function RebalancePage() {
  const [searchParams] = useSearchParams();
  const [recommendationId, setRecommendationId] = useState<number | null>(
    Number(searchParams.get("recommendation")) || null,
  );
  const [rows, setRows] = useState<HoldingRow[]>([newHoldingRow()]);
  const [cashText, setCashText] = useState("0");
  const [allowSelling, setAllowSelling] = useState(false);
  const [result, setResult] = useState<RebalanceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const holdings = rows
    .filter((row) => row.symbol.trim() && Number(row.quantityText) > 0)
    .map((row) => ({ symbol: row.symbol.trim(), quantity: Number(row.quantityText) }));
  const cash = Number(cashText) || 0;
  const canSubmit = recommendationId !== null && (holdings.length > 0 || cash > 0) && !isLoading;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!canSubmit || recommendationId === null) return;
    setIsLoading(true);
    setError(null);
    try {
      setResult(
        await planningApi.rebalance({
          recommendation_id: recommendationId,
          holdings,
          additional_cash: cash,
          allow_selling: allowSelling,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="page">
      <PageHeader
        eyebrow="Plan"
        title="Rebalance my portfolio"
        description="Compare what you own with a recommended target and get the exact buy / sell list — whole shares for stocks, units for funds."
      />

      <div className="planner-layout planner-layout--wide-form">
        <form className="card planner-form" onSubmit={handleSubmit}>
          <h2 className="card__title">Your portfolio</h2>

          <RecommendationPicker id="rebalance-target" label="Target allocation" value={recommendationId} onChange={setRecommendationId} />

          <HoldingsEditor rows={rows} onChange={setRows} />

          <div className="field">
            <label className="field__label" htmlFor="rebalance-cash">
              New cash to invest (₹)
            </label>
            <input
              id="rebalance-cash"
              className="input"
              type="number"
              min={0}
              step="any"
              value={cashText}
              onChange={(e) => setCashText(e.target.value)}
            />
          </div>

          <fieldset className="field">
            <legend className="field__label">How to get there</legend>
            <div className="segmented">
              <button
                type="button"
                className={`segmented__option${!allowSelling ? " segmented__option--selected" : ""}`}
                aria-pressed={!allowSelling}
                onClick={() => setAllowSelling(false)}
              >
                <span className="segmented__label">Don't sell anything</span>
                <span className="segmented__hint">Only invest new cash where you're underweight — no tax</span>
              </button>
              <button
                type="button"
                className={`segmented__option${allowSelling ? " segmented__option--selected" : ""}`}
                aria-pressed={allowSelling}
                onClick={() => setAllowSelling(true)}
              >
                <span className="segmented__label">Full rebalance</span>
                <span className="segmented__hint">Sell overweight holdings to hit the target exactly</span>
              </button>
            </div>
          </fieldset>

          <button type="submit" className="button button--primary button--large button--block" disabled={!canSubmit}>
            <Scale size={18} /> {isLoading ? "Pricing your holdings…" : "Build trade plan"}
          </button>
          {!canSubmit && !isLoading && (
            <p className="field__hint">Add at least one holding or some new cash.</p>
          )}
        </form>

        <div className="planner-results">
          {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
          {isLoading && <LoadingSpinner label="Fetching today's prices and NAVs…" />}
          {!result && !isLoading && (
            <section className="card empty-state planner-empty">
              <Scale size={28} />
              <p>
                Pick a target, enter what you own (or import it), then click <strong>Build trade plan</strong>.
              </p>
            </section>
          )}
          {result && !isLoading && <RebalanceResults result={result} />}
        </div>
      </div>
    </div>
  );
}
