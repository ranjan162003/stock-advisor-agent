"""Assemble a full `StockSnapshot` (indicators + fundamentals + news) per ticker.

Fresh snapshots come from the SQLite cache; everything else is fetched once
(prices batched, fundamentals/news in parallel) and written back to the cache.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy.orm import Session

from app.analysis.fundamentals_extractor import company_display_name, extract_fundamental_metrics
from app.analysis.technical_indicators import compute_technical_indicators
from app.core.app_settings import AppSettings
from app.data_sources.default_stock_universe import DEFAULT_UNIVERSE_BY_TICKER
from app.data_sources.news_headlines_client import fetch_recent_headlines
from app.data_sources.yfinance_market_data_client import fetch_closing_price_history, fetch_company_profile
from app.db.repositories.market_data_cache_repository import load_fresh_cached_snapshots, save_snapshots_to_cache
from app.schemas.market_data_schemas import StockSnapshot

logger = logging.getLogger(__name__)

NO_PRICE_HISTORY_REASON = "No price history found — check the symbol and exchange suffix (e.g. .NS / .BO)."


@dataclass
class SnapshotBuildResult:
    snapshots: list[StockSnapshot]
    skipped: dict[str, str] = field(default_factory=dict)


def build_stock_snapshots(session: Session, tickers: list[str], settings: AppSettings) -> SnapshotBuildResult:
    cached = load_fresh_cached_snapshots(
        session, tickers, max_age=timedelta(minutes=settings.market_data_cache_ttl_minutes)
    )
    to_fetch = [t for t in tickers if t not in cached]
    logger.info("Snapshots: %d from cache, %d to fetch", len(cached), len(to_fetch))

    fetched: list[StockSnapshot] = []
    skipped: dict[str, str] = {}
    if to_fetch:
        closes_by_ticker = fetch_closing_price_history(to_fetch, settings.price_history_period)
        skipped = {t: NO_PRICE_HISTORY_REASON for t in to_fetch if t not in closes_by_ticker}

        with ThreadPoolExecutor(max_workers=settings.market_data_fetch_workers) as pool:
            fetched = list(
                pool.map(
                    lambda item: _build_single_snapshot(item[0], item[1], settings),
                    closes_by_ticker.items(),
                )
            )
        save_snapshots_to_cache(session, fetched)

    by_ticker = {**cached, **{s.ticker: s for s in fetched}}
    ordered = [by_ticker[t] for t in tickers if t in by_ticker]
    return SnapshotBuildResult(snapshots=ordered, skipped=skipped)


def _build_single_snapshot(ticker: str, closes: pd.Series, settings: AppSettings) -> StockSnapshot:
    profile = fetch_company_profile(ticker)
    known = DEFAULT_UNIVERSE_BY_TICKER.get(ticker)
    company_name = company_display_name(profile, known.company_name if known else ticker)
    return StockSnapshot(
        ticker=ticker,
        company_name=company_name,
        sector=profile.get("sector") or (known.sector if known else None),
        currency=profile.get("currency"),
        technicals=compute_technical_indicators(closes),
        fundamentals=extract_fundamental_metrics(profile),
        headlines=fetch_recent_headlines(
            ticker, company_name, settings.news_headlines_per_stock, settings.finnhub_api_key
        ),
        fetched_at=datetime.now(timezone.utc),
    )
