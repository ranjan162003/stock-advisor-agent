"""Request/response contracts for generating and listing recommendations."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.schemas.market_data_schemas import CandidateScore, NewsHeadline
from app.schemas.provider_schemas import ProviderId

RECOMMENDATION_DISCLAIMER = (
    "AI-generated opinion for personal research and education only — not licensed "
    "financial advice. Data may be stale or incomplete and the model can be wrong. "
    "Any investment decision, and its risk, is entirely yours."
)


class InvestmentMode(str, Enum):
    ONE_TIME = "one_time"
    RECURRING = "recurring"


class RecurringFrequency(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class StockUniverseSource(str, Enum):
    DEFAULT = "default"
    WATCHLIST = "watchlist"
    CUSTOM = "custom"


RISK_LEVEL_LABELS = {
    1: "very conservative",
    2: "conservative",
    3: "balanced",
    4: "growth-oriented",
    5: "aggressive",
}


class RecommendationRequest(BaseModel):
    investment_mode: InvestmentMode
    amount: float = Field(gt=0, le=1_000_000_000, description="Amount in INR")
    recurring_frequency: RecurringFrequency | None = None
    risk_level: int = Field(ge=1, le=5)
    provider_id: ProviderId
    model_name: str | None = Field(default=None, max_length=64)
    universe_source: StockUniverseSource = StockUniverseSource.DEFAULT
    custom_tickers: list[str] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def _check_mode_specific_fields(self) -> "RecommendationRequest":
        if self.investment_mode is InvestmentMode.RECURRING and self.recurring_frequency is None:
            raise ValueError("recurring_frequency is required for recurring investments")
        if self.investment_mode is InvestmentMode.ONE_TIME:
            self.recurring_frequency = None
        if self.universe_source is StockUniverseSource.CUSTOM and not self.custom_tickers:
            raise ValueError("custom_tickers must list at least one ticker")
        return self


class StockAllocation(BaseModel):
    ticker: str
    company_name: str
    sector: str | None = None
    weight_percent: float
    amount: float = Field(description="INR for this one-time investment, or for this period if recurring")
    last_price: float
    approx_whole_shares: int
    rationale: str


class CandidateSummary(BaseModel):
    ticker: str
    company_name: str
    sector: str | None = None
    last_price: float
    return_1y_percent: float | None = None
    annualized_volatility_percent: float | None = None
    trailing_pe: float | None = None
    score: CandidateScore
    headlines: list[NewsHeadline] = []
    was_picked: bool


class RecommendationResponse(BaseModel):
    id: int
    created_at: datetime
    investment_mode: InvestmentMode
    recurring_frequency: RecurringFrequency | None
    amount: float
    risk_level: int
    provider_id: ProviderId
    model_name: str
    allocations: list[StockAllocation]
    summary: str
    risk_notes: list[str]
    candidates_considered: list[CandidateSummary]
    skipped_tickers: dict[str, str] = Field(default_factory=dict, description="ticker -> why it was skipped")
    disclaimer: str = RECOMMENDATION_DISCLAIMER


class RecommendationHistoryItem(BaseModel):
    id: int
    created_at: datetime
    investment_mode: InvestmentMode
    recurring_frequency: RecurringFrequency | None
    amount: float
    risk_level: int
    provider_id: ProviderId
    model_name: str
    picked_tickers: list[str]
