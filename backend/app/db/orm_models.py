"""Database tables: watchlist, market-data cache, and recommendation history."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database_session import OrmBase


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WatchlistTicker(OrmBase):
    __tablename__ = "watchlist_tickers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class WatchlistFund(OrmBase):
    __tablename__ = "watchlist_funds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_code: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    scheme_name: Mapped[str] = mapped_column(String(256))
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
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


class FundCatalogEntry(OrmBase):
    """One active, open-ended mutual fund scheme from AMFI's daily list (refreshed daily)."""

    __tablename__ = "fund_catalog"

    scheme_code: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme_name: Mapped[str] = mapped_column(String(300))
    fund_house: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    plan: Mapped[str | None] = mapped_column(String(60), nullable=True)
    option: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_direct_growth: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    nav: Mapped[float | None] = mapped_column(Float, nullable=True)
    nav_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class FundCatalogRefresh(OrmBase):
    __tablename__ = "fund_catalog_refresh"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    scheme_count: Mapped[int] = mapped_column(Integer)
