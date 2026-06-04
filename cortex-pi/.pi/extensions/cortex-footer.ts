/**
 * cortex-footer.ts — Footer "tablero Cortex" (T1) + título de terminal por rol (T4)
 *
 * Tanda TUI del overhaul UX. Dos cosas, ambas client-side (0 tokens de LLM):
 *
 *   T1 · Footer powerline SIEMPRE visible (ctx.ui.setFooter). Reemplaza el
 *        footer built-in con una línea compacta: rol/persona · MASTER/WORKER ·
 *        sesión + tiempo · peers + 📨cola · modelo · % contexto · rama git.
 *        Lee todo del singleton _cortex-state + el FooterDataProvider (rama
 *        git + statuses de otras extensiones) + el último ctx (getContextUsage).
 *
 *   T4 · Título de la pestaña de terminal por rol (ctx.ui.setTitle), para
 *        distinguir las pestañas de WezTerm de un vistazo: "Cortex · designer".
 *
 * Por qué una extensión aparte y no dentro del cockpit: el cockpit (F1) fue
 * arreglado con cuidado (causa raíz del STANDBY) y es lector PURO vía widget +
 * setStatus. setFooter REEMPLAZA el footer built-in que renderiza esos
 * setStatus, así que este footer rinde la info del singleton directamente y
 * además anexa los statuses de OTRAS extensiones (vía getExtensionStatuses)
 * para no perder nada. Si se desactiva esta extensión, el cockpit vuelve a su
 * status bar built-in sin cambios.
 *
 * NO toca lógica de coordinación ni llama tools. Render puro sobre estado.
 *
 * Uso: settings.json defaultExtensions: [..., ".pi/extensions/cortex-footer.ts"].
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";
import { cortexState, subscribe } from "../lib/cortex-state";

// ── Helpers ──────────────────────────────────────────────────────────────

/** "12m" / "1h32m" / "47s" (igual que el cockpit). */
function formatDuration(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  return `${h}h${m - h * 60}m`;
}

function shortSessionId(id: string): string {
  if (id.length <= 24) return id;
  return id.slice(0, 21) + "…";
}

/** Sólo el id del modelo (último segmento de "provider/id"), acortado. */
function shortModel(model: string | null): string | null {
  if (!model) return null;
  const id = model.includes("/") ? model.slice(model.lastIndexOf("/") + 1) : model;
  return id.length <= 22 ? id : id.slice(0, 21) + "…";
}

/** Etiqueta de rol para footer/título. */
function roleLabel(): string {
  if (cortexState.myRole) return cortexState.myRole;
  if (cortexState.activeAgentName === "cortex-sync") return "sync";
  if (cortexState.sessionId) return "standby";
  return "—";
}

// Keys de status que ya representamos en la powerline (no las dupliques al
// anexar getExtensionStatuses): las 3 del cockpit + la persona de system-select.
const OWN_STATUS_KEYS = new Set(["cortex-session", "cortex-role", "cortex-peers", "cortex-agent"]);

