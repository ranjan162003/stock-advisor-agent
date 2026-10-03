// Mirrors backend/app/schemas/sip_planner_schemas.py

// ---------- SIP / goal planner ----------

export type ReturnSource = "funds" | "preset";

export interface FundWeight {
  scheme_code: number;
  weight_percent: number;
}
export type ReturnPreset = "debt" | "hybrid" | "large_cap" | "flexi_cap" | "mid_small_cap";

export interface ReturnPresetInfo {
  preset: ReturnPreset;
  label: string;
  annual_return_percent: number;
  annual_volatility_percent: number;
}

export interface SipProjectionRequest {
  monthly_amount: number;
  years: number;
  annual_step_up_percent: number;
  goal_amount: number | null;
  return_source: ReturnSource;
  preset: ReturnPreset | null;
  funds: FundWeight[];
}

export interface YearlyProjectionPoint {
  year: number;
  invested: number;
  bad_case: number;
  typical: number;
  good_case: number;
}

export interface SipProjectionResponse {
  monthly_amount: number;
  years: number;
  annual_step_up_percent: number;
  total_invested: number;
  bad_case: number;
  typical: number;
  good_case: number;
  chance_of_loss_percent: number;
  goal_amount: number | null;
  goal_probability_percent: number | null;
  required_monthly_for_goal_50: number | null;
  required_monthly_for_goal_80: number | null;
  yearly: YearlyProjectionPoint[];
  source_description: string;
  basis_annual_return_percent: number;
  basis_annual_volatility_percent: number;
  history_months: number | null;
  simulated_paths: number;
}

// ---------- What would have happened (historical SIP replay) ----------

export interface SipBacktestRequest {
  funds: FundWeight[];
  monthly_amount: number;
  years: number;
  annual_step_up_percent: number;
}

export interface BacktestPoint {
  date: string;
  invested: number;
  value: number;
}

export interface BacktestFundResult {
  scheme_code: number;
  short_name: string;
  scheme_name: string;
  weight_percent: number;
  invested: number;
  units: number;
  latest_nav: number;
  value: number;
  xirr_percent: number | null;
}

export interface SipBacktestResponse {
  start_date: string;
  end_date: string;
  installments: number;
  monthly_amount: number;
  annual_step_up_percent: number;
  total_invested: number;
  final_value: number;
  gain: number;
  absolute_return_percent: number;
  xirr_percent: number | null;
  fixed_deposit_value: number;
  fixed_deposit_rate_percent: number;
  worst_drawdown_percent: number;
  timeline: BacktestPoint[];
  funds: BacktestFundResult[];
}
