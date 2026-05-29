/**
 * cortex-panel.ts — Panel de control on-demand de Cortex Pi 2.5+net
 *
 * F4 del overhaul UX (ver docs/multi-ide-mcp-hardening/PI-COCKPIT-UX/).
 *
 * Registra el slash command ``/cortex`` que abre una TUI modal grande
 * con todas las acciones disponibles. Reemplaza la necesidad de
 * recordar los comandos sueltos ``/cortex-net``, ``/cortex-mode``,
 * ``/cortex-role``, ``/cortex-net-shutdown`` (que siguen existiendo
 * como aliases por compatibilidad).
 *
 * Dos vistas según ``cortexState.isMaster``:
 *
 *   - MASTER (este proceso levantó el hub):
 *       acciones completas incluidas las "destructivas" como
 *       abandonar sesión o agregar peers al team.
 *
 *   - WORKER (cliente de un hub externo):
 *       vista limitada — mandar mensajes, ver transcript, cambiar
 *       rol propio, salir de la red. Las acciones de master no
 *       aparecen en el SelectList.
 *
 * Decisión: el panel NO duplica la lógica de los slash commands de
 * cortex-net (cambio de modo, cambio de rol, etc.). Cuando una acción
 * mapea a un comando ya existente, el panel cierra y muestra un
 * ``notify`` con la instrucción. Esto evita drift entre dos
 * implementaciones de la misma acción.
 *
 * Las acciones "complejas" (mandar mensaje) sí se manejan acá usando
 * ``ctx.ui.select`` en cascada — más simple que duplicar como tools.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
// Bugfix mayo 2026: import desde .pi/lib/ (ver cortex-cockpit.ts y
// docs/multi-ide-mcp-hardening/PI-COCKPIT-UX/README.md § 8).
import {
  cortexState,
  CORTEX_ROLES,
  type CortexRole,
} from "../lib/cortex-state";

// ── Tipos de acciones ──────────────────────────────────────────────────────

type Action =
  | "send_message"
  | "broadcast"
  | "team_spawn"       // F5 — placeholder hasta F5
  | "switch_documenter"
  | "abandon_session"
  | "change_mode"
  | "change_role"
  | "view_transcript"
  | "view_audit"
  | "view_status"
  | "leave_network"
  | "close";

interface ActionItem {
  id: Action;
  label: string;
  masterOnly: boolean;
  /** Si está pendiente de otra fase, mostrar el flag al lado del label. */
  pendingFeature?: string;
}

const ACTIONS: ActionItem[] = [
  { id: "send_message", label: "Mandar mensaje a un peer", masterOnly: false },
  { id: "broadcast", label: "Broadcast a todos los peers", masterOnly: false },
  {
    id: "team_spawn",
    label: "Agregar peers al team (auto-spawn de terminales)",
    masterOnly: true,
  },
  {
    id: "switch_documenter",
    label: "Cambiar a documenter (preparar cierre)",
    masterOnly: true,
  },
  { id: "view_transcript", label: "Ver transcript completo", masterOnly: false },
  { id: "view_audit", label: "Audit log de la red", masterOnly: true },
  { id: "view_status", label: "Status de la red (peers + sesión)", masterOnly: false },
  { id: "change_mode", label: "Cambiar modo (Full / Solo)", masterOnly: true },
  { id: "change_role", label: "Cambiar de rol propio", masterOnly: false },
  {
    id: "abandon_session",
    label: "Cerrar sesión sin documenter (abandonar)",
    masterOnly: true,
  },
  {
    id: "leave_network",
    label: "Salir de la red (este proceso)",
    masterOnly: false,
  },
];

function filterActions(): ActionItem[] {
  return ACTIONS.filter((a) => !a.masterOnly || cortexState.isMaster);
}

// ── Component custom del panel ─────────────────────────────────────────────

