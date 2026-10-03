"""Recent news headlines per stock.

Yahoo Finance news is the default (free, no key, covers NSE). If a Finnhub key
is configured, Finnhub company news is used as a fallback when Yahoo returns
nothing (Finnhub's free tier mainly covers US listings).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
import yfinance as yf

from app.schemas.market_data_schemas import NewsHeadline

logger = logging.getLogger(__name__)

FINNHUB_COMPANY_NEWS_URL = "https://finnhub.io/api/v1/company-news"
LEGAL_NAME_SUFFIXES = {"limited", "ltd", "inc", "corp", "corporation", "plc", "company", "co", "industries"}
# Words too common to prove a headline is about *this* company.
GENERIC_NAME_WORDS = {
    "india", "indian", "bank", "power", "grid", "steel", "finance", "financial", "services", "consultancy",
    "technologies", "pharmaceutical", "pharmaceuticals", "laboratories", "motors", "the", "and", "of",
}


def fetch_recent_headlines(
    ticker: str, company_name: str, limit: int, finnhub_api_key: str | None = None
) -> list[NewsHeadline]:
    headlines = _fetch_yahoo_headlines(ticker, company_name, limit)
    if not headlines and finnhub_api_key:
        headlines = _fetch_finnhub_headlines(ticker, limit, finnhub_api_key)
    return headlines


def _fetch_yahoo_headlines(ticker: str, company_name: str, limit: int) -> list[NewsHeadline]:
    # Yahoo's search endpoint is the reliable news source; `Ticker.news` often
    # comes back empty. Searching by company name gives the most relevant hits.
    raw_items: list[dict[str, Any]] = []
    try:
        for query in _news_search_queries(company_name):
            raw_items = yf.Search(query, news_count=limit).news or []
            if raw_items:
                break
        if not raw_items:
            raw_items = yf.Ticker(ticker).news or []
    except Exception as exc:
        logger.warning("Yahoo news unavailable for %s: %s", ticker, exc)
        return []
    headlines = [h for h in (_parse_yahoo_news_item(item) for item in raw_items) if h]
    return [h for h in headlines if _mentions_company(h.title, company_name)][:limit]


def _mentions_company(title: str, company_name: str) -> bool:
    """Search results are fuzzy; keep a headline only if it names a distinctive word of the company."""
    distinctive = [
        w.strip(".'&()").lower()
        for w in company_name.split()
        if w.strip(".'&()").lower() not in LEGAL_NAME_SUFFIXES | GENERIC_NAME_WORDS and len(w.strip(".'&()")) >= 3
    ]
    lowered = title.lower()
    return not distinctive or any(word in lowered for word in distinctive)


def _news_search_queries(company_name: str) -> list[str]:
    """Yahoo's search matches short names far better than legal names.

    "Sun Pharmaceutical Industries Limited" finds nothing, "Sun Pharma" does --
    so try the name without legal suffixes, then just its first two words.
    """
    words = [w for w in company_name.replace(",", " ").split() if w.lower().strip(".") not in LEGAL_NAME_SUFFIXES]
    queries = [" ".join(words), " ".join(words[:2]).rstrip(" &")]
    return [q for q in dict.fromkeys(queries) if q]


def _parse_yahoo_news_item(item: dict[str, Any]) -> NewsHeadline | None:
    # Newer yfinance versions nest everything under "content"; older ones are flat.
    content = item.get("content") or item
    title = content.get("title")
    if not title:
        return None

    published_at: datetime | None = None
    if content.get("pubDate"):
        try:
            published_at = datetime.fromisoformat(content["pubDate"].replace("Z", "+00:00"))
        except ValueError:
            published_at = None
    elif item.get("providerPublishTime"):
        published_at = datetime.fromtimestamp(item["providerPublishTime"], tz=timezone.utc)

    provider = content.get("provider")
    publisher = provider.get("displayName") if isinstance(provider, dict) else item.get("publisher")
    canonical = content.get("canonicalUrl")
    url = canonical.get("url") if isinstance(canonical, dict) else item.get("link")
    return NewsHeadline(title=title, publisher=publisher, published_at=published_at, url=url)


def _fetch_finnhub_headlines(ticker: str, limit: int, api_key: str) -> list[NewsHeadline]:
    symbol = ticker.split(".")[0]
    today = date.today()
    try:
        response = httpx.get(
            FINNHUB_COMPANY_NEWS_URL,
            params={"symbol": symbol, "from": (today - timedelta(days=14)).isoformat(), "to": today.isoformat()},
            headers={"X-Finnhub-Token": api_key},
            timeout=15,
        )
        response.raise_for_status()
        raw_items = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Finnhub news unavailable for %s: %s", ticker, exc)
        return []

    return [
        NewsHeadline(
            title=item["headline"],
            publisher=item.get("source"),
            published_at=datetime.fromtimestamp(item["datetime"], tz=timezone.utc) if item.get("datetime") else None,
            url=item.get("url"),
        )
        for item in raw_items[:limit]
        if item.get("headline")
    ]
