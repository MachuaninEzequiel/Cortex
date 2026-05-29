/**
 * cortex-cockpit.ts — Widget persistente + status bar de Cortex Pi 2.5+net
 *
 * F1 del overhaul UX (ver docs/multi-ide-mcp-hardening/PI-COCKPIT-UX/).
 *
 * Lo que hace:
 *
 *   1. Widget arriba del editor (``ctx.ui.setWidget("cortex-cockpit", ...)``)
 *      que muestra estado de la sesión, rol propio, peers en la red y
 *      tráfico reciente. Read-only — la interacción pasa por /cortex (F4)
 *      o por las hotkeys virtuales de cortex-autopilot (F2).
 *
 *   2. Status bar multi-key (``ctx.ui.setStatus(...)``) con tres slots
 *      siempre visibles aunque el widget quede fuera de viewport:
 *        - cortex-session : ⬡ <id> · <tiempo>
 *        - cortex-role    : <rol> · MASTER/WORKER
 *        - cortex-peers   : <count> peers (<idle>/<busy>)
 *
 *   3. Suscriptor del singleton ``_cortex-state``: cuando cortex-net o
 *      cortex-autopilot mutan el estado, el cockpit se redibuja sin
 *      polling extra. Igualmente hay un ``setInterval`` de respaldo
 *      para leer ``.cortex/session.lock`` por si la sesión cambia
 *      fuera-de-banda (otra Pi la cerró, p.ej.).
 *
 * NO hace:
 *
 *   - No captura keyboard (los widgets persistentes no reciben input
 *     según la doc de Pi). Las hotkeys son responsabilidad de F2.
 *   - No llama tools MCP. El estado lo lee del singleton + del
 *     session.lock + del audit/transcript log que ya escribe cortex-net.
 *   - No abre paneles modales. Eso es F4 (``cortex-panel.ts``).
 *
 * Uso: cargada automáticamente por settings.json
 *      (defaultExtensions: [..., ".pi/extensions/cortex-cockpit.ts"]).
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
// truncateToWidth respeta los ANSI escape codes al cortar (a diferencia
// de String.slice). visibleWidth nos dice cuántas "columnas" ocupa un
// string con escapes embebidos. Indispensable para no crashear Pi con
// "Rendered line N exceeds terminal width".
import { truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
import { existsSync, readFileSync, statSync } from "fs";
import { join } from "path";
// Bugfix mayo 2026: el singleton vive en .pi/lib/ para evitar la
// doble instancia que provoca el autoloader de Pi v0.77 (ver
// docs/multi-ide-mcp-hardening/PI-COCKPIT-UX/README.md § 8).
import {
  cortexState,
  subscribe,
  update,
  reset,
} from "../lib/cortex-state";

// ── Constantes ─────────────────────────────────────────────────────────────

const WIDGET_ID = "cortex-cockpit";
const STATUS_SESSION = "cortex-session";
const STATUS_ROLE = "cortex-role";
const STATUS_PEERS = "cortex-peers";

/** Período del polling de respaldo en ms (lee session.lock por si cambió). */
const REFRESH_INTERVAL_MS = 3000;

// ── Helpers de derivación de estado ────────────────────────────────────────

/**
 * Lee ``<cwd>/.cortex/session.lock`` y devuelve el session_id, o null.
 *
 * Best-effort: cualquier error de IO devuelve null. Usado por el polling
 * de respaldo para detectar si la sesión cambió sin que el hook de
 * cortex-net lo haya propagado (p.ej. otro Pi cerró la sesión).
 */
function readSessionLock(cwd: string): { id: string; mtime: number } | null {
  const lock = join(cwd, ".cortex", "session.lock");
  if (!existsSync(lock)) return null;
  try {
    const raw = readFileSync(lock, "utf-8").trim();
    if (!raw) return null;
    const st = statSync(lock);
    return { id: raw, mtime: st.mtimeMs };
  } catch {
    return null;
  }
}

/** Formato compacto "12m" / "1h32m" / "47s" para mostrar duración. */
function formatDuration(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  return `${h}h${m - h * 60}m`;
}

