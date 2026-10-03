"""Turn an LLM's free-form reply into a validated, normalized set of picks.

LLMs (especially small local ones) wrap JSON in prose or fences, invent
tickers, or give weights that don't sum to 100. This module tolerates all of
that and only raises when nothing usable is left.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.core.app_exceptions import RecommendationParseError

FENCED_JSON_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass
class ParsedPick:
    ticker: str
    weight_percent: float
    rationale: str


@dataclass
class ParsedRecommendation:
    picks: list[ParsedPick]
    summary: str
    risk_notes: list[str] = field(default_factory=list)


def parse_recommendation_reply(raw_reply: str, allowed_tickers: set[str], max_picks: int) -> ParsedRecommendation:
    payload = _extract_json_object(raw_reply)

    raw_picks = payload.get("picks")
    if not isinstance(raw_picks, list) or not raw_picks:
        raise RecommendationParseError("The model's reply had no 'picks' list.")

    picks = _clean_picks(raw_picks, allowed_tickers)
    if not picks:
        raise RecommendationParseError("None of the model's picks were valid tickers from the candidate list.")

    picks = sorted(picks, key=lambda p: p.weight_percent, reverse=True)[:max_picks]
    _normalize_weights_to_100(picks)

    risk_notes = payload.get("risk_notes") or []
    return ParsedRecommendation(
        picks=picks,
        summary=str(payload.get("summary") or "").strip(),
        risk_notes=[str(note).strip() for note in risk_notes if str(note).strip()] if isinstance(risk_notes, list) else [],
    )


def _extract_json_object(raw_reply: str) -> dict:
    text = raw_reply.strip()
    candidates = [text]
    fenced = FENCED_JSON_PATTERN.search(text)
    if fenced:
        candidates.insert(0, fenced.group(1))
    first_brace, last_brace = text.find("{"), text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidates.append(text[first_brace : last_brace + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise RecommendationParseError("The model's reply wasn't valid JSON.")


def _clean_picks(raw_picks: list, allowed_tickers: set[str]) -> list[ParsedPick]:
    allowed_by_upper = {t.upper(): t for t in allowed_tickers}
    merged: dict[str, ParsedPick] = {}
    for item in raw_picks:
        if not isinstance(item, dict):
            continue
        ticker = allowed_by_upper.get(str(item.get("ticker", "")).strip().upper())
        try:
            weight = float(item.get("weight_percent", 0))
        except (TypeError, ValueError):
            continue
        if not ticker or weight <= 0:
            continue
        rationale = str(item.get("rationale") or "").strip()
        if ticker in merged:  # duplicate ticker — combine rather than drop
            merged[ticker].weight_percent += weight
        else:
            merged[ticker] = ParsedPick(ticker=ticker, weight_percent=weight, rationale=rationale)
    return list(merged.values())


def _normalize_weights_to_100(picks: list[ParsedPick]) -> None:
    total = sum(p.weight_percent for p in picks)
    for pick in picks:
        pick.weight_percent = round(pick.weight_percent / total * 100, 1)
    # Push the rounding remainder onto the largest pick so the split is exactly 100.
    picks[0].weight_percent = round(picks[0].weight_percent + 100 - sum(p.weight_percent for p in picks), 1)
