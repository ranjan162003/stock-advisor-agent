"""Prompt for the chat assistant: persona, rules, tools, context and the running turn.

The model replies with ONE JSON object per step — either a tool call or the
final answer — which works the same on Claude, Gemini and Ollama because the
backend (not a vendor tool-calling API) runs the tools.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from app.assistant.assistant_tools import ASSISTANT_TOOLS

MAX_TOOL_RESULT_CHARS = 6000
HISTORY_MESSAGES = 10

# Machine-readable reply contract (enforced on Ollama, described to everyone).
ASSISTANT_REPLY_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["tool", "answer"]},
        "tool": {"type": "string"},
        "arguments": {"type": "object"},
        "answer": {"type": "string"},
        "suggestions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["action"],
}


@dataclass
class TurnStep:
    """One tool call made earlier in the current turn, and what it returned."""

    tool: str
    arguments: dict
    result: dict | None = None
    error: str | None = None


def build_assistant_prompt(
    history: list[tuple[str, str]],
    user_message: str,
    steps: list[TurnStep],
    page: str | None,
    current_recommendation_id: int | None,
    must_answer_now: bool = False,
) -> str:
    sections = [
        "You are the Stock Advisor assistant inside an Indian investing app. You help the user understand their "
        "AI-generated stock/mutual-fund recommendations, look up real fund and stock data, run SIP calculations, "
        "and learn investing concepts. Today is " + date.today().isoformat() + ".",
        "## Rules\n"
        "- Educational help only — not licensed financial advice. Never promise or guarantee returns.\n"
        "- Quote numbers ONLY from tool results in this conversation, and say where they come from "
        "(e.g. \"based on NAVs up to 1 Oct 2026\"). Never invent figures, NAVs or returns.\n"
        "- When the user names a fund, call search_funds first to get its scheme_code.\n"
        "- Prefer Direct-Growth plans. Mention risk alongside return.\n"
        "- You cannot place trades or change the user's portfolio.\n"
        "- Plain-English concept questions (e.g. \"what is XIRR?\") need no tool.\n"
        "- Write answers in short paragraphs or bullet lists using **bold** for key numbers, in INR (₹, lakh/crore).\n"
        "- The app shows each tool result as a card (fund/stock details, comparison table, SIP chart) right above "
        "your answer, so don't repeat every number or draw tables — say what the numbers mean for the user.\n"
        "- Keep answers focused: usually under 180 words.",
        "## Tools\n" + "\n".join(
            f"- {tool.name}: {tool.description}\n  arguments: {tool.arguments}" for tool in ASSISTANT_TOOLS.values()
        ),
        "## Reply format\n"
        "Reply with ONLY one JSON object, no text around it:\n"
        '- To use a tool: {"action": "tool", "tool": "<name>", "arguments": {...}}\n'
        '- To answer: {"action": "answer", "answer": "<markdown>", "suggestions": ["<follow-up question>", ...]}\n'
        "Give 2–3 short follow-up suggestions the user might ask next. Use at most 4 tools per question.",
    ]

    context = []
    if page:
        context.append(f"The user is on the '{page}' page.")
    if current_recommendation_id:
        context.append(
            f"They are looking at recommendation #{current_recommendation_id} — 'this', 'my portfolio' or "
            "'the result' refer to it (use get_recommendation)."
        )
    if context:
        sections.append("## Context\n" + " ".join(context))

    if history:
        sections.append(
            "## Conversation so far\n"
            + "\n".join(f"{role.upper()}: {text[:1500]}" for role, text in history[-HISTORY_MESSAGES:])
        )

    sections.append(f"## Current question\nUSER: {user_message}")

    if steps:
        lines = []
        for i, step in enumerate(steps, 1):
            outcome = (
                f"ERROR: {step.error}"
                if step.error
                else json.dumps(step.result, ensure_ascii=False, default=str)[:MAX_TOOL_RESULT_CHARS]
            )
            lines.append(f"{i}. {step.tool}({json.dumps(step.arguments, ensure_ascii=False)}) -> {outcome}")
        sections.append("## Tool results so far (this question)\n" + "\n".join(lines))

    if must_answer_now:
        sections.append("You have used all your tool calls. Answer now with what you have (action \"answer\").")
    return "\n\n".join(sections)
