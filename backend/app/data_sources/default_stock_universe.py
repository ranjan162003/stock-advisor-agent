"""Default candidate universe: large, liquid NSE stocks spread across sectors.

Used when the user hasn't built a watchlist or entered custom tickers. Symbols
use Yahoo Finance's `.NS` (National Stock Exchange of India) suffix.
"""
from __future__ import annotations

from app.schemas.market_data_schemas import UniverseStock

DEFAULT_NSE_UNIVERSE: list[UniverseStock] = [
    UniverseStock(ticker="RELIANCE.NS", company_name="Reliance Industries", sector="Energy & Conglomerate"),
    UniverseStock(ticker="TCS.NS", company_name="Tata Consultancy Services", sector="IT Services"),
    UniverseStock(ticker="INFY.NS", company_name="Infosys", sector="IT Services"),
    UniverseStock(ticker="HCLTECH.NS", company_name="HCL Technologies", sector="IT Services"),
    UniverseStock(ticker="HDFCBANK.NS", company_name="HDFC Bank", sector="Banking"),
    UniverseStock(ticker="ICICIBANK.NS", company_name="ICICI Bank", sector="Banking"),
    UniverseStock(ticker="SBIN.NS", company_name="State Bank of India", sector="Banking"),
    UniverseStock(ticker="KOTAKBANK.NS", company_name="Kotak Mahindra Bank", sector="Banking"),
    UniverseStock(ticker="BAJFINANCE.NS", company_name="Bajaj Finance", sector="Financial Services"),
    UniverseStock(ticker="BHARTIARTL.NS", company_name="Bharti Airtel", sector="Telecom"),
    UniverseStock(ticker="ITC.NS", company_name="ITC", sector="FMCG"),
    UniverseStock(ticker="HINDUNILVR.NS", company_name="Hindustan Unilever", sector="FMCG"),
    UniverseStock(ticker="NESTLEIND.NS", company_name="Nestle India", sector="FMCG"),
    UniverseStock(ticker="ASIANPAINT.NS", company_name="Asian Paints", sector="Consumer Durables"),
    UniverseStock(ticker="TITAN.NS", company_name="Titan Company", sector="Consumer Durables"),
    UniverseStock(ticker="MARUTI.NS", company_name="Maruti Suzuki", sector="Automobile"),
    UniverseStock(ticker="M&M.NS", company_name="Mahindra & Mahindra", sector="Automobile"),
    UniverseStock(ticker="SUNPHARMA.NS", company_name="Sun Pharmaceutical", sector="Pharma"),
    UniverseStock(ticker="DRREDDY.NS", company_name="Dr. Reddy's Laboratories", sector="Pharma"),
    UniverseStock(ticker="LT.NS", company_name="Larsen & Toubro", sector="Infrastructure"),
    UniverseStock(ticker="ULTRACEMCO.NS", company_name="UltraTech Cement", sector="Cement"),
    UniverseStock(ticker="NTPC.NS", company_name="NTPC", sector="Power"),
    UniverseStock(ticker="POWERGRID.NS", company_name="Power Grid Corporation", sector="Power"),
    UniverseStock(ticker="TATASTEEL.NS", company_name="Tata Steel", sector="Metals"),
]

DEFAULT_UNIVERSE_BY_TICKER = {stock.ticker: stock for stock in DEFAULT_NSE_UNIVERSE}


def normalize_ticker(raw_ticker: str) -> str:
    """Upper-case a user-typed ticker and default bare symbols to NSE.

    `infy` -> `INFY.NS`; anything that already has an exchange suffix or is an
    index symbol (`^NSEI`) is left as-is, so other exchanges still work.
    """
    ticker = raw_ticker.strip().upper()
    if not ticker:
        raise ValueError("Ticker can't be empty")
    if "." in ticker or ticker.startswith("^"):
        return ticker
    return f"{ticker}.NS"
