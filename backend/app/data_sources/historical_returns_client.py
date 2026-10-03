"""Long-run monthly return series for stocks (Yahoo) and mutual funds (mfapi.in).

Used by the SIP planner to replay real historical months. Series are indexed by
calendar month (`pd.Period`, freq "M") so stocks and funds line up exactly.
"""
from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

from app.data_sources.mfapi_mutual_fund_client import fetch_fund_nav_history

logger = logging.getLogger(__name__)

HISTORY_YEARS = 10


def fetch_stock_monthly_returns(tickers: list[str], years: int = HISTORY_YEARS) -> dict[str, pd.Series]:
    if not tickers:
        return {}
    frame = yf.download(
        tickers,
        period=f"{years}y",
        interval="1mo",
        auto_adjust=True,
        group_by="ticker",
        threads=True,
        progress=False,
    )
    if frame is None or frame.empty:
        return {}
    returns: dict[str, pd.Series] = {}
    for ticker in tickers:
        try:
            closes = frame[ticker]["Close"] if isinstance(frame.columns, pd.MultiIndex) else frame["Close"]
        except KeyError:
            continue
        closes = closes.dropna()
        if len(closes) < 13:
            continue
        closes.index = pd.DatetimeIndex(closes.index).to_period("M")
        # The current, still-open month would be a partial return; drop it.
        series = closes.pct_change().dropna().iloc[:-1]
        returns[ticker] = series[~series.index.duplicated(keep="last")]
    return returns


def fetch_fund_monthly_returns(scheme_code: int, years: int = HISTORY_YEARS) -> pd.Series | None:
    history = fetch_fund_nav_history(scheme_code)
    if history is None:
        return None
    return monthly_returns_from_navs(history.navs, years)


def monthly_returns_from_navs(navs: pd.Series, years: int = HISTORY_YEARS) -> pd.Series:
    """Month-end to month-end returns from daily NAVs, indexed by calendar month."""
    month_end_navs = navs.resample("ME").last().dropna()
    month_end_navs.index = month_end_navs.index.to_period("M")
    series = month_end_navs.pct_change().dropna().iloc[:-1]  # drop the still-open month
    return series.iloc[-years * 12:]
