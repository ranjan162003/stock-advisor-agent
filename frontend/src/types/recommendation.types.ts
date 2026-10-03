// Mirrors backend/app/schemas/recommendation_schemas.py

import type { ProviderId } from "./provider.types";

export type InvestmentMode = "one_time" | "recurring";
export type RecurringFrequency = "monthly" | "yearly";
export type StockUniverseSource = "default" | "watchlist" | "custom";

export interface RecommendationRequest {
  investment_mode: InvestmentMode;
  amount: number;
  recurring_frequency: RecurringFrequency | null;
  risk_level: number;
  provider_id: ProviderId;
  model_name: string | null;
  universe_source: StockUniverseSource;
  custom_tickers: string[];
}

export interface CandidateScore {
  momentum_score: number;
  quality_score: number;
  valuation_score: number;
  risk_fit_score: number;
  total_score: number;
}

export interface NewsHeadline {
  title: string;
  publisher: string | null;
  published_at: string | null;
  url: string | null;
}

export interface StockAllocation {
  ticker: string;
  company_name: string;
  sector: string | null;
  weight_percent: number;
  amount: number;
  last_price: number;
  approx_whole_shares: number;
  rationale: string;
}

export interface CandidateSummary {
  ticker: string;
  company_name: string;
  sector: string | null;
  last_price: number;
  return_1y_percent: number | null;
  annualized_volatility_percent: number | null;
  trailing_pe: number | null;
  score: CandidateScore;
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
  allocations: StockAllocation[];
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
  picked_tickers: string[];
}
