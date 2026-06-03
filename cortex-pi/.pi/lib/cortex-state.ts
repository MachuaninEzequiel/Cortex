/**
 * cortex-state.ts — Singleton de estado compartido entre extensiones Cortex
 *
 * Bugfix mayo 2026: este archivo VIVÍA antes en
 * ``.pi/extensions/_cortex-state.ts``, pero Pi v0.77 autoloadea TODO lo
 * que está en ``.pi/extensions/`` sin importar el prefijo del nombre.
 * Eso provocaba **dos instancias** del módulo:
 *
 *   - Camino A: Pi carga ``_cortex-state.ts`` como extension (autoload).
 *   - Camino B: las otras extensiones lo importan con ``./_cortex-state``.
 *
 * Y bun/jiti resolvía cada camino a un módulo distinto, así que cada
 * uno tenía su propio ``cortexState`` y los updates de una extension no
 * se veían en otra. Síntoma típico: cortex-net dice "registrado como
 * sddwork (hub)" pero el cockpit muestra "STANDBY".
 *
 * Moviendo el archivo a ``.pi/lib/`` Pi NO lo autoloadea (solo escanea
 * ``.pi/extensions/``), y las extensions lo importan con
 * ``../lib/cortex-state``. Una sola ruta resuelta, una sola instancia.
 *
 * Patrón de uso (sin cambios):
 *
 *   // Lector (cockpit, panel)
 *   import { cortexState, subscribe } from "../lib/cortex-state";
 *   const unsub = subscribe(() => redrawWidget());
 *
 *   // Escritor (cortex-net cuando cambia el state de la red)
 *   import { cortexState, update } from "../lib/cortex-state";
 *   update({ peers: newPeers });
 */

// ── Tipos compartidos ──────────────────────────────────────────────────────

/**
 * Roles canónicos en el ecosistema Cortex Pi 2.5+net.
 *
 * Importante: ``cortex-sync`` NO está en esta lista. Por diseño B', el
 * anchor de sincronización vive afuera de la red (es secuencial y se
 * ejecuta antes de que cualquier otro rol entre a cortex-net).
 *
 * Mantener alineado con ``CORTEX_ROLES`` en cortex-net.ts.
 */
export type CortexRole =
  | "sddwork"
  | "designer"
  | "explorer"
  | "implementer"
  | "security"
  | "test-verifier"
  | "documenter";

export const CORTEX_ROLES: readonly CortexRole[] = [
  "sddwork",
  "designer",
  "explorer",
  "implementer",
  "security",
  "test-verifier",
  "documenter",
] as const;

/**
 * Mapa fijo de nombres canónicos de agents → roles cortex-net.
 *
 * ``cortex-sync`` se ausentó a propósito (B' anchor). Si el agent activo
 * de Pi es cortex-sync, ``resolveRoleFromAgentName`` devuelve null.
 *
 * Mantener alineado con ``AGENT_TO_ROLE`` en cortex-net.ts.
 */
export const AGENT_TO_ROLE: Record<string, CortexRole> = {
  "cortex-sddwork": "sddwork",
  "cortex-code-designer": "designer",
  "cortex-code-explorer": "explorer",
  "cortex-code-implementer": "implementer",
  "cortex-security-auditor": "security",
  "cortex-test-verifier": "test-verifier",
  "cortex-documenter": "documenter",
};

/**
 * Mapa inverso rol → nombre canónico del agent (tal cual el ``name:`` del
 * frontmatter en ``.pi/agents/``). Lo usa cortex-team para decirle a la
 * terminal hija qué persona activar (env ``CORTEX_AGENT``), así el peer
 * spawneado no solo tiene el rol de red sino la persona Pi correcta.
 *
 * Mantener alineado con AGENT_TO_ROLE (es su inverso).
 */
export const ROLE_TO_AGENT: Record<CortexRole, string> = {
  sddwork: "cortex-SDDwork",
  designer: "cortex-code-designer",
  explorer: "cortex-code-explorer",
  implementer: "cortex-code-implementer",
  security: "cortex-security-auditor",
  "test-verifier": "cortex-test-verifier",
  documenter: "cortex-documenter",
};

/** Nombre canónico del agent para un rol cortex-net. */
export function agentForRole(role: CortexRole): string {
  return ROLE_TO_AGENT[role];
}

/**
 * Snapshot mínimo de un peer en la red, replicado desde cortex-net para
 * que el cockpit no tenga que abrir socket al hub solo para mostrar la
 * lista. Mantener alineado con ``Peer`` en cortex-net.ts.
 */
