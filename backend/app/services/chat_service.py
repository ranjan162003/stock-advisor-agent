"""Ask-AI chats: saved conversations and one streamed assistant turn.

`stream_chat_reply` yields Server-Sent-Event lines (`data: {...}\n\n`) so the
UI can show live status ("Searching funds…"), cards as soon as a tool returns,
and finally the answer. The question and answer are saved together only when
the turn succeeds.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.agent.providers.llm_provider_registry import get_llm_provider
from app.assistant.assistant_agent import TurnOutcome, run_assistant_turn
from app.assistant.assistant_tools import ToolContext
from app.core.app_exceptions import ProviderNotConnectedError, ResourceNotFoundError, StockAdvisorError
from app.db.orm_models import ChatConversation, ChatMessage
from app.db.repositories import chat_repository
from app.schemas.chat_schemas import (
    ChatConversationDetail,
    ChatConversationSummary,
    ChatMessageRead,
    ChatSendRequest,
)

logger = logging.getLogger(__name__)

TITLE_LENGTH = 60


def list_chats(session: Session, limit: int) -> list[ChatConversationSummary]:
    return [_summary(c) for c in chat_repository.list_conversations(session, limit)]


def create_chat(session: Session) -> ChatConversationDetail:
    return _detail(chat_repository.create_conversation(session))


def get_chat(session: Session, conversation_id: int) -> ChatConversationDetail:
    return _detail(_require(session, conversation_id))


def rename_chat(session: Session, conversation_id: int, title: str) -> ChatConversationSummary:
    conversation = _require(session, conversation_id)
    chat_repository.rename_conversation(session, conversation, title.strip())
    return _summary(conversation)


def delete_chat(session: Session, conversation_id: int) -> None:
    chat_repository.delete_conversation(session, _require(session, conversation_id))


def stream_chat_reply(session: Session, conversation_id: int, request: ChatSendRequest) -> Iterator[str]:
    """Run one assistant turn, yielding SSE lines. Never raises — failures become an `error` event."""
    try:
        conversation = _require(session, conversation_id)
        yield _event({"type": "status", "text": "Connecting to the model…"})

        provider = get_llm_provider(request.provider_id)
        status = provider.get_status()
        if not status.is_ready:
            hint = f" {status.setup_hint}" if status.setup_hint else ""
            raise ProviderNotConnectedError(f"{provider.display_name}: {status.status_message}{hint}")

        history = [(m.role, m.content) for m in conversation.messages]
        ctx = ToolContext(session=session, current_recommendation_id=request.recommendation_id)
        outcome = TurnOutcome()
        for event in run_assistant_turn(
            provider, request.model_name or status.default_model, history, request.message, ctx, request.page, outcome
        ):
            yield _event(event)

        if not conversation.messages:
            conversation.title = _title_from(request.message)
        user_message = ChatMessage(role="user", content=request.message)
        assistant_message = ChatMessage(
            role="assistant",
            content=outcome.answer,
            cards_json=json.dumps(outcome.cards, default=str),
            suggestions_json=json.dumps(outcome.suggestions),
        )
        chat_repository.add_exchange(session, conversation, user_message, assistant_message)
        yield _event(
            {
                "type": "done",
                "conversation": _summary(conversation).model_dump(mode="json"),
                "user_message": _message(user_message).model_dump(mode="json"),
                "assistant_message": _message(assistant_message).model_dump(mode="json"),
            }
        )
    except StockAdvisorError as exc:
        session.rollback()
        yield _event({"type": "error", "message": exc.message})
    except Exception:  # the stream has already started, so an HTTP error is no longer possible
        logger.exception("Chat turn failed")
        session.rollback()
        yield _event({"type": "error", "message": "Something went wrong while answering. Please try again."})


def _event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _title_from(message: str) -> str:
    text = " ".join(message.split())
    return text if len(text) <= TITLE_LENGTH else text[: TITLE_LENGTH - 1].rsplit(" ", 1)[0] + "…"


def _require(session: Session, conversation_id: int) -> ChatConversation:
    conversation = chat_repository.get_conversation(session, conversation_id)
    if conversation is None:
        raise ResourceNotFoundError(f"Chat #{conversation_id} not found.")
    return conversation


def _summary(c: ChatConversation) -> ChatConversationSummary:
    return ChatConversationSummary(id=c.id, title=c.title, created_at=c.created_at, updated_at=c.updated_at)


def _message(m: ChatMessage) -> ChatMessageRead:
    return ChatMessageRead(
        id=m.id,
        role=m.role,
        content=m.content,
        cards=json.loads(m.cards_json or "[]"),
        suggestions=json.loads(m.suggestions_json or "[]"),
        created_at=m.created_at,
    )


def _detail(c: ChatConversation) -> ChatConversationDetail:
    return ChatConversationDetail(**_summary(c).model_dump(), messages=[_message(m) for m in c.messages])
