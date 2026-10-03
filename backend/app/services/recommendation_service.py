"""End-to-end recommendation pipeline.

    resolve tickers -> market data snapshots -> pre-score & shortlist
    -> LLM agent picks + weights -> rupee allocation -> save to history
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.agent.allocation_calculator import calculate_stock_allocations
from app.agent.providers.llm_provider_registry import get_llm_provider
from app.agent.recommendation_agent import RecommendationAgent
from app.analysis.candidate_scoring import shortlist_candidates
from app.analysis.stock_snapshot_builder import build_stock_snapshots
from app.core.app_exceptions import MarketDataError, ProviderNotConnectedError
from app.core.app_settings import get_settings
from app.db.orm_models import RecommendationRecord
from app.db.repositories.recommendation_repository import (
    save_recommendation_record,
    update_recommendation_response_json,
)
from app.schemas.market_data_schemas import ScoredStockCandidate
from app.schemas.provider_schemas import ProviderId
from app.schemas.recommendation_schemas import (
    CandidateSummary,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.stock_universe_service import resolve_candidate_tickers

logger = logging.getLogger(__name__)


def generate_recommendation(session: Session, request: RecommendationRequest) -> RecommendationResponse:
    settings = get_settings()

    provider = get_llm_provider(request.provider_id)
    provider_status = provider.get_status()
    if not provider_status.is_ready:
        hint = f" {provider_status.setup_hint}" if provider_status.setup_hint else ""
        raise ProviderNotConnectedError(f"{provider.display_name}: {provider_status.status_message}{hint}")
    model_name = request.model_name or provider_status.default_model

    tickers = resolve_candidate_tickers(session, request)
    build_result = build_stock_snapshots(session, tickers, settings)
    if len(build_result.snapshots) < 2:
        raise MarketDataError(
            "Couldn't load market data for enough of the requested stocks. "
            "Check the symbols and your internet connection, then try again."
        )

    candidate_limit = (
        settings.max_candidates_sent_to_local_llm
        if request.provider_id is ProviderId.OLLAMA
        else settings.max_candidates_sent_to_llm
    )
    shortlisted = shortlist_candidates(build_result.snapshots, request.risk_level, limit=candidate_limit)
    logger.info("Asking %s (%s) to choose from %d candidates", provider.display_name, model_name, len(shortlisted))

    agent = RecommendationAgent(provider, model_name, max_picks=settings.max_stocks_per_recommendation)
    parsed = agent.recommend(request, shortlisted)

    snapshots_by_ticker = {c.snapshot.ticker: c.snapshot for c in shortlisted}
    allocations = calculate_stock_allocations(parsed, snapshots_by_ticker, request.amount)
    picked = {a.ticker for a in allocations}

    record = save_recommendation_record(
        session,
        RecommendationRecord(
            investment_mode=request.investment_mode.value,
            amount=request.amount,
            risk_level=request.risk_level,
            provider_id=request.provider_id.value,
            model_name=model_name,
            response_json="{}",
        ),
    )
    response = RecommendationResponse(
        id=record.id,
        created_at=record.created_at,
        investment_mode=request.investment_mode,
        recurring_frequency=request.recurring_frequency,
        amount=request.amount,
        risk_level=request.risk_level,
        provider_id=request.provider_id,
        model_name=model_name,
        allocations=allocations,
        summary=parsed.summary,
        risk_notes=parsed.risk_notes,
        candidates_considered=[_summarize_candidate(c, c.snapshot.ticker in picked) for c in shortlisted],
        skipped_tickers=build_result.skipped,
    )
    update_recommendation_response_json(session, record, response.model_dump_json())
    return response


def _summarize_candidate(candidate: ScoredStockCandidate, was_picked: bool) -> CandidateSummary:
    s = candidate.snapshot
    return CandidateSummary(
        ticker=s.ticker,
        company_name=s.company_name,
        sector=s.sector,
        last_price=s.technicals.last_close,
        return_1y_percent=s.technicals.return_1y_percent,
        annualized_volatility_percent=s.technicals.annualized_volatility_percent,
        trailing_pe=s.fundamentals.trailing_pe,
        score=candidate.score,
        headlines=s.headlines,
        was_picked=was_picked,
    )
