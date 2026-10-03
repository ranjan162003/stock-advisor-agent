"""Standard technical indicators computed from a daily closing-price series.

All functions are pure (Series in, number out) so they're easy to unit-test.
Percent values are returned as percentages (12.5 means 12.5%).
"""
from __future__ import annotations

import math

import pandas as pd

from app.schemas.market_data_schemas import TechnicalIndicators

TRADING_DAYS_PER_MONTH = 21
TRADING_DAYS_PER_YEAR = 252


def simple_moving_average(closes: pd.Series, window: int) -> float | None:
    if len(closes) < window:
        return None
    return float(closes.iloc[-window:].mean())


def relative_strength_index(closes: pd.Series, period: int = 14) -> float | None:
    """Wilder's RSI (0-100). Above ~70 is conventionally "overbought", below ~30 "oversold"."""
    if len(closes) <= period:
        return None
    deltas = closes.diff().dropna()
    average_gain = deltas.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
    average_loss = (-deltas.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return float(100 - 100 / (1 + relative_strength))


def trailing_return_percent(closes: pd.Series, trading_days: int) -> float | None:
    if len(closes) <= trading_days:
        return None
    start_price = closes.iloc[-trading_days - 1]
    return float((closes.iloc[-1] / start_price - 1) * 100)


def annualized_volatility_percent(closes: pd.Series) -> float | None:
    daily_returns = closes.pct_change().dropna()
    if len(daily_returns) < 20:
        return None
    return float(daily_returns.std() * math.sqrt(TRADING_DAYS_PER_YEAR) * 100)


def max_drawdown_percent(closes: pd.Series) -> float | None:
    """Worst peak-to-trough fall over the series, as a negative percentage."""
    if closes.empty:
        return None
    drawdowns = closes / closes.cummax() - 1
    return float(drawdowns.min() * 100)


def compute_technical_indicators(closes: pd.Series) -> TechnicalIndicators:
    last_close = float(closes.iloc[-1])
    sma_200 = simple_moving_average(closes, 200)
    one_year_days = min(TRADING_DAYS_PER_YEAR, len(closes) - 1)
    return TechnicalIndicators(
        last_close=round(last_close, 2),
        sma_50=_round(simple_moving_average(closes, 50)),
        sma_200=_round(sma_200),
        price_vs_sma_200_percent=_round((last_close / sma_200 - 1) * 100) if sma_200 else None,
        rsi_14=_round(relative_strength_index(closes, 14)),
        return_1m_percent=_round(trailing_return_percent(closes, TRADING_DAYS_PER_MONTH)),
        return_3m_percent=_round(trailing_return_percent(closes, 3 * TRADING_DAYS_PER_MONTH)),
        return_6m_percent=_round(trailing_return_percent(closes, 6 * TRADING_DAYS_PER_MONTH)),
        # A "1y" download is ~248-252 sessions; use whatever full year we have.
        return_1y_percent=_round(trailing_return_percent(closes, one_year_days)) if one_year_days >= 200 else None,
        annualized_volatility_percent=_round(annualized_volatility_percent(closes)),
        max_drawdown_1y_percent=_round(max_drawdown_percent(closes.iloc[-TRADING_DAYS_PER_YEAR:])),
    )


def _round(value: float | None, digits: int = 2) -> float | None:
    if value is None or math.isnan(value) or math.isinf(value):
        return None
    return round(value, digits)
