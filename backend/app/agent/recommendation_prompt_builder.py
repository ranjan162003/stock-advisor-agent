"""Build the provider-agnostic prompt the recommendation agent sends to any LLM.

The prompt carries only structured, pre-computed numbers (no raw price series)
plus a strict JSON reply contract, so even small local models can follow it.
"""
from __future__ import annotations

import json

from app.schemas.market_data_schemas import ScoredStockCandidate
from app.schemas.recommendation_schemas import RISK_LEVEL_LABELS, InvestmentMode, RecommendationRequest

REPLY_JSON_CONTRACT = """{
  "picks": [
    {"ticker": "<exact ticker from the candidate list>", "weight_percent": <number>, "rationale": "<2-3 sentences citing the numbers/news that justify this pick>"}
  ],
  "summary": "<3-5 sentences explaining the overall portfolio logic for this investor>",
  "risk_notes": ["<concrete risk 1>", "<concrete risk 2>", "..."]
}"""

# Machine-readable form of REPLY_JSON_CONTRACT, for providers that can constrain
# their output to a schema (Ollama structured outputs).
REPLY_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "picks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "weight_percent": {"type": "number"},
                    "rationale": {"type": "string"},
                },
                "required": ["ticker", "weight_percent", "rationale"],
            },
        },
        "summary": {"type": "string"},
        "risk_notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["picks", "summary", "risk_notes"],
}


def build_recommendation_prompt(
    request: RecommendationRequest,
    candidates: list[ScoredStockCandidate],
    max_picks: int,
) -> str:
    risk_label = RISK_LEVEL_LABELS[request.risk_level]
    min_picks = min(2, len(candidates))
    return "\n\n".join(
        [
            "You are a careful equity research assistant helping an individual investor in India "
            "decide how to split money across stocks. You give an educational opinion, not licensed advice.",
            "## Investor profile\n" + _describe_investment(request) + f"\nRisk preference: {request.risk_level}/5 ({risk_label}).",
            "## Candidate stocks\n"
            "Pre-computed data for each candidate (prices in INR; percentages are %; "
            "`prescore` is a rule-based 0-100 score — a hint, not a verdict):\n"
            + "\n".join(_describe_candidate(c) for c in candidates),
            "## Task\n"
            f"Choose between {min_picks} and {max_picks} stocks ONLY from the candidate list above and "
            "assign each a weight_percent. Rules:\n"
            "- weights must be positive and add up to exactly 100\n"
            "- no single stock above 40%\n"
            "- prefer diversification across sectors\n"
            "- match volatility and drawdown to the investor's risk preference\n"
            "- treat headlines as context; don't over-react to a single news item\n"
            + _mode_specific_rule(request),
            "## Reply format\n"
            "Reply with ONLY a JSON object, no markdown fences or text around it, matching:\n" + REPLY_JSON_CONTRACT,
        ]
    )


def build_json_repair_prompt(original_prompt: str, invalid_reply: str, problem: str) -> str:
    return (
        f"{original_prompt}\n\n## Correction needed\nYour previous reply could not be used ({problem}). "
        f"Previous reply:\n{invalid_reply[:2000]}\n\nReply again with ONLY the corrected JSON object."
    )


def _describe_investment(request: RecommendationRequest) -> str:
    if request.investment_mode is InvestmentMode.ONE_TIME:
        return f"One-time lump sum to invest now: INR {request.amount:,.0f}."
    period = "month" if request.recurring_frequency and request.recurring_frequency.value == "monthly" else "year"
    return (
        f"Recurring investment: INR {request.amount:,.0f} every {period}. The investor will re-apply your "
        "percentage split to each contribution themselves, so recommend a durable long-term target allocation."
    )


def _mode_specific_rule(request: RecommendationRequest) -> str:
    if request.investment_mode is InvestmentMode.ONE_TIME:
        return (
            "- the money is invested in whole shares, so avoid giving a stock less money than one share costs "
            "(check `price` against your allocation of the lump sum)"
        )
    return "- favour stocks you'd be comfortable buying every period for years, not short-term trades"


def _describe_candidate(candidate: ScoredStockCandidate) -> str:
    s = candidate.snapshot
    t, f = s.technicals, s.fundamentals
    data = {
        "ticker": s.ticker,
        "name": s.company_name,
        "sector": s.sector,
        "price": t.last_close,
        "ret_1m": t.return_1m_percent,
        "ret_6m": t.return_6m_percent,
        "ret_1y": t.return_1y_percent,
        "vs_sma200": t.price_vs_sma_200_percent,
        "rsi14": t.rsi_14,
        "volatility": t.annualized_volatility_percent,
        "max_drawdown_1y": t.max_drawdown_1y_percent,
        "pe": f.trailing_pe,
        "fwd_pe": f.forward_pe,
        "earnings_growth": f.earnings_growth_percent,
        "roe": f.return_on_equity_percent,
        "profit_margin": f.profit_margin_percent,
        "debt_to_equity": f.debt_to_equity,
        "dividend_yield": f.dividend_yield_percent,
        "prescore": candidate.score.total_score,
        "headlines": [h.title for h in s.headlines],
    }
    compact = {key: value for key, value in data.items() if value not in (None, [])}
    return "- " + json.dumps(compact, ensure_ascii=False)
