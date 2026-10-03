"""SIP / goal planner request and response contracts."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ReturnSource(str, Enum):
    FUNDS = "funds"
    PRESET = "preset"


class FundWeight(BaseModel):
    scheme_code: int = Field(gt=0)
    weight_percent: float = Field(gt=0, le=100)


def _validate_fund_split(funds: list[FundWeight]) -> None:
    if not 1 <= len(funds) <= 5:
        raise ValueError("pick between 1 and 5 funds")
    if len({f.scheme_code for f in funds}) != len(funds):
        raise ValueError("each fund can only appear once")
    if abs(sum(f.weight_percent for f in funds) - 100) > 0.5:
        raise ValueError("fund weights must add up to 100%")


class ReturnPreset(str, Enum):
    DEBT = "debt"
    HYBRID = "hybrid"
    LARGE_CAP = "large_cap"
    FLEXI_CAP = "flexi_cap"
    MID_SMALL_CAP = "mid_small_cap"


class ReturnPresetInfo(BaseModel):
    preset: ReturnPreset
    label: str
    annual_return_percent: float
    annual_volatility_percent: float


class SipProjectionRequest(BaseModel):
    monthly_amount: float = Field(gt=0, le=10_000_000)
    years: int = Field(ge=1, le=40)
    annual_step_up_percent: float = Field(default=0, ge=0, le=50)
    goal_amount: float | None = Field(default=None, gt=0)
    return_source: ReturnSource = ReturnSource.PRESET
    preset: ReturnPreset | None = ReturnPreset.FLEXI_CAP
    funds: list[FundWeight] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_source(self) -> "SipProjectionRequest":
        if self.return_source is ReturnSource.PRESET and self.preset is None:
            raise ValueError("preset is required when return_source is 'preset'")
        if self.return_source is ReturnSource.FUNDS:
            _validate_fund_split(self.funds)
        return self


class YearlyProjectionPoint(BaseModel):
    year: int
    invested: float
    bad_case: float = Field(description="10th percentile")
    typical: float = Field(description="Median")
    good_case: float = Field(description="90th percentile")


class SipProjectionResponse(BaseModel):
    monthly_amount: float
    years: int
    annual_step_up_percent: float
    total_invested: float
    bad_case: float
    typical: float
    good_case: float
    chance_of_loss_percent: float = Field(description="Paths ending below the total invested")
    goal_amount: float | None = None
    goal_probability_percent: float | None = None
    required_monthly_for_goal_50: float | None = Field(default=None, description="SIP that reaches the goal in half the paths")
    required_monthly_for_goal_80: float | None = Field(default=None, description="SIP that reaches the goal in 80% of paths")
    yearly: list[YearlyProjectionPoint]
    source_description: str
    basis_annual_return_percent: float
    basis_annual_volatility_percent: float
    history_months: int | None = None
    simulated_paths: int


# ---------- "What would have happened" (historical SIP replay) ----------


class SipBacktestRequest(BaseModel):
    funds: list[FundWeight]
    monthly_amount: float = Field(gt=0, le=10_000_000)
    years: int = Field(ge=1, le=30)
    annual_step_up_percent: float = Field(default=0, ge=0, le=50)

    @model_validator(mode="after")
    def _check_funds(self) -> "SipBacktestRequest":
        _validate_fund_split(self.funds)
        return self


class BacktestPoint(BaseModel):
    date: str
    invested: float
    value: float


class BacktestFundResult(BaseModel):
    scheme_code: int
    short_name: str
    scheme_name: str
    weight_percent: float
    invested: float
    units: float
    latest_nav: float
    value: float
    xirr_percent: float | None


class SipBacktestResponse(BaseModel):
    start_date: str
    end_date: str
    installments: int
    monthly_amount: float
    annual_step_up_percent: float
    total_invested: float
    final_value: float
    gain: float
    absolute_return_percent: float
    xirr_percent: float | None = Field(description="Annualised return accounting for when each SIP went in")
    fixed_deposit_value: float = Field(description="Same SIP in a fixed deposit at FIXED_DEPOSIT_RATE_PERCENT")
    fixed_deposit_rate_percent: float
    worst_drawdown_percent: float = Field(description="Largest fall in portfolio value (incl. new money) along the way")
    timeline: list[BacktestPoint]
    funds: list[BacktestFundResult]
