// Mirrors backend/app/schemas/recommendation_schemas.py

import type { ProviderId } from "./provider.types";

export type InvestmentMode = "one_time" | "recurring";
export type RecurringFrequency = "monthly" | "yearly";
export type StockUniverseSource = "default" | "watchlist" | "custom";
export type AssetMix = "stocks" | "mutual_funds" | "mixed";
export type AssetType = "stock" | "mutual_fund";

export interface RecommendationRequest {
  investment_mode: InvestmentMode;
  amount: number;
  recurring_frequency: RecurringFrequency | null;
  risk_level: number;
  provider_id: ProviderId;
  model_name: string | null;
  asset_mix: AssetMix;
  universe_source: StockUniverseSource;
  custom_tickers: string[];
}

/** Stock pre-score breakdown. */
export interface CandidateScore {
  momentum_score: number;
  quality_score: number;
  valuation_score: number;
  risk_fit_score: number;
  total_score: number;
}

/** Mutual fund pre-score breakdown. */
export interface FundScore {
  returns_score: number;
  risk_adjusted_score: number;
  downside_score: number;
  risk_fit_score: number;
  total_score: number;
}

export interface NewsHeadline {
  title: string;
  publisher: string | null;
  published_at: string | null;
  url: string | null;
}

export interface PortfolioAllocation {
  /** Stock ticker ("TCS.NS") or fund symbol ("MF:122639"). */
  ticker: string;
  asset_type?: AssetType;
  display_name?: string | null;
  /** Company name, or the full scheme name for a fund. */
  company_name: string;
  /** Sector for stocks, category for funds. */
  sector: string | null;
  weight_percent: number;
  amount: number;
  /** Share price, or NAV for a fund. */
  last_price: number;
  approx_whole_shares: number;
  approx_units?: number | null;
  rationale: string;
}

export interface CandidateSummary {
  ticker: string;
  asset_type?: AssetType;
  display_name?: string | null;
  company_name: string;
  sector: string | null;
  last_price: number;
  return_1y_percent: number | null;
  cagr_3y_percent?: number | null;
  annualized_volatility_percent: number | null;
  trailing_pe: number | null;
  score: CandidateScore | FundScore;
  headlines: NewsHeadline[];
  was_picked: boolean;
}

export interface RecommendationResponse {
  id: number;
  created_at: string;
  investment_mode: InvestmentMode;
  recurring_frequency: RecurringFrequency | null;
  amount: number;
  risk_level: number;
  provider_id: ProviderId;
  model_name: string;
  asset_mix?: AssetMix;
  allocations: PortfolioAllocation[];
  summary: string;
  risk_notes: string[];
  candidates_considered: CandidateSummary[];
  skipped_tickers: Record<string, string>;
  disclaimer: string;
}

export interface RecommendationHistoryItem {
  id: number;
  created_at: string;
  investment_mode: InvestmentMode;
  recurring_frequency: RecurringFrequency | null;
  amount: number;
  risk_level: number;
  provider_id: ProviderId;
  model_name: string;
  asset_mix?: AssetMix;
  picked_tickers: string[];
  picked_labels?: string[];
}
