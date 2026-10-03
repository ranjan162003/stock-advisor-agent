import type { FundCategory, FundSearchResult, UniverseFund, WatchlistFund } from "../types/mutualFund.types";
import { requestJson } from "./httpClient";

export const mutualFundApi = {
  getDefaultUniverse: () => requestJson<UniverseFund[]>("/api/funds/default-universe"),

  search: (query: string, options: { category?: string; includeAllPlans?: boolean; limit?: number } = {}) => {
    const params = new URLSearchParams({ q: query, limit: String(options.limit ?? 20) });
    if (options.category) params.set("category", options.category);
    if (options.includeAllPlans) params.set("include_all_plans", "true");
    return requestJson<FundSearchResult[]>(`/api/funds/search?${params}`);
  },

  getCategories: () => requestJson<FundCategory[]>("/api/funds/categories"),

  listWatchlist: () => requestJson<WatchlistFund[]>("/api/watchlist/funds"),

  addToWatchlist: (schemeCode: number) =>
    requestJson<WatchlistFund>("/api/watchlist/funds", {
      method: "POST",
      body: JSON.stringify({ scheme_code: schemeCode }),
    }),

  removeFromWatchlist: (schemeCode: number) =>
    requestJson<void>(`/api/watchlist/funds/${schemeCode}`, { method: "DELETE" }),
};
