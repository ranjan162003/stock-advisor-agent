import { RISK_LEVEL_LABELS } from "../../utils/investmentLabels";

const RISK_LEVEL_DESCRIPTIONS: Record<number, string> = {
  1: "Prioritise stability: low volatility, strong balance sheets.",
  2: "Mostly steady names, a little room for growth.",
  3: "A mix of steady and growing companies.",
  4: "Lean into momentum and growth; accept bigger swings.",
  5: "Chase strong momentum; expect large drawdowns.",
};

interface RiskLevelSliderProps {
  value: number;
  onChange: (riskLevel: number) => void;
}

export function RiskLevelSlider({ value, onChange }: RiskLevelSliderProps) {
  return (
    <div className="field">
      <label className="field__label" htmlFor="risk-level">
        Risk preference: <strong>{RISK_LEVEL_LABELS[value]}</strong>
      </label>
      <input
        id="risk-level"
        className="risk-slider"
        type="range"
        min={1}
        max={5}
        step={1}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        aria-valuetext={RISK_LEVEL_LABELS[value]}
      />
      <div className="risk-slider__scale" aria-hidden="true">
        <span>Conservative</span>
        <span>Aggressive</span>
      </div>
      <p className="field__hint">{RISK_LEVEL_DESCRIPTIONS[value]}</p>
    </div>
  );
}
