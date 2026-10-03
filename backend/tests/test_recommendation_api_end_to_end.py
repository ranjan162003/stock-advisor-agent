"""Full API flow with market data and the LLM replaced by fakes (no network)."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.providers.base_llm_provider import BaseLlmProvider
from app.analysis.stock_snapshot_builder import SnapshotBuildResult
from app.db.database_session import OrmBase, get_db_session
from app.main import create_app
from app.schemas.market_data_schemas import FundamentalMetrics, StockSnapshot, TechnicalIndicators
from app.schemas.provider_schemas import AuthMethod, ProviderId, ProviderStatus
from app.services import recommendation_service


class FakeOllamaProvider(BaseLlmProvider):
    provider_id = ProviderId.OLLAMA
    display_name = "Fake"

    def __init__(self):
        self.prompts: list[str] = []

    def get_status(self) -> ProviderStatus:
        return ProviderStatus(
            provider_id=self.provider_id, display_name="Fake", description="", supports_cli_login=False,
            supports_api_key=False, is_ready=True, active_auth_method=AuthMethod.LOCAL_SERVER,
            default_model="fake-model", status_message="ok",
        )

    def generate_text(self, prompt: str, model_name: str | None = None) -> str:
        self.prompts.append(prompt)
        return (
            '{"picks": [{"ticker": "TCS.NS", "weight_percent": 70, "rationale": "Quality"},'
            '{"ticker": "ITC.NS", "weight_percent": 30, "rationale": "Defensive"}],'
            '"summary": "Test summary", "risk_notes": ["Test risk"]}'
        )


def fake_snapshot(ticker: str, price: float) -> StockSnapshot:
    return StockSnapshot(
        ticker=ticker, company_name=ticker, sector=ticker,
        technicals=TechnicalIndicators(last_close=price, annualized_volatility_percent=22, return_6m_percent=8),
        fundamentals=FundamentalMetrics(trailing_pe=25),
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
