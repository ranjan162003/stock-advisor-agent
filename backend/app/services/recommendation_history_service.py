from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.app_exceptions import ResourceNotFoundError
from app.db.repositories.recommendation_repository import (
    delete_recommendation_record,
    get_recommendation_record,
    list_recent_recommendation_records,
)
from app.schemas.recommendation_schemas import RecommendationHistoryItem, RecommendationResponse


def list_recommendation_history(session: Session, limit: int) -> list[RecommendationHistoryItem]:
    items: list[RecommendationHistoryItem] = []
    for record in list_recent_recommendation_records(session, limit):
        response = RecommendationResponse.model_validate_json(record.response_json)
        items.append(
            RecommendationHistoryItem(
                id=response.id,
                created_at=response.created_at,
                investment_mode=response.investment_mode,
                recurring_frequency=response.recurring_frequency,
                amount=response.amount,
                risk_level=response.risk_level,
                provider_id=response.provider_id,
                model_name=response.model_name,
                picked_tickers=[a.ticker for a in response.allocations],
            )
        )
    return items


def get_recommendation_detail(session: Session, record_id: int) -> RecommendationResponse:
    record = get_recommendation_record(session, record_id)
    if record is None:
        raise ResourceNotFoundError(f"Recommendation {record_id} not found.")
    return RecommendationResponse.model_validate_json(record.response_json)


def delete_recommendation(session: Session, record_id: int) -> None:
    record = get_recommendation_record(session, record_id)
    if record is None:
        raise ResourceNotFoundError(f"Recommendation {record_id} not found.")
    delete_recommendation_record(session, record)
