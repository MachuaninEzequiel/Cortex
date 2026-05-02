/**
 * agent-chain — Cortex Sequential Pipeline Orchestrator
 *
 * Lee los pipelines definidos en .pi/agents/agent-chain.yaml y los ejecuta
 * como cadenas secuenciales: el output de cada paso se convierte en $INPUT
 * del siguiente. $ORIGINAL siempre contiene el prompt inicial del usuario.
 *
 * Pipelines disponibles en Cortex:
 *   - sddwork  → Ciclo completo: sync → SDDwork → security → test → docs
 *   - hotfix   → Fast Track directo: SDDwork → docs
 *   - refactor → Análisis profundo: sync → explorer → implementer → docs
 *
 * Comandos:
 *   /chain        → selector interactivo de pipeline
 *   /chain-list   → lista todos los pipelines disponibles
 *
 * Uso: pi -e .pi/extensions/agent-chain.ts
 *
 * Basado en disler/pi-vs-claude-code agent-chain.ts, adaptado para Cortex.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { readFileSync, existsSync, readdirSync, mkdirSync } from "fs";
import { join } from "path";
import { spawn } from "child_process";

// ── Types ──────────────────────────────────────────────────────────────────

interface ChainStep {
  agent: string;
  prompt: string;
}

interface ChainDef {
  key: string;
  description: string;
  steps: ChainStep[];
}

interface AgentDef {
  name: string;
  description: string;
  tools: string;
  systemPrompt: string;
}

interface StepState {
  agent: string;
  status: "pending" | "running" | "done" | "error";
  elapsed: number;
  lastLine: string;
}

// ── Parsers ────────────────────────────────────────────────────────────────

function parseAgentFile(filePath: string): AgentDef | null {
  try {
    const raw = readFileSync(filePath, "utf-8");
    const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
    if (!match) return null;

    const fm: Record<string, string> = {};
    for (const line of match[1].split("\n")) {
      const idx = line.indexOf(":");
      if (idx > 0) fm[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
    }

    if (!fm.name) return null;
    return {
      name: fm.name,
      description: fm.description || "",
      tools: fm.tools || "read,grep,find,ls,bash",
      systemPrompt: match[2].trim(),
    };
  } catch {
    return null;
  }
}

function scanAgents(cwd: string): Map<string, AgentDef> {
  const agentsDir = join(cwd, ".pi", "agents");
  const agents = new Map<string, AgentDef>();
  if (!existsSync(agentsDir)) return agents;

  try {
    for (const file of readdirSync(agentsDir)) {
      if (!file.endsWith(".md")) continue;
      const def = parseAgentFile(join(agentsDir, file));
      if (def) agents.set(def.name.toLowerCase(), def);
    }
  } catch {}
  return agents;
}

/**
 * Parser manual de agent-chain.yaml (formato Cortex).
 * Soporta la estructura:
 *   chains:
 *     sddwork:
 *       description: "..."
 *       steps:
 *         - agent: cortex-sync
 *           prompt: |
 *             ...
 */
