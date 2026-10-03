"""Rule-based pre-scoring that shortlists mutual funds before the LLM sees them.

Every sub-score is 0-100. Funds are matched to the investor mostly through
`risk_class` (debt … small cap) rather than raw volatility, because a fund's
category is the main thing that decides how it behaves in a downturn.
"""
from __future__ import annotations

from collections import Counter

from app.analysis.candidate_scoring import NEUTRAL_SCORE, scale_to_score
from app.schemas.mutual_fund_schemas import FundScore, FundSnapshot, ScoredFundCandidate

# (returns, risk-adjusted, downside, risk fit) weights per investor risk level; rows sum to 1.
FUND_SCORE_WEIGHTS_BY_RISK_LEVEL = {
    1: (0.10, 0.20, 0.25, 0.45),
    2: (0.15, 0.25, 0.20, 0.40),
    3: (0.25, 0.25, 0.15, 0.35),
    4: (0.35, 0.20, 0.10, 0.35),
    5: (0.40, 0.20, 0.05, 0.35),
}

MAX_SHORTLISTED_PER_CATEGORY = 2


def returns_score(snapshot: FundSnapshot) -> float:
    m = snapshot.metrics
    long_run = m.cagr_5y_percent if m.cagr_5y_percent is not None else m.cagr_3y_percent
    parts = []
    if long_run is not None:
        parts.append(scale_to_score(long_run, 0, 25))
    if m.return_1y_percent is not None:
        parts.append(scale_to_score(m.return_1y_percent, -15, 35) * 0.5 + NEUTRAL_SCORE * 0.5)
    return sum(parts) / len(parts) if parts else NEUTRAL_SCORE


def risk_adjusted_score(snapshot: FundSnapshot) -> float:
    sharpe = snapshot.metrics.sharpe_ratio_3y
    return NEUTRAL_SCORE if sharpe is None else scale_to_score(sharpe, -0.5, 1.5)


def downside_score(snapshot: FundSnapshot) -> float:
    drawdown = snapshot.metrics.max_drawdown_3y_percent
    return NEUTRAL_SCORE if drawdown is None else scale_to_score(drawdown, -40, 0)


def fund_risk_fit_score(snapshot: FundSnapshot, risk_level: int) -> float:
    return max(0.0, 100 - 30 * abs(snapshot.risk_class - risk_level))


def score_fund(snapshot: FundSnapshot, risk_level: int) -> FundScore:
    returns = returns_score(snapshot)
    risk_adjusted = risk_adjusted_score(snapshot)
    downside = downside_score(snapshot)
    risk_fit = fund_risk_fit_score(snapshot, risk_level)
    w_ret, w_adj, w_down, w_fit = FUND_SCORE_WEIGHTS_BY_RISK_LEVEL[risk_level]
    total = returns * w_ret + risk_adjusted * w_adj + downside * w_down + risk_fit * w_fit
    return FundScore(
        returns_score=round(returns, 1),
        risk_adjusted_score=round(risk_adjusted, 1),
        downside_score=round(downside, 1),
        risk_fit_score=round(risk_fit, 1),
        total_score=round(max(0.0, min(100.0, total)), 1),
    )


def shortlist_funds(snapshots: list[FundSnapshot], risk_level: int, limit: int) -> list[ScoredFundCandidate]:
    """Highest total score first, capped per category so the LLM sees a diversified set."""
    scored = sorted(
        (ScoredFundCandidate(snapshot=s, score=score_fund(s, risk_level)) for s in snapshots),
        key=lambda candidate: candidate.score.total_score,
        reverse=True,
    )
    shortlisted: list[ScoredFundCandidate] = []
    per_category: Counter[str] = Counter()
    for candidate in scored:
        category = candidate.snapshot.category or "Other"
        if per_category[category] >= MAX_SHORTLISTED_PER_CATEGORY:
            continue
        shortlisted.append(candidate)
        per_category[category] += 1
        if len(shortlisted) == limit:
            break
    return shortlisted
