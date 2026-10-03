from datetime import datetime, timezone

from app.analysis.candidate_scoring import scale_to_score, score_candidate, shortlist_candidates
from app.schemas.market_data_schemas import FundamentalMetrics, StockSnapshot, TechnicalIndicators


def make_snapshot(ticker: str, sector: str, volatility: float, return_6m: float) -> StockSnapshot:
    return StockSnapshot(
        ticker=ticker,
        company_name=ticker,
        sector=sector,
        technicals=TechnicalIndicators(
            last_close=100, annualized_volatility_percent=volatility, return_6m_percent=return_6m
        ),
        fundamentals=FundamentalMetrics(trailing_pe=20, return_on_equity_percent=18),
        fetched_at=datetime.now(timezone.utc),
    )


def test_scale_to_score_clamps_and_supports_inverted_ranges():
    assert scale_to_score(5, 0, 10) == 50
    assert scale_to_score(50, 0, 10) == 100
    assert scale_to_score(0, 10, 0) == 100  # lower is better


def test_low_volatility_stock_fits_a_conservative_investor_better():
    calm = make_snapshot("CALM", "FMCG", volatility=16, return_6m=5)
    wild = make_snapshot("WILD", "Tech", volatility=55, return_6m=5)
    assert score_candidate(calm, risk_level=1).risk_fit_score > score_candidate(wild, risk_level=1).risk_fit_score


def test_shortlist_caps_each_sector():
    snapshots = [make_snapshot(f"BANK{i}", "Banking", 25, 10 + i) for i in range(5)]
    snapshots.append(make_snapshot("ITC", "FMCG", 25, 0))
    shortlisted = shortlist_candidates(snapshots, risk_level=3, limit=10)
    sectors = [c.snapshot.sector for c in shortlisted]
    assert sectors.count("Banking") == 3
    assert "FMCG" in sectors
