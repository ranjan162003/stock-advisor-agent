import { ArrowUp, Check, Copy, RotateCcw, Sparkles, Square } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";

import { useAssistant, type AssistantPageContext } from "../../context/AssistantContext";
import { useProviderConnections } from "../../context/ProviderConnectionsContext";
import { useToast } from "../../context/ToastContext";
import type { ChatMessage } from "../../types/chat.types";
import { Skeleton } from "../common/Skeleton";
import { ChatCards } from "./ChatCards";
import { ChatMarkdown } from "./ChatMarkdown";

/** Messages, the live in-progress turn, and the composer — shared by the side panel and the Ask AI page. */
export function ChatThread() {
  const { messages, liveTurn, error, send, stop, retry, isLoadingConversation, pageContext, takeQueuedQuestion } =
    useAssistant();
  const { activeStatus, activeModel } = useProviderConnections();
  const scrollRef = useRef<HTMLDivElement>(null);
  const isBusy = liveTurn !== null;

  // A question queued by "Ask about this" buttons is sent as soon as the thread is on screen.
  useEffect(() => {
    const queued = takeQueuedQuestion();
    if (queued) void send(queued);
  }, [takeQueuedQuestion, send]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, liveTurn, error]);

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");

  return (
    <div className="chat-thread">
      <div className="chat-thread__scroll" ref={scrollRef}>
        {isLoadingConversation ? (
          <div className="chat-thread__messages" role="status" aria-label="Loading chat">
            <div className="chat-bubble chat-bubble--user">
              <Skeleton width="55%" height={40} radius={16} />
            </div>
            <div className="chat-bubble chat-bubble--assistant">
              <Skeleton width={28} height={28} radius={14} />
              <div className="chat-bubble__body">
                <Skeleton height={90} radius={12} />
                <Skeleton width="90%" />
                <Skeleton width="75%" />
                <Skeleton width="60%" />
              </div>
            </div>
          </div>
        ) : messages.length === 0 && !isBusy ? (
          <ChatWelcome context={pageContext} onPick={(q) => void send(q)} />
        ) : (
          <div className="chat-thread__messages">
            {messages.map((message) => (
              <ChatBubble key={message.id} message={message} />
            ))}
            {liveTurn && (
              <div className="chat-bubble chat-bubble--assistant">
                <AssistantAvatar />
                <div className="chat-bubble__body">
                  <ChatCards cards={liveTurn.cards} />
                  <div className="chat-status" role="status">
                    <span className="chat-status__dots" aria-hidden="true">
                      <i />
                      <i />
                      <i />
                    </span>
                    {liveTurn.status}
                  </div>
                </div>
              </div>
            )}
            {error && (
              <div className="chat-error" role="alert">
                <span>{error}</span>
                <button type="button" className="button button--secondary button--small" onClick={retry}>
                  <RotateCcw size={14} /> Retry
                </button>
              </div>
            )}
            {!isBusy && !error && lastAssistant && lastAssistant === messages[messages.length - 1] && (
              <SuggestionChips suggestions={lastAssistant.suggestions} onPick={(q) => void send(q)} />
            )}
          </div>
        )}
      </div>

      <ChatComposer isBusy={isBusy} onSend={(text) => void send(text)} onStop={stop} />
      <p className="chat-thread__footnote">
        {activeStatus?.is_ready ? (
          <>
            Answering with {activeStatus.display_name} · {activeModel || activeStatus.default_model}. Educational only —
            not financial advice.
          </>
        ) : (
          <>
            No model connected — <Link to="/connectors">connect one</Link> to chat.
          </>
        )}
      </p>
    </div>
  );
}

export function ChatBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="chat-bubble chat-bubble--user">
        <div className="chat-bubble__body">{message.content}</div>
      </div>
    );
  }
  return (
    <div className="chat-bubble chat-bubble--assistant">
      <AssistantAvatar />
      <div className="chat-bubble__body">
        <ChatCards cards={message.cards} />
        <ChatMarkdown text={message.content} />
        <div className="chat-bubble__tools no-print">
          <CopyAnswerButton text={message.content} />
        </div>
      </div>
    </div>
  );
}

function CopyAnswerButton({ text }: { text: string }) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast({ message: "Answer copied" });
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      toast({ message: "Couldn't copy — your browser blocked clipboard access.", tone: "error" });
    }
  };

  return (
    <button type="button" className="chat-tool" onClick={() => void copy()} aria-label="Copy answer" title="Copy answer">
      {copied ? <Check size={14} /> : <Copy size={14} />}
      <span>{copied ? "Copied" : "Copy"}</span>
    </button>
  );
}

function AssistantAvatar() {
  return (
    <span className="chat-avatar" aria-hidden="true">
      <Sparkles size={14} />
    </span>
  );
}

function SuggestionChips({ suggestions, onPick }: { suggestions: string[]; onPick: (q: string) => void }) {
  if (suggestions.length === 0) return null;
  return (
    <div className="chat-suggestions" aria-label="Suggested follow-ups">
      {suggestions.map((s) => (
        <button key={s} type="button" className="chat-suggestion" onClick={() => onPick(s)}>
          {s}
        </button>
      ))}
    </div>
  );
}

const STARTERS: Record<string, string[]> = {
  result: [
    "Explain this recommendation in simple words",
    "What are the biggest risks in this portfolio?",
    "Why were these picks chosen over the others?",
  ],
  planner: [
    "What would ₹10,000 a month in Parag Parikh Flexi Cap be worth after 10 years?",
    "If I'd started a ₹5,000 SIP in a Nifty 50 index fund 5 years ago, what would I have now?",
    "What is XIRR and why does it differ from CAGR?",
  ],
  default: [
    "How has Parag Parikh Flexi Cap done?",
    "Compare HDFC Mid-Cap Opportunities with Kotak Emerging Equity",
    "What do TCS's numbers look like right now?",
    "What is a SIP step-up?",
  ],
};

function ChatWelcome({ context, onPick }: { context: AssistantPageContext; onPick: (q: string) => void }) {
  const starters = context.recommendationId ? STARTERS.result : (STARTERS[context.page] ?? STARTERS.default);
  return (
    <div className="chat-welcome">
      <span className="chat-welcome__orb" aria-hidden="true">
        <Sparkles size={22} />
      </span>
      <h2>Ask anything about your money</h2>
      <p className="muted">
        I can explain your recommendations, look up real fund and stock numbers, run SIP calculations and explain
        investing terms.
      </p>
      <div className="chat-welcome__starters">
        {starters.map((q) => (
          <button key={q} type="button" className="chat-starter" onClick={() => onPick(q)}>
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

function ChatComposer({
  isBusy,
  onSend,
  onStop,
}: {
  isBusy: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
}) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Grow with the text, up to a few lines.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }, [text]);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    if (isBusy || !text.trim()) return;
    onSend(text);
    setText("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) submit(event);
  };

  return (
    <form className="chat-composer" onSubmit={submit}>
      <textarea
        ref={inputRef}
        className="chat-composer__input"
        rows={1}
        maxLength={2000}
        placeholder="Ask about a fund, a stock, your SIP or your result…"
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
        aria-label="Message"
      />
      {isBusy ? (
        <button
          type="button"
          className="chat-composer__send chat-composer__send--stop"
          onClick={onStop}
          aria-label="Stop"
        >
          <Square size={14} />
        </button>
      ) : (
        <button type="submit" className="chat-composer__send" disabled={!text.trim()} aria-label="Send">
          <ArrowUp size={18} />
        </button>
      )}
    </form>
  );
}
