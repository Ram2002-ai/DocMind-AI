# DocuMind AI — Frontend

A production-grade React + TypeScript + Vite chat UI for a document-intelligence
assistant: upload PDFs, images, or text; ask questions; get streamed answers;
manage multiple threads.

## Quick start

```bash
npm install
cp .env.example .env
npm run dev
```

By default `.env` has `VITE_USE_MOCK_API=true`, so the app runs standalone
with a realistic mock backend — no server required. Open it, create a thread,
drop in a file, and chat to see the whole flow (streaming, upload progress,
thread switching) working end to end.

## Wiring up your real backend (`E:\New folder\DocuMind-AI-main`)

1. Set `VITE_USE_MOCK_API=false` and `VITE_API_BASE_URL` to your server, e.g.
   `http://localhost:8000`, in `.env`.
2. Every route the frontend calls lives in **one file**:
   `src/api/endpoints.ts`. If your backend's paths differ from the defaults
   below, change them there only — nothing else references a URL directly.
3. Match the request/response shapes below (or adjust `src/api/client.ts` to
   transform your backend's actual shapes — it's the only file that touches
   `fetch`/`XMLHttpRequest`).

### Expected API contract

| Purpose | Method & Path | Notes |
|---|---|---|
| List threads | `GET /api/threads` | Returns `Thread[]` |
| Create thread | `POST /api/threads` | Returns a new `Thread` |
| Delete thread | `DELETE /api/threads/:id` | |
| Get history | `GET /api/threads/:id/messages` | Returns `ChatMessage[]` |
| Upload file | `POST /api/threads/:id/files` (multipart, field `file`) | Returns an `Attachment`. One request per file — the UI already loops over multi-file selections/drops. |
| Delete file | `DELETE /api/threads/:id/files/:fileId` | |
| Streamed chat | `POST /api/threads/:id/chat/stream` (SSE) | Body `{ "message": string }`. Response `Content-Type: text/event-stream`. See event format below. |
| Non-streaming chat | `POST /api/threads/:id/chat` | Fallback used automatically if the SSE connection fails to open. Body `{ "message": string }`, returns one `ChatMessage`. |

### SSE event format (streamed chat)

Standard SSE frames, one event per model token (or larger chunks — either
works):

```
event: token
data: {"text": "Hello"}

event: token
data: {"text": " there"}

event: tool_call
data: {"id": "t1", "name": "search_docs", "status": "running"}

event: message_done
data: {}
```

If your backend can't easily emit named `event:` lines, bare `data:` lines
are treated as `token` events automatically — see `src/api/sse.ts`.

### Types

All shared shapes are in `src/types.ts` (`Thread`, `ChatMessage`, `Attachment`,
`ToolCall`, `StreamEvent`) — align your backend's JSON to these, or adapt
`src/api/client.ts` to map between them.

## Architecture

```
src/
  api/
    endpoints.ts   — all backend URLs (edit this to match your server)
    client.ts      — real fetch/XHR/SSE implementation
    mock.ts        — in-memory mock with the same interface, for local dev
    sse.ts         — SSE stream parser
    index.ts       — picks real vs. mock based on VITE_USE_MOCK_API
  hooks/
    useThreads.ts    — thread list, create/delete, optimistic updates
    useChat.ts       — streaming send/stop, history load, fallback-on-error
    useFileUpload.ts — multi-file upload with per-file progress
  components/        — presentational UI (Sidebar, Composer, MessageList, ...)
  types.ts
```

Because `backend` (in `src/api/index.ts`) is the only thing components and
hooks talk to, and it has an identical interface in both real and mock form,
you can develop the whole UI without a backend, then flip one env var to go
live.

## Production build

```bash
npm run build   # outputs to dist/
npm run preview # serve the production build locally
```

`dist/` is a static bundle — serve it from any static host, or from your
backend itself (FastAPI's `StaticFiles`, Nginx, etc.).

## Notes on the pieces called for in the brief

- **Images, text, and PDFs**: `Composer`'s attach button and drag-and-drop
  both accept `.pdf, .png, .jpg, .jpeg, .webp, .gif, .txt, .md, .csv`
  (edit `ACCEPTED` in `useFileUpload.ts` to change).
- **Streaming**: `useChat` consumes the SSE stream token-by-token and falls
  back to a single non-streaming request if the stream can't open, so a
  flaky connection doesn't lose the response.
- **Threading**: the sidebar lists/creates/deletes threads; switching threads
  reloads that thread's history and attachments independently.
- **Persistence**: all state (threads, messages, attachments) is fetched
  from and written to the backend — the frontend holds no source of truth
  beyond a local optimistic cache that reconciles with server responses.
