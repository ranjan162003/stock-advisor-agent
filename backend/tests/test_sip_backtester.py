from datetime import date

import pandas as pd
import pytest

from app.analysis.sip_backtester import (
    FundLeg,
    fixed_deposit_value,
    instalment_schedule,
    run_sip_backtest,
    worst_drawdown_percent,
    xirr,
)


def growing_navs(start: str, end: str, annual_growth: float, start_nav: float = 10.0) -> pd.Series:
    dates = pd.date_range(start, end, freq="D")
    days = (dates - dates[0]).days.to_numpy()
    return pd.Series(start_nav * (1 + annual_growth) ** (days / 365.0), index=dates)


def test_xirr_of_a_simple_one_year_investment():
    assert xirr([(date(2020, 1, 1), -100.0), (date(2021, 1, 1), 112.0)]) == pytest.approx(0.1197, abs=1e-3)


def test_xirr_needs_both_signs():
    assert xirr([(date(2020, 1, 1), -100.0)]) is None


def test_schedule_has_one_instalment_per_month():
    schedule = instalment_schedule(pd.Timestamp("2026-10-01"), years=10)
    assert len(schedule) == 120
    assert schedule[-1] == pd.Timestamp("2026-10-01")


def test_flat_nav_returns_exactly_what_was_invested():
    navs = pd.Series(25.0, index=pd.date_range("2015-01-01", "2026-10-01", freq="D"))
    result = run_sip_backtest([FundLeg("Flat", 1.0, navs)], monthly_amount=1000, years=5, annual_step_up_percent=0)
    assert result.total_invested == pytest.approx(60_000)
    assert result.final_value == pytest.approx(60_000)
    assert xirr(result.cash_flows) == pytest.approx(0.0, abs=1e-6)


def test_steady_growth_fund_has_xirr_equal_to_its_growth_rate():
    navs = growing_navs("2014-01-01", "2026-10-01", annual_growth=0.12)
    result = run_sip_backtest([FundLeg("Steady", 1.0, navs)], monthly_amount=10_000, years=10, annual_step_up_percent=0)
    assert result.total_invested == pytest.approx(1_200_000)
    assert xirr(result.cash_flows) == pytest.approx(0.12, abs=0.002)
    assert result.final_value > result.total_invested


def test_split_across_two_funds_and_step_up():
    a = growing_navs("2014-01-01", "2026-10-01", 0.10)
    b = growing_navs("2014-01-01", "2026-10-01", 0.06)
    result = run_sip_backtest(
        [FundLeg("A", 0.6, a), FundLeg("B", 0.4, b)], monthly_amount=1000, years=2, annual_step_up_percent=10
    )
    by_key = {leg.key: leg for leg in result.legs}
    assert result.total_invested == pytest.approx(12 * 1000 + 12 * 1100)
    assert by_key["A"].invested == pytest.approx(result.total_invested * 0.6)


def test_too_little_history_is_rejected():
    navs = growing_navs("2023-01-01", "2026-10-01", 0.1)
    with pytest.raises(ValueError, match="years of NAV history"):
        run_sip_backtest([FundLeg("New fund", 1.0, navs)], monthly_amount=1000, years=10, annual_step_up_percent=0)


def test_fixed_deposit_and_drawdown_helpers():
    flows = [(date(2020, 1, 1), -1000.0), (date(2021, 1, 1), 0.0)]
    assert fixed_deposit_value(flows, date(2021, 1, 1), rate_percent=7) == pytest.approx(1070, abs=0.5)
    assert worst_drawdown_percent([100, 120, 90, 130]) == pytest.approx(-25.0)
