"""Turn Yahoo Finance's loosely-typed `info` dict into clean `FundamentalMetrics`."""
from __future__ import annotations

import math
from typing import Any

from app.schemas.market_data_schemas import FundamentalMetrics


def extract_fundamental_metrics(company_profile: dict[str, Any]) -> FundamentalMetrics:
    debt_to_equity_percent = _number(company_profile.get("debtToEquity"))
    return FundamentalMetrics(
        market_cap=_number(company_profile.get("marketCap")),
        trailing_pe=_positive_or_none(_number(company_profile.get("trailingPE"))),
        forward_pe=_positive_or_none(_number(company_profile.get("forwardPE"))),
        price_to_book=_number(company_profile.get("priceToBook")),
        earnings_growth_percent=_fraction_to_percent(company_profile.get("earningsGrowth")),
        revenue_growth_percent=_fraction_to_percent(company_profile.get("revenueGrowth")),
        profit_margin_percent=_fraction_to_percent(company_profile.get("profitMargins")),
        return_on_equity_percent=_fraction_to_percent(company_profile.get("returnOnEquity")),
        # Yahoo reports D/E as a percentage (45.0 == 0.45x); store the plain ratio.
        debt_to_equity=round(debt_to_equity_percent / 100, 2) if debt_to_equity_percent is not None else None,
        # `trailingAnnualDividendYield` is consistently a fraction, unlike `dividendYield`.
        dividend_yield_percent=_fraction_to_percent(company_profile.get("trailingAnnualDividendYield")),
        beta=_number(company_profile.get("beta")),
    )


def company_display_name(company_profile: dict[str, Any], fallback: str) -> str:
    return company_profile.get("longName") or company_profile.get("shortName") or fallback


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return round(float(value), 4)


def _fraction_to_percent(value: Any) -> float | None:
    number = _number(value)
    return round(number * 100, 2) if number is not None else None


def _positive_or_none(value: float | None) -> float | None:
    # Negative P/E (loss-making company) isn't a meaningful valuation multiple.
    return value if value is not None and value > 0 else None
