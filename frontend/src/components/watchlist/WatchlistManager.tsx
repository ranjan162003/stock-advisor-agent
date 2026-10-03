import { Star } from "lucide-react";
import { useState, type FormEvent } from "react";

import type { UniverseStock } from "../../api/stockUniverseApi";
import type { WatchlistTicker } from "../../types/watchlist.types";
import { shortTicker } from "../../utils/displayFormatters";
import { EmptyState } from "../common/EmptyState";

interface WatchlistManagerProps {
  watchlist: WatchlistTicker[];
  suggestions: UniverseStock[];
  onAdd: (ticker: string) => Promise<void>;
  onAddExamples: () => Promise<void>;
  onRemove: (ticker: string) => void;
}

export function WatchlistManager({ watchlist, suggestions, onAdd, onAddExamples, onRemove }: WatchlistManagerProps) {
  const [tickerInput, setTickerInput] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const watched = new Set(watchlist.map((w) => w.ticker));
  const unwatchedSuggestions = suggestions.filter((s) => !watched.has(s.ticker));

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!tickerInput.trim()) return;
    setIsAdding(true);
    try {
      await onAdd(tickerInput.trim());
      setTickerInput("");
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <>
      <section className="card">
        <h2 className="card__title">Stocks ({watchlist.length})</h2>
        <form className="inline-form" onSubmit={handleSubmit}>
          <input
            className="input"
            placeholder="Ticker, e.g. ZOMATO or TATAMOTORS.BO"
            value={tickerInput}
            onChange={(event) => setTickerInput(event.target.value)}
            aria-label="Ticker to add"
          />
          <button type="submit" className="button button--primary" disabled={isAdding || !tickerInput.trim()}>
            Add
          </button>
        </form>
        <p className="field__hint">Plain symbols default to NSE (.NS). Symbols are checked when a recommendation runs.</p>

        {watchlist.length === 0 ? (
          <EmptyState
            compact
            icon={Star}
            title="No stocks yet"
            description="Add tickers above, tap a suggestion below — or start with a few popular large caps."
            actions={
              suggestions.length > 0 && (
                <button type="button" className="button button--primary button--small" onClick={() => void onAddExamples()}>
                  Try an example: add 5 popular stocks
                </button>
              )
            }
          />
        ) : (
          <ul className="chip-list">
            {watchlist.map((entry) => (
              <li key={entry.ticker} className="chip">
                {shortTicker(entry.ticker)}
                <span className="muted chip__suffix">{entry.ticker.slice(shortTicker(entry.ticker).length)}</span>
                <button
                  type="button"
                  className="chip__remove"
                  aria-label={`Remove ${entry.ticker}`}
                  onClick={() => onRemove(entry.ticker)}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {unwatchedSuggestions.length > 0 && (
        <section className="card">
          <h2 className="card__title">Suggestions</h2>
          <ul className="chip-list">
            {unwatchedSuggestions.map((stock) => (
              <li key={stock.ticker}>
                <button
                  type="button"
                  className="chip chip--add"
                  title={`${stock.company_name} · ${stock.sector}`}
                  onClick={() => void onAdd(stock.ticker)}
                >
                  + {shortTicker(stock.ticker)}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
