/**
 * cortex-memory-widget — Widget de Memoria RRF para Pi
 *
 * Muestra en tiempo real los resultados de búsqueda en la memoria híbrida
 * de Cortex (episódica + semántica) antes de cada turno del agente.
 *
 * Uso: pi -e extensions/cortex-dashboard.ts -e extensions/cortex-memory-widget.ts
 */

import type { Extension, PiContext } from "@mariozechner/pi-coding-agent";

const extension: Extension = {
  name: "cortex-memory-widget",
  version: "2.0.0",

  async init(ctx: PiContext) {
    const C = {
      reset: "\x1b[0m",
      bold: "\x1b[1m",
      dim: "\x1b[2m",
      blue: "\x1b[94m",
      orange: "\x1b[33m",
      green: "\x1b[32m",
      muted: "\x1b[90m",
      cyan: "\x1b[36m",
      yellow: "\x1b[93m",
    };

    let lastResults: MemoryResult[] = [];
    let isSearching = false;
    let widgetVisible = true;

    interface MemoryResult {
      score: number;
      source: "episodic" | "semantic";
      content: string;
      timestamp?: string;
    }

    // ─── Widget overlay ───────────────────────────────────────────────────
    const widget = ctx.ui.createWidget({
      position: "above-editor",
      render: () => {
        if (!widgetVisible || lastResults.length === 0) return "";

        const sourceIcon = (s: string) =>
          s === "episodic"
            ? `${C.orange}EP${C.reset}`
            : `${C.cyan}SM${C.reset}`;

        const truncate = (s: string, n: number) =>
          s.length > n ? s.slice(0, n) + "…" : s;

        const header = `${C.blue}${C.bold}╔ CORTEX MEMORY — RRF Results${C.reset}${isSearching ? ` ${C.muted}[searching...]${C.reset}` : ""}`;
        const rows = lastResults.slice(0, 5).map((r, i) => {
          const score = `${C.green}${r.score.toFixed(2)}${C.reset}`;
          const src = sourceIcon(r.source);
          const content = truncate(r.content, 60);
          const ts = r.timestamp ? ` ${C.muted}(${r.timestamp.slice(0, 10)})${C.reset}` : "";
          return `${C.muted}│${C.reset} ${i + 1}. [${score}] ${src} ${content}${ts}`;
        });
        const footer = `${C.blue}╚${C.reset}${C.muted} /mem-toggle to hide · /mem-search <query> to search${C.reset}`;

        return [header, ...rows, footer].join("\n");
      },
    });

    // ─── Búsqueda en memoria Cortex ───────────────────────────────────────
    const searchMemory = async (query: string) => {
      if (!query.trim()) return;
      isSearching = true;
      widget.refresh();

      try {
        const result = await ctx.tools.bash({
          command: `cortex search "${query.replace(/"/g, "'")}" --format json 2>/dev/null || cortex search "${query.replace(/"/g, "'")}" 2>/dev/null`,
        });

        if (result.stdout) {
          // Intentar parsear JSON, si no, parsear texto plano
          try {
            const parsed = JSON.parse(result.stdout);
            lastResults = parsed.results ?? parsed ?? [];
          } catch {
            // Parsear output texto de cortex search
            const lines = result.stdout.split("\n").filter((l: string) => l.includes("]"));
            lastResults = lines.slice(0, 8).map((line: string) => {
              const scoreMatch = line.match(/\[(\d+\.\d+)\]/);
              const sourceMatch = line.match(/EPISODIC|SEMANTIC/i);
              const score = scoreMatch ? parseFloat(scoreMatch[1]) : 0.5;
              const source = (
                sourceMatch?.[0]?.toLowerCase() === "episodic" ? "episodic" : "semantic"
              ) as "episodic" | "semantic";
              const content = line.replace(/.*EPISODIC:|.*SEMANTIC:/i, "").trim();
              return { score, source, content };
            });
          }
        }
      } catch {
        lastResults = [];
      } finally {
        isSearching = false;
        widget.refresh();
      }
    };

    // ─── Auto-búsqueda en cada input del usuario ──────────────────────────
    ctx.on("input", async (message: string) => {
      // Extrae palabras clave del mensaje (>4 chars, no comandos)
      if (message.startsWith("/")) return;
      const keywords = message
        .split(/\s+/)
        .filter((w: string) => w.length > 4 && !w.startsWith("http"))
        .slice(0, 3)
        .join(" ");

      if (keywords) {
        await searchMemory(keywords);
      }
    });

    // ─── Comandos de memoria ──────────────────────────────────────────────

    ctx.addCommand("/mem-search", async (args: string) => {
      await searchMemory(args);
    });

    ctx.addCommand("/mem-toggle", async (_: string) => {
      widgetVisible = !widgetVisible;
      widget.refresh();
      ctx.ui.showMessage(
        `Memory widget ${widgetVisible ? "visible" : "hidden"}`
      );
    });

    ctx.addCommand("/mem-clear", async (_: string) => {
      lastResults = [];
      widget.refresh();
    });

    // /remember — Guarda una memoria episódica rápida
    ctx.addCommand("/remember", async (args: string) => {
      if (!args.trim()) {
        ctx.ui.showMessage("Uso: /remember <texto a memorizar>");
        return;
      }
      ctx.sendMessage(
        `Ejecuta: cortex remember "${args.trim()}" y confirma que fue guardado exitosamente.`
      );
    });

    // /context — Enriquece contexto con archivos modificados
    ctx.addCommand("/context", async (_: string) => {
      ctx.sendMessage(
        "Ejecuta: cortex context y muestra el contexto recuperado relevante para los archivos modificados."
      );
    });
  },
};

export default extension;
