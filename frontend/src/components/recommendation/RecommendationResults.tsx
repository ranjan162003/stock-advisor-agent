import type { RecommendationResponse } from "../../types/recommendation.types";
import { formatDateTime, formatInr } from "../../utils/displayFormatters";
import { PROVIDER_LABELS, RISK_LEVEL_LABELS, periodWord } from "../../utils/investmentLabels";
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
              {isRecurring ? "Re-apply these percentages to each contribution" : `${formatInr(rec.amount)} across ${rec.allocations.length} stocks`}
            </h2>
          </div>
          <dl className="results__meta">
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
