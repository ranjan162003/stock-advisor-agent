"""The full list of active Indian mutual fund schemes, from AMFI's daily NAV file.

AMFI (the industry body) publishes every scheme that reported a NAV today, so
closed or merged schemes drop out automatically. The file is ~1.5 MB of
semicolon-separated rows, grouped under category and fund-house heading lines:

    Open Ended Schemes(Equity Scheme - Flexi Cap Fund)      <- category heading
    PPFAS Mutual Fund                                        <- fund house heading
    122639;INF879O01027;-;Parag Parikh Flexi Cap Fund;Direct Plan;Growth;88.2569;01-Oct-2026
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime

import httpx

from app.core.app_exceptions import MarketDataError

logger = logging.getLogger(__name__)

AMFI_NAV_ALL_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"
REQUEST_TIMEOUT_SECONDS = 60
_CATEGORY_HEADING = re.compile(r"^(?P<type>.+?Schemes?)\s*\((?P<category>.+)\)\s*$")


@dataclass
class CatalogFund:
    scheme_code: int
    scheme_name: str
    fund_house: str | None
    scheme_type: str | None  # "Open Ended Schemes", "Close Ended Schemes", …
    category: str | None  # "Equity Scheme - Flexi Cap Fund"
    plan: str | None  # "Direct Plan" / "Regular Plan"
    option: str | None  # "Growth" / "IDCW Option" / …
    isin: str | None
    nav: float | None
    nav_date: date | None


def download_amfi_catalog() -> list[CatalogFund]:
    try:
        response = httpx.get(AMFI_NAV_ALL_URL, timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise MarketDataError(f"Couldn't download the AMFI fund list: {exc}") from exc
    funds = parse_amfi_nav_file(response.text)
    if not funds:
        raise MarketDataError("The AMFI fund list came back empty.")
    logger.info("Downloaded AMFI catalog: %d schemes", len(funds))
    return funds


def parse_amfi_nav_file(text: str) -> list[CatalogFund]:
    funds: list[CatalogFund] = []
    scheme_type = category = fund_house = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("Scheme Code"):
            continue
        if ";" not in line:
            heading = _CATEGORY_HEADING.match(line)
            if heading:
                scheme_type, category = heading.group("type").strip(), heading.group("category").strip()
            else:
                fund_house = line
            continue
        parts = [part.strip() for part in line.split(";")]
        if len(parts) < 8 or not parts[0].isdigit():
            continue
        funds.append(
            CatalogFund(
                scheme_code=int(parts[0]),
                scheme_name=parts[3],
                fund_house=fund_house,
                scheme_type=scheme_type,
                category=category,
                plan=_blank_to_none(parts[4]),
                option=_blank_to_none(parts[5]),
                isin=parts[1] if parts[1] not in ("", "-") else None,
                nav=_parse_float(parts[6]),
                nav_date=_parse_date(parts[7]),
            )
        )
    return funds


def _blank_to_none(value: str) -> str | None:
    """AMFI writes "-" (or nothing) when the plan/option is part of the scheme name instead."""
    return value if value and value != "-" else None


def _parse_float(value: str) -> float | None:
    try:
        number = float(value)
    except ValueError:
        return None
    return number if number > 0 else None


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%d-%b-%Y").date()
    except ValueError:
        return None
