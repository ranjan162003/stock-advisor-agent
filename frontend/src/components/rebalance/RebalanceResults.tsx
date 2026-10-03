import type { RebalanceLine, RebalanceResponse } from "../../types/planning.types";
import { formatInr, formatInrPrecise, formatPercent, formatUnits } from "../../utils/displayFormatters";
import { StatTile } from "../common/StatTile";
import { AssetTypePill } from "../recommendation/AssetTypePill";

interface RebalanceResultsProps {
  result: RebalanceResponse;
}

export function RebalanceResults({ result }: RebalanceResultsProps) {
  const unpriced = Object.entries(result.unpriced_holdings);
  const trades = result.lines.filter((line) => line.action !== "hold").length;

  return (
    <>
      <section className="card">
        <div className="stat-tiles">
          <StatTile label="Portfolio now" value={formatInr(result.current_value)} />
          <StatTile label="New cash" value={formatInr(result.additional_cash)} />
          <StatTile label="Buy" value={formatInr(result.total_buy)} tone="good" />
          <StatTile label="Sell" value={formatInr(result.total_sell)} tone={result.total_sell ? "critical" : undefined} />
          <StatTile label="Left in cash" value={formatInr(result.cash_left_over)} />
        </div>

        <div className="drift">
          <div className="drift__labels">
            <span>Off-target before</span>
            <strong>{formatPercent(result.drift_before_percent)}</strong>
            <span aria-hidden="true">→</span>
            <span>after</span>
            <strong className="drift__after">{formatPercent(result.drift_after_percent)}</strong>
          </div>
          <div className="drift__bar" aria-hidden="true">
            <div className="drift__before" style={{ width: `${Math.min(100, result.drift_before_percent)}%` }} />
            <div className="drift__now" style={{ width: `${Math.min(100, result.drift_after_percent)}%` }} />
          </div>
          <p className="field__hint">
            “Off-target” is the share of your money sitting in the wrong place compared with the target.{" "}
            {result.allow_selling ? "" : "You chose not to sell, so only new cash moves you closer."}
          </p>
        </div>
      </section>

      <section className="card">
        <h2 className="card__title">
          {trades === 0 ? "Nothing to trade — you're already close to target" : `${trades} trade${trades > 1 ? "s" : ""} to make`}
        </h2>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Holding</th>
                <th scope="col">Action</th>
                <th scope="col" className="num">Quantity</th>
                <th scope="col" className="num">Amount</th>
                <th scope="col" className="num">Price / NAV</th>
                <th scope="col" className="num">Weight now → after</th>
                <th scope="col" className="num">Target</th>
              </tr>
            </thead>
            <tbody>
              {result.lines.map((line) => (
                <tr key={line.ticker}>
                  <td>
                    <div className="stock-cell__ticker">
                      {line.display_name}
                      <AssetTypePill assetType={line.asset_type} />
                    </div>
                    <div className="stock-cell__name">
                      Own {formatQuantity(line, line.current_quantity)} · {formatInr(line.current_value)}
                    </div>
                    {line.note && <div className="stock-cell__name text-warning">{line.note}</div>}
                  </td>
                  <td>
                    <span className={`action-badge action-badge--${line.action}`}>{line.action}</span>
                  </td>
                  <td className="num">{line.action === "hold" ? "—" : formatQuantity(line, line.trade_quantity)}</td>
                  <td className="num">{line.action === "hold" ? "—" : formatInr(line.trade_value)}</td>
                  <td className="num">{formatInrPrecise(line.price)}</td>
                  <td className="num">
                    {formatPercent(line.current_weight_percent)} → <strong>{formatPercent(line.after_weight_percent)}</strong>
                  </td>
                  <td className="num">{formatPercent(line.target_weight_percent)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {unpriced.length > 0 && (
          <div className="skipped-tickers">
            <strong>Couldn't price (left out):</strong>
            <ul>
              {unpriced.map(([ticker, reason]) => (
                <li key={ticker}>
                  <code>{ticker}</code> — {reason}
                </li>
              ))}
            </ul>
          </div>
        )}
        <p className="field__hint">
          Uses the latest close / NAV, so live prices will differ slightly. Selling can trigger capital-gains tax and exit
          loads — check before you trade.
        </p>
      </section>
    </>
  );
}

function formatQuantity(line: RebalanceLine, quantity: number): string {
  if (line.asset_type === "mutual_fund") return `${formatUnits(quantity)} units`;
  return `${quantity} share${quantity === 1 ? "" : "s"}`;
}
