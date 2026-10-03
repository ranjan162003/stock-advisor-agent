import { Fragment, useState } from "react";

import type { CandidateSummary } from "../../types/recommendation.types";
import { formatInrPrecise, formatPercent, formatSignedPercent, holdingLabel } from "../../utils/displayFormatters";
import { AssetTypePill } from "./AssetTypePill";

interface CandidatesConsideredTableProps {
  candidates: CandidateSummary[];
  skippedTickers: Record<string, string>;
}

/** Every shortlisted stock/fund the agent saw, its rule-based pre-score, and (for stocks) its headlines. */
export function CandidatesConsideredTable({ candidates, skippedTickers }: CandidatesConsideredTableProps) {
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);
  const skipped = Object.entries(skippedTickers);
  const hasFunds = candidates.some((c) => c.asset_type === "mutual_fund");
  const hasStocks = candidates.some((c) => c.asset_type !== "mutual_fund");
  const noun = hasFunds && hasStocks ? "Holdings" : hasFunds ? "Funds" : "Stocks";

  return (
    <section className="card">
      <details>
        <summary className="card__title card__title--summary">
          {noun} the agent considered ({candidates.length})
        </summary>
        <p className="muted">
          Pre-score is a transparent rule-based 0–100 blend — for stocks: momentum, quality, valuation and risk fit;
          for funds: long-run returns, risk-adjusted return, downside and risk fit. It shortlists candidates; the AI
          makes the final choice.
        </p>
        <div className="table-scroll">
          <table className="data-table data-table--compact">
            <thead>
              <tr>
                <th scope="col">{noun.replace(/s$/, "")}</th>
                <th scope="col" className="num">{hasFunds ? (hasStocks ? "Price / NAV" : "NAV") : "Price"}</th>
                <th scope="col" className="num">1Y return</th>
                {hasFunds && <th scope="col" className="num">3Y CAGR</th>}
                <th scope="col" className="num">Volatility</th>
                {hasStocks && <th scope="col" className="num">P/E</th>}
                <th scope="col" className="num">Pre-score</th>
                {hasStocks && <th scope="col">News</th>}
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <Fragment key={candidate.ticker}>
                  <tr className={candidate.was_picked ? "data-table__row--picked" : undefined}>
                    <td>
                      <div className="stock-cell__ticker">
                        {holdingLabel(candidate)}
                        <AssetTypePill assetType={candidate.asset_type} />
                        {candidate.was_picked && <span className="pill">Picked</span>}
                      </div>
                      <div className="stock-cell__name">
                        {candidate.asset_type === "mutual_fund" ? candidate.sector : candidate.company_name}
                      </div>
                    </td>
                    <td className="num">{formatInrPrecise(candidate.last_price)}</td>
                    <td className="num">{formatSignedPercent(candidate.return_1y_percent)}</td>
                    {hasFunds && <td className="num">{formatSignedPercent(candidate.cagr_3y_percent)}</td>}
                    <td className="num">{formatPercent(candidate.annualized_volatility_percent)}</td>
                    {hasStocks && <td className="num">{candidate.trailing_pe?.toFixed(1) ?? "—"}</td>}
                    <td className="num" title={describeScore(candidate)}>
                      {candidate.score.total_score.toFixed(0)}
                    </td>
                    {hasStocks && (
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
                    )}
                  </tr>
                  {expandedTicker === candidate.ticker && (
                    <tr className="data-table__detail-row">
                      <td colSpan={9}>
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
  if ("momentum_score" in score) {
    return (
      `Momentum ${score.momentum_score.toFixed(0)} · Quality ${score.quality_score.toFixed(0)} · ` +
      `Valuation ${score.valuation_score.toFixed(0)} · Risk fit ${score.risk_fit_score.toFixed(0)}`
    );
  }
  return (
    `Returns ${score.returns_score.toFixed(0)} · Risk-adjusted ${score.risk_adjusted_score.toFixed(0)} · ` +
    `Downside ${score.downside_score.toFixed(0)} · Risk fit ${score.risk_fit_score.toFixed(0)}`
  );
}
