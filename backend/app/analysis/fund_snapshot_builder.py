"""Assemble a `FundSnapshot` (NAV metrics + category + risk class) per scheme.

Fresh snapshots come from the SQLite cache; the rest are fetched from mfapi.in
in parallel and written back to the cache.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.analysis.fund_metrics import compute_fund_metrics, is_nav_stale
from app.core.app_settings import AppSettings
from app.data_sources.default_fund_universe import (
    DEFAULT_FUNDS_BY_CODE,
    fund_symbol,
    infer_fund_risk_class,
    short_fund_name,
)
from app.data_sources.mfapi_mutual_fund_client import fetch_fund_nav_history
from app.db.repositories.market_data_cache_repository import load_fresh_cached_snapshots, save_snapshots_to_cache
from app.schemas.mutual_fund_schemas import FundSnapshot

logger = logging.getLogger(__name__)

MIN_HISTORY_DAYS = 180


@dataclass
class FundSnapshotBuildResult:
    snapshots: list[FundSnapshot]
    skipped: dict[str, str] = field(default_factory=dict)


def build_fund_snapshots(session: Session, scheme_codes: list[int], settings: AppSettings) -> FundSnapshotBuildResult:
    symbols = [fund_symbol(code) for code in scheme_codes]
    cached = load_fresh_cached_snapshots(
        session, symbols, max_age=timedelta(minutes=settings.market_data_cache_ttl_minutes), model=FundSnapshot
    )
    to_fetch = [code for code in scheme_codes if fund_symbol(code) not in cached]
    logger.info("Fund snapshots: %d from cache, %d to fetch", len(cached), len(to_fetch))

    fetched: dict[str, FundSnapshot] = {}
    skipped: dict[str, str] = {}
    if to_fetch:
        with ThreadPoolExecutor(max_workers=settings.market_data_fetch_workers) as pool:
            for code, outcome in zip(to_fetch, pool.map(_build_single_fund_snapshot, to_fetch)):
                if isinstance(outcome, FundSnapshot):
                    fetched[outcome.symbol] = outcome
                else:
                    skipped[fund_symbol(code)] = outcome
        save_snapshots_to_cache(session, fetched, fetched_at=datetime.now(timezone.utc))

    by_symbol = {**cached, **fetched}
    return FundSnapshotBuildResult(
        snapshots=[by_symbol[s] for s in symbols if s in by_symbol],
        skipped=skipped,
    )


def _build_single_fund_snapshot(scheme_code: int) -> FundSnapshot | str:
    """The snapshot, or a human-readable reason the fund was skipped."""
    history = fetch_fund_nav_history(scheme_code)
    if history is None:
        return "No NAV data found — check the scheme code."
    navs = history.navs
    if (navs.index[-1] - navs.index[0]).days < MIN_HISTORY_DAYS:
        return "Less than 6 months of NAV history — too new to evaluate."
    if is_nav_stale(navs):
        return f"NAV hasn't updated since {navs.index[-1]:%d %b %Y} — the scheme may be closed or merged."

    known = DEFAULT_FUNDS_BY_CODE.get(scheme_code)
    return FundSnapshot(
        symbol=fund_symbol(scheme_code),
        scheme_code=scheme_code,
        scheme_name=history.scheme_name,
        short_name=known.short_name if known else short_fund_name(history.scheme_name),
        fund_house=history.fund_house,
        category=known.category if known else history.category,
        risk_class=known.risk_class if known else infer_fund_risk_class(history.category, history.scheme_name),
        metrics=compute_fund_metrics(navs),
        fetched_at=datetime.now(timezone.utc),
    )
