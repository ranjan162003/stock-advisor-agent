"""The assistant's toolbox: real app data and calculators the chat agent can call.

Each tool takes JSON arguments chosen by the model and returns:
  * `data`  — a compact dict the model reads to write its answer
  * `card`  — optional structured payload the chat UI renders (fund card, chart, …)

Keeping the model on tools means every number it quotes comes from the app's
data sources, not from its memory.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.analysis.fund_snapshot_builder import build_fund_snapshots
from app.analysis.stock_snapshot_builder import build_stock_snapshots
from app.core.app_exceptions import InvalidRequestError, StockAdvisorError
from app.core.app_settings import get_settings
from app.data_sources.default_stock_universe import normalize_ticker
from app.schemas.sip_planner_schemas import FundWeight, ReturnPreset, ReturnSource, SipBacktestRequest, SipProjectionRequest
from app.services.mutual_fund_service import search_funds
from app.services.recommendation_history_service import get_recommendation_detail, list_recommendation_history
from app.services.sip_planner_service import RETURN_PRESETS, backtest_sip, project_sip


@dataclass
class ToolResult:
    data: dict[str, Any]
    card: dict[str, Any] | None = None


@dataclass
class ToolContext:
    session: Session
    current_recommendation_id: int | None = None


@dataclass
class AssistantTool:
    name: str
    description: str
    arguments: str  # human-readable argument spec shown to the model
    status: str  # what the UI shows while the tool runs, e.g. "Looking up {query}…"
    handler: Callable[[ToolContext, dict[str, Any]], ToolResult] = field(repr=False)


# ---------------------------------------------------------------- funds


def _search_funds(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    query = str(args.get("query") or "").strip()
    if not query:
        raise InvalidRequestError("search_funds needs a `query`.")
    results = search_funds(ctx.session, query, category=args.get("category") or None, limit=8)
    funds = [
        {
            "scheme_code": r.scheme_code,
            "name": r.scheme_name,
            "category": r.category_label,
            "fund_house": r.fund_house,
            "nav": r.nav,
        }
        for r in results
    ]
    return ToolResult(data={"matches": funds}, card={"type": "fund_list", "query": query, "funds": funds} if funds else None)


def _fund_metrics(ctx: ToolContext, scheme_codes: list[int]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    result = build_fund_snapshots(ctx.session, scheme_codes, get_settings())
    funds = []
    for snapshot in result.snapshots:
        m = snapshot.metrics
        funds.append(
            {
                "scheme_code": snapshot.scheme_code,
                "name": snapshot.short_name,
                "full_name": snapshot.scheme_name,
                "category": snapshot.category,
                "fund_house": snapshot.fund_house,
                "risk_class_1_to_5": snapshot.risk_class,
                "nav": m.latest_nav,
                "nav_date": m.nav_date,
                "return_1y_percent": m.return_1y_percent,
                "cagr_3y_percent": m.cagr_3y_percent,
                "cagr_5y_percent": m.cagr_5y_percent,
                "volatility_percent": m.annualized_volatility_percent,
                "worst_drawdown_3y_percent": m.max_drawdown_3y_percent,
                "sharpe_3y": m.sharpe_ratio_3y,
                "history_years": m.history_years,
            }
        )
    return funds, result.skipped


def _get_fund_details(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    code = _as_int(args.get("scheme_code"), "scheme_code")
    funds, skipped = _fund_metrics(ctx, [code])
    if not funds:
        raise InvalidRequestError(next(iter(skipped.values()), f"No data for scheme {code}."))
    return ToolResult(data=funds[0], card={"type": "fund", "fund": funds[0]})


def _compare_funds(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    codes = [_as_int(c, "scheme_codes") for c in (args.get("scheme_codes") or [])][:4]
    if len(codes) < 2:
        raise InvalidRequestError("compare_funds needs 2–4 `scheme_codes` (use search_funds first).")
    funds, skipped = _fund_metrics(ctx, codes)
    return ToolResult(data={"funds": funds, "skipped": skipped}, card={"type": "fund_comparison", "funds": funds})


# ---------------------------------------------------------------- stocks


def _get_stock_details(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    ticker = normalize_ticker(str(args.get("ticker") or ""))
    result = build_stock_snapshots(ctx.session, [ticker], get_settings())
    if not result.snapshots:
        raise InvalidRequestError(result.skipped.get(ticker, f"No data for {ticker}."))
    s = result.snapshots[0]
    t, f = s.technicals, s.fundamentals
    stock = {
        "ticker": s.ticker,
        "name": s.company_name,
        "sector": s.sector,
        "price": t.last_close,
        "return_1m_percent": t.return_1m_percent,
        "return_6m_percent": t.return_6m_percent,
        "return_1y_percent": t.return_1y_percent,
        "vs_200_day_average_percent": t.price_vs_sma_200_percent,
        "rsi_14": t.rsi_14,
        "volatility_percent": t.annualized_volatility_percent,
        "worst_drawdown_1y_percent": t.max_drawdown_1y_percent,
        "pe": f.trailing_pe,
        "forward_pe": f.forward_pe,
        "roe_percent": f.return_on_equity_percent,
        "earnings_growth_percent": f.earnings_growth_percent,
        "debt_to_equity": f.debt_to_equity,
        "dividend_yield_percent": f.dividend_yield_percent,
        "headlines": [h.title for h in s.headlines],
    }
    return ToolResult(data=stock, card={"type": "stock", "stock": stock})


# ---------------------------------------------------------------- SIP calculators


def _fund_weights(raw: Any) -> list[FundWeight]:
    """Funds the model passed; missing weights mean an equal split."""
    pairs = [
        (_as_int(item.get("scheme_code"), "scheme_code"), float(item.get("weight_percent") or 0))
        for item in raw or []
        if isinstance(item, dict)
    ]
    if pairs and all(weight == 0 for _, weight in pairs):
        pairs = [(code, 100 / len(pairs)) for code, _ in pairs]
    return [FundWeight(scheme_code=code, weight_percent=weight) for code, weight in pairs]


def _project_sip(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    funds = _fund_weights(args.get("funds"))
    preset = args.get("preset")
    request = SipProjectionRequest(
        monthly_amount=float(args.get("monthly_amount") or 0),
        years=int(args.get("years") or 0),
        annual_step_up_percent=float(args.get("annual_step_up_percent") or 0),
        goal_amount=float(args["goal_amount"]) if args.get("goal_amount") else None,
        return_source=ReturnSource.FUNDS if funds else ReturnSource.PRESET,
        funds=funds,
        preset=ReturnPreset(preset) if preset else ReturnPreset.FLEXI_CAP,
    )
    result = project_sip(request)
    data = {
        "total_invested": result.total_invested,
        "bad_case_10th_percentile": result.bad_case,
        "typical_median": result.typical,
        "good_case_90th_percentile": result.good_case,
        "chance_of_loss_percent": result.chance_of_loss_percent,
        "goal_probability_percent": result.goal_probability_percent,
        "monthly_needed_for_goal_80_percent_chance": result.required_monthly_for_goal_80,
        "basis": result.source_description,
    }
    return ToolResult(data=data, card={"type": "sip_projection", "result": result.model_dump()})


def _replay_past_sip(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    request = SipBacktestRequest(
        funds=_fund_weights(args.get("funds")),
        monthly_amount=float(args.get("monthly_amount") or 0),
        years=int(args.get("years") or 0),
        annual_step_up_percent=float(args.get("annual_step_up_percent") or 0),
    )
    result = backtest_sip(request)
    data = {
        "start_date": result.start_date,
        "total_invested": result.total_invested,
        "value_today": result.final_value,
        "gain": result.gain,
        "xirr_percent": result.xirr_percent,
        "same_sip_in_7_percent_fd": result.fixed_deposit_value,
        "worst_dip_percent": result.worst_drawdown_percent,
        "funds": [{"name": f.short_name, "value_today": f.value, "xirr_percent": f.xirr_percent} for f in result.funds],
    }
    return ToolResult(data=data, card={"type": "sip_backtest", "result": result.model_dump()})


# ---------------------------------------------------------------- the user's recommendations


def _get_recommendation(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    rec_id = args.get("recommendation_id") or ctx.current_recommendation_id
    if not rec_id:
        history = list_recommendation_history(ctx.session, limit=1)
        if not history:
            raise InvalidRequestError("The user has no saved recommendations yet.")
        rec_id = history[0].id
    rec = get_recommendation_detail(ctx.session, int(rec_id))
    data = {
        "id": rec.id,
        "created_at": rec.created_at.isoformat(),
        "invest_in": rec.asset_mix.value,
        "mode": rec.investment_mode.value,
        "amount": rec.amount,
        "risk_level_1_to_5": rec.risk_level,
        "model": rec.model_name,
        "allocations": [
            {
                "name": a.display_name or a.ticker,
                "type": a.asset_type.value,
                "weight_percent": a.weight_percent,
                "amount": a.amount,
                "sector_or_category": a.sector,
                "reason": a.rationale,
            }
            for a in rec.allocations
        ],
        "summary": rec.summary,
        "risks": rec.risk_notes,
    }
    return ToolResult(data=data, card={"type": "recommendation", "recommendation": rec.model_dump(mode="json")})


def _list_recommendations(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    items = list_recommendation_history(ctx.session, limit=10)
    return ToolResult(
        data={
            "recommendations": [
                {
                    "id": i.id,
                    "date": i.created_at.date().isoformat(),
                    "amount": i.amount,
                    "invest_in": i.asset_mix.value,
                    "picks": i.picked_labels or i.picked_tickers,
                }
                for i in items
            ]
        }
    )


# ---------------------------------------------------------------- registry

_PRESET_NAMES = ", ".join(f'"{p.value}" ({info.label}, ~{info.annual_return_percent:g}%/yr)' for p, info in RETURN_PRESETS.items())

ASSISTANT_TOOLS: dict[str, AssistantTool] = {
    tool.name: tool
    for tool in [
        AssistantTool(
            "search_funds",
            "Find mutual funds by any part of their name (abbreviations OK). Returns scheme codes — use this "
            "before any other fund tool when the user names a fund.",
            '{"query": "parag flexi", "category": optional e.g. "Equity · Small Cap"}',
            "Searching funds for “{query}”…",
            _search_funds,
        ),
        AssistantTool(
            "get_fund_details",
            "Real performance of one fund: 1y return, 3y/5y CAGR, volatility, worst drawdown, Sharpe, NAV, category.",
            '{"scheme_code": 122639}',
            "Reading the fund's NAV history…",
            _get_fund_details,
        ),
        AssistantTool(
            "compare_funds",
            "Side-by-side performance of 2–4 funds.",
            '{"scheme_codes": [122639, 118955]}',
            "Comparing funds…",
            _compare_funds,
        ),
        AssistantTool(
            "get_stock_details",
            "One NSE/BSE stock: price, returns, RSI, volatility, P/E, ROE, growth, debt, dividend and recent headlines.",
            '{"ticker": "TCS"}',
            "Looking up {ticker}…",
            _get_stock_details,
        ),
        AssistantTool(
            "project_sip",
            "Project a FUTURE monthly SIP as a bad/typical/good range (4,000 simulated paths). Pass `funds` (from "
            f"search_funds) to use their real history, or a `preset` instead: {_PRESET_NAMES}.",
            '{"monthly_amount": 10000, "years": 10, "annual_step_up_percent": 0, "goal_amount": optional, '
            '"funds": [{"scheme_code": 122639, "weight_percent": 100}] OR "preset": "flexi_cap"}',
            "Simulating 4,000 market paths…",
            _project_sip,
        ),
        AssistantTool(
            "replay_past_sip",
            "What a SIP started N years ago would be worth TODAY, at real historical NAVs (with XIRR and an FD comparison).",
            '{"monthly_amount": 10000, "years": 10, "funds": [{"scheme_code": 122639, "weight_percent": 100}]}',
            "Replaying every month at real NAVs…",
            _replay_past_sip,
        ),
        AssistantTool(
            "get_recommendation",
            "Read one of the user's saved recommendations (holdings, weights, reasons, risks). Omit the id to get the one "
            "they're viewing, or else their latest.",
            '{"recommendation_id": optional}',
            "Reading your recommendation…",
            _get_recommendation,
        ),
        AssistantTool(
            "list_recommendations",
            "The user's 10 most recent saved recommendations (id, date, amount, picks).",
            "{}",
            "Checking your history…",
            _list_recommendations,
        ),
    ]
}


def run_tool(name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    tool = ASSISTANT_TOOLS.get(name)
    if tool is None:
        raise InvalidRequestError(f"Unknown tool '{name}'. Available: {', '.join(ASSISTANT_TOOLS)}.")
    try:
        return tool.handler(ctx, args if isinstance(args, dict) else {})
    except StockAdvisorError:
        raise
    except ValidationError as exc:  # bad arguments from the model: tell it which field, briefly
        problems = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'input'}: {e['msg']}" for e in exc.errors())
        raise InvalidRequestError(f"Bad arguments for {name} — {problems}") from exc
    except (ValueError, TypeError) as exc:
        raise InvalidRequestError(f"Bad arguments for {name}: {exc}") from exc


def tool_status_text(name: str, args: dict[str, Any]) -> str:
    tool = ASSISTANT_TOOLS.get(name)
    if tool is None:
        return "Working…"
    try:
        return tool.status.format(**{k: str(v) for k, v in (args or {}).items()})
    except (KeyError, IndexError):
        return tool.status.split("{")[0].strip() or "Working…"


def _as_int(value: Any, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidRequestError(f"`{name}` must be a number (use search_funds to find scheme codes).") from exc
