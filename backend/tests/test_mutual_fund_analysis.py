from datetime import datetime, timezone

import pandas as pd
import pytest

from app.analysis.fund_metrics import cagr_percent, compute_fund_metrics, is_nav_stale
from app.analysis.fund_scoring import score_fund, shortlist_funds
from app.data_sources.default_fund_universe import (
    fund_symbol,
    infer_fund_risk_class,
    is_fund_symbol,
    scheme_code_from_symbol,
    short_fund_name,
)
from app.data_sources.mfapi_mutual_fund_client import is_direct_growth_plan
from app.schemas.mutual_fund_schemas import FundMetrics, FundSnapshot


def daily_navs(years: float, annual_growth: float) -> pd.Series:
    dates = pd.date_range(end="2026-10-01", periods=int(years * 365) + 1, freq="D")
    daily_rate = (1 + annual_growth) ** (1 / 365) - 1
    return pd.Series([100 * (1 + daily_rate) ** i for i in range(len(dates))], index=dates)


def make_fund(code: int, risk_class: int, category: str, cagr_3y: float, drawdown: float) -> FundSnapshot:
    return FundSnapshot(
        symbol=fund_symbol(code),
        scheme_code=code,
        scheme_name=f"Fund {code} - Direct Plan - Growth",
        short_name=f"Fund {code}",
        category=category,
        risk_class=risk_class,
        metrics=FundMetrics(
            latest_nav=50,
            nav_date="2026-10-01",
            history_years=6,
            return_1y_percent=cagr_3y,
            cagr_3y_percent=cagr_3y,
            annualized_volatility_percent=12,
            max_drawdown_3y_percent=drawdown,
            sharpe_ratio_3y=0.8,
        ),
        fetched_at=datetime.now(timezone.utc),
    )


def test_cagr_matches_a_constant_growth_rate():
    navs = daily_navs(years=6, annual_growth=0.12)
    assert cagr_percent(navs, 3) == pytest.approx(12.0, abs=0.1)
    assert cagr_percent(navs, 5) == pytest.approx(12.0, abs=0.1)


def test_cagr_is_none_when_history_is_too_short():
    assert cagr_percent(daily_navs(years=2, annual_growth=0.1), 3) is None


def test_compute_fund_metrics_on_steady_growth():
    metrics = compute_fund_metrics(daily_navs(years=6, annual_growth=0.10))
    assert metrics.cagr_3y_percent == pytest.approx(10.0, abs=0.1)
    assert metrics.max_drawdown_3y_percent == pytest.approx(0.0, abs=1e-6)
    assert metrics.history_years == pytest.approx(6.0, abs=0.1)


def test_stale_nav_is_detected():
    navs = daily_navs(years=1, annual_growth=0.05)
    assert is_nav_stale(navs, today=pd.Timestamp("2026-12-31"))
    assert not is_nav_stale(navs, today=pd.Timestamp("2026-10-05"))


@pytest.mark.parametrize(
    ("category", "name", "expected"),
    [
        ("Debt Scheme - Liquid Fund", "SBI Liquid Fund", 1),
        ("Debt Scheme - Corporate Bond Fund", "HDFC Corporate Bond Fund", 1),
        ("Hybrid Scheme - Balanced Advantage", "HDFC Balanced Advantage Fund", 2),
        ("Equity Scheme - Large Cap Fund", "Nippon India Large Cap Fund", 3),
        ("Other Scheme - Index Funds", "UTI Nifty 50 Index Fund", 3),
        ("Equity Scheme - Mid Cap Fund", "HDFC Mid Cap Fund", 4),
        ("Equity Scheme - Small Cap Fund", "SBI Small Cap Fund", 5),
    ],
)
def test_risk_class_inference(category, name, expected):
    assert infer_fund_risk_class(category, name) == expected


def test_fund_symbols_and_names():
    assert fund_symbol(122639) == "MF:122639"
    assert is_fund_symbol("MF:122639") and not is_fund_symbol("TCS.NS")
    assert scheme_code_from_symbol("MF:122639") == 122639
    assert short_fund_name("Parag Parikh Flexi Cap Fund - Direct Plan - Growth") == "Parag Parikh Flexi Cap"
    assert is_direct_growth_plan("HDFC Mid Cap Fund - Direct Plan - Growth Option")
    assert not is_direct_growth_plan("HDFC Mid Cap Fund - Direct Plan - IDCW")
    assert not is_direct_growth_plan("HDFC Mid Cap Fund - Regular Plan - Growth")


def test_conservative_investor_prefers_debt_over_small_cap():
    debt = make_fund(1, risk_class=1, category="Debt", cagr_3y=7, drawdown=-1)
    small_cap = make_fund(2, risk_class=5, category="Small cap", cagr_3y=22, drawdown=-30)
    assert score_fund(debt, risk_level=1).total_score > score_fund(small_cap, risk_level=1).total_score
    assert score_fund(small_cap, risk_level=5).total_score > score_fund(debt, risk_level=5).total_score


def test_fund_shortlist_caps_each_category():
    funds = [make_fund(i, risk_class=3, category="Flexi cap", cagr_3y=15 + i, drawdown=-10) for i in range(4)]
    funds.append(make_fund(99, risk_class=3, category="Large cap", cagr_3y=10, drawdown=-10))
    categories = [c.snapshot.category for c in shortlist_funds(funds, risk_level=3, limit=10)]
    assert categories.count("Flexi cap") == 2
    assert "Large cap" in categories
