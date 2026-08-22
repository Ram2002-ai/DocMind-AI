import { ENDPOINTS } from "./endpoints";
import { parseSSEStream } from "./sse";
import type { Attachment, ChatMessage, StreamEvent, Thread } from "../types";

class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}

async function handleJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      message = body.detail || body.message || message;
    } catch {
      /* body wasn't JSON */
    }
    throw new ApiError(message, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async listThreads(): Promise<Thread[]> {
    const res = await fetch(ENDPOINTS.listThreads());
    return handleJson<Thread[]>(res);
  },

  async createThread(): Promise<Thread> {
    const res = await fetch(ENDPOINTS.createThread(), { method: "POST" });
    return handleJson<Thread>(res);
  },

  async deleteThread(threadId: string): Promise<void> {
    const res = await fetch(ENDPOINTS.deleteThread(threadId), { method: "DELETE" });
    if (!res.ok) throw new ApiError(`Failed to delete thread (${res.status})`, res.status);
  },

  async getMessages(threadId: string): Promise<ChatMessage[]> {
    const res = await fetch(ENDPOINTS.getMessages(threadId));
    return handleJson<ChatMessage[]>(res);
  },

  /** Upload one file (PDF, image, or text) with progress reporting via XHR. */
  uploadFile(
    threadId: string,
    file: File,
    onProgress: (pct: number) => void,
    signal?: AbortSignal
  ): Promise<Attachment> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", ENDPOINTS.uploadFile(threadId));

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch {
            reject(new ApiError("Malformed response from upload endpoint"));
          }
        } else {
          reject(new ApiError(`Upload failed (${xhr.status})`, xhr.status));
        }
      };
      xhr.onerror = () => reject(new ApiError("Network error during upload"));
      xhr.onabort = () => reject(new ApiError("Upload cancelled"));

      signal?.addEventListener("abort", () => xhr.abort());

      const form = new FormData();
      form.append("file", file);
      xhr.send(form);
    });
  },

  async deleteFile(threadId: string, fileId: string): Promise<void> {
    const res = await fetch(ENDPOINTS.deleteFile(threadId, fileId), { method: "DELETE" });
    if (!res.ok) throw new ApiError(`Failed to remove file (${res.status})`, res.status);
  },

  /** Streams the assistant's reply token-by-token via SSE. */
  async *streamChat(
    threadId: string,
    message: string,
    signal: AbortSignal
  ): AsyncGenerator<StreamEvent> {
    const res = await fetch(ENDPOINTS.chatStream(threadId), {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ message }),
      signal,
    });

    if (!res.ok || !res.body) {
      throw new ApiError(`Chat stream failed to open (${res.status})`, res.status);
    }

    yield* parseSSEStream(res, signal);
  },

  /** Non-streaming fallback used if the SSE connection can't be established. */
  async chatOnce(threadId: string, message: string): Promise<ChatMessage> {
    const res = await fetch(ENDPOINTS.chat(threadId), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    return handleJson<ChatMessage>(res);
  },
};

export { ApiError };
