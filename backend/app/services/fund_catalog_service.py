"""Local catalog of every active open-ended mutual fund, searchable as you type.

The AMFI list is downloaded at most once a day into SQLite, and an in-memory
index is built from it so each keystroke searches ~9,000 schemes locally in a
few milliseconds — no network round-trip, and no exact spelling needed.
"""
from __future__ import annotations

import logging
import re
import threading
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.app_exceptions import MarketDataError
from app.data_sources.amfi_fund_catalog_client import CatalogFund, download_amfi_catalog
from app.data_sources.default_fund_universe import DEFAULT_FUNDS_BY_CODE
from app.data_sources.fund_search_aliases import FILLER_WORDS, query_variants, relevance_score
from app.data_sources.mfapi_mutual_fund_client import is_direct_growth_plan
from app.db.orm_models import FundCatalogEntry
from app.db.repositories.fund_catalog_repository import latest_catalog_refresh, list_catalog_entries, replace_catalog
from app.schemas.mutual_fund_schemas import FundCategory, FundSearchResult

logger = logging.getLogger(__name__)

CATALOG_MAX_AGE = timedelta(hours=24)
STALE_NAV_DAYS = 30  # a scheme with no NAV for a month has been closed or merged
SIP_ELIGIBLE_TYPES = ("Open Ended", "Interval")
POPULAR_FUND_BOOST = 1.5  # well-known funds win ties ("parag" -> Flexi Cap, not Arbitrage)
_WORD = re.compile(r"[a-z0-9&]+")


@dataclass
class IndexedFund:
    result: FundSearchResult
    words: list[str]
    squashed: str  # lower-case name with spaces removed, so "midcap" matches "Mid Cap"


_index: list[IndexedFund] = []
_index_built_at: datetime | None = None
_lock = threading.Lock()


# ---------------------------------------------------------------- loading


def ensure_catalog(session: Session) -> list[IndexedFund]:
    """Return the search index, downloading a fresh AMFI list if the stored one is over a day old."""
    global _index, _index_built_at
    with _lock:
        refresh = latest_catalog_refresh(session)
        refreshed_at = _as_utc(refresh.refreshed_at) if refresh else None
        if refreshed_at is None or datetime.now(timezone.utc) - refreshed_at > CATALOG_MAX_AGE:
            try:
                refreshed_at = _download_into_db(session)
            except MarketDataError as exc:
                if refreshed_at is None:
                    raise
                logger.warning("AMFI refresh failed, keeping the catalog from %s: %s", refreshed_at, exc.message)
        if _index_built_at != refreshed_at:
            _index = [_index_entry(entry) for entry in list_catalog_entries(session)]
            _index_built_at = refreshed_at
            logger.info("Fund search index built: %d schemes", len(_index))
        return _index


def _download_into_db(session: Session) -> datetime:
    today = date.today()
    entries = [
        _to_entry(fund)
        for fund in download_amfi_catalog()
        if fund.scheme_type
        and fund.scheme_type.startswith(SIP_ELIGIBLE_TYPES)
        and fund.nav_date
        and (today - fund.nav_date).days <= STALE_NAV_DAYS
    ]
    refreshed_at = datetime.now(timezone.utc)
    replace_catalog(session, entries, refreshed_at)
    return refreshed_at


def _to_entry(fund: CatalogFund) -> FundCatalogEntry:
    plan_text = " ".join(filter(None, [fund.scheme_name, fund.plan, fund.option]))
    return FundCatalogEntry(
        scheme_code=fund.scheme_code,
        scheme_name=fund.scheme_name,
        fund_house=fund.fund_house,
        category=fund.category,
        plan=fund.plan,
        option=fund.option,
        is_direct_growth=is_direct_growth_plan(plan_text),
        nav=fund.nav,
        nav_date=fund.nav_date,
    )


def _index_entry(entry: FundCatalogEntry) -> IndexedFund:
    full_name = full_scheme_name(entry.scheme_name, entry.plan, entry.option)
    group, label = split_category(entry.category)
    lowered = f"{full_name} {entry.fund_house or ''}".lower()
    return IndexedFund(
        result=FundSearchResult(
            scheme_code=entry.scheme_code,
            scheme_name=full_name,
            is_direct_growth=entry.is_direct_growth,
            fund_house=entry.fund_house,
            category=entry.category,
            category_group=group,
            category_label=label,
            nav=entry.nav,
            nav_date=entry.nav_date.isoformat() if entry.nav_date else None,
        ),
        words=[w for w in _WORD.findall(lowered) if w not in FILLER_WORDS],
        squashed=lowered.replace(" ", ""),
    )


# ---------------------------------------------------------------- searching


