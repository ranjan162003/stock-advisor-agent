"""Build the provider-agnostic prompt the recommendation agent sends to any LLM.

Covers stocks, mutual funds, or a mix — each candidate list is described in its own section.

The prompt carries only structured, pre-computed numbers (no raw price series)
plus a strict JSON reply contract, so even small local models can follow it.
"""
from __future__ import annotations

import json

from app.schemas.market_data_schemas import ScoredStockCandidate
from app.schemas.mutual_fund_schemas import ScoredFundCandidate
from app.schemas.recommendation_schemas import (
    RISK_LEVEL_LABELS,
    AssetMix,
    InvestmentMode,
    RecommendationRequest,
)

REPLY_JSON_CONTRACT = """{
  "picks": [
    {"ticker": "<exact stock ticker or fund id from the candidate lists>", "weight_percent": <number>, "rationale": "<2-3 sentences citing the numbers/news that justify this pick>"}
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
    stock_candidates: list[ScoredStockCandidate],
    fund_candidates: list[ScoredFundCandidate],
    max_picks: int,
) -> str:
    risk_label = RISK_LEVEL_LABELS[request.risk_level]
    min_picks = min(2, len(stock_candidates) + len(fund_candidates))
    sections = [
        "You are a careful investment research assistant helping an individual investor in India "
        f"decide how to split money across {_asset_words(request)}. You give an educational opinion, "
        "not licensed advice.",
        "## Investor profile\n"
        + _describe_investment(request)
        + f"\nRisk preference: {request.risk_level}/5 ({risk_label}).",
    ]
    if stock_candidates:
        sections.append(
            "## Candidate stocks\n"
            "Pre-computed data for each stock (prices in INR; percentages are %; "
            "`prescore` is a rule-based 0-100 score — a hint, not a verdict):\n"
            + "\n".join(_describe_stock_candidate(c) for c in stock_candidates)
        )
    if fund_candidates:
        sections.append(
            "## Candidate mutual funds\n"
            "All are Direct-Growth plans. `nav` is in INR; returns are % (cagr = compound annual growth); "
            "`risk_class` is 1 (liquid/debt) to 5 (small cap); `prescore` is a rule-based 0-100 hint. "
            'Use the exact `id` (e.g. "MF:122639") as the ticker in your reply:\n'
            + "\n".join(_describe_fund_candidate(c) for c in fund_candidates)
        )
    rules = [
        "- weights must be positive and add up to exactly 100",
        "- no single holding above 40%",
        "- diversify across sectors / fund categories",
        "- match volatility, drawdown and fund risk_class to the investor's risk preference",
    ]
    if stock_candidates:
        rules.append("- treat headlines as context; don't over-react to a single news item")
    rules += _mix_rules(request)
    rules.append(_mode_specific_rule(request))
    sections.append(
        "## Task\n"
        f"Choose between {min_picks} and {max_picks} holdings ONLY from the candidates above and "
        "assign each a weight_percent. Rules:\n" + "\n".join(rules)
    )
    sections.append(
        "## Reply format\n"
        "Reply with ONLY a JSON object, no markdown fences or text around it, matching:\n" + REPLY_JSON_CONTRACT
    )
    return "\n\n".join(sections)


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


def _asset_words(request: RecommendationRequest) -> str:
    return {
        AssetMix.STOCKS: "stocks",
        AssetMix.MUTUAL_FUNDS: "mutual funds",
        AssetMix.MIXED: "a mix of stocks and mutual funds",
    }[request.asset_mix]


def _mix_rules(request: RecommendationRequest) -> list[str]:
    if request.asset_mix is not AssetMix.MIXED:
        return []
    return [
        "- include at least one stock AND at least one mutual fund",
        "- set the stock vs fund balance from the risk preference: conservative investors should hold most of "
        "the money in funds (especially debt, hybrid and large-cap index funds); aggressive investors can hold "
        "more in individual stocks and mid/small-cap funds",
        "- explain the stock/fund balance you chose in the summary",
    ]


def _mode_specific_rule(request: RecommendationRequest) -> str:
    if request.investment_mode is InvestmentMode.ONE_TIME:
        rules = []
        if request.includes_stocks:
            rules.append(
                "- stocks are bought in whole shares, so avoid giving a stock less money than one share costs "
                "(check `price` against your allocation of the lump sum)"
            )
        if request.includes_funds:
            rules.append("- mutual funds are bought by amount (most accept ₹100–₹1,000 minimum), so any NAV is fine")
        return "\n".join(rules)
    if request.includes_funds:
        return "- this is effectively a SIP: favour holdings suited to steady long-term periodic buying, not short-term trades"
    return "- favour stocks you'd be comfortable buying every period for years, not short-term trades"


def _describe_stock_candidate(candidate: ScoredStockCandidate) -> str:
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


def _describe_fund_candidate(candidate: ScoredFundCandidate) -> str:
    s = candidate.snapshot
    m = s.metrics
    data = {
        "id": s.symbol,
        "name": s.short_name,
        "category": s.category,
        "fund_house": s.fund_house,
        "risk_class": s.risk_class,
        "nav": m.latest_nav,
        "ret_1y": m.return_1y_percent,
        "cagr_3y": m.cagr_3y_percent,
        "cagr_5y": m.cagr_5y_percent,
        "volatility": m.annualized_volatility_percent,
        "max_drawdown_3y": m.max_drawdown_3y_percent,
        "sharpe_3y": m.sharpe_ratio_3y,
        "history_years": m.history_years,
        "prescore": candidate.score.total_score,
    }
    compact = {key: value for key, value in data.items() if value is not None}
    return "- " + json.dumps(compact, ensure_ascii=False)
