import type { AssetMix, InvestmentMode, RecurringFrequency } from "../types/recommendation.types";
import type { ProviderId } from "../types/provider.types";

// Keep in sync with RISK_LEVEL_LABELS in backend/app/schemas/recommendation_schemas.py
export const RISK_LEVEL_LABELS: Record<number, string> = {
  1: "Very conservative",
  2: "Conservative",
  3: "Balanced",
  4: "Growth",
  5: "Aggressive",
};

export const PROVIDER_LABELS: Record<ProviderId, string> = {
  claude: "Claude",
  gemini: "Gemini",
  ollama: "Ollama",
};

export function describeInvestmentMode(mode: InvestmentMode, frequency: RecurringFrequency | null): string {
  if (mode === "one_time") return "One-time";
  return frequency === "yearly" ? "Every year" : "Every month";
}

export function periodWord(frequency: RecurringFrequency | null): string {
  return frequency === "yearly" ? "year" : "month";
}

export const ASSET_MIX_LABELS: Record<AssetMix, string> = {
  stocks: "Stocks",
  mutual_funds: "Mutual funds",
  mixed: "Stocks + funds",
};
