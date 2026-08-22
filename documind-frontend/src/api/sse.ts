import type { StreamEvent } from "../types";

/**
 * Reads a fetch() Response body as a Server-Sent-Events stream and yields
 * parsed events. Works with any backend that writes standard SSE frames:
 *
 *   event: token
 *   data: {"text": "hello"}
 *
 *   event: message_done
 *   data: {}
 *
 * If the backend only sends bare `data:` lines (no `event:` line), events
 * default to type "token".
 */
export async function* parseSSEStream(
  response: Response,
  signal?: AbortSignal
): AsyncGenerator<StreamEvent> {
  if (!response.body) throw new Error("Response has no body to stream");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (signal?.aborted) {
        await reader.cancel();
        return;
      }

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const event = parseFrame(frame);
        if (event) yield event;
      }
    }

    if (buffer.trim()) {
      const event = parseFrame(buffer);
      if (event) yield event;
    }
  } finally {
    reader.releaseLock();
  }
}

function parseFrame(frame: string): StreamEvent | null {
  let type: StreamEvent["type"] = "token";
  const dataLines: string[] = [];

  for (const rawLine of frame.split("\n")) {
    const line = rawLine.trim();
    if (!line || line.startsWith(":")) continue; // comment/heartbeat
    if (line.startsWith("event:")) {
      type = line.slice("event:".length).trim() as StreamEvent["type"];
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (dataLines.length === 0) return null;
  const raw = dataLines.join("\n");

  try {
    return { type, data: JSON.parse(raw) };
  } catch {
    // Non-JSON payload (plain token text) — wrap it.
    return { type, data: { text: raw } };
  }
}
