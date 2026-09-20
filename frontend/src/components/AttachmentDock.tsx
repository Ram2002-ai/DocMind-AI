import type { Attachment } from "../types";
import { AttachmentChip } from "./AttachmentChip";
import "./AttachmentDock.css";

interface Props {
  attachments: Attachment[];
  pending: Attachment[];
  onRemove: (id: string) => void;
  onDismissPending: (id: string) => void;
}

export function AttachmentDock({ attachments, pending, onRemove, onDismissPending }: Props) {
  if (attachments.length === 0 && pending.length === 0) return null;

  return (
    <div className="attachment-dock">
      {attachments.map((a) => (
        <AttachmentChip key={a.id} attachment={a} onRemove={() => onRemove(a.id)} />
      ))}
      {pending.map((a) => (
        <AttachmentChip
          key={a.id}
          attachment={a}
          onRemove={a.status === "error" ? () => onDismissPending(a.id) : undefined}
        />
      ))}
    </div>
  );
}
