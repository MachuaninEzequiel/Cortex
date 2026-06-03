/**
 * cortex-net — Cortex peer-to-peer agent communication
 *
 * Inspirado en disler/pi-vs-claude-code (coms / coms-net), adaptado al
 * modelo de gobernanza de Cortex Release 2.5 (Pluggable Middle Fase 09.A+).
 *
 * Diferencias clave con coms/coms-net original:
 *
 *   1. Cada agente se identifica por su ROL canónico (designer, explorer,
 *      implementer, security, test-verifier, sddwork, documenter), no por
 *      un ID random. Esto permite que el documenter sepa a quién preguntar
 *      sin tener que mantener un directorio aparte.
 *
 *   2. Todo mensaje lleva el `session_id` de la Cortex Session activa. Dos
 *      agentes con session_id distinto NO pueden hablarse — el server
 *      rechaza el mensaje. Esto previene cross-talk entre sesiones
 *      paralelas en el mismo proyecto.
 *
 *   3. El contrato real (artefactos, decisiones) sigue viviendo en el
 *      backend Cortex via `cortex_session_checkpoint`. cortex-net solo
 *      mueve SEÑALES de coordinación: preguntas, propuestas, bloqueos,
 *      handoffs. Los mensajes son CORTOS por diseño.
 *
 *   4. Auto-reply implícita: el output del próximo turn del receptor se
 *      empaqueta como respuesta al msg_id en espera (mismo patrón que
 *      disler). Previene loops A→B→A por construcción.
 *
 *   5. Audit log per-sesión que NUNCA guarda el cuerpo del prompt, solo
 *      msg_id + sender_role + recipient_role + timestamp + session_id.
 *
 * Tools registradas:
 *   - cortex_net_list        : agentes peers visibles en la red
 *   - cortex_net_send        : enviar un mensaje a otro rol
 *   - cortex_net_get         : leer respuesta (non-blocking)
 *   - cortex_net_await       : leer respuesta (bloqueante con timeout)
 *   - cortex_net_transcript  : lee el transcript completo de la sesión
 *                              (uso primario: documenter al cierre)
 *
 * Tipos de mensaje (semántica):
 *   - "question"  : pido aclaración a un peer durante mi turno
 *   - "proposal"  : propongo algo, espero accept/reject
 *   - "blocker"   : informo un bloqueo (no espera respuesta)
 *   - "handoff"   : delego turno explícitamente (Deep Track)
 *   - "observe"   : me suscribo silencioso (documenter usa esto)
 *
 * Uso: pi -e .pi/extensions/cortex-net.ts
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Text } from "@mariozechner/pi-tui";
import { Type } from "@sinclair/typebox";
import {
  appendFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from "fs";
import { dirname, join } from "path";
import { createServer, createConnection, Server, Socket } from "net";
import { randomBytes } from "crypto";
// F1 del overhaul UX: cortex-net escribe su estado al singleton para que
// cortex-cockpit y otras extensiones lo lean sin abrir socket al hub.
// Bugfix mayo 2026: import desde .pi/lib/ para evitar doble instancia
// del singleton (ver docs/.../PI-COCKPIT-UX/README.md § 8).
import {
  cortexState,
  subscribe as subscribeCortexState,
  update as updateCortexState,
  registerNetActions,
  type PeerSnapshot,
} from "../lib/cortex-state";

// ── Constants ──────────────────────────────────────────────────────────────

/**
 * Roles canónicos en el ecosistema Cortex.
 * Si un agente NO tiene uno de estos roles, NO entra a cortex-net.
 * Sync queda explícitamente AFUERA — es secuencial pre-net (B' design).
 */
const CORTEX_ROLES = [
  "sddwork",
  "designer",
  "explorer",
  "implementer",
  "security",
  "test-verifier",
  "documenter",
] as const;

type CortexRole = (typeof CORTEX_ROLES)[number];

const MSG_TYPES = ["question", "proposal", "blocker", "handoff", "observe"] as const;
type MsgType = (typeof MSG_TYPES)[number];

// Heartbeat / self-heal
const HEARTBEAT_MS = 5_000;
const STALE_AFTER_MS = 15_000;

// ── Types ──────────────────────────────────────────────────────────────────

/**
 * Estado actual de un peer en la red.
 *
 *   idle     : no está en mitad de un turn; disponible para inbounds.
 *   busy     : está en mitad de un turn (agent generando, tool en ejecución).
 *   observe  : se suscribe silencioso (documenter en modo observer in-flight).
 *
 * F3 introduce este campo. Antes de F3 el campo no existía y el cockpit
 * mostraba "?" como status. Compatibilidad hacia atrás: peers que no
 * mandan status en register se asumen "idle".
 */
type PeerStatus = "idle" | "busy" | "observe";

interface Peer {
  role: CortexRole;
  pid: number;
  session_id: string;
  model: string;
  last_heartbeat: number;
  socket_path: string;
  status: PeerStatus;
}

interface NetMessage {
  kind:
    | "send"
    | "reply"
    | "heartbeat"
    | "register"
    | "unregister"
    | "list"
    | "broadcast"     // F3: fanout a todos los peers de la sesión
    | "peer_event";   // F3: notificación push del hub (joined/left/status)
  msg_id?: string;
  from_role: CortexRole;
  to_role?: CortexRole;
  session_id: string;
  msg_type?: MsgType;
  body?: string;
  reply_to_msg_id?: string;
  // Solo para register / heartbeat (F3 agrega status)
  pid?: number;
  model?: string;
  socket_path?: string;
  status?: PeerStatus;
  // Solo para peer_event (F3)
  event_op?: "joined" | "left" | "status_changed";
  event_role?: CortexRole;
  event_status?: PeerStatus;
}

