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
import { existsSync, readFileSync } from "fs";
import { join } from "path";
// Bugfix mayo 2026: import desde .pi/lib/ (ver cortex-cockpit.ts y
// docs/multi-ide-mcp-hardening/PI-COCKPIT-UX/README.md § 8).
import {
  cortexState,
  CORTEX_ROLES,
  getNetActions,
  getTeamActions,
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
 * Cascada para mandar un mensaje 1:1 a un peer y enviarlo DE VERDAD —sin
 * LLM— vía el registro de acciones de red que publica cortex-net. Si el
 * usuario cancela cualquier paso, no se manda nada.
 */
async function sendMessageFlow(ctx: any): Promise<void> {
  const net = getNetActions();
  if (!net || !net.isReady()) {
    ctx.ui.notify(
      "cortex-net no está conectado en este proceso (¿estás en standby o en cortex-sync?).",
      "warning"
    );
    return;
  }

  // 1. Destinatario (excluyendo a uno mismo)
  const peerOptions = cortexState.peers
    .filter((p) => p.role !== cortexState.myRole)
    .map((p) => `${p.role}  (${p.status ?? "?"})`);
  if (peerOptions.length === 0) {
    ctx.ui.notify(
      "No hay otros peers conectados. Abrí el team con /cortex-team primero.",
      "warning"
    );
    return;
  }
  const peer = await ctx.ui.select("Destinatario:", peerOptions);
  if (peer === undefined) return;
  const toRole = peer.split(/\s+/)[0] as CortexRole;

  // 2. Tipo
  const msgType = await ctx.ui.select("Tipo de mensaje:", [
    "question  — pido aclaración",
    "proposal  — propongo algo, espero accept/reject",
    "blocker   — informo bloqueo (no espera reply)",
    "handoff   — delego turno explícitamente",
  ]);
  if (msgType === undefined) return;
  const typeKey = msgType.split(/\s+/)[0];

  // 3. Cuerpo (texto libre) + envío REAL.
  const body = await ctx.ui.input(`Mensaje para ${toRole}:`, "Escribí el mensaje…");
  if (body === undefined || body.trim() === "") {
    ctx.ui.notify("Mensaje vacío — no se envió nada.", "info");
    return;
  }
  const res = await net.send(toRole, typeKey, body.trim());
  ctx.ui.notify(
    res.ok
      ? `✓ Mensaje enviado a ${toRole} (${typeKey}).`
      : `✗ No se pudo enviar: ${res.error ?? "error desconocido"}`,
    res.ok ? "success" : "error"
  );
}

/**
 * Cascada para broadcast a todos los peers y enviarlo DE VERDAD vía el
 * registro de acciones de red. Igual que sendMessageFlow pero sin el paso
 * "destinatario".
 */
async function broadcastFlow(ctx: any): Promise<void> {
  const net = getNetActions();
  if (!net || !net.isReady()) {
    ctx.ui.notify("cortex-net no está conectado en este proceso.", "warning");
    return;
  }
  if (cortexState.peers.length === 0) {
    ctx.ui.notify(
      "No hay peers conectados — el broadcast iría a 0 destinatarios.",
      "warning"
    );
    return;
  }

  const msgType = await ctx.ui.select("Tipo de mensaje (broadcast):", [
    "question  — pedido amplio",
    "proposal  — propuesta general",
    "blocker   — bloqueo a comunicar",
    "observe   — notificación pasiva",
  ]);
  if (msgType === undefined) return;
  const typeKey = msgType.split(/\s+/)[0];

  const body = await ctx.ui.input(
    "Mensaje (broadcast a todos los peers):",
    "Escribí el mensaje…"
  );
  if (body === undefined || body.trim() === "") {
    ctx.ui.notify("Mensaje vacío — no se envió nada.", "info");
    return;
  }
  const res = await net.broadcast(typeKey, body.trim());
  ctx.ui.notify(
    res.ok
      ? `✓ Broadcast enviado (${typeKey}) a ${res.delivered ?? cortexState.peers.length} peer(s).`
      : `✗ No se pudo broadcastear: ${res.error ?? "error desconocido"}`,
    res.ok ? "success" : "error"
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

/**
 * Lee las últimas ``n`` líneas de un log de cortex-net en
 * ``<cwd>/.pi/agent-sessions/<file>``. Best-effort: [] si no existe o falla.
 */
function tailLog(cwd: string, file: string, n: number): string[] {
  if (!cwd) return [];
  const p = join(cwd, ".pi", "agent-sessions", file);
  if (!existsSync(p)) return [];
  try {
    return readFileSync(p, "utf-8").trim().split("\n").filter(Boolean).slice(-n);
  } catch {
    return [];
  }
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

      // Despacho. send/broadcast/team_spawn EJECUTAN de verdad (vía los
      // registros que publican cortex-net y cortex-team). view_* leen los
      // logs. change_mode/change_role/switch_documenter apuntan a los slash
      // commands cortos (Pi no permite invocarlos desde acá).
      switch (selected) {
        case "send_message":
          await sendMessageFlow(ctx);
          break;

        case "broadcast":
          await broadcastFlow(ctx);
          break;

        case "view_transcript": {
          const cwd = cortexState.cwd ?? ctx.cwd ?? "";
          const lines = tailLog(cwd, "cortex-net-transcript.log", 8).filter((l) => {
            try {
              return JSON.parse(l).session_id === cortexState.sessionId;
            } catch {
              return true;
            }
          });
          if (lines.length === 0) {
            ctx.ui.notify("Transcript vacío para esta sesión todavía.", "info");
            break;
          }
          const fmt = lines.map((l) => {
            try {
              const e = JSON.parse(l);
              return `${e.from_role} → ${e.to_role ?? "all"} [${e.msg_type}]: ${String(
                e.body ?? ""
              ).slice(0, 80)}`;
            } catch {
              return l.slice(0, 100);
            }
          });
          ctx.ui.notify("Transcript reciente:\n" + fmt.join("\n"), "info");
          break;
        }

        case "view_audit": {
          const cwd = cortexState.cwd ?? ctx.cwd ?? "";
          const lines = tailLog(cwd, "cortex-net.log", 8);
          if (lines.length === 0) {
            ctx.ui.notify("Audit log vacío o inexistente todavía.", "info");
            break;
          }
          const fmt = lines.map((l) => {
            try {
              const e = JSON.parse(l);
              const t = String(e.ts ?? "").slice(11, 19);
              return `${t} ${e.op ?? "?"} ${e.from ?? e.role ?? ""}${
                e.to ? " → " + e.to : ""
              }${e.msg_type ? " [" + e.msg_type + "]" : ""}`;
            } catch {
              return l.slice(0, 100);
            }
          });
          ctx.ui.notify(
            "Audit log (últimas " + fmt.length + "):\n" + fmt.join("\n"),
            "info"
          );
          break;
        }

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
            "Usá /cx-mode (o /cortex-mode) para cambiar entre Full (red activa) y Solo (sin red).",
            "info"
          );
          break;

        case "change_role":
          ctx.ui.notify(
            "Usá /cx-role (o /cortex-role) para forzar un rol específico o volver a modo Auto.",
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

        case "team_spawn": {
          const team = getTeamActions();
          if (team) {
            await team.spawn(ctx); // abre el spawner REAL (mismo flujo que /cortex-team)
          } else {
            ctx.ui.notify("cortex-team no está cargado en este proceso.", "warning");
          }
          break;
        }

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
