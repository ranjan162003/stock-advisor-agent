"""'Since this recommendation': then-vs-now prices, weighted into one portfolio change."""
from datetime import datetime, timezone
from types import SimpleNamespace

from app.analysis.fund_snapshot_builder import FundSnapshotBuildResult
from app.analysis.stock_snapshot_builder import SnapshotBuildResult
from app.schemas.recommendation_schemas import (
    AssetType,
    InvestmentMode,
    PortfolioAllocation,
    RecommendationResponse,
)
from app.schemas.provider_schemas import ProviderId
from app.services import recommendation_performance_service as service


def allocation(ticker: str, weight: float, price: float, asset_type=AssetType.STOCK) -> PortfolioAllocation:
    return PortfolioAllocation(
        ticker=ticker, asset_type=asset_type, display_name=ticker, company_name=ticker, weight_percent=weight,
        amount=weight * 100, last_price=price, approx_whole_shares=0, rationale="",
    )


def test_performance_weights_each_holding_and_tolerates_missing_prices(monkeypatch):
    rec = RecommendationResponse(
        id=1, created_at=datetime(2026, 9, 1, tzinfo=timezone.utc), investment_mode=InvestmentMode.ONE_TIME,
        recurring_frequency=None, amount=10_000, risk_level=3, provider_id=ProviderId.CLAUDE, model_name="m",
        allocations=[
            allocation("TCS.NS", 50, 100.0),  # +10%
            allocation("MF:122639", 30, 50.0, AssetType.MUTUAL_FUND),  # -5%
            allocation("GONE.NS", 20, 10.0),  # no price today -> left out of the average
        ],
        summary="", risk_notes=[], candidates_considered=[],
    )
    monkeypatch.setattr(service, "get_recommendation_detail", lambda session, record_id: rec)
    monkeypatch.setattr(
        service, "build_stock_snapshots",
        lambda session, tickers, settings: SnapshotBuildResult(
            snapshots=[SimpleNamespace(ticker="TCS.NS", technicals=SimpleNamespace(last_close=110.0))]
        ),
    )
    monkeypatch.setattr(
        service, "build_fund_snapshots",
        lambda session, codes, settings: FundSnapshotBuildResult(
            snapshots=[SimpleNamespace(symbol="MF:122639", metrics=SimpleNamespace(latest_nav=47.5))]
        ),
    )

    result = service.get_recommendation_performance(session=None, record_id=1)

    changes = {h.ticker: h.change_percent for h in result.holdings}
    assert changes == {"TCS.NS": 10.0, "MF:122639": -5.0, "GONE.NS": None}
    # (50 * 10 + 30 * -5) / 80 = 4.375
    assert result.portfolio_change_percent == 4.38
    assert result.value_now == 10_438.0
