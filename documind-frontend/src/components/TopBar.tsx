import { useEffect, useState } from "react";
import type { Thread } from "../types";
import { shortId } from "../lib/format";
import { BASE_URL } from "../api/endpoints";
import "./TopBar.css";

type Status = "checking" | "online" | "offline";

export function TopBar({ thread, live }: { thread: Thread | null; live: boolean }) {
  const [status, setStatus] = useState<Status>(live ? "checking" : "online");

  useEffect(() => {
    if (!live) return;
    let cancelled = false;
    const check = () => {
      fetch(`${BASE_URL}/health`)
        .then((res) => {
          if (!cancelled) setStatus(res.ok ? "online" : "offline");
        })
        .catch(() => {
          if (!cancelled) setStatus("offline");
        });
    };
    check();
    const interval = setInterval(check, 8000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [live]);

  const label = !live ? "Demo mode" : status === "checking" ? "Checking…" : status === "online" ? "Connected" : "Backend unreachable";

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="topbar-title">{thread ? thread.title || "Untitled thread" : "DocuMind AI"}</div>
        {thread && <div className="topbar-id">thread {shortId(thread.id, 12)}</div>}
      </div>
      <div className="topbar-right">
        <span className={`status-dot ${!live ? "status-mock" : status === "online" ? "status-live" : status === "offline" ? "status-offline" : "status-mock"}`} />
        {label}
      </div>
    </header>
  );
}
