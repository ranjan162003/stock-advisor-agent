"""Monte Carlo projection of a monthly SIP.

Two ways to generate future monthly returns:

* **Historical bootstrap** — replay randomly chosen 12-month blocks of the
  portfolio's *real* past monthly returns. Blocks keep realistic streaks (a bad
  year stays a bad year) instead of shuffling single months.
* **Assumed return** — log-normal months with a chosen yearly return and
  volatility, for when there's no portfolio history to replay.

Each path invests at the start of every month, optionally stepping the SIP up
once a year. Results are summarised as percentiles, so the user sees a range
(bad / typical / good) rather than one falsely precise number.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

DEFAULT_PATHS = 4000
BOOTSTRAP_BLOCK_MONTHS = 12
PERCENTILES = (10, 50, 90)


@dataclass
class YearlyProjection:
    year: int
    invested: float
    p10: float
    p50: float
    p90: float


@dataclass
class SipSimulation:
    yearly: list[YearlyProjection]
    final_values: np.ndarray  # one per path
    total_invested: float


def bootstrap_monthly_returns(
    history: np.ndarray, months: int, n_paths: int, rng: np.random.Generator, block: int = BOOTSTRAP_BLOCK_MONTHS
) -> np.ndarray:
    """(n_paths, months) matrix of returns built from random contiguous blocks of `history`."""
    if history.size < block:
        raise ValueError("Need at least one full block of history to bootstrap.")
    n_blocks = math.ceil(months / block)
    starts = rng.integers(0, history.size, size=(n_paths, n_blocks))
    indices = (starts[..., None] + np.arange(block)) % history.size  # wrap around the end
    return history[indices.reshape(n_paths, n_blocks * block)[:, :months]]


def lognormal_monthly_returns(
    annual_return_percent: float, annual_volatility_percent: float, months: int, n_paths: int, rng: np.random.Generator
) -> np.ndarray:
    # `annual_return_percent` is a compound (CAGR-style) rate, the way fund returns are quoted,
    # so the median path grows at exactly that rate; volatility then spreads paths around it.
    sigma = annual_volatility_percent / 100 / math.sqrt(12)
    mu = math.log(1 + annual_return_percent / 100) / 12
    return np.exp(rng.normal(mu, sigma, size=(n_paths, months))) - 1


def monthly_contributions(monthly_amount: float, months: int, annual_step_up_percent: float) -> np.ndarray:
    years_elapsed = np.arange(months) // 12
    return monthly_amount * (1 + annual_step_up_percent / 100) ** years_elapsed


def simulate_sip(returns: np.ndarray, monthly_amount: float, annual_step_up_percent: float) -> SipSimulation:
    n_paths, months = returns.shape
    contributions = monthly_contributions(monthly_amount, months, annual_step_up_percent)
    values = np.zeros(n_paths)
    yearly: list[YearlyProjection] = []
    for month in range(months):
        values = (values + contributions[month]) * (1 + returns[:, month])
        if (month + 1) % 12 == 0 or month == months - 1:
            low, mid, high = np.percentile(values, PERCENTILES)
            yearly.append(
                YearlyProjection(
                    year=math.ceil((month + 1) / 12),
                    invested=float(contributions[: month + 1].sum()),
                    p10=float(low),
                    p50=float(mid),
                    p90=float(high),
                )
            )
    return SipSimulation(yearly=yearly, final_values=values, total_invested=float(contributions.sum()))


def probability_at_least(final_values: np.ndarray, target: float) -> float:
    return float((final_values >= target).mean() * 100)


def required_monthly_amount(final_values: np.ndarray, monthly_amount: float, goal: float, confidence: float) -> float:
    """SIP needed to reach `goal` in `confidence` of paths.

    Final value scales linearly with the SIP amount (same returns, same step-up),
    so we rescale the path value at the matching low percentile.
    """
    value_at_confidence = float(np.percentile(final_values, (1 - confidence) * 100))
    return monthly_amount * goal / value_at_confidence if value_at_confidence > 0 else float("inf")


def annualized_stats(monthly_returns: np.ndarray) -> tuple[float, float]:
    """(compound annual return %, annualized volatility %) of a monthly return series."""
    # Average log growth avoids overflow when multiplying many months together.
    cagr = (math.exp(12 * float(np.mean(np.log1p(monthly_returns)))) - 1) * 100
    volatility = float(np.std(monthly_returns, ddof=1) * math.sqrt(12) * 100)
    return cagr, volatility
