import { FileText, Image as ImageIcon, FileType, X, AlertTriangle, Loader2 } from "lucide-react";
import type { Attachment } from "../types";
import { formatBytes } from "../lib/format";
import "./AttachmentChip.css";

const kindIcon = { pdf: FileText, image: ImageIcon, text: FileType, other: FileType } as const;

interface Props {
  attachment: Attachment;
  compact?: boolean;
  onRemove?: () => void;
}

export function AttachmentChip({ attachment, compact, onRemove }: Props) {
  const Icon = kindIcon[attachment.kind];
  const isBusy = attachment.status === "uploading" || attachment.status === "processing";
  const isError = attachment.status === "error";

  return (
    <div className={`chip ${compact ? "chip-compact" : ""} ${isError ? "chip-error" : ""}`}>
      {attachment.kind === "image" && attachment.previewUrl ? (
        <img src={attachment.previewUrl} alt="" className="chip-thumb" />
      ) : isBusy ? (
        <Loader2 size={14} className="chip-spin" />
      ) : isError ? (
        <AlertTriangle size={14} />
      ) : (
        <Icon size={14} />
      )}

      <div className="chip-body">
        <div className="chip-name" title={attachment.name}>
          {attachment.name}
        </div>
        <div className="chip-meta">
          {isError
            ? attachment.errorMessage || "Failed"
            : attachment.status === "uploading"
            ? `Uploading ${attachment.progress ?? 0}%`
            : attachment.status === "processing"
            ? "Processing…"
            : attachment.kind === "pdf" && attachment.chunks
            ? `${attachment.chunks} chunks · ${attachment.pages} pages`
            : formatBytes(attachment.sizeBytes)}
        </div>
        {isBusy && (
          <div className="chip-progress-track">
            <div
              className="chip-progress-fill"
              style={{ width: `${attachment.status === "processing" ? 100 : attachment.progress ?? 0}%` }}
            />
          </div>
        )}
      </div>

      {onRemove && (
        <button className="chip-remove" onClick={onRemove} aria-label={`Remove ${attachment.name}`}>
          <X size={12} />
        </button>
      )}
    </div>
  );
}
