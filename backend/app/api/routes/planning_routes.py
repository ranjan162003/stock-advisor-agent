"""SIP / goal planner endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.sip_planner_schemas import (
    ReturnPresetInfo,
    SipBacktestRequest,
    SipBacktestResponse,
    SipProjectionRequest,
    SipProjectionResponse,
)
from app.services.sip_planner_service import backtest_sip, list_return_presets, project_sip

router = APIRouter(tags=["planning"])


@router.get("/planner/return-presets", response_model=list[ReturnPresetInfo])
def read_return_presets() -> list[ReturnPresetInfo]:
    return list_return_presets()


# Plain `def`: these do blocking network fetches, so FastAPI runs them in a worker thread.
@router.post("/planner/sip", response_model=SipProjectionResponse)
def create_sip_projection(request: SipProjectionRequest) -> SipProjectionResponse:
    return project_sip(request)


@router.post("/planner/sip-backtest", response_model=SipBacktestResponse)
def create_sip_backtest(request: SipBacktestRequest) -> SipBacktestResponse:
    return backtest_sip(request)
