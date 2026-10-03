from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.orm_models import FundCatalogEntry, FundCatalogRefresh


def latest_catalog_refresh(session: Session) -> FundCatalogRefresh | None:
    return session.scalar(select(FundCatalogRefresh).order_by(FundCatalogRefresh.refreshed_at.desc()).limit(1))


def list_catalog_entries(session: Session) -> list[FundCatalogEntry]:
    return list(session.scalars(select(FundCatalogEntry)))


def get_catalog_entry(session: Session, scheme_code: int) -> FundCatalogEntry | None:
    return session.get(FundCatalogEntry, scheme_code)


def replace_catalog(session: Session, entries: list[FundCatalogEntry], refreshed_at: datetime) -> None:
    """Swap the whole catalog in one transaction so readers never see a half-written list."""
    session.execute(delete(FundCatalogEntry))
    session.add_all(entries)
    session.add(FundCatalogRefresh(refreshed_at=refreshed_at, scheme_count=len(entries)))
    session.commit()
