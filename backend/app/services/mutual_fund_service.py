"""Fund search and the fund side of the watchlist."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.core.app_exceptions import InvalidRequestError, MarketDataError, ResourceNotFoundError
from app.data_sources.fund_search_aliases import query_variants, relevance_score
from app.data_sources.mfapi_mutual_fund_client import (
    fetch_fund_nav_history,
    is_direct_growth_plan,
    search_mutual_funds,
)
from app.db.orm_models import WatchlistFund
from app.services.fund_catalog_service import find_catalog_fund, search_catalog
from app.db.repositories.watchlist_fund_repository import (
    add_watchlist_fund,
    delete_watchlist_fund,
    find_watchlist_fund,
    list_watchlist_funds,
)
from app.schemas.mutual_fund_schemas import FundSearchResult

MAX_SEARCH_RESULTS = 25


def search_funds(
    session: Session, query: str, category: str | None = None, include_all_plans: bool = False, limit: int = 20
) -> list[FundSearchResult]:
    """Search the local AMFI catalog (instant, forgiving); fall back to mfapi if it can't be loaded."""
    try:
        return search_catalog(session, query, category, include_all_plans, limit)
    except MarketDataError as exc:
        logger.warning("Fund catalog unavailable (%s); searching mfapi instead", exc.message)
        if len(query.strip()) < 3:
            return []
        results = search_funds_online(query)
        return [r for r in results if include_all_plans or r.is_direct_growth][:limit]
MAX_WATCHLIST_FUNDS = 30

logger = logging.getLogger(__name__)


def search_funds_online(query: str) -> list[FundSearchResult]:
    """Fallback search straight against mfapi.in, used only if the AMFI catalog is unavailable.

    "icici pru bluechip", "ppfas" and "hdfc midcap" all find the funds people mean,
    even though none of those words appear literally in the scheme names.
    """
    query = query.strip()
    if len(query) < 3:
        raise InvalidRequestError("Type at least 3 characters to search funds.")

    variants = query_variants(query) or [query]
    with ThreadPoolExecutor(max_workers=len(variants)) as pool:
        batches = list(pool.map(_search_quietly, variants))
    if all(batch is None for batch in batches):
        raise MarketDataError("Mutual fund search is unavailable right now — check your internet connection.")

    merged: dict[int, FundSearchResult] = {}
    for batch in batches:
        for item in batch or []:
            code = int(item["schemeCode"])
            merged.setdefault(
                code,
                FundSearchResult(
                    scheme_code=code,
                    scheme_name=item["schemeName"],
                    is_direct_growth=is_direct_growth_plan(item["schemeName"]),
                ),
            )
    ranked = sorted(
        merged.values(),
        key=lambda r: (-relevance_score(query, r.scheme_name, r.is_direct_growth), r.scheme_name),
    )
    return ranked[:MAX_SEARCH_RESULTS]


def _search_quietly(query: str) -> list[dict] | None:
    try:
        return search_mutual_funds(query)
    except MarketDataError:
        return None


def get_fund_watchlist(session: Session) -> list[WatchlistFund]:
    return list_watchlist_funds(session)


def add_fund_to_watchlist(session: Session, scheme_code: int) -> WatchlistFund:
    existing = find_watchlist_fund(session, scheme_code)
    if existing:
        return existing
    if len(list_watchlist_funds(session)) >= MAX_WATCHLIST_FUNDS:
        raise InvalidRequestError(f"The fund watchlist is limited to {MAX_WATCHLIST_FUNDS} funds.")
    try:
        listed = find_catalog_fund(session, scheme_code)
    except MarketDataError:
        listed = None
    if listed:
        return add_watchlist_fund(session, scheme_code, listed.scheme_name, listed.category)
    history = fetch_fund_nav_history(scheme_code)
    if history is None:
        raise ResourceNotFoundError(f"No mutual fund found with scheme code {scheme_code}.")
    return add_watchlist_fund(session, scheme_code, history.scheme_name, history.category)


def remove_fund_from_watchlist(session: Session, scheme_code: int) -> None:
    entry = find_watchlist_fund(session, scheme_code)
    if entry is None:
        raise ResourceNotFoundError(f"Scheme {scheme_code} isn't on your watchlist.")
    delete_watchlist_fund(session, entry)
