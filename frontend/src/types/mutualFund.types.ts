// Mirrors backend/app/schemas/mutual_fund_schemas.py

export interface UniverseFund {
  scheme_code: number;
  short_name: string;
  category: string;
  risk_class: number;
}

export interface FundSearchResult {
  scheme_code: number;
  scheme_name: string;
  is_direct_growth: boolean;
  fund_house?: string | null;
  category?: string | null;
  category_group?: string | null;
  category_label?: string | null;
  nav?: number | null;
  nav_date?: string | null;
}

export interface FundCategory {
  /** Filter key, e.g. "Equity · Flexi Cap". */
  category: string;
  group: string;
  label: string;
  fund_count: number;
}

export interface WatchlistFund {
  id: number;
  scheme_code: number;
  scheme_name: string;
  category: string | null;
  added_at: string;
}
