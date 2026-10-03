from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.app_exceptions import InvalidRequestError, ResourceNotFoundError
from app.data_sources.default_stock_universe import normalize_ticker
from app.db.orm_models import WatchlistTicker
from app.db.repositories.watchlist_repository import (
    add_watchlist_ticker,
    delete_watchlist_ticker,
    find_watchlist_ticker,
    list_watchlist_tickers,
)

MAX_WATCHLIST_SIZE = 40


def get_watchlist(session: Session) -> list[WatchlistTicker]:
    return list_watchlist_tickers(session)


def add_to_watchlist(session: Session, raw_ticker: str) -> WatchlistTicker:
    try:
        ticker = normalize_ticker(raw_ticker)
    except ValueError as exc:
        raise InvalidRequestError(str(exc)) from exc
    existing = find_watchlist_ticker(session, ticker)
    if existing:
        return existing
    if len(list_watchlist_tickers(session)) >= MAX_WATCHLIST_SIZE:
        raise InvalidRequestError(f"The watchlist is limited to {MAX_WATCHLIST_SIZE} stocks.")
    return add_watchlist_ticker(session, ticker)


def remove_from_watchlist(session: Session, ticker: str) -> None:
    entry = find_watchlist_ticker(session, ticker)
    if entry is None:
        raise ResourceNotFoundError(f"{ticker} isn't on your watchlist.")
    delete_watchlist_ticker(session, entry)
