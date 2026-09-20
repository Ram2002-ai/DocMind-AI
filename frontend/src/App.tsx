import { useCallback, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { MessageList } from "./components/MessageList";
import { Composer } from "./components/Composer";
import { AttachmentDock } from "./components/AttachmentDock";
import { ErrorBanner } from "./components/ErrorBanner";
import { useThreads } from "./hooks/useThreads";
import { useChat } from "./hooks/useChat";
import { useFileUpload } from "./hooks/useFileUpload";
import { backend } from "./api";
import type { Attachment } from "./types";
import "./App.css";

const isMock = import.meta.env.VITE_USE_MOCK_API === "true";

export default function App() {
  const {
    threads,
    activeThreadId,
    setActiveThreadId,
    loading: threadsLoading,
    error: threadsError,
    createThread,
    deleteThread,
    touchThread,
  } = useThreads();

  const handleThreadTitle = useCallback(
    (title: string) => {
      if (activeThreadId) touchThread(activeThreadId, { title });
    },
    [activeThreadId, touchThread]
  );
  const { messages, loadingHistory, sending, error: chatError, send, stop } = useChat(activeThreadId, handleThreadTitle);

  const [localError, setLocalError] = useState<string | null>(null);
  const activeThread = threads.find((t) => t.id === activeThreadId) ?? null;

  const handleUploaded = useCallback(
    (attachment: Attachment) => {
      if (!activeThreadId) return;
      const current = threads.find((t) => t.id === activeThreadId);
      touchThread(activeThreadId, {
        attachments: [...(current?.attachments ?? []), attachment],
      });
    },
    [activeThreadId, threads, touchThread]
  );

  const { pending, upload, dismiss, error: uploadError, ACCEPTED } = useFileUpload(
    activeThreadId,
    handleUploaded
  );

  const handleNewChat = async () => {
    await createThread();
  };

  const handleRemoveAttachment = async (fileId: string) => {
    if (!activeThreadId || !activeThread) return;
    const rollback = activeThread.attachments;
    touchThread(activeThreadId, {
      attachments: activeThread.attachments.filter((a) => a.id !== fileId),
    });
    try {
      await backend.deleteFile(activeThreadId, fileId);
    } catch {
      touchThread(activeThreadId, { attachments: rollback });
      setLocalError("Couldn't remove that file — it may still be attached on the server.");
    }
  };

  const activeError = localError || threadsError || chatError || uploadError;

  return (
    <div className="app-shell">
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        loading={threadsLoading}
        error={null}
        onSelect={setActiveThreadId}
        onCreate={handleNewChat}
        onDelete={deleteThread}
      />

      <main className="app-main">
        <TopBar thread={activeThread} live={!isMock} />

        {activeThread ? (
          <>
            <MessageList messages={messages} loading={loadingHistory} onPrompt={send} />

            {activeError && <ErrorBanner message={activeError} onDismiss={() => setLocalError(null)} />}

            <AttachmentDock
              attachments={activeThread.attachments}
              pending={pending}
              onRemove={handleRemoveAttachment}
              onDismissPending={dismiss}
            />

            <div className="composer-wrap">
              <Composer
                disabled={!activeThreadId}
                sending={sending}
                onSend={send}
                onStop={stop}
                onFiles={upload}
                accept={ACCEPTED}
                focusKey={activeThreadId}
              />
              <div className="composer-hint">
                Enter to send · Shift + Enter for a new line · PDF, image, or text files up to 25MB
              </div>
            </div>
          </>
        ) : (
          <div className="app-main-empty">
            {activeError ? (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                <ErrorBanner message={activeError} onDismiss={() => setLocalError(null)} />
                <button className="new-chat-btn" style={{ margin: 0 }} onClick={handleNewChat}>
                  Retry
                </button>
              </div>
            ) : threadsLoading ? (
              "Loading…"
            ) : (
              "Select or start a conversation to begin."
            )}
          </div>
        )}
      </main>
    </div>
  );
}
