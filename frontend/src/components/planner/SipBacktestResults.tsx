import type { SipBacktestResponse } from "../../types/planning.types";
import { formatInr, formatInrCompact, formatInrPrecise, formatUnits } from "../../utils/displayFormatters";
import { StatTile } from "../common/StatTile";
import { SipBacktestChart } from "./SipBacktestChart";

const MONTH_YEAR = new Intl.DateTimeFormat("en-IN", { month: "short", year: "numeric" });

/** "What would have happened": the exact outcome of a past SIP at real NAVs. */
export function SipBacktestResults({ result }: { result: SipBacktestResponse }) {
  const beatFd = result.final_value - result.fixed_deposit_value;
  const fundNames = result.funds.map((f) => f.short_name).join(" + ");
  const maxBar = Math.max(result.final_value, result.fixed_deposit_value, result.total_invested);

  return (
    <>
      <section className="card">
        <p className="backtest-headline">
          {formatInr(result.monthly_amount)} every month in <strong>{fundNames}</strong> from{" "}
          {MONTH_YEAR.format(new Date(result.start_date))} would be worth{" "}
          <strong className="backtest-headline__value">{formatInr(result.final_value)}</strong> today.
        </p>

        <div className="stat-tiles">
          <StatTile label="You'd have put in" value={formatInrCompact(result.total_invested)} hint={`${result.installments} monthly instalments`} />
          <StatTile label="Worth today" value={formatInrCompact(result.final_value)} hint={`as of ${MONTH_YEAR.format(new Date(result.end_date))}`} tone="emphasis" />
          <StatTile
            label="Gain"
            value={`${result.gain >= 0 ? "+" : ""}${formatInrCompact(result.gain)}`}
            hint={`${result.absolute_return_percent >= 0 ? "+" : ""}${result.absolute_return_percent}% overall`}
            tone={result.gain >= 0 ? "good" : "critical"}
          />
          <StatTile
            label="Annual return (XIRR)"
            value={result.xirr_percent !== null ? `${result.xirr_percent}%` : "—"}
            hint="per year, timing of each SIP included"
          />
        </div>

        <div className="compare-bars" aria-label="Comparison with a fixed deposit">
          {[
            { label: "This SIP", value: result.final_value, className: "compare-bars__fill--fund" },
            { label: `Fixed deposit @ ${result.fixed_deposit_rate_percent}%`, value: result.fixed_deposit_value, className: "compare-bars__fill--fd" },
            { label: "Money put in", value: result.total_invested, className: "compare-bars__fill--invested" },
          ].map((bar) => (
            <div key={bar.label} className="compare-bars__row">
              <span className="compare-bars__label">{bar.label}</span>
              <div className="compare-bars__track">
                <div className={`compare-bars__fill ${bar.className}`} style={{ width: `${(bar.value / maxBar) * 100}%` }} />
              </div>
              <span className="compare-bars__value">{formatInrCompact(bar.value)}</span>
            </div>
          ))}
          <p className="field__hint">
            {beatFd >= 0
              ? `${formatInr(beatFd)} more than the same SIP in a ${result.fixed_deposit_rate_percent}% FD.`
              : `${formatInr(-beatFd)} less than the same SIP in a ${result.fixed_deposit_rate_percent}% FD.`}{" "}
            Along the way the portfolio's biggest dip was {result.worst_drawdown_percent}%.
          </p>
        </div>

        <SipBacktestChart points={result.timeline} />
      </section>

      {result.funds.length > 1 && (
        <section className="card">
          <h2 className="card__title">By fund</h2>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Fund</th>
                  <th scope="col" className="num">Share</th>
                  <th scope="col" className="num">Put in</th>
                  <th scope="col" className="num">Units</th>
                  <th scope="col" className="num">Worth today</th>
                  <th scope="col" className="num">XIRR</th>
                </tr>
              </thead>
              <tbody>
                {result.funds.map((fund) => (
                  <tr key={fund.scheme_code}>
                    <td>
                      <div className="stock-cell__ticker">{fund.short_name}</div>
                      <div className="stock-cell__name">NAV {formatInrPrecise(fund.latest_nav)}</div>
                    </td>
                    <td className="num">{fund.weight_percent}%</td>
                    <td className="num">{formatInr(fund.invested)}</td>
                    <td className="num">{formatUnits(fund.units)}</td>
                    <td className="num">{formatInr(fund.value)}</td>
                    <td className="num">{fund.xirr_percent !== null ? `${fund.xirr_percent}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="card planner-assumptions">
        <h2 className="card__title">How this was calculated</h2>
        <ul>
          <li>
            Bought units on the 1st business day of each month from {MONTH_YEAR.format(new Date(result.start_date))}, at that
            day's actual NAV{result.annual_step_up_percent ? `, raising the SIP ${result.annual_step_up_percent}% every year` : ""}.
          </li>
          <li>Valued at the latest NAV ({result.end_date}). Direct-plan NAVs already include the fund's expenses.</li>
          <li>Before tax and exit loads. Past performance doesn't guarantee future returns.</li>
        </ul>
      </section>
    </>
  );
}