export interface PeerSnapshot {
  role: CortexRole;
  pid: number;
  session_id: string;
  model: string;
  last_heartbeat: number;
  status?: "idle" | "busy" | "observe"; // poblado en F3
}

/**
 * Entrada del transcript que el cockpit muestra como "tráfico reciente".
 * Subset del JSON serializado en ``cortex-net-transcript.log``.
 */
export interface TranscriptSnapshot {
  ts: string;
  kind: "send" | "reply";
  msg_id: string;
  from_role: CortexRole;
  to_role: CortexRole;
  msg_type: string;
  body: string;
  reply_to_msg_id?: string | null;
}

/**
 * Próxima acción sugerida que el cockpit muestra como hint.
 */
export interface Suggestion {
  label: string;
  hotkey: string | null;
  reason: string;
}

/**
 * Snapshot de un mensaje entrante encolado (cortex-net). El cockpit lo usa
 * para mostrar "📨 N en cola". La cola REAL (con el body completo y el orden
 * FIFO) vive en cortex-net.ts; esto es solo visibilidad.
 */
export interface InboundSnapshot {
  from: CortexRole;
  type: string;
  preview: string;
}

/**
 * Snapshot completo del estado Cortex en este proceso Pi.
 *
 * Convenciones:
 *
 *   - ``sessionId === null`` → no hay Cortex Session activa (standby).
 *   - ``myRole === null`` → el agent activo no participa de la red
 *     (cortex-sync, o agent desconocido).
 *   - ``isMaster === true`` → este proceso levantó el hub.
 *   - Todos los timestamps son epoch ms (Date.now()) salvo
 *     ``TranscriptSnapshot.ts`` que es ISO string heredado del log.
 */
export interface CortexState {
  // Workspace
  cwd: string | null;

  // Session
  sessionId: string | null;
  sessionOpenedAt: number | null;

  // Self
  activeAgentName: string | null;
  myRole: CortexRole | null;
  isMaster: boolean;
  myModel: string | null;

  // Network
  peers: PeerSnapshot[];
  recentTraffic: TranscriptSnapshot[];
  // Cola de mensajes entrantes pendientes (visibilidad; la cola real, con
  // body completo, vive en cortex-net.ts).
  inbound: InboundSnapshot[];

  // Workflow guidance
  suggestion: Suggestion | null;

  // Última actualización
  lastUpdate: number;
}

// ── Anclaje a globalThis ────────────────────────────────────────────────────
//
// Bugfix CRÍTICO mayo 2026: el loader TS de Pi v0.77 (bun/jiti) parece
// evaluar este módulo **una vez por extension que lo importa**, dando
// como resultado N copias separadas del state. El paso anterior fue
// moverlo de ``.pi/extensions/`` a ``.pi/lib/`` para sacarlo del
// autoload — eso eliminó UNA fuente de duplicación pero NO la que
// genera el sandboxing por-extension del loader.
//
// La solución universalmente robusta es anclar el state a
// ``globalThis``: es UNA sola referencia por proceso Node.js, no
// depende de cómo el loader trate cada módulo. Cada copia del módulo
// que se cargue va a apuntar al MISMO objeto en globalThis.
//
// Síntoma típico cuando este fix no está: cortex-net dice "registrado
// como sddwork (hub)" pero cortex-cockpit muestra "STANDBY ·
// (no en la red)". Son dos vistas del mismo `cortexState` que en
// realidad son objetos distintos.

const GLOBAL_KEY = "__cortex_pi_state_v1__";

/**
 * Acciones de red que ``cortex-net.ts`` publica al cargar, para que otras
 * extensiones (p.ej. el panel ``/cortex``) puedan EJECUTAR de verdad
 * —sin LLM— sin depender de invocar slash commands ni tools (Pi v0.77 no
 * expone ninguna API para eso). cortex-net registra esto en su factory; el
 * panel lo obtiene con ``getNetActions()``. Es ``null`` mientras cortex-net
 * no esté cargado/listo.
 */
export interface NetActions {
  /** ¿Hay cliente conectado al hub ahora mismo? */
  isReady(): boolean;
  /** Lista los peers actuales (vacío si no hay cliente). */
  listPeers(): Promise<PeerSnapshot[]>;
  /** Manda un mensaje 1:1 a un peer. */
  send(
    toRole: CortexRole,
    msgType: string,
    body: string
  ): Promise<{ ok: boolean; error?: string }>;
  /** Broadcast a todos los peers de la sesión. */
  broadcast(
    msgType: string,
    body: string
  ): Promise<{ ok: boolean; delivered?: number; error?: string }>;
}

