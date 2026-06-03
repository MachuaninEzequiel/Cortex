/**
 * cortex-autopilot.ts — Hotkeys virtuales + gates + sugerencias contextuales
 *
 * F2 del overhaul UX (ver docs/multi-ide-mcp-hardening/PI-COCKPIT-UX/).
 *
 * Tres responsabilidades:
 *
 *   1. HOTKEYS VIRTUALES (interceptor del evento ``input``).
 *      Atajos cortos prefijados con ``:`` que el usuario tipea en el
 *      prompt. El handler los captura ANTES de que lleguen al agent y
 *      los traduce a slash commands o notificaciones. Cero costo de
 *      tokens. Prefijo ``:`` para no chocar con texto natural.
 *
 *      Mapeo actual:
 *
 *        :n  → ejecutar/anunciar la sugerencia activa del cockpit
 *        :t  → abrir panel team (F5; placeholder hasta F5)
 *        :d  → hint para cambiar a documenter
 *        :r  → /cortex-role
 *        :m  → /cortex-mode
 *        :l  → /cortex-net (status de red)
 *        :?  → mostrar lista de hotkeys disponibles
 *
 *   2. GATES DE GOBERNANZA (interceptor ``tool_call``).
 *      Detección temprana de violaciones de contrato Cortex sin romper
 *      el flujo (el backend ya tiene sus propios gates más estrictos —
 *      esto es feedback temprano en la UI, no enforcement).
 *
 *      Por ahora: warning si ``cortex_create_spec`` se invoca sin
 *      ``cortex_sync_ticket`` previo en este proceso.
 *
 *   3. SUGERENCIAS CONTEXTUALES (computa ``cortexState.suggestion``).
 *      Tras cada cambio de estado relevante (before_agent_start,
 *      turn_end), recalcula la próxima acción sugerida y la escribe al
 *      singleton. El cockpit la renderiza con su hotkey si la tiene.
 *
 * No registra ningún slash command propio en F2 — los hotkeys
 * virtuales delegan a comandos existentes (cortex-net.ts).
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
// Bugfix mayo 2026: import desde .pi/lib/ (ver cortex-cockpit.ts y
// docs/multi-ide-mcp-hardening/PI-COCKPIT-UX/README.md § 8).
import {
  cortexState,
  subscribe as subscribeCortexState,
  update as updateCortexState,
  type Suggestion,
} from "../lib/cortex-state";

// Bugfix mayo 2026: Pi v0.77 trata el prefijo ``:`` como un comando
// bash (igual que ``!``), así que las hotkeys :n :t :d etc. terminan
// disparando un shell command en vez de pasar por el handler de
// ``input``. Solución: registrar slash commands cortos con prefijo
// ``cx-`` (de "cortex") como aliases de las acciones más usadas. Pi
// los manda al handler registrado garantizado.
//
// IMPORTANTE: los alias que mapean a comandos de OTRAS extensiones
// (/cx-team → cortex-team; /cx-role, /cx-mode → cortex-net) se co-registran
// EN esas extensiones (apuntando al mismo handler), porque Pi no permite
// invocar un slash command desde otro handler. Acá sólo viven los propios:
//
//   /cx-next  → anuncia la sugerencia activa
//   /cx-help  → lista los atajos

// ── Sugerencias contextuales ───────────────────────────────────────────────

/**
 * Calcula la próxima acción recomendada según el estado actual.
 *
 * Reglas en orden de prioridad (la primera que matchea gana):
 *
 *   1. Sin sesión → tipear tarea para activar sync.
 *   2. Sync activo, sin checkpoints → esperar que sync persista spec.
 *   3. Sin agent activo aún → esperar primer cambio de agent.
 *   4. Documenter activo → cerrar con cortex_close_session.
 *   5. Middle activo, sin peers conectados → abrir terminales role-*.
 *   6. Middle activo, peers conectados → seguir coordinando.
 *
 * Devuelve null cuando no hay nada interesante que sugerir.
 */
function computeSuggestion(): Suggestion | null {
  // 1. Standby
  if (!cortexState.sessionId) {
    return {
      label: "Tipeá tu tarea — cortex-sync va a abrir la sesión automáticamente",
      hotkey: null,
      reason: "no hay Cortex Session activa",
    };
  }

  // 2. Sync activo
  if (cortexState.activeAgentName === "cortex-sync") {
    return {
      label: "Esperando que cortex-sync persista la spec",
      hotkey: null,
      reason: "sync corriendo (B' anchor, afuera de la red)",
    };
  }

  // 3. Sin agent del medio asignado
  if (!cortexState.myRole) {
    return {
      label: "Cambiá a un agent del medio (/system → cortex-SDDwork u otro)",
      hotkey: null,
      reason: "no estás registrado en la red todavía",
    };
  }

  // 4. Documenter activo → cerrar
  if (cortexState.myRole === "documenter") {
    return {
      label: "Llamá cortex_documenter_briefing + cortex_close_session para cerrar",
      hotkey: null,
      reason: "documenter activo, listo para cerrar",
    };
  }

  // 5. Middle activo sin peers conectados
  if (cortexState.peers.length === 0) {
    return {
      label: "Sin peers en la red — abrí el team con /cortex-team (o /cx-team)",
      hotkey: null,
      reason: "deep track requiere multi-terminal",
    };
  }

  // 6. Middle activo con peers
  return {
    label: "Coordiná con peers desde /cortex (mandar mensaje / broadcast)",
    hotkey: null,
    reason: `${cortexState.peers.length} peers conectados`,
  };
}

