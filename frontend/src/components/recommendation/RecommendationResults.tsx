import { Calculator, Scale } from "lucide-react";
import { Link } from "react-router-dom";

import type { RecommendationResponse } from "../../types/recommendation.types";
import { formatDateTime, formatInr } from "../../utils/displayFormatters";
import { ASSET_MIX_LABELS, PROVIDER_LABELS, RISK_LEVEL_LABELS, periodWord } from "../../utils/investmentLabels";
import { DisclaimerBanner } from "../layout/DisclaimerBanner";
import { AgentReasoningPanel } from "./AgentReasoningPanel";
import { AllocationStackedBar } from "./AllocationStackedBar";
import { AllocationTable } from "./AllocationTable";
import { CandidatesConsideredTable } from "./CandidatesConsideredTable";

interface RecommendationResultsProps {
  recommendation: RecommendationResponse;
}

export function RecommendationResults({ recommendation: rec }: RecommendationResultsProps) {
  const isRecurring = rec.investment_mode === "recurring";
  const period = periodWord(rec.recurring_frequency);
  const amountLabel = isRecurring ? `per ${period}` : "now";

  return (
    <div className="results">
      <DisclaimerBanner text={rec.disclaimer} />

      <section className="card">
        <div className="results__header">
          <div>
            <p className="results__eyebrow">
              {isRecurring ? `Target allocation for ${formatInr(rec.amount)} every ${period}` : "One-time investment split"}
            </p>
            <h2 className="results__headline">
              {isRecurring ? "Re-apply these percentages to each contribution" : `${formatInr(rec.amount)} across ${describeHoldings(rec)}`}
            </h2>
          </div>
          <dl className="results__meta">
            <div>
              <dt>Invests in</dt>
              <dd>{ASSET_MIX_LABELS[rec.asset_mix ?? "stocks"]}</dd>
            </div>
            <div>
              <dt>Risk</dt>
              <dd>{RISK_LEVEL_LABELS[rec.risk_level]}</dd>
            </div>
            <div>
              <dt>Model</dt>
              <dd>
                {PROVIDER_LABELS[rec.provider_id]} · {rec.model_name}
              </dd>
            </div>
            <div>
              <dt>Generated</dt>
              <dd>{formatDateTime(rec.created_at)}</dd>
            </div>
          </dl>
        </div>

        <AllocationStackedBar allocations={rec.allocations} amountLabel={amountLabel} />
        <AllocationTable
          allocations={rec.allocations}
          investmentMode={rec.investment_mode}
          amountColumnLabel={isRecurring ? `This ${period}` : "Amount"}
        />
        <div className="results__actions">
          <Link to={`/planner?recommendation=${rec.id}`} className="button button--secondary button--small">
            <Calculator size={14} /> Plan a SIP with this
          </Link>
          <Link to={`/rebalance?recommendation=${rec.id}`} className="button button--secondary button--small">
            <Scale size={14} /> Rebalance to this
          </Link>
        </div>
        {isRecurring && (
          <p className="field__hint">
            Rupee amounts are for this {period}'s contribution only — keep the percentages as your target and click
            “Get recommendation” again whenever you want the agent to refresh them.
          </p>
        )}
      </section>

      <AgentReasoningPanel summary={rec.summary} allocations={rec.allocations} riskNotes={rec.risk_notes} />
      <CandidatesConsideredTable candidates={rec.candidates_considered} skippedTickers={rec.skipped_tickers} />
    </div>
  );
}

/** "6 stocks", "4 funds", or "3 stocks + 2 funds". */
function describeHoldings(rec: RecommendationResponse): string {
  const funds = rec.allocations.filter((a) => a.asset_type === "mutual_fund").length;
  const stocks = rec.allocations.length - funds;
  const parts = [];
  if (stocks) parts.push(`${stocks} stock${stocks > 1 ? "s" : ""}`);
  if (funds) parts.push(`${funds} fund${funds > 1 ? "s" : ""}`);
  return parts.join(" + ");
}
