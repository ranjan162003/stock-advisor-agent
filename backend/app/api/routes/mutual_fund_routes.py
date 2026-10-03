"""Mutual fund search, the built-in fund list, and the fund side of the watchlist."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.data_sources.default_fund_universe import DEFAULT_FUND_UNIVERSE
from app.db.database_session import get_db_session
from app.schemas.mutual_fund_schemas import (
    FundCategory,
    FundSearchResult,
    UniverseFund,
    WatchlistFundCreate,
    WatchlistFundRead,
)
from app.services.fund_catalog_service import list_catalog_categories
from app.services.mutual_fund_service import (
    add_fund_to_watchlist,
    get_fund_watchlist,
    remove_fund_from_watchlist,
    search_funds,
)

router = APIRouter(tags=["mutual funds"])


@router.get("/funds/default-universe", response_model=list[UniverseFund])
def read_default_fund_universe() -> list[UniverseFund]:
    return DEFAULT_FUND_UNIVERSE


@router.get("/funds/search", response_model=list[FundSearchResult])
def search_mutual_funds(
    q: str = Query(default="", max_length=80),
    category: str | None = Query(default=None, max_length=160),
    include_all_plans: bool = False,
    limit: int = Query(default=20, ge=1, le=5000),
    session: Session = Depends(get_db_session),
) -> list[FundSearchResult]:
    """Search all active Indian mutual funds by any words in their name, optionally within one category."""
    return search_funds(session, q, category, include_all_plans, limit)


@router.get("/funds/categories", response_model=list[FundCategory])
def read_fund_categories(include_all_plans: bool = False, session: Session = Depends(get_db_session)) -> list[FundCategory]:
    return list_catalog_categories(session, include_all_plans)


@router.get("/watchlist/funds", response_model=list[WatchlistFundRead])
def read_fund_watchlist(session: Session = Depends(get_db_session)) -> list[WatchlistFundRead]:
    return [WatchlistFundRead.model_validate(entry) for entry in get_fund_watchlist(session)]


@router.post("/watchlist/funds", response_model=WatchlistFundRead, status_code=status.HTTP_201_CREATED)
def create_watchlist_fund(body: WatchlistFundCreate, session: Session = Depends(get_db_session)) -> WatchlistFundRead:
    return WatchlistFundRead.model_validate(add_fund_to_watchlist(session, body.scheme_code))


@router.delete("/watchlist/funds/{scheme_code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist_fund(scheme_code: int, session: Session = Depends(get_db_session)) -> None:
    remove_fund_from_watchlist(session, scheme_code)
