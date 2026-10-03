"""Decide which stocks and funds a recommendation considers: built-in lists, watchlist, or custom."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.app_exceptions import InvalidRequestError
from app.data_sources.default_fund_universe import DEFAULT_FUND_UNIVERSE
from app.data_sources.default_stock_universe import DEFAULT_NSE_UNIVERSE, normalize_ticker
from app.db.repositories.watchlist_fund_repository import list_watchlist_funds
from app.db.repositories.watchlist_repository import list_watchlist_tickers
from app.schemas.recommendation_schemas import AssetMix, RecommendationRequest, StockUniverseSource


def resolve_candidate_tickers(session: Session, request: RecommendationRequest) -> list[str]:
    if request.universe_source is StockUniverseSource.WATCHLIST:
        tickers = [entry.ticker for entry in list_watchlist_tickers(session)]
        if not tickers:
            raise InvalidRequestError("Your stock watchlist is empty — add some stocks or use the default list.")
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


def resolve_candidate_fund_codes(session: Session, request: RecommendationRequest) -> list[int]:
    """Watchlist funds when the watchlist is chosen, otherwise the built-in fund list.

    Custom lists hold stock tickers only, so a mixed request with a custom stock
    list still draws its funds from the built-in list.
    """
    if request.universe_source is StockUniverseSource.WATCHLIST:
        codes = [entry.scheme_code for entry in list_watchlist_funds(session)]
        if len(codes) < (2 if request.asset_mix is AssetMix.MUTUAL_FUNDS else 1):
            raise InvalidRequestError("Add mutual funds to your watchlist first, or use the built-in fund list.")
        return codes
    return [fund.scheme_code for fund in DEFAULT_FUND_UNIVERSE]