interface PendingReply {
  resolve: (body: string) => void;
  timer: NodeJS.Timeout;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function newMsgId(): string {
  return randomBytes(8).toString("hex").toUpperCase();
}

function workspaceRoot(cwd: string): string {
  return cwd;
}

function netDir(cwd: string): string {
  return join(workspaceRoot(cwd), ".pi", "agent-sessions");
}

/**
 * Bugfix mayo 2026: hash corto del cwd para nombrar pipes únicos por
 * workspace. Necesario en Windows porque los Named Pipes viven en un
 * namespace global del sistema (no por filesystem), así que distintos
 * proyectos Cortex en la misma máquina necesitan nombres distintos.
 */
function workspaceHash(cwd: string): string {
  // Hash determinístico djb2 — chico y rápido. No criptográfico
  // pero alcanza para diferenciar workspaces (~8 chars hex).
  let h = 5381;
  for (let i = 0; i < cwd.length; i++) {
    h = ((h << 5) + h + cwd.charCodeAt(i)) | 0;
  }
  return (h >>> 0).toString(16).padStart(8, "0");
}

const IS_WINDOWS = process.platform === "win32";

/**
 * Path del socket/pipe del hub.
 *
 * En Linux/macOS: archivo Unix domain socket bajo .pi/agent-sessions/.
 * En Windows: Named Pipe en el namespace ``\\.\pipe\`` (no es un archivo
 *   real; no requiere mkdir ni existsSync ni rmSync). El hash del cwd se
 *   incluye para que workspaces distintos no colisionen.
 *
 * Antes de este fix Windows tiraba ``EACCES`` al intentar listen() en
 * un path ``.sock``.
 */
function hubSocketPath(cwd: string): string {
  if (IS_WINDOWS) {
    return `\\\\.\\pipe\\cortex-net-hub-${workspaceHash(cwd)}`;
  }
  return join(netDir(cwd), "cortex-net.sock");
}

/** Ídem hubSocketPath pero por peer. */
function peerSocketPath(cwd: string, role: CortexRole): string {
  if (IS_WINDOWS) {
    return `\\\\.\\pipe\\cortex-net-peer-${workspaceHash(cwd)}-${role}-${process.pid}`;
  }
  return join(netDir(cwd), `cortex-net-${role}-${process.pid}.sock`);
}

function auditLogPath(cwd: string): string {
  return join(netDir(cwd), "cortex-net.log");
}

function logAudit(cwd: string, entry: object): void {
  try {
    appendFileSync(
      auditLogPath(cwd),
      JSON.stringify({ ts: new Date().toISOString(), ...entry }) + "\n",
      "utf-8"
    );
  } catch {
    /* logging never throws */
  }
}

/**
 * Transcript log: a diferencia del audit, SÍ guarda el body de los mensajes.
 * Esto permite al documenter en el cierre reconstruir las decisiones que
 * pasaron por la red (negociaciones designer-SDDwork, blockers resueltos
 * vía question/reply, etc.) y citarlas explícitamente en la session note.
 *
 * Una entrada por send/reply exitoso. Filtrable por session_id en lectura.
 * El archivo vive en el mismo directorio que el audit y se borra junto
 * con `.pi/agent-sessions/` cuando el usuario hace cleanup o
 * `/cortex-net-shutdown`.
 *
 * Formato de cada línea JSON:
 *   {
 *     "ts": "ISO timestamp",
 *     "session_id": "...",
 *     "kind": "send" | "reply",
 *     "msg_id": "...",
 *     "from_role": "...",
 *     "to_role": "...",
 *     "msg_type": "question" | "proposal" | "blocker" | "handoff" | "observe",
 *     "body": "...",                      // texto completo del mensaje
 *     "reply_to_msg_id": "..." | null     // solo para kind="reply"
 *   }
 */
function transcriptLogPath(cwd: string): string {
  return join(netDir(cwd), "cortex-net-transcript.log");
}

function logTranscript(cwd: string, entry: object): void {
  try {
    appendFileSync(
      transcriptLogPath(cwd),
      JSON.stringify({ ts: new Date().toISOString(), ...entry }) + "\n",
      "utf-8"
    );
  } catch {
    /* logging never throws */
  }
}

function ensureNetDir(cwd: string): void {
  const dir = netDir(cwd);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

/**
 * Mapa fijo de nombres canónicos de agents Cortex → roles cortex-net.
 * Sync queda fuera del mapa por diseño (B' model).
 */
const AGENT_TO_ROLE: Record<string, CortexRole> = {
  "cortex-sddwork": "sddwork",
  "cortex-code-designer": "designer",
  "cortex-code-explorer": "explorer",
  "cortex-code-implementer": "implementer",
  "cortex-security-auditor": "security",
  "cortex-test-verifier": "test-verifier",
  "cortex-documenter": "documenter",
};

/**
 * Resuelve el rol cortex-net del agente activo.
 *
 * Orden de prioridad (de mayor a menor):
 *
 *   1. ``activeAgentName`` provisto por el hook ``before_agent_start`` —
 *      esto es lo que sucede en uso normal cuando el usuario cambia de
 *      agent in-session (vía /system o slash command). Es la fuente más
 *      fresca y la que usamos por default.
 *
 *   2. Env var ``CORTEX_NET_ROLE`` — override explícito. Útil para
 *      terminales dedicadas estilo IndyDevDan demo (``just role-designer``).
 *      Si la env var dice "designer" pero el hook dice "implementer",
 *      gana el hook salvo que no haya hook todavía.
 *
 *   3. Env var ``CORTEX_ACTIVE_AGENT`` — legacy/compat para flows que
 *      todavía la setean.
 *
 * Retorna null si el agente NO debería entrar a la red (sync o
 * agente desconocido).
 */
function resolveRole(activeAgentName?: string): CortexRole | null {
  // 1. Hook-provided agent name (fuente más fresca)
  if (activeAgentName) {
    const normalized = activeAgentName.trim().toLowerCase();
    if (normalized === "cortex-sync") return null; // B' anchor
    if (AGENT_TO_ROLE[normalized]) return AGENT_TO_ROLE[normalized];
  }

  // 2. Env var explícita (override para multi-terminal manual)
  const explicit = process.env.CORTEX_NET_ROLE?.trim().toLowerCase();
  if (explicit && CORTEX_ROLES.includes(explicit as CortexRole)) {
    return explicit as CortexRole;
  }

  // 3. Legacy env var CORTEX_ACTIVE_AGENT (compat)
  const legacy = process.env.CORTEX_ACTIVE_AGENT?.trim().toLowerCase() ?? "";
  if (legacy === "cortex-sync") return null;
  if (AGENT_TO_ROLE[legacy]) return AGENT_TO_ROLE[legacy];

  return null;
}

/**
 * Lee la session_id activa de Cortex. Estrategia:
 *   1. CORTEX_SESSION_ID env var (la setea el adapter cuando arranca Pi).
 *   2. Lee `.cortex/session.lock` si existe.
 *   3. null — en cuyo caso cortex-net NO arranca (no hay sesión activa).
 */
function resolveSessionId(cwd: string): string | null {
  const fromEnv = process.env.CORTEX_SESSION_ID?.trim();
  if (fromEnv) return fromEnv;

  const lock = join(cwd, ".cortex", "session.lock");
  if (existsSync(lock)) {
    try {
      const raw = readFileSync(lock, "utf-8").trim();
      if (raw) return raw;
    } catch {
      /* ignore */
    }
  }
  return null;
}

// ── Hub server (one per workspace) ────────────────────────────────────────

/**
 * El primer agente que arranca crea el hub server en hubSocketPath.
 * Los siguientes lo encuentran y se registran como clients.
 * Si el hub muere, el próximo agente que arranque lo recrea.
 */
class CortexNetHub {
  private server: Server | null = null;
  private peers = new Map<CortexRole, Peer>();
  private constructor(private readonly cwd: string) {}

  static async tryStart(cwd: string): Promise<CortexNetHub | null> {
    const sockPath = hubSocketPath(cwd);

    // Connect-test directo: probamos a conectarnos al pipe/socket. Si
    // hay un hub vivo, conecta. Si no hay nadie escuchando o el path
    // está muerto, falla.
    //
    // Bugfix mayo 2026: NO chequeamos existsSync antes, porque en
    // Windows los Named Pipes (\\.\pipe\...) no se ven como "existentes"
    // en el filesystem y existsSync siempre devuelve false. El
    // connect-test funciona idéntico en Linux y Windows.
    const alive = await new Promise<boolean>((resolve) => {
      const test = createConnection(sockPath);
      const timer = setTimeout(() => {
        test.destroy();
        resolve(false);
      }, 500);
      test.once("error", () => {
        clearTimeout(timer);
        resolve(false);
      });
      test.once("connect", () => {
        clearTimeout(timer);
        test.end();
        resolve(true);
      });
    });
    if (alive) return null; // hay hub vivo, somos client

    // Hub no responde. En Linux, si quedó un socket file muerto, hay
    // que removerlo antes de poder listen(). En Windows los Named
    // Pipes son auto-cleanup al cierre del proceso anterior.
    if (!IS_WINDOWS) {
      try {
        if (existsSync(sockPath)) rmSync(sockPath);
      } catch {
        /* ignore */
      }
    }

    const hub = new CortexNetHub(cwd);
    hub.server = createServer((sock) => hub.handleConnection(sock));
    return new Promise((resolve) => {
      hub.server!.once("error", () => resolve(null)); // race condition, otro nos ganó
      hub.server!.listen(sockPath, () => resolve(hub));
    });
  }

  private handleConnection(sock: Socket): void {
    let buf = "";
    sock.on("data", (chunk) => {
      buf += chunk.toString("utf-8");
      let nl: number;
      while ((nl = buf.indexOf("\n")) !== -1) {
        const line = buf.slice(0, nl);
        buf = buf.slice(nl + 1);
        if (!line.trim()) continue;
        try {
          const msg = JSON.parse(line) as NetMessage;
          this.dispatch(msg, sock);
        } catch {
          /* malformed, ignore */
        }
      }
    });
    sock.on("error", () => {
      /* swallow */
    });
  }

  private dispatch(msg: NetMessage, sock: Socket): void {
    switch (msg.kind) {
      case "register": {
        // F3: default status según rol. documenter empieza en "observe";
        // el resto en "idle". El cliente puede overridear vía heartbeat.
        const defaultStatus: PeerStatus =
          msg.from_role === "documenter" ? "observe" : "idle";
        const status = msg.status ?? defaultStatus;
        this.peers.set(msg.from_role, {
          role: msg.from_role,
          pid: msg.pid ?? 0,
          session_id: msg.session_id,
          model: msg.model ?? "unknown",
          last_heartbeat: Date.now(),
          socket_path: msg.socket_path ?? "",
          status,
        });
        sock.write(JSON.stringify({ ok: true }) + "\n");
        logAudit(this.cwd, {
          op: "register",
          role: msg.from_role,
          session_id: msg.session_id,
        });
        // F3: notificamos a todos los demás peers de la misma sesión
        // que se sumó alguien. Push-based, sin polling.
        this.broadcastPeerEvent(msg.session_id, {
          event_op: "joined",
          event_role: msg.from_role,
          event_status: status,
        });
        break;
      }

      case "heartbeat": {
        const peer = this.peers.get(msg.from_role);
        if (peer) {
          peer.last_heartbeat = Date.now();
          // F3: heartbeat puede traer status nuevo. Si cambió,
          // notificamos a todos.
          if (msg.status && msg.status !== peer.status) {
            peer.status = msg.status;
            this.broadcastPeerEvent(msg.session_id, {
              event_op: "status_changed",
              event_role: msg.from_role,
              event_status: msg.status,
            });
          }
        }
        sock.write(JSON.stringify({ ok: true }) + "\n");
        break;
      }

      case "unregister":
        this.peers.delete(msg.from_role);
        sock.write(JSON.stringify({ ok: true }) + "\n");
        logAudit(this.cwd, {
          op: "unregister",
          role: msg.from_role,
          session_id: msg.session_id,
        });
        // F3: notificamos al resto.
        this.broadcastPeerEvent(msg.session_id, {
          event_op: "left",
          event_role: msg.from_role,
        });
        break;

      case "list":
        this.pruneStale();
        sock.write(
          JSON.stringify({
            peers: [...this.peers.values()].map((p) => ({
              role: p.role,
              session_id: p.session_id,
              model: p.model,
              pid: p.pid,
              status: p.status, // F3
            })),
          }) + "\n"
        );
        break;

      case "broadcast": {
        // F3: fanout a todos los peers de la misma sesión (excepto el emisor).
        // Útil para "spec actualizada", "blocker general", etc.
        let delivered = 0;
        for (const peer of this.peers.values()) {
          if (peer.role === msg.from_role) continue;
          if (peer.session_id !== msg.session_id) continue;
          this.relayTo(peer, { ...msg, kind: "send", to_role: peer.role });
          delivered++;
          // Log transcript con cada destinatario para que el documenter
          // pueda reconstruir el fanout.
          logTranscript(this.cwd, {
            session_id: msg.session_id,
            kind: "send",
            msg_id: msg.msg_id,
            from_role: msg.from_role,
            to_role: peer.role,
            msg_type: msg.msg_type,
            body: msg.body ?? "",
            reply_to_msg_id: null,
          });
        }
        sock.write(
          JSON.stringify({ ok: true, msg_id: msg.msg_id, delivered }) + "\n"
        );
        logAudit(this.cwd, {
          op: "broadcast",
          from: msg.from_role,
          msg_type: msg.msg_type,
          delivered,
        });
        break;
      }

      case "send": {
        // Gate de session_id: solo agentes en la misma sesión se hablan
        const target = this.peers.get(msg.to_role!);
        if (!target) {
          sock.write(
            JSON.stringify({
              ok: false,
              error: `peer "${msg.to_role}" no está en la red`,
            }) + "\n"
          );
          return;
        }
        if (target.session_id !== msg.session_id) {
          sock.write(
            JSON.stringify({
              ok: false,
              error: `cross-session traffic blocked (sender=${msg.session_id}, target=${target.session_id})`,
            }) + "\n"
          );
          logAudit(this.cwd, {
            op: "cross_session_blocked",
            from: msg.from_role,
            to: msg.to_role,
          });
          return;
        }

        // Reenvía al socket del target
        this.relayTo(target, msg);
        sock.write(JSON.stringify({ ok: true, msg_id: msg.msg_id }) + "\n");
        logAudit(this.cwd, {
          op: "send",
          from: msg.from_role,
          to: msg.to_role,
          msg_type: msg.msg_type,
          msg_id: msg.msg_id,
        });
        // Transcript con body completo (para el documenter al cierre)
        logTranscript(this.cwd, {
          session_id: msg.session_id,
          kind: "send",
          msg_id: msg.msg_id,
          from_role: msg.from_role,
          to_role: msg.to_role,
          msg_type: msg.msg_type,
          body: msg.body ?? "",
          reply_to_msg_id: null,
        });
        break;
      }

      case "reply": {
        // Las replies van al sender original
        const orig = this.peers.get(msg.to_role!);
        if (!orig) {
          sock.write(JSON.stringify({ ok: false, error: "sender gone" }) + "\n");
          return;
        }
        this.relayTo(orig, msg);
        sock.write(JSON.stringify({ ok: true }) + "\n");
        logAudit(this.cwd, {
          op: "reply",
          from: msg.from_role,
          to: msg.to_role,
          reply_to: msg.reply_to_msg_id,
        });
        // Transcript con body completo (para el documenter al cierre)
        logTranscript(this.cwd, {
          session_id: msg.session_id,
          kind: "reply",
          msg_id: msg.msg_id ?? `reply-${msg.reply_to_msg_id}`,
          from_role: msg.from_role,
          to_role: msg.to_role,
          msg_type: "reply" as any,
          body: msg.body ?? "",
          reply_to_msg_id: msg.reply_to_msg_id ?? null,
        });
        break;
      }
    }
  }

  private relayTo(target: Peer, msg: NetMessage): void {
    if (!target.socket_path) return;
    // Bugfix mayo 2026: existsSync(\\.\pipe\...) siempre devuelve false
    // en Windows, así que skippeamos el chequeo en Windows. En Linux lo
    // mantenemos como guard rápido. Si en Windows el pipe está muerto,
    // createConnection emitirá ``error`` y el handler abajo lo come.
    if (!IS_WINDOWS && !existsSync(target.socket_path)) return;
    try {
      const conn = createConnection(target.socket_path);
      conn.on("error", () => {
        /* peer offline */
      });
      conn.on("connect", () => {
        conn.write(JSON.stringify(msg) + "\n");
        conn.end();
      });
    } catch {
      /* ignore */
    }
  }

  /**
   * F3: emite un ``peer_event`` push a TODOS los peers de la sesión
   * indicada (incluyendo al que disparó el evento — el client decide si
   * filtrar self-events). Best-effort: no espera ack, los peers offline
   * se ignoran sin error.
   */
  private broadcastPeerEvent(
    sessionId: string,
    event: {
      event_op: "joined" | "left" | "status_changed";
      event_role: CortexRole;
      event_status?: PeerStatus;
    }
  ): void {
    for (const peer of this.peers.values()) {
      if (peer.session_id !== sessionId) continue;
      this.relayTo(peer, {
        kind: "peer_event",
        from_role: event.event_role, // semánticamente: "quién disparó"
        session_id: sessionId,
        event_op: event.event_op,
        event_role: event.event_role,
        event_status: event.event_status,
      });
    }
  }

  private pruneStale(): void {
    const now = Date.now();
    for (const [role, peer] of this.peers) {
      if (now - peer.last_heartbeat > STALE_AFTER_MS) {
        const sessionId = peer.session_id;
        this.peers.delete(role);
        logAudit(this.cwd, { op: "prune_stale", role });
        // F3: notificamos al resto. Mismo evento que unregister
        // pero generado por el hub (no por el peer mismo).
        this.broadcastPeerEvent(sessionId, {
          event_op: "left",
          event_role: role,
        });
      }
    }
  }

  shutdown(): void {
    this.server?.close();
    // En Windows los Named Pipes se limpian solos al cerrar el server;
    // rmSync sobre \\.\pipe\... falla con ENOENT/EPERM. Solo en Linux
    // hay un archivo .sock que sobrevive y conviene borrar.
    if (!IS_WINDOWS) {
      try {
        rmSync(hubSocketPath(this.cwd));
      } catch {
        /* ignore */
      }
    }
  }
}

// ── Client (per-agent) ─────────────────────────────────────────────────────

class CortexNetClient {
  private inboundServer: Server | null = null;
  private pendingReplies = new Map<string, PendingReply>();
  /**
   * Cola FIFO de mensajes entrantes pendientes. Rediseño may-2026: se
   * entregan UNO por turno y el receptor los ejecuta DIRECTO (sin auto-reply).
   * El handler de Pi los entrega vía pi.sendUserMessage.
   */
  inboundQueue: Array<{
    msg_id: string;
    from_role: CortexRole;
    msg_type: MsgType;
    body: string;
  }> = [];

  /**
   * Callback que el handler de Pi setea para enterarse de un inbound nuevo
   * (lo invoca processInbound). El handler decide: notificar + (si el agente
   * está libre) auto-disparar un turno para ejecutarlo. null = sin listener.
   */
  onInbound: (() => void) | null = null;

  private heartbeatTimer: NodeJS.Timeout | null = null;

  /**
   * F3: status actual de este cliente. ``idle`` por default; ``observe``
   * para documenter. ``busy`` lo seteamos desde el handler de Pi en
   * ``before_agent_start`` y volvemos a ``idle`` en ``turn_end``.
   *
   * Cada heartbeat lo envía; si cambió, el hub propaga ``status_changed``
   * push a todos los peers.
   */
  private myStatus: PeerStatus;

  /**
   * F3: callback que el handler de Pi setea para enterarse de eventos
   * push del hub (joined/left/status_changed). El client lo invoca al
   * recibir un ``peer_event``. ``null`` = no hay listener (los eventos
   * se ignoran silenciosamente).
   */
  onPeerEvent: ((ev: {
    op: "joined" | "left" | "status_changed";
    role: CortexRole;
    status?: PeerStatus;
  }) => void) | null = null;

  constructor(
    private readonly cwd: string,
    private readonly role: CortexRole,
    private readonly sessionId: string,
    private readonly model: string
  ) {
    this.myStatus = role === "documenter" ? "observe" : "idle";
  }

  /** F3: setter público para que el handler externo cambie el status. */
  setStatus(status: PeerStatus): void {
    this.myStatus = status;
    // El cambio viaja al hub en el próximo heartbeat (max HEARTBEAT_MS).
    // No mandamos un heartbeat eager porque el rate-limit del hub
    // procesa mejor pulsos regulares.
  }

  /** F3: lectura del status actual. */
  getStatus(): PeerStatus {
    return this.myStatus;
  }

  async start(): Promise<void> {
    ensureNetDir(this.cwd);

    // 1. Levantamos nuestro socket/pipe de inbound. En Linux limpiamos
    // un .sock muerto si quedó de un proceso anterior; en Windows los
    // Named Pipes son auto-cleanup y no aplica.
    const myPath = peerSocketPath(this.cwd, this.role);
    if (!IS_WINDOWS) {
      try {
        if (existsSync(myPath)) rmSync(myPath);
      } catch {
        /* ignore */
      }
    }

    this.inboundServer = createServer((sock) => this.handleInbound(sock));
    await new Promise<void>((resolve, reject) => {
      this.inboundServer!.once("error", reject);
      this.inboundServer!.listen(myPath, resolve);
    });

    // 2. Nos registramos en el hub (F3: con status inicial)
    await this.send({
      kind: "register",
      from_role: this.role,
      session_id: this.sessionId,
      pid: process.pid,
      model: this.model,
      socket_path: myPath,
      status: this.myStatus,
    });

    // 3. Empezamos heartbeats (F3: incluyen status)
    this.heartbeatTimer = setInterval(() => {
      this.send({
        kind: "heartbeat",
        from_role: this.role,
        session_id: this.sessionId,
        status: this.myStatus,
      }).catch(() => {
        /* hub gone, no-op (next register will recreate) */
      });
    }, HEARTBEAT_MS);
  }

  async stop(): Promise<void> {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    try {
      await this.send({
        kind: "unregister",
        from_role: this.role,
        session_id: this.sessionId,
      });
    } catch {
      /* hub already gone */
    }
    this.inboundServer?.close();
    // Solo aplica en Linux. Windows Named Pipes se limpian solos.
    if (!IS_WINDOWS) {
      try {
        rmSync(peerSocketPath(this.cwd, this.role));
      } catch {
        /* ignore */
      }
    }
  }

  /** Envío al hub. Retorna la respuesta JSON del hub (ok/error/peers). */
  send(msg: NetMessage): Promise<any> {
    return new Promise((resolve, reject) => {
      const conn = createConnection(hubSocketPath(this.cwd));
      let buf = "";
      const timeout = setTimeout(() => {
        conn.destroy();
        reject(new Error("hub timeout"));
      }, 3000);
      conn.on("connect", () => {
        conn.write(JSON.stringify(msg) + "\n");
      });
      conn.on("data", (chunk) => {
        buf += chunk.toString("utf-8");
        const nl = buf.indexOf("\n");
        if (nl !== -1) {
          clearTimeout(timeout);
          try {
            const parsed = JSON.parse(buf.slice(0, nl));
            resolve(parsed);
          } catch (e) {
            reject(e);
          }
          conn.end();
        }
      });
      conn.on("error", (e) => {
        clearTimeout(timeout);
        reject(e);
      });
    });
  }

  /** Inbound handler: aceptamos mensajes routed por el hub. */
  private handleInbound(sock: Socket): void {
    let buf = "";
    sock.on("data", (chunk) => {
      buf += chunk.toString("utf-8");
      const nl = buf.indexOf("\n");
      if (nl !== -1) {
        try {
          const msg = JSON.parse(buf.slice(0, nl)) as NetMessage;
          this.processInbound(msg);
        } catch {
          /* ignore */
        }
      }
    });
  }

  private processInbound(msg: NetMessage): void {
    if (msg.kind === "send") {
      // Mensaje nuevo: lo encolamos para que el system prompt lo vea
      // y marcamos que el próximo turn auto-reply a este msg_id
      this.inboundQueue.push({
        msg_id: msg.msg_id!,
        from_role: msg.from_role,
        msg_type: msg.msg_type ?? "question",
        body: msg.body ?? "",
      });
      // Avisar al handler de Pi: notifica + (si el agente está libre)
      // auto-dispara un turno para ejecutar el inbound DIRECTO.
      this.onInbound?.();
    } else if (msg.kind === "reply") {
      // Respuesta a un await/get nuestro
      const pending = this.pendingReplies.get(msg.reply_to_msg_id!);
      if (pending) {
        clearTimeout(pending.timer);
        pending.resolve(msg.body ?? "");
        this.pendingReplies.delete(msg.reply_to_msg_id!);
      }
    } else if (msg.kind === "peer_event") {
      // F3: notificación push del hub. Filtramos self-events (cuando el
      // hub broadcastea joined del que se acaba de registrar, le llega
      // también a él). Es informativo para el client mismo, pero
      // upstream el handler suele filtrarlo.
      if (this.onPeerEvent && msg.event_op && msg.event_role) {
        this.onPeerEvent({
          op: msg.event_op,
          role: msg.event_role,
          status: msg.event_status,
        });
      }
    }
  }

  /** Public API: envía un mensaje y obtiene msg_id. */
  async sendMessage(
    toRole: CortexRole,
    msgType: MsgType,
    body: string
  ): Promise<{ msg_id: string; ok: boolean; error?: string }> {
    const msg_id = newMsgId();
    const res = await this.send({
      kind: "send",
      msg_id,
      from_role: this.role,
      to_role: toRole,
      session_id: this.sessionId,
      msg_type: msgType,
      body,
    });
    return { msg_id, ok: res.ok ?? false, error: res.error };
  }

  /**
   * F3: Public API — broadcast a TODOS los peers de la misma sesión.
   *
   * El hub hace fanout: cada peer recibe el mensaje como si hubiera sido
   * un send dirigido. ``msg_id`` es uno solo para todos los destinatarios
   * (el transcript guarda una línea por delivery con ese mismo msg_id).
   *
   * Útil para "spec actualizada", "blocker general", "team standup", etc.
   * NO espera respuestas — si querés una sola respuesta agregada, usá
   * sendMessage 1:1 al peer correspondiente.
   */
  async broadcast(
    msgType: MsgType,
    body: string
  ): Promise<{ msg_id: string; ok: boolean; delivered?: number; error?: string }> {
    const msg_id = newMsgId();
    const res = await this.send({
      kind: "broadcast",
      msg_id,
      from_role: this.role,
      session_id: this.sessionId,
      msg_type: msgType,
      body,
    });
    return {
      msg_id,
      ok: res.ok ?? false,
      delivered: res.delivered,
      error: res.error,
    };
  }

  /** Public API: lista peers actuales. */
  async listPeers(): Promise<
    Array<{ role: string; session_id: string; model: string; pid: number }>
  > {
    const res = await this.send({
      kind: "list",
      from_role: this.role,
      session_id: this.sessionId,
    });
    return res.peers ?? [];
  }

  /** Public API: lee respuesta sin bloquear. */
  getReply(msg_id: string): string | null {
    // Las replies llegan via inbound y resuelven el pending — pero si nadie
    // hizo await, el pending no existe. Implementamos un buffer simple:
    // si no hay pending y la reply llega, queda en this.replyBuffer.
    return this.replyBuffer.get(msg_id) ?? null;
  }

  /** Public API: bloquea hasta que llegue reply (o timeout). */
  awaitReply(msg_id: string, timeoutMs = 120_000): Promise<string> {
    const buffered = this.replyBuffer.get(msg_id);
    if (buffered) {
      this.replyBuffer.delete(msg_id);
      return Promise.resolve(buffered);
    }
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pendingReplies.delete(msg_id);
        reject(new Error(`await timeout for ${msg_id}`));
      }, timeoutMs);
      this.pendingReplies.set(msg_id, { resolve, timer });
    });
  }

  private replyBuffer = new Map<string, string>();

  // Rediseño may-2026: se eliminó sendAutoReply (auto-reply implícita). Ahora
  // el receptor ejecuta el inbound directo y, si quiere responder, manda un
  // cortex_net_send explícito (gated por el humano). Los replies que SÍ llegan
  // (de un cortex_net_await) se manejan en processInbound → pendingReplies.

  /** Saca el siguiente inbound de la cola (FIFO), o null si está vacía. */
  dequeueInbound():
    | { msg_id: string; from_role: CortexRole; msg_type: MsgType; body: string }
    | null {
    return this.inboundQueue.shift() ?? null;
  }

  /** Cantidad de inbounds pendientes en la cola. */
  inboundCount(): number {
    return this.inboundQueue.length;
  }
}

