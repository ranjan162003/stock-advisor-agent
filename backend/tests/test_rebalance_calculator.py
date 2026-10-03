import pytest

from app.analysis.rebalance_calculator import PricedPosition, plan_rebalance
from app.schemas.rebalance_schemas import TradeAction
from app.schemas.recommendation_schemas import AssetType


def stock(ticker: str, price: float, qty: float) -> PricedPosition:
    return PricedPosition(ticker=ticker, asset_type=AssetType.STOCK, display_name=ticker, price=price, quantity=qty)


def fund(ticker: str, nav: float, units: float) -> PricedPosition:
    return PricedPosition(ticker=ticker, asset_type=AssetType.MUTUAL_FUND, display_name=ticker, price=nav, quantity=units)


def by_ticker(plan):
    return {line.ticker: line for line in plan.lines}


def test_allow_selling_moves_to_exact_targets_and_sells_non_targets():
    positions = [stock("A", 100, 600), stock("B", 100, 200), stock("OLD", 50, 40), fund("MF:1", 10, 0)]
    plan = plan_rebalance(positions, {"A": 0.4, "B": 0.4, "MF:1": 0.2}, additional_cash=0, allow_selling=True)
    lines = by_ticker(plan)
    # Total ₹82,000 → A 32,800 · B 32,800 · fund 16,400
    assert lines["A"].action is TradeAction.SELL and lines["A"].trade_quantity == 272
    assert lines["B"].action is TradeAction.BUY and lines["B"].trade_quantity == 128
    assert lines["OLD"].action is TradeAction.SELL and lines["OLD"].trade_quantity == 40
    assert lines["MF:1"].trade_quantity == pytest.approx(1640.0)
    assert plan.drift_after_percent < 1
    assert plan.drift_before_percent > plan.drift_after_percent


def test_no_selling_only_invests_new_cash_into_underweight_targets():
    positions = [stock("A", 100, 80), fund("MF:1", 10, 200), stock("OLD", 50, 10)]
    plan = plan_rebalance(positions, {"A": 0.5, "MF:1": 0.5}, additional_cash=6000, allow_selling=False)
    lines = by_ticker(plan)
    assert plan.total_sell == 0
    assert lines["OLD"].action is TradeAction.HOLD
    # A is overweight (₹8,000 vs fund ₹2,000), so all new cash goes to the fund.
    assert lines["A"].action is TradeAction.HOLD
    assert lines["MF:1"].action is TradeAction.BUY and lines["MF:1"].trade_value == pytest.approx(6000)


def test_stock_buys_round_down_to_whole_shares_and_report_leftover_cash():
    plan = plan_rebalance([stock("A", 3000, 0)], {"A": 1.0}, additional_cash=10_000, allow_selling=True)
    line = plan.lines[0]
    assert line.trade_quantity == 3 and line.trade_value == 9000
    assert plan.cash_left_over == pytest.approx(1000)


def test_tiny_differences_are_held():
    positions = [stock("A", 100, 501), stock("B", 100, 499)]
    plan = plan_rebalance(positions, {"A": 0.5, "B": 0.5}, additional_cash=0, allow_selling=True)
    assert all(line.action is TradeAction.HOLD for line in plan.lines)


def test_nothing_to_rebalance_raises():
    with pytest.raises(ValueError):
        plan_rebalance([stock("A", 100, 0)], {"A": 1.0}, additional_cash=0, allow_selling=True)


def test_leftover_cash_is_spent_on_the_most_underweight_target():
    # ₹10,000 split 50/50 → ₹5,000 each; A costs ₹3,000 so the first pass buys 1 (₹2,000 idle),
    # and the top-up pass should put that spare cash into the fund rather than leave it unused.
    plan = plan_rebalance([stock("A", 3000, 0), fund("MF:1", 10, 0)], {"A": 0.5, "MF:1": 0.5},
                          additional_cash=10_000, allow_selling=True)
    lines = by_ticker(plan)
    assert lines["A"].trade_quantity == 1
    assert lines["MF:1"].trade_value == pytest.approx(7000)
    assert plan.cash_left_over == pytest.approx(0, abs=0.01)


def test_mixed_case_single_words_are_names_not_tickers():
    from app.services.holdings_import_service import _TICKER_PATTERN
    assert _TICKER_PATTERN.match("INFY") and _TICKER_PATTERN.match("M&M") and _TICKER_PATTERN.match("TCS.NS")
    assert not _TICKER_PATTERN.match("Infosys")
