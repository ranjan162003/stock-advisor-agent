"""Full API flow with market data and the LLM replaced by fakes (no network)."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.providers.base_llm_provider import BaseLlmProvider
from app.analysis.fund_snapshot_builder import FundSnapshotBuildResult
from app.analysis.stock_snapshot_builder import SnapshotBuildResult
from app.db.database_session import OrmBase, get_db_session
from app.main import create_app
from app.schemas.market_data_schemas import FundamentalMetrics, StockSnapshot, TechnicalIndicators
from app.schemas.mutual_fund_schemas import FundMetrics, FundSnapshot
from app.schemas.provider_schemas import AuthMethod, ProviderId, ProviderStatus
from app.services import recommendation_service


class FakeOllamaProvider(BaseLlmProvider):
    provider_id = ProviderId.OLLAMA
    display_name = "Fake"

    def __init__(self):
        self.prompts: list[str] = []
        self.reply = (
            '{"picks": [{"ticker": "TCS.NS", "weight_percent": 70, "rationale": "Quality"},'
            '{"ticker": "ITC.NS", "weight_percent": 30, "rationale": "Defensive"}],'
            '"summary": "Test summary", "risk_notes": ["Test risk"]}'
        )

    def get_status(self) -> ProviderStatus:
        return ProviderStatus(
            provider_id=self.provider_id, display_name="Fake", description="", supports_cli_login=False,
            supports_api_key=False, is_ready=True, active_auth_method=AuthMethod.LOCAL_SERVER,
            default_model="fake-model", status_message="ok",
        )

    def generate_text(self, prompt: str, model_name: str | None = None, json_schema: dict | None = None) -> str:
        self.prompts.append(prompt)
        return self.reply


def fake_snapshot(ticker: str, price: float) -> StockSnapshot:
    return StockSnapshot(
        ticker=ticker, company_name=ticker, sector=ticker,
        technicals=TechnicalIndicators(last_close=price, annualized_volatility_percent=22, return_6m_percent=8),
        fundamentals=FundamentalMetrics(trailing_pe=25),
        fetched_at=datetime.now(timezone.utc),
    )


def fake_fund(code: int, short_name: str, nav: float, risk_class: int) -> FundSnapshot:
    return FundSnapshot(
        symbol=f"MF:{code}", scheme_code=code, scheme_name=f"{short_name} Fund - Direct Plan - Growth",
        short_name=short_name, category="Flexi cap", risk_class=risk_class,
        metrics=FundMetrics(latest_nav=nav, nav_date="2026-10-01", history_years=8, cagr_3y_percent=15,
                            max_drawdown_3y_percent=-12, sharpe_ratio_3y=0.9),
        fetched_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def client_and_provider(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    OrmBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    provider = FakeOllamaProvider()
    monkeypatch.setattr(recommendation_service, "get_llm_provider", lambda _: provider)
    monkeypatch.setattr(
        recommendation_service,
        "build_stock_snapshots",
        lambda session, tickers, settings: SnapshotBuildResult(
            snapshots=[fake_snapshot("TCS.NS", 4000), fake_snapshot("ITC.NS", 450), fake_snapshot("INFY.NS", 1800)],
            skipped={"BAD.NS": "No price history found"},
        ),
    )

    monkeypatch.setattr(
        recommendation_service,
        "build_fund_snapshots",
        lambda session, codes, settings: FundSnapshotBuildResult(
            snapshots=[fake_fund(122639, "Parag Parikh Flexi Cap", 80.0, 3), fake_fund(119800, "SBI Liquid", 4000.0, 1)],
        ),
    )

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app), provider


def test_one_time_recommendation_is_split_in_rupees_and_saved(client_and_provider):
    client, provider = client_and_provider
    response = client.post(
        "/api/recommendations",
        json={
            "investment_mode": "one_time", "amount": 50000, "risk_level": 3, "provider_id": "ollama",
            "universe_source": "custom", "custom_tickers": ["tcs", "itc", "infy", "bad"],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    allocations = {a["ticker"]: a for a in body["allocations"]}
    assert allocations["TCS.NS"]["amount"] == 35000
    assert allocations["TCS.NS"]["approx_whole_shares"] == 8
    assert allocations["ITC.NS"]["amount"] == 15000
    assert body["skipped_tickers"] == {"BAD.NS": "No price history found"}
    assert "not licensed financial advice" in body["disclaimer"]
    assert "One-time lump sum" in provider.prompts[0]

    history = client.get("/api/recommendations").json()
    assert history[0]["picked_tickers"] == ["TCS.NS", "ITC.NS"]
    assert client.get(f"/api/recommendations/{body['id']}").json()["summary"] == "Test summary"


def test_recurring_requires_a_frequency(client_and_provider):
    client, _ = client_and_provider
    response = client.post(
        "/api/recommendations",
        json={"investment_mode": "recurring", "amount": 10000, "risk_level": 2, "provider_id": "ollama"},
    )
    assert response.status_code == 422


def test_recurring_prompt_asks_for_a_long_term_target(client_and_provider):
    client, provider = client_and_provider
    response = client.post(
        "/api/recommendations",
        json={
            "investment_mode": "recurring", "recurring_frequency": "monthly", "amount": 10000,
            "risk_level": 2, "provider_id": "ollama",
        },
    )
    assert response.status_code == 201, response.text
    assert "every month" in provider.prompts[0]


def test_mixed_portfolio_returns_stocks_and_fund_units(client_and_provider):
    client, provider = client_and_provider
    provider.reply = (
        '{"picks": [{"ticker": "TCS.NS", "weight_percent": 40, "rationale": "Quality stock"},'
        '{"ticker": "MF:122639", "weight_percent": 60, "rationale": "Diversified core"}],'
        '"summary": "Mostly funds", "risk_notes": []}'
    )
    response = client.post(
        "/api/recommendations",
        json={"investment_mode": "one_time", "amount": 50000, "risk_level": 2, "provider_id": "ollama",
              "asset_mix": "mixed"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["asset_mix"] == "mixed"
    fund = next(a for a in body["allocations"] if a["asset_type"] == "mutual_fund")
    assert fund["display_name"] == "Parag Parikh Flexi Cap"
    assert fund["amount"] == 30000
    assert fund["approx_units"] == 375.0
    stock = next(a for a in body["allocations"] if a["asset_type"] == "stock")
    assert stock["approx_whole_shares"] == 5
    assert {c["asset_type"] for c in body["candidates_considered"]} == {"stock", "mutual_fund"}
    assert "Candidate mutual funds" in provider.prompts[0]
    assert "at least one stock AND at least one mutual fund" in provider.prompts[0]

    history = client.get("/api/recommendations").json()
    assert history[0]["picked_labels"] == ["Parag Parikh Flexi Cap", "TCS"]


def test_funds_only_prompt_has_no_stocks(client_and_provider):
    client, provider = client_and_provider
    provider.reply = (
        '{"picks": [{"ticker": "MF:122639", "weight_percent": 70, "rationale": "Core"},'
        '{"ticker": "MF:119800", "weight_percent": 30, "rationale": "Cushion"}], "summary": "s", "risk_notes": []}'
    )
    response = client.post(
        "/api/recommendations",
        json={"investment_mode": "recurring", "recurring_frequency": "monthly", "amount": 10000,
              "risk_level": 2, "provider_id": "ollama", "asset_mix": "mutual_funds"},
    )
    assert response.status_code == 201, response.text
    assert all(a["asset_type"] == "mutual_fund" for a in response.json()["allocations"])
    assert "Candidate stocks" not in provider.prompts[0]
    assert "SIP" in provider.prompts[0]


def test_custom_ticker_list_is_rejected_for_funds_only(client_and_provider):
    client, _ = client_and_provider
    response = client.post(
        "/api/recommendations",
        json={"investment_mode": "one_time", "amount": 10000, "risk_level": 3, "provider_id": "ollama",
              "asset_mix": "mutual_funds", "universe_source": "custom", "custom_tickers": ["TCS", "INFY"]},
    )
    assert response.status_code == 422
