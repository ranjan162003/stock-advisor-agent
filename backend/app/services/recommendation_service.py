"""End-to-end recommendation pipeline.

    resolve candidates (stocks and/or mutual funds)
    -> market data snapshots -> pre-score & shortlist
    -> LLM agent picks + weights -> rupee allocation -> save to history
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.agent.allocation_calculator import calculate_allocations
from app.agent.providers.llm_provider_registry import get_llm_provider
from app.agent.recommendation_agent import RecommendationAgent
from app.analysis.candidate_scoring import shortlist_candidates
from app.analysis.fund_scoring import shortlist_funds
from app.analysis.fund_snapshot_builder import build_fund_snapshots
from app.analysis.stock_snapshot_builder import build_stock_snapshots
from app.core.app_exceptions import MarketDataError, ProviderNotConnectedError
from app.core.app_settings import AppSettings, get_settings
from app.db.orm_models import RecommendationRecord
from app.db.repositories.recommendation_repository import (
    save_recommendation_record,
    update_recommendation_response_json,
)
from app.schemas.market_data_schemas import ScoredStockCandidate
from app.schemas.mutual_fund_schemas import ScoredFundCandidate
from app.schemas.provider_schemas import ProviderId
from app.schemas.recommendation_schemas import (
    AssetMix,
    AssetType,
    CandidateSummary,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.stock_universe_service import resolve_candidate_fund_codes, resolve_candidate_tickers

logger = logging.getLogger(__name__)

# In a mixed portfolio each side gets a smaller share of the prompt.
MIXED_SHORTLIST_FRACTION = 0.6


def generate_recommendation(session: Session, request: RecommendationRequest) -> RecommendationResponse:
    settings = get_settings()

    provider = get_llm_provider(request.provider_id)
    provider_status = provider.get_status()
    if not provider_status.is_ready:
        hint = f" {provider_status.setup_hint}" if provider_status.setup_hint else ""
        raise ProviderNotConnectedError(f"{provider.display_name}: {provider_status.status_message}{hint}")
    model_name = request.model_name or provider_status.default_model

    stock_limit, fund_limit = _shortlist_limits(request, settings)
    skipped: dict[str, str] = {}

    stock_candidates: list[ScoredStockCandidate] = []
    if request.includes_stocks:
        stock_result = build_stock_snapshots(session, resolve_candidate_tickers(session, request), settings)
        skipped.update(stock_result.skipped)
        stock_candidates = shortlist_candidates(stock_result.snapshots, request.risk_level, limit=stock_limit)

    fund_candidates: list[ScoredFundCandidate] = []
    if request.includes_funds:
        fund_result = build_fund_snapshots(session, resolve_candidate_fund_codes(session, request), settings)
        skipped.update(fund_result.skipped)
        fund_candidates = shortlist_funds(fund_result.snapshots, request.risk_level, limit=fund_limit)

    _require_enough_candidates(request, stock_candidates, fund_candidates)
    logger.info(
        "Asking %s (%s) to choose from %d stocks + %d funds",
        provider.display_name, model_name, len(stock_candidates), len(fund_candidates),
    )

    agent = RecommendationAgent(provider, model_name, max_picks=settings.max_stocks_per_recommendation)
    parsed = agent.recommend(request, stock_candidates, fund_candidates)

    allocations = calculate_allocations(
        parsed,
        stocks_by_ticker={c.snapshot.ticker: c.snapshot for c in stock_candidates},
        funds_by_symbol={c.snapshot.symbol: c.snapshot for c in fund_candidates},
        amount=request.amount,
    )
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
        asset_mix=request.asset_mix,
        allocations=allocations,
        summary=parsed.summary,
        risk_notes=parsed.risk_notes,
        candidates_considered=[_summarize_stock(c, c.snapshot.ticker in picked) for c in stock_candidates]
        + [_summarize_fund(c, c.snapshot.symbol in picked) for c in fund_candidates],
        skipped_tickers=skipped,
    )
    update_recommendation_response_json(session, record, response.model_dump_json())
    return response


def _shortlist_limits(request: RecommendationRequest, settings: AppSettings) -> tuple[int, int]:
    is_local = request.provider_id is ProviderId.OLLAMA
    stock_limit = settings.max_candidates_sent_to_local_llm if is_local else settings.max_candidates_sent_to_llm
    fund_limit = (
        settings.max_fund_candidates_sent_to_local_llm if is_local else settings.max_fund_candidates_sent_to_llm
    )
    if request.asset_mix is AssetMix.MIXED:
        stock_limit = max(3, round(stock_limit * MIXED_SHORTLIST_FRACTION))
        fund_limit = max(3, round(fund_limit * MIXED_SHORTLIST_FRACTION))
    return stock_limit, fund_limit


def _require_enough_candidates(
    request: RecommendationRequest,
    stock_candidates: list[ScoredStockCandidate],
    fund_candidates: list[ScoredFundCandidate],
) -> None:
    if request.includes_stocks and request.includes_funds:
        if not stock_candidates or not fund_candidates:
            missing = "stocks" if not stock_candidates else "mutual funds"
            raise MarketDataError(f"Couldn't load data for any {missing}, so a mixed portfolio isn't possible right now.")
    elif len(stock_candidates) + len(fund_candidates) < 2:
        raise MarketDataError(
            "Couldn't load market data for enough of the requested holdings. "
            "Check the symbols and your internet connection, then try again."
        )


def _summarize_stock(candidate: ScoredStockCandidate, was_picked: bool) -> CandidateSummary:
    s = candidate.snapshot
    return CandidateSummary(
        ticker=s.ticker,
        asset_type=AssetType.STOCK,
        display_name=s.ticker.removesuffix(".NS").removesuffix(".BO"),
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


def _summarize_fund(candidate: ScoredFundCandidate, was_picked: bool) -> CandidateSummary:
    s = candidate.snapshot
    return CandidateSummary(
        ticker=s.symbol,
        asset_type=AssetType.MUTUAL_FUND,
        display_name=s.short_name,
        company_name=s.scheme_name,
        sector=s.category,
        last_price=s.metrics.latest_nav,
        return_1y_percent=s.metrics.return_1y_percent,
        cagr_3y_percent=s.metrics.cagr_3y_percent,
        annualized_volatility_percent=s.metrics.annualized_volatility_percent,
        score=candidate.score,
        was_picked=was_picked,
    )
