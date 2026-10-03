"""SIP / goal planner and portfolio rebalancing endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database_session import get_db_session
from app.schemas.rebalance_schemas import (
    HoldingsImportRequest,
    HoldingsImportResponse,
    RebalanceRequest,
    RebalanceResponse,
)
from app.schemas.sip_planner_schemas import (
    ReturnPresetInfo,
    SipBacktestRequest,
    SipBacktestResponse,
    SipProjectionRequest,
    SipProjectionResponse,
)
from app.services.holdings_import_service import import_holdings
from app.services.rebalance_service import rebalance_portfolio
from app.services.sip_planner_service import backtest_sip, list_return_presets, project_sip

router = APIRouter(tags=["planning"])


@router.get("/planner/return-presets", response_model=list[ReturnPresetInfo])
def read_return_presets() -> list[ReturnPresetInfo]:
    return list_return_presets()


# Plain `def`: these do blocking network fetches, so FastAPI runs them in a worker thread.
@router.post("/planner/sip", response_model=SipProjectionResponse)
def create_sip_projection(request: SipProjectionRequest, session: Session = Depends(get_db_session)) -> SipProjectionResponse:
    return project_sip(session, request)


@router.post("/planner/sip-backtest", response_model=SipBacktestResponse)
def create_sip_backtest(request: SipBacktestRequest) -> SipBacktestResponse:
    return backtest_sip(request)


@router.post("/rebalance", response_model=RebalanceResponse)
def create_rebalance_plan(request: RebalanceRequest, session: Session = Depends(get_db_session)) -> RebalanceResponse:
    return rebalance_portfolio(session, request)


@router.post("/rebalance/import-holdings", response_model=HoldingsImportResponse)
def parse_holdings(request: HoldingsImportRequest) -> HoldingsImportResponse:
    return import_holdings(request.text)
