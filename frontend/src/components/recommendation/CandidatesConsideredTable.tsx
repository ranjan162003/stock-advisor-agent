import { Fragment, useState } from "react";

import type { CandidateSummary } from "../../types/recommendation.types";
import { formatInrPrecise, formatPercent, formatSignedPercent, shortTicker } from "../../utils/displayFormatters";

interface CandidatesConsideredTableProps {
  candidates: CandidateSummary[];
  skippedTickers: Record<string, string>;
}

/** Every shortlisted stock the agent saw, its rule-based pre-score, and its headlines. */
export function CandidatesConsideredTable({ candidates, skippedTickers }: CandidatesConsideredTableProps) {
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);
  const skipped = Object.entries(skippedTickers);

  return (
    <section className="card">
      <details>
        <summary className="card__title card__title--summary">
          Stocks the agent considered ({candidates.length})
        </summary>
        <p className="muted">
          Pre-score is a transparent rule-based 0–100 blend of momentum, quality, valuation and fit with your risk
          level. It shortlists candidates; the AI makes the final choice.
        </p>
        <div className="table-scroll">
          <table className="data-table data-table--compact">
            <thead>
              <tr>
                <th scope="col">Stock</th>
                <th scope="col" className="num">Price</th>
                <th scope="col" className="num">1Y return</th>
                <th scope="col" className="num">Volatility</th>
                <th scope="col" className="num">P/E</th>
                <th scope="col" className="num">Pre-score</th>
                <th scope="col">News</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <Fragment key={candidate.ticker}>
                  <tr className={candidate.was_picked ? "data-table__row--picked" : undefined}>
                    <td>
                      <div className="stock-cell__ticker">
                        {shortTicker(candidate.ticker)}
                        {candidate.was_picked && <span className="pill">Picked</span>}
                      </div>
                      <div className="stock-cell__name">{candidate.company_name}</div>
                    </td>
                    <td className="num">{formatInrPrecise(candidate.last_price)}</td>
                    <td className="num">{formatSignedPercent(candidate.return_1y_percent)}</td>
                    <td className="num">{formatPercent(candidate.annualized_volatility_percent)}</td>
                    <td className="num">{candidate.trailing_pe?.toFixed(1) ?? "—"}</td>
                    <td className="num" title={describeScore(candidate)}>
                      {candidate.score.total_score.toFixed(0)}
                    </td>
                    <td>
                      {candidate.headlines.length > 0 ? (
                        <button
                          type="button"
                          className="link-button"
                          aria-expanded={expandedTicker === candidate.ticker}
                          onClick={() =>
                            setExpandedTicker(expandedTicker === candidate.ticker ? null : candidate.ticker)
                          }
                        >
                          {candidate.headlines.length} headline{candidate.headlines.length > 1 ? "s" : ""}
                        </button>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                  {expandedTicker === candidate.ticker && (
                    <tr className="data-table__detail-row">
                      <td colSpan={7}>
                        <ul className="headline-list">
                          {candidate.headlines.map((headline) => (
                            <li key={headline.title}>
                              {headline.url ? (
                                <a href={headline.url} target="_blank" rel="noreferrer">
                                  {headline.title}
                                </a>
                              ) : (
                                headline.title
                              )}
                              {headline.publisher && <span className="muted"> — {headline.publisher}</span>}
                            </li>
                          ))}
                        </ul>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
        {skipped.length > 0 && (
          <div className="skipped-tickers">
            <strong>Skipped:</strong>
            <ul>
              {skipped.map(([ticker, reason]) => (
                <li key={ticker}>
                  <code>{ticker}</code> — {reason}
                </li>
              ))}
            </ul>
          </div>
        )}
      </details>
    </section>
  );
}

function describeScore({ score }: CandidateSummary): string {
  return (
    `Momentum ${score.momentum_score.toFixed(0)} · Quality ${score.quality_score.toFixed(0)} · ` +
    `Valuation ${score.valuation_score.toFixed(0)} · Risk fit ${score.risk_fit_score.toFixed(0)}`
  );
}