/**
 * Component custom que maneja navegación con flechas y selección con
 * enter. Cierra con esc retornando null (cancelado).
 *
 * Pi pasa input crudo (raw escape sequences) a handleInput; nuestro
 * matching cubre los layouts más comunes (xterm). Si una key específica
 * no se reconoce, el handler la ignora silenciosamente (no rompe el
 * panel).
 */
class CortexPanelComponent {
  private focusedIdx = 0;
  private actions: ActionItem[];

  constructor(
    private theme: any,
    private done: (action: Action | null) => void
  ) {
    this.actions = filterActions();
  }

  render(width: number): string[] {
    const lines: string[] = [];
    // Tope inferior 40 para terminales angostas; superior 120 para no
    // verse ridículo en monitores anchos.
    const W = Math.max(40, Math.min(width || 80, 120));

    // ── Header ────────────────────────────────────────────────────────
    const mode = cortexState.isMaster
      ? this.theme.fg("accent", "MASTER")
      : this.theme.fg("muted", "WORKER");
    lines.push(
      this.theme.fg("accent", "⬡ CORTEX · PANEL ") +
        this.theme.fg("dim", "· ") +
        mode
    );

    if (cortexState.sessionId) {
      lines.push(
        this.theme.fg("dim", "Sesión: ") +
          this.theme.fg("text", cortexState.sessionId) +
          this.theme.fg("dim", " · rol propio: ") +
          this.theme.fg("text", cortexState.myRole ?? "(ninguno)")
      );
    } else {
      lines.push(
        this.theme.fg(
          "muted",
          "Sin Cortex Session activa — el panel ofrece acciones limitadas"
        )
      );
    }
    lines.push("");

    // ── Acciones ─────────────────────────────────────────────────────
    lines.push(this.theme.fg("dim", "Acciones disponibles:"));
    this.actions.forEach((a, i) => {
      const isFocus = i === this.focusedIdx;
      const cursor = isFocus
        ? this.theme.fg("accent", "▶ ")
        : "  ";
      const label = isFocus
        ? this.theme.fg("accent", a.label)
        : this.theme.fg("text", a.label);
      const pending = a.pendingFeature
        ? this.theme.fg("warning", ` [${a.pendingFeature} pendiente]`)
        : "";
      const master =
        a.masterOnly && cortexState.isMaster
          ? this.theme.fg("dim", " ★master")
          : "";
      lines.push(`  ${cursor}${label}${pending}${master}`);
    });

    if (this.actions.length === 0) {
      lines.push(this.theme.fg("muted", "  (no hay acciones disponibles)"));
    }

    lines.push("");

    // ── Peers (read-only) ────────────────────────────────────────────
    if (cortexState.peers.length > 0) {
      lines.push(
        this.theme.fg(
          "dim",
          `Peers en la red (${cortexState.peers.length}):`
        )
      );
      for (const p of cortexState.peers) {
        const isMe = p.role === cortexState.myRole;
        const arrow = isMe
          ? this.theme.fg("accent", "→ ")
          : "  ";
        const statusColor =
          p.status === "idle"
            ? "success"
            : p.status === "busy"
            ? "warning"
            : p.status === "observe"
            ? "accent"
            : "muted";
        lines.push(
          `  ${arrow}` +
            this.theme.fg("text", p.role.padEnd(15)) +
            this.theme.fg(statusColor, p.status ?? "?")
        );
      }
    } else {
      lines.push(this.theme.fg("muted", "(sin peers conectados)"));
    }

    lines.push("");

    // ── Footer ───────────────────────────────────────────────────────
    lines.push(
      this.theme.fg(
        "dim",
        "↑↓ navegar  ·  enter ejecutar  ·  esc cerrar"
      )
    );

    // Truncamos cada línea al width disponible. Pi crashea con
    // uncaughtException si alguna línea excede el ancho de la
    // terminal. truncateToWidth preserva los ANSI escape codes.
    return lines.map((l) =>
      visibleWidth(l) > W ? truncateToWidth(l, W) : l
    );
  }

