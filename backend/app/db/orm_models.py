"""Database tables: watchlist, market-data cache, and recommendation history."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database_session import OrmBase


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WatchlistTicker(OrmBase):
    __tablename__ = "watchlist_tickers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MarketDataCacheEntry(OrmBase):
    """One cached `StockSnapshot` (prices + indicators + fundamentals + news) per ticker."""

    __tablename__ = "market_data_cache"

    ticker: Mapped[str] = mapped_column(String(32), primary_key=True)
    snapshot_json: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RecommendationRecord(OrmBase):
    __tablename__ = "recommendation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    investment_mode: Mapped[str] = mapped_column(String(16))
    amount: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[int] = mapped_column(Integer)
    provider_id: Mapped[str] = mapped_column(String(16))
    model_name: Mapped[str] = mapped_column(String(64))
    # Full `RecommendationResponse` body, so history replays exactly what was shown.
    response_json: Mapped[str] = mapped_column(Text)
