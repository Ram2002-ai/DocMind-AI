import { useCallback, useEffect, useState } from "react";
import { backend, ApiError } from "../api";
import type { Thread } from "../types";

export function useThreads() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await backend.listThreads();
      if (list.length === 0) {
        // Land the user directly in a composer instead of an empty
        // "select a conversation" placeholder, mirroring the New Chat flow.
        const created = await backend.createThread();
        setThreads([created]);
        setActiveThreadId(created.id);
      } else {
        setThreads(list);
        setActiveThreadId((current) => current ?? list[0]?.id ?? null);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't reach the backend.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const createThread = useCallback(async () => {
    setError(null);
    try {
      const t = await backend.createThread();
      setThreads((prev) => [t, ...prev]);
      setActiveThreadId(t.id);
      return t;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't start a new chat.");
      return null;
    }
  }, []);

  const deleteThread = useCallback(
    async (id: string) => {
      const prevThreads = threads;
      const wasLastThread = prevThreads.length === 1 && prevThreads[0]?.id === id;
      setThreads((prev) => prev.filter((t) => t.id !== id));
      if (activeThreadId === id) {
        const next = prevThreads.find((t) => t.id !== id);
        setActiveThreadId(next?.id ?? null);
      }
      try {
        await backend.deleteThread(id);
        if (wasLastThread) {
          // Never leave the user with zero threads and no composer visible.
          const created = await backend.createThread();
          setThreads([created]);
          setActiveThreadId(created.id);
        }
      } catch (e) {
        setThreads(prevThreads); // roll back on failure
        setError(e instanceof ApiError ? e.message : "Couldn't delete that thread.");
      }
    },
    [threads, activeThreadId]
  );

  const touchThread = useCallback((id: string, patch: Partial<Thread>) => {
    setThreads((prev) =>
      prev
        .map((t) => (t.id === id ? { ...t, ...patch, updatedAt: new Date().toISOString() } : t))
        .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    );
  }, []);

  return {
    threads,
    activeThreadId,
    setActiveThreadId,
    loading,
    error,
    createThread,
    deleteThread,
    touchThread,
    refresh,
  };
}
