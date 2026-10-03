from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database_session import get_db_session
from app.schemas.watchlist_schemas import WatchlistTickerCreate, WatchlistTickerRead
from app.services.watchlist_service import add_to_watchlist, get_watchlist, remove_from_watchlist

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistTickerRead])
def read_watchlist(session: Session = Depends(get_db_session)) -> list[WatchlistTickerRead]:
    return [WatchlistTickerRead.model_validate(entry) for entry in get_watchlist(session)]


@router.post("", response_model=WatchlistTickerRead, status_code=status.HTTP_201_CREATED)
def create_watchlist_ticker(
    body: WatchlistTickerCreate, session: Session = Depends(get_db_session)
) -> WatchlistTickerRead:
    return WatchlistTickerRead.model_validate(add_to_watchlist(session, body.ticker))


@router.delete("/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist_ticker(ticker: str, session: Session = Depends(get_db_session)) -> None:
    remove_from_watchlist(session, ticker)