def search_catalog(
    session: Session, query: str, category: str | None = None, include_all_plans: bool = False, limit: int = 20
) -> list[FundSearchResult]:
    index = ensure_catalog(session)
    candidates = [
        item
        for item in index
        if (include_all_plans or item.result.is_direct_growth) and (not category or category_key(item.result) == category)
    ]
    query = query.strip()
    if not query:
        # Browsing (all funds, or one category): well-known funds first, then A–Z.
        browse_order = sorted(
            candidates,
            key=lambda i: (i.result.scheme_code not in DEFAULT_FUNDS_BY_CODE, i.result.scheme_name.lower()),
        )
        return [item.result for item in browse_order[:limit]]

    for variant in query_variants(query) or [query.lower()]:
        tokens = [t for t in _WORD.findall(variant) if t not in FILLER_WORDS]
        matches = [item for item in candidates if all(_token_matches(t, item) for t in tokens)]
        if matches:
            ranked = sorted(
                matches,
                key=lambda i: (
                    -(relevance_score(query, i.result.scheme_name, i.result.is_direct_growth)
                      + (POPULAR_FUND_BOOST if i.result.scheme_code in DEFAULT_FUNDS_BY_CODE else 0)),
                    i.result.scheme_name,
                ),
            )
            return [item.result for item in ranked[:limit]]
    return []


def _token_matches(token: str, item: IndexedFund) -> bool:
    return any(word.startswith(token) for word in item.words) or (len(token) >= 4 and token in item.squashed)


def list_catalog_categories(session: Session, include_all_plans: bool = False) -> list[FundCategory]:
    index = ensure_catalog(session)
    # AMFI spells some headings two ways ("Equity Scheme"/"Equity Schemes"), so group by the cleaned key.
    counts = Counter(
        (item.result.category_group, item.result.category_label)
        for item in index
        if item.result.category and (include_all_plans or item.result.is_direct_growth)
    )
    categories = [
        FundCategory(category=f"{group} · {label}", group=group, label=label, fund_count=count)
        for (group, label), count in counts.items()
    ]
    return sorted(categories, key=lambda c: (_GROUP_ORDER.get(c.group, 99), c.label))


def find_catalog_fund(session: Session, scheme_code: int) -> FundSearchResult | None:
    return next((item.result for item in ensure_catalog(session) if item.result.scheme_code == scheme_code), None)


# ---------------------------------------------------------------- naming helpers

_GROUP_ORDER = {"Equity": 0, "Index & ETF": 1, "Hybrid": 2, "Debt": 3, "Fund of Funds": 4, "Solution Oriented": 5, "Other": 6}


def category_key(result: FundSearchResult) -> str:
    return f"{result.category_group} · {result.category_label}"


# AMFI's file mixes the current SEBI category names with an older naming scheme,
# so the same bucket can appear twice. These maps fold both onto one set.
_GROUP_ALIASES = {
    "income/debt oriented": "Debt",
    "income": "Debt",
    "index funds": "Index & ETF",
    "exchange traded funds (etfs)": "Index & ETF",
    "fund of funds scheme (domestic)": "Fund of Funds",
    "overseas fund of funds": "Fund of Funds",
    "children’s fund": "Solution Oriented",
    "children's fund": "Solution Oriented",
    "life cycle funds": "Solution Oriented",
}
_LABEL_ALIASES = {
    "banking and psu debt": "Banking and PSU",
    "short term": "Short Duration",
    "ultra short term": "Ultra Short Duration",
    "medium term": "Medium Duration",
    "medium to long term": "Medium to Long Duration",
    "long term": "Long Duration",
    "dynamic term": "Dynamic Bond",
    "floating interest rates": "Floater",
    "10-year constant maturity gilt": "Gilt (10-year constant maturity)",
    "balanced advantage fund/ dynamic asset allocation": "Balanced Advantage",
    "dynamic asset allocation or balanced advantage": "Balanced Advantage",
    "children’s": "Children's",
    "childrens'": "Children's",
    "fund of funds scheme (domestic)": "FoF Domestic",
    "fund of funds investing overseas": "FoF Overseas",
    "other etf": "Other ETFs",
}


def split_category(category: str | None) -> tuple[str, str]:
    """'Equity Scheme - Flexi Cap Fund' -> ('Equity', 'Flexi Cap'), with old/new AMFI names unified."""
    if not category:
        return "Other", "Uncategorised"
    head, _, tail = category.partition(" - ")
    group = re.sub(r"\s*Schemes?\s*\**$", "", head.replace("**", "")).strip() or "Other"
    label = re.sub(r"\s+Funds?$", "", (tail or head).strip()) or category
    label = re.sub(r"\s+", " ", re.sub(r"^ELSS\b.*", "ELSS", label)).strip()
    if re.fullmatch(r"(?i)sectoral|thematic|sectoral\s*/\s*thematic", label):
        label = "Sectoral / Thematic"
    if label.lower().startswith("life cycle"):
        label = "Life Cycle"

    group = _GROUP_ALIASES.get(group.lower(), group)
    label = _LABEL_ALIASES.get(label.lower(), label)
    if group == "Index & ETF" and label in ("Debt", "Equity", "Hybrid"):
        label = f"{label} index"  # old naming: "Index Funds - Equity"
    if group == "Other" and re.search(r"index|etf|exchange traded", label, re.IGNORECASE):
        group = "Index & ETF"
    if group == "Other" and label.startswith("FoF"):
        group = "Fund of Funds"
    return group, label


def full_scheme_name(name: str, plan: str | None, option: str | None) -> str:
    """Append plan/option when AMFI lists them in separate columns rather than in the name."""
    lowered = name.lower()
    extras = [part for part in (plan, option) if part and part.lower() not in lowered]
    return " - ".join([name, *extras])


def _as_utc(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
