from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.orm_models import WatchlistFund


def list_watchlist_funds(session: Session) -> list[WatchlistFund]:
    return list(session.scalars(select(WatchlistFund).order_by(WatchlistFund.added_at)))


def find_watchlist_fund(session: Session, scheme_code: int) -> WatchlistFund | None:
    return session.scalar(select(WatchlistFund).where(WatchlistFund.scheme_code == scheme_code))


def add_watchlist_fund(session: Session, scheme_code: int, scheme_name: str, category: str | None) -> WatchlistFund:
    entry = WatchlistFund(scheme_code=scheme_code, scheme_name=scheme_name, category=category)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def delete_watchlist_fund(session: Session, entry: WatchlistFund) -> None:
    session.delete(entry)
    session.commit()
