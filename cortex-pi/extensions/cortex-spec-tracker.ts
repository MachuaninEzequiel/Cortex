/**
 * cortex-spec-tracker — Tracker de SPECs y Criterios de Aceptación
 *
 * Lee los specs de .cortex/specs/ y muestra un tracker visual
 * de criterios de aceptación en tiempo real durante la implementación.
 *
 * Uso: pi -e extensions/cortex-dashboard.ts -e extensions/cortex-spec-tracker.ts
 */

import type { Extension, PiContext } from "@mariozechner/pi-coding-agent";
import { readFileSync, readdirSync } from "fs";
import { join } from "path";

const extension: Extension = {
  name: "cortex-spec-tracker",
  version: "2.0.0",

  async init(ctx: PiContext) {
    const C = {
      reset: "\x1b[0m",
      bold: "\x1b[1m",
      dim: "\x1b[2m",
      violet: "\x1b[38;5;93m",
      green: "\x1b[38;5;71m",
      red: "\x1b[38;5;196m",
      yellow: "\x1b[38;5;178m",
      muted: "\x1b[38;5;242m",
      cyan: "\x1b[38;5;38m",
    };

    interface Criterion {
      text: string;
      done: boolean;
    }

    interface SpecState {
      name: string;
      objective: string;
      criteria: Criterion[];
      file: string;
    }

    let activeSpec: SpecState | null = null;
    let specFiles: string[] = [];

    // ─── Leer specs de .cortex/specs/ ────────────────────────────────────
    const loadSpecFiles = (): string[] => {
      try {
        const specsDir = join(process.cwd(), ".cortex", "specs");
        return readdirSync(specsDir)
          .filter((f) => f.endsWith(".md"))
          .sort()
          .reverse(); // más reciente primero
      } catch {
        return [];
      }
    };

    const parseSpec = (filePath: string): SpecState | null => {
      try {
        const content = readFileSync(filePath, "utf-8");
        const lines = content.split("\n");

        // Extraer nombre del archivo
        const name = filePath.split("/").pop()?.replace(/^\d{4}-\d{2}-\d{2}-/, "").replace(".md", "") ?? "spec";

        // Extraer objetivo (primera línea después de ## Objetivo)
        let objective = "";
        let inObjective = false;
        const criteria: Criterion[] = [];
        let inCriteria = false;

        for (const line of lines) {
          if (line.startsWith("## Objetivo")) {
            inObjective = true;
            inCriteria = false;
            continue;
          }
          if (line.startsWith("## Criterios")) {
            inObjective = false;
            inCriteria = true;
            continue;
          }
          if (line.startsWith("##")) {
            inObjective = false;
            inCriteria = false;
          }

          if (inObjective && line.trim() && !objective) {
            objective = line.trim();
          }

          if (inCriteria && line.trim().startsWith("- [")) {
            const done = line.includes("- [x]") || line.includes("- [X]");
            const text = line
              .replace(/- \[[ xX]\]\s*/, "")
              .trim();
            if (text) criteria.push({ text, done });
          }
        }

        return { name, objective, criteria, file: filePath };
      } catch {
        return null;
      }
    };

    // ─── Widget del spec activo ───────────────────────────────────────────
    const widget = ctx.ui.createWidget({
      position: "above-editor",
      render: () => {
        if (!activeSpec) {
          return `${C.muted}No hay SPEC activo. Usa /spec-load para cargar uno.${C.reset}`;
        }

        const { name, objective, criteria } = activeSpec;
        const done = criteria.filter((c) => c.done).length;
        const total = criteria.length;
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;

        const progressBar = (() => {
          const filled = Math.round(pct / 5);
          const empty = 20 - filled;
          return (
            `${C.green}${"█".repeat(filled)}${C.reset}` +
            `${C.muted}${"░".repeat(empty)}${C.reset}` +
            ` ${pct}%`
          );
        })();

        const header = `${C.violet}${C.bold}╔ SPEC: ${name}${C.reset}`;
        const obj = `${C.muted}│${C.reset} ${C.cyan}${objective.slice(0, 70)}${C.reset}`;
        const progress = `${C.muted}│${C.reset} Criterios: ${done}/${total} ${progressBar}`;

        const items = criteria.slice(0, 6).map((c) => {
          const icon = c.done
            ? `${C.green}✓${C.reset}`
            : `${C.muted}○${C.reset}`;
          const text = c.done
            ? `${C.muted}${c.text.slice(0, 55)}${C.reset}`
            : c.text.slice(0, 55);
          return `${C.muted}│${C.reset}  ${icon} ${text}`;
        });

        const more =
          criteria.length > 6
            ? `${C.muted}│  ... y ${criteria.length - 6} más${C.reset}`
            : "";

        const footer = `${C.violet}╚${C.reset}${C.muted} /spec-check <n> · /spec-load · /spec-list${C.reset}`;

        return [header, obj, progress, ...items, more, footer]
          .filter(Boolean)
          .join("\n");
      },
    });

    // ─── Comandos de spec ─────────────────────────────────────────────────

    // /spec-list — Lista specs disponibles
    ctx.addCommand("/spec-list", async (_: string) => {
      specFiles = loadSpecFiles();
      if (specFiles.length === 0) {
        ctx.ui.showMessage(
          "No hay specs en .cortex/specs/\nCrea uno con: cortex create-spec <descripción>"
        );
        return;
      }
      const list = specFiles
        .slice(0, 10)
        .map((f, i) => `  ${i + 1}. ${f.split("/").pop()}`)
        .join("\n");
      ctx.ui.showMessage(`Specs disponibles:\n${list}\n\nUsa /spec-load <número>`);
    });

    // /spec-load — Carga un spec por índice o nombre
    ctx.addCommand("/spec-load", async (args: string) => {
      specFiles = loadSpecFiles();

      let targetFile: string | undefined;

      if (!args.trim()) {
        // Carga el más reciente
        targetFile = specFiles[0];
      } else if (/^\d+$/.test(args.trim())) {
        const idx = parseInt(args.trim()) - 1;
        targetFile = specFiles[idx];
      } else {
        targetFile = specFiles.find((f) =>
          f.toLowerCase().includes(args.trim().toLowerCase())
        );
      }

      if (!targetFile) {
        ctx.ui.showMessage("Spec no encontrado. Usa /spec-list para ver opciones.");
        return;
      }

      const spec = parseSpec(join(process.cwd(), ".cortex", "specs", targetFile));
      if (!spec) {
        ctx.ui.showMessage("Error al leer el spec.");
        return;
      }

      activeSpec = spec;
      widget.refresh();
      ctx.ui.showMessage(`Spec cargado: ${spec.name}`);
    });

    // /spec-check — Marca un criterio como completado
    ctx.addCommand("/spec-check", async (args: string) => {
      if (!activeSpec) {
        ctx.ui.showMessage("No hay spec activo. Usa /spec-load primero.");
        return;
      }
      const idx = parseInt(args.trim()) - 1;
      if (isNaN(idx) || idx < 0 || idx >= activeSpec.criteria.length) {
        ctx.ui.showMessage(
          `Criterio inválido. Rango: 1-${activeSpec.criteria.length}`
        );
        return;
      }
      activeSpec.criteria[idx].done = !activeSpec.criteria[idx].done;
      widget.refresh();
    });

    // /spec-check-all — Marca todos los criterios como completados
    ctx.addCommand("/spec-check-all", async (_: string) => {
      if (!activeSpec) return;
      activeSpec.criteria.forEach((c) => (c.done = true));
      widget.refresh();
    });

    // Auto-cargar el spec más reciente al iniciar
    specFiles = loadSpecFiles();
    if (specFiles.length > 0) {
      const spec = parseSpec(
        join(process.cwd(), ".cortex", "specs", specFiles[0])
      );
      if (spec) {
        activeSpec = spec;
        widget.refresh();
      }
    }
  },
};

export default extension;
