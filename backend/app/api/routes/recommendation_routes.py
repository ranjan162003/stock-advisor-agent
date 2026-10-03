"""Generate a recommendation and browse/delete past ones."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database_session import get_db_session
from app.schemas.recommendation_schemas import (
    RecommendationHistoryItem,
    RecommendationPerformance,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.recommendation_history_service import (
    delete_recommendation,
    get_recommendation_detail,
    list_recommendation_history,
)
from app.services.recommendation_performance_service import get_recommendation_performance
from app.services.recommendation_service import generate_recommendation

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# Plain `def` (not async): the pipeline does blocking network/LLM calls, so
# FastAPI runs it in a worker thread instead of blocking the event loop.
@router.post("", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
def create_recommendation(
    request: RecommendationRequest, session: Session = Depends(get_db_session)
) -> RecommendationResponse:
    return generate_recommendation(session, request)


@router.get("", response_model=list[RecommendationHistoryItem])
def read_recommendation_history(
    limit: int = Query(default=50, ge=1, le=200), session: Session = Depends(get_db_session)
) -> list[RecommendationHistoryItem]:
    return list_recommendation_history(session, limit)


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def read_recommendation(recommendation_id: int, session: Session = Depends(get_db_session)) -> RecommendationResponse:
    return get_recommendation_detail(session, recommendation_id)


@router.get("/{recommendation_id}/performance", response_model=RecommendationPerformance)
def read_recommendation_performance(
    recommendation_id: int, session: Session = Depends(get_db_session)
) -> RecommendationPerformance:
    """Then-vs-now prices for each holding (cached market data, refreshed every few hours)."""
    return get_recommendation_performance(session, recommendation_id)


@router.delete("/{recommendation_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_recommendation(recommendation_id: int, session: Session = Depends(get_db_session)) -> None:
    delete_recommendation(session, recommendation_id)