/** Acorta el session_id para mostrar (mantiene la fecha y el primer slug). */
function shortSessionId(id: string): string {
  // Formato canónico: YYYY-MM-DD_<slug>. Lo mostramos completo pero
  // truncado a ~28 chars para que entre en una línea típica.
  if (id.length <= 32) return id;
  return id.slice(0, 29) + "…";
}

// ── Render ──────────────────────────────────────────────────────────────────

/**
 * Renderiza el widget grande. Devuelve líneas listas para Pi.
 *
 * Estados que cubre F1:
 *
 *   - Standby: sin sessionId. Mensaje breve.
 *   - Sync activo: hay sessionId y el agent activo es cortex-sync (B').
 *   - Middle: hay sessionId y el rol propio es uno de los 7.
 *   - Documenter: hay sessionId y el rol propio es "documenter".
 *
 * Render más sofisticado (sugerencias contextuales, tráfico reciente,
 * conteo de checkpoints) llegan con F2/F3.
 */
function renderCockpit(theme: any, width: number): string[] {
  const lines: string[] = [];
  // El widget se renderiza al ancho de la terminal. Si Pi pasa 0 o algo
  // raro, tope mínimo de 40 cols. Tope superior 120 para que no se vea
  // ridículo en monitores anchos.
  const W = Math.max(40, Math.min(width || 80, 120));

  // ── Standby ───────────────────────────────────────────────────────────
  if (!cortexState.sessionId) {
    lines.push(theme.fg("muted", "⬡ Cortex · standby"));
    lines.push(theme.fg("dim", "  Sin sesión activa — tipeá tu tarea para empezar"));
    return finalize(lines, W);
  }

  // ── Con sesión ────────────────────────────────────────────────────────
  const elapsed = cortexState.sessionOpenedAt
    ? formatDuration(Date.now() - cortexState.sessionOpenedAt)
    : "—";
  const role = cortexState.activeAgentName === "cortex-sync"
    ? "sync (B' — afuera de la red)"
    : cortexState.myRole ?? "(no en la red)";
  // Modo: MASTER si vos levantaste el hub; WORKER si te conectaste a un
  // hub externo; "—" si ni siquiera estás en la red todavía (caso típico
  // tras un session_start sin lock — cortex-net espera al lock para
  // levantar el hub).
  const mode = !cortexState.myRole
    ? cortexState.activeAgentName === "cortex-sync"
      ? theme.fg("dim", "sync")
      : theme.fg("dim", "STANDBY")
    : cortexState.isMaster
    ? theme.fg("accent", "MASTER")
    : theme.fg("muted", "WORKER");

  // Línea 1: header con session id + tiempo + master/worker
  lines.push(
    theme.fg("accent", "⬡ CORTEX") +
      " · " +
      theme.fg("text", shortSessionId(cortexState.sessionId)) +
      theme.fg("dim", ` · ${elapsed}`) +
      theme.fg("dim", " — ") +
      mode
  );

  // Línea 2: rol propio + agent activo
  const agentLabel = cortexState.activeAgentName ?? "(ninguno)";
  lines.push(
    theme.fg("dim", "  Rol: ") +
      theme.fg("text", String(role)) +
      theme.fg("dim", " · agent: ") +
      theme.fg("text", agentLabel)
  );

  // Línea 3+: peers
  if (cortexState.peers.length === 0) {
    const hint =
      cortexState.activeAgentName === "cortex-sync"
        ? "(en sync; peers entran al cambiar de rol)"
        : "(ninguno — /cortex-team o just role-*)";
    lines.push(theme.fg("dim", "  Peers: ") + theme.fg("muted", hint));
  } else {
    const peerLabels = cortexState.peers.map((p) => {
      const self = p.role === cortexState.myRole ? "→" : " ";
      const status = p.status ?? "?";
      const statusColor =
        status === "idle"
          ? "success"
          : status === "busy"
          ? "warning"
          : status === "observe"
          ? "accent"
          : "muted";
      return (
        theme.fg("dim", `${self} `) +
        theme.fg("text", p.role.padEnd(14)) +
        theme.fg(statusColor, status)
      );
    });
    lines.push(theme.fg("dim", `  Peers (${cortexState.peers.length}):`));
    // 2 peers por línea para no desbordar en terminales angostas.
    for (let i = 0; i < peerLabels.length; i += 2) {
      const pair = peerLabels.slice(i, i + 2).join("  ·  ");
      lines.push("    " + pair);
    }
  }

  // Sugerencia (la popula F2)
  if (cortexState.suggestion) {
    const hk = cortexState.suggestion.hotkey
      ? theme.fg("accent", ` [${cortexState.suggestion.hotkey}]`)
      : "";
    lines.push(
      theme.fg("dim", "  → ") +
        theme.fg("text", cortexState.suggestion.label) +
        hk
    );
  }

  // Footer: hints de comandos. Corto a propósito para no exceder
  // terminales angostas.
  lines.push(
    theme.fg("dim", "  ") +
      theme.fg("accent", "/cortex") +
      theme.fg("dim", " panel · ") +
      theme.fg("accent", "/cx-help") +
      theme.fg("dim", " atajos")
  );

  return finalize(lines, W);
}

