import { Check, MessageSquare, Pencil, Plus, Trash2, X } from "lucide-react";
import { useState, type FormEvent } from "react";

import { ChatThread } from "../components/assistant/ChatThread";
import { ExportChatButton } from "../components/assistant/ExportChatButton";
import { useAssistant, useAssistantPageContext } from "../context/AssistantContext";
import { useUndoableDelete } from "../context/ToastContext";
import type { ChatConversationSummary } from "../types/chat.types";
import { formatDateTime } from "../utils/displayFormatters";

/** Full-page Ask AI: saved conversations on the left, the chat on the right. */
export function AssistantPage() {
  useAssistantPageContext("assistant");
  const { conversations, activeConversationId, openConversation, startNewChat, deleteConversation } = useAssistant();
  const deleteWithUndo = useUndoableDelete();
  // Chats waiting out their Undo window: hidden here, deleted on the server only if not undone.
  const [hiddenIds, setHiddenIds] = useState<Set<number>>(new Set());
  // Phones: the saved-chats list folds away so the chat gets the whole screen.
  const [isListOpen, setIsListOpen] = useState(false);
  const visible = conversations.filter((c) => !hiddenIds.has(c.id));

  const setHidden = (id: number, hidden: boolean) =>
    setHiddenIds((current) => {
      const next = new Set(current);
      if (hidden) next.add(id);
      else next.delete(id);
      return next;
    });

  const removeChat = (conversation: ChatConversationSummary) =>
    deleteWithUndo({
      message: `Deleted “${conversation.title}”`,
      hide: () => {
        setHidden(conversation.id, true);
        if (conversation.id === activeConversationId) startNewChat();
      },
      restore: () => setHidden(conversation.id, false),
      commit: () => deleteConversation(conversation.id).finally(() => setHidden(conversation.id, false)),
    });

  return (
    <div className={`assistant-page${isListOpen ? " assistant-page--list-open" : ""}`}>
      <aside className="assistant-page__list" aria-label="Saved chats">
        <div className="assistant-page__list-actions">
          <button
            type="button"
            className="button button--primary button--block"
            onClick={() => {
              startNewChat();
              setIsListOpen(false);
            }}
          >
            <Plus size={16} /> New chat
          </button>
          <button
            type="button"
            className="button button--secondary assistant-page__list-toggle"
            onClick={() => setIsListOpen((open) => !open)}
            aria-expanded={isListOpen}
          >
            <MessageSquare size={16} /> Chats <span className="tabs__count">{visible.length}</span>
          </button>
        </div>
        <div className="assistant-page__list-body">
          <ExportChatButton variant="button" />
          {visible.length === 0 ? (
            <p className="muted assistant-page__empty">Your chats are saved here.</p>
          ) : (
            <ul className="chat-history">
              {visible.map((c) => (
                <ConversationRow
                  key={c.id}
                  conversation={c}
                  isActive={c.id === activeConversationId}
                  onOpen={() => {
                    void openConversation(c.id);
                    setIsListOpen(false);
                  }}
                  onDelete={() => removeChat(c)}
                />
              ))}
            </ul>
          )}
        </div>
      </aside>
      <section className="assistant-page__chat card">
        <ChatThread />
      </section>
    </div>
  );
}

function ConversationRow({
  conversation,
  isActive,
  onOpen,
  onDelete,
}: {
  conversation: ChatConversationSummary;
  isActive: boolean;
  onOpen: () => void;
  onDelete: () => void;
}) {
  const { renameConversation } = useAssistant();
  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState(conversation.title);

  const saveTitle = async (event: FormEvent) => {
    event.preventDefault();
    if (title.trim() && title.trim() !== conversation.title) await renameConversation(conversation.id, title.trim());
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <li className="chat-history__item chat-history__item--editing">
        <form onSubmit={saveTitle} className="chat-history__rename">
          <input
            className="input input--compact"
            value={title}
            maxLength={120}
            autoFocus
            onChange={(e) => setTitle(e.target.value)}
          />
          <button type="submit" className="icon-button icon-button--subtle" aria-label="Save name">
            <Check size={16} />
          </button>
          <button
            type="button"
            className="icon-button icon-button--subtle"
            aria-label="Cancel"
            onClick={() => setIsEditing(false)}
          >
            <X size={16} />
          </button>
        </form>
      </li>
    );
  }

  return (
    <li className={`chat-history__item${isActive ? " chat-history__item--active" : ""}`}>
      <button type="button" className="chat-history__open" onClick={onOpen}>
        <MessageSquare size={15} />
        <span className="chat-history__text">
          <span className="chat-history__title">{conversation.title}</span>
          <span className="chat-history__date">{formatDateTime(conversation.updated_at)}</span>
        </span>
      </button>
      <span className="chat-history__actions">
        <button
          type="button"
          className="icon-button icon-button--subtle"
          aria-label="Rename chat"
          onClick={() => setIsEditing(true)}
        >
          <Pencil size={14} />
        </button>
        <button
          type="button"
          className="icon-button icon-button--subtle"
          aria-label="Delete chat"
          onClick={onDelete}
        >
          <Trash2 size={14} />
        </button>
      </span>
    </li>
  );
}
