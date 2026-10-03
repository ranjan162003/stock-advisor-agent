"""Structured per-fund data the agent reasons over (NAV-derived metrics, not raw NAVs)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FundMetrics(BaseModel):
    latest_nav: float
    nav_date: str
    history_years: float
    return_1y_percent: float | None = None
    cagr_3y_percent: float | None = None
    cagr_5y_percent: float | None = None
    annualized_volatility_percent: float | None = None
    max_drawdown_3y_percent: float | None = None
    sharpe_ratio_3y: float | None = None


class FundSnapshot(BaseModel):
    symbol: str = Field(description='App-wide id, e.g. "MF:122639"')
    scheme_code: int
    scheme_name: str
    short_name: str
    fund_house: str | None = None
    category: str | None = None
    risk_class: int = Field(ge=1, le=5, description="1 = liquid/debt … 5 = small cap/sectoral")
    metrics: FundMetrics
    fetched_at: datetime


class FundScore(BaseModel):
    """Transparent, rule-based pre-score used to shortlist funds before the LLM sees them."""

    returns_score: float = Field(ge=0, le=100)
    risk_adjusted_score: float = Field(ge=0, le=100)
    downside_score: float = Field(ge=0, le=100)
    risk_fit_score: float = Field(ge=0, le=100)
    total_score: float = Field(ge=0, le=100)


class ScoredFundCandidate(BaseModel):
    snapshot: FundSnapshot
    score: FundScore


class UniverseFund(BaseModel):
    scheme_code: int
    short_name: str
    category: str
    risk_class: int


class FundSearchResult(BaseModel):
    scheme_code: int
    scheme_name: str
    is_direct_growth: bool
    fund_house: str | None = None
    category: str | None = None
    category_group: str | None = None  # "Equity", "Debt", "Hybrid", …
    category_label: str | None = None  # "Flexi Cap", "Liquid", …
    nav: float | None = None
    nav_date: str | None = None


class FundCategory(BaseModel):
    category: str
    group: str
    label: str
    fund_count: int


class WatchlistFundCreate(BaseModel):
    scheme_code: int = Field(gt=0)


class WatchlistFundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scheme_code: int
    scheme_name: str
    category: str | None
    added_at: datetime
