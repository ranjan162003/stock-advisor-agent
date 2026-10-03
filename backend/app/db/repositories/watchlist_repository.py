from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.orm_models import WatchlistTicker


def list_watchlist_tickers(session: Session) -> list[WatchlistTicker]:
    return list(session.scalars(select(WatchlistTicker).order_by(WatchlistTicker.added_at)))


def find_watchlist_ticker(session: Session, ticker: str) -> WatchlistTicker | None:
    return session.scalar(select(WatchlistTicker).where(WatchlistTicker.ticker == ticker))


def add_watchlist_ticker(session: Session, ticker: str) -> WatchlistTicker:
    entry = WatchlistTicker(ticker=ticker)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def delete_watchlist_ticker(session: Session, entry: WatchlistTicker) -> None:
    session.delete(entry)
    session.commit()
