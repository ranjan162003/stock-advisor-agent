import { X } from "lucide-react";

import { FundSearchCombobox } from "../common/FundSearchCombobox";

export interface PickedFund {
  schemeCode: number;
  name: string;
  weightText: string;
}

const MAX_FUNDS = 5;

interface FundPickerProps {
  funds: PickedFund[];
  onChange: (funds: PickedFund[]) => void;
}

/** Choose 1–5 mutual funds (browse or search all funds) and how the SIP is split between them. */
export function FundPicker({ funds, onChange }: FundPickerProps) {
  const total = funds.reduce((sum, f) => sum + (Number(f.weightText) || 0), 0);
  const chosen = new Set(funds.map((f) => f.schemeCode));

  return (
    <div className="fund-picker">
      {funds.length > 0 && (
        <ul className="fund-picker__chosen">
          {funds.map((fund) => (
            <li key={fund.schemeCode} className="fund-picker__row">
              <span className="fund-picker__name" title={fund.name}>
                {fund.name}
              </span>
              {funds.length > 1 && (
                <span className="fund-picker__weight">
                  <input
                    className="input input--compact"
                    type="number"
                    min={1}
                    max={100}
                    step="any"
                    value={fund.weightText}
                    aria-label={`${fund.name} share of the SIP`}
                    onChange={(e) =>
                      onChange(funds.map((f) => (f.schemeCode === fund.schemeCode ? { ...f, weightText: e.target.value } : f)))
                    }
                  />
                  %
                </span>
              )}
              <button
                type="button"
                className="icon-button"
                aria-label={`Remove ${fund.name}`}
                onClick={() => onChange(evenSplit(funds.filter((f) => f.schemeCode !== fund.schemeCode)))}
              >
                <X size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
      {funds.length > 1 && Math.abs(total - 100) > 0.5 && (
        <p className="field__hint field__hint--warning">Splits add up to {total}% — make them total 100%.</p>
      )}

      {funds.length < MAX_FUNDS ? (
        <FundSearchCombobox
          selectedCodes={chosen}
          placeholder={funds.length ? "Add another fund…" : undefined}
          onSelect={(fund) => onChange(evenSplit([...funds, { schemeCode: fund.schemeCode, name: fund.shortName, weightText: "" }]))}
        />
      ) : (
        <p className="field__hint">Up to {MAX_FUNDS} funds — remove one to add another.</p>
      )}
    </div>
  );
}

/** Reset to an even split whenever funds are added/removed (user can then adjust). */
function evenSplit(funds: PickedFund[]): PickedFund[] {
  if (funds.length === 0) return funds;
  const base = Math.floor(100 / funds.length);
  return funds.map((fund, i) => ({ ...fund, weightText: String(i === 0 ? 100 - base * (funds.length - 1) : base) }));
}

export function toFundWeights(funds: PickedFund[]) {
  return funds.map((f) => ({ scheme_code: f.schemeCode, weight_percent: funds.length === 1 ? 100 : Number(f.weightText) || 0 }));
}

export function fundSplitIsValid(funds: PickedFund[]): boolean {
  if (funds.length === 0) return false;
  if (funds.length === 1) return true;
  const total = funds.reduce((sum, f) => sum + (Number(f.weightText) || 0), 0);
  return Math.abs(total - 100) <= 0.5 && funds.every((f) => Number(f.weightText) > 0);
}
