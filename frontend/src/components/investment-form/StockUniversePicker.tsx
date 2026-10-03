import { Link } from "react-router-dom";

import type { AssetMix, StockUniverseSource } from "../../types/recommendation.types";

export interface WatchlistCounts {
  stocks: number;
  funds: number;
}

interface StockUniversePickerProps {
  assetMix: AssetMix;
  source: StockUniverseSource;
  customTickersText: string;
  watchlistCounts: WatchlistCounts;
  onSourceChange: (source: StockUniverseSource) => void;
  onCustomTickersTextChange: (text: string) => void;
}

/** Which candidates the agent may pick from: built-in lists, the watchlist, or custom stock tickers. */
export function StockUniversePicker({
  assetMix,
  source,
  customTickersText,
  watchlistCounts,
  onSourceChange,
  onCustomTickersTextChange,
}: StockUniversePickerProps) {
  const includesStocks = assetMix !== "mutual_funds";
  const includesFunds = assetMix !== "stocks";

  const builtInLabel = [includesStocks && "24 large NSE stocks", includesFunds && "18 popular funds"]
    .filter(Boolean)
    .join(" + ");
  const watchlistCount = [includesStocks && `${watchlistCounts.stocks} stocks`, includesFunds && `${watchlistCounts.funds} funds`]
    .filter(Boolean)
    .join(", ");
  const watchlistTooSmall =
    (assetMix === "stocks" && watchlistCounts.stocks < 2) ||
    (assetMix === "mutual_funds" && watchlistCounts.funds < 2) ||
    (assetMix === "mixed" && (watchlistCounts.stocks < 1 || watchlistCounts.funds < 1));

  const options: { value: StockUniverseSource; label: string; extra?: string; disabled?: boolean }[] = [
    { value: "default", label: builtInLabel },
    { value: "watchlist", label: "My watchlist", extra: `(${watchlistCount})` },
    { value: "custom", label: "Custom stock list", disabled: !includesStocks },
  ];

  return (
    <fieldset className="field">
      <legend className="field__label">What the agent can choose from</legend>
      <div className="radio-row">
        {options.map((option) => (
          <label
            key={option.value}
            className={`radio-row__option${option.disabled ? " radio-row__option--disabled" : ""}`}
            title={option.disabled ? "Custom lists are for stock tickers" : undefined}
          >
            <input
              type="radio"
              name="universe-source"
              value={option.value}
              checked={source === option.value}
              disabled={option.disabled}
              onChange={() => onSourceChange(option.value)}
            />
            {option.label}
            {option.extra && <span className="muted"> {option.extra}</span>}
          </label>
        ))}
      </div>

      {source === "watchlist" && watchlistTooSmall && (
        <p className="field__hint field__hint--warning">
          Add {assetMix === "mixed" ? "at least 1 stock and 1 fund" : assetMix === "mutual_funds" ? "at least 2 funds" : "at least 2 stocks"} on
          the <Link to="/watchlist">Watchlist</Link> page first.
        </p>
      )}

      {source === "custom" && includesStocks && (
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
            {includesFunds && " Funds come from the built-in list."}
          </p>
        </>
      )}
    </fieldset>
  );
}