/**
 * Acción de spawn de team que ``cortex-team.ts`` publica al cargar, para
 * que el panel ``/cortex`` pueda abrir el spawner real (selector de presets
 * + apertura de terminales) en vez de mostrar un hint. ``null`` si
 * cortex-team no está cargado.
 */
export interface TeamActions {
  /** Abre el selector de presets y spawnea las terminales elegidas. */
  spawn(ctx: any): Promise<void>;
}

interface GlobalAnchor {
  state: CortexState;
  subscribers: Set<Listener>;
  netActions: NetActions | null;
  teamActions: TeamActions | null;
}

type Listener = () => void;

function getAnchor(): GlobalAnchor {
  const g = globalThis as unknown as Record<string, GlobalAnchor>;
  if (!g[GLOBAL_KEY]) {
    g[GLOBAL_KEY] = {
      state: {
        cwd: null,
        sessionId: null,
        sessionOpenedAt: null,
        activeAgentName: null,
        myRole: null,
        isMaster: false,
        myModel: null,
        peers: [],
        recentTraffic: [],
        inbound: [],
        suggestion: null,
        lastUpdate: Date.now(),
      },
      subscribers: new Set<Listener>(),
      netActions: null,
      teamActions: null,
    };
  }
  return g[GLOBAL_KEY];
}

const anchor = getAnchor();

/**
 * Snapshot reactivo del estado Cortex. Es UNA misma referencia por
 * proceso Pi, anclada a ``globalThis``. Si lo mutás directamente, los
 * suscriptores NO se enteran — usá ``update(...)``.
 */
export const cortexState: CortexState = anchor.state;

const subscribers: Set<Listener> = anchor.subscribers;

// ── Registro de acciones de red (lo publica cortex-net) ─────────────────────

/** cortex-net publica sus acciones acá al cargar. Pasar null para limpiar. */
export function registerNetActions(actions: NetActions | null): void {
  anchor.netActions = actions;
}

/** El panel (u otra extensión) obtiene las acciones de red, o null si cortex-net no está. */
export function getNetActions(): NetActions | null {
  return anchor.netActions;
}

/** cortex-team publica su acción de spawn acá al cargar. */
export function registerTeamActions(actions: TeamActions | null): void {
  anchor.teamActions = actions;
}

/** El panel obtiene la acción de spawn de team, o null si cortex-team no está. */
export function getTeamActions(): TeamActions | null {
  return anchor.teamActions;
}

// ── Pub/sub ─────────────────────────────────────────────────────────────────

/**
 * Suscribe ``fn`` a cambios del estado. Devuelve la función de
 * desuscripción — llamala en ``session_shutdown`` o cuando ya no
 * necesites el callback.
 */
export function subscribe(fn: Listener): () => void {
  subscribers.add(fn);
  return () => subscribers.delete(fn);
}

/**
 * Mutación atómica del estado. Aplica el patch, actualiza ``lastUpdate``
 * y notifica a todos los suscriptores. Los suscriptores se ejecutan
 * sincrónicamente; si uno tira, los demás se ejecutan igual.
 */
export function update(patch: Partial<CortexState>): void {
  Object.assign(cortexState, patch);
  cortexState.lastUpdate = Date.now();
  for (const fn of subscribers) {
    try {
      fn();
    } catch {
      /* listener buggy — no rompe a los demás */
    }
  }
}

/**
 * Reset completo. Lo usa cortex-cockpit en ``session_shutdown`` para que
 * un próximo session_start arranque limpio.
 */
export function reset(): void {
  Object.assign(cortexState, {
    cwd: null,
    sessionId: null,
    sessionOpenedAt: null,
    activeAgentName: null,
    myRole: null,
    isMaster: false,
    myModel: null,
    peers: [],
    recentTraffic: [],
    inbound: [],
    suggestion: null,
    lastUpdate: Date.now(),
  });
  for (const fn of subscribers) {
    try {
      fn();
    } catch {
      /* idem */
    }
  }
}

// ── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Deriva el rol cortex-net del nombre canónico del agent. Devuelve null
 * para cortex-sync (afuera de la red por diseño) o agents desconocidos.
 */
export function resolveRoleFromAgentName(
  agentName: string | undefined | null
): CortexRole | null {
  if (!agentName) return null;
  const normalized = agentName.trim().toLowerCase();
  if (normalized === "cortex-sync") return null;
  return AGENT_TO_ROLE[normalized] ?? null;
}
