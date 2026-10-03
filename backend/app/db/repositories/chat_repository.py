from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.orm_models import ChatConversation, ChatMessage, utc_now


def create_conversation(session: Session) -> ChatConversation:
    conversation = ChatConversation()
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def list_conversations(session: Session, limit: int) -> list[ChatConversation]:
    query = select(ChatConversation).order_by(ChatConversation.updated_at.desc()).limit(limit)
    return list(session.scalars(query))


def get_conversation(session: Session, conversation_id: int) -> ChatConversation | None:
    return session.get(ChatConversation, conversation_id)


def add_exchange(
    session: Session, conversation: ChatConversation, user_message: ChatMessage, assistant_message: ChatMessage
) -> None:
    """Save a question and its answer together, so a failed turn leaves no half-exchange behind."""
    conversation.messages.extend([user_message, assistant_message])
    conversation.updated_at = utc_now()
    session.commit()


def rename_conversation(session: Session, conversation: ChatConversation, title: str) -> None:
    conversation.title = title
    session.commit()


def delete_conversation(session: Session, conversation: ChatConversation) -> None:
    session.delete(conversation)
    session.commit()
