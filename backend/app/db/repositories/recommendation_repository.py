from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.orm_models import RecommendationRecord


def save_recommendation_record(session: Session, record: RecommendationRecord) -> RecommendationRecord:
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def update_recommendation_response_json(session: Session, record: RecommendationRecord, response_json: str) -> None:
    record.response_json = response_json
    session.commit()


def list_recent_recommendation_records(session: Session, limit: int) -> list[RecommendationRecord]:
    query = select(RecommendationRecord).order_by(RecommendationRecord.created_at.desc()).limit(limit)
    return list(session.scalars(query))


def get_recommendation_record(session: Session, record_id: int) -> RecommendationRecord | None:
    return session.get(RecommendationRecord, record_id)


def delete_recommendation_record(session: Session, record: RecommendationRecord) -> None:
    session.delete(record)
    session.commit()
