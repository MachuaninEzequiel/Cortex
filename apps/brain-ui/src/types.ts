/**
 * Tipos canónicos para Cortex Brain UI (Obra 20, G-A7 / G-A8).
 * Espejo de los tipos en Rust (`cortex-brain-app`).
 */

export interface ProjectEntry {
  path: string;
  branch: string;
  has_session: boolean;
  valid_config: boolean;
  last_scan: number;
}

export interface ToolCall {
  tool: string;
  args: string;
}

export interface ChatTurn {
  text: string;
  tool_calls: ToolCall[];
  backend: string;
}

export interface ModelEntry {
  name: string;
  filename: string;
  path: string;
  exists: boolean;
  active: boolean;
  size_bytes?: number;
}

export interface ChatChunkPayload {
  request_id: string;
  chunk: string;
}

export interface DownloadProgressPayload {
  bytes_done: number;
  bytes_total?: number;
  percentage?: number;
  status: "downloading" | "done" | "error";
  error?: string;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "brain";
  text: string;
  timestamp: number;
  tool_calls?: ToolCall[];
  backend?: string;
  isStreaming?: boolean;
}

export type MarkRamState = "idle" | "weak_awake" | "awake";

export type Lang = "es" | "en";
