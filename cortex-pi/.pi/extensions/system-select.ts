/**
 * system-select — Cortex Agent Persona Switcher
 *
 * Comando /system: selector interactivo de agentes definidos en .pi/agents/
 * Al seleccionar uno, inyecta su system prompt en cada turno via before_agent_start.
 * Al seleccionar "(ninguno)", restaura el comportamiento por defecto.
 *
 * Además de la persona, esta extensión administra DOS configuraciones por rol
 * (jun-2026), porque la activación de persona es el único punto que conoce el
 * rol activo:
 *
 *   - C2 · Tools activas por rol: aplica un DENY-LIST de las tools NATIVAS de
 *     escritura (write/edit/bash) según el `tools:` del frontmatter del agente.
 *     Hace real el "explorer read-only", etc. Incluye S1: a SDDwork se le sacan
 *     write/edit cuando hay un implementer en la red (no debe escribir código
 *     mientras orquesta un equipo). Se aplica en before_agent_start (idempotente,
 *     así el snapshot incluye las tools MCP que se registran async, y SDDwork se
 *     re-evalúa según los peers cada turno).
 *   - C1 · Modelo + thinking por rol: override OPT-IN por agente, persistido en
 *     .pi/cortex-model-overrides.json y seteado con /cortex-model. Default = el
 *     modelo de sesión (sin sorpresa de costo). Se aplica en los puntos de
 *     activación (cambia rara vez, no conviene re-setear el modelo cada turno).
 *
 * API real de Pi v0.70+ (verificada contra docs oficiales):
 *
 *   pi.sendMessage({ customType, content, display, details }, options?) → void
 *     - content: string  ← SIEMPRE string o array de bloques, nunca omitir
 *     - display: boolean ← true para mostrar en TUI
 *
 *   pi.on("before_agent_start", async (event, ctx) => {
 *     return { systemPrompt: event.systemPrompt + "\n\n..." }
 *   })
 *     - event.systemPrompt: string con el prompt acumulado hasta ese handler
 *     - retornar { systemPrompt } reemplaza (en realidad: encadena) el prompt
 *
 *   pi.getActiveTools() / pi.setActiveTools(names[])  ← C2
 *   pi.setModel(model) → Promise<boolean>  (false si falta API key)  ← C1
 *   pi.getThinkingLevel() / pi.setThinkingLevel(level)  ← C1
 *   ctx.modelRegistry.getAll()  ← lista de modelos para el selector
 *   ctx.model  ← modelo actual (para snapshot del default)
 *
 *   ctx.ui.select(title: string, options: string[]) → Promise<string | undefined>
 *   ctx.ui.notify(message: string, level?) → void
 *   ctx.ui.setStatus(key: string, text: string) → void
 *   ctx.ui.confirm(title: string, message: string) → Promise<boolean>
 *
 *   pi.registerMessageRenderer(customType, renderer) → void
 *     - Para que sendMessage({ display: true }) se vea bien en TUI
 *
 * Uso: pi -e .pi/extensions/system-select.ts
 * Dentro de Pi: /system   /system-list   /cortex-model
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Text } from "@mariozechner/pi-tui";
import { readFileSync, existsSync, readdirSync, writeFileSync } from "fs";
import { join } from "path";
// Bugfix mayo 2026: Pi v0.77 no dispara before_agent_start con
// event.agentName cuando el "agent persona" lo gestiona system-select
// (system-select solo inyecta system prompt, no le dice a Pi qué agent
// está activo). Para que el cockpit / cortex-net se enteren del cambio,
// system-select escribe al singleton compartido.
// Import desde .pi/lib/ para evitar doble instancia del singleton (ver
// docs/multi-ide-mcp-hardening/PI-COCKPIT-UX/README.md § 8).
import {
  cortexState,
  update as updateCortexState,
  resolveRoleFromAgentName,
} from "../lib/cortex-state";

// ── Types ──────────────────────────────────────────────────────────────────

interface AgentDef {
  name: string;
  description: string;
  systemPrompt: string;
  filePath: string;
  /** Tools declaradas en el frontmatter `tools:` (alias estilo Cortex como
   *  read_file/write_file). null = sin línea `tools:` → hereda el set default
   *  (caso cortex-SDDwork / cortex-sync). */
  tools: string[] | null;
}

// ── Parser de archivos de agente ───────────────────────────────────────────

