"""Structured per-stock data the agent reasons over (never raw price series)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.utc_time import UtcDatetime


class TechnicalIndicators(BaseModel):
    last_close: float
    sma_50: float | None = None
    sma_200: float | None = None
    price_vs_sma_200_percent: float | None = None
    rsi_14: float | None = None
    return_1m_percent: float | None = None
    return_3m_percent: float | None = None
    return_6m_percent: float | None = None
    return_1y_percent: float | None = None
    annualized_volatility_percent: float | None = None
    max_drawdown_1y_percent: float | None = None


class FundamentalMetrics(BaseModel):
    market_cap: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    price_to_book: float | None = None
    earnings_growth_percent: float | None = None
    revenue_growth_percent: float | None = None
    profit_margin_percent: float | None = None
    return_on_equity_percent: float | None = None
    debt_to_equity: float | None = None
    dividend_yield_percent: float | None = None
    beta: float | None = None


class NewsHeadline(BaseModel):
    title: str
    publisher: str | None = None
    published_at: UtcDatetime | None = None
    url: str | None = None


class CandidateScore(BaseModel):
    """Transparent, rule-based pre-score used to shortlist stocks before the LLM sees them."""

    momentum_score: float = Field(ge=0, le=100)
    quality_score: float = Field(ge=0, le=100)
    valuation_score: float = Field(ge=0, le=100)
    risk_fit_score: float = Field(ge=0, le=100)
    total_score: float = Field(ge=0, le=100)


class StockSnapshot(BaseModel):
    ticker: str
    company_name: str
    sector: str | None = None
    currency: str | None = None
    technicals: TechnicalIndicators
    fundamentals: FundamentalMetrics
    headlines: list[NewsHeadline] = []
    fetched_at: UtcDatetime


class ScoredStockCandidate(BaseModel):
    snapshot: StockSnapshot
    score: CandidateScore


class UniverseStock(BaseModel):
    ticker: str
    company_name: str
    sector: str
