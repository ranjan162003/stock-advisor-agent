"""Ask-AI chat: conversations, messages and the send-message request."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.utc_time import UtcDatetime
from app.schemas.provider_schemas import ProviderId


class ChatMessageRead(BaseModel):
    id: int
    role: str
    content: str
    cards: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    created_at: UtcDatetime


class ChatConversationSummary(BaseModel):
    id: int
    title: str
    created_at: UtcDatetime
    updated_at: UtcDatetime


class ChatConversationDetail(ChatConversationSummary):
    messages: list[ChatMessageRead]


class ChatConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ChatSendRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    provider_id: ProviderId
    model_name: str | None = Field(default=None, max_length=64)
    page: str | None = Field(default=None, max_length=40, description='Where the user asked from, e.g. "advisor"')
    recommendation_id: int | None = Field(default=None, description="The recommendation on screen, if any")