function parseAgentFile(filePath: string): AgentDef | null {
  try {
    const raw = readFileSync(filePath, "utf-8");
    const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);

    if (!match) {
      // Sin frontmatter: usa nombre de archivo como nombre del agente
      const name = filePath.split(/[\\/]/).pop()!.replace(".md", "");
      return { name, description: "(sin descripción)", systemPrompt: raw.trim(), filePath, tools: null };
    }

    const fm: Record<string, string> = {};
    for (const line of match[1].split("\n")) {
      const idx = line.indexOf(":");
      if (idx > 0) {
        fm[line.slice(0, idx).trim()] = line.slice(idx + 1).trim().replace(/^["']|["']$/g, "");
      }
    }

    // C2: parsear el `tools:` del frontmatter (lista separada por comas).
    const tools = fm.tools
      ? fm.tools.split(",").map((t) => t.trim()).filter(Boolean)
      : null;

    return {
      name: fm.name || filePath.split(/[\\/]/).pop()!.replace(".md", ""),
      description: fm.description || "(sin descripción)",
      systemPrompt: match[2].trim(),
      filePath,
      tools,
    };
  } catch {
    return null;
  }
}

function scanAgents(cwd: string): AgentDef[] {
  const agentsDir = join(cwd, ".pi", "agents");
  if (!existsSync(agentsDir)) return [];

  const agents: AgentDef[] = [];
  try {
    for (const file of readdirSync(agentsDir)) {
      if (!file.endsWith(".md")) continue;
      const def = parseAgentFile(join(agentsDir, file));
      if (def) agents.push(def);
    }
  } catch {}

  // Orquestador primero, luego alfabético
  const priority = ["cortex-sddwork", "cortex-sdwork"];
  return agents.sort((a, b) => {
    const ai = priority.indexOf(a.name.toLowerCase());
    const bi = priority.indexOf(b.name.toLowerCase());
    if (ai !== -1 && bi !== -1) return ai - bi;
    if (ai !== -1) return -1;
    if (bi !== -1) return 1;
    return a.name.localeCompare(b.name);
  });
}

// ── C1/C2 — config por rol ──────────────────────────────────────────────────

/**
 * Tools de escritura NATIVAS de Pi → su alias en el frontmatter Cortex.
 * El frontmatter usa read_file/write_file/edit_file/execute_command, pero las
 * tools nativas reales de Pi son read/write/edit/bash (ver agent-chain.ts y los
 * tipos ToolCallEvent). C2 sólo controla estas nativas de escritura por
 * deny-list; las MCP (cortex_*) nunca se tocan (y write_design_note_canonical
 * queda registrada como mcp_cortex_write_design_note_canonical, así que un
 * allow-list estricto rompería al designer — por eso deny-list).
 */
const NATIVE_WRITE_TOOLS: Array<{ native: string; alias: string }> = [
  { native: "write", alias: "write_file" },
  { native: "edit", alias: "edit_file" },
  { native: "bash", alias: "execute_command" },
];

const VALID_THINKING = ["off", "minimal", "low", "medium", "high", "xhigh"];

interface ModelOverride {
  model?: string;
  thinking?: string;
}

function modelOverridesPath(cwd: string): string {
  return join(cwd, ".pi", "cortex-model-overrides.json");
}

function readModelOverrides(cwd: string): Record<string, ModelOverride> {
  try {
    const p = modelOverridesPath(cwd);
    if (!existsSync(p)) return {};
    const data = JSON.parse(readFileSync(p, "utf-8"));
    return data && typeof data === "object" ? data : {};
  } catch {
    return {};
  }
}

function writeModelOverrides(cwd: string, data: Record<string, ModelOverride>): void {
  try {
    writeFileSync(modelOverridesPath(cwd), JSON.stringify(data, null, 2), "utf-8");
  } catch {
    /* best-effort */
  }
}

// ── Extension ──────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let activeAgent: AgentDef | null = null;

  // ── Estado C1/C2 ──
  /** Set completo de tools conocido (acumulado por turno; nunca pierde nativas
   *  filtradas ni tools MCP que se registran tarde). Base del deny-list. */
  let defaultTools: string[] | null = null;
  /** Modelo y thinking de sesión, para restaurar cuando un rol no tiene override. */
  let defaultModel: any = undefined;
  let defaultThinking: any = undefined;
  /** True si pisamos modelo/thinking con un override (para saber si restaurar
   *  sin clobberear un cambio manual del usuario cuando no hay override). */
  let modelOverrideActive = false;
  let thinkingOverrideActive = false;
  /** Overrides por agente, cargados de .pi/cortex-model-overrides.json. */
  let overrides: Record<string, ModelOverride> = {};

  // ── Helpers C2 (tools por rol) ──

  function peersIncludeImplementer(): boolean {
    try {
      return cortexState.peers.some((p: any) => p.role === "implementer");
    } catch {
      return false;
    }
  }

  /** Qué tools NATIVAS de escritura sacarle al rol (deny-list, derivado del
   *  frontmatter). Nunca vacía el set ni toca MCP. */
  function denyToolsFor(agent: AgentDef | null): string[] {
    if (!agent) return []; // (ninguno) → set completo
    if (agent.tools) {
      const declared = agent.tools;
      const deny: string[] = [];
      for (const { native, alias } of NATIVE_WRITE_TOOLS) {
        if (!declared.includes(alias) && !declared.includes(native)) deny.push(native);
      }
      return deny;
    }
    // Sin `tools:` en el frontmatter: SDDwork es dinámico (S1); el resto
    // (cortex-sync) queda con el set completo.
    if (agent.name.toLowerCase() === "cortex-sddwork") {
      return peersIncludeImplementer() ? ["write", "edit"] : [];
    }
    return [];
  }

  /** Aplica el deny-list sobre el set conocido. Corre cada turno desde
   *  before_agent_start: idempotente, deja que el snapshot acumule las tools
   *  MCP async, y re-evalúa a SDDwork según los peers. */
  function applyToolsForTurn(): void {
    try {
      const current = pi.getActiveTools();
      if (!current || current.length === 0) return; // guard anti-brick
      if (!defaultTools) {
        defaultTools = current.slice();
      } else {
        const set = new Set(defaultTools);
        for (const t of current) set.add(t);
        defaultTools = [...set];
      }
      const deny = denyToolsFor(activeAgent);
      pi.setActiveTools(defaultTools.filter((t) => !deny.includes(t)));
    } catch {
      /* nunca lanzar desde un hook */
    }
  }

  // ── Helpers C1 (modelo/thinking por rol) ──

  function resolveModelById(ctx: any, id: string | undefined): any {
    if (!id) return undefined;
    try {
      const all = ctx.modelRegistry?.getAll?.() ?? [];
      return all.find(
        (m: any) => m.id === id || `${m.provider}/${m.id}` === id || m.name === id
      );
    } catch {
      return undefined;
    }
  }

  /** Aplica modelo + thinking del override del agente activo, o restaura el
   *  default si no hay override (y antes habíamos pisado). */
  async function applyModelThinking(ctx: any): Promise<void> {
    const ov = activeAgent ? overrides[activeAgent.name] : undefined;
    // ── Modelo ──
    try {
      if (ov?.model) {
        const m = resolveModelById(ctx, ov.model);
        if (m) {
          const ok = await pi.setModel(m);
          if (ok) modelOverrideActive = true;
          else
            ctx.ui?.notify(
              `⬡ No pude cambiar al modelo "${ov.model}" (¿falta API key?). Sigo con el actual.`,
              "warning"
            );
        } else {
          ctx.ui?.notify(
            `⬡ Modelo "${ov.model}" no está en el registry. Sigo con el actual.`,
            "warning"
          );
        }
      } else if (modelOverrideActive && defaultModel) {
        await pi.setModel(defaultModel);
        modelOverrideActive = false;
      }
    } catch {
      /* no romper la activación de persona */
    }
    // ── Thinking ── (sólo lo tocamos si hay override o si veníamos pisando)
    try {
      if (ov?.thinking && VALID_THINKING.includes(ov.thinking)) {
        pi.setThinkingLevel(ov.thinking as any);
        thinkingOverrideActive = true;
      } else if (thinkingOverrideActive && defaultThinking) {
        pi.setThinkingLevel(defaultThinking as any);
        thinkingOverrideActive = false;
      }
    } catch {
      /* idem */
    }
  }

  // ── Renderer para los mensajes de esta extensión ───────────────────────
  // Sin esto, display:true mostraría el JSON crudo en el TUI
  pi.registerMessageRenderer("cortex-system-select", (message, _options, theme) => {
    const content = typeof message.content === "string" ? message.content : "";
    return new Text(theme.fg("accent", "⬡ ") + content, 0, 0);
  });

  // ── Inyecta el system prompt del agente activo + aplica tools (C2) ──────
  pi.on("before_agent_start", async (event, _ctx) => {
    // C2: aplicar el deny-list de tools cada turno (idempotente). Corre siempre,
    // incluso sin persona (deny vacío = set completo), así el snapshot acumula
    // las tools MCP que se registran async y SDDwork se re-evalúa por peers.
    applyToolsForTurn();

    if (!activeAgent) return;
    // event.systemPrompt ya contiene el prompt encadenado de handlers anteriores
    return {
      systemPrompt:
        event.systemPrompt +
        `\n\n---\n## Agente Activo: ${activeAgent.name}\n\n${activeAgent.systemPrompt}`,
    };
  });

  // ── Notificación al arrancar + snapshot de defaults (C1) ───────────────
  pi.on("session_start", async (_event, ctx) => {
    // C1: snapshot del modelo/thinking de sesión (para restaurar) + overrides.
    try {
      defaultModel = ctx.model;
      defaultThinking = pi.getThinkingLevel();
      overrides = readModelOverrides(ctx.cwd);
    } catch {
      /* defensivo: si algo falla, C1 simplemente no aplica overrides */
    }

    const agents = scanAgents(ctx.cwd);
    if (agents.length === 0) return;

    // Auto-activación por env (CORTEX_AGENT): cortex-team la setea al
    // spawnear una terminal de rol, para que la hija arranque YA con la
    // persona correcta (sin que el usuario tenga que hacer /system). Match
    // case-insensitive para tolerar el casing de cortex-SDDwork.
    const envAgent = process.env.CORTEX_AGENT?.trim();
    if (envAgent) {
      const match = agents.find(
        (a) => a.name.toLowerCase() === envAgent.toLowerCase()
      );
      if (match) {
        activeAgent = match;
        ctx.ui.setStatus("cortex-agent", `⬡ ${match.name}`);
        // Fuente de verdad del agent/rol para cockpit + cortex-net.
        updateCortexState({
          activeAgentName: match.name,
          myRole: resolveRoleFromAgentName(match.name),
        });
        // C1: aplicar modelo/thinking del rol (las tools se aplican en el
        // primer before_agent_start).
        await applyModelThinking(ctx);
        ctx.ui.notify(`✓ Agente activo (auto vía CORTEX_AGENT): ${match.name}`, "success");
        return;
      }
    }

    ctx.ui.notify(
      `⬡ Cortex: ${agents.length} agentes en .pi/agents/ → /system para activar`,
      "info"
    );
  });

  // ── Comando /system ────────────────────────────────────────────────────
  pi.registerCommand("system", {
    description: "Selecciona un agente Cortex como persona activa del system prompt",
    async handler(_args: string, ctx: any) {
      const agents = scanAgents(ctx.cwd);

      if (agents.length === 0) {
        ctx.ui.notify("⚠ No se encontraron agentes en .pi/agents/", "warning");
        return;
      }

      const NONE = "(ninguno — system prompt por defecto)";

      // ctx.ui.select(title, options[]) → options DEBE ser string[]
      const options: string[] = [
        NONE,
        ...agents.map(
          (a) =>
            `${a.name}  —  ${
              a.description.length > 65
                ? a.description.slice(0, 62) + "…"
                : a.description
            }`
        ),
      ];

      const selected: string | undefined = await ctx.ui.select(
        "⬡ Cortex — Seleccionar Agente",
        options
      );

      // undefined = usuario canceló con Escape
      if (selected === undefined) {
        ctx.ui.notify("Selección cancelada", "info");
        return;
      }

      if (selected === NONE) {
        activeAgent = null;
        ctx.ui.setStatus("cortex-agent", "");
        // Bugfix: propagar al singleton para que cortex-cockpit y
        // cortex-net se enteren (Pi v0.77 no dispara
        // before_agent_start con event.agentName en este flujo).
        updateCortexState({
          activeAgentName: null,
          myRole: null,
        });
        // C1: restaurar modelo/thinking de sesión (las tools vuelven al set
        // completo en el próximo before_agent_start).
        await applyModelThinking(ctx);
        ctx.ui.notify("✓ System prompt por defecto restaurado", "success");
        // sendMessage con firma correcta: objeto con customType, content, display
        pi.sendMessage({
          customType: "cortex-system-select",
          content: "⬡ Agente desactivado — usando system prompt por defecto",
          display: true,
        });
        return;
      }

      // Extrae el nombre del agente (antes de "  —  ")
      const agentName = selected.split("  —  ")[0].trim();
      const agent = agents.find((a) => a.name === agentName);

      if (!agent) {
        ctx.ui.notify("⚠ Agente no encontrado", "warning");
        return;
      }

      activeAgent = agent;
      ctx.ui.setStatus("cortex-agent", `⬡ ${agent.name}`);
      // Bugfix: propagar al singleton para que cortex-cockpit y
      // cortex-net se enteren del cambio de agent. resolveRoleFromAgentName
      // devuelve null para cortex-sync (B' anchor, afuera de la red).
      updateCortexState({
        activeAgentName: agent.name,
        myRole: resolveRoleFromAgentName(agent.name),
      });
      // C1: aplicar modelo/thinking del rol (las tools se aplican en el próximo
      // before_agent_start).
      await applyModelThinking(ctx);
      ctx.ui.notify(`✓ Agente activo: ${agent.name}`, "success");

      // Muestra la descripción del agente en el chat
      pi.sendMessage({
        customType: "cortex-system-select",
        content: `⬡ Agente cargado: ${agent.name}\n${agent.description}\n\nSu system prompt se inyectará en cada turno.`,
        display: true,
      });
    },
  });

  // ── Comando /system-list ───────────────────────────────────────────────
  pi.registerCommand("system-list", {
    description: "Lista todos los agentes Cortex disponibles en .pi/agents/",
    handler(_args: string, ctx: any) {
      const agents = scanAgents(ctx.cwd);

      if (agents.length === 0) {
        ctx.ui.notify("No hay agentes en .pi/agents/", "warning");
        return;
      }

      const activeName = activeAgent?.name ?? "(ninguno)";
      const lines = agents
        .map((a) => {
          const marker = a.name === activeAgent?.name ? " ◀ ACTIVO" : "";
          return `${a.name}${marker}\n  ${a.description}`;
        })
        .join("\n\n");

      pi.sendMessage({
        customType: "cortex-system-select",
        content: `Agentes disponibles (activo: ${activeName})\n\n${lines}`,
        display: true,
      });
    },
  });

  // ── C1 · Comando /cortex-model ─────────────────────────────────────────
  // Setea modelo/thinking por agente. Default = modelo de sesión (sin sorpresa
  // de costo); este comando es el override opt-in. Persiste en
  // .pi/cortex-model-overrides.json.
  async function configureModelFlow(ctx: any): Promise<void> {
    const agents = scanAgents(ctx.cwd);
    if (agents.length === 0) {
      ctx.ui.notify("No hay agentes en .pi/agents/", "warning");
      return;
    }

    // 1. Agente
    const agentSel = await ctx.ui.select(
      "⬡ Modelo/thinking por rol — Elegí el agente:",
      agents.map((a) => a.name)
    );
    if (agentSel === undefined) return;

    // 2. Modelo (desde el registry) + "Default"
    let models: any[] = [];
    try {
      models = ctx.modelRegistry?.getAll?.() ?? [];
    } catch {
      models = [];
    }
    const DEFAULT_MODEL = "(Default de sesión)";
    const modelLabels = models.map((m: any) => m.id ?? m.name ?? String(m));
    const modelSel = await ctx.ui.select(`Modelo para ${agentSel}:`, [
      DEFAULT_MODEL,
      ...modelLabels,
    ]);
    if (modelSel === undefined) return;

    // 3. Thinking + "Default"
    const DEFAULT_THINKING = "(Default)";
    const thinkingSel = await ctx.ui.select(`Thinking para ${agentSel}:`, [
      DEFAULT_THINKING,
      ...VALID_THINKING,
    ]);
    if (thinkingSel === undefined) return;

    // Persistir
    const data = readModelOverrides(ctx.cwd);
    const entry: ModelOverride = {};
    if (modelSel !== DEFAULT_MODEL) entry.model = modelSel;
    if (thinkingSel !== DEFAULT_THINKING) entry.thinking = thinkingSel;
    if (Object.keys(entry).length === 0) delete data[agentSel];
    else data[agentSel] = entry;
    writeModelOverrides(ctx.cwd, data);
    overrides = data;

    ctx.ui.notify(
      Object.keys(entry).length === 0
        ? `✓ ${agentSel}: override limpiado (usa el default de sesión).`
        : `✓ ${agentSel}: ${JSON.stringify(entry)}`,
      "success"
    );

    // Aplicar en vivo si es el agente activo en esta terminal
    if (activeAgent && activeAgent.name === agentSel) {
      await applyModelThinking(ctx);
      ctx.ui.notify(`✓ Aplicado en vivo (sos ${agentSel}).`, "info");
    }
  }

  pi.registerCommand("cortex-model", {
    description: "Setea modelo/thinking por rol (default = modelo de sesión; override opt-in)",
    async handler(_args: string, ctx: any) {
      await configureModelFlow(ctx);
    },
  });

}
