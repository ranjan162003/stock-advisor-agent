"""Ask-AI chats: saved conversations and a streamed (SSE) send-message endpoint."""
from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database_session import SessionFactory, get_db_session
from app.schemas.chat_schemas import (
    ChatConversationDetail,
    ChatConversationRename,
    ChatConversationSummary,
    ChatSendRequest,
)
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])

# The stream outlives the request's dependency scope, so it opens its own session.
# (Tests swap this for an in-memory database.)
stream_session_factory = SessionFactory


@router.get("/conversations", response_model=list[ChatConversationSummary])
def read_conversations(
    limit: int = Query(default=50, ge=1, le=200), session: Session = Depends(get_db_session)
) -> list[ChatConversationSummary]:
    return chat_service.list_chats(session, limit)


@router.post("/conversations", response_model=ChatConversationDetail, status_code=status.HTTP_201_CREATED)
def create_conversation(session: Session = Depends(get_db_session)) -> ChatConversationDetail:
    return chat_service.create_chat(session)


@router.get("/conversations/{conversation_id}", response_model=ChatConversationDetail)
def read_conversation(conversation_id: int, session: Session = Depends(get_db_session)) -> ChatConversationDetail:
    return chat_service.get_chat(session, conversation_id)


@router.patch("/conversations/{conversation_id}", response_model=ChatConversationSummary)
def rename_conversation(
    conversation_id: int, body: ChatConversationRename, session: Session = Depends(get_db_session)
) -> ChatConversationSummary:
    return chat_service.rename_chat(session, conversation_id, body.title)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_conversation(conversation_id: int, session: Session = Depends(get_db_session)) -> None:
    chat_service.delete_chat(session, conversation_id)


@router.post("/conversations/{conversation_id}/messages")
def send_message(conversation_id: int, request: ChatSendRequest) -> StreamingResponse:
    """Stream the assistant's turn as Server-Sent Events: status → card* → answer → done (or error)."""

    def events() -> Iterator[str]:
        session = stream_session_factory()
        try:
            yield from chat_service.stream_chat_reply(session, conversation_id, request)
        finally:
            session.close()

    # A sync generator: Starlette iterates it in a worker thread, so blocking LLM calls are fine.
    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
