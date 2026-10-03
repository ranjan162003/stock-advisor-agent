"""Turn an LLM's free-form reply into a validated, normalized set of picks.

LLMs (especially small local ones) wrap JSON in prose or fences, invent
tickers, or give weights that don't sum to 100. This module tolerates all of
that and only raises when nothing usable is left.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from app.core.app_exceptions import RecommendationParseError

logger = logging.getLogger(__name__)

FENCED_JSON_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
# strict=False lets raw line breaks/tabs inside strings through — models often write them in long prose.
_LENIENT_DECODER = json.JSONDecoder(strict=False)


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
    payload = extract_json_object(raw_reply)

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


def extract_json_object(raw_reply: str) -> dict:
    """The first JSON object in a model reply, tolerating the usual slips.

    Handles: markdown fences, prose before or after the object (even prose that
    contains braces), raw line breaks inside strings, and unescaped double quotes
    inside strings (`"the "defensive" pick"`).
    """
    text = raw_reply.strip()
    starts = []
    fenced = FENCED_JSON_PATTERN.search(text)
    if fenced:
        starts.append(fenced.group(1))
    first_brace = text.find("{")
    if first_brace != -1:
        starts.append(text[first_brace:])

    first_error: json.JSONDecodeError | None = None
    for candidate in starts:
        for attempt in (candidate, escape_stray_quotes(candidate)):
            try:
                # raw_decode stops at the end of the first complete object and ignores what follows.
                parsed, _ = _LENIENT_DECODER.raw_decode(attempt)
            except json.JSONDecodeError as exc:
                first_error = first_error or exc
                continue
            if isinstance(parsed, dict):
                return parsed

    if first_error is not None:
        at = first_error.pos
        logger.warning(
            "Model reply isn't valid JSON: %s (reply is %d chars). Around the problem: %r",
            first_error.msg, len(text), first_error.doc[max(0, at - 150) : at + 150],
        )
        if _is_cut_off(first_error.doc):
            raise RecommendationParseError("The model's reply was cut off before the JSON ended.")
    raise RecommendationParseError("The model's reply wasn't valid JSON.")


def _is_cut_off(text: str) -> bool:
    """True if the text ends inside a string or with braces/brackets still open."""
    depth, in_string, escaped = 0, False, False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
    return in_string or depth > 0


def escape_stray_quotes(text: str) -> str:
    """Escape double quotes that sit *inside* a JSON string.

    A quote ends a string only if the next non-space character is one that can
    follow a string value (`,` `:` `}` `]`) or the text ends; any other quote is
    part of the prose and gets escaped. Best-effort — only used after a strict
    parse has already failed.
    """
    out: list[str] = []
    in_string = False
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if in_string and ch == "\\":
            out.append(text[i : i + 2])
            i += 2
            continue
        if ch == '"':
            if not in_string:
                in_string = True
                out.append(ch)
            else:
                j = i + 1
                while j < n and text[j] in " \t\r\n":
                    j += 1
                if j >= n or text[j] in ",:}]":
                    in_string = False
                    out.append(ch)
                else:
                    out.append('\\"')
        else:
            out.append(ch)
        i += 1
    return "".join(out)


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
