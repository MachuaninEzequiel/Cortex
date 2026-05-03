/**
 * cortex-tools — Cortex CLI como tools nativas de Pi
 *
 * Registra los comandos reales del CLI de Cortex v2.1 como tools nativas
 * de Pi. Los agentes pueden llamarlas igual que cualquier otra tool.
 *
 * Comandos reales verificados con `cortex --help`:
 *   search          → Query both memory layers
 *   remember        → Store a new episodic memory
 *   forget          → Delete an episodic memory by ID
 *   context         → Get enriched context for current work
 *   save-session    → Persist a structured session note into the vault
 *   create-spec     → Persist an implementation spec into the vault
 *   stats           → Print memory store statistics
 *   doctor          → Validate Cortex runtime prerequisites
 *   agent-guidelines→ Display agent behavior guidelines
 *   sync-vault      → Re-index the markdown vault
 *
 * Uso: pi -e .pi/extensions/cortex-tools.ts
 * Comando en Pi: /cortex-tools
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Text } from "@mariozechner/pi-tui";
import { Type } from "@sinclair/typebox";
import { existsSync } from "fs";
import { join } from "path";
import { homedir } from "os";
import { execFileSync, spawnSync } from "child_process";

// ── Resuelve el ejecutable de cortex ──────────────────────────────────────

function resolveCortexBin(): string {
  if (process.env.CORTEX_BIN && existsSync(process.env.CORTEX_BIN)) {
    return process.env.CORTEX_BIN;
  }

  const isWin = process.platform === "win32";
  const binName = isWin ? "cortex.exe" : "cortex";
  const scriptDir = isWin ? "Scripts" : "bin";
  const home = homedir();
  const candidates: string[] = [];

  // 1. pipx environment --value PIPX_LOCAL_VENVS (más confiable)
  try {
    const venvs = execFileSync("pipx", ["environment", "--value", "PIPX_LOCAL_VENVS"], {
      encoding: "utf-8", timeout: 5000,
    }).trim();
    if (venvs) {
      candidates.push(join(venvs, "cortex-memory", scriptDir, binName));
      candidates.push(join(venvs, "cortex", scriptDir, binName));
    }
  } catch {}

  // 2. Ruta derivada estándar de pipx en Windows (%USERPROFILE%\pipx\venvs)
  candidates.push(join(home, "pipx", "venvs", "cortex-memory", scriptDir, binName));
  candidates.push(join(home, "pipx", "venvs", "cortex", scriptDir, binName));

  if (isWin) {
    const localAppData = process.env.LOCALAPPDATA ?? join(home, "AppData", "Local");
    candidates.push(join(localAppData, "pipx", "pipx", "venvs", "cortex-memory", "Scripts", binName));
  } else {
    candidates.push(join(home, ".local", "pipx", "venvs", "cortex-memory", "bin", binName));
  }

  // 3. ~/.local/bin donde pipx instala los scripts globales
  candidates.push(join(home, ".local", "bin", binName));

  for (const c of candidates) {
    if (existsSync(c)) return c;
  }

  // 4. Fallback al PATH
  return binName;
}

// ── Runner ────────────────────────────────────────────────────────────────

function runCortex(
  bin: string,
  args: string[],
  cwd: string,
  configPath: string,
): { stdout: string; stderr: string; ok: boolean } {
  try {
    const result = spawnSync(bin, args, {
      cwd,
      encoding: "utf-8",
      timeout: 60_000,
      env: {
        ...process.env as Record<string, string>,
        CORTEX_CONFIG_PATH: configPath,
      },
    });
    return {
      stdout: result.stdout ?? "",
      stderr: result.stderr ?? "",
      ok: result.status === 0,
    };
  } catch (err: any) {
    return { stdout: "", stderr: err.message, ok: false };
  }
}

function fmt(stdout: string, stderr: string, ok: boolean): string {
  const out = stdout.trim();
  const err = stderr.trim();
  if (out) return out;
  if (!ok && err) return `Error: ${err}`;
  return ok ? "(completado sin output)" : `Falló: ${err || "sin detalles"}`;
}

// ── Extension ──────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  let bin = "";
  let cwd = "";
  let cfg = "";

  pi.registerMessageRenderer("cortex-tools", (message, _options, theme) => {
    const content = typeof message.content === "string" ? message.content : "";
    return new Text(theme.fg("cyan", "⬡ cortex: ") + content, 0, 0);
  });

  pi.on("session_start", async (_event, ctx) => {
    cwd = ctx.cwd;
    cfg = join(cwd, "config.yaml");
    bin = resolveCortexBin();

    const check = spawnSync(bin, ["--version"], {
      encoding: "utf-8", timeout: 5000,
      env: { ...process.env as Record<string, string> },
    });

    if (check.status === 0 || (check.stderr ?? "").includes("cortex")) {
      const ver = ((check.stdout ?? "") + (check.stderr ?? "")).trim().split("\n")[0];
      ctx.ui.notify(`✓ Cortex CLI: ${ver || "OK"} — tools cortex_* disponibles`, "success");
    } else {
      ctx.ui.notify(`⚠ Cortex CLI no encontrado (${bin}) — corré /cortex-tools para diagnosticar`, "warning");
    }
  });

  // ── cortex_search ────────────────────────────────────────────────────────
  pi.registerTool({
    name: "cortex_search",
    label: "Cortex: Buscar memoria",
    description: "Busca en la memoria híbrida de Cortex (episódica + semántica). Recupera contexto relevante antes de implementar.",
    parameters: Type.Object({
      query: Type.String({ description: "Consulta en lenguaje natural" }),
      limit: Type.Optional(Type.Number({ description: "Máximo de resultados (default: 10)" })),
    }),
    async execute(_id, params) {
      const args = ["search", params.query];
      if (params.limit) args.push("--limit", String(params.limit));
      const r = runCortex(bin, args, cwd, cfg);
      return { content: [{ type: "text" as const, text: fmt(r.stdout, r.stderr, r.ok) }] };
    },
  });

  // ── cortex_context ───────────────────────────────────────────────────────
  pi.registerTool({
    name: "cortex_context",
    label: "Cortex: Contexto enriquecido",
    description: "Obtiene contexto enriquecido para el trabajo actual. Equivale al pre-flight de cortex-sync.",
    parameters: Type.Object({
      ticket: Type.Optional(Type.String({ description: "ID o descripción del ticket actual" })),
    }),
    async execute(_id, params) {
      const args = ["context"];
      if (params.ticket) args.push("--ticket", params.ticket);
      const r = runCortex(bin, args, cwd, cfg);
      return { content: [{ type: "text" as const, text: fmt(r.stdout, r.stderr, r.ok) }] };
    },
  });

  // ── cortex_remember ──────────────────────────────────────────────────────
  pi.registerTool({
    name: "cortex_remember",
    label: "Cortex: Guardar memoria episódica",
    description: "Guarda una decisión, aprendizaje o contexto importante en la memoria episódica de Cortex.",
    parameters: Type.Object({
      content: Type.String({ description: "Contenido a guardar en memoria" }),
    }),
    async execute(_id, params) {
      const r = runCortex(bin, ["remember", params.content], cwd, cfg);
      return { content: [{ type: "text" as const, text: fmt(r.stdout, r.stderr, r.ok) }] };
    },
  });

  // ── cortex_save_session ──────────────────────────────────────────────────
  pi.registerTool({
    name: "cortex_save_session",
    label: "Cortex: Guardar sesión",
    description: "Persiste una nota estructurada de la sesión en el vault. Usar al finalizar una sesión de trabajo.",
    parameters: Type.Object({
      content: Type.String({ description: "Resumen estructurado de la sesión en Markdown" }),
    }),
    async execute(_id, params) {
      const r = runCortex(bin, ["save-session", params.content], cwd, cfg);
      return { content: [{ type: "text" as const, text: fmt(r.stdout, r.stderr, r.ok) }] };
    },
  });

  // ── cortex_create_spec ───────────────────────────────────────────────────
  pi.registerTool({
    name: "cortex_create_spec",
    label: "Cortex: Crear spec",
    description: "Persiste una especificación técnica en el vault. Usado por cortex-sync al finalizar el pre-flight.",
    parameters: Type.Object({
      content: Type.String({ description: "Contenido completo de la spec en Markdown" }),
    }),
    async execute(_id, params) {
      const r = runCortex(bin, ["create-spec", params.content], cwd, cfg);
      return { content: [{ type: "text" as const, text: fmt(r.stdout, r.stderr, r.ok) }] };
    },
  });

  // ── cortex_forget ────────────────────────────────────────────────────────
  pi.registerTool({
    name: "cortex_forget",
    label: "Cortex: Olvidar memoria",
    description: "Elimina una memoria episódica por su ID.",
    parameters: Type.Object({
      id: Type.String({ description: "ID de la memoria a eliminar" }),
    }),
    async execute(_id, params) {
      const r = runCortex(bin, ["forget", params.id], cwd, cfg);
      return { content: [{ type: "text" as const, text: fmt(r.stdout, r.stderr, r.ok) }] };
    },
  });

  // ── cortex_stats ─────────────────────────────────────────────────────────
  pi.registerTool({
    name: "cortex_stats",
    label: "Cortex: Estadísticas de memoria",
    description: "Muestra estadísticas del almacén de memoria de Cortex.",
    parameters: Type.Object({}),
    async execute(_id) {
      const r = runCortex(bin, ["stats"], cwd, cfg);
      return { content: [{ type: "text" as const, text: fmt(r.stdout, r.stderr, r.ok) }] };
    },
  });

  // ── cortex_doctor ────────────────────────────────────────────────────────
  pi.registerTool({
    name: "cortex_doctor",
    label: "Cortex: Diagnóstico del sistema",
    description: "Valida los prerequisitos de runtime y el estado de governance de Cortex.",
    parameters: Type.Object({}),
    async execute(_id) {
      const r = runCortex(bin, ["doctor"], cwd, cfg);
      return { content: [{ type: "text" as const, text: fmt(r.stdout, r.stderr, r.ok) }] };
    },
  });

  // ── cortex_agent_guidelines ──────────────────────────────────────────────
  pi.registerTool({
    name: "cortex_agent_guidelines",
    label: "Cortex: Guías del agente",
    description: "Muestra las guías de comportamiento del agente Cortex para el proyecto actual.",
    parameters: Type.Object({}),
    async execute(_id) {
      const r = runCortex(bin, ["agent-guidelines"], cwd, cfg);
      return { content: [{ type: "text" as const, text: fmt(r.stdout, r.stderr, r.ok) }] };
    },
  });

  // ── cortex_sync_vault ────────────────────────────────────────────────────
  pi.registerTool({
    name: "cortex_sync_vault",
    label: "Cortex: Sincronizar vault",
    description: "Re-indexa el vault de Markdown en la memoria semántica de Cortex.",
    parameters: Type.Object({}),
    async execute(_id) {
      const r = runCortex(bin, ["sync-vault"], cwd, cfg);
      return { content: [{ type: "text" as const, text: fmt(r.stdout, r.stderr, r.ok) }] };
    },
  });

  // ── /cortex-tools ────────────────────────────────────────────────────────
  pi.registerCommand("cortex-tools", {
    description: "Lista las tools de Cortex y verifica el CLI",
    handler(_args, ctx) {
      const check = spawnSync(bin, ["--version"], {
        encoding: "utf-8", timeout: 5000,
        env: { ...process.env as Record<string, string> },
      });
      const ver = ((check.stdout ?? "") + (check.stderr ?? "")).trim().split("\n")[0] || "desconocida";
      const status = check.status === 0 ? "✓ OK" : "✗ NO DISPONIBLE";

      pi.sendMessage({
        customType: "cortex-tools",
        content: [
          `Cortex CLI: ${bin}`,
          `Estado: ${status}  Versión: ${ver}`,
          `Config: ${cfg}`,
          "",
          "Tools disponibles:",
          "  cortex_search           — buscar en memoria híbrida",
          "  cortex_context          — contexto enriquecido (pre-flight)",
          "  cortex_remember         — guardar memoria episódica",
          "  cortex_save_session     — persistir sesión en vault",
          "  cortex_create_spec      — crear spec en vault",
          "  cortex_forget           — eliminar memoria por ID",
          "  cortex_stats            — estadísticas de memoria",
          "  cortex_doctor           — diagnóstico del sistema",
          "  cortex_agent_guidelines — guías del agente",
          "  cortex_sync_vault       — re-indexar vault",
        ].join("\n"),
        display: true,
      });
    },
  });
}