function parseChainYaml(raw: string): ChainDef[] {
  const chains: ChainDef[] = [];
  const lines = raw.split("\n");
  let i = 0;

  // Salta hasta "chains:"
  while (i < lines.length && !lines[i].match(/^chains:\s*$/)) i++;
  i++; // salta la línea "chains:"

  while (i < lines.length) {
    // Chain key: dos espacios + nombre + ":"
    const chainMatch = lines[i].match(/^  (\S+):\s*$/);
    if (!chainMatch) { i++; continue; }

    const chain: ChainDef = { key: chainMatch[1], description: "", steps: [] };
    chains.push(chain);
    i++;

    // Parsea description y steps dentro del chain
    while (i < lines.length) {
      const line = lines[i];

      // Nuevo chain de nivel superior → salir del loop interno
      if (line.match(/^  \S+:\s*$/) && !line.match(/^\s{4}/)) break;

      // description
      const descMatch = line.match(/^    description:\s*"?([^"]*)"?\s*$/);
      if (descMatch) { chain.description = descMatch[1].trim(); i++; continue; }

      // step: - agent:
      const agentMatch = line.match(/^\s+-\s+agent:\s+(\S+)/);
      if (agentMatch) {
        const step: ChainStep = { agent: agentMatch[1], prompt: "" };
        chain.steps.push(step);
        i++;

        // prompt (puede ser literal block |)
        if (i < lines.length && lines[i].match(/^\s+prompt:\s*\|?\s*$/)) {
          i++;
          const promptLines: string[] = [];
          // Detecta la indentación del primer línea del bloque
          const indentMatch = lines[i]?.match(/^(\s+)/);
          const baseIndent = indentMatch ? indentMatch[1].length : 10;

          while (i < lines.length) {
            const pl = lines[i];
            // Si la línea tiene menos indentación (o es otro step/campo), corta
            if (pl.trim() === "" || (pl.match(/^\s+/) && pl.match(/^\s+/)[0].length >= baseIndent)) {
              promptLines.push(pl.slice(baseIndent));
              i++;
            } else if (pl.match(/^\s+-\s+agent:/) || pl.match(/^\s{4}\w/)) {
              break;
            } else {
              promptLines.push(pl.slice(baseIndent));
              i++;
            }
          }
          step.prompt = promptLines.join("\n").trim();
        } else if (i < lines.length) {
          const inlineMatch = lines[i].match(/^\s+prompt:\s+(.+)$/);
          if (inlineMatch) {
            step.prompt = inlineMatch[1].replace(/^["']|["']$/g, "");
            i++;
          }
        }
        continue;
      }

      i++;
    }
  }

  return chains;
}

// ── Widget helpers ─────────────────────────────────────────────────────────

const STATUS_ICON: Record<string, string> = {
  pending: "○",
  running: "◉",
  done: "✓",
  error: "✗",
};

const STATUS_COLOR: Record<string, string> = {
  pending: "dim",
  running: "accent",
  done: "success",
  error: "error",
};

function renderStepCard(
  state: StepState,
  colW: number,
  theme: any
): string[] {
  const inner = colW - 2;
  const clip = (s: string, max: number) =>
    s.length > max ? s.slice(0, max - 3) + "…" : s;

  const name = state.agent.replace(/^cortex-/, "").replace(/-/g, " ");
  const nameStr = theme.fg("accent", theme.bold(clip(name, inner)));
  const nameLen = Math.min(name.length, inner);

  const icon = STATUS_ICON[state.status] ?? "?";
  const elapsed = state.elapsed > 0 ? ` ${Math.round(state.elapsed / 1000)}s` : "";
  const statusRaw = `${icon} ${state.status}${elapsed}`;
  const statusStr = theme.fg(STATUS_COLOR[state.status] ?? "dim", statusRaw);
  const statusLen = statusRaw.length;

  const workRaw = state.lastLine
    ? clip(state.lastLine, Math.min(50, inner - 1))
    : "—";
  const workStr = state.lastLine
    ? theme.fg("muted", workRaw)
    : theme.fg("dim", workRaw);
  const workLen = workRaw.length;

  const top = "┌" + "─".repeat(inner) + "┐";
  const bot = "└" + "─".repeat(inner) + "┘";
  const row = (content: string, visLen: number) =>
    theme.fg("dim", "│") +
    content +
    " ".repeat(Math.max(0, inner - visLen)) +
    theme.fg("dim", "│");

  return [
    theme.fg("dim", top),
    row(" " + nameStr, 1 + nameLen),
    row(" " + statusStr, 1 + statusLen),
    row(" " + workStr, 1 + workLen),
    theme.fg("dim", bot),
  ];
}

// ── Subprocess runner ──────────────────────────────────────────────────────

function runAgentStep(
  agent: AgentDef,
  task: string,
  sessionFile: string,
  model: string,
  onProgress: (line: string) => void
): Promise<{ output: string; ok: boolean; elapsed: number }> {
  const args = [
    "--mode", "json",
    "-p",
    "--no-extensions",
    "--model", model,
    "--tools", agent.tools,
    "--thinking", "off",
    "--append-system-prompt", agent.systemPrompt,
    "--session", sessionFile,
    task,
  ];

  const start = Date.now();
  const chunks: string[] = [];

  return new Promise((resolve) => {
    const proc = spawn("pi", args, {
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env },
    });

    let buf = "";
    proc.stdout!.setEncoding("utf-8");
    proc.stdout!.on("data", (chunk: string) => {
      buf += chunk;
      const lines = buf.split("\n");
      buf = lines.pop() || "";
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const ev = JSON.parse(line);
          if (ev.type === "message_update") {
            const delta = ev.assistantMessageEvent;
            if (delta?.type === "text_delta" && delta.delta) {
              chunks.push(delta.delta);
              const full = chunks.join("");
              const last = full.split("\n").filter((l: string) => l.trim()).pop() || "";
              onProgress(last);
            }
          }
        } catch {}
      }
    });

    proc.stderr!.setEncoding("utf-8");
    proc.stderr!.on("data", () => {});

    proc.on("close", (code) => {
      resolve({
        output: chunks.join(""),
        ok: code === 0,
        elapsed: Date.now() - start,
      });
    });
  });
}

