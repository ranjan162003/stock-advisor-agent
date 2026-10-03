"""SIP / goal planner: build a return basis, simulate, and summarise."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.analysis.sip_simulator import (
    DEFAULT_PATHS,
    annualized_stats,
    bootstrap_monthly_returns,
    lognormal_monthly_returns,
    probability_at_least,
    required_monthly_amount,
    simulate_sip,
)
from app.core.app_exceptions import InvalidRequestError, MarketDataError
from app.data_sources.default_fund_universe import is_fund_symbol, scheme_code_from_symbol
from app.analysis.sip_backtester import (
    FIXED_DEPOSIT_RATE_PERCENT,
    FundLeg,
    fixed_deposit_value,
    run_sip_backtest,
    worst_drawdown_percent,
    xirr,
)
from app.data_sources.default_fund_universe import DEFAULT_FUNDS_BY_CODE, short_fund_name
from app.data_sources.historical_returns_client import (
    fetch_fund_monthly_returns,
    fetch_stock_monthly_returns,
    monthly_returns_from_navs,
)
from app.data_sources.mfapi_mutual_fund_client import fetch_fund_nav_history
from app.schemas.recommendation_schemas import RecommendationResponse
from app.schemas.sip_planner_schemas import (
    BacktestFundResult,
    BacktestPoint,
    FundWeight,
    ReturnPreset,
    ReturnPresetInfo,
    ReturnSource,
    SipBacktestRequest,
    SipBacktestResponse,
    SipProjectionRequest,
    SipProjectionResponse,
    YearlyProjectionPoint,
)
from app.services.recommendation_history_service import get_recommendation_detail

logger = logging.getLogger(__name__)

# Long-run planning assumptions (yearly return %, yearly volatility %) — deliberately moderate.
RETURN_PRESETS: dict[ReturnPreset, ReturnPresetInfo] = {
    ReturnPreset.DEBT: ReturnPresetInfo(
        preset=ReturnPreset.DEBT, label="Debt / liquid funds", annual_return_percent=7, annual_volatility_percent=2
    ),
    ReturnPreset.HYBRID: ReturnPresetInfo(
        preset=ReturnPreset.HYBRID, label="Hybrid / balanced funds", annual_return_percent=10, annual_volatility_percent=9
    ),
    ReturnPreset.LARGE_CAP: ReturnPresetInfo(
        preset=ReturnPreset.LARGE_CAP, label="Large-cap / Nifty index", annual_return_percent=11, annual_volatility_percent=15
    ),
    ReturnPreset.FLEXI_CAP: ReturnPresetInfo(
        preset=ReturnPreset.FLEXI_CAP, label="Flexi-cap / diversified equity", annual_return_percent=12, annual_volatility_percent=17
    ),
    ReturnPreset.MID_SMALL_CAP: ReturnPresetInfo(
        preset=ReturnPreset.MID_SMALL_CAP, label="Mid & small cap", annual_return_percent=14, annual_volatility_percent=23
    ),
}

MIN_HISTORY_MONTHS = 36
MIN_COVERED_WEIGHT = 0.5
SIMULATION_SEED = 20261003  # fixed so the same inputs always give the same projection


def list_return_presets() -> list[ReturnPresetInfo]:
    return list(RETURN_PRESETS.values())


def project_sip(session: Session, request: SipProjectionRequest) -> SipProjectionResponse:
    months = request.years * 12
    rng = np.random.default_rng(SIMULATION_SEED)
    excluded: dict[str, str] = {}
    history_months: int | None = None

    if request.return_source is ReturnSource.RECOMMENDATION:
        recommendation = get_recommendation_detail(session, request.recommendation_id)
        history, excluded = build_portfolio_monthly_returns(recommendation)
        history_months = history.size
        basis_return, basis_volatility = annualized_stats(history)
        returns = bootstrap_monthly_returns(history, months, DEFAULT_PATHS, rng)
        labels = ", ".join(a.display_name or a.ticker for a in recommendation.allocations[:4])
        more = len(recommendation.allocations) - 4
        source = f"Replaying {history_months} real months of your recommendation #{recommendation.id} ({labels}"
        source += f" +{more} more)" if more > 0 else ")"
    elif request.return_source is ReturnSource.FUNDS:
        funds = load_funds(request.funds)
        history = weighted_monthly_returns(
            {f.key: monthly_returns_from_navs(f.navs) for f in funds}, {f.key: f.weight for f in funds}
        )
        history_months = history.size
        basis_return, basis_volatility = annualized_stats(history)
        returns = bootstrap_monthly_returns(history, months, DEFAULT_PATHS, rng)
        split = " + ".join(f"{f.key} {f.weight * 100:g}%" for f in funds) if len(funds) > 1 else funds[0].key
        source = f"Replaying {history_months} real months of {split}"
    else:
        preset = RETURN_PRESETS[request.preset]
        basis_return, basis_volatility = preset.annual_return_percent, preset.annual_volatility_percent
        returns = lognormal_monthly_returns(basis_return, basis_volatility, months, DEFAULT_PATHS, rng)
        source = f"Assumed {preset.label}: about {basis_return:g}% a year with {basis_volatility:g}% volatility"

    simulation = simulate_sip(returns, request.monthly_amount, request.annual_step_up_percent)
    final = simulation.final_values
    last = simulation.yearly[-1]

    goal_probability = required_50 = required_80 = None
    if request.goal_amount:
        goal_probability = round(probability_at_least(final, request.goal_amount), 1)
        required_50 = round(required_monthly_amount(final, request.monthly_amount, request.goal_amount, 0.5), -1)
        required_80 = round(required_monthly_amount(final, request.monthly_amount, request.goal_amount, 0.8), -1)

    return SipProjectionResponse(
        monthly_amount=request.monthly_amount,
        years=request.years,
        annual_step_up_percent=request.annual_step_up_percent,
        total_invested=round(simulation.total_invested),
        bad_case=round(last.p10),
        typical=round(last.p50),
        good_case=round(last.p90),
        chance_of_loss_percent=round(100 - probability_at_least(final, simulation.total_invested), 1),
        goal_amount=request.goal_amount,
        goal_probability_percent=goal_probability,
        required_monthly_for_goal_50=required_50,
        required_monthly_for_goal_80=required_80,
        yearly=[
            YearlyProjectionPoint(
                year=point.year,
                invested=round(point.invested),
                bad_case=round(point.p10),
                typical=round(point.p50),
                good_case=round(point.p90),
            )
            for point in simulation.yearly
        ],
        source_description=source,
        basis_annual_return_percent=round(basis_return, 1),
        basis_annual_volatility_percent=round(basis_volatility, 1),
        history_months=history_months,
        excluded_holdings=excluded,
        simulated_paths=DEFAULT_PATHS,
    )


def build_portfolio_monthly_returns(recommendation: RecommendationResponse) -> tuple[np.ndarray, dict[str, str]]:
    """Weighted monthly returns of the recommended holdings over their common history.

    Holdings with less than 3 years of history are left out (and reported) so a
    new fund doesn't shrink the window for everything else.
    """
    weights = {a.ticker: a.weight_percent / 100 for a in recommendation.allocations}
    stock_tickers = [t for t in weights if not is_fund_symbol(t)]
    fund_symbols = [t for t in weights if is_fund_symbol(t)]

    series: dict[str, pd.Series] = dict(fetch_stock_monthly_returns(stock_tickers))
    with ThreadPoolExecutor(max_workers=8) as pool:
        for symbol, fund_series in zip(
            fund_symbols, pool.map(lambda s: fetch_fund_monthly_returns(scheme_code_from_symbol(s)), fund_symbols)
        ):
            if fund_series is not None:
                series[symbol] = fund_series

    excluded: dict[str, str] = {}
    usable: dict[str, pd.Series] = {}
    for ticker in weights:
        if ticker not in series:
            excluded[ticker] = "No price history available."
        elif len(series[ticker]) < MIN_HISTORY_MONTHS:
            excluded[ticker] = f"Only {len(series[ticker])} months of history (need {MIN_HISTORY_MONTHS})."
        else:
            usable[ticker] = series[ticker]

    covered_weight = sum(weights[t] for t in usable)
    if covered_weight < MIN_COVERED_WEIGHT:
        raise MarketDataError(
            "Not enough of this portfolio has 3+ years of history to replay. Use a preset return assumption instead."
        )
    portfolio = weighted_monthly_returns(usable, {t: weights[t] for t in usable})
    logger.info("SIP basis: %d months, %d holdings (%d excluded)", portfolio.size, len(usable), len(excluded))
    return portfolio, excluded


def weighted_monthly_returns(series: dict[str, pd.Series], weights: dict[str, float]) -> np.ndarray:
    """Weighted portfolio return per month over the months every series has (weights renormalised)."""
    aligned = pd.concat(series, axis=1, join="inner").dropna()
    if len(aligned) < MIN_HISTORY_MONTHS:
        raise InvalidRequestError(
            f"These holdings share only {len(aligned)} months of history (need {MIN_HISTORY_MONTHS}). "
            "Pick older funds or use a preset return assumption."
        )
    total = sum(weights[key] for key in aligned.columns)
    normalized = pd.Series({key: weights[key] / total for key in aligned.columns})
    return aligned.mul(normalized, axis=1).sum(axis=1).to_numpy()


def load_funds(fund_weights: list[FundWeight]) -> list[FundLeg]:
    """Full NAV history for each chosen fund, labelled with its short name."""
    with ThreadPoolExecutor(max_workers=5) as pool:
        histories = list(pool.map(lambda f: fetch_fund_nav_history(f.scheme_code), fund_weights))
    legs: list[FundLeg] = []
    for fund, history in zip(fund_weights, histories):
        if history is None:
            raise InvalidRequestError(f"No NAV data found for scheme {fund.scheme_code}.")
        known = DEFAULT_FUNDS_BY_CODE.get(fund.scheme_code)
        legs.append(
            FundLeg(
                key=known.short_name if known else short_fund_name(history.scheme_name),
                weight=fund.weight_percent / 100,
                navs=history.navs,
                scheme_code=fund.scheme_code,
                scheme_name=history.scheme_name,
            )
        )
    total = sum(leg.weight for leg in legs)
    for leg in legs:
        leg.weight /= total
    return legs


def backtest_sip(request: SipBacktestRequest) -> SipBacktestResponse:
    legs = load_funds(request.funds)
    legs_by_key = {leg.key: leg for leg in legs}
    try:
        result = run_sip_backtest(legs, request.monthly_amount, request.years, request.annual_step_up_percent)
    except ValueError as exc:
        raise InvalidRequestError(f"{exc} — choose {int(_max_years(legs))} years or fewer.") from exc

    portfolio_xirr = xirr(result.cash_flows)
    end = result.end_date.date()
    return SipBacktestResponse(
        start_date=result.instalment_dates[0].date().isoformat(),
        end_date=end.isoformat(),
        installments=len(result.instalment_dates),
        monthly_amount=request.monthly_amount,
        annual_step_up_percent=request.annual_step_up_percent,
        total_invested=round(result.total_invested),
        final_value=round(result.final_value),
        gain=round(result.final_value - result.total_invested),
        absolute_return_percent=round((result.final_value / result.total_invested - 1) * 100, 1),
        xirr_percent=round(portfolio_xirr * 100, 2) if portfolio_xirr is not None else None,
        fixed_deposit_value=round(fixed_deposit_value(result.cash_flows, end)),
        fixed_deposit_rate_percent=FIXED_DEPOSIT_RATE_PERCENT,
        worst_drawdown_percent=round(worst_drawdown_percent([v for _, _, v in result.timeline]), 1),
        timeline=[
            BacktestPoint(date=when.date().isoformat(), invested=round(invested), value=round(value))
            for when, invested, value in result.timeline
        ],
        funds=[
            BacktestFundResult(
                scheme_code=legs_by_key[leg.key].scheme_code,
                short_name=leg.key,
                scheme_name=legs_by_key[leg.key].scheme_name,
                weight_percent=round(legs_by_key[leg.key].weight * 100, 1),
                invested=round(leg.invested),
                units=round(leg.units, 3),
                latest_nav=round(leg.latest_nav, 4),
                value=round(leg.value),
                xirr_percent=round(x * 100, 2) if (x := xirr(leg.cash_flows)) is not None else None,
            )
            for leg in result.legs
        ],
    )


def _max_years(legs: list[FundLeg]) -> float:
    end = min(leg.navs.index[-1] for leg in legs)
    return min((end - leg.navs.index[0]).days / 365.25 for leg in legs)