  handleInput(data: string): void {
    // Esc: cierra el panel cancelando.
    if (data === "\x1b" || data === "escape") {
      this.done(null);
      return;
    }
    // Flecha arriba: \x1b[A (xterm)
    if (data === "\x1b[A" || data === "up") {
      this.focusedIdx =
        (this.focusedIdx - 1 + this.actions.length) % this.actions.length;
      return;
    }
    // Flecha abajo: \x1b[B
    if (data === "\x1b[B" || data === "down") {
      this.focusedIdx = (this.focusedIdx + 1) % this.actions.length;
      return;
    }
    // Enter: ejecuta acción seleccionada.
    if (data === "\r" || data === "\n" || data === "enter") {
      if (this.actions.length === 0) {
        this.done(null);
        return;
      }
      this.done(this.actions[this.focusedIdx].id);
      return;
    }
    // Cualquier otro input se ignora silenciosamente.
  }

  invalidate(): void {
    /* render es puro sobre estado mutado externamente; nada que invalidar acá */
  }
}

// ── Sub-flows (acciones complejas) ─────────────────────────────────────────

/**
 * Cascada de prompts para mandar un mensaje 1:1 a un peer.
 *
 * Si no hay peers conectados, el flow corta con notify. Si el usuario
 * cancela cualquier paso (esc en select), tampoco se manda nada.
 *
 * No invoca la tool MCP cortex_net_send directamente — sería duplicar
 * lógica que ya vive en cortex-net.ts. En su lugar imprime el comando
 * tool-ready que el agent debería invocar.
 */
async function sendMessageFlow(ctx: any): Promise<void> {
  if (cortexState.peers.length === 0) {
    ctx.ui.notify(
      "No hay peers conectados a quien mandarle. Abrí otra terminal con `just role-*` primero.",
      "warning"
    );
    return;
  }

  // 1. Destinatario
  const peerOptions = cortexState.peers.map(
    (p) =>
      `${p.role}  (${p.status ?? "?"}${
        p.role === cortexState.myRole ? " · vos mismo" : ""
      })`
  );
  const peer = await ctx.ui.select(
    "Destinatario:",
    peerOptions
  );
  if (peer === undefined) return;
  const toRole = peer.split(/\s+/)[0] as CortexRole;
  if (toRole === cortexState.myRole) {
    ctx.ui.notify("No tiene sentido mandarte un mensaje a vos mismo.", "warning");
    return;
  }

  // 2. Tipo
  const msgType = await ctx.ui.select(
    "Tipo de mensaje:",
    [
      "question  — pido aclaración",
      "proposal  — propongo algo, espero accept/reject",
      "blocker   — informo bloqueo (no espera reply)",
      "handoff   — delego turno explícitamente",
    ]
  );
  if (msgType === undefined) return;
  const typeKey = msgType.split(/\s+/)[0];

  // 3. Mensaje
  ctx.ui.notify(
    `Para enviar, tu agent debe invocar:\n` +
      `  cortex_net_send(to_role="${toRole}", msg_type="${typeKey}", body="<tu mensaje>")\n` +
      `(F4 todavía no invoca tools directamente; eso requeriría API pi.execTool no documentada.)`,
    "info"
  );
}

/**
 * Cascada para broadcast a todos los peers. Igual que sendMessageFlow
 * pero salta el paso "destinatario".
 */
async function broadcastFlow(ctx: any): Promise<void> {
  if (cortexState.peers.length === 0) {
    ctx.ui.notify(
      "No hay peers conectados a quien broadcastear. El broadcast iría a 0 destinatarios.",
      "warning"
    );
    return;
  }

  const msgType = await ctx.ui.select(
    "Tipo de mensaje (broadcast):",
    [
      "question  — pedido amplio",
      "proposal  — propuesta general",
      "blocker   — bloqueo a comunicar",
      "observe   — notificación pasiva",
    ]
  );
  if (msgType === undefined) return;
  const typeKey = msgType.split(/\s+/)[0];

  ctx.ui.notify(
    `Para broadcast a ${cortexState.peers.length} peer(s), tu agent debe invocar:\n` +
      `  cortex_net_broadcast(msg_type="${typeKey}", body="<tu mensaje>")`,
    "info"
  );
}

