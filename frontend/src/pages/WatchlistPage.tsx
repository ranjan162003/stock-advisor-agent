import { useCallback, useEffect, useState } from "react";

import { stockUniverseApi, type UniverseStock } from "../api/stockUniverseApi";
import { watchlistApi } from "../api/watchlistApi";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { PageHeader } from "../components/layout/PageHeader";
import { WatchlistManager } from "../components/watchlist/WatchlistManager";
import type { WatchlistTicker } from "../types/watchlist.types";

export function WatchlistPage() {
  const [watchlist, setWatchlist] = useState<WatchlistTicker[] | null>(null);
  const [suggestions, setSuggestions] = useState<UniverseStock[]>([]);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setWatchlist(await watchlistApi.list());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void reload();
    stockUniverseApi.getDefaultUniverse().then(setSuggestions).catch(() => setSuggestions([]));
  }, [reload]);

  const runAndReload = async (action: () => Promise<unknown>) => {
    setError(null);
    try {
      await action();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="page page--narrow">
      <PageHeader
        eyebrow="Your universe"
        title="Watchlist"
        description="Build your own list of stocks, then choose “My watchlist” on the Advisor page so the agent only picks from these."
      />
      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
      {watchlist === null ? (
        <LoadingSpinner />
      ) : (
        <WatchlistManager
          watchlist={watchlist}
          suggestions={suggestions}
          onAdd={(ticker) => runAndReload(() => watchlistApi.add(ticker))}
          onRemove={(ticker) => runAndReload(() => watchlistApi.remove(ticker))}
        />
      )}
    </div>
  );
}
