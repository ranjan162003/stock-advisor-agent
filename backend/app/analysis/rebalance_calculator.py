"""Turn current holdings + a target allocation into buy / sell / hold trades.

Deterministic arithmetic only (no LLM) so the numbers are exact and repeatable.

Two policies:
* **Allow selling** — move every holding to its exact target value; anything
  not in the target is sold.
* **No selling** — only invest the new cash, filling the most underweight
  targets first (avoids capital-gains tax and exit loads). Holdings outside
  the target are kept.

Stocks trade in whole shares (buys round down so we never overspend);
mutual funds trade by amount, so units can be fractional.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.schemas.rebalance_schemas import RebalanceLine, TradeAction
from app.schemas.recommendation_schemas import AssetType

# Trades smaller than this (₹, or % of the portfolio) aren't worth the hassle.
MIN_TRADE_RUPEES = 100
MIN_TRADE_FRACTION = 0.005
FUND_UNIT_DECIMALS = 3


@dataclass
class PricedPosition:
    ticker: str
    asset_type: AssetType
    display_name: str
    price: float
    quantity: float  # 0 for a target holding you don't own yet

    @property
    def value(self) -> float:
        return self.price * self.quantity


@dataclass
class RebalancePlan:
    lines: list[RebalanceLine]
    total_buy: float
    total_sell: float
    cash_left_over: float
    drift_before_percent: float
    drift_after_percent: float


def plan_rebalance(
    positions: list[PricedPosition],
    target_weights: dict[str, float],
    additional_cash: float,
    allow_selling: bool,
) -> RebalancePlan:
    """`target_weights` maps ticker -> fraction (sums to 1). Every target must have a position (qty may be 0)."""
    current_total = sum(p.value for p in positions)
    total_after = current_total + additional_cash
    if total_after <= 0:
        raise ValueError("Nothing to rebalance: no holdings and no new cash.")

    desired_change = _desired_changes(positions, target_weights, additional_cash, total_after, allow_selling)
    min_trade = max(MIN_TRADE_RUPEES, MIN_TRADE_FRACTION * total_after)

    lines: list[RebalanceLine] = []
    total_buy = total_sell = 0.0
    for position in positions:
        change = desired_change[position.ticker]
        action, quantity, trade_value, note = _to_trade(position, change, min_trade)
        if action is TradeAction.BUY:
            total_buy += trade_value
        elif action is TradeAction.SELL:
            total_sell += trade_value
        after_value = position.value + (trade_value if action is TradeAction.BUY else -trade_value if action is TradeAction.SELL else 0)
        lines.append(
            RebalanceLine(
                ticker=position.ticker,
                asset_type=position.asset_type,
                display_name=position.display_name,
                price=round(position.price, 4),
                current_quantity=position.quantity,
                current_value=round(position.value, 2),
                current_weight_percent=_pct(position.value, current_total),
                target_weight_percent=round(target_weights.get(position.ticker, 0) * 100, 2),
                action=action,
                trade_quantity=quantity,
                trade_value=round(trade_value, 2),
                after_value=round(after_value, 2),
                after_weight_percent=0.0,  # filled in below once the total is known
                note=note,
            )
        )

    # Rounding buys down to whole shares leaves cash idle; spend it on whatever is still most underweight.
    ideal_base = total_after if allow_selling else sum(p.value for p in positions if p.ticker in target_weights) + additional_cash
    total_buy += _spend_leftover_cash(lines, target_weights, ideal_base, additional_cash + total_sell - total_buy)

    cash_left_over = additional_cash + total_sell - total_buy
    value_after = sum(line.after_value for line in lines)
    for line in lines:
        line.after_weight_percent = _pct(line.after_value, value_after)

    return RebalancePlan(
        lines=sorted(lines, key=lambda l: (l.action is TradeAction.HOLD, -l.trade_value)),
        total_buy=round(total_buy, 2),
        total_sell=round(total_sell, 2),
        cash_left_over=round(cash_left_over, 2),
        drift_before_percent=_drift({p.ticker: p.value for p in positions}, target_weights, current_total),
        drift_after_percent=_drift({l.ticker: l.after_value for l in lines}, target_weights, value_after),
    )


def _desired_changes(
    positions: list[PricedPosition],
    target_weights: dict[str, float],
    cash: float,
    total_after: float,
    allow_selling: bool,
) -> dict[str, float]:
    """Rupee change wanted per holding (+ buy, − sell) before share rounding."""
    if allow_selling:
        return {p.ticker: total_after * target_weights.get(p.ticker, 0) - p.value for p in positions}

    # Kept non-target holdings sit outside the plan, so targets apply to (target holdings + new cash).
    target_base = sum(p.value for p in positions if p.ticker in target_weights) + cash
    shortfalls = {
        p.ticker: max(0.0, target_base * target_weights[p.ticker] - p.value) for p in positions if p.ticker in target_weights
    }
    total_shortfall = sum(shortfalls.values())
    changes = {p.ticker: 0.0 for p in positions}
    if total_shortfall >= cash:
        # Not enough cash to fix everything: spread it in proportion to how underweight each target is.
        for ticker, shortfall in shortfalls.items():
            changes[ticker] = cash * shortfall / total_shortfall if total_shortfall else 0.0
    else:
        # Every gap can be closed; split what's left by target weight.
        leftover = cash - total_shortfall
        for ticker, shortfall in shortfalls.items():
            changes[ticker] = shortfall + leftover * target_weights[ticker]
    return changes


def _spend_leftover_cash(
    lines: list[RebalanceLine], target_weights: dict[str, float], ideal_base: float, leftover: float
) -> float:
    """Greedy top-up: repeatedly buy into the target furthest below its ideal value.

    Stocks get one more share at a time, only if that share closes at least half
    its price worth of gap (so we don't badly overshoot); funds take the exact gap.
    Returns the extra rupees spent.
    """
    by_ticker = {line.ticker: line for line in lines}
    spent = 0.0
    for _ in range(500):  # safety bound; each loop buys at least one share or fills one fund
        best: RebalanceLine | None = None
        best_gap = 0.0
        for ticker, weight in target_weights.items():
            line = by_ticker[ticker]
            gap = ideal_base * weight - line.after_value
            if line.action is TradeAction.SELL or gap <= 0:
                continue
            if line.asset_type is AssetType.MUTUAL_FUND:
                affordable = leftover >= MIN_TRADE_RUPEES and gap >= MIN_TRADE_RUPEES
            else:
                affordable = leftover >= line.price and gap >= line.price / 2
            if affordable and gap > best_gap:
                best, best_gap = line, gap
        if best is None:
            return spent + _park_remainder_in_funds(by_ticker, target_weights, leftover)

        if best.asset_type is AssetType.MUTUAL_FUND:
            units = round(min(best_gap, leftover) / best.price, FUND_UNIT_DECIMALS)
            amount = units * best.price
        else:
            units, amount = 1, best.price
        best.action = TradeAction.BUY
        best.trade_quantity = round(best.trade_quantity + units, FUND_UNIT_DECIMALS)
        best.trade_value = round(best.trade_value + amount, 2)
        best.after_value = round(best.after_value + amount, 2)
        best.note = None
        leftover -= amount
        spent += amount
    return spent


def _park_remainder_in_funds(by_ticker: dict[str, RebalanceLine], target_weights: dict[str, float], leftover: float) -> float:
    """Cash too small for another share goes into the target funds (they accept any amount), by weight."""
    funds = {t: w for t, w in target_weights.items() if by_ticker[t].asset_type is AssetType.MUTUAL_FUND
             and by_ticker[t].action is not TradeAction.SELL}
    fund_weight = sum(funds.values())
    if leftover < MIN_TRADE_RUPEES or fund_weight <= 0:
        return 0.0
    spent = 0.0
    for ticker, weight in funds.items():
        line = by_ticker[ticker]
        units = math.floor(leftover * weight / fund_weight / line.price * 10**FUND_UNIT_DECIMALS) / 10**FUND_UNIT_DECIMALS
        amount = units * line.price
        if amount <= 0:
            continue
        line.action = TradeAction.BUY
        line.trade_quantity = round(line.trade_quantity + units, FUND_UNIT_DECIMALS)
        line.trade_value = round(line.trade_value + amount, 2)
        line.after_value = round(line.after_value + amount, 2)
        spent += amount
    return spent


def _to_trade(position: PricedPosition, change: float, min_trade: float) -> tuple[TradeAction, float, float, str | None]:
    """(action, quantity, rupee value, note) for one holding."""
    if abs(change) < min_trade or position.price <= 0:
        return TradeAction.HOLD, 0, 0.0, None

    if position.asset_type is AssetType.MUTUAL_FUND:
        units = round(abs(change) / position.price, FUND_UNIT_DECIMALS)
        if change < 0:
            units = min(units, position.quantity)
        value = units * position.price
        return (TradeAction.BUY if change > 0 else TradeAction.SELL), units, value, None

    if change > 0:
        shares = math.floor(change / position.price)
        if shares == 0:
            return TradeAction.HOLD, 0, 0.0, f"₹{change:,.0f} is less than one share (₹{position.price:,.0f})"
        return TradeAction.BUY, shares, shares * position.price, None
    shares = min(round(abs(change) / position.price), int(position.quantity))
    if shares == 0:
        return TradeAction.HOLD, 0, 0.0, None
    note = "Not in the target — sell all" if shares == int(position.quantity) and position.quantity > 0 else None
    return TradeAction.SELL, shares, shares * position.price, note


def _pct(value: float, total: float) -> float:
    return round(value / total * 100, 2) if total > 0 else 0.0


def _drift(values: dict[str, float], target_weights: dict[str, float], total: float) -> float:
    """Share of the portfolio that sits in the 'wrong' place: ½ Σ |actual − target|."""
    if total <= 0:
        return 100.0
    tickers = set(values) | set(target_weights)
    gap = sum(abs(values.get(t, 0) / total - target_weights.get(t, 0)) for t in tickers)
    return round(gap / 2 * 100, 2)
