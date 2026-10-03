import { Calculator, History as HistoryIcon, Target, TrendingUp } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { planningApi } from "../api/planningApi";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { PageHeader } from "../components/layout/PageHeader";
import { FundPicker, fundSplitIsValid, toFundWeights, type PickedFund } from "../components/planner/FundPicker";
import { SipBacktestResults } from "../components/planner/SipBacktestResults";
import { SipProjectionResults } from "../components/planner/SipProjectionResults";
import { useAssistantPageContext } from "../context/AssistantContext";
import type {
  ReturnPreset,
  ReturnPresetInfo,
  ReturnSource,
  SipBacktestResponse,
  SipProjectionResponse,
} from "../types/planning.types";
import { formatInr, formatInrCompact } from "../utils/displayFormatters";

type PlannerMode = "future" | "past";

const EXAMPLE_FUND = { schemeCode: 122639, name: "Parag Parikh Flexi Cap" };

const SOURCE_OPTIONS: { value: ReturnSource; label: string; hint: string }[] = [
  { value: "funds", label: "My funds", hint: "Uses their real NAV history" },
  { value: "preset", label: "A fund type", hint: "Typical long-run returns" },
];

export function SipPlannerPage() {
  useAssistantPageContext("planner");
  const [mode, setMode] = useState<PlannerMode>("future");
  const [monthlyText, setMonthlyText] = useState("10000");
  const [years, setYears] = useState(10);
  const [stepUp, setStepUp] = useState(0);
  const [goalText, setGoalText] = useState("");
  const [source, setSource] = useState<ReturnSource>("funds");
  const [funds, setFunds] = useState<PickedFund[]>([]);
  const [preset, setPreset] = useState<ReturnPreset>("flexi_cap");
  const [presets, setPresets] = useState<ReturnPresetInfo[]>([]);
  const [projection, setProjection] = useState<SipProjectionResponse | null>(null);
  const [backtest, setBacktest] = useState<SipBacktestResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const [runWhenReady, setRunWhenReady] = useState(false);

  useEffect(() => {
    planningApi.getReturnPresets().then(setPresets).catch(() => setPresets([]));
  }, []);

  const isPast = mode === "past";
  const usesFunds = isPast || source === "funds";
  const monthly = Number(monthlyText);
  const goal = Number(goalText);
  const maxYears = isPast ? 30 : 40;
  const blocker =
    !(monthly > 0)
      ? "Enter a monthly amount."
      : usesFunds && funds.length === 0
        ? "Pick at least one fund."
        : usesFunds && !fundSplitIsValid(funds)
          ? "Make the fund split add up to 100%."
          : null;

  // "Try an example" fills the form, then submits once the new values are in place.
  useEffect(() => {
    if (!runWhenReady || blocker) return;
    setRunWhenReady(false);
    formRef.current?.requestSubmit();
  }, [runWhenReady, blocker]);

  const tryExample = () => {
    setMonthlyText(isPast ? "5000" : "10000");
    setYears(isPast ? 7 : 10);
    setStepUp(0);
    setSource("funds");
    setFunds([{ schemeCode: EXAMPLE_FUND.schemeCode, name: EXAMPLE_FUND.name, weightText: "100" }]);
    setRunWhenReady(true);
  };

  const switchMode = (next: PlannerMode) => {
    setMode(next);
    setError(null);
    if (next === "past") setYears((y) => Math.min(y, 30));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (blocker || isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      if (isPast) {
        setBacktest(
          await planningApi.backtestSip({
            funds: toFundWeights(funds),
            monthly_amount: monthly,
            years,
            annual_step_up_percent: stepUp,
          }),
        );
      } else {
        setProjection(
          await planningApi.projectSip({
            monthly_amount: monthly,
            years,
            annual_step_up_percent: stepUp,
            goal_amount: goalText ? goal : null,
            return_source: source,
            preset: source === "preset" ? preset : null,
            funds: source === "funds" ? toFundWeights(funds) : [],
          }),
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  };

  const result = isPast ? backtest : projection;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Plan"
        title="SIP & goal planner"
        description="Project what a monthly SIP could grow to — or see exactly what it would have grown to if you'd started years ago."
      />

      <div className="tabs" role="tablist" aria-label="Planner mode">
        <button
          type="button"
          role="tab"
          aria-selected={!isPast}
          className={`tabs__tab${!isPast ? " tabs__tab--active" : ""}`}
          onClick={() => switchMode("future")}
        >
          <TrendingUp size={16} /> Project the future
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={isPast}
          className={`tabs__tab${isPast ? " tabs__tab--active" : ""}`}
          onClick={() => switchMode("past")}
        >
          <HistoryIcon size={16} /> What would have happened
        </button>
      </div>

      <div className="planner-layout">
        <form ref={formRef} className="card planner-form" onSubmit={handleSubmit}>
          <h2 className="card__title">{isPast ? "A SIP you could have started" : "Your SIP"}</h2>

          {!isPast && (
            <fieldset className="field">
              <legend className="field__label">Expected returns based on</legend>
              <div className="segmented">
                {SOURCE_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`segmented__option${source === option.value ? " segmented__option--selected" : ""}`}
                    aria-pressed={source === option.value}
                    onClick={() => setSource(option.value)}
                  >
                    <span className="segmented__label">{option.label}</span>
                    <span className="segmented__hint">{option.hint}</span>
                  </button>
                ))}
              </div>
            </fieldset>
          )}

          {usesFunds && (
            <div className="field">
              <span className="field__label">{isPast ? "Fund(s)" : "Your fund(s)"}</span>
              <FundPicker funds={funds} onChange={setFunds} />
            </div>
          )}
          {!isPast && source === "preset" && (
            <label className="field" htmlFor="sip-preset">
              <span className="field__label">Fund type</span>
              <select id="sip-preset" className="input" value={preset} onChange={(e) => setPreset(e.target.value as ReturnPreset)}>
                {presets.map((p) => (
                  <option key={p.preset} value={p.preset}>
                    {p.label} — ~{p.annual_return_percent}% a year
                  </option>
                ))}
              </select>
            </label>
          )}

          <div className="field">
            <label className="field__label" htmlFor="sip-monthly">
              Monthly amount (₹)
            </label>
            <input
              id="sip-monthly"
              className="input"
              type="number"
              min={100}
              step="any"
              value={monthlyText}
              onChange={(e) => setMonthlyText(e.target.value)}
            />
            {monthly > 0 && <p className="field__hint">{formatInr(monthly)} every month</p>}
          </div>

          <div className="field">
            <label className="field__label" htmlFor="sip-years">
              {isPast ? "Started" : "For"} <strong>{years}</strong> year{years > 1 ? "s" : ""} {isPast ? "ago" : ""}
            </label>
            <input
              id="sip-years"
              className="risk-slider"
              type="range"
              min={1}
              max={maxYears}
              value={years}
              onChange={(e) => setYears(Number(e.target.value))}
            />
          </div>

          <div className="field">
            <label className="field__label" htmlFor="sip-stepup">
              Increase the SIP every year by <strong>{stepUp}%</strong>
            </label>
            <input
              id="sip-stepup"
              className="risk-slider"
              type="range"
              min={0}
              max={25}
              value={stepUp}
              onChange={(e) => setStepUp(Number(e.target.value))}
            />
          </div>

          {!isPast && (
            <div className="field">
              <label className="field__label" htmlFor="sip-goal">
                Goal amount (₹, optional)
              </label>
              <input
                id="sip-goal"
                className="input"
                type="number"
                min={0}
                step="any"
                placeholder="e.g. 2500000"
                value={goalText}
                onChange={(e) => setGoalText(e.target.value)}
              />
              {goal > 0 && <p className="field__hint">{formatInrCompact(goal)} target</p>}
            </div>
          )}

          <button type="submit" className="button button--primary button--large button--block" disabled={Boolean(blocker) || isLoading}>
            {isPast ? <HistoryIcon size={18} /> : <Calculator size={18} />}{" "}
            {isLoading ? "Working…" : isPast ? "Show what would have happened" : "Project my SIP"}
          </button>
          {blocker && <p className="field__hint">{blocker}</p>}
        </form>

        <div className="planner-results">
          {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
          {isLoading && (
            <LoadingSpinner label={isPast ? "Replaying every month at real NAVs…" : "Simulating 4,000 market paths…"} />
          )}
          {!result && !isLoading && (
            <section className="card planner-empty">
              <EmptyState
                icon={isPast ? HistoryIcon : Target}
                title={isPast ? "Replay a SIP from the past" : "See where a SIP could take you"}
                description={
                  isPast
                    ? "Pick a fund and how many years ago you'd have started — every month is replayed at the real NAV."
                    : "Pick your fund(s), set the SIP, and see a bad / typical / good range from 4,000 simulated paths."
                }
                actions={
                  <button type="button" className="button button--primary" onClick={tryExample}>
                    Try an example:{" "}
                    {isPast ? "₹5,000/month for 7 years" : "₹10,000/month for 10 years"} in {EXAMPLE_FUND.name}
                  </button>
                }
              />
            </section>
          )}
          {!isLoading && isPast && backtest && <SipBacktestResults result={backtest} />}
          {!isLoading && !isPast && projection && <SipProjectionResults result={projection} />}
        </div>
      </div>
    </div>
  );
}
