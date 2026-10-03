"""Portfolio rebalancing request/response contracts."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.recommendation_schemas import AssetType


class HoldingInput(BaseModel):
    symbol: str = Field(min_length=1, max_length=40, description='Stock ticker ("TCS" / "TCS.NS") or fund symbol ("MF:122639")')
    quantity: float = Field(gt=0, description="Shares for stocks, units for funds")


class RebalanceRequest(BaseModel):
    recommendation_id: int
    holdings: list[HoldingInput] = Field(default_factory=list, max_length=100)
    additional_cash: float = Field(default=0, ge=0, le=1_000_000_000)
    allow_selling: bool = True


class TradeAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class RebalanceLine(BaseModel):
    ticker: str
    asset_type: AssetType
    display_name: str
    price: float
    current_quantity: float
    current_value: float
    current_weight_percent: float
    target_weight_percent: float
    action: TradeAction
    trade_quantity: float = Field(description="Whole shares for stocks, units (3 decimals) for funds")
    trade_value: float
    after_value: float
    after_weight_percent: float
    note: str | None = None


class RebalanceResponse(BaseModel):
    recommendation_id: int
    allow_selling: bool
    current_value: float
    additional_cash: float
    total_buy: float
    total_sell: float
    cash_left_over: float
    value_after: float
    drift_before_percent: float = Field(description="Half the sum of |current − target| weights")
    drift_after_percent: float
    lines: list[RebalanceLine]
    unpriced_holdings: dict[str, str] = Field(default_factory=dict)


class HoldingsImportRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200_000, description="CSV / TSV pasted from a broker holdings export")


class ParsedHolding(BaseModel):
    input_text: str
    symbol: str | None
    display_name: str | None
    asset_type: AssetType | None
    quantity: float | None
    matched: bool
    note: str | None = None


class HoldingsImportResponse(BaseModel):
    holdings: list[ParsedHolding]
    detected_columns: dict[str, str] = Field(default_factory=dict)
