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
  url?: string;
  description?: string;
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

// ── WebGraph & Interacción Bidireccional (Línea B) ──────────────────────────

export interface GraphNode {
  id: string;
  label: string;
  kind: "file" | "spec" | "adr" | "module";
  path: string;
  metadata?: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: "imports" | "documents" | "tests" | "depends_on";
}

export interface ProjectGraphPayload {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface NodeHighlightEvent {
  node_ids: string[];
  topic: string;
}

export interface PinnedContextNode {
  id: string;
  label: string;
  kind: "file" | "spec" | "adr" | "module";
  path: string;
}

// ── Gobernanza y Salud de Cortex (Línea B) ───────────────────────────────────

export interface SessionStatusPayload {
  active: boolean;
  session_id?: string;
  spec_path?: string;
  checkpoints_count: number;
  last_checkpoint?: string;
}

export interface DoctorCheck {
  name: string;
  status: "ok" | "warn" | "fail";
  message: string;
  auto_fix_tool?: string;
}

export interface DoctorReportPayload {
  is_healthy: boolean;
  checks: DoctorCheck[];
}

// ── Memoria Organizacional & Enterprise Vault ────────────────────────────────

export interface OrgKnowledgeItem {
  origin_id: string;
  rel_path: string;
  doc_type: string;
  title: string;
  status: string;
  priority: string;
  issues: string[];
  reviewer?: string | null;
  reason?: string | null;
  updated_at: string;
  is_promoted: boolean;
}

export interface OrgMemoryPayload {
  enterprise_vault_path: string;
  total_promoted: number;
  total_candidates: number;
  items: OrgKnowledgeItem[];
}
