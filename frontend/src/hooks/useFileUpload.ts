import { useCallback, useState } from "react";
import { backend, ApiError } from "../api";
import type { Attachment } from "../types";

const uid = () => Math.random().toString(36).slice(2, 10);

const ACCEPTED = [".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".txt", ".md", ".csv"];
const MAX_SIZE_BYTES = 25 * 1024 * 1024; // 25MB

function kindFor(file: File): Attachment["kind"] {
  if (file.type.includes("pdf")) return "pdf";
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("text/") || file.name.match(/\.(txt|md|csv)$/i)) return "text";
  if (file.name.match(/\.docx$/i)) return "text";
  return "other";
}

export function useFileUpload(threadId: string | null, onUploaded: (a: Attachment) => void) {
  const [pending, setPending] = useState<Record<string, Attachment>>({});
  const [error, setError] = useState<string | null>(null);

  const upload = useCallback(
    async (files: FileList | File[]) => {
      if (!threadId) return;
      setError(null);
      const list = Array.from(files);

      for (const file of list) {
        if (file.size > MAX_SIZE_BYTES) {
          setError(`${file.name} is over the 25MB limit.`);
          continue;
        }
        const localId = uid();
        const optimistic: Attachment = {
          id: localId,
          name: file.name,
          kind: kindFor(file),
          sizeBytes: file.size,
          status: "uploading",
          progress: 0,
        };
        setPending((prev) => ({ ...prev, [localId]: optimistic }));

        const controller = new AbortController();
        try {
          const result = await backend.uploadFile(
            threadId,
            file,
            (pct) =>
              setPending((prev) => ({
                ...prev,
                [localId]: { ...prev[localId], progress: pct, status: pct < 100 ? "uploading" : "processing" },
              })),
            controller.signal
          );
          setPending((prev) => {
            const next = { ...prev };
            delete next[localId];
            return next;
          });
          onUploaded({ ...result, status: "ready" });
        } catch (e) {
          const message = e instanceof ApiError ? e.message : "Upload failed.";
          setPending((prev) => ({
            ...prev,
            [localId]: { ...prev[localId], status: "error", errorMessage: message },
          }));
        }
      }
    },
    [threadId, onUploaded]
  );

  const dismiss = useCallback((localId: string) => {
    setPending((prev) => {
      const next = { ...prev };
      delete next[localId];
      return next;
    });
  }, []);

  return { pending: Object.values(pending), upload, dismiss, error, ACCEPTED };
}
