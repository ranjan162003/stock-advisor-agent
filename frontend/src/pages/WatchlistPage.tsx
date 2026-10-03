import { PiggyBank, TrendingUp } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { mutualFundApi } from "../api/mutualFundApi";
import { stockUniverseApi, type UniverseStock } from "../api/stockUniverseApi";
import { watchlistApi } from "../api/watchlistApi";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { PageHeader } from "../components/layout/PageHeader";
import { FundWatchlistManager } from "../components/watchlist/FundWatchlistManager";
import { WatchlistManager } from "../components/watchlist/WatchlistManager";
import type { UniverseFund, WatchlistFund } from "../types/mutualFund.types";
import type { WatchlistTicker } from "../types/watchlist.types";

type WatchlistTab = "stocks" | "funds";

export function WatchlistPage() {
  const [tab, setTab] = useState<WatchlistTab>("stocks");
  const [stocks, setStocks] = useState<WatchlistTicker[] | null>(null);
  const [funds, setFunds] = useState<WatchlistFund[] | null>(null);
  const [stockSuggestions, setStockSuggestions] = useState<UniverseStock[]>([]);
  const [fundSuggestions, setFundSuggestions] = useState<UniverseFund[]>([]);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const [stockList, fundList] = await Promise.all([watchlistApi.list(), mutualFundApi.listWatchlist()]);
      setStocks(stockList);
      setFunds(fundList);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void reload();
    stockUniverseApi.getDefaultUniverse().then(setStockSuggestions).catch(() => setStockSuggestions([]));
    mutualFundApi.getDefaultUniverse().then(setFundSuggestions).catch(() => setFundSuggestions([]));
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
        description="Build your own list of stocks and mutual funds, then choose “My watchlist” on the Advisor page so the agent only picks from these."
      />

      <div className="tabs" role="tablist" aria-label="Watchlist type">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "stocks"}
          className={`tabs__tab${tab === "stocks" ? " tabs__tab--active" : ""}`}
          onClick={() => setTab("stocks")}
        >
          <TrendingUp size={16} /> Stocks <span className="tabs__count">{stocks?.length ?? 0}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "funds"}
          className={`tabs__tab${tab === "funds" ? " tabs__tab--active" : ""}`}
          onClick={() => setTab("funds")}
        >
          <PiggyBank size={16} /> Mutual funds <span className="tabs__count">{funds?.length ?? 0}</span>
        </button>
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {stocks === null || funds === null ? (
        <LoadingSpinner />
      ) : tab === "stocks" ? (
        <WatchlistManager
          watchlist={stocks}
          suggestions={stockSuggestions}
          onAdd={(ticker) => runAndReload(() => watchlistApi.add(ticker))}
          onRemove={(ticker) => runAndReload(() => watchlistApi.remove(ticker))}
        />
      ) : (
        <FundWatchlistManager
          watchlist={funds}
          suggestions={fundSuggestions}
          onAdd={(code) => runAndReload(() => mutualFundApi.addToWatchlist(code))}
          onRemove={(code) => runAndReload(() => mutualFundApi.removeFromWatchlist(code))}
        />
      )}
    </div>
  );
}
