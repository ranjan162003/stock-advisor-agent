import { Maximize2, Plus, Sparkles, X } from "lucide-react";
import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";

import { useAssistant } from "../../context/AssistantContext";
import { ChatThread } from "./ChatThread";
import { ExportChatButton } from "./ExportChatButton";

/** Floating "Ask AI" button plus the slide-in chat panel, available on every page except Ask AI itself. */
export function AssistantPanel() {
  const { isPanelOpen, openPanel, closePanel, startNewChat, conversations, activeConversationId } = useAssistant();
  const { pathname } = useLocation();
  const onAssistantPage = pathname.startsWith("/assistant");

  useEffect(() => {
    if (onAssistantPage) closePanel();
  }, [onAssistantPage, closePanel]);

  useEffect(() => {
    if (!isPanelOpen) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && closePanel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isPanelOpen, closePanel]);

  if (onAssistantPage) return null;
  const title = conversations.find((c) => c.id === activeConversationId)?.title ?? "New chat";

  return (
    <>
      {!isPanelOpen && (
        <button type="button" className="assistant-launcher" onClick={() => openPanel()}>
          <Sparkles size={18} />
          <span>Ask AI</span>
        </button>
      )}
      {isPanelOpen && (
        <aside className="assistant-panel" aria-label="Ask AI">
          <header className="assistant-panel__header">
            <span className="chat-avatar" aria-hidden="true">
              <Sparkles size={14} />
            </span>
            <div className="assistant-panel__title">
              <strong>Ask AI</strong>
              <span className="muted">{title}</span>
            </div>
            <button
              type="button"
              className="icon-button icon-button--subtle"
              onClick={startNewChat}
              title="New chat"
              aria-label="New chat"
            >
              <Plus size={18} />
            </button>
            <ExportChatButton variant="icon" />
            <Link
              to="/assistant"
              className="icon-button icon-button--subtle"
              title="Open full page"
              aria-label="Open full page"
            >
              <Maximize2 size={16} />
            </Link>
            <button
              type="button"
              className="icon-button icon-button--subtle"
              onClick={closePanel}
              title="Close"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </header>
          <ChatThread />
        </aside>
      )}
    </>
  );
}
