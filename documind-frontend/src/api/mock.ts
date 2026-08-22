import type { Attachment, ChatMessage, StreamEvent, Thread } from "../types";

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
const uid = () => Math.random().toString(36).slice(2, 10);

let threads: Thread[] = [
  {
    id: "c39ecdac-aee8-4f5d-922f-72a75471d6d6",
    title: "Resume review",
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
    attachments: [
      {
        id: "f1",
        name: "Resume_2026.pdf",
        kind: "pdf",
        sizeBytes: 7700,
        status: "ready",
        chunks: 8,
        pages: 2,
      },
    ],
    messagePreview: "What recruiters look for in a CV engineer",
  },
];

const messagesByThread: Record<string, ChatMessage[]> = {
  "c39ecdac-aee8-4f5d-922f-72a75471d6d6": [
    {
      id: uid(),
      role: "user",
      content: "What should I highlight for a computer vision engineer role?",
      createdAt: new Date().toISOString(),
    },
  ],
};

const MOCK_REPLY = `Here's what stands out for a computer-vision engineering resume:

| Category | Why It Matters | How to Show It |
|---|---|---|
| Core CV Skills | Demonstrates you can build and deploy pipelines | List frameworks (PyTorch, OpenCV, YOLO) |
| Training & Optimization | Shows you can train or fine-tune | Mention dataset size, mAP, inference speed |
| Deployment | Recruiters want a full-stack engineer | Docker, ONNX, TensorRT, CI/CD |

Want me to rewrite your summary section using this framing?`;

export const mockApi = {
  async listThreads(): Promise<Thread[]> {
    await wait(300);
    return [...threads].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  },

  async createThread(): Promise<Thread> {
    await wait(200);
    const t: Thread = {
      id: crypto.randomUUID ? crypto.randomUUID() : uid(),
      title: "New chat",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      attachments: [],
    };
    threads.push(t);
    messagesByThread[t.id] = [];
    return t;
  },

  async deleteThread(threadId: string): Promise<void> {
    await wait(150);
    threads = threads.filter((t) => t.id !== threadId);
    delete messagesByThread[threadId];
  },

  async getMessages(threadId: string): Promise<ChatMessage[]> {
    await wait(250);
    return messagesByThread[threadId] ?? [];
  },

  async uploadFile(
    threadId: string,
    file: File,
    onProgress: (pct: number) => void,
    signal?: AbortSignal
  ): Promise<Attachment> {
    for (let pct = 0; pct <= 100; pct += 20) {
      if (signal?.aborted) throw new Error("Upload cancelled");
      await wait(120);
      onProgress(pct);
    }
    await wait(400); // server-side chunking/processing
    const kind: Attachment["kind"] = file.type.includes("pdf")
      ? "pdf"
      : file.type.startsWith("image/")
      ? "image"
      : "text";
    const attachment: Attachment = {
      id: uid(),
      name: file.name,
      kind,
      sizeBytes: file.size,
      status: "ready",
      chunks: kind === "pdf" ? Math.max(2, Math.round(file.size / 900)) : undefined,
      pages: kind === "pdf" ? Math.max(1, Math.round(file.size / 3500)) : undefined,
      previewUrl: kind === "image" ? URL.createObjectURL(file) : undefined,
    };
    const thread = threads.find((t) => t.id === threadId);
    if (thread) thread.attachments.push(attachment);
    return attachment;
  },

  async deleteFile(threadId: string, fileId: string): Promise<void> {
    await wait(150);
    const thread = threads.find((t) => t.id === threadId);
    if (thread) thread.attachments = thread.attachments.filter((a) => a.id !== fileId);
  },

  async *streamChat(
    threadId: string,
    message: string,
    signal: AbortSignal
  ): AsyncGenerator<StreamEvent> {
    messagesByThread[threadId] = messagesByThread[threadId] ?? [];
    messagesByThread[threadId].push({
      id: uid(),
      role: "user",
      content: message,
      createdAt: new Date().toISOString(),
    });

    yield { type: "message_start", data: {} };
    await wait(400);

    const words = MOCK_REPLY.split(" ");
    let acc = "";
    for (const word of words) {
      if (signal.aborted) return;
      acc += (acc ? " " : "") + word;
      await wait(25);
      yield { type: "token", data: { text: word + " " } };
    }

    messagesByThread[threadId].push({
      id: uid(),
      role: "assistant",
      content: acc,
      createdAt: new Date().toISOString(),
    });
    yield { type: "message_done", data: {} };
  },

  async chatOnce(threadId: string, _message: string): Promise<ChatMessage> {
    await wait(600);
    const reply: ChatMessage = {
      id: uid(),
      role: "assistant",
      content: MOCK_REPLY,
      createdAt: new Date().toISOString(),
    };
    messagesByThread[threadId] = messagesByThread[threadId] ?? [];
    messagesByThread[threadId].push(reply);
    return reply;
  },
};
