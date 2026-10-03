"""Read/write cached `StockSnapshot`s so repeat requests don't re-hit Yahoo."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.orm_models import MarketDataCacheEntry
from app.schemas.market_data_schemas import StockSnapshot


def load_fresh_cached_snapshots(
    session: Session, tickers: list[str], max_age: timedelta
) -> dict[str, StockSnapshot]:
    if not tickers:
        return {}
    oldest_allowed = datetime.now(timezone.utc) - max_age
    rows = session.scalars(select(MarketDataCacheEntry).where(MarketDataCacheEntry.ticker.in_(tickers)))
    fresh: dict[str, StockSnapshot] = {}
    for row in rows:
        fetched_at = row.fetched_at if row.fetched_at.tzinfo else row.fetched_at.replace(tzinfo=timezone.utc)
        if fetched_at >= oldest_allowed:
            fresh[row.ticker] = StockSnapshot.model_validate_json(row.snapshot_json)
    return fresh


def save_snapshots_to_cache(session: Session, snapshots: list[StockSnapshot]) -> None:
    for snapshot in snapshots:
        session.merge(
            MarketDataCacheEntry(
                ticker=snapshot.ticker,
                snapshot_json=snapshot.model_dump_json(),
                fetched_at=snapshot.fetched_at,
            )
        )
    session.commit()
