import numpy as np
import pytest

from app.analysis.sip_simulator import (
    annualized_stats,
    bootstrap_monthly_returns,
    lognormal_monthly_returns,
    monthly_contributions,
    probability_at_least,
    required_monthly_amount,
    simulate_sip,
)


def test_zero_return_sip_is_just_the_sum_invested():
    returns = np.zeros((5, 24))
    result = simulate_sip(returns, monthly_amount=1000, annual_step_up_percent=0)
    assert result.total_invested == 24_000
    assert result.yearly[-1].p50 == pytest.approx(24_000)
    assert [p.year for p in result.yearly] == [1, 2]


def test_constant_return_matches_future_value_of_an_annuity_due():
    monthly_rate = 0.01
    returns = np.full((3, 120), monthly_rate)
    result = simulate_sip(returns, monthly_amount=10_000, annual_step_up_percent=0)
    expected = 10_000 * ((1 + monthly_rate) ** 120 - 1) / monthly_rate * (1 + monthly_rate)
    assert result.yearly[-1].p50 == pytest.approx(expected, rel=1e-9)


def test_step_up_raises_the_sip_once_a_year():
    contributions = monthly_contributions(1000, 36, annual_step_up_percent=10)
    assert contributions[0] == 1000 and contributions[11] == 1000
    assert contributions[12] == pytest.approx(1100)
    assert contributions[24] == pytest.approx(1210)


def test_percentiles_are_ordered():
    rng = np.random.default_rng(1)
    returns = lognormal_monthly_returns(12, 18, months=120, n_paths=2000, rng=rng)
    result = simulate_sip(returns, 5000, 0)
    for point in result.yearly:
        assert point.p10 <= point.p50 <= point.p90


def test_bootstrap_only_uses_historical_months():
    history = np.array([0.01, -0.02, 0.03, 0.0, 0.05, -0.01, 0.02, 0.01, 0.0, -0.03, 0.04, 0.02])
    sampled = bootstrap_monthly_returns(history, months=30, n_paths=50, rng=np.random.default_rng(3))
    assert sampled.shape == (50, 30)
    assert set(np.unique(sampled)) <= set(history)


def test_lognormal_returns_hit_the_requested_average():
    returns = lognormal_monthly_returns(12, 15, months=600, n_paths=2000, rng=np.random.default_rng(5))
    cagr, volatility = annualized_stats(returns.reshape(-1))
    assert cagr == pytest.approx(12, abs=0.5)
    assert volatility == pytest.approx(15, abs=0.5)


def test_goal_helpers():
    finals = np.array([80.0, 100.0, 120.0, 140.0, 160.0])
    assert probability_at_least(finals, 120) == 60.0
    # Value scales linearly with the SIP amount, so doubling the goal doubles the required SIP.
    assert required_monthly_amount(finals, 1000, goal=240, confidence=0.5) == pytest.approx(2000)
