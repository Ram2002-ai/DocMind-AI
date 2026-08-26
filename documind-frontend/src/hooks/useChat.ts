import { useCallback, useEffect, useRef, useState } from "react";
import { backend, ApiError } from "../api";
import type { ChatMessage } from "../types";

const uid = () => Math.random().toString(36).slice(2, 10);

export function useChat(threadId: string | null, onThreadTitle?: (title: string) => void) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load history whenever the active thread changes.
  useEffect(() => {
    if (!threadId) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    setLoadingHistory(true);
    setError(null);
    backend
      .getMessages(threadId)
      .then((history) => {
        if (!cancelled) setMessages(history);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof ApiError ? e.message : "Couldn't load this conversation.");
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });
    return () => {
      cancelled = true;
    };
  }, [threadId]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setSending(false);
  }, []);

  const send = useCallback(
    async (text: string) => {
      if (!threadId || !text.trim()) return;
      setError(null);

      const userMsg: ChatMessage = {
        id: uid(),
        role: "user",
        content: text,
        createdAt: new Date().toISOString(),
      };
      const assistantId = uid();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        streaming: true,
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setSending(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        for await (const event of backend.streamChat(threadId, text, controller.signal)) {
          if (event.type === "token") {
            const chunk = event.data?.text ?? "";
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + chunk } : m))
            );
          } else if (event.type === "tool_call") {
            // The agent emits one event when a tool starts (status: "running")
            // and another when it finishes (status: "done") for the SAME id —
            // update that entry in place instead of appending a duplicate row.
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== assistantId) return m;
                const existing = m.toolCalls ?? [];
                const idx = existing.findIndex((tc) => tc.id === event.data?.id);
                const toolCalls =
                  idx === -1
                    ? [...existing, event.data]
                    : existing.map((tc, i) => (i === idx ? { ...tc, ...event.data } : tc));
                return { ...m, toolCalls };
              })
            );
          } else if (event.type === "thread_title") {
            const title = typeof event.data?.title === "string" ? event.data.title : "";
            if (title) onThreadTitle?.(title);
          } else if (event.type === "error") {
            throw new Error(event.data?.message || "The model returned an error.");
          }
        }
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, streaming: false } : m))
        );
      } catch (e) {
        if (controller.signal.aborted) {
          setMessages((prev) =>
            prev.map((m) => (m.id === assistantId ? { ...m, streaming: false } : m))
          );
        } else {
          const message = e instanceof Error ? e.message : "Streaming failed. Trying once more…";
          // Fall back to non-streaming call so a transient stream failure
          // doesn't lose the response entirely.
          try {
            const reply = await backend.chatOnce(threadId, text);
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...reply, streaming: false } : m))
            );
          } catch {
            setError(message);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, streaming: false, error: message } : m
              )
            );
          }
        }
      } finally {
        setSending(false);
        abortRef.current = null;
      }
    },
    [threadId, onThreadTitle]
  );

  return { messages, loadingHistory, sending, error, send, stop };
}