// ── Extension ──────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let chains: ChainDef[] = [];
  let agents: Map<string, AgentDef> = new Map();
  let activeChain: ChainDef | null = null;
  let stepStates: StepState[] = [];
  let sessionDir = "";

  function activateChain(chain: ChainDef, ctx: any) {
    activeChain = chain;
    stepStates = chain.steps.map(s => ({
      agent: s.agent,
      status: "pending" as const,
      elapsed: 0,
      lastLine: "",
    }));
    updateWidget(ctx);
  }

  function loadConfig(cwd: string) {
    agents = scanAgents(cwd);
    sessionDir = join(cwd, ".pi", "agent-sessions");
    if (!existsSync(sessionDir)) {
      try { mkdirSync(sessionDir, { recursive: true }); } catch {}
    }

    const chainPath = join(cwd, ".pi", "agents", "agent-chain.yaml");
    if (existsSync(chainPath)) {
      try {
        chains = parseChainYaml(readFileSync(chainPath, "utf-8"));
      } catch (e) {
        chains = [];
      }
    }
  }

  function updateWidget(ctx: any) {
    ctx.ui.setWidget("cortex-chain", (_tui: any, theme: any) => {
      return {
        render(width: number): string[] {
          if (!activeChain || stepStates.length === 0) {
            return [theme.fg("dim", " Sin pipeline activo. Usa /chain para seleccionar.")];
          }

          const arrowW = 5; // " ──▶ "
          const cols = stepStates.length;
          const colW = Math.max(14, Math.floor((width - arrowW * (cols - 1)) / cols));
          const cards = stepStates.map(s => renderStepCard(s, colW, theme));
          const cardH = cards[0].length;
          const arrowRow = 2;
          const out: string[] = [];

          for (let row = 0; row < cardH; row++) {
            let line = cards[0][row];
            for (let c = 1; c < cols; c++) {
              line += row === arrowRow
                ? theme.fg("dim", " ──▶ ")
                : " ".repeat(arrowW);
              line += cards[c][row];
            }
            out.push(line);
          }
          return out;
        },
        invalidate() {},
      };
    });
  }

  async function executeChain(chain: ChainDef, initialInput: string, ctx: any) {
    activeChain = chain;
    stepStates = chain.steps.map(s => ({
      agent: s.agent,
      status: "pending" as const,
      elapsed: 0,
      lastLine: "",
    }));
    updateWidget(ctx);

    const modelObj = ctx.model;
    const model = modelObj
      ? `${modelObj.provider}/${modelObj.id}`
      : "anthropic/claude-sonnet-4-20250514";

    let prevOutput = initialInput;

    for (let i = 0; i < chain.steps.length; i++) {
      const step = chain.steps[i];
      const state = stepStates[i];
      const agentDef = agents.get(step.agent.toLowerCase());

      if (!agentDef) {
        state.status = "error";
        state.lastLine = `Agente "${step.agent}" no encontrado en .pi/agents/`;
        updateWidget(ctx);
        ctx.ui.notify(`⚠ ${state.lastLine}`, "warning");
        break;
      }

      state.status = "running";
      updateWidget(ctx);

      // Sustituye las variables de template
      const task = step.prompt
        .replace(/\$INPUT/g, prevOutput)
        .replace(/\$ORIGINAL/g, initialInput);

      const sessionFile = join(sessionDir, `chain-${step.agent}.json`);

      const tickTimer = setInterval(() => {
        state.elapsed += 1000;
        updateWidget(ctx);
      }, 1000);

      const result = await runAgentStep(
        agentDef,
        task,
        sessionFile,
        model,
        (line) => {
          state.lastLine = line;
          updateWidget(ctx);
        }
      );

      clearInterval(tickTimer);
      state.status = result.ok ? "done" : "error";
      state.elapsed = result.elapsed;
      updateWidget(ctx);

      if (!result.ok) {
        ctx.ui.notify(`⚠ Paso ${i + 1} (${step.agent}) terminó con error`, "warning");
        break;
      }

      prevOutput = result.output || prevOutput;
    }

    const allDone = stepStates.every(s => s.status === "done");
    ctx.ui.notify(
      allDone
        ? `✓ Pipeline "${chain.key}" completado`
        : `⚠ Pipeline "${chain.key}" terminado con errores`,
      allDone ? "success" : "warning"
    );
  }

  // ── /chain — selector de pipeline ──
  pi.registerCommand("chain", {
    description: "Selecciona y ejecuta un pipeline Cortex",
    async handler(args: string, ctx: any) {
      const cwd = process.cwd();
      loadConfig(cwd);

      if (chains.length === 0) {
        ctx.ui.notify("⚠ No se encontraron pipelines en .pi/agents/agent-chain.yaml", "warning");
        return;
      }

      // ctx.ui.select recibe título y array de STRINGS simples
      const options: string[] = chains.map(c => {
        const steps = c.steps.map(s => s.agent.replace("cortex-", "")).join("→");
        return `${c.key}  [${steps}]  ${c.description ? "— " + c.description : ""}`;
      });

      const selected: string | undefined = await ctx.ui.select(
        "⬡ Cortex — Seleccionar Pipeline",
        options
      );

      if (selected === undefined) {
        ctx.ui.notify("Selección cancelada", "info");
        return;
      }

      const chainKey = selected.split("  ")[0].trim();
      const chain = chains.find(c => c.key === chainKey);
      if (!chain) {
        ctx.ui.notify("⚠ Pipeline no encontrado", "warning");
        return;
      }

      // Si el usuario pasó args, úsalos como input; si no, pide confirmación de tarea
      const input = args.trim();
      if (!input) {
        ctx.ui.notify(`Pipeline "${chain.key}" seleccionado. Escribí tu tarea en el chat y Pi la ejecutará en el pipeline.`, "info");
        pi.sendMessage(`**Pipeline activo:** \`${chain.key}\`\n\n${chain.description}\n\nPasos: ${chain.steps.map(s => `\`${s.agent}\``).join(" → ")}\n\n*Escribí la tarea y el pipeline se ejecutará automáticamente.*`);
        // Registra el chain como activo para que el próximo mensaje lo dispare
        activeChain = chain;
        activateChain(chain, ctx);
        return;
      }

      await executeChain(chain, input, ctx);
    },
  });

  // ── /chain-list — listar pipelines ──
  pi.registerCommand("chain-list", {
    description: "Lista todos los pipelines Cortex disponibles",
    handler(_args: string, ctx: any) {
      const cwd = process.cwd();
      loadConfig(cwd);

      if (chains.length === 0) {
        ctx.ui.notify("No hay pipelines definidos en agent-chain.yaml", "warning");
        return;
      }

      const lines = chains.map(c => {
        const stepNames = c.steps.map(s => s.agent.replace("cortex-", "")).join(" → ");
        return `**${c.key}** — ${c.description}\n  \`${stepNames}\``;
      });

      pi.sendMessage(`## Pipelines Cortex\n\n${lines.join("\n\n")}`);
    },
  });

  // ── Carga config al arrancar ──
  pi.on("session_start", (_event: any, ctx: any) => {
    const cwd = process.cwd();
    loadConfig(cwd);
    if (chains.length > 0) {
      ctx.ui.notify(
        `⬡ Cortex Chain: ${chains.length} pipeline${chains.length !== 1 ? "s" : ""} → /chain para ejecutar`,
        "info"
      );
    }
  });
}
