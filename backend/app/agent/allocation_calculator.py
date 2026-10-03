"""Convert percentage picks into rupee amounts (+ whole shares / fund units).

Both investment modes share this step — the only difference is presentation:
one-time shows the rupee split, recurring leads with percentages and shows
the rupee split for *this* period as a convenience.

Stocks trade in whole shares, so we show how many the amount buys. Mutual
funds are bought by amount, so we show the (fractional) units at today's NAV.
"""
from __future__ import annotations

import math

from app.agent.recommendation_response_parser import ParsedRecommendation
from app.schemas.market_data_schemas import StockSnapshot
from app.schemas.mutual_fund_schemas import FundSnapshot
from app.schemas.recommendation_schemas import AssetType, PortfolioAllocation


def calculate_allocations(
    parsed: ParsedRecommendation,
    stocks_by_ticker: dict[str, StockSnapshot],
    funds_by_symbol: dict[str, FundSnapshot],
    amount: float,
) -> list[PortfolioAllocation]:
    allocations: list[PortfolioAllocation] = []
    for pick in parsed.picks:
        rupee_amount = round(amount * pick.weight_percent / 100, 2)
        if pick.ticker in funds_by_symbol:
            fund = funds_by_symbol[pick.ticker]
            nav = fund.metrics.latest_nav
            allocations.append(
                PortfolioAllocation(
                    ticker=fund.symbol,
                    asset_type=AssetType.MUTUAL_FUND,
                    display_name=fund.short_name,
                    company_name=fund.scheme_name,
                    sector=fund.category,
                    weight_percent=pick.weight_percent,
                    amount=rupee_amount,
                    last_price=nav,
                    approx_whole_shares=0,
                    approx_units=round(rupee_amount / nav, 3) if nav > 0 else None,
                    rationale=pick.rationale,
                )
            )
        else:
            stock = stocks_by_ticker[pick.ticker]
            price = stock.technicals.last_close
            allocations.append(
                PortfolioAllocation(
                    ticker=stock.ticker,
                    asset_type=AssetType.STOCK,
                    display_name=stock.ticker.removesuffix(".NS").removesuffix(".BO"),
                    company_name=stock.company_name,
                    sector=stock.sector,
                    weight_percent=pick.weight_percent,
                    amount=rupee_amount,
                    last_price=price,
                    approx_whole_shares=math.floor(rupee_amount / price) if price > 0 else 0,
                    rationale=pick.rationale,
                )
            )
    return allocations
