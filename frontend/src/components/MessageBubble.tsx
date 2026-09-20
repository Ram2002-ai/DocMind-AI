import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Wrench, AlertCircle } from "lucide-react";
import type { ChatMessage } from "../types";
import { AttachmentChip } from "./AttachmentChip";
import "./MessageBubble.css";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`msg-row ${isUser ? "msg-row-user" : "msg-row-assistant"}`}>
      <div className={`msg-avatar ${isUser ? "msg-avatar-user" : "msg-avatar-assistant"}`}>
        {isUser ? "U" : "DM"}
      </div>
      <div className="msg-content">
        {message.attachments && message.attachments.length > 0 && (
          <div className="msg-attachments">
            {message.attachments.map((a) => (
              <AttachmentChip key={a.id} attachment={a} compact />
            ))}
          </div>
        )}

        {message.toolCalls?.map((tc) => (
          <div key={tc.id} className="msg-tool-call">
            <Wrench size={12} />
            <span className="msg-tool-name">{tc.name}</span>
            <span className={`msg-tool-status msg-tool-status-${tc.status}`}>{tc.status}</span>
          </div>
        ))}

        <div className={`msg-bubble ${isUser ? "msg-bubble-user" : "msg-bubble-assistant"}`}>
          {message.content ? (
            <div className="msg-markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          ) : message.streaming ? (
            <span className="msg-typing" aria-label="Assistant is typing">
              <span />
              <span />
              <span />
            </span>
          ) : null}
          {message.streaming && message.content && <span className="msg-cursor" aria-hidden />}
        </div>

        {message.error && (
          <div className="msg-error">
            <AlertCircle size={13} />
            {message.error}
          </div>
        )}
      </div>
    </div>
  );
}
