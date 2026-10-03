"""The recommendation agent: prompt -> LLM -> parse, with one self-repair retry."""
from __future__ import annotations

import logging

from app.agent.providers.base_llm_provider import BaseLlmProvider
from app.agent.recommendation_prompt_builder import build_json_repair_prompt, build_recommendation_prompt
from app.agent.recommendation_response_parser import ParsedRecommendation, parse_recommendation_reply
from app.core.app_exceptions import RecommendationParseError
from app.schemas.market_data_schemas import ScoredStockCandidate
from app.schemas.mutual_fund_schemas import ScoredFundCandidate
from app.schemas.recommendation_schemas import RecommendationRequest

logger = logging.getLogger(__name__)


class RecommendationAgent:
    def __init__(self, provider: BaseLlmProvider, model_name: str | None, max_picks: int):
        self._provider = provider
        self._model_name = model_name
        self._max_picks = max_picks

    def recommend(
        self,
        request: RecommendationRequest,
        stock_candidates: list[ScoredStockCandidate],
        fund_candidates: list[ScoredFundCandidate],
    ) -> ParsedRecommendation:
        allowed_tickers = {c.snapshot.ticker for c in stock_candidates} | {c.snapshot.symbol for c in fund_candidates}
        prompt = build_recommendation_prompt(request, stock_candidates, fund_candidates, self._max_picks)

        reply = self._provider.generate_text(prompt, self._model_name)
        try:
            return parse_recommendation_reply(reply, allowed_tickers, self._max_picks)
        except RecommendationParseError as first_error:
            logger.warning(
                "First reply unusable (%s); asking the model to repair it. Reply was: %r",
                first_error.message, reply[:1000],
            )
            repair_prompt = build_json_repair_prompt(prompt, reply, first_error.message)
            repaired_reply = self._provider.generate_text(repair_prompt, self._model_name)
            try:
                return parse_recommendation_reply(repaired_reply, allowed_tickers, self._max_picks)
            except RecommendationParseError as second_error:
                logger.error("Repaired reply also unusable. Reply was: %r", repaired_reply[:2000])
                raise RecommendationParseError(
                    f"{second_error.message} (after one retry) — {self._provider.display_name} replied: "
                    f"{_excerpt(repaired_reply)}. Try again, or pick a stronger model."
                ) from second_error


def _excerpt(text: str, limit: int = 160) -> str:
    flat = " ".join(text.split())
    if not flat:
        return "(an empty reply)"
    return f"“{flat[:limit]}{'…' if len(flat) > limit else ''}”"
