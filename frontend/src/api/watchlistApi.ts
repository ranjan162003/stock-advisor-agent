import type { WatchlistTicker } from "../types/watchlist.types";
import { requestJson } from "./httpClient";

export const watchlistApi = {
  list: () => requestJson<WatchlistTicker[]>("/api/watchlist"),

  add: (ticker: string) =>
    requestJson<WatchlistTicker>("/api/watchlist", { method: "POST", body: JSON.stringify({ ticker }) }),

  remove: (ticker: string) =>
    requestJson<void>(`/api/watchlist/${encodeURIComponent(ticker)}`, { method: "DELETE" }),
};
