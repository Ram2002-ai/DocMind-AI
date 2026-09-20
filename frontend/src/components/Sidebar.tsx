import { Plus, Trash2, FileText, Image as ImageIcon, FileType } from "lucide-react";
import type { Thread } from "../types";
import { formatRelativeTime, shortId } from "../lib/format";
import "./Sidebar.css";

interface Props {
  threads: Thread[];
  activeThreadId: string | null;
  loading: boolean;
  error: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
}

const kindIcon = { pdf: FileText, image: ImageIcon, text: FileType, other: FileType } as const;

export function Sidebar({ threads, activeThreadId, loading, error, onSelect, onCreate, onDelete }: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark">DM</span>
        <div>
          <div className="sidebar-brand-title">DocuMind AI</div>
          <div className="sidebar-brand-sub">document intelligence</div>
        </div>
      </div>

      <button className="new-chat-btn" onClick={onCreate}>
        <Plus size={16} strokeWidth={2.25} />
        New chat
      </button>

      <div className="sidebar-section-label">Index</div>

      <div className="thread-list">
        {loading && <div className="sidebar-empty">Loading threads…</div>}
        {!loading && error && <div className="sidebar-empty sidebar-error">{error}</div>}
        {!loading && !error && threads.length === 0 && (
          <div className="sidebar-empty">No conversations yet. Start one above.</div>
        )}
        {threads.map((t) => {
          const primaryKind = t.attachments[0]?.kind ?? "other";
          const Icon = kindIcon[primaryKind];
          return (
            <div
              key={t.id}
              className={`thread-card ${t.id === activeThreadId ? "thread-card-active" : ""}`}
              onClick={() => onSelect(t.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && onSelect(t.id)}
            >
              <div className="thread-card-tab" aria-hidden />
              <div className="thread-card-body">
                <div className="thread-card-title">{t.title || "Untitled thread"}</div>
                {t.messagePreview && <div className="thread-card-preview">{t.messagePreview}</div>}
                <div className="thread-card-meta">
                  <span className="thread-card-callnum">{shortId(t.id)}</span>
                  <span className="thread-card-dot">·</span>
                  <span>{formatRelativeTime(t.updatedAt)}</span>
                  {t.attachments.length > 0 && (
                    <>
                      <span className="thread-card-dot">·</span>
                      <Icon size={12} />
                      <span>{t.attachments.length}</span>
                    </>
                  )}
                </div>
              </div>
              <button
                className="thread-card-delete"
                aria-label="Delete thread"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(t.id);
                }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
