/**
 * Single source of truth for backend routes.
 *
 * If your real DocuMind AI backend uses different paths, change them ONLY
 * here — nothing else in the app should hardcode a URL.
 */
export const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const ENDPOINTS = {
  // Threads
  listThreads: () => `${BASE_URL}/api/threads`,
  createThread: () => `${BASE_URL}/api/threads`,
  getThread: (threadId: string) => `${BASE_URL}/api/threads/${threadId}`,
  deleteThread: (threadId: string) => `${BASE_URL}/api/threads/${threadId}`,
  getMessages: (threadId: string) => `${BASE_URL}/api/threads/${threadId}/messages`,

  // Files (PDF / image / text)
  uploadFile: (threadId: string) => `${BASE_URL}/api/threads/${threadId}/files`,
  deleteFile: (threadId: string, fileId: string) =>
    `${BASE_URL}/api/threads/${threadId}/files/${fileId}`,

  // Chat — streamed via Server-Sent Events (text/event-stream) over POST.
  chatStream: (threadId: string) => `${BASE_URL}/api/threads/${threadId}/chat/stream`,

  // Non-streaming fallback, used automatically if the stream fails to open.
  chat: (threadId: string) => `${BASE_URL}/api/threads/${threadId}/chat`,
};