/**
 * Aplica truncateToWidth a cada línea para garantizar que ninguna excede
 * el ancho de la terminal. Pi crashea con uncaughtException si una línea
 * supera el width. truncateToWidth preserva los escape codes ANSI al
 * cortar — no podemos usar slice porque cortaría en medio de un escape.
 */
function finalize(lines: string[], width: number): string[] {
  return lines.map((l) => (visibleWidth(l) > width ? truncateToWidth(l, width) : l));
}

/** Actualiza la status bar multi-key (3 slots). Independiente del widget. */
function updateStatusBar(ctx: any): void {
  if (!cortexState.sessionId) {
    ctx.ui.setStatus(STATUS_SESSION, "⬡ standby");
    ctx.ui.setStatus(STATUS_ROLE, "");
    ctx.ui.setStatus(STATUS_PEERS, "");
    return;
  }

  // Slot 1: sesión + tiempo
  const elapsed = cortexState.sessionOpenedAt
    ? formatDuration(Date.now() - cortexState.sessionOpenedAt)
    : "—";
  ctx.ui.setStatus(
    STATUS_SESSION,
    `⬡ ${shortSessionId(cortexState.sessionId)} · ${elapsed}`
  );

  // Slot 2: rol + master/worker. Espeja la lógica de 3 estados del widget
  // (STANDBY / sync / role·MASTER|WORKER). Antes mostraba "— · WORKER"
  // cuando myRole era null, contradiciendo al widget de arriba.
  let roleStatus: string;
  if (!cortexState.myRole) {
    roleStatus = cortexState.activeAgentName === "cortex-sync" ? "sync" : "STANDBY";
  } else {
    roleStatus = `${cortexState.myRole} · ${cortexState.isMaster ? "MASTER" : "WORKER"}`;
  }
  ctx.ui.setStatus(STATUS_ROLE, roleStatus);

  // Slot 3: peers
  if (cortexState.peers.length === 0) {
    ctx.ui.setStatus(STATUS_PEERS, "0 peers");
  } else {
    const idle = cortexState.peers.filter((p) => p.status === "idle").length;
    const busy = cortexState.peers.filter((p) => p.status === "busy").length;
    ctx.ui.setStatus(
      STATUS_PEERS,
      `${cortexState.peers.length} peers (${idle}i/${busy}b)`
    );
  }
}

