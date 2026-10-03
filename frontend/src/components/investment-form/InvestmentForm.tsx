import type { InvestmentMode, RecurringFrequency, StockUniverseSource } from "../../types/recommendation.types";
import { formatInr } from "../../utils/displayFormatters";
import { InvestmentModeToggle } from "./InvestmentModeToggle";
import { RiskLevelSlider } from "./RiskLevelSlider";
import { StockUniversePicker } from "./StockUniversePicker";

export interface InvestmentFormValues {
  investmentMode: InvestmentMode;
  amountText: string;
  recurringFrequency: RecurringFrequency;
  riskLevel: number;
  universeSource: StockUniverseSource;
  customTickersText: string;
}

export const INITIAL_INVESTMENT_FORM_VALUES: InvestmentFormValues = {
  investmentMode: "one_time",
  amountText: "50000",
  recurringFrequency: "monthly",
  riskLevel: 3,
  universeSource: "default",
  customTickersText: "",
};

interface InvestmentFormProps {
  values: InvestmentFormValues;
  watchlistSize: number;
  onChange: (values: InvestmentFormValues) => void;
}

export function InvestmentForm({ values, watchlistSize, onChange }: InvestmentFormProps) {
  const update = <K extends keyof InvestmentFormValues>(key: K, value: InvestmentFormValues[K]) =>
    onChange({ ...values, [key]: value });

  const amount = Number(values.amountText);
  const isRecurring = values.investmentMode === "recurring";

  return (
    <section className="card">
      <h2 className="card__title">Investment</h2>

      <InvestmentModeToggle value={values.investmentMode} onChange={(mode) => update("investmentMode", mode)} />

      <div className="field-row">
        <div className="field field--grow">
          <label className="field__label" htmlFor="amount">
            {isRecurring ? "Amount per period (₹)" : "Lump sum (₹)"}
          </label>
          <input
            id="amount"
            className="input"
            type="number"
            inputMode="numeric"
            min={1}
            step={500}
            value={values.amountText}
            onChange={(event) => update("amountText", event.target.value)}
          />
          {amount > 0 && <p className="field__hint">{formatInr(amount)}</p>}
        </div>

        {isRecurring && (
          <div className="field">
            <label className="field__label" htmlFor="frequency">
              Every
            </label>
            <select
              id="frequency"
              className="input"
              value={values.recurringFrequency}
              onChange={(event) => update("recurringFrequency", event.target.value as RecurringFrequency)}
            >
              <option value="monthly">Month</option>
              <option value="yearly">Year</option>
            </select>
          </div>
        )}
      </div>

      <RiskLevelSlider value={values.riskLevel} onChange={(level) => update("riskLevel", level)} />

      <StockUniversePicker
        source={values.universeSource}
        customTickersText={values.customTickersText}
        watchlistSize={watchlistSize}
        onSourceChange={(source) => update("universeSource", source)}
        onCustomTickersTextChange={(text) => update("customTickersText", text)}
      />
    </section>
  );
}
