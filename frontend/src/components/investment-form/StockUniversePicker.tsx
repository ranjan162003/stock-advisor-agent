import { Link } from "react-router-dom";

import type { StockUniverseSource } from "../../types/recommendation.types";

const SOURCE_OPTIONS: { value: StockUniverseSource; label: string }[] = [
  { value: "default", label: "24 large NSE stocks" },
  { value: "watchlist", label: "My watchlist" },
  { value: "custom", label: "Custom list" },
];

interface StockUniversePickerProps {
  source: StockUniverseSource;
  customTickersText: string;
  watchlistSize: number;
  onSourceChange: (source: StockUniverseSource) => void;
  onCustomTickersTextChange: (text: string) => void;
}

export function StockUniversePicker({
  source,
  customTickersText,
  watchlistSize,
  onSourceChange,
  onCustomTickersTextChange,
}: StockUniversePickerProps) {
  return (
    <fieldset className="field">
      <legend className="field__label">Stocks the agent can choose from</legend>
      <div className="radio-row">
        {SOURCE_OPTIONS.map((option) => (
          <label key={option.value} className="radio-row__option">
            <input
              type="radio"
              name="universe-source"
              value={option.value}
              checked={source === option.value}
              onChange={() => onSourceChange(option.value)}
            />
            {option.label}
            {option.value === "watchlist" && <span className="muted"> ({watchlistSize})</span>}
          </label>
        ))}
      </div>

      {source === "watchlist" && watchlistSize < 2 && (
        <p className="field__hint field__hint--warning">
          Add at least 2 stocks on the <Link to="/watchlist">Watchlist</Link> page first.
        </p>
      )}

      {source === "custom" && (
        <>
          <textarea
            className="input input--textarea"
            rows={2}
            placeholder="e.g. INFY, TCS, HDFCBANK, ITC, SUNPHARMA"
            value={customTickersText}
            onChange={(event) => onCustomTickersTextChange(event.target.value)}
            aria-label="Custom tickers, comma separated"
          />
          <p className="field__hint">
            Comma-separated. Plain symbols default to NSE (<code>.NS</code>); add <code>.BO</code> for BSE.
          </p>
        </>
      )}
    </fieldset>
  );
}
