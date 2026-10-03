"""Parse holdings pasted from a broker export (Zerodha, Groww, Upstox, Coin, …).

Brokers name their columns differently, so we look for any recognisable
symbol/name column and quantity/units column. Each row is then resolved:

* `TCS`, `TCS.NS`, `M&M`           -> stock ticker
* `MF:122639` or `122639`          -> mutual fund by AMFI scheme code
* `Parag Parikh Flexi Cap Fund…`   -> mutual fund, matched via mfapi search
* `Tata Consultancy Services`      -> stock, matched via Yahoo search

Every match is returned for the user to confirm before rebalancing.
"""
from __future__ import annotations

import csv
import io
import logging
import re
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

from app.core.app_exceptions import InvalidRequestError, MarketDataError
from app.data_sources.default_fund_universe import fund_symbol, is_fund_symbol, short_fund_name
from app.data_sources.default_stock_universe import normalize_ticker
from app.data_sources.mfapi_mutual_fund_client import search_mutual_funds
from app.schemas.rebalance_schemas import HoldingsImportResponse, ParsedHolding
from app.schemas.recommendation_schemas import AssetType

logger = logging.getLogger(__name__)

MAX_ROWS = 100
SYMBOL_COLUMN_NAMES = [
    "instrument", "tradingsymbol", "trading symbol", "symbol", "ticker", "scrip", "stock", "stock name",
    "scheme", "scheme name", "fund", "fund name", "company", "company name", "name", "security",
]
QUANTITY_COLUMN_NAMES = [
    "qty", "qty.", "quantity", "units", "balance units", "no. of units", "shares", "holding", "holdings",
    "available qty", "quantity available",
]
_TICKER_PATTERN = re.compile(r"^(MF:)?[A-Z0-9&\-]{1,20}(\.(NS|BO))?$")
_FUND_WORDS = re.compile(r"\b(fund|scheme|plan|growth|idcw|direct|regular|index|fof|etf)\b", re.IGNORECASE)
_WORD = re.compile(r"[a-z0-9&]+")


def import_holdings(text: str) -> HoldingsImportResponse:
    rows, detected = _read_rows(text)
    if not rows:
        raise InvalidRequestError("Couldn't find any holdings in that text. Paste rows like: TCS, 10")
    if len(rows) > MAX_ROWS:
        raise InvalidRequestError(f"That's more than {MAX_ROWS} holdings; import them in smaller batches.")
    with ThreadPoolExecutor(max_workers=8) as pool:
        holdings = list(pool.map(lambda row: _resolve_row(*row), rows))
    return HoldingsImportResponse(holdings=holdings, detected_columns=detected)


