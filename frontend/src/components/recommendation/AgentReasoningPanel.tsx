import type { StockAllocation } from "../../types/recommendation.types";
import { formatPercent, shortTicker } from "../../utils/displayFormatters";

interface AgentReasoningPanelProps {
  summary: string;
  allocations: StockAllocation[];
  riskNotes: string[];
}

export function AgentReasoningPanel({ summary, allocations, riskNotes }: AgentReasoningPanelProps) {
  return (
    <section className="card">
      <h2 className="card__title">Why the agent chose this</h2>
      {summary && <p className="reasoning__summary">{summary}</p>}

      <ul className="reasoning__picks">
        {allocations.map((allocation) => (
          <li key={allocation.ticker} className="reasoning__pick">
            <div className="reasoning__pick-header">
              <strong>{shortTicker(allocation.ticker)}</strong>
              <span className="muted">
                {allocation.company_name} · {formatPercent(allocation.weight_percent)}
              </span>
            </div>
            <p>{allocation.rationale || "No rationale given."}</p>
          </li>
        ))}
      </ul>

      {riskNotes.length > 0 && (
        <div className="risk-notes">
          <h3 className="risk-notes__title">
            <span aria-hidden="true">⚠</span> Risks to keep in mind
          </h3>
          <ul>
            {riskNotes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
