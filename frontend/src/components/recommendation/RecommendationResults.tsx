import { FileDown, Sparkles } from "lucide-react";

import { useAssistant } from "../../context/AssistantContext";
import { usePrint } from "../../context/PrintContext";
import type { RecommendationResponse } from "../../types/recommendation.types";
import { formatDateTime, formatInr, parseTimestamp } from "../../utils/displayFormatters";
import { ASSET_MIX_LABELS, PROVIDER_LABELS, RISK_LEVEL_LABELS, periodWord } from "../../utils/investmentLabels";
import { PrintableDocument } from "../common/PrintableDocument";
import { DisclaimerBanner } from "../layout/DisclaimerBanner";
import { AgentReasoningPanel } from "./AgentReasoningPanel";
import { AllocationDonut } from "./AllocationDonut";
import { AllocationStackedBar } from "./AllocationStackedBar";
import { AllocationTable } from "./AllocationTable";
import { CandidatesConsideredTable } from "./CandidatesConsideredTable";
import { PerformanceSincePanel } from "./PerformanceSincePanel";

interface RecommendationResultsProps {
  recommendation: RecommendationResponse;
  /** History shows how the split has done since; a brand-new result has nothing to show yet. */
  showPerformance?: boolean;
}

export function RecommendationResults({ recommendation: rec, showPerformance = false }: RecommendationResultsProps) {
  const isRecurring = rec.investment_mode === "recurring";
  const period = periodWord(rec.recurring_frequency);
  const amountLabel = isRecurring ? `per ${period}` : "now";
  const { openPanel } = useAssistant();
  const print = usePrint();

  const downloadPdf = () =>
    print({
      fileName: `stock-advisor-recommendation-${rec.id}-${parseTimestamp(rec.created_at).toLocaleDateString("en-CA")}`,
      content: (
        <PrintableDocument
          title={`Recommendation #${rec.id}`}
          subtitle={`${formatInr(rec.amount)} ${isRecurring ? `every ${period}` : "one-time"} · ${ASSET_MIX_LABELS[rec.asset_mix ?? "stocks"]} · ${RISK_LEVEL_LABELS[rec.risk_level]} risk · ${formatDateTime(rec.created_at)}`}
        >
          <RecommendationResults recommendation={rec} />
        </PrintableDocument>
      ),
    });

  return (
    <div className="results">
      <DisclaimerBanner text={rec.disclaimer} />
      <div className="results__toolbar no-print">
        <button type="button" className="button button--secondary button--small" onClick={downloadPdf}>
          <FileDown size={14} /> Download PDF
        </button>
      </div>

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
        <AllocationDonut allocations={rec.allocations} />
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

      {showPerformance && <PerformanceSincePanel recommendation={rec} />}

      <div className="ask-about no-print">
        <span className="ask-about__text">
          <Sparkles size={16} /> Questions about this result?
        </span>
        {ASK_ABOUT_QUESTIONS.map((question) => (
          <button key={question} type="button" className="chat-suggestion" onClick={() => openPanel(question)}>
            {question}
          </button>
        ))}
      </div>

      <AgentReasoningPanel summary={rec.summary} allocations={rec.allocations} riskNotes={rec.risk_notes} />
      <CandidatesConsideredTable candidates={rec.candidates_considered} skippedTickers={rec.skipped_tickers} />
    </div>
  );
}

const ASK_ABOUT_QUESTIONS = [
  "Explain this recommendation in simple words",
  "What are the biggest risks here?",
  "Why these picks over the others?",
];

/** "6 stocks", "4 funds", or "3 stocks + 2 funds". */
function describeHoldings(rec: RecommendationResponse): string {
  const funds = rec.allocations.filter((a) => a.asset_type === "mutual_fund").length;
  const stocks = rec.allocations.length - funds;
  const parts = [];
  if (stocks) parts.push(`${stocks} stock${stocks > 1 ? "s" : ""}`);
  if (funds) parts.push(`${funds} fund${funds > 1 ? "s" : ""}`);
  return parts.join(" + ");
}
