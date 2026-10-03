import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { chatApi } from "../api/chatApi";
import type { ChatCard, ChatConversationSummary, ChatMessage } from "../types/chat.types";
import { useProviderConnections } from "./ProviderConnectionsContext";

/** What the user is looking at, so "explain this" means something. */
export interface AssistantPageContext {
  page: string;
  recommendationId?: number | null;
}

/** The assistant's in-flight turn: live status line, cards that arrived so far. */
export interface LiveTurn {
  status: string;
  cards: ChatCard[];
}

interface AssistantValue {
  isPanelOpen: boolean;
  openPanel: (question?: string) => void;
  closePanel: () => void;

  pageContext: AssistantPageContext;
  setPageContext: (context: AssistantPageContext) => void;

  conversations: ChatConversationSummary[];
  refreshConversations: () => Promise<void>;
  activeConversationId: number | null;
  messages: ChatMessage[];
  isLoadingConversation: boolean;
  openConversation: (id: number) => Promise<void>;
  startNewChat: () => void;
  renameConversation: (id: number, title: string) => Promise<void>;
  deleteConversation: (id: number) => Promise<void>;

  liveTurn: LiveTurn | null;
  error: string | null;
  send: (text: string) => Promise<void>;
  stop: () => void;
  retry: () => void;
  /** A question queued by `openPanel(question)`; the thread sends it once mounted. */
  takeQueuedQuestion: () => string | null;
}

const AssistantContext = createContext<AssistantValue | null>(null);

const DEFAULT_CONTEXT: AssistantPageContext = { page: "advisor" };

/** One app-wide chat: the floating panel and the Ask AI page show the same conversation. */
export function AssistantProvider({ children }: { children: ReactNode }) {
  const { activeProviderId, activeModel } = useProviderConnections();
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [pageContext, setPageContextState] = useState<AssistantPageContext>(DEFAULT_CONTEXT);
  const [conversations, setConversations] = useState<ChatConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [liveTurn, setLiveTurn] = useState<LiveTurn | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const lastQuestionRef = useRef<string | null>(null);
  const queuedQuestionRef = useRef<string | null>(null);

  const setPageContext = useCallback((context: AssistantPageContext) => {
    setPageContextState((current) =>
      current.page === context.page && (current.recommendationId ?? null) === (context.recommendationId ?? null)
        ? current
        : context,
    );
  }, []);

  const refreshConversations = useCallback(async () => {
    try {
      setConversations(await chatApi.listConversations());
    } catch {
      // The list is a convenience; the chat itself still works.
    }
  }, []);

  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setLiveTurn(null);
  }, []);

  const openConversation = useCallback(
    async (id: number) => {
      stop();
      setError(null);
      setActiveConversationId(id);
      setIsLoadingConversation(true);
      try {
        const detail = await chatApi.getConversation(id);
        setMessages(detail.messages);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setMessages([]);
      } finally {
        setIsLoadingConversation(false);
      }
    },
    [stop],
  );

  const startNewChat = useCallback(() => {
    stop();
    setActiveConversationId(null);
    setMessages([]);
    setError(null);
  }, [stop]);

  const send = useCallback(
    async (rawText: string) => {
      const text = rawText.trim();
      if (!text || abortRef.current) return;
      setError(null);
      lastQuestionRef.current = text;
      const optimistic: ChatMessage = {
        id: -Date.now(),
        role: "user",
        content: text,
        cards: [],
        suggestions: [],
        created_at: new Date().toISOString(),
      };
      setMessages((current) => [...current, optimistic]);
      setLiveTurn({ status: "Sending…", cards: [] });
      const controller = new AbortController();
      abortRef.current = controller;

      const dropOptimistic = () => setMessages((current) => current.filter((m) => m.id !== optimistic.id));
      try {
        let conversationId = activeConversationId;
        if (conversationId === null) {
          conversationId = (await chatApi.createConversation()).id;
          setActiveConversationId(conversationId);
        }
        let finished = false;
        await chatApi.sendMessage(
          conversationId,
          {
            message: text,
            provider_id: activeProviderId,
            model_name: activeModel || null,
            page: pageContext.page,
            recommendation_id: pageContext.recommendationId ?? null,
          },
          (event) => {
            if (event.type === "status") {
              setLiveTurn((turn) => ({
                status: event.text,
                cards: turn?.cards ?? [],
              }));
            } else if (event.type === "card") {
              setLiveTurn((turn) => ({
                status: turn?.status ?? "",
                cards: [...(turn?.cards ?? []), event.card],
              }));
            } else if (event.type === "done") {
              finished = true;
              setMessages((current) => [
                ...current.filter((m) => m.id !== optimistic.id),
                event.user_message,
                event.assistant_message,
              ]);
              setConversations((current) => [
                event.conversation,
                ...current.filter((c) => c.id !== event.conversation.id),
              ]);
            } else if (event.type === "error") {
              finished = true;
              dropOptimistic();
              setError(event.message);
            }
          },
          controller.signal,
        );
        if (!finished) {
          dropOptimistic();
          setError("The answer was cut off. Please try again.");
        }
      } catch (e) {
        dropOptimistic();
        if (!controller.signal.aborted) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        setLiveTurn(null);
      }
    },
    [activeConversationId, activeProviderId, activeModel, pageContext],
  );

  const retry = useCallback(() => {
    if (lastQuestionRef.current) void send(lastQuestionRef.current);
  }, [send]);

  const renameConversation = useCallback(async (id: number, title: string) => {
    const updated = await chatApi.renameConversation(id, title);
    setConversations((current) => current.map((c) => (c.id === id ? updated : c)));
  }, []);

  const deleteConversation = useCallback(
    async (id: number) => {
      await chatApi.deleteConversation(id);
      setConversations((current) => current.filter((c) => c.id !== id));
      if (id === activeConversationId) startNewChat();
    },
    [activeConversationId, startNewChat],
  );

  const openPanel = useCallback((question?: string) => {
    if (question) queuedQuestionRef.current = question;
    setIsPanelOpen(true);
  }, []);

  const takeQueuedQuestion = useCallback(() => {
    const question = queuedQuestionRef.current;
    queuedQuestionRef.current = null;
    return question;
  }, []);

  const value = useMemo<AssistantValue>(
    () => ({
      isPanelOpen,
      openPanel,
      closePanel: () => setIsPanelOpen(false),
      pageContext,
      setPageContext,
      conversations,
      refreshConversations,
      activeConversationId,
      messages,
      isLoadingConversation,
      openConversation,
      startNewChat,
      renameConversation,
      deleteConversation,
      liveTurn,
      error,
      send,
      stop,
      retry,
      takeQueuedQuestion,
    }),
    [
      isPanelOpen,
      openPanel,
      pageContext,
      setPageContext,
      conversations,
      refreshConversations,
      activeConversationId,
      messages,
      isLoadingConversation,
      openConversation,
      startNewChat,
      renameConversation,
      deleteConversation,
      liveTurn,
      error,
      send,
      stop,
      retry,
      takeQueuedQuestion,
    ],
  );

  return <AssistantContext.Provider value={value}>{children}</AssistantContext.Provider>;
}

export function useAssistant(): AssistantValue {
  const value = useContext(AssistantContext);
  if (!value) throw new Error("useAssistant must be used inside <AssistantProvider>");
  return value;
}

/** Pages call this so the assistant knows where the user is (and which result "this" means). */
export function useAssistantPageContext(page: string, recommendationId?: number | null): void {
  const { setPageContext } = useAssistant();
  useEffect(() => {
    setPageContext({ page, recommendationId: recommendationId ?? null });
  }, [page, recommendationId, setPageContext]);
}
