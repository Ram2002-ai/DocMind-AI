import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";
import "./MessageList.css";

export function MessageList({ messages, loading, onPrompt }: { messages: ChatMessage[]; loading: boolean; onPrompt?: (prompt: string) => void }) {
  const endRef = useRef<HTMLDivElement>(null);
  const wasNearBottom = useRef(true);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (wasNearBottom.current) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages]);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    wasNearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  };

  if (loading) {
    return (
      <div className="message-list" ref={containerRef}>
        <div className="message-list-skeleton">
          <div className="skel-line skel-line-short" />
          <div className="skel-line" />
          <div className="skel-line skel-line-med" />
        </div>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="message-list message-list-empty">
        <div className="empty-state">
          <div className="empty-state-mark">✦</div>
          <div className="empty-state-eyebrow">DOCUMIND ASSISTANT</div>
          <h2>How can I help today?</h2>
          <p>Upload a document for grounded answers, or start a conversation with any question.</p>
          <div className="prompt-grid">
            {[
              "Summarize the key points of my document",
              "What are the important deadlines?",
              "Extract action items and next steps",
              "Explain this in simple language",
            ].map((prompt) => (
              <button key={prompt} type="button" className="prompt-card" onClick={() => onPrompt?.(prompt)}>
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list" ref={containerRef} onScroll={handleScroll}>
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
