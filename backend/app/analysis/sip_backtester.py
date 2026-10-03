"""Replay a real past SIP, month by month, at actual historical NAVs.

On each instalment date we buy units at that day's NAV (the first NAV on or
after the date, as a fund house would), split across the chosen funds. The
holding is valued at the latest NAV, and the return is the XIRR — the yearly
rate that accounts for each rupee's actual time invested.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

FIXED_DEPOSIT_RATE_PERCENT = 7.0


@dataclass
class FundLeg:
    key: str
    weight: float  # fraction, legs sum to 1
    navs: pd.Series  # daily NAVs indexed by date, oldest first
    scheme_code: int = 0
    scheme_name: str = ""


@dataclass
class LegResult:
    key: str
    invested: float
    units: float
    latest_nav: float
    value: float
    cash_flows: list[tuple[date, float]]


@dataclass
class BacktestResult:
    instalment_dates: list[pd.Timestamp]
    end_date: pd.Timestamp
    total_invested: float
    final_value: float
    timeline: list[tuple[pd.Timestamp, float, float]]  # (date, invested so far, value)
    legs: list[LegResult]
    cash_flows: list[tuple[date, float]]


def instalment_schedule(end_date: pd.Timestamp, years: int) -> list[pd.Timestamp]:
    """Monthly dates going back `years` from the month after (end − years), ending at or before `end_date`."""
    first = (end_date - pd.DateOffset(years=years)) + pd.DateOffset(months=1)
    dates = pd.date_range(first.normalize(), end_date.normalize(), freq=pd.DateOffset(months=1))
    return list(dates)


def nav_on_or_after(navs: pd.Series, when: pd.Timestamp) -> tuple[pd.Timestamp, float] | None:
    position = navs.index.searchsorted(when, side="left")
    if position >= len(navs):
        return None
    return navs.index[position], float(navs.iloc[position])


def run_sip_backtest(legs: list[FundLeg], monthly_amount: float, years: int, annual_step_up_percent: float) -> BacktestResult:
    end_date = min(leg.navs.index[-1] for leg in legs)
    earliest_needed = end_date - pd.DateOffset(years=years)
    for leg in legs:
        if leg.navs.index[0] > earliest_needed + pd.Timedelta(days=31):
            available = (end_date - leg.navs.index[0]).days / 365.25
            raise ValueError(f"{leg.key} only has {available:.1f} years of NAV history")

    schedule = instalment_schedule(end_date, years)
    units = {leg.key: 0.0 for leg in legs}
    invested = {leg.key: 0.0 for leg in legs}
    flows: dict[str, list[tuple[date, float]]] = {leg.key: [] for leg in legs}
    timeline: list[tuple[pd.Timestamp, float, float]] = []
    portfolio_flows: list[tuple[date, float]] = []

    for i, when in enumerate(schedule):
        amount = monthly_amount * (1 + annual_step_up_percent / 100) ** (i // 12)
        trade_day = when
        for leg in legs:
            priced = nav_on_or_after(leg.navs, when)
            if priced is None:
                continue
            trade_day, nav = priced
            leg_amount = amount * leg.weight
            units[leg.key] += leg_amount / nav
            invested[leg.key] += leg_amount
            flows[leg.key].append((trade_day.date(), -leg_amount))
        portfolio_flows.append((trade_day.date(), -amount))
        value_now = sum(units[leg.key] * float(leg.navs.asof(trade_day)) for leg in legs)
        timeline.append((trade_day, sum(invested.values()), value_now))

    leg_results: list[LegResult] = []
    for leg in legs:
        latest_nav = float(leg.navs.asof(end_date))
        value = units[leg.key] * latest_nav
        leg_results.append(
            LegResult(
                key=leg.key,
                invested=invested[leg.key],
                units=units[leg.key],
                latest_nav=latest_nav,
                value=value,
                cash_flows=flows[leg.key] + [(end_date.date(), value)],
            )
        )

    final_value = sum(r.value for r in leg_results)
    timeline.append((end_date, sum(invested.values()), final_value))
    return BacktestResult(
        instalment_dates=schedule,
        end_date=end_date,
        total_invested=sum(invested.values()),
        final_value=final_value,
        timeline=timeline,
        legs=leg_results,
        cash_flows=portfolio_flows + [(end_date.date(), final_value)],
    )


def xirr(cash_flows: list[tuple[date, float]]) -> float | None:
    """Annualised internal rate of return for dated cash flows (outflows negative), as a fraction."""
    if len(cash_flows) < 2 or not any(cf < 0 for _, cf in cash_flows) or not any(cf > 0 for _, cf in cash_flows):
        return None
    start = cash_flows[0][0]
    years = np.array([(d - start).days / 365.0 for d, _ in cash_flows])
    amounts = np.array([cf for _, cf in cash_flows])

    def npv(rate: float) -> float:
        return float(np.sum(amounts / (1 + rate) ** years))

    low, high = -0.99, 10.0
    if npv(low) * npv(high) > 0:
        return None
    for _ in range(200):  # bisection: slow but can't diverge
        mid = (low + high) / 2
        if npv(low) * npv(mid) <= 0:
            high = mid
        else:
            low = mid
        if high - low < 1e-9:
            break
    return (low + high) / 2


def fixed_deposit_value(cash_flows: list[tuple[date, float]], end: date, rate_percent: float = FIXED_DEPOSIT_RATE_PERCENT) -> float:
    """What the same instalments would be worth in an FD compounding yearly at `rate_percent`."""
    return sum(-cf * (1 + rate_percent / 100) ** ((end - d).days / 365.0) for d, cf in cash_flows if cf < 0)


def worst_drawdown_percent(values: list[float]) -> float:
    series = pd.Series(values, dtype=float)
    peaks = series.cummax()
    return float(((series / peaks) - 1).min() * 100) if not series.empty else 0.0
