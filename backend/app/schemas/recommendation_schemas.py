"""Request/response contracts for generating and listing recommendations."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.core.utc_time import UtcDatetime
from app.schemas.market_data_schemas import CandidateScore, NewsHeadline
from app.schemas.mutual_fund_schemas import FundScore
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


class AssetMix(str, Enum):
    STOCKS = "stocks"
    MUTUAL_FUNDS = "mutual_funds"
    MIXED = "mixed"


class AssetType(str, Enum):
    STOCK = "stock"
    MUTUAL_FUND = "mutual_fund"


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
    asset_mix: AssetMix = AssetMix.STOCKS
    # Which candidates to consider: the built-in lists, your watchlist, or (stocks only) custom tickers.
    universe_source: StockUniverseSource = StockUniverseSource.DEFAULT
    custom_tickers: list[str] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def _check_mode_specific_fields(self) -> "RecommendationRequest":
        if self.investment_mode is InvestmentMode.RECURRING and self.recurring_frequency is None:
            raise ValueError("recurring_frequency is required for recurring investments")
        if self.investment_mode is InvestmentMode.ONE_TIME:
            self.recurring_frequency = None
        if self.universe_source is StockUniverseSource.CUSTOM:
            if self.asset_mix is AssetMix.MUTUAL_FUNDS:
                raise ValueError("custom lists are for stocks; add funds to your watchlist instead")
            if not self.custom_tickers:
                raise ValueError("custom_tickers must list at least one ticker")
        return self

    @property
    def includes_stocks(self) -> bool:
        return self.asset_mix in (AssetMix.STOCKS, AssetMix.MIXED)

    @property
    def includes_funds(self) -> bool:
        return self.asset_mix in (AssetMix.MUTUAL_FUNDS, AssetMix.MIXED)


class PortfolioAllocation(BaseModel):
    ticker: str = Field(description='Stock ticker ("TCS.NS") or fund symbol ("MF:122639")')
    asset_type: AssetType = AssetType.STOCK
    display_name: str | None = Field(default=None, description='Short label, e.g. "TCS" or "Parag Parikh Flexi Cap"')
    company_name: str = Field(description="Company name, or the full scheme name for a fund")
    sector: str | None = Field(default=None, description="Sector for stocks, category for funds")
    weight_percent: float
    amount: float = Field(description="INR for this one-time investment, or for this period if recurring")
    last_price: float = Field(description="Share price, or NAV for a fund")
    approx_whole_shares: int = Field(description="Whole shares the amount buys (0 for funds)")
    approx_units: float | None = Field(default=None, description="Fund units the amount buys (funds only)")
    rationale: str


class CandidateSummary(BaseModel):
    ticker: str
    asset_type: AssetType = AssetType.STOCK
    display_name: str | None = None
    company_name: str
    sector: str | None = None
    last_price: float
    return_1y_percent: float | None = None
    cagr_3y_percent: float | None = None
    annualized_volatility_percent: float | None = None
    trailing_pe: float | None = None
    score: CandidateScore | FundScore
    headlines: list[NewsHeadline] = []
    was_picked: bool


class RecommendationResponse(BaseModel):
    id: int
    created_at: UtcDatetime
    investment_mode: InvestmentMode
    recurring_frequency: RecurringFrequency | None
    amount: float
    risk_level: int
    provider_id: ProviderId
    model_name: str
    asset_mix: AssetMix = AssetMix.STOCKS
    allocations: list[PortfolioAllocation]
    summary: str
    risk_notes: list[str]
    candidates_considered: list[CandidateSummary]
    skipped_tickers: dict[str, str] = Field(default_factory=dict, description="ticker -> why it was skipped")
    disclaimer: str = RECOMMENDATION_DISCLAIMER


class RecommendationHistoryItem(BaseModel):
    id: int
    created_at: UtcDatetime
    investment_mode: InvestmentMode
    recurring_frequency: RecurringFrequency | None
    amount: float
    risk_level: int
    provider_id: ProviderId
    model_name: str
    asset_mix: AssetMix = AssetMix.STOCKS
    picked_tickers: list[str]
    picked_labels: list[str] = Field(default_factory=list)


class HoldingPerformance(BaseModel):
    ticker: str
    display_name: str
    asset_type: AssetType
    weight_percent: float
    price_then: float = Field(description="Share price / NAV when the recommendation was made")
    price_now: float | None = Field(description="Latest close / NAV; None if it couldn't be fetched")
    change_percent: float | None


class RecommendationPerformance(BaseModel):
    """How the recommended split has moved since it was made (prices only, before costs and taxes)."""

    recommendation_id: int
    created_at: UtcDatetime
    checked_at: UtcDatetime
    holdings: list[HoldingPerformance]
    portfolio_change_percent: float | None = Field(description="Weighted by the recommended split")
    amount: float
    value_now: float | None = Field(description="What `amount` invested in this split would be worth now")
