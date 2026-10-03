import { FileDown } from "lucide-react";

import { useAssistant } from "../../context/AssistantContext";
import { slugify, usePrint } from "../../context/PrintContext";
import { formatDateTime } from "../../utils/displayFormatters";
import { PrintableDocument } from "../common/PrintableDocument";
import { ChatBubble } from "./ChatThread";

/** Saves the open chat — answers, cards and charts — as a PDF. */
export function ExportChatButton({ variant }: { variant: "icon" | "button" }) {
  const { messages, conversations, activeConversationId, liveTurn } = useAssistant();
  const print = usePrint();
  const saved = messages.filter((m) => m.id > 0);
  const title = conversations.find((c) => c.id === activeConversationId)?.title ?? "Ask AI chat";
  const disabled = saved.length === 0 || liveTurn !== null;

  const exportPdf = () =>
    print({
      fileName: `stock-advisor-chat-${slugify(title)}`,
      content: (
        <PrintableDocument
          title={title}
          subtitle={`Ask AI conversation · ${saved.length} messages · ${formatDateTime(saved[0].created_at)}`}
        >
          <div className="chat-thread__messages">
            {saved.map((message) => (
              <ChatBubble key={message.id} message={message} />
            ))}
          </div>
        </PrintableDocument>
      ),
    });

  if (variant === "icon") {
    return (
      <button
        type="button"
        className="icon-button icon-button--subtle"
        onClick={exportPdf}
        disabled={disabled}
        title="Download chat as PDF"
        aria-label="Download chat as PDF"
      >
        <FileDown size={16} />
      </button>
    );
  }
  return (
    <button type="button" className="button button--secondary button--block" onClick={exportPdf} disabled={disabled}>
      <FileDown size={16} /> Download chat as PDF
    </button>
  );
}
