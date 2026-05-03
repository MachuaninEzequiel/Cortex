/**
 * system-select — Cortex Agent Persona Switcher
 *
 * Comando /system: selector interactivo de agentes definidos en .pi/agents/
 * Al seleccionar uno, inyecta su system prompt en cada turno via before_agent_start.
 * Al seleccionar "(ninguno)", restaura el comportamiento por defecto.
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
 *   ctx.ui.select(title: string, options: string[]) → Promise<string | undefined>
 *   ctx.ui.notify(message: string, level?) → void
 *   ctx.ui.setStatus(key: string, text: string) → void
 *   ctx.ui.confirm(title: string, message: string) → Promise<boolean>
 *
 *   pi.registerMessageRenderer(customType, renderer) → void
 *     - Para que sendMessage({ display: true }) se vea bien en TUI
 *
 * Uso: pi -e .pi/extensions/system-select.ts
 * Dentro de Pi: /system   /system-list
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Text } from "@mariozechner/pi-tui";
import { readFileSync, existsSync, readdirSync } from "fs";
import { join } from "path";

// ── Types ──────────────────────────────────────────────────────────────────

interface AgentDef {
  name: string;
  description: string;
  systemPrompt: string;
  filePath: string;
}

// ── Parser de archivos de agente ───────────────────────────────────────────

function parseAgentFile(filePath: string): AgentDef | null {
  try {
    const raw = readFileSync(filePath, "utf-8");
    const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);

    if (!match) {
      // Sin frontmatter: usa nombre de archivo como nombre del agente
      const name = filePath.split(/[\\/]/).pop()!.replace(".md", "");
      return { name, description: "(sin descripción)", systemPrompt: raw.trim(), filePath };
    }

    const fm: Record<string, string> = {};
    for (const line of match[1].split("\n")) {
      const idx = line.indexOf(":");
      if (idx > 0) {
        fm[line.slice(0, idx).trim()] = line.slice(idx + 1).trim().replace(/^["']|["']$/g, "");
      }
    }

    return {
      name: fm.name || filePath.split(/[\\/]/).pop()!.replace(".md", ""),
      description: fm.description || "(sin descripción)",
      systemPrompt: match[2].trim(),
      filePath,
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

// ── Extension ──────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let activeAgent: AgentDef | null = null;

  // ── Renderer para los mensajes de esta extensión ───────────────────────
  // Sin esto, display:true mostraría el JSON crudo en el TUI
  pi.registerMessageRenderer("cortex-system-select", (message, _options, theme) => {
    const content = typeof message.content === "string" ? message.content : "";
    return new Text(theme.fg("accent", "⬡ ") + content, 0, 0);
  });

  // ── Inyecta el system prompt del agente activo en cada turno ───────────
  pi.on("before_agent_start", async (event, _ctx) => {
    if (!activeAgent) return;
    // event.systemPrompt ya contiene el prompt encadenado de handlers anteriores
    return {
      systemPrompt:
        event.systemPrompt +
        `\n\n---\n## Agente Activo: ${activeAgent.name}\n\n${activeAgent.systemPrompt}`,
    };
  });

  // ── Notificación al arrancar ───────────────────────────────────────────
  pi.on("session_start", async (_event, ctx) => {
    const agents = scanAgents(ctx.cwd);
    if (agents.length === 0) return;
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
}
