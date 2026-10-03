"""How a saved recommendation has done since it was made: then-price vs latest price per holding."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.analysis.fund_snapshot_builder import build_fund_snapshots
from app.analysis.stock_snapshot_builder import build_stock_snapshots
from app.core.app_settings import get_settings
from app.data_sources.default_fund_universe import is_fund_symbol, scheme_code_from_symbol
from app.schemas.recommendation_schemas import HoldingPerformance, RecommendationPerformance
from app.services.recommendation_history_service import get_recommendation_detail


def get_recommendation_performance(session: Session, record_id: int) -> RecommendationPerformance:
    rec = get_recommendation_detail(session, record_id)
    settings = get_settings()

    stock_tickers = [a.ticker for a in rec.allocations if not is_fund_symbol(a.ticker)]
    fund_codes = [scheme_code_from_symbol(a.ticker) for a in rec.allocations if is_fund_symbol(a.ticker)]
    latest: dict[str, float] = {}
    if stock_tickers:
        for s in build_stock_snapshots(session, stock_tickers, settings).snapshots:
            latest[s.ticker] = s.technicals.last_close
    if fund_codes:
        for f in build_fund_snapshots(session, fund_codes, settings).snapshots:
            latest[f.symbol] = f.metrics.latest_nav

    holdings = []
    for a in rec.allocations:
        now = latest.get(a.ticker)
        change = round((now / a.last_price - 1) * 100, 2) if now and a.last_price else None
        holdings.append(
            HoldingPerformance(
                ticker=a.ticker,
                display_name=a.display_name or a.ticker,
                asset_type=a.asset_type,
                weight_percent=a.weight_percent,
                price_then=a.last_price,
                price_now=now,
                change_percent=change,
            )
        )

    priced = [h for h in holdings if h.change_percent is not None]
    priced_weight = sum(h.weight_percent for h in priced)
    portfolio_change = (
        round(sum(h.weight_percent * h.change_percent for h in priced) / priced_weight, 2) if priced_weight else None
    )
    return RecommendationPerformance(
        recommendation_id=rec.id,
        created_at=rec.created_at,
        checked_at=datetime.now(timezone.utc),
        holdings=holdings,
        portfolio_change_percent=portfolio_change,
        amount=rec.amount,
        value_now=round(rec.amount * (1 + portfolio_change / 100), 2) if portfolio_change is not None else None,
    )

