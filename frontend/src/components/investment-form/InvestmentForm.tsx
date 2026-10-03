import type { AssetMix, InvestmentMode, RecurringFrequency, StockUniverseSource } from "../../types/recommendation.types";
import { formatInr } from "../../utils/displayFormatters";
import { AssetMixToggle } from "./AssetMixToggle";
import { InvestmentModeToggle } from "./InvestmentModeToggle";
import { RiskLevelSlider } from "./RiskLevelSlider";
import { StockUniversePicker, type WatchlistCounts } from "./StockUniversePicker";

export interface InvestmentFormValues {
  assetMix: AssetMix;
  investmentMode: InvestmentMode;
  amountText: string;
  recurringFrequency: RecurringFrequency;
  riskLevel: number;
  universeSource: StockUniverseSource;
  customTickersText: string;
}

export const INITIAL_INVESTMENT_FORM_VALUES: InvestmentFormValues = {
  assetMix: "stocks",
  investmentMode: "one_time",
  amountText: "50000",
  recurringFrequency: "monthly",
  riskLevel: 3,
  universeSource: "default",
  customTickersText: "",
};

interface InvestmentFormProps {
  values: InvestmentFormValues;
  watchlistCounts: WatchlistCounts;
  onChange: (values: InvestmentFormValues) => void;
}

export function InvestmentForm({ values, watchlistCounts, onChange }: InvestmentFormProps) {
  const update = <K extends keyof InvestmentFormValues>(key: K, value: InvestmentFormValues[K]) =>
    onChange({ ...values, [key]: value });

  const amount = Number(values.amountText);
  const isRecurring = values.investmentMode === "recurring";

  return (
    <section className="card">
      <h2 className="card__title">Investment</h2>

      <AssetMixToggle
        value={values.assetMix}
        onChange={(assetMix) =>
          onChange({
            ...values,
            assetMix,
            // Custom lists hold stock tickers, so they don't apply to a funds-only request.
            universeSource: assetMix === "mutual_funds" && values.universeSource === "custom" ? "default" : values.universeSource,
          })
        }
      />

      <InvestmentModeToggle value={values.investmentMode} onChange={(mode) => update("investmentMode", mode)} />

      <div className="field-row">
        <div className="field field--grow">
          <label className="field__label" htmlFor="amount">
            {isRecurring ? (values.assetMix === "stocks" ? "Amount per period (₹)" : "SIP amount per period (₹)") : "Lump sum (₹)"}
          </label>
          <input
            id="amount"
            className="input"
            type="number"
            inputMode="numeric"
            min={1}
            step="any"
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
        assetMix={values.assetMix}
        source={values.universeSource}
        customTickersText={values.customTickersText}
        watchlistCounts={watchlistCounts}
        onSourceChange={(source) => update("universeSource", source)}
        onCustomTickersTextChange={(text) => update("customTickersText", text)}
      />
    </section>
  );
}
