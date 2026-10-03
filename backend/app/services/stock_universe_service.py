"""Decide which tickers a recommendation considers: default, watchlist, or custom."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.app_exceptions import InvalidRequestError
from app.data_sources.default_stock_universe import DEFAULT_NSE_UNIVERSE, normalize_ticker
from app.db.repositories.watchlist_repository import list_watchlist_tickers
from app.schemas.recommendation_schemas import RecommendationRequest, StockUniverseSource


def resolve_candidate_tickers(session: Session, request: RecommendationRequest) -> list[str]:
    if request.universe_source is StockUniverseSource.WATCHLIST:
        tickers = [entry.ticker for entry in list_watchlist_tickers(session)]
        if not tickers:
            raise InvalidRequestError("Your watchlist is empty — add some stocks or use the default list.")
    elif request.universe_source is StockUniverseSource.CUSTOM:
        try:
            tickers = [normalize_ticker(t) for t in request.custom_tickers if t.strip()]
        except ValueError as exc:
            raise InvalidRequestError(str(exc)) from exc
    else:
        tickers = [stock.ticker for stock in DEFAULT_NSE_UNIVERSE]

    unique_tickers = list(dict.fromkeys(tickers))
    if len(unique_tickers) < 2:
        raise InvalidRequestError("Give the agent at least 2 stocks to choose between.")
    return unique_tickers
