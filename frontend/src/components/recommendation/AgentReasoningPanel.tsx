import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

import type { PortfolioAllocation } from "../../types/recommendation.types";
import { formatPercent, holdingLabel } from "../../utils/displayFormatters";
import { AssetTypePill } from "./AssetTypePill";

interface AgentReasoningPanelProps {
  summary: string;
  allocations: PortfolioAllocation[];
  riskNotes: string[];
}

const BRIEF_SENTENCES = 3;
const BRIEF_RISKS = 3;

/**
 * The agent's reasoning, short by default: the summary's key sentences as bullets,
 * each pick's reason clamped to a few lines, and the top risks — "Read more" shows
 * everything. (PDF export always prints the full text.)
 */
export function AgentReasoningPanel({ summary, allocations, riskNotes }: AgentReasoningPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const sentences = splitSentences(summary);
  const hasMore =
    sentences.length > BRIEF_SENTENCES || riskNotes.length > BRIEF_RISKS || allocations.some((a) => a.rationale.length > 220);

  return (
    <section className={`card reasoning${expanded ? " reasoning--expanded" : " reasoning--collapsed"}`}>
      <h2 className="card__title">Why the agent chose this</h2>
      {summary && (
        <>
          <ul className="reasoning__brief">
            {sentences.slice(0, BRIEF_SENTENCES).map((sentence) => (
              <li key={sentence}>{sentence}</li>
            ))}
          </ul>
          <p className="reasoning__summary">{summary}</p>
        </>
      )}

      <ul className="reasoning__picks">
        {allocations.map((allocation) => (
          <li key={allocation.ticker} className="reasoning__pick">
            <div className="reasoning__pick-header">
              <strong>
                {holdingLabel(allocation)} <AssetTypePill assetType={allocation.asset_type} />
              </strong>
              <span className="muted">
                {allocation.asset_type === "mutual_fund" ? allocation.sector : allocation.company_name} ·{" "}
                {formatPercent(allocation.weight_percent)}
              </span>
            </div>
            <p className="reasoning__rationale">{allocation.rationale || "No rationale given."}</p>
          </li>
        ))}
      </ul>

      {riskNotes.length > 0 && (
        <div className="risk-notes">
          <h3 className="risk-notes__title">
            <span aria-hidden="true">⚠</span> Risks to keep in mind
          </h3>
          <ul>
            {riskNotes.map((note, i) => (
              <li key={note} className={i >= BRIEF_RISKS ? "reasoning__extra" : undefined}>
                {note}
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasMore && (
        <button
          type="button"
          className="button button--ghost button--small reasoning__toggle no-print"
          onClick={() => setExpanded((open) => !open)}
          aria-expanded={expanded}
        >
          {expanded ? (
            <>
              <ChevronUp size={14} /> Show less
            </>
          ) : (
            <>
              <ChevronDown size={14} /> Read the full reasoning
              {riskNotes.length > BRIEF_RISKS ? ` (+${riskNotes.length - BRIEF_RISKS} more risks)` : ""}
            </>
          )}
        </button>
      )}
    </section>
  );
}

/** Split prose into sentences without breaking on decimals ("15.5%") or "e.g.". */
function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.!?])\s+(?=[A-Z₹(“"])/)
    .map((s) => s.trim())
    .filter(Boolean);
}
