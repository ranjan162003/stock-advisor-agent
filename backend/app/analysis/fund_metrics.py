"""Performance and risk metrics computed from a fund's daily NAV history."""
from __future__ import annotations

import math

import pandas as pd

from app.analysis.technical_indicators import annualized_volatility_percent, max_drawdown_percent
from app.schemas.mutual_fund_schemas import FundMetrics

# Approximate Indian risk-free rate (T-bill yield), used for the Sharpe ratio.
RISK_FREE_RATE_PERCENT = 6.5
STALE_NAV_DAYS = 30


def cagr_percent(navs: pd.Series, years: float) -> float | None:
    """Compound annual growth rate over the trailing `years`, or None if history is too short."""
    if navs.empty:
        return None
    end_date = navs.index[-1]
    start_date = end_date - pd.DateOffset(days=round(years * 365.25))
    if navs.index[0] > start_date + pd.Timedelta(days=7):
        return None
    start_nav = navs[navs.index <= start_date]
    start_value = start_nav.iloc[-1] if not start_nav.empty else navs.iloc[0]
    return float(((navs.iloc[-1] / start_value) ** (1 / years) - 1) * 100)


def sharpe_ratio(navs: pd.Series, years: float = 3) -> float | None:
    """Annualized excess return per unit of volatility over the trailing window."""
    window = navs[navs.index >= navs.index[-1] - pd.DateOffset(days=round(years * 365.25))]
    cagr = cagr_percent(navs, years)
    volatility = annualized_volatility_percent(window)
    if cagr is None or not volatility:
        return None
    return float((cagr - RISK_FREE_RATE_PERCENT) / volatility)


def compute_fund_metrics(navs: pd.Series) -> FundMetrics:
    three_years = navs[navs.index >= navs.index[-1] - pd.DateOffset(years=3)]
    one_year = navs[navs.index >= navs.index[-1] - pd.DateOffset(years=1)]
    history_years = (navs.index[-1] - navs.index[0]).days / 365.25
    return FundMetrics(
        latest_nav=round(float(navs.iloc[-1]), 4),
        nav_date=navs.index[-1].strftime("%Y-%m-%d"),
        history_years=round(history_years, 1),
        return_1y_percent=_round(cagr_percent(navs, 1)),
        cagr_3y_percent=_round(cagr_percent(navs, 3)),
        cagr_5y_percent=_round(cagr_percent(navs, 5)),
        annualized_volatility_percent=_round(annualized_volatility_percent(one_year)),
        max_drawdown_3y_percent=_round(max_drawdown_percent(three_years)),
        sharpe_ratio_3y=_round(sharpe_ratio(navs, 3)),
    )


def is_nav_stale(navs: pd.Series, today: pd.Timestamp | None = None) -> bool:
    """A fund whose NAV hasn't updated for a month is likely closed or merged."""
    today = today or pd.Timestamp.today().normalize()
    return (today - navs.index[-1]).days > STALE_NAV_DAYS


def _round(value: float | None, digits: int = 2) -> float | None:
    if value is None or math.isnan(value) or math.isinf(value):
        return None
    return round(value, digits)
