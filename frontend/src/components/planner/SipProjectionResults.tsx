import type { SipProjectionResponse } from "../../types/planning.types";
import { formatInr, formatInrCompact } from "../../utils/displayFormatters";
import { StatTile } from "../common/StatTile";
import { SipProjectionChart } from "./SipProjectionChart";

/** Forward-looking SIP projection: bad / typical / good range, goal odds and the fan chart. */
export function SipProjectionResults({ result }: { result: SipProjectionResponse }) {
  const multiple = result.typical / result.total_invested;
  return (
    <>
      <section className="card">
        <div className="stat-tiles">
          <StatTile label="You invest" value={formatInr(result.total_invested)} hint={`over ${result.years} years`} />
          <StatTile label="Bad case" value={formatInrCompact(result.bad_case)} hint="1 in 10 paths do worse" />
          <StatTile label="Typical" value={formatInrCompact(result.typical)} hint={`${multiple.toFixed(1)}× your money`} tone="emphasis" />
          <StatTile label="Good case" value={formatInrCompact(result.good_case)} hint="1 in 10 paths do better" />
        </div>

        {result.goal_amount ? (
          <div className="goal-box">
            <div className="goal-box__meter" aria-hidden="true">
              <div className="goal-box__fill" style={{ width: `${result.goal_probability_percent ?? 0}%` }} />
            </div>
            <p>
              <strong>{result.goal_probability_percent}% chance</strong> of reaching your{" "}
              {formatInrCompact(result.goal_amount)} goal.
              {result.required_monthly_for_goal_80 ? (
                <>
                  {" "}
                  For an 80% chance, invest about <strong>{formatInr(result.required_monthly_for_goal_80)}/month</strong>
                  {result.required_monthly_for_goal_50
                    ? ` (≈${formatInr(result.required_monthly_for_goal_50)}/month for a 50% chance)`
                    : ""}
                  .
                </>
              ) : null}
            </p>
          </div>
        ) : null}

        <SipProjectionChart points={result.yearly} goalAmount={result.goal_amount} />
      </section>

      <section className="card planner-assumptions">
        <h2 className="card__title">How this was calculated</h2>
        <p>{result.source_description}.</p>
        <ul>
          <li>
            Basis: about <strong>{result.basis_annual_return_percent}%</strong> a year with{" "}
            {result.basis_annual_volatility_percent}% volatility
            {result.history_months ? ` over the last ${result.history_months} months` : ""}.
          </li>
          <li>
            {result.simulated_paths.toLocaleString("en-IN")} simulated paths; {result.chance_of_loss_percent}% of them end
            below the amount invested.
          </li>
          {Object.entries(result.excluded_holdings).map(([ticker, reason]) => (
            <li key={ticker}>
              Left out <code>{ticker}</code>: {reason}
            </li>
          ))}
        </ul>
        <p className="field__hint">
          Past returns don't guarantee future ones — a strong recent decade makes replayed projections optimistic.
          Figures are before tax and in today's rupees (not adjusted for inflation).
        </p>
      </section>
    </>
  );
}