async function abandonSession(ctx: any): Promise<void> {
  const confirmed = await ctx.ui.confirm(
    "Abandonar sesión",
    "Esto la cierra sin documenter. La memoria organizacional pierde el cierre con criterio editorial. ¿Continuar?"
  );
  if (!confirmed) return;
  ctx.ui.notify(
    'Tu agent debe invocar: cortex_close_session(status="abandoned", session_note_path=null, adrs_created=[])',
    "warning"
  );
}

// ── Extension ──────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  pi.registerCommand("cortex", {
    description:
      "Panel de control de Cortex Pi 2.5+net (sesión, peers, acciones)",
    async handler(_args: string, ctx: any) {
      // Abrir panel modal. ctx.ui.custom devuelve la promesa que
      // resuelve cuando el Component llama done(action | null).
      const selected = await ctx.ui.custom<Action | null>(
        (_tui: any, theme: any, _kb: any, done: (v: Action | null) => void) => {
          return new CortexPanelComponent(theme, done);
        }
      );

      if (selected === null || selected === "close") return;

      // Despacho de acciones. Las que mapean a slash commands ya
      // implementados en cortex-net.ts emiten notify con la instrucción
      // (no duplicamos lógica).
      switch (selected) {
        case "send_message":
          await sendMessageFlow(ctx);
          break;

        case "broadcast":
          await broadcastFlow(ctx);
          break;

        case "view_transcript":
          ctx.ui.notify(
            cortexState.myRole === "documenter"
              ? "Como documenter, invocá la tool cortex_net_transcript para leer el transcript filtrado por session_id."
              : "El transcript completo lo lee el documenter al cierre. Para ver el log crudo: `cat .pi/agent-sessions/cortex-net-transcript.log`",
            "info"
          );
          break;

        case "view_audit":
          ctx.ui.notify(
            "Tipeá /cortex-net para ver status + audit log (últimas 5 entradas).",
            "info"
          );
          break;

        case "view_status":
          ctx.ui.notify(
            `Sesión: ${cortexState.sessionId ?? "(ninguna)"} · ` +
              `Rol: ${cortexState.myRole ?? "(ninguno)"} · ` +
              `Master: ${cortexState.isMaster ? "sí" : "no"} · ` +
              `Peers: ${cortexState.peers.length}`,
            "info"
          );
          break;

        case "change_mode":
          ctx.ui.notify(
            "Tipeá /cortex-mode para cambiar entre Full (red activa) y Solo (sin red).",
            "info"
          );
          break;

        case "change_role":
          ctx.ui.notify(
            "Tipeá /cortex-role para forzar un rol específico o volver a modo Auto.",
            "info"
          );
          break;

        case "switch_documenter":
          ctx.ui.notify(
            "Tipeá /system y elegí cortex-documenter para preparar el cierre con criterio editorial.",
            "info"
          );
          break;

        case "abandon_session":
          await abandonSession(ctx);
          break;

        case "team_spawn":
          ctx.ui.notify(
            "Tipeá /cortex-team para abrir el spawner de terminales (auto-detecta " +
              "Windows Terminal / tmux / iTerm / etc., con fallback a clipboard).",
            "info"
          );
          break;

        case "leave_network":
          ctx.ui.notify(
            "Para salir de la red: cerrá Pi con Ctrl+D (te desregistrás limpio). " +
              "O usá /cortex-mode → Solo si solo querés desconectar este cliente del hub.",
            "info"
          );
          break;
      }
    },
  });
}
