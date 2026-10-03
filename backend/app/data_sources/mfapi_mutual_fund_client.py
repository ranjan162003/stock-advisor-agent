"""Indian mutual fund data from mfapi.in (free, no API key).

Provides scheme search and full daily NAV history with fund house and SEBI
category. It does not provide expense ratio or AUM, so the agent can't weigh those.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx
import pandas as pd

from app.core.app_exceptions import MarketDataError

logger = logging.getLogger(__name__)

MFAPI_BASE_URL = "https://api.mfapi.in/mf"
REQUEST_TIMEOUT_SECONDS = 20
_NOT_DIRECT_GROWTH = re.compile(r"idcw|dividend|bonus|payout|reinvest|segregated", re.IGNORECASE)


@dataclass
class FundNavHistory:
    scheme_code: int
    scheme_name: str
    fund_house: str | None
    category: str | None
    navs: pd.Series  # indexed by date, oldest first


def is_direct_growth_plan(scheme_name: str) -> bool:
    return (
        bool(re.search(r"direct", scheme_name, re.IGNORECASE))
        and bool(re.search(r"growth", scheme_name, re.IGNORECASE))
        and not _NOT_DIRECT_GROWTH.search(scheme_name)
    )


def search_mutual_funds(query: str) -> list[dict]:
    """Return `[{"schemeCode": int, "schemeName": str}, ...]` matching the query."""
    try:
        response = httpx.get(f"{MFAPI_BASE_URL}/search", params={"q": query}, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise MarketDataError(f"Mutual fund search is unavailable right now: {exc}") from exc


def fetch_fund_nav_history(scheme_code: int) -> FundNavHistory | None:
    """Full NAV history for one scheme, or None if the code is unknown or the API fails."""
    try:
        response = httpx.get(f"{MFAPI_BASE_URL}/{scheme_code}", timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("NAV history unavailable for scheme %s: %s", scheme_code, exc)
        return None

    meta = payload.get("meta") or {}
    rows = payload.get("data") or []
    if not meta.get("scheme_name") or not rows:
        return None

    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"], format="%d-%m-%Y", errors="coerce")
    frame["nav"] = pd.to_numeric(frame["nav"], errors="coerce")
    navs = frame.dropna().query("nav > 0").set_index("date")["nav"].sort_index()
    navs = navs[~navs.index.duplicated(keep="last")]
    return FundNavHistory(
        scheme_code=int(meta.get("scheme_code") or scheme_code),
        scheme_name=meta["scheme_name"],
        fund_house=meta.get("fund_house"),
        category=meta.get("scheme_category"),
        navs=navs,
    )