/** Igualdad por valor de sugerencias (para no re-escribir ni loopear). */
function suggestionsEqual(a: Suggestion | null, b: Suggestion | null): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  return a.label === b.label && a.hotkey === b.hotkey && a.reason === b.reason;
}

// ── Extension ──────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  // Set local de tools llamadas en este proceso. Sirve para detectar
  // ``cortex_create_spec`` sin ``cortex_sync_ticket`` previo. NO es
  // perfecto en multi-terminal (otra Pi puede haber llamado sync_ticket),
  // pero el flujo canónico es que sync corre en UN solo proceso antes
  // de que los workers entren a la red — así que el set local cubre el
  // caso real. El backend MCP tiene su propio gate más robusto.
  const toolsCalled = new Set<string>();
  let unsub: (() => void) | null = null;

  // ── Slash commands cortos (reemplazo de las hotkeys ":" que Pi v0.77
  //    interpretaba como bash). Ver bloque de comentario arriba.
  pi.registerCommand("cx-next", {
    description: "Anuncia la próxima acción sugerida según el estado actual",
    async handler(_args, ctx) {
      if (cortexState.suggestion) {
        ctx.ui.notify(
          `→ ${cortexState.suggestion.label} (${cortexState.suggestion.reason})`,
          "info"
        );
      } else {
        ctx.ui.notify(
          "Sin sugerencia activa. Tipeá tu tarea o abrí /cortex.",
          "info"
        );
      }
    },
  });

  pi.registerCommand("cx-help", {
    description: "Lista los atajos slash de Cortex Pi 2.5+net",
    async handler(_args, ctx) {
      ctx.ui.notify(
        "Atajos Cortex Pi 2.5+net:\n" +
          "  /cortex      panel grande (todas las acciones)\n" +
          "  /cx-next     próxima acción sugerida\n" +
          "  /cx-team     auto-spawn de terminales\n" +
          "  /cx-role     cambiar rol\n" +
          "  /cx-mode     cambiar modo (Full/Solo)\n" +
          "  /cx-help     esta ayuda\n" +
          "  /cortex-net  status detallado de la red\n" +
          "  /system      cambiar agent activo",
        "info"
      );
    },
  });

  // Los alias /cx-team, /cx-role y /cx-mode YA NO viven acá: se co-registran
  // en cortex-team.ts (/cx-team) y cortex-net.ts (/cx-role, /cx-mode)
  // apuntando al handler REAL, así ejecutan en vez de mostrar un hint (Pi no
  // permite invocar un slash command desde otra extensión). Acá quedan sólo
  // /cx-next y /cx-help, que son propios de autopilot.

  // ── tool_call: gates de gobernanza ───────────────────────────────────
  pi.on("tool_call", async (event, ctx) => {
    // Bugfix may 2026: el ToolCallEvent de Pi entrega event.toolName
    // (ver types.d.ts CustomToolCallEvent y damage-control.ts en este mismo
    // bundle). La versión previa leía event.tool?.name / event.name →
    // siempre undefined → el gate jamás disparaba (código muerto).
    const toolName: string = (event as any).toolName ?? "";
    if (!toolName) return;

    toolsCalled.add(toolName);

    // Gate: cortex_create_spec sin cortex_sync_ticket
    if (
      toolName === "cortex_create_spec" &&
      !toolsCalled.has("cortex_sync_ticket")
    ) {
      ctx?.ui?.notify(
        "⚠ Llamando cortex_create_spec sin cortex_sync_ticket previo. " +
          "El backend MCP va a rechazarlo con violación de gobernanza. " +
          "Ejecutá cortex_sync_ticket primero.",
        "warning"
      );
      // No bloqueamos — el backend ya rechaza. Esto es solo feedback temprano.
    }
  });

  // ── before_agent_start: recalcular sugerencia ───────────────────────
  pi.on("before_agent_start", async () => {
    updateCortexState({ suggestion: computeSuggestion() });
  });

  // ── turn_end: recalcular sugerencia (refresca contexto) ─────────────
  pi.on("turn_end", async () => {
    updateCortexState({ suggestion: computeSuggestion() });
  });

  // ── session_start: sembrar primera sugerencia + suscribir refresh ─────
  pi.on("session_start", async (_event, ctx) => {
    updateCortexState({ suggestion: computeSuggestion() });

    // 1a: la sugerencia se recalcula cuando CUALQUIER parte del estado
    // cambia (sessionId/myRole/peers vía la red), no solo en eventos de Pi.
    // Antes quedaba stale (un worker que no hace turns mostraba "tipeá tu
    // tarea" para siempre). Deferimos con queueMicrotask y sólo escribimos
    // si cambió, para no loopear con el propio update() (que re-notifica).
    if (!unsub) {
      unsub = subscribeCortexState(() => {
        queueMicrotask(() => {
          const next = computeSuggestion();
          if (!suggestionsEqual(next, cortexState.suggestion)) {
            updateCortexState({ suggestion: next });
          }
        });
      });
    }

    ctx.ui.notify(
      "⬡ cortex-autopilot: tipeá /cx-help para ver atajos. " +
        "Sugerencias contextuales activas.",
      "info"
    );
  });

  // ── session_shutdown: limpiar estado local ──────────────────────────
  pi.on("session_shutdown", async () => {
    toolsCalled.clear();
    if (unsub) {
      unsub();
      unsub = null;
    }
    // No notify acá: Pi se está cerrando, no llega.
    // No reset del singleton: cortex-cockpit ya lo hace en su shutdown.
  });
}
