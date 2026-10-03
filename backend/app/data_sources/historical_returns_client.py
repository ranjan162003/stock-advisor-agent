"""Monthly return series from a fund's daily NAVs, for SIP projections.

Indexed by calendar month (`pd.Period`, freq "M") so several funds line up exactly.
"""
from __future__ import annotations

import pandas as pd

HISTORY_YEARS = 10


def monthly_returns_from_navs(navs: pd.Series, years: int = HISTORY_YEARS) -> pd.Series:
    """Month-end to month-end returns from daily NAVs, indexed by calendar month."""
    month_end_navs = navs.resample("ME").last().dropna()
    month_end_navs.index = month_end_navs.index.to_period("M")
    series = month_end_navs.pct_change().dropna().iloc[:-1]  # drop the still-open month
    return series.iloc[-years * 12:]
