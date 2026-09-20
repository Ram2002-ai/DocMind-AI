export type Role = "user" | "assistant" | "tool" | "system";

export interface Attachment {
  id: string;
  name: string;
  kind: "pdf" | "image" | "text" | "other";
  sizeBytes: number;
  status: "uploading" | "processing" | "ready" | "error";
  progress?: number; // 0-100, upload progress
  chunks?: number;
  pages?: number;
  errorMessage?: string;
  previewUrl?: string; // for images
}

export interface ToolCall {
  id: string;
  name: string;
  input?: Record<string, unknown>;
  status: "running" | "done" | "error";
  output?: string;
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  createdAt: string;
  attachments?: Attachment[];
  toolCalls?: ToolCall[];
  streaming?: boolean;
  error?: string;
}

export interface Thread {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  attachments: Attachment[];
  messagePreview?: string;
}

export interface StreamEvent {
  type: "token" | "tool_call" | "tool_result" | "message_start" | "message_done" | "thread_title" | "error";
  data: any;
}
