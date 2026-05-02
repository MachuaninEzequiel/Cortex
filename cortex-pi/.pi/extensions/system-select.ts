/**
 * system-select — Cortex Agent Persona Switcher
 *
 * Comando /system: muestra un selector interactivo con todos los agentes
 * definidos en .pi/agents/. Al seleccionar uno, inyecta el system prompt
 * del agente en el siguiente turno via before_agent_start.
 *
 * API real de Pi v0.70:
 *   ctx.ui.select(title: string, options: string[]) → Promise<string | undefined>
 *   ctx.ui.confirm(title: string, message: string)  → Promise<boolean>
 *   ctx.ui.notify(message: string, level)           → void
 *   ctx.ui.setStatus(key, text)                     → void
 *   pi.sendMessage(text)                            → void  (inyecta como assistant msg)
 *   pi.sendUserMessage(text)                        → void
 *
 * Uso: pi -e .pi/extensions/system-select.ts
 * Dentro de Pi: /system
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { readFileSync, existsSync, readdirSync } from "fs";
import { join } from "path";

interface AgentDef {
  name: string;
  description: string;
  systemPrompt: string;
  filePath: string;
}

// ── Parsea frontmatter + body de un .md de agente ─────────────────────────
function parseAgentFile(filePath: string): AgentDef | null {
  try {
    const raw = readFileSync(filePath, "utf-8");
    const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);

    if (!match) {
      const name = filePath.split(/[\\/]/).pop()!.replace(".md", "");
      return { name, description: "(sin descripción)", systemPrompt: raw.trim(), filePath };
    }

    const fm: Record<string, string> = {};
    for (const line of match[1].split("\n")) {
      const idx = line.indexOf(":");
      if (idx > 0) fm[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
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

// ── Escanea .pi/agents/ ────────────────────────────────────────────────────
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

  // Ordenar: orquestador primero
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

  // Inyecta el system prompt del agente activo en cada turno
  pi.on("before_agent_start", async (_event, ctx) => {
    if (!activeAgent) return;
    // Agrega el system prompt del agente como instrucción adicional al inicio
    return {
      appendSystemPrompt: `\n\n---\n## Agente Activo: ${activeAgent.name}\n\n${activeAgent.systemPrompt}`,
    };
  });

  // Notificación al arrancar
  pi.on("session_start", async (_event, ctx) => {
    const agents = scanAgents(ctx.cwd);
    if (agents.length === 0) return;
    ctx.ui.notify(
      `⬡ Cortex: ${agents.length} agentes disponibles → /system para seleccionar`,
      "info"
    );
  });

  // ── Comando /system ──────────────────────────────────────────────────────
  pi.registerCommand("system", {
    description: "Selecciona un agente Cortex como persona activa",
    async handler(args: string, ctx: any) {
      const agents = scanAgents(ctx.cwd);

      if (agents.length === 0) {
        ctx.ui.notify("⚠ No se encontraron agentes en .pi/agents/", "warning");
        return;
      }

      // Opción extra para desactivar el agente actual
      const noneOption = "(ninguno — sistema por defecto)";

      // ctx.ui.select recibe título y array de STRINGS simples
      const options: string[] = [
        noneOption,
        ...agents.map(a => `${a.name}  —  ${a.description.slice(0, 60)}${a.description.length > 60 ? "…" : ""}`)
      ];

      const selected: string | undefined = await ctx.ui.select(
        "⬡ Cortex — Seleccionar Agente",
        options
      );

      if (selected === undefined) {
        ctx.ui.notify("Selección cancelada", "info");
        return;
      }

      if (selected === noneOption) {
        activeAgent = null;
        ctx.ui.notify("✓ Sistema por defecto restaurado", "success");
        ctx.ui.setStatus("cortex-agent", "");
        return;
      }

      // Encuentra el agente que coincide con la opción seleccionada
      const agentName = selected.split("  —  ")[0].trim();
      const agent = agents.find(a => a.name === agentName);
      if (!agent) {
        ctx.ui.notify("⚠ Agente no encontrado", "warning");
        return;
      }

      activeAgent = agent;
      ctx.ui.notify(`✓ Agente activo: ${agent.name}`, "success");
      ctx.ui.setStatus("cortex-agent", `⬡ ${agent.name}`);

      // Muestra descripción en el chat via un mensaje del sistema
      pi.sendMessage(
        `**Agente cargado:** \`${agent.name}\`\n\n> ${agent.description}\n\n*El system prompt de este agente se inyectará en el próximo turno.*`
      );
    },
  });

  // ── Comando /system-list: muestra todos los agentes disponibles ───────────
  pi.registerCommand("system-list", {
    description: "Lista todos los agentes Cortex disponibles",
    handler(args: string, ctx: any) {
      const agents = scanAgents(ctx.cwd);
      if (agents.length === 0) {
        ctx.ui.notify("No hay agentes en .pi/agents/", "warning");
        return;
      }
      const active = activeAgent?.name ?? "(ninguno)";
      const lines = agents.map(a => {
        const marker = a.name === activeAgent?.name ? " ◀ activo" : "";
        return `- **${a.name}**${marker}\n  ${a.description}`;
      });
      pi.sendMessage(
        `## Agentes Cortex\n\n**Activo:** \`${active}\`\n\n${lines.join("\n\n")}`
      );
    },
  });
}
