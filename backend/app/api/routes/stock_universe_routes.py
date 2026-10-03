"""Expose the default candidate list and a per-stock data preview."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analysis.stock_snapshot_builder import build_stock_snapshots
from app.core.app_exceptions import InvalidRequestError, MarketDataError
from app.core.app_settings import get_settings
from app.data_sources.default_stock_universe import DEFAULT_NSE_UNIVERSE, normalize_ticker
from app.db.database_session import get_db_session
from app.schemas.market_data_schemas import StockSnapshot, UniverseStock

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/default-universe", response_model=list[UniverseStock])
def read_default_universe() -> list[UniverseStock]:
    return DEFAULT_NSE_UNIVERSE


@router.get("/{ticker}/snapshot", response_model=StockSnapshot)
def read_stock_snapshot(ticker: str, session: Session = Depends(get_db_session)) -> StockSnapshot:
    try:
        normalized = normalize_ticker(ticker)
    except ValueError as exc:
        raise InvalidRequestError(str(exc)) from exc
    result = build_stock_snapshots(session, [normalized], get_settings())
    if not result.snapshots:
        raise MarketDataError(result.skipped.get(normalized, f"No data found for {normalized}."))
    return result.snapshots[0]
