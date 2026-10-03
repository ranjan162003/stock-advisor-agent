import { Layers, PiggyBank, TrendingUp, type LucideIcon } from "lucide-react";

import type { AssetMix } from "../../types/recommendation.types";

const ASSET_MIX_OPTIONS: { value: AssetMix; label: string; hint: string; icon: LucideIcon }[] = [
  { value: "stocks", label: "Stocks", hint: "Individual NSE companies", icon: TrendingUp },
  { value: "mutual_funds", label: "Mutual funds", hint: "Diversified, professionally managed", icon: PiggyBank },
  { value: "mixed", label: "Mix of both", hint: "Agent balances stocks vs funds", icon: Layers },
];

interface AssetMixToggleProps {
  value: AssetMix;
  onChange: (assetMix: AssetMix) => void;
}

export function AssetMixToggle({ value, onChange }: AssetMixToggleProps) {
  return (
    <div className="field">
      <span className="field__label">Invest in</span>
      <div className="segmented segmented--three" role="radiogroup" aria-label="What to invest in">
        {ASSET_MIX_OPTIONS.map(({ value: option, label, hint, icon: Icon }) => (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={value === option}
            className={`segmented__option${value === option ? " segmented__option--selected" : ""}`}
            onClick={() => onChange(option)}
          >
            <span className="segmented__label">
              <Icon size={16} aria-hidden="true" /> {label}
            </span>
            <span className="segmented__hint">{hint}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
