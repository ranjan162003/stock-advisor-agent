"""Convert percentage picks into rupee amounts (+ whole-share estimates).

Both investment modes share this step — the only difference is presentation:
one-time shows the rupee split, recurring leads with percentages and shows
the rupee split for *this* period as a convenience.
"""
from __future__ import annotations

import math

from app.agent.recommendation_response_parser import ParsedRecommendation
from app.schemas.market_data_schemas import StockSnapshot
from app.schemas.recommendation_schemas import StockAllocation


def calculate_stock_allocations(
    parsed: ParsedRecommendation,
    snapshots_by_ticker: dict[str, StockSnapshot],
    amount: float,
) -> list[StockAllocation]:
    allocations: list[StockAllocation] = []
    for pick in parsed.picks:
        snapshot = snapshots_by_ticker[pick.ticker]
        price = snapshot.technicals.last_close
        rupee_amount = round(amount * pick.weight_percent / 100, 2)
        allocations.append(
            StockAllocation(
                ticker=pick.ticker,
                company_name=snapshot.company_name,
                sector=snapshot.sector,
                weight_percent=pick.weight_percent,
                amount=rupee_amount,
                last_price=price,
                approx_whole_shares=math.floor(rupee_amount / price) if price > 0 else 0,
                rationale=pick.rationale,
            )
        )
    return allocations
