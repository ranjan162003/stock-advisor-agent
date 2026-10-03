"""Ask-AI assistant: reply parsing, the tool loop, and the streamed chat API (no network)."""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.providers.base_llm_provider import BaseLlmProvider
from app.api.routes import chat_routes
from app.assistant import assistant_agent, assistant_tools
from app.assistant.assistant_agent import MAX_TOOL_CALLS, TurnOutcome, parse_assistant_reply, run_assistant_turn
from app.assistant.assistant_tools import ToolContext, ToolResult
from app.db.database_session import OrmBase, get_db_session
from app.main import create_app
from app.schemas.provider_schemas import AuthMethod, ProviderId, ProviderStatus
from app.services import chat_service


class ScriptedProvider(BaseLlmProvider):
    """Replies with a fixed sequence of model outputs and records each prompt."""

    provider_id = ProviderId.OLLAMA
    display_name = "Fake"

    def __init__(self, replies: list[str], ready: bool = True):
        self.replies = list(replies)
        self.prompts: list[str] = []
        self.ready = ready

    def get_status(self) -> ProviderStatus:
        return ProviderStatus(
            provider_id=self.provider_id, display_name="Fake", description="", supports_cli_login=False,
            supports_api_key=False, is_ready=self.ready, active_auth_method=AuthMethod.LOCAL_SERVER,
            default_model="fake-model", status_message="ok" if self.ready else "Not running.",
        )

    def generate_text(self, prompt: str, model_name: str | None = None, json_schema: dict | None = None) -> str:
        self.prompts.append(prompt)
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


def answer(text: str, suggestions=()) -> str:
    return json.dumps({"action": "answer", "answer": text, "suggestions": list(suggestions)})


def tool_call(name: str, **arguments) -> str:
    return json.dumps({"action": "tool", "tool": name, "arguments": arguments})


# ---------------------------------------------------------------- parsing


def test_parse_reply_reads_tool_calls_and_answers():
    call = parse_assistant_reply('```json\n{"action": "tool", "tool": "search_funds", "arguments": {"query": "parag"}}\n```')
    assert (call.action, call.tool, call.arguments) == ("tool", "search_funds", {"query": "parag"})

    reply = parse_assistant_reply(answer("Hi **there**", ["a", "b", "c", "d"]))
    assert reply.action == "answer" and reply.answer == "Hi **there**" and reply.suggestions == ["a", "b", "c"]


def test_parse_reply_treats_plain_text_as_the_answer():
    reply = parse_assistant_reply("XIRR is your annualised return.")
    assert reply.action == "answer" and reply.answer == "XIRR is your annualised return."


# ---------------------------------------------------------------- agent loop


def run_turn(provider, monkeypatch=None, tools=None):
    outcome = TurnOutcome()
    events = list(
        run_assistant_turn(provider, None, [], "How has Parag Parikh done?", ToolContext(session=None), "planner", outcome)
    )
    return events, outcome


def test_turn_runs_a_tool_then_answers_with_its_card(monkeypatch):
    calls = []

    def fake_run_tool(name, args, ctx):
        calls.append((name, args))
        return ToolResult(data={"cagr_3y_percent": 18.2}, card={"type": "fund", "fund": {"name": "Parag Parikh"}})

    monkeypatch.setattr(assistant_agent, "run_tool", fake_run_tool)
    provider = ScriptedProvider([tool_call("get_fund_details", scheme_code=122639), answer("It returned **18.2%** a year.", ["Compare it"])])

    events, outcome = run_turn(provider)

    assert calls == [("get_fund_details", {"scheme_code": 122639})]
    assert [e["type"] for e in events] == ["status", "status", "card", "status", "answer"]
    assert outcome.answer == "It returned **18.2%** a year." and outcome.suggestions == ["Compare it"]
    assert outcome.cards == [{"type": "fund", "fund": {"name": "Parag Parikh"}}]
    # The tool's result is fed back to the model on the next step.
    assert '"cagr_3y_percent": 18.2' in provider.prompts[1]