def _read_rows(text: str) -> tuple[list[tuple[str, str]], dict[str, str]]:
    """(symbol text, quantity text) per row, plus which columns were used."""
    lines = [line for line in text.strip().splitlines() if line.strip()]
    if not lines:
        return [], {}
    try:
        dialect = csv.Sniffer().sniff("\n".join(lines[:5]), delimiters=",\t;|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = "\t" if "\t" in lines[0] else ","
    table = [[cell.strip().strip('"') for cell in row] for row in csv.reader(io.StringIO("\n".join(lines)), delimiter=delimiter)]

    header = [cell.lower() for cell in table[0]]
    symbol_col = _find_column(header, SYMBOL_COLUMN_NAMES)
    quantity_col = _find_column(header, QUANTITY_COLUMN_NAMES)
    if symbol_col is not None and quantity_col is not None:
        detected = {"symbol": table[0][symbol_col], "quantity": table[0][quantity_col]}
        body = table[1:]
    else:
        # No recognisable header: assume "symbol, quantity" rows.
        symbol_col, quantity_col = 0, 1
        detected = {}
        body = table[1:] if not _looks_numeric(table[0][1] if len(table[0]) > 1 else "") else table

    rows = [
        (row[symbol_col], row[quantity_col])
        for row in body
        if len(row) > max(symbol_col, quantity_col) and row[symbol_col] and not row[symbol_col].lower().startswith("total")
    ]
    return rows, detected


def _find_column(header: list[str], names: list[str]) -> int | None:
    for name in names:  # names are in priority order
        if name in header:
            return header.index(name)
    return None


def _looks_numeric(value: str) -> bool:
    return _parse_quantity(value) is not None


def _parse_quantity(value: str) -> float | None:
    try:
        quantity = float(value.replace(",", "").strip())
    except ValueError:
        return None
    return quantity if quantity > 0 else None


def _resolve_row(symbol_text: str, quantity_text: str) -> ParsedHolding:
    quantity = _parse_quantity(quantity_text)
    base = ParsedHolding(
        input_text=symbol_text, symbol=None, display_name=None, asset_type=None, quantity=quantity, matched=False
    )
    if quantity is None:
        return base.model_copy(update={"note": f"Couldn't read the quantity “{quantity_text}”."})

    cleaned = symbol_text.strip()
    try:
        if cleaned.isdigit():
            return base.model_copy(update={"symbol": fund_symbol(int(cleaned)), "display_name": f"Scheme {cleaned}",
                                           "asset_type": AssetType.MUTUAL_FUND, "matched": True})
        # Broker exports write tickers in capitals; "Infosys" is a name to look up, "INFY" is a ticker.
        if _TICKER_PATTERN.match(cleaned) or is_fund_symbol(cleaned):
            if is_fund_symbol(cleaned):
                return base.model_copy(update={"symbol": cleaned.upper(), "display_name": cleaned.upper(),
                                               "asset_type": AssetType.MUTUAL_FUND, "matched": True})
            ticker = normalize_ticker(cleaned)
            return base.model_copy(update={"symbol": ticker, "display_name": ticker.removesuffix(".NS").removesuffix(".BO"),
                                           "asset_type": AssetType.STOCK, "matched": True})
        if _FUND_WORDS.search(cleaned):
            return _match_fund_by_name(base, cleaned)
        return _match_stock_by_name(base, cleaned)
    except (MarketDataError, ValueError) as exc:
        return base.model_copy(update={"note": str(exc)})


def _match_fund_by_name(base: ParsedHolding, name: str) -> ParsedHolding:
    query = " ".join(_WORD.findall(re.split(r"\s+-\s+|\(", name, maxsplit=1)[0].lower())[:5])
    candidates = search_mutual_funds(query) if len(query) >= 3 else []
    if not candidates:
        return base.model_copy(update={"note": "No matching mutual fund found — add it by scheme code instead."})
    best = max(candidates, key=lambda c: _fund_match_score(name, c["schemeName"]))
    return base.model_copy(update={
        "symbol": fund_symbol(int(best["schemeCode"])),
        "display_name": short_fund_name(best["schemeName"]),
        "asset_type": AssetType.MUTUAL_FUND,
        "matched": True,
        "note": f"Matched to “{best['schemeName']}” — check the plan (Direct/Regular, Growth/IDCW).",
    })


def _fund_match_score(wanted: str, candidate: str) -> float:
    wanted_words, candidate_words = set(_WORD.findall(wanted.lower())), set(_WORD.findall(candidate.lower()))
    score = len(wanted_words & candidate_words) - 0.1 * len(candidate_words - wanted_words)
    # Brokers usually spell out the plan; respect it, otherwise assume Direct-Growth.
    for wanted_plan, other_plan in (("regular", "direct"), ("idcw", "growth")):
        if wanted_plan in wanted_words:
            score += 2 if wanted_plan in candidate_words else -2
        elif other_plan in candidate_words:
            score += 1
    return score


def _match_stock_by_name(base: ParsedHolding, name: str) -> ParsedHolding:
    try:
        quotes = yf.Search(name, max_results=8).quotes or []
    except Exception as exc:  # yfinance search raises assorted transport errors
        logger.warning("Stock search failed for %r: %s", name, exc)
        quotes = []
    indian = [q for q in quotes if str(q.get("symbol", "")).endswith((".NS", ".BO"))]
    if not indian:
        return base.model_copy(update={"note": "No NSE/BSE stock found with that name — enter its ticker instead."})
    best = next((q for q in indian if q["symbol"].endswith(".NS")), indian[0])
    ticker = best["symbol"]
    return base.model_copy(update={
        "symbol": ticker,
        "display_name": ticker.removesuffix(".NS").removesuffix(".BO"),
        "asset_type": AssetType.STOCK,
        "matched": True,
        "note": f"Matched to {best.get('shortname') or best.get('longname') or ticker}.",
    })
