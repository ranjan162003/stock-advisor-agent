import { PiggyBank } from "lucide-react";
import { useState } from "react";

import type { UniverseFund, WatchlistFund } from "../../types/mutualFund.types";
import { EmptyState } from "../common/EmptyState";
import { FundSearchCombobox } from "../common/FundSearchCombobox";

interface FundWatchlistManagerProps {
  watchlist: WatchlistFund[];
  suggestions: UniverseFund[];
  onAdd: (schemeCode: number) => Promise<void>;
  onAddExamples: () => Promise<void>;
  onRemove: (schemeCode: number) => void;
}

/** Browse or search every active Indian mutual fund and keep a personal fund watchlist. */
export function FundWatchlistManager({ watchlist, suggestions, onAdd, onAddExamples, onRemove }: FundWatchlistManagerProps) {
  const [isAdding, setIsAdding] = useState(false);
  const watchedCodes = new Set(watchlist.map((fund) => fund.scheme_code));

  const add = async (schemeCode: number) => {
    setIsAdding(true);
    try {
      await onAdd(schemeCode);
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <section className="card">
      <h2 className="card__title">Mutual funds ({watchlist.length})</h2>
      <FundSearchCombobox selectedCodes={watchedCodes} onSelect={(fund) => void add(fund.schemeCode)} />
      <p className="field__hint">
        Pick a category to browse, or type any part of a fund's name. Direct · Growth plans are shown by default — they
        cost less than Regular plans and reinvest returns.
      </p>
      {isAdding && <p className="muted">Adding…</p>}

      {watchlist.length === 0 ? (
        <EmptyState
          compact
          icon={PiggyBank}
          title="No funds yet"
          description="Search the list above — or start with a few popular Direct-Growth funds."
          actions={
            suggestions.length > 0 && (
              <button type="button" className="button button--primary button--small" onClick={() => void onAddExamples()}>
                Try an example: add 3 popular funds
              </button>
            )
          }
        />
      ) : (
        <ul className="chip-list">
          {watchlist.map((fund) => (
            <li key={fund.scheme_code} className="chip" title={fund.category ?? undefined}>
              {fund.scheme_name.split(" - ")[0]}
              <button
                type="button"
                className="chip__remove"
                aria-label={`Remove ${fund.scheme_name}`}
                onClick={() => onRemove(fund.scheme_code)}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