def test_tool_errors_are_shown_to_the_model_not_raised(monkeypatch):
    provider = ScriptedProvider([tool_call("no_such_tool"), answer("Sorry, I couldn't look that up.")])
    events, outcome = run_turn(provider)
    assert "ERROR: Unknown tool 'no_such_tool'" in provider.prompts[1]
    assert outcome.answer == "Sorry, I couldn't look that up."


def test_turn_forces_an_answer_after_the_tool_budget(monkeypatch):
    monkeypatch.setattr(assistant_agent, "run_tool", lambda *_: ToolResult(data={}))
    provider = ScriptedProvider([tool_call("search_funds", query="x")])  # never stops asking for tools
    events, outcome = run_turn(provider)
    assert len(provider.prompts) == MAX_TOOL_CALLS + 1
    assert "Answer now" in provider.prompts[-1]
    assert events[-1]["type"] == "answer" and outcome.answer  # a fallback answer, not an endless loop


def test_tool_status_text_fills_in_arguments():
    assert assistant_tools.tool_status_text("search_funds", {"query": "parag"}) == "Searching funds for “parag”…"
    assert assistant_tools.tool_status_text("get_stock_details", {}) == "Looking up"


# ---------------------------------------------------------------- API


@pytest.fixture
def chat_client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    OrmBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    holder = {"provider": ScriptedProvider([answer("Hello!", ["What is a SIP?"])])}
    monkeypatch.setattr(chat_routes, "stream_session_factory", session_factory)
    monkeypatch.setattr(chat_service, "get_llm_provider", lambda _: holder["provider"])
    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app), holder


def read_events(response) -> list[dict]:
    return [json.loads(line[len("data: "):]) for line in response.text.split("\n\n") if line.startswith("data: ")]


def test_chat_streams_an_answer_and_saves_the_exchange(chat_client):
    client, _ = chat_client
    chat_id = client.post("/api/chat/conversations").json()["id"]

    response = client.post(
        f"/api/chat/conversations/{chat_id}/messages",
        json={"message": "Hi, what can you do for my portfolio?", "provider_id": "ollama"},
    )
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/event-stream")
    events = read_events(response)
    assert events[-2] == {"type": "answer", "text": "Hello!", "suggestions": ["What is a SIP?"]}
    assert events[-1]["type"] == "done" and events[-1]["conversation"]["title"] == "Hi, what can you do for my portfolio?"

    saved = client.get(f"/api/chat/conversations/{chat_id}").json()
    assert [(m["role"], m["content"]) for m in saved["messages"]] == [
        ("user", "Hi, what can you do for my portfolio?"),
        ("assistant", "Hello!"),
    ]
    assert saved["messages"][1]["suggestions"] == ["What is a SIP?"]
    assert [c["id"] for c in client.get("/api/chat/conversations").json()] == [chat_id]


def test_chat_reports_a_disconnected_model_as_an_error_event(chat_client):
    client, holder = chat_client
    holder["provider"] = ScriptedProvider([answer("unused")], ready=False)
    chat_id = client.post("/api/chat/conversations").json()["id"]

    events = read_events(client.post(f"/api/chat/conversations/{chat_id}/messages", json={"message": "hi", "provider_id": "ollama"}))

    assert events[-1]["type"] == "error" and "Not running." in events[-1]["message"]
    assert client.get(f"/api/chat/conversations/{chat_id}").json()["messages"] == []  # nothing half-saved


def test_chat_rename_delete_and_missing(chat_client):
    client, _ = chat_client
    chat_id = client.post("/api/chat/conversations").json()["id"]
    assert client.patch(f"/api/chat/conversations/{chat_id}", json={"title": "Retirement"}).json()["title"] == "Retirement"
    assert client.delete(f"/api/chat/conversations/{chat_id}").status_code == 204
    assert client.get(f"/api/chat/conversations/{chat_id}").status_code == 404
    events = read_events(client.post(f"/api/chat/conversations/{chat_id}/messages", json={"message": "hi", "provider_id": "ollama"}))
    assert events == [{"type": "error", "message": f"Chat #{chat_id} not found."}]
