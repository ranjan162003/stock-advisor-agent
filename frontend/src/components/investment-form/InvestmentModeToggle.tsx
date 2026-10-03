import type { InvestmentMode } from "../../types/recommendation.types";

const MODE_OPTIONS: { value: InvestmentMode; label: string; hint: string }[] = [
  { value: "one_time", label: "One-time", hint: "Split a lump sum into rupee amounts now" },
  { value: "recurring", label: "Recurring", hint: "Get a % target to re-apply every period" },
];

interface InvestmentModeToggleProps {
  value: InvestmentMode;
  onChange: (mode: InvestmentMode) => void;
}

export function InvestmentModeToggle({ value, onChange }: InvestmentModeToggleProps) {
  return (
    <div className="segmented" role="radiogroup" aria-label="Investment mode">
      {MODE_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          className={`segmented__option${value === option.value ? " segmented__option--selected" : ""}`}
          onClick={() => onChange(option.value)}
        >
          <span className="segmented__label">{option.label}</span>
          <span className="segmented__hint">{option.hint}</span>
        </button>
      ))}
    </div>
  );
}
