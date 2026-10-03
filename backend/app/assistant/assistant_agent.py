"""The chat assistant's agent loop: think → (tool → observe)* → answer.

`run_assistant_turn` is a generator of UI events so the frontend can show what
the agent is doing in real time:

    {"type": "status", "text": "Searching funds for “parag”…"}
    {"type": "card", "card": {...}}                      # fund card, chart, …
    {"type": "answer", "text": "...", "suggestions": [...]}
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from app.agent.providers.base_llm_provider import BaseLlmProvider
from app.agent.recommendation_response_parser import extract_json_object
from app.assistant.assistant_prompt_builder import ASSISTANT_REPLY_SCHEMA, TurnStep, build_assistant_prompt
from app.assistant.assistant_tools import ToolContext, run_tool, tool_status_text
from app.core.app_exceptions import RecommendationParseError, StockAdvisorError

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 4


@dataclass
class TurnOutcome:
    answer: str = ""
    suggestions: list[str] = field(default_factory=list)
    cards: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ParsedReply:
    action: str  # "tool" | "answer"
    tool: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    answer: str = ""
    suggestions: list[str] = field(default_factory=list)


def parse_assistant_reply(raw: str) -> ParsedReply:
    """Read the model's JSON step; anything that isn't valid JSON is treated as a plain answer."""
    try:
        payload = extract_json_object(raw)
    except RecommendationParseError:
        return ParsedReply(action="answer", answer=raw.strip())

    suggestions = [str(s).strip() for s in payload.get("suggestions") or [] if str(s).strip()][:3]
    if payload.get("action") == "tool" or (payload.get("tool") and not payload.get("answer")):
        arguments = payload.get("arguments")
        return ParsedReply(action="tool", tool=str(payload.get("tool") or ""), arguments=arguments if isinstance(arguments, dict) else {})
    answer = payload.get("answer")
    return ParsedReply(action="answer", answer=str(answer).strip() if answer else raw.strip(), suggestions=suggestions)


def run_assistant_turn(
    provider: BaseLlmProvider,
    model_name: str | None,
    history: list[tuple[str, str]],
    user_message: str,
    ctx: ToolContext,
    page: str | None,
    outcome: TurnOutcome,
) -> Iterator[dict[str, Any]]:
    """Yield UI events while the agent works; the final answer/cards are also stored on `outcome`."""
    steps: list[TurnStep] = []
    yield {"type": "status", "text": f"{provider.display_name} is thinking…"}

    for attempt in range(MAX_TOOL_CALLS + 1):
        must_answer = attempt == MAX_TOOL_CALLS
        prompt = build_assistant_prompt(history, user_message, steps, page, ctx.current_recommendation_id, must_answer)
        raw = provider.generate_text(prompt, model_name, json_schema=ASSISTANT_REPLY_SCHEMA)
        reply = parse_assistant_reply(raw)

        if reply.action == "answer" or must_answer or not reply.tool:
            outcome.answer = reply.answer or "Sorry — I couldn't put an answer together. Could you rephrase?"
            outcome.suggestions = reply.suggestions
            yield {"type": "answer", "text": outcome.answer, "suggestions": outcome.suggestions}
            return

        yield {"type": "status", "text": tool_status_text(reply.tool, reply.arguments)}
        step = TurnStep(tool=reply.tool, arguments=reply.arguments)
        try:
            result = run_tool(reply.tool, reply.arguments, ctx)
            step.result = result.data
            if result.card:
                outcome.cards.append(result.card)
                yield {"type": "card", "card": result.card}
        except StockAdvisorError as exc:
            logger.info("Assistant tool %s failed: %s", reply.tool, exc.message)
            step.error = exc.message
        steps.append(step)
        yield {"type": "status", "text": f"{provider.display_name} is reading the results…"}