// ── Extension entry ────────────────────────────────────────────────────────

export default async function (pi: ExtensionAPI) {
  // Estado global de la extensión
  let client: CortexNetClient | null = null;
  let hub: CortexNetHub | null = null;
  // Último ctx visto en un handler — lo usan los callbacks async (ej. la
  // llegada de un inbound por socket) para ctx.isIdle() / ctx.ui.notify().
  let lastCtx: any = null;
  let cachedSessionId: string | null = null;
  let cachedModel = "unknown";
  let cachedCwd = "";
  let currentRegisteredRole: CortexRole | null = null;
  // F1: handle del polling de peers que mantiene cortexState.peers fresco
  // para el cockpit. Inicializado en session_start, limpiado en session_shutdown.
  let peerPollHandle: NodeJS.Timeout | null = null;
  // Bugfix mayo 2026: suscripción al singleton para detectar lock que
  // aparece post-arranque (sync abre la sesión después de session_start).
  let stateUnsub: (() => void) | null = null;

  pi.registerMessageRenderer("cortex-net", (message, _options, theme) => {
    const content = typeof message.content === "string" ? message.content : "";
    return new Text(theme.fg("accent", "⬢ net: ") + content, 0, 0);
  });

  // Publicamos las acciones de red para que el panel /cortex (u otra
  // extensión) pueda mandar/broadcastear DE VERDAD —sin LLM— en vez de
  // mostrar un hint. Los closures leen `client` en tiempo de llamada, así
  // que siguen al cliente actual aunque se re-registre o se baje.
  registerNetActions({
    isReady: () => client !== null,
    listPeers: async () => cortexState.peers,
    send: async (toRole, msgType, body) => {
      if (!client) return { ok: false, error: "no estás conectado a la red" };
      try {
        const r = await client.sendMessage(
          toRole as CortexRole,
          msgType as MsgType,
          body
        );
        return { ok: r.ok, error: r.error };
      } catch (e: any) {
        return { ok: false, error: e?.message ?? String(e) };
      }
    },
    broadcast: async (msgType, body) => {
      if (!client) return { ok: false, error: "no estás conectado a la red" };
      try {
        const r = await client.broadcast(msgType as MsgType, body);
        return { ok: r.ok, delivered: r.delivered, error: r.error };
      } catch (e: any) {
        return { ok: false, error: e?.message ?? String(e) };
      }
    },
  });

  // ── Cola de inbound (rediseño may-2026) ─────────────────────────────────

  /** Refleja la cola del cliente al singleton (cockpit muestra "📨 N en cola"). */
  function syncInboundSnapshot(): void {
    const q = client?.inboundQueue ?? [];
    updateCortexState({
      inbound: q.map((m) => ({
        from: m.from_role,
        type: m.msg_type,
        preview: m.body.slice(0, 60),
      })),
    });
  }

  /**
   * Entrega UN inbound (FIFO) al agente vía pi.sendUserMessage, que dispara un
   * turno. El agente lo ejecuta DIRECTO (el humano emisor ya aprobó el envío).
   * Para responder/coordinar, el agente usa cortex_net_send (gated).
   */
  function deliverNextInbound(): void {
    if (!client) return;
    const msg = client.dequeueInbound();
    syncInboundSnapshot();
    if (!msg) return;
    pi.sendUserMessage(
      `📨 [cortex-net] Mensaje de "${msg.from_role}" (${msg.msg_type}):\n` +
        `${msg.body}\n\n` +
        `Ejecutá esta instrucción directamente. Para responder o coordinar usá ` +
        `cortex_net_send (te lo confirma el humano antes de salir).`
    );
  }

  /**
   * Lo llama el cliente al llegar un inbound nuevo. Notifica y, si el agente
   * está LIBRE y es el único en cola, lo dispara directo (knob a). Si está
   * ocupado, queda en cola y se libera tras el turno (turn_end / /cx-inbox) —
   * así no se encadenan instrucciones sin relación ni se pisa el trabajo en vuelo.
   */
  function handleNewInbound(): void {
    const q = client?.inboundQueue ?? [];
    syncInboundSnapshot();
    if (q.length === 0) return;
    const last = q[q.length - 1];
    lastCtx?.ui?.notify(
      `📨 ${last.msg_type} de ${last.from_role}: ${last.body.slice(0, 80)}`,
      "info"
    );
    const idle = typeof lastCtx?.isIdle === "function" ? lastCtx.isIdle() : true;
    if (idle && q.length === 1) {
      deliverNextInbound();
    }
  }

  /**
   * Helper interno: registra (o re-registra) el cliente con un rol dado.
   * Se llama desde before_agent_start cada vez que el agent activo cambia.
   * Si el rol no varió, no-op. Si varió, hace stop() del cliente anterior
   * y start() del nuevo.
   */
  async function ensureRegisteredAs(role: CortexRole, ctx: any): Promise<void> {
    if (currentRegisteredRole === role && client) return; // ya estamos bien

    // Hay que rotar: si había cliente con otro rol, lo damos de baja
    if (client) {
      try {
        await client.stop();
      } catch {
        /* swallow */
      }
      client = null;
    }

    if (!cachedSessionId) {
      // Reintentamos leer session_id (puede haber cambiado mid-session)
      cachedSessionId = resolveSessionId(cachedCwd);
    }
    if (!cachedSessionId) {
      ctx?.ui?.notify(
        "⬢ cortex-net: no hay Cortex Session activa, red no iniciada",
        "warning"
      );
      return;
    }

    client = new CortexNetClient(cachedCwd, role, cachedSessionId, cachedModel);
    // Rediseño may-2026: al llegar un inbound, notificar + (si está libre)
    // ejecutar directo. Se engancha ANTES del start() para no perder mensajes.
    client.onInbound = handleNewInbound;
    // F3: enchufar el callback de peer_event ANTES del start(), así no
    // perdemos eventos que lleguen entre register y la primera vuelta
    // del event loop.
    client.onPeerEvent = (ev) => {
      // Self-event: ignoramos (el hub broadcastea joined al recién
      // registrado también). Para los demás eventos: actualizamos el
      // singleton al toque (sin esperar el polling de respaldo).
      if (ev.op === "joined" && ev.role === role) return;
      // Mutamos peers en el snapshot del singleton de forma quirúrgica
      // para preservar otros campos si los hay.
      const current = [...cortexState.peers];
      if (ev.op === "joined" || ev.op === "status_changed") {
        const idx = current.findIndex((p) => p.role === ev.role);
        if (idx >= 0) {
          current[idx] = { ...current[idx], status: ev.status };
        } else if (ev.op === "joined") {
          // Peer nuevo del que no teníamos snapshot — placeholder. El
          // próximo listPeers() de respaldo lo completará con pid/model.
          current.push({
            role: ev.role,
            pid: 0,
            session_id: cachedSessionId ?? "",
            model: "unknown",
            last_heartbeat: Date.now(),
            status: ev.status,
          });
        }
      } else if (ev.op === "left") {
        const idx = current.findIndex((p) => p.role === ev.role);
        if (idx >= 0) current.splice(idx, 1);
      }
      updateCortexState({ peers: current });
    };
    try {
      await client.start();
      currentRegisteredRole = role;
      // F1: propagar al singleton para el cockpit.
      updateCortexState({ myRole: role, isMaster: hub !== null });
      ctx?.ui?.notify(
        `⬢ cortex-net: registrado como "${role}" en sesión ${cachedSessionId.slice(0, 8)}… ${hub ? "(hub)" : ""}`,
        "success"
      );
    } catch (err: any) {
      ctx?.ui?.notify(
        `⬢ cortex-net: fallo al unirse — ${err.message}`,
        "warning"
      );
      client = null;
      currentRegisteredRole = null;
      updateCortexState({ myRole: null });
    }
  }

  // ── session_start: arrancamos hub y cacheamos contexto base ────────────
  // NO registramos cliente todavía. El rol se decide en before_agent_start
  // según qué agent esté arrancando (model D, hook-driven). Esto permite
  // que el mismo proceso Pi cambie de rol cuando el usuario hace /system
  // o invoca un subagent vía Task.
  /**
   * Bugfix mayo 2026: extraída del session_start para poder llamarla
   * también desde el polling y la suscripción al singleton cuando el
   * session.lock aparece DESPUÉS de session_start (caso típico: Pi
   * arranca con default agent cortex-sync, el usuario escribe la tarea,
   * sync crea la spec y recién ahí el backend escribe el lock).
   *
   * Idempotente: si ya tenemos hub o client, no-op.
   */
  async function tryInitNetwork(ctx: any): Promise<boolean> {
    if (hub !== null || client !== null) return true;
    if (!cachedCwd) return false;

    cachedSessionId = resolveSessionId(cachedCwd);
    if (!cachedSessionId) return false;

    // Propagar al singleton ANTES de tocar el hub para que el cockpit
    // tenga sessionId disponible desde el primer redraw.
    updateCortexState({ sessionId: cachedSessionId });

    hub = await CortexNetHub.tryStart(cachedCwd);
    updateCortexState({ isMaster: hub !== null });

    ctx?.ui?.notify(
      `⬢ cortex-net: hub ${hub ? "iniciado" : "detectado"} para sesión ${cachedSessionId.slice(0, 8)}…`,
      "info"
    );

    // Si el usuario forzó un rol vía CORTEX_NET_ROLE, registramos ya.
    const forced = resolveRole();
    if (forced) {
      await ensureRegisteredAs(forced, ctx);
    } else if (cortexState.myRole) {
      // Si system-select ya escribió un rol al singleton (típico: el
      // usuario eligió cortex-SDDwork antes de que apareciera el lock),
      // registrarlo ahora mismo. Sino, esperamos al subscriber del
      // singleton que reacciona cuando myRole cambia.
      await ensureRegisteredAs(cortexState.myRole, ctx);
    }
    return true;
  }

  pi.on("session_start", async (_event, ctx) => {
    lastCtx = ctx;
    cachedCwd = ctx.cwd;
    cachedModel =
      `${ctx.model?.provider ?? "?"}/${ctx.model?.id ?? "?"}` || "unknown";

    // F1: sembrar el singleton con lo que se sabe antes de tocar el hub.
    updateCortexState({
      cwd: ctx.cwd,
      myModel: cachedModel,
    });

    // Intentamos init de red. Si no hay lock todavía, deja todo en
    // standby — el polling y la suscripción al singleton lo retomarán
    // cuando aparezca.
    const inited = await tryInitNetwork(ctx);
    if (!inited) {
      ctx.ui.notify(
        "⬢ cortex-net: standby (esperando session.lock — corré cortex-sync para crear sesión)",
        "info"
      );
    }

    // Suscripción al singleton: nos enteramos de dos clases de eventos
    // sin re-suscribirnos por separado a cada hook:
    //
    //   1. sessionId apareció (cockpit polling detectó el lock que el
    //      backend acaba de escribir) → init network.
    //
    //   2. myRole cambió (system-select escribió un agent del medio
    //      al singleton) → registrarse en la red con el rol nuevo.
    //
    //   3. myRole se limpió (system-select eligió "ninguno" o
    //      cortex-sync) → darse de baja de la red.
    if (!stateUnsub) {
      stateUnsub = subscribeCortexState(() => {
        // 1. Lock que apareció post-arranque.
        if (cortexState.sessionId && !cachedSessionId && !hub && !client && cachedCwd) {
          queueMicrotask(() => {
            void tryInitNetwork(ctx);
          });
          return;
        }
        // 2. myRole cambió y hub ya está levantado → registrar.
        if (
          cortexState.myRole &&
          hub !== null &&
          cortexState.myRole !== currentRegisteredRole
        ) {
          const role = cortexState.myRole;
          queueMicrotask(() => {
            void ensureRegisteredAs(role, ctx);
          });
          return;
        }
        // 3. myRole se limpió mientras estábamos registrados → bajar.
        if (!cortexState.myRole && client !== null) {
          queueMicrotask(async () => {
            if (client) {
              try {
                await client.stop();
              } catch {
                /* swallow */
              }
              client = null;
              currentRegisteredRole = null;
            }
          });
        }
      });
    }

    // F3: el camino feliz son eventos push del hub. El polling de 15s
    // queda como respaldo Y ahora también como detector secundario del
    // lock — si la suscripción al singleton perdió el evento, el
    // polling lo agarra en la próxima vuelta.
    peerPollHandle = setInterval(async () => {
      // 1. Si red no inicializada y hay lock → init
      if (!client && !hub) {
        await tryInitNetwork(ctx);
      }
      // 2. Si red activa → refrescar peers
      if (client) {
        try {
          const peers = await client.listPeers();
          const snapshot: PeerSnapshot[] = peers.map((p: any) => ({
            role: p.role,
            pid: p.pid,
            session_id: p.session_id,
            model: p.model,
            last_heartbeat: p.last_heartbeat ?? Date.now(),
            status: p.status,
          }));
          updateCortexState({ peers: snapshot });
        } catch {
          /* hub puede estar reiniciando, no rompe nada */
        }
      }
    }, 15000);
  });

  // ── session_shutdown: salimos limpio ───────────────────────────────────
  pi.on("session_shutdown", async () => {
    if (peerPollHandle) {
      clearInterval(peerPollHandle);
      peerPollHandle = null;
    }
    if (stateUnsub) {
      stateUnsub();
      stateUnsub = null;
    }
    if (client) await client.stop();
    if (hub) hub.shutdown();
    // F1: limpiar estado de red en el singleton. cortex-cockpit hará
    // su propio reset() en su handler de session_shutdown, pero
    // limpiamos también acá por si el cockpit no está cargado.
    updateCortexState({
      peers: [],
      myRole: null,
      isMaster: false,
      inbound: [],
    });
    registerNetActions(null); // dejamos de exponer acciones de red
  });

  // ── before_agent_start: re-asegura el registro según el singleton ─────
  //
  // El rol del medio lo fija system-select al singleton (campo
  // activeAgentName) cuando el usuario elige un agent con /system, o el
  // flujo `just role-*` lo fuerza vía CORTEX_NET_ROLE. Acá NO decidimos
  // identidad a partir del evento (Pi no la expone — ver comentario abajo);
  // sólo re-aseguramos el registro de forma idempotente como respaldo del
  // subscriber del singleton.
  pi.on("before_agent_start", async (event, ctx) => {
    // Bugfix may 2026: Pi v0.77 NO expone el agent activo en
    // before_agent_start (el tipo BeforeAgentStartEvent no tiene agentName,
    // por lo que (event as any).agentName era SIEMPRE undefined). La fuente
    // de verdad del agent/rol es system-select, que lo escribe al singleton
    // al usar /system; el flujo `just role-*` lo fuerza vía CORTEX_NET_ROLE
    // (resolveRole lo contempla). Derivamos el rol de ahí, no del evento.
    // ensureRegisteredAs es idempotente, así que re-derivar cada turno no
    // cuesta nada y actúa de respaldo del subscriber del singleton.
    lastCtx = ctx;
    const activeAgentName = cortexState.activeAgentName ?? undefined;
    const role = resolveRole(activeAgentName);

    if (role) {
      await ensureRegisteredAs(role, ctx);
    } else if (activeAgentName?.toLowerCase() === "cortex-sync") {
      // Sync explícitamente afuera (B' design). Si estábamos registrados
      // como otro rol (poco probable, pero defensivo), nos damos de baja.
      if (client) {
        try {
          await client.stop();
        } catch {
          /* swallow */
        }
        client = null;
        currentRegisteredRole = null;
        // F1: propagar al singleton — el cockpit muestra
        // "sync (B' anchor — fuera de la red)" cuando myRole es null y
        // activeAgentName es cortex-sync.
        updateCortexState({ myRole: null });
        ctx.ui?.notify(
          "⬢ cortex-net: agent es sync, saliendo de la red (B' anchor)",
          "info"
        );
      }
    }

    // Rediseño may-2026: la entrega de inbounds ya NO se hace acá (inyección
    // al system prompt + auto-reply). Ahora cada inbound se entrega como user
    // message vía pi.sendUserMessage (deliverNextInbound), UNO por turno, y el
    // agente lo ejecuta directo. before_agent_start solo asegura el registro.
  });

  // ── turn_start: marcamos status busy ───────────────────────────────────
  // F3: el cliente avisa al hub que está procesando un turn vía status.
  // Documenter queda en ``observe`` (no rota a busy) porque su rol es
  // mirar la red, no consumirla.
  pi.on("turn_start", async (_event, ctx) => {
    lastCtx = ctx;
    if (!client) return;
    if (client.getStatus() === "observe") return;
    client.setStatus("busy");
  });

  // ── turn_end: volver a idle + avisar si quedan inbounds en cola ─────────
  pi.on("turn_end", async (_event, ctx) => {
    lastCtx = ctx;
    if (!client) return;
    // F3: volver a idle (excepto documenter que mantiene observe).
    if (client.getStatus() !== "observe") {
      client.setStatus("idle");
    }
    // Rediseño may-2026: NO encadenamos solo al siguiente inbound. Si quedan
    // en cola, avisamos y el usuario los libera con /cx-inbox (ventana de
    // revisión: ves lo recién hecho antes de procesar el siguiente).
    const pending = client.inboundCount();
    if (pending > 0) {
      syncInboundSnapshot();
      ctx?.ui?.notify(
        `📨 ${pending} mensaje(s) en cola. Liberá el siguiente con /cx-inbox cuando quieras.`,
        "info"
      );
    }
  });

  // ── Gate de SALIDA: confirmar/editar/bloquear todo mensaje que sale ─────
  // Rediseño may-2026: la comunicación es autónoma (el agente decide qué y a
  // quién) PERO está prohibido enviar sin que el humano lo apruebe. Cada
  // cortex_net_send / cortex_net_broadcast se intercepta acá.
  const NET_MSG_CAP = 1500;
  pi.on("tool_call", async (event, ctx) => {
    lastCtx = ctx;
    const toolName = (event as any).toolName ?? "";
    if (toolName !== "cortex_net_send" && toolName !== "cortex_net_broadcast") {
      return;
    }
    const input = (event as any).input as Record<string, any> | undefined;
    const isBroadcast = toolName === "cortex_net_broadcast";
    const dest = isBroadcast ? "TODOS los peers" : String(input?.to_role ?? "?");
    const type = String(input?.msg_type ?? "?");
    let body = String(input?.body ?? "");

    // Loop Enviar / Editar / No enviar.
    while (true) {
      const over = body.length > NET_MSG_CAP;
      const preview =
        body.length > 600 ? body.slice(0, 600) + "\n…(vista recortada)" : body;
      const title =
        `⬢ El agente quiere ${isBroadcast ? "broadcastear" : `mandar a ${dest}`} (${type}):\n\n` +
        `${preview}\n` +
        (over
          ? `\n⚠ Excede ${NET_MSG_CAP} chars (${body.length}). Conviene recortar (Editar).`
          : "");
      const choice = await ctx.ui.select(title, [
        "✅ Enviar",
        "✏️ Editar",
        "❌ No enviar",
      ]);
      if (choice === undefined || choice.startsWith("❌")) {
        return { block: true, reason: "El usuario rechazó el envío por cortex-net." };
      }
      if (choice.startsWith("✏️")) {
        const edited = await ctx.ui.editor(
          "Editá el mensaje (esto es lo que se va a enviar)",
          body
        );
        if (edited !== undefined) body = edited;
        continue;
      }
      // Enviar: persistimos el body final (posiblemente editado) en event.input.
      if (input) input.body = body;
      return; // permitir la ejecución de la tool
    }
  });

  // ── /cx-inbox: liberar el siguiente mensaje de la cola ──────────────────
  pi.registerCommand("cx-inbox", {
    description: "Procesar el siguiente mensaje entrante de cortex-net (cola)",
    async handler(_args, ctx) {
      lastCtx = ctx;
      if (!client || client.inboundCount() === 0) {
        ctx.ui.notify("No hay mensajes en cola.", "info");
        return;
      }
      if (typeof ctx.isIdle === "function" && !ctx.isIdle()) {
        ctx.ui.notify(
          "El agente está ocupado — esperá a que termine y reintentá.",
          "warning"
        );
        return;
      }
      deliverNextInbound();
    },
  });

  // ── Tools ──────────────────────────────────────────────────────────────

  pi.registerTool({
    name: "cortex_net_list",
    label: "Cortex Net: listar peers",
    description:
      "Lista los agentes Cortex actualmente conectados a la red peer-to-peer. Útil ANTES de mandar un mensaje para saber a quién podés hablarle.",
    parameters: Type.Object({}),
    async execute(_id) {
      if (!client) {
        return {
          content: [
            {
              type: "text" as const,
              text: "cortex-net no activo en este agente.",
            },
          ],
        };
      }
      const peers = await client.listPeers();
      if (peers.length === 0) {
        return {
          content: [
            { type: "text" as const, text: "(sin peers activos en la red)" },
          ],
        };
      }
      const lines = peers.map(
        (p) => `  ${p.role.padEnd(15)} ${p.model.padEnd(40)} pid=${p.pid}`
      );
      return {
        content: [
          {
            type: "text" as const,
            text: `Peers en cortex-net (${peers.length}):\n${lines.join("\n")}`,
          },
        ],
      };
    },
  });

  pi.registerTool({
    name: "cortex_net_send",
    label: "Cortex Net: enviar mensaje",
    description:
      "Envía un mensaje corto a otro agente Cortex. Devuelve un msg_id que podés usar con cortex_net_await para esperar respuesta. NO uses esta tool para responder a un inbound — el output de tu turn es auto-empaquetado como reply. Usá esta tool solo para INICIAR una conversación.",
    parameters: Type.Object({
      to_role: Type.String({
        description:
          "Rol destino: designer, explorer, implementer, security, test-verifier, sddwork, documenter",
      }),
      msg_type: Type.String({
        description:
          "Tipo: question (pido aclaración), proposal (propongo algo), blocker (informo bloqueo), handoff (delego turno), observe (me suscribo silencioso)",
      }),
      body: Type.String({
        description:
          "Cuerpo del mensaje. Corto (<300 palabras). El contrato real (artefactos, decisiones) vive en cortex_session_checkpoint, no acá.",
      }),
    }),
    async execute(_id, params) {
      if (!client) {
        return {
          content: [
            {
              type: "text" as const,
              text: "cortex-net no activo en este agente.",
            },
          ],
        };
      }
      const toRole = params.to_role.toLowerCase() as CortexRole;
      if (!CORTEX_ROLES.includes(toRole)) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Rol "${params.to_role}" no es válido. Roles: ${CORTEX_ROLES.join(", ")}.`,
            },
          ],
        };
      }
      const msgType = params.msg_type.toLowerCase() as MsgType;
      if (!MSG_TYPES.includes(msgType)) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Tipo "${params.msg_type}" no válido. Tipos: ${MSG_TYPES.join(", ")}.`,
            },
          ],
        };
      }

      const result = await client.sendMessage(toRole, msgType, params.body);
      if (!result.ok) {
        return {
          content: [
            {
              type: "text" as const,
              text: `✗ Envío falló: ${result.error}`,
            },
          ],
        };
      }
      return {
        content: [
          {
            type: "text" as const,
            text: `✓ Enviado a "${toRole}" (tipo=${msgType}). msg_id: ${result.msg_id}\nUsá cortex_net_await con este msg_id para esperar respuesta.`,
          },
        ],
      };
    },
  });

  // F3: cortex_net_broadcast ─────────────────────────────────────────────
  // Fanout 1-a-N a todos los peers de la misma sesión. NO espera replies.
  // Útil para anuncios globales: "spec actualizada", "blocker general",
  // "team standup". Si necesitás una sola respuesta agregada, usá
  // cortex_net_send 1:1 al peer correspondiente.
  pi.registerTool({
    name: "cortex_net_broadcast",
    label: "Cortex Net: broadcast a todos los peers",
    description:
      "Envía el mismo mensaje a todos los peers de la sesión actual de una vez (fanout). NO espera respuestas; cada peer lo recibe como inbound y puede contestar individualmente. Devuelve el msg_id (mismo para todos) y la cantidad de entregas. Useful para anuncios, no para preguntas dirigidas.",
    parameters: Type.Object({
      msg_type: Type.String({
        description:
          "Tipo: question (pedido amplio), proposal (propuesta general), blocker (bloqueo a comunicar), observe (notificación pasiva). NO uses handoff con broadcast.",
      }),
      body: Type.String({
        description:
          "Cuerpo del mensaje. Corto (<300 palabras). El contrato real (artefactos, decisiones) vive en cortex_session_checkpoint, no acá.",
      }),
    }),
    async execute(_id, params) {
      if (!client) {
        return {
          content: [
            { type: "text" as const, text: "cortex-net no activo en este agente." },
          ],
        };
      }
      const msgType = params.msg_type.toLowerCase() as MsgType;
      if (!MSG_TYPES.includes(msgType)) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Tipo "${params.msg_type}" no válido. Tipos: ${MSG_TYPES.join(", ")}.`,
            },
          ],
        };
      }
      if (msgType === "handoff") {
        return {
          content: [
            {
              type: "text" as const,
              text:
                "broadcast + handoff no tiene sentido (no podés delegar el turno a N peers). " +
                "Usá cortex_net_send con un destinatario único.",
            },
          ],
        };
      }
      const result = await client.broadcast(msgType, params.body);
      if (!result.ok) {
        return {
          content: [
            { type: "text" as const, text: `✗ Broadcast falló: ${result.error}` },
          ],
        };
      }
      return {
        content: [
          {
            type: "text" as const,
            text:
              `✓ Broadcast (tipo=${msgType}). msg_id: ${result.msg_id} · ` +
              `entregado a ${result.delivered ?? 0} peer(s).`,
          },
        ],
      };
    },
  });

  pi.registerTool({
    name: "cortex_net_get",
    label: "Cortex Net: leer respuesta (no bloquea)",
    description:
      "Lee la respuesta a un msg_id sin bloquear. Devuelve null si todavía no llegó. Útil cuando seguís trabajando y checkeás cada tanto.",
    parameters: Type.Object({
      msg_id: Type.String({ description: "msg_id que devolvió cortex_net_send" }),
    }),
    async execute(_id, params) {
      if (!client) {
        return {
          content: [{ type: "text" as const, text: "cortex-net no activo." }],
        };
      }
      const reply = client.getReply(params.msg_id);
      return {
        content: [
          {
            type: "text" as const,
            text: reply ?? "(sin respuesta todavía)",
          },
        ],
      };
    },
  });

  pi.registerTool({
    name: "cortex_net_await",
    label: "Cortex Net: esperar respuesta",
    description:
      "Bloquea hasta que llegue la respuesta al msg_id (o timeout de 120s por default). Usá esta tool cuando NECESITÁS la respuesta antes de seguir, como en negociación de design o aprobación de security.",
    parameters: Type.Object({
      msg_id: Type.String({ description: "msg_id que devolvió cortex_net_send" }),
      timeout_seconds: Type.Optional(
        Type.Number({
          description: "Timeout en segundos. Default: 120. Max: 600.",
        })
      ),
    }),
    async execute(_id, params) {
      if (!client) {
        return {
          content: [{ type: "text" as const, text: "cortex-net no activo." }],
        };
      }
      const timeout = Math.min(params.timeout_seconds ?? 120, 600) * 1000;
      try {
        const reply = await client.awaitReply(params.msg_id, timeout);
        return { content: [{ type: "text" as const, text: reply }] };
      } catch (err: any) {
        return {
          content: [
            { type: "text" as const, text: `✗ await falló: ${err.message}` },
          ],
        };
      }
    },
  });

  // ── cortex_net_transcript ─────────────────────────────────────────────
  // Tool específica para el documenter al cierre. Lee el transcript log
  // filtrado por session_id actual. Devuelve la conversación que pasó por
  // la red durante el medio, con bodies completos, para que el documenter
  // pueda citar decisiones in-flight en la session note.
  //
  // Esta tool es la que habilita que la red sea FUENTE de documentación
  // (claramente diferenciada del briefing canónico). Si la red nunca
  // estuvo activa o no hay mensajes en la sesión actual, devuelve vacío
  // — el documenter cae al modo canónico (solo briefing).
  pi.registerTool({
    name: "cortex_net_transcript",
    label: "Cortex Net: leer transcript de la sesión",
    description:
      "Devuelve el transcript completo de mensajes peer-to-peer de la sesión actual (filtrado por session_id). Cada entrada incluye msg_id, from_role, to_role, msg_type, body completo y timestamp. Diseñado para que el documenter cite decisiones in-flight en la session note. Si la red nunca se usó o no hay mensajes, devuelve lista vacía — eso NO es error, significa modo canónico (solo briefing). NO uses esta tool fuera del rol documenter; los otros roles vivieron el medio en vivo.",
    parameters: Type.Object({
      max_entries: Type.Optional(
        Type.Number({
          description: "Máximo de entradas a devolver (default: 200, max: 1000). Las más recientes.",
        })
      ),
      filter_msg_types: Type.Optional(
        Type.String({
          description: "Lista comma-separated de msg_types a incluir (ej: 'question,proposal'). Default: todos.",
        })
      ),
    }),
    async execute(_id, params) {
      if (!cachedCwd) {
        return {
          content: [
            { type: "text" as const, text: "cortex-net no inicializado (sin cwd cacheado)." },
          ],
        };
      }
      if (!cachedSessionId) {
        return {
          content: [
            {
              type: "text" as const,
              text: "(sin session_id activo: el transcript no se puede filtrar)",
            },
          ],
        };
      }

      const path = transcriptLogPath(cachedCwd);
      if (!existsSync(path)) {
        return {
          content: [
            {
              type: "text" as const,
              text: "(sin transcript: la red nunca se usó en este workspace, o no hubo mensajes)",
            },
          ],
        };
      }

      const maxEntries = Math.min(params.max_entries ?? 200, 1000);
      const typeFilter = params.filter_msg_types
        ?.split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      let raw: string;
      try {
        raw = readFileSync(path, "utf-8");
      } catch (err: any) {
        return {
          content: [
            { type: "text" as const, text: `✗ Error leyendo transcript: ${err.message}` },
          ],
        };
      }

      const entries: any[] = [];
      for (const line of raw.trim().split("\n")) {
        if (!line.trim()) continue;
        try {
          const e = JSON.parse(line);
          if (e.session_id !== cachedSessionId) continue;
          if (typeFilter && typeFilter.length > 0 && !typeFilter.includes(e.msg_type)) {
            continue;
          }
          entries.push(e);
        } catch {
          /* línea corrupta, ignorar */
        }
      }

      const slice = entries.slice(-maxEntries);

      if (slice.length === 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: `(sin mensajes en transcript para session_id=${cachedSessionId.slice(0, 8)}…)`,
            },
          ],
        };
      }

      // Renderizamos como JSON-array para que el documenter lo parsee fácil.
      // También incluimos un resumen humano-legible al principio.
      const summary = {
        session_id: cachedSessionId,
        total_entries: slice.length,
        by_kind: slice.reduce((acc: any, e) => {
          acc[e.kind] = (acc[e.kind] ?? 0) + 1;
          return acc;
        }, {}),
        by_msg_type: slice.reduce((acc: any, e) => {
          if (e.msg_type) acc[e.msg_type] = (acc[e.msg_type] ?? 0) + 1;
          return acc;
        }, {}),
        roles_involved: [...new Set(slice.flatMap((e) => [e.from_role, e.to_role]))],
      };

      const text =
        `# cortex-net transcript — session ${cachedSessionId}\n\n` +
        `## Resumen\n${JSON.stringify(summary, null, 2)}\n\n` +
        `## Entradas (${slice.length})\n\n` +
        slice
          .map((e, i) => {
            const time = e.ts?.slice(11, 19) ?? "??:??:??";
            const kind = e.kind === "reply" ? `REPLY → ${e.reply_to_msg_id?.slice(0, 8) ?? "?"}` : e.msg_type?.toUpperCase() ?? "SEND";
            return (
              `### [${i + 1}] ${time} · ${e.from_role} → ${e.to_role} · ${kind} · msg_id=${e.msg_id}\n\n` +
              `${e.body ?? "(sin body)"}\n`
            );
          })
          .join("\n---\n\n");

      return { content: [{ type: "text" as const, text }] };
    },
  });

  // ── /cortex-net — diagnóstico completo con TUI ─────────────────────────
  pi.registerCommand("cortex-net", {
    description: "Estado de cortex-net: peers, sesión, rol, audit log",
    async handler(_args, ctx) {
      const lines: string[] = [];
      lines.push("═══ cortex-net status ═══");
      lines.push("");
      lines.push(`Sesión Cortex: ${cachedSessionId ?? "(ninguna activa)"}`);
      lines.push(`Workspace: ${cachedCwd || "(?)"}`);
      lines.push(`Rol propio: ${currentRegisteredRole ?? "(no registrado)"}`);
      lines.push(`Modo hub: ${hub ? "este proceso es el hub" : "cliente de hub externo"}`);
      lines.push("");

      if (!client) {
        lines.push("✗ Cliente no activo.");
        if (!cachedSessionId) {
          lines.push("  → Causa probable: no hay Cortex Session abierta.");
          lines.push("  → Solución: corré cortex-sync para crear una Session.");
        } else {
          lines.push("  → Causa probable: agent activo no mapea a un rol cortex-net.");
          lines.push("  → Solución: cambiá de agent con /system, o forzá rol con /cortex-role.");
        }
        pi.sendMessage({
          customType: "cortex-net",
          content: lines.join("\n"),
          display: true,
        });
        return;
      }

      try {
        const peers = await client.listPeers();
        lines.push(`Peers conectados (${peers.length}):`);
        if (peers.length === 0) {
          lines.push("  (solo vos en la red — los otros agents no se conectaron todavía)");
        } else {
          for (const p of peers) {
            const isMe = p.role === currentRegisteredRole;
            lines.push(
              `  ${isMe ? "→" : " "} ${p.role.padEnd(15)} ${p.model.padEnd(30)} pid=${p.pid}`
            );
          }
        }
      } catch (err: any) {
        lines.push(`✗ Error consultando peers: ${err.message}`);
      }

      // Tail del audit log (últimas 5 líneas)
      try {
        const logPath = auditLogPath(cachedCwd);
        if (existsSync(logPath)) {
          const raw = readFileSync(logPath, "utf-8");
          const auditLines = raw.trim().split("\n").slice(-5);
          if (auditLines.length > 0) {
            lines.push("");
            lines.push(`Audit log (últimas ${auditLines.length} entradas):`);
            for (const line of auditLines) {
              try {
                const e = JSON.parse(line);
                const op = e.op ?? "?";
                const from = e.from ?? e.role ?? "?";
                const to = e.to ? ` → ${e.to}` : "";
                const type = e.msg_type ? ` [${e.msg_type}]` : "";
                lines.push(`  ${e.ts?.slice(11, 19) ?? "??:??:??"}  ${op.padEnd(12)} ${from}${to}${type}`);
              } catch {
                lines.push(`  ${line.slice(0, 100)}`);
              }
            }
          }
        }
      } catch {
        /* ignore audit log errors */
      }

      pi.sendMessage({
        customType: "cortex-net",
        content: lines.join("\n"),
        display: true,
      });
    },
  });

  // ── /cortex-mode — TUI selector de modo de operación ───────────────────
  // Handler compartido por /cortex-mode y su alias corto /cx-mode
  // (co-registrado abajo: Pi no permite invocar comandos programáticamente,
  // así que el alias apunta al MISMO handler para que SÍ ejecute).
  async function cortexModeHandler(_args: string, ctx: any) {
      const currentMode = client ? "Full (red activa)" : "Solo (sin red)";

      const choice = await ctx.ui.select(
        `Modo actual: ${currentMode}. Elegí el nuevo modo:`,
        [
          "Full · cortex-net activo (Deep Track con peers)",
          "Solo · sin red (Fast Track, BYO, hotfix)",
          "Cancelar",
        ]
      );

      if (!choice || choice === "Cancelar") {
        ctx.ui.notify("Modo sin cambios", "info");
        return;
      }

      if (choice.startsWith("Full")) {
        if (client) {
          ctx.ui.notify("Ya estás en modo Full", "info");
          return;
        }
        // Reintentamos arrancar la red. Si no hay sesión, avisamos.
        cachedSessionId = resolveSessionId(cachedCwd);
        if (!cachedSessionId) {
          ctx.ui.notify(
            "✗ No hay Cortex Session activa. Corré cortex-sync primero.",
            "warning"
          );
          return;
        }
        if (!hub) {
          hub = await CortexNetHub.tryStart(cachedCwd);
        }
        const role = resolveRole();
        if (role) {
          await ensureRegisteredAs(role, ctx);
          ctx.ui.notify(`⬢ Modo Full activado · rol "${role}"`, "success");
        } else {
          ctx.ui.notify(
            "⬢ Hub levantado · esperando primer agent activo para registrarte",
            "info"
          );
        }
      } else if (choice.startsWith("Solo")) {
        // Desactivamos el cliente y opcionalmente el hub
        if (client) {
          try {
            await client.stop();
          } catch {
            /* swallow */
          }
          client = null;
          currentRegisteredRole = null;
        }
        // 2b: propagar la baja al singleton para que el cockpit/panel no
        // muestren rol/peers fantasma.
        updateCortexState({ myRole: null, peers: [] });
        // El hub lo dejamos vivo: otras Pi en otras terminales podrían
        // estar usándolo. Solo cerramos NUESTRO cliente. Si vos sos el
        // hub y querés cerrarlo del todo, usá /cortex-net-shutdown.
        ctx.ui.notify("⬢ Modo Solo activado · cortex-net desconectado", "success");
      }
  }
  pi.registerCommand("cortex-mode", {
    description: "Cambiar modo de operación de cortex-net (Full / Solo)",
    handler: cortexModeHandler,
  });
  pi.registerCommand("cx-mode", {
    description: "Alias de /cortex-mode (Full / Solo)",
    handler: cortexModeHandler,
  });

  // ── /cortex-role — TUI selector para forzar rol ────────────────────────
  // Handler compartido por /cortex-role y su alias corto /cx-role.
  async function cortexRoleHandler(_args: string, ctx: any) {
      const currentLabel = currentRegisteredRole
        ? `Actual: ${currentRegisteredRole}`
        : "Sin rol asignado";

      const choices = [
        ...CORTEX_ROLES.map((r) => `${r} ${r === currentRegisteredRole ? "✓" : ""}`),
        "Auto (inferir del agent activo)",
        "Cancelar",
      ];

      const choice = await ctx.ui.select(
        `${currentLabel}. Elegí el rol:`,
        choices
      );

      if (!choice || choice === "Cancelar") {
        ctx.ui.notify("Rol sin cambios", "info");
        return;
      }

      if (choice.startsWith("Auto")) {
        // Limpiamos override y volvemos al modo hook-driven
        // (la próxima before_agent_start va a inferir solo)
        delete process.env.CORTEX_NET_ROLE;
        if (client) {
          try {
            await client.stop();
          } catch {
            /* swallow */
          }
          client = null;
          currentRegisteredRole = null;
        }
        // 2b: propagar la baja al singleton (cockpit/panel).
        updateCortexState({ myRole: null, peers: [] });
        ctx.ui.notify(
          "⬢ Modo auto · rol se infiere del agent activo en cada turno",
          "success"
        );
        return;
      }

      // Extraemos el rol del label "rolname ✓" → "rolname"
      const role = choice.split(" ")[0] as CortexRole;
      if (!CORTEX_ROLES.includes(role)) {
        ctx.ui.notify(`Rol inválido: ${role}`, "warning");
        return;
      }

      // Seteamos override y re-registramos
      process.env.CORTEX_NET_ROLE = role;
      await ensureRegisteredAs(role, ctx);
  }
  pi.registerCommand("cortex-role", {
    description: "Forzar rol cortex-net (escape hatch para multi-terminal)",
    handler: cortexRoleHandler,
  });
  pi.registerCommand("cx-role", {
    description: "Alias de /cortex-role (forzar rol)",
    handler: cortexRoleHandler,
  });

  // ── /cortex-net-shutdown — cierre limpio del hub si vos lo levantaste ──
  pi.registerCommand("cortex-net-shutdown", {
    description: "Cerrar el hub cortex-net (si este proceso lo levantó)",
    async handler(_args, ctx) {
      if (!hub) {
        ctx.ui.notify(
          "Este proceso no es el hub. Otro Pi tiene el hub levantado.",
          "info"
        );
        return;
      }
      const confirmed = await ctx.ui.confirm(
        "Cerrar hub cortex-net",
        "Esto desconecta a TODOS los peers en este workspace. ¿Continuar?"
      );
      if (!confirmed) return;

      if (client) {
        try {
          await client.stop();
        } catch {
          /* swallow */
        }
        client = null;
        currentRegisteredRole = null;
      }
      hub.shutdown();
      hub = null;
      // 2b: salimos del todo de la red → limpiar el singleton.
      updateCortexState({ myRole: null, isMaster: false, peers: [] });
      ctx.ui.notify("⬢ Hub cerrado · workspace sin red hasta nuevo session_start", "success");
    },
  });
}