// ── Extensión ──────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  // Último ctx visto, para getContextUsage()/model desde el factory del footer
  // (que recibe (tui, theme, footerData) pero NO ctx).
  let lastCtx: any = null;
  let lastTitle = "";
  let unsubscribe: (() => void) | null = null;

  /** Construye la línea de la powerline. Devuelve string[] (1 línea), truncada. */
  function renderFooter(theme: any, footerData: any, width: number): string[] {
    const W = Math.max(20, Math.min(width || 80, 200));
    const SEP = theme.fg("dim", " ▏ ");
    const segs: string[] = [];

    // ── Standby (sin sesión) ──
    if (!cortexState.sessionId) {
      segs.push(theme.fg("muted", "⬡ Cortex") + theme.fg("dim", " · standby"));
    } else {
      // Rol + MASTER/WORKER
      const role = roleLabel();
      let mode = "";
      if (cortexState.myRole) {
        mode = cortexState.isMaster
          ? theme.fg("accent", " MASTER")
          : theme.fg("muted", " WORKER");
      }
      segs.push(theme.fg("accent", "⬡ " + role) + mode);

      // Sesión + tiempo
      const elapsed = cortexState.sessionOpenedAt
        ? formatDuration(Date.now() - cortexState.sessionOpenedAt)
        : "—";
      segs.push(
        theme.fg("text", shortSessionId(cortexState.sessionId)) +
          theme.fg("dim", " " + elapsed)
      );

      // Peers + cola de inbound
      const npeers = cortexState.peers.length;
      const mail =
        cortexState.inbound.length > 0
          ? theme.fg("warning", ` 📨${cortexState.inbound.length}`)
          : "";
      segs.push(theme.fg("text", `${npeers}p`) + mail);
    }

    // Modelo (T1): del último ctx, o del singleton (lo siembra el cockpit).
    const modelStr =
      shortModel(
        lastCtx?.model
          ? `${lastCtx.model.provider ?? "?"}/${lastCtx.model.id ?? "?"}`
          : cortexState.myModel
      ) ?? null;
    if (modelStr) segs.push(theme.fg("dim", modelStr));

    // % de contexto (T1): coloreado por umbral.
    try {
      const usage = lastCtx?.getContextUsage?.();
      if (usage && usage.percent != null) {
        const pct = Math.round(usage.percent);
        const color = pct >= 85 ? "error" : pct >= 70 ? "warning" : "dim";
        segs.push(theme.fg(color, `ctx ${pct}%`));
      }
    } catch {
      /* getContextUsage puede no estar disponible */
    }

    // Rama git (del FooterDataProvider).
    try {
      const branch = footerData?.getGitBranch?.();
      if (branch) segs.push(theme.fg("dim", "⎇ " + branch));
    } catch {
      /* sin git */
    }

    // Anexar statuses de OTRAS extensiones (no las que ya representamos), para
    // no perderlas al reemplazar el footer built-in.
    try {
      const statuses: ReadonlyMap<string, string> | undefined =
        footerData?.getExtensionStatuses?.();
      if (statuses) {
        for (const [key, text] of statuses) {
          if (OWN_STATUS_KEYS.has(key)) continue;
          if (text && text.trim()) segs.push(theme.fg("dim", text));
        }
      }
    } catch {
      /* best-effort */
    }

    const line = segs.join(SEP);
    return [visibleWidth(line) > W ? truncateToWidth(line, W) : line];
  }

  /** (Re)aplica el footer y el título. */
  function apply(ctx: any): void {
    lastCtx = ctx;
    try {
      ctx.ui.setFooter((_tui: any, theme: any, footerData: any) => ({
        render(width: number): string[] {
          return renderFooter(theme, footerData, width);
        },
        invalidate() {
          /* render puro sobre cortexState */
        },
        dispose() {
          /* nada que limpiar */
        },
      }));
    } catch {
      /* si setFooter no está disponible en este modo (print/rpc), no pasa nada */
    }

    // T4 · título de terminal por rol (sólo si cambió, para no spammear).
    try {
      const title = `Cortex · ${roleLabel()}`;
      if (title !== lastTitle) {
        ctx.ui.setTitle(title);
        lastTitle = title;
      }
    } catch {
      /* setTitle puede no estar disponible */
    }
  }

  pi.on("session_start", async (_event, ctx) => {
    lastCtx = ctx;
    // Re-aplicar el footer cuando el estado cambie (peers, rol, cola, etc.).
    unsubscribe = subscribe(() => {
      if (lastCtx) apply(lastCtx);
    });
    apply(ctx);
  });

  // Refrescar por turno: actualiza % de contexto, tiempo y modelo aunque el
  // singleton no haya mutado.
  pi.on("turn_end", async (_event, ctx) => {
    apply(ctx);
  });
  pi.on("turn_start", async (_event, ctx) => {
    lastCtx = ctx;
  });

  pi.on("session_shutdown", async () => {
    if (unsubscribe) {
      unsubscribe();
      unsubscribe = null;
    }
  });
}
