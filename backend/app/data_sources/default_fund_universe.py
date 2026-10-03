"""Default mutual-fund universe: popular Direct-Growth schemes across categories.

Scheme codes are AMFI codes as served by mfapi.in. `risk_class` is our own 1–5
rating used to match funds to the investor's risk level:
1 liquid/debt · 2 hybrid · 3 large cap/flexi/gold · 4 mid cap/large & mid · 5 small cap.
"""
from __future__ import annotations

import re

from app.schemas.mutual_fund_schemas import UniverseFund

FUND_SYMBOL_PREFIX = "MF:"

DEFAULT_FUND_UNIVERSE: list[UniverseFund] = [
    UniverseFund(scheme_code=120716, short_name="UTI Nifty 50 Index", category="Index · Large cap", risk_class=3),
    UniverseFund(scheme_code=147666, short_name="Axis Nifty 100 Index", category="Index · Large cap", risk_class=3),
    UniverseFund(scheme_code=120684, short_name="ICICI Pru Nifty Next 50 Index", category="Index · Large cap", risk_class=4),
    UniverseFund(scheme_code=147622, short_name="Motilal Oswal Midcap 150 Index", category="Index · Mid cap", risk_class=4),
    UniverseFund(scheme_code=120586, short_name="ICICI Pru Large Cap", category="Large cap", risk_class=3),
    UniverseFund(scheme_code=118632, short_name="Nippon India Large Cap", category="Large cap", risk_class=3),
    UniverseFund(scheme_code=122639, short_name="Parag Parikh Flexi Cap", category="Flexi cap", risk_class=3),
    UniverseFund(scheme_code=118955, short_name="HDFC Flexi Cap", category="Flexi cap", risk_class=3),
    UniverseFund(scheme_code=118834, short_name="Mirae Asset Large & Midcap", category="Large & mid cap", risk_class=4),
    UniverseFund(scheme_code=118989, short_name="HDFC Mid Cap", category="Mid cap", risk_class=4),
    UniverseFund(scheme_code=118778, short_name="Nippon India Small Cap", category="Small cap", risk_class=5),
    UniverseFund(scheme_code=125497, short_name="SBI Small Cap", category="Small cap", risk_class=5),
    UniverseFund(scheme_code=135781, short_name="Mirae Asset ELSS Tax Saver", category="ELSS (tax saver)", risk_class=3),
    UniverseFund(scheme_code=118968, short_name="HDFC Balanced Advantage", category="Hybrid · Balanced advantage", risk_class=2),
    UniverseFund(scheme_code=120334, short_name="ICICI Pru Multi Asset", category="Hybrid · Multi asset", risk_class=2),
    UniverseFund(scheme_code=118987, short_name="HDFC Corporate Bond", category="Debt · Corporate bond", risk_class=1),
    UniverseFund(scheme_code=119800, short_name="SBI Liquid", category="Debt · Liquid", risk_class=1),
    UniverseFund(scheme_code=119788, short_name="SBI Gold", category="Gold", risk_class=3),
]

DEFAULT_FUNDS_BY_CODE = {fund.scheme_code: fund for fund in DEFAULT_FUND_UNIVERSE}

# (pattern, risk class) checked in order against "<category> <scheme name>", lowercased.
_RISK_CLASS_RULES: list[tuple[str, int]] = [
    (r"liquid|overnight|money market|arbitrage", 1),
    (r"gilt|bond|debt|duration|banking and psu|credit risk|floater|income", 1),
    (r"small ?cap|sectoral|thematic", 5),
    (r"mid ?cap|large & mid|large and mid|next 50|international|overseas|global", 4),
    (r"conservative hybrid|equity savings|balanced advantage|dynamic asset|multi asset|multi-asset", 2),
    (r"gold|silver|aggressive hybrid|large ?cap|nifty 50|nifty 100|sensex|flexi|multi ?cap|elss|focused|value|contra|dividend yield|index", 3),
]


def fund_symbol(scheme_code: int) -> str:
    return f"{FUND_SYMBOL_PREFIX}{scheme_code}"


def is_fund_symbol(symbol: str) -> bool:
    return symbol.upper().startswith(FUND_SYMBOL_PREFIX)


def scheme_code_from_symbol(symbol: str) -> int:
    return int(symbol[len(FUND_SYMBOL_PREFIX):])


def infer_fund_risk_class(category: str | None, scheme_name: str) -> int:
    """Estimate a 1–5 risk class for any fund from its SEBI category and name."""
    text = f"{category or ''} {scheme_name}".lower()
    for pattern, risk_class in _RISK_CLASS_RULES:
        if re.search(pattern, text):
            return risk_class
    return 3


def short_fund_name(scheme_name: str) -> str:
    """'Parag Parikh Flexi Cap Fund - Direct Plan - Growth' -> 'Parag Parikh Flexi Cap'."""
    name = re.split(r"\s+-\s+|\(", scheme_name, maxsplit=1)[0]
    name = re.sub(r"\s+fund$", "", name.strip(), flags=re.IGNORECASE)
    return name.strip() or scheme_name
