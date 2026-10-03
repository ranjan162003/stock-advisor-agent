"""Read/write cached snapshots so repeat requests don't re-hit Yahoo / mfapi.

One table holds both kinds: stocks are keyed by ticker ("TCS.NS") and funds by
symbol ("MF:122639"); `model` says which schema to parse the JSON back into.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.orm_models import MarketDataCacheEntry
from app.schemas.market_data_schemas import StockSnapshot

SnapshotT = TypeVar("SnapshotT", bound=BaseModel)


def load_fresh_cached_snapshots(
    session: Session, keys: list[str], max_age: timedelta, model: type[SnapshotT] = StockSnapshot
) -> dict[str, SnapshotT]:
    if not keys:
        return {}
    oldest_allowed = datetime.now(timezone.utc) - max_age
    rows = session.scalars(select(MarketDataCacheEntry).where(MarketDataCacheEntry.ticker.in_(keys)))
    fresh: dict[str, SnapshotT] = {}
    for row in rows:
        fetched_at = row.fetched_at if row.fetched_at.tzinfo else row.fetched_at.replace(tzinfo=timezone.utc)
        if fetched_at >= oldest_allowed:
            fresh[row.ticker] = model.model_validate_json(row.snapshot_json)
    return fresh


def save_snapshots_to_cache(session: Session, snapshots: dict[str, BaseModel], fetched_at: datetime) -> None:
    """`snapshots` maps cache key -> snapshot."""
    for key, snapshot in snapshots.items():
        session.merge(MarketDataCacheEntry(ticker=key, snapshot_json=snapshot.model_dump_json(), fetched_at=fetched_at))
    session.commit()
