"""Make fund search forgiving: expand abbreviations/old names, then rank by relevance.

mfapi.in's search needs every word to appear in the scheme name, so a query like
"icici pru bluechip" finds nothing (the name says "Prudential" and the fund was
renamed "Large Cap"). We turn the user's words into a few likely spellings,
search them all, and rank the merged results by how well they match.
"""
from __future__ import annotations

import re

# Applied in order to the lower-cased query. Each maps a pattern to its replacement.
QUERY_ALIASES: list[tuple[str, str]] = [
    # Fund-house short forms
    (r"\bpru\b", "prudential"),
    (r"\bppfas\b", "parag parikh"),
    (r"\bppfcf\b", "parag parikh flexi cap"),
    (r"\b(absl|abslmf)\b", "aditya birla sun life"),
    (r"\bmo\b", "motilal oswal"),
    (r"\bmirae\b", "mirae asset"),
    (r"\bboi\b", "bank of india"),
    # Renamed schemes / SEBI category names
    (r"\bblue ?chip\b", "large cap"),
    (r"\blong term equity\b", "elss"),
    (r"\btax ?saver\b", "elss"),
    (r"\bemerging equity\b", "midcap"),
    (r"\bbalanced advantage\b", "balanced advantage"),
    # "midcap" -> "mid cap" etc. (the reverse spelling is tried as a separate variant)
    (r"\b(mid|small|large|multi|flexi)cap\b", r"\1 cap"),
]

# Words that appear in nearly every scheme name; searching with them only narrows results.
FILLER_WORDS = {"fund", "funds", "direct", "plan", "growth", "option", "the", "of", "scheme", "regular", "-"}
_WORD = re.compile(r"[a-z0-9&]+")
_ETF_OR_FOF = re.compile(r"exchange traded|\betf\b|\bfof\b|fund of funds?", re.IGNORECASE)


def query_variants(query: str) -> list[str]:
    """Distinct search strings to try, most likely first (max 3)."""
    original = " ".join(w for w in _WORD.findall(query.lower()) if w not in FILLER_WORDS)
    expanded = original
    for pattern, replacement in QUERY_ALIASES:
        expanded = re.sub(pattern, replacement, expanded)
    # Index funds tend to write "Midcap 150"; active funds write "Mid Cap".
    squashed = re.sub(r"\b(mid|small|large|multi|flexi) cap\b", r"\1cap", expanded)
    variants = [v.strip() for v in (expanded, original, squashed) if len(v.strip()) >= 3]
    return list(dict.fromkeys(variants))[:3]


def relevance_score(query: str, scheme_name: str, is_direct_growth: bool) -> float:
    """Higher is better: word overlap with the (expanded) query, Direct-Growth first, ETFs/FoFs last."""
    wanted = set(_WORD.findall(query_variants(query)[0] if query_variants(query) else query.lower()))
    name = scheme_name.lower()
    name_words = set(_WORD.findall(name)) - FILLER_WORDS
    # "mid cap" in the query should also match "midcap" in the name, and vice versa.
    joined_name = name.replace(" ", "")
    matched = sum(1 for w in wanted if w in name_words or w in joined_name)
    score = matched * 2.0
    # Words the user literally typed (e.g. an old name like "bluechip") count extra.
    typed = set(_WORD.findall(query.lower())) - FILLER_WORDS - wanted
    score += sum(1.0 for w in typed if w in joined_name)
    score -= 0.15 * len(name_words - wanted)  # prefer names without lots of extra words
    if is_direct_growth:
        score += 3
    if _ETF_OR_FOF.search(name) and not _ETF_OR_FOF.search(query):
        score -= 2.5
    return score
