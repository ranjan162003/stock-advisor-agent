import { PiggyBank, TrendingUp } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { mutualFundApi } from "../api/mutualFundApi";
import { stockUniverseApi, type UniverseStock } from "../api/stockUniverseApi";
import { watchlistApi } from "../api/watchlistApi";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { SkeletonList } from "../components/common/Skeleton";
import { PageHeader } from "../components/layout/PageHeader";
import { FundWatchlistManager } from "../components/watchlist/FundWatchlistManager";
import { WatchlistManager } from "../components/watchlist/WatchlistManager";
import { useAssistantPageContext } from "../context/AssistantContext";
import { useToast, useUndoableDelete } from "../context/ToastContext";
import type { UniverseFund, WatchlistFund } from "../types/mutualFund.types";
import type { WatchlistTicker } from "../types/watchlist.types";
import { shortTicker } from "../utils/displayFormatters";

type WatchlistTab = "stocks" | "funds";

const EXAMPLE_STOCK_COUNT = 5;
const EXAMPLE_FUND_COUNT = 3;

export function WatchlistPage() {
  useAssistantPageContext("watchlist");
  const toast = useToast();
  const deleteWithUndo = useUndoableDelete();
  const [tab, setTab] = useState<WatchlistTab>("stocks");
  const [stocks, setStocks] = useState<WatchlistTicker[] | null>(null);
  const [funds, setFunds] = useState<WatchlistFund[] | null>(null);
  const [stockSuggestions, setStockSuggestions] = useState<UniverseStock[]>([]);
  const [fundSuggestions, setFundSuggestions] = useState<UniverseFund[]>([]);
  const [error, setError] = useState<string | null>(null);
  // Removals waiting out their Undo window — still on the server, but hidden here.
  const pendingRemovals = useRef(new Set<string>());

  const reload = useCallback(async () => {
    try {
      const [stockList, fundList] = await Promise.all([watchlistApi.list(), mutualFundApi.listWatchlist()]);
      setStocks(stockList.filter((s) => !pendingRemovals.current.has(s.ticker)));
      setFunds(fundList.filter((f) => !pendingRemovals.current.has(`MF:${f.scheme_code}`)));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void reload();
    stockUniverseApi.getDefaultUniverse().then(setStockSuggestions).catch(() => setStockSuggestions([]));
    mutualFundApi.getDefaultUniverse().then(setFundSuggestions).catch(() => setFundSuggestions([]));
  }, [reload]);

  const addAll = async (actions: (() => Promise<unknown>)[], message: string) => {
    setError(null);
    try {
      for (const action of actions) await action();
      await reload();
      toast({ message });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      await reload();
    }
  };

  const removeWithUndo = <T,>(
    key: string,
    label: string,
    setList: (update: (current: T[] | null) => T[] | null) => void,
    matches: (item: T) => boolean,
    commit: () => Promise<unknown>,
  ) => {
    let removed: T | undefined;
    deleteWithUndo({
      message: `Removed ${label} from your watchlist`,
      hide: () => {
        pendingRemovals.current.add(key);
        setList((current) => {
          removed = current?.find(matches);
          return current?.filter((item) => !matches(item)) ?? null;
        });
      },
      restore: () => {
        pendingRemovals.current.delete(key);
        setList((current) => (current && removed && !current.some(matches) ? [...current, removed] : current));
      },
      commit: () => commit().finally(() => pendingRemovals.current.delete(key)),
    });
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
        <section className="card">
          <SkeletonList rows={3} label="Loading your watchlist" />
        </section>
      ) : tab === "stocks" ? (
        <WatchlistManager
          watchlist={stocks}
          suggestions={stockSuggestions}
          onAdd={(ticker) =>
            addAll([() => watchlistApi.add(ticker)], `Added ${shortTicker(ticker.toUpperCase())} to your watchlist`)
          }
          onAddExamples={() =>
            addAll(
              stockSuggestions.slice(0, EXAMPLE_STOCK_COUNT).map((s) => () => watchlistApi.add(s.ticker)),
              `Added ${EXAMPLE_STOCK_COUNT} popular stocks — remove any you don't want`,
            )
          }
          onRemove={(ticker) =>
            removeWithUndo<WatchlistTicker>(ticker, shortTicker(ticker), setStocks, (s) => s.ticker === ticker, () =>
              watchlistApi.remove(ticker),
            )
          }
        />
      ) : (
        <FundWatchlistManager
          watchlist={funds}
          suggestions={fundSuggestions}
          onAdd={(code) => {
            const name = fundSuggestions.find((f) => f.scheme_code === code)?.short_name ?? "the fund";
            return addAll([() => mutualFundApi.addToWatchlist(code)], `Added ${name} to your watchlist`);
          }}
          onAddExamples={() =>
            addAll(
              fundSuggestions.slice(0, EXAMPLE_FUND_COUNT).map((f) => () => mutualFundApi.addToWatchlist(f.scheme_code)),
              `Added ${EXAMPLE_FUND_COUNT} popular funds — remove any you don't want`,
            )
          }
          onRemove={(code) => {
            const fund = funds.find((f) => f.scheme_code === code);
            removeWithUndo<WatchlistFund>(
              `MF:${code}`,
              fund?.scheme_name.split(" - ")[0] ?? "the fund",
              setFunds,
              (f) => f.scheme_code === code,
              () => mutualFundApi.removeFromWatchlist(code),
            );
          }}
        />
      )}
    </div>
  );
}
