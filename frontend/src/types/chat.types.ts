// Ask-AI chat — mirrors backend/app/schemas/chat_schemas.py and the cards from assistant_tools.py.

import type { SipBacktestResponse, SipProjectionResponse } from "./planning.types";
import type { ProviderId } from "./provider.types";
import type { RecommendationResponse } from "./recommendation.types";

export interface ChatFundListItem {
  scheme_code: number;
  name: string;
  category: string | null;
  fund_house: string | null;
  nav: number | null;
}

export interface ChatFundDetails {
  scheme_code: number;
  name: string;
  full_name: string;
  category: string | null;
  fund_house: string | null;
  risk_class_1_to_5: number;
  nav: number;
  nav_date: string;
  return_1y_percent: number | null;
  cagr_3y_percent: number | null;
  cagr_5y_percent: number | null;
  volatility_percent: number | null;
  worst_drawdown_3y_percent: number | null;
  sharpe_3y: number | null;
  history_years: number;
}

export interface ChatStockDetails {
  ticker: string;
  name: string;
  sector: string | null;
  price: number;
  return_1m_percent: number | null;
  return_6m_percent: number | null;
  return_1y_percent: number | null;
  vs_200_day_average_percent: number | null;
  rsi_14: number | null;
  volatility_percent: number | null;
  worst_drawdown_1y_percent: number | null;
  pe: number | null;
  forward_pe: number | null;
  roe_percent: number | null;
  earnings_growth_percent: number | null;
  debt_to_equity: number | null;
  dividend_yield_percent: number | null;
  headlines: string[];
}

export type ChatCard =
  | { type: "fund_list"; query: string; funds: ChatFundListItem[] }
  | { type: "fund"; fund: ChatFundDetails }
  | { type: "fund_comparison"; funds: ChatFundDetails[] }
  | { type: "stock"; stock: ChatStockDetails }
  | { type: "sip_projection"; result: SipProjectionResponse }
  | { type: "sip_backtest"; result: SipBacktestResponse }
  | { type: "recommendation"; recommendation: RecommendationResponse };

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  cards: ChatCard[];
  suggestions: string[];
  created_at: string;
}

export interface ChatConversationSummary {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatConversationDetail extends ChatConversationSummary {
  messages: ChatMessage[];
}

export interface ChatSendRequest {
  message: string;
  provider_id: ProviderId;
  model_name?: string | null;
  page?: string | null;
  recommendation_id?: number | null;
}

/** One Server-Sent Event from POST /api/chat/conversations/{id}/messages. */
export type ChatStreamEvent =
  | { type: "status"; text: string }
  | { type: "card"; card: ChatCard }
  | { type: "answer"; text: string; suggestions: string[] }
  | {
      type: "done";
      conversation: ChatConversationSummary;
      user_message: ChatMessage;
      assistant_message: ChatMessage;
    }
  | { type: "error"; message: string };
