"""Rule-based pre-scoring that shortlists candidates before the LLM sees them.

This keeps the prompt small and gives the agent (and the user) a transparent,
deterministic baseline. The LLM still makes the final pick and split — it just
reasons over the best-looking candidates rather than the whole universe.

Every sub-score is 0-100. The weights shift with the user's risk level: a
conservative investor leans on quality and low volatility, an aggressive one
on momentum.
"""
from __future__ import annotations

from collections import Counter

from app.schemas.market_data_schemas import CandidateScore, ScoredStockCandidate, StockSnapshot

NEUTRAL_SCORE = 50.0

# Annualized volatility (%) that best "fits" each risk level 1..5.
TARGET_VOLATILITY_BY_RISK_LEVEL = {1: 16.0, 2: 21.0, 3: 27.0, 4: 34.0, 5: 42.0}

# (momentum, quality, valuation, risk_fit) weights per risk level; each row sums to 1.
SCORE_WEIGHTS_BY_RISK_LEVEL = {
    1: (0.10, 0.35, 0.20, 0.35),
    2: (0.20, 0.35, 0.20, 0.25),
    3: (0.30, 0.30, 0.20, 0.20),
    4: (0.40, 0.25, 0.15, 0.20),
    5: (0.50, 0.20, 0.10, 0.20),
}

MAX_SHORTLISTED_PER_SECTOR = 3


def scale_to_score(value: float, worst: float, best: float) -> float:
    """Linearly map `value` onto 0-100 where `worst`->0 and `best`->100 (clamped)."""
    if best == worst:
        return NEUTRAL_SCORE
    fraction = (value - worst) / (best - worst)
    return max(0.0, min(100.0, fraction * 100))


def momentum_score(snapshot: StockSnapshot) -> float:
    t = snapshot.technicals
    parts: list[tuple[float, float]] = []
    if t.return_6m_percent is not None:
        parts.append((scale_to_score(t.return_6m_percent, -30, 40), 0.4))
    if t.return_1y_percent is not None:
        parts.append((scale_to_score(t.return_1y_percent, -30, 60), 0.3))
    if t.price_vs_sma_200_percent is not None:
        parts.append((scale_to_score(t.price_vs_sma_200_percent, -20, 25), 0.3))
    score = _weighted_average(parts)
    if t.rsi_14 is not None and t.rsi_14 > 75:
        score -= 10  # stretched / overbought — momentum may be about to stall
    elif t.rsi_14 is not None and t.rsi_14 < 30:
        score -= 5
    return _clamp(score)


def quality_score(snapshot: StockSnapshot) -> float:
    f = snapshot.fundamentals
    parts: list[tuple[float, float]] = []
    if f.return_on_equity_percent is not None:
        parts.append((scale_to_score(f.return_on_equity_percent, 0, 30), 1.0))
    if f.profit_margin_percent is not None:
        parts.append((scale_to_score(f.profit_margin_percent, 0, 25), 1.0))
    if f.earnings_growth_percent is not None:
        parts.append((scale_to_score(f.earnings_growth_percent, -20, 40), 1.0))
    if f.debt_to_equity is not None:
        parts.append((scale_to_score(f.debt_to_equity, 2.5, 0), 1.0))
    return _clamp(_weighted_average(parts))


def valuation_score(snapshot: StockSnapshot) -> float:
    pe = snapshot.fundamentals.forward_pe or snapshot.fundamentals.trailing_pe
    if pe is None:
        return 40.0  # unknown or loss-making: slightly below neutral
    return scale_to_score(pe, 70, 10)


def risk_fit_score(snapshot: StockSnapshot, risk_level: int) -> float:
    volatility = snapshot.technicals.annualized_volatility_percent
    if volatility is None:
        return NEUTRAL_SCORE
    distance = abs(volatility - TARGET_VOLATILITY_BY_RISK_LEVEL[risk_level])
    score = scale_to_score(distance, 25, 0)
    drawdown = snapshot.technicals.max_drawdown_1y_percent
    if risk_level <= 2 and drawdown is not None and drawdown < -30:
        score -= 15  # conservative investors shouldn't hold things that recently fell 30%+
    return _clamp(score)


def score_candidate(snapshot: StockSnapshot, risk_level: int) -> CandidateScore:
    momentum = momentum_score(snapshot)
    quality = quality_score(snapshot)
    valuation = valuation_score(snapshot)
    risk_fit = risk_fit_score(snapshot, risk_level)
    w_momentum, w_quality, w_valuation, w_risk = SCORE_WEIGHTS_BY_RISK_LEVEL[risk_level]
    total = momentum * w_momentum + quality * w_quality + valuation * w_valuation + risk_fit * w_risk
    return CandidateScore(
        momentum_score=round(momentum, 1),
        quality_score=round(quality, 1),
        valuation_score=round(valuation, 1),
        risk_fit_score=round(risk_fit, 1),
        total_score=round(_clamp(total), 1),
    )


def shortlist_candidates(snapshots: list[StockSnapshot], risk_level: int, limit: int) -> list[ScoredStockCandidate]:
    """Highest total score first, capped per sector so the LLM sees a diversified set."""
    scored = sorted(
        (ScoredStockCandidate(snapshot=s, score=score_candidate(s, risk_level)) for s in snapshots),
        key=lambda candidate: candidate.score.total_score,
        reverse=True,
    )
    shortlisted: list[ScoredStockCandidate] = []
    per_sector: Counter[str] = Counter()
    for candidate in scored:
        sector = candidate.snapshot.sector or "Unknown"
        if per_sector[sector] >= MAX_SHORTLISTED_PER_SECTOR:
            continue
        shortlisted.append(candidate)
        per_sector[sector] += 1
        if len(shortlisted) == limit:
            break
    return shortlisted


def _weighted_average(parts: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in parts)
    if total_weight == 0:
        return NEUTRAL_SCORE
    return sum(value * weight for value, weight in parts) / total_weight


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))
