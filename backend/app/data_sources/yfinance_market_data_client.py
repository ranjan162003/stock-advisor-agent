"""Price history and company fundamentals from Yahoo Finance (free, no API key)."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_closing_price_history(tickers: list[str], period: str) -> dict[str, pd.Series]:
    """Download adjusted daily closes for all tickers in one batched request.

    Tickers with no data (delisted, typo, wrong suffix) are simply absent from
    the result — callers report them as skipped.
    """
    if not tickers:
        return {}
    frame = yf.download(
        tickers,
        period=period,
        interval="1d",
        auto_adjust=True,
        group_by="ticker",
        threads=True,
        progress=False,
    )
    if frame is None or frame.empty:
        return {}

    closes: dict[str, pd.Series] = {}
    for ticker in tickers:
        try:
            series = frame[ticker]["Close"] if isinstance(frame.columns, pd.MultiIndex) else frame["Close"]
        except KeyError:
            continue
        series = series.dropna()
        if len(series) >= 20:  # too little history makes every indicator meaningless
            closes[ticker] = series
    return closes


def fetch_company_profile(ticker: str) -> dict[str, Any]:
    """Return Yahoo's `info` dict (name, sector, valuation and balance-sheet ratios).

    Yahoo occasionally rate-limits or omits this; an empty dict is a valid
    "no fundamentals available" answer, not an error.
    """
    try:
        return yf.Ticker(ticker).info or {}
    except Exception as exc:  # yfinance raises a wide variety of transport/parse errors
        logger.warning("Fundamentals unavailable for %s: %s", ticker, exc)
        return {}
