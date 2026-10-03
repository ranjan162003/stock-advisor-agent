import type {
  ChatConversationDetail,
  ChatConversationSummary,
  ChatSendRequest,
  ChatStreamEvent,
} from "../types/chat.types";
import { ApiError, requestJson } from "./httpClient";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export const chatApi = {
  listConversations: () => requestJson<ChatConversationSummary[]>("/api/chat/conversations"),

  createConversation: () => requestJson<ChatConversationDetail>("/api/chat/conversations", { method: "POST" }),

  getConversation: (id: number) => requestJson<ChatConversationDetail>(`/api/chat/conversations/${id}`),

  renameConversation: (id: number, title: string) =>
    requestJson<ChatConversationSummary>(`/api/chat/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),

  deleteConversation: (id: number) => requestJson<void>(`/api/chat/conversations/${id}`, { method: "DELETE" }),

  /**
   * Send a message and call `onEvent` for each streamed event (status → card* → answer → done | error).
   * EventSource can't POST, so this reads the SSE stream from fetch directly.
   */
  async sendMessage(
    conversationId: number,
    request: ChatSendRequest,
    onEvent: (event: ChatStreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}/api/chat/conversations/${conversationId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify(request),
        signal,
      });
    } catch (error) {
      if (signal?.aborted) throw error;
      throw new ApiError("Can't reach the backend. Is it running on port 8000?", 0);
    }
    if (!response.ok || !response.body) {
      const body = await response.json().catch(() => null);
      const detail = body && typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`;
      throw new ApiError(detail, response.status);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const data = block
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n");
        if (data) onEvent(JSON.parse(data) as ChatStreamEvent);
        boundary = buffer.indexOf("\n\n");
      }
      if (done) return;
    }
  },
};
