"""Price the user's holdings and a target recommendation, then plan the trades."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.analysis.fund_snapshot_builder import build_fund_snapshots
from app.analysis.rebalance_calculator import PricedPosition, plan_rebalance
from app.analysis.stock_snapshot_builder import build_stock_snapshots
from app.core.app_exceptions import InvalidRequestError
from app.core.app_settings import get_settings
from app.data_sources.default_fund_universe import fund_symbol, is_fund_symbol, scheme_code_from_symbol
from app.data_sources.default_stock_universe import normalize_ticker
from app.schemas.rebalance_schemas import RebalanceRequest, RebalanceResponse
from app.schemas.recommendation_schemas import AssetType
from app.services.recommendation_history_service import get_recommendation_detail


def rebalance_portfolio(session: Session, request: RebalanceRequest) -> RebalanceResponse:
    if not request.holdings and request.additional_cash <= 0:
        raise InvalidRequestError("Add your current holdings, some new cash to invest, or both.")

    recommendation = get_recommendation_detail(session, request.recommendation_id)
    target_weights = {a.ticker: a.weight_percent / 100 for a in recommendation.allocations}
    target_names = {a.ticker: a.display_name or a.ticker for a in recommendation.allocations}

    # Merge duplicate rows (e.g. the same stock entered twice) and normalise symbols.
    quantities: dict[str, float] = {}
    for holding in request.holdings:
        symbol = _normalize_symbol(holding.symbol)
        quantities[symbol] = quantities.get(symbol, 0) + holding.quantity

    all_symbols = list(dict.fromkeys([*quantities, *target_weights]))
    prices, names, unpriced = _price_symbols(session, all_symbols)
    missing_targets = [s for s in target_weights if s in unpriced]
    if missing_targets:
        raise InvalidRequestError(f"Couldn't get today's price for target holdings: {', '.join(missing_targets)}.")

    positions = [
        PricedPosition(
            ticker=symbol,
            asset_type=AssetType.MUTUAL_FUND if is_fund_symbol(symbol) else AssetType.STOCK,
            display_name=target_names.get(symbol) or names.get(symbol, symbol),
            price=prices[symbol],
            quantity=quantities.get(symbol, 0),
        )
        for symbol in all_symbols
        if symbol in prices
    ]
    plan = plan_rebalance(positions, target_weights, request.additional_cash, request.allow_selling)
    current_value = sum(p.value for p in positions)
    return RebalanceResponse(
        recommendation_id=recommendation.id,
        allow_selling=request.allow_selling,
        current_value=round(current_value, 2),
        additional_cash=request.additional_cash,
        total_buy=plan.total_buy,
        total_sell=plan.total_sell,
        cash_left_over=plan.cash_left_over,
        value_after=round(sum(line.after_value for line in plan.lines), 2),
        drift_before_percent=plan.drift_before_percent,
        drift_after_percent=plan.drift_after_percent,
        lines=plan.lines,
        unpriced_holdings=unpriced,
    )


def _normalize_symbol(raw: str) -> str:
    text = raw.strip()
    if is_fund_symbol(text):
        return fund_symbol(scheme_code_from_symbol(text.upper()))
    if text.isdigit():
        return fund_symbol(int(text))  # bare AMFI scheme code
    try:
        return normalize_ticker(text)
    except ValueError as exc:
        raise InvalidRequestError(str(exc)) from exc


def _price_symbols(session: Session, symbols: list[str]) -> tuple[dict[str, float], dict[str, str], dict[str, str]]:
    """(price per symbol, display name per symbol, unpriced symbol -> reason)."""
    settings = get_settings()
    stock_symbols = [s for s in symbols if not is_fund_symbol(s)]
    fund_codes = [scheme_code_from_symbol(s) for s in symbols if is_fund_symbol(s)]

    prices: dict[str, float] = {}
    names: dict[str, str] = {}
    unpriced: dict[str, str] = {}
    if stock_symbols:
        stocks = build_stock_snapshots(session, stock_symbols, settings)
        for snapshot in stocks.snapshots:
            prices[snapshot.ticker] = snapshot.technicals.last_close
            names[snapshot.ticker] = snapshot.ticker.removesuffix(".NS").removesuffix(".BO")
        unpriced.update(stocks.skipped)
    if fund_codes:
        funds = build_fund_snapshots(session, fund_codes, settings)
        for snapshot in funds.snapshots:
            prices[snapshot.symbol] = snapshot.metrics.latest_nav
            names[snapshot.symbol] = snapshot.short_name
        unpriced.update(funds.skipped)
    for symbol in symbols:
        if symbol not in prices and symbol not in unpriced:
            unpriced[symbol] = "No price found."
    return prices, names, unpriced