// ── Extensión ──────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let pollHandle: NodeJS.Timeout | null = null;
  let unsubscribe: (() => void) | null = null;
  let lastLockMtime = 0;

  /**
   * Vuelve a registrar el widget y actualiza la status bar.
   *
   * setWidget acepta una factory que devuelve un Component-like; cada
   * llamada reemplaza al anterior con el mismo id. Pi se encarga del
   * redraw real.
   */
  function refresh(ctx: any): void {
    ctx.ui.setWidget(
      WIDGET_ID,
      (_tui: any, theme: any) => ({
        render(width: number): string[] {
          return renderCockpit(theme, width);
        },
        invalidate() {
          /* no-op: el render es puro sobre cortexState */
        },
      }),
      { placement: "aboveEditor" }
    );
    updateStatusBar(ctx);
  }

  /**
   * Polling de respaldo: lee session.lock cada N segundos y actualiza
   * sessionId si cambió (otra Pi cerró/abrió una sesión).
   *
   * Si cortex-net está cargado, este polling es redundante en el
   * camino feliz — el hook session_start de cortex-net ya popula
   * sessionId. El polling lo agrego de igual modo para que el cockpit
   * funcione standalone (sin cortex-net cargado).
   */
  function pollLock(ctx: any): void {
    if (!cortexState.cwd) return;
    const lock = readSessionLock(cortexState.cwd);
    if (!lock) {
      if (cortexState.sessionId !== null) {
        // sesión que existía ya no existe — limpiar
        update({
          sessionId: null,
          sessionOpenedAt: null,
        });
        refresh(ctx);
      }
      return;
    }
    if (lock.id !== cortexState.sessionId || lock.mtime !== lastLockMtime) {
      lastLockMtime = lock.mtime;
      update({
        sessionId: lock.id,
        sessionOpenedAt: cortexState.sessionOpenedAt ?? lock.mtime,
      });
      refresh(ctx);
    }
  }

  // ── session_start ─────────────────────────────────────────────────────
  pi.on("session_start", async (_event, ctx) => {
    // Estado inicial. cortex-net (si está cargado) va a sobrescribir
    // isMaster / peers / myRole en sus propios hooks; nosotros sembramos
    // lo que se puede deducir solo del filesystem.
    const lock = readSessionLock(ctx.cwd);
    lastLockMtime = lock?.mtime ?? 0;
    update({
      cwd: ctx.cwd,
      sessionId: lock?.id ?? null,
      sessionOpenedAt: lock?.mtime ?? null,
      myModel: ctx.model
        ? `${ctx.model.provider ?? "?"}/${ctx.model.id ?? "?"}`
        : null,
    });

    // Subscripción al singleton: cualquier ``update(...)`` desde otra
    // extensión nos hace re-renderizar.
    unsubscribe = subscribe(() => refresh(ctx));

    refresh(ctx);
    pollHandle = setInterval(() => pollLock(ctx), REFRESH_INTERVAL_MS);
  });

  // ── before_agent_start: NO se usa, a propósito ───────────────────────
  // Bugfix may 2026 (causa raíz del STANDBY): Pi v0.77 NO expone el agent
  // activo en ningún evento ni en ctx. Verificado contra los tipos
  // instalados: BeforeAgentStartEvent = { type, prompt, images?,
  // systemPrompt, systemPromptOptions } — sin agentName. La versión previa
  // leía (event as any).agentName → SIEMPRE undefined → escribía
  // activeAgentName:null / myRole:null EN CADA TURNO, pisando lo que
  // /system (system-select) había fijado y devolviendo el cockpit a
  // STANDBY. El cockpit es lector PURO: la identidad de rol la administra
  // system-select y nos enteramos vía subscribe() → refresh().

  // ── turn_end ─────────────────────────────────────────────────────────
  pi.on("turn_end", async (_event, ctx) => {
    // Defensa: re-poblar cwd si por alguna razón se perdió (observado
    // en runtime: /cortex-team falla con "no hay cwd cacheado" aunque
    // session_start del cockpit corrió. Mejor poblarlo de defensiva).
    if (!cortexState.cwd && ctx?.cwd) {
      update({ cwd: ctx.cwd });
    }
    // Forzamos un refresh por si el tiempo elapsed cambió de minuto y
    // el render necesita actualizar el contador.
    refresh(ctx);
  });

  // ── session_shutdown ─────────────────────────────────────────────────
  pi.on("session_shutdown", async () => {
    if (pollHandle) {
      clearInterval(pollHandle);
      pollHandle = null;
    }
    if (unsubscribe) {
      unsubscribe();
      unsubscribe = null;
    }
    reset();
  });
}
