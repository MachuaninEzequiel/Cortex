/**
 * damage-control — Cortex Safety Auditor en tiempo real
 *
 * Intercepta cada llamada a bash y la evalúa contra las reglas definidas
 * en .pi/damage-control-rules.yaml antes de ejecutarla.
 *
 * Reglas que aplica:
 *   bashToolPatterns   → bloquea o pide confirmación en comandos peligrosos
 *   zeroAccessPaths    → bloquea acceso total a archivos sensibles (.env, .ssh, *.pem)
 *   readOnlyPaths      → permite leer, bloquea escritura en lockfiles y /etc/
 *   noDeletePaths      → bloquea borrado de .git/, README.md, Dockerfiles
 *
 * Además: protege los archivos críticos del vault de Cortex.
 *
 * Uso: pi -e .pi/extensions/damage-control.ts
 *
 * Basado en disler/pi-vs-claude-code damage-control.ts, adaptado para Cortex.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Text } from "@mariozechner/pi-tui";
import { readFileSync, existsSync } from "fs";
import { join } from "path";

// ── Types ──────────────────────────────────────────────────────────────────

interface BashPattern {
  pattern: string;
  reason: string;
  ask?: boolean;  // true = pide confirmación en vez de bloquear directamente
}

interface DamageControlRules {
  bashToolPatterns?: BashPattern[];
  zeroAccessPaths?: string[];
  readOnlyPaths?: string[];
  noDeletePaths?: string[];
}

// ── YAML parser mínimo para las reglas ────────────────────────────────────

function parseRulesYaml(raw: string): DamageControlRules {
  const rules: DamageControlRules = {
    bashToolPatterns: [],
    zeroAccessPaths: [],
    readOnlyPaths: [],
    noDeletePaths: [],
  };

  const lines = raw.split("\n");
  let section: keyof DamageControlRules | null = null;
  let currentPattern: BashPattern | null = null;

  for (const line of lines) {
    if (line.startsWith("#") || line.trim() === "") continue;

    // Sección principal
    const sectionMatch = line.match(/^(\w[\w-]*):\s*$/);
    if (sectionMatch) {
      if (currentPattern && section === "bashToolPatterns") {
        rules.bashToolPatterns!.push(currentPattern);
        currentPattern = null;
      }
      section = sectionMatch[1] as keyof DamageControlRules;
      continue;
    }

    if (!section) continue;

    // Lista simple de strings (zeroAccessPaths, readOnlyPaths, noDeletePaths)
    if (section !== "bashToolPatterns") {
      const itemMatch = line.match(/^\s+-\s+"?([^"]+)"?\s*$/);
      if (itemMatch) {
        (rules[section] as string[]).push(itemMatch[1].trim());
      }
      continue;
    }

    // bashToolPatterns: cada item tiene pattern, reason, ask?
    const listItem = line.match(/^\s+-\s+pattern:\s+"?([^"]+)"?\s*$/);
    if (listItem) {
      if (currentPattern) rules.bashToolPatterns!.push(currentPattern);
      currentPattern = { pattern: listItem[1], reason: "" };
      continue;
    }
    const reasonMatch = line.match(/^\s+reason:\s+"?([^"]+)"?\s*$/);
    if (reasonMatch && currentPattern) {
      currentPattern.reason = reasonMatch[1];
      continue;
    }
    const askMatch = line.match(/^\s+ask:\s+(true|false)\s*$/);
    if (askMatch && currentPattern) {
      currentPattern.ask = askMatch[1] === "true";
    }
  }
  if (currentPattern && section === "bashToolPatterns") {
    rules.bashToolPatterns!.push(currentPattern);
  }

  return rules;
}

// ── Reglas por defecto de Cortex (si no existe el YAML) ───────────────────

const DEFAULT_RULES: DamageControlRules = {
  bashToolPatterns: [
    { pattern: "rm\\s+(-rf?|--recursive)", reason: "rm -rf puede borrar datos irreversiblemente", ask: true },
    { pattern: "git\\s+reset\\s+--hard", reason: "git reset --hard descarta cambios no commiteados", ask: true },
    { pattern: "git\\s+push\\s+.*--force", reason: "force push puede sobrescribir historia del repositorio", ask: true },
    { pattern: "DROP\\s+(?:TABLE|DATABASE|SCHEMA)", reason: "Operación destructiva de base de datos", ask: false },
    { pattern: "truncate\\s+table", reason: "Borra todos los datos de la tabla", ask: true },
    { pattern: "aws\\s+s3\\s+rm\\s+.*--recursive", reason: "Borrado masivo en S3", ask: false },
    { pattern: "\\bsudo\\s+rm\\b", reason: "rm con sudo es extremadamente peligroso", ask: false },
  ],
  zeroAccessPaths: [".env", ".env.local", ".env.production", "~/.ssh/", "*.pem", "*.key", "secrets.yaml"],
  readOnlyPaths: ["package-lock.json", "bun.lock", "poetry.lock", "/etc/"],
  noDeletePaths: [".git/", "README.md", "Dockerfile", "docker-compose.yml", ".pi/agents/", ".pi/skills/"],
};

// ── Helpers ────────────────────────────────────────────────────────────────

function matchesPath(command: string, patterns: string[]): string | null {
  for (const p of patterns) {
    const escaped = p.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*");
    if (new RegExp(escaped, "i").test(command)) return p;
  }
  return null;
}

function isDestructiveWrite(command: string, paths: string[]): boolean {
  const writeOps = /\b(echo\s+.*>|tee|cp|mv|rm|write|sed\s+-i)\b/i;
  if (!writeOps.test(command)) return false;
  return matchesPath(command, paths) !== null;
}

function isDeleteOp(command: string, paths: string[]): boolean {
  const delOps = /\b(rm|git\s+clean|rmdir)\b/i;
  if (!delOps.test(command)) return false;
  return matchesPath(command, paths) !== null;
}

// ── Extension ──────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  pi.registerMessageRenderer("cortex-damage-control", (message, _options, theme) => {
    const content = typeof message.content === "string" ? message.content : "";
    return new Text(theme.fg("warning", "🛡 ") + content, 0, 0);
  });

  let rules: DamageControlRules = DEFAULT_RULES;
  let blockedCount = 0;
  let askedCount = 0;

  function loadRules(cwd: string) {
    const rulesPath = join(cwd, ".pi", "damage-control-rules.yaml");
    if (existsSync(rulesPath)) {
      try {
        rules = parseRulesYaml(readFileSync(rulesPath, "utf-8"));
      } catch {
        rules = DEFAULT_RULES;
      }
    }
  }

  pi.on("session_start", (_event: any, ctx: any) => {
    loadRules(process.cwd());
    ctx.ui.notify("🛡 Cortex damage-control activo", "info");
  });

  // ── Intercepta cada tool_call ──
  pi.on("tool_call", async (event: any, ctx: any) => {
    if (event.toolName !== "bash") return;

    const command: string = event.input?.command || "";
    if (!command.trim()) return;

    // 1. Rutas de acceso cero
    const zeroMatch = matchesPath(command, rules.zeroAccessPaths || []);
    if (zeroMatch) {
      blockedCount++;
      ctx.ui.notify(`🛡 BLOQUEADO: acceso a "${zeroMatch}" prohibido`, "error");
      return { block: true, reason: `Acceso a "${zeroMatch}" bloqueado por damage-control (zeroAccessPaths)` };
    }

    // 2. Rutas de solo lectura (bloquea escritura)
    if (isDestructiveWrite(command, rules.readOnlyPaths || [])) {
      blockedCount++;
      ctx.ui.notify("🛡 BLOQUEADO: intento de escritura en ruta de solo lectura", "error");
      return { block: true, reason: "Escritura en readOnlyPath bloqueada por damage-control" };
    }

    // 3. Rutas sin borrado
    if (isDeleteOp(command, rules.noDeletePaths || [])) {
      blockedCount++;
      ctx.ui.notify("🛡 BLOQUEADO: intento de borrar archivo/directorio protegido", "error");
      return { block: true, reason: "Borrado de noDeletePath bloqueado por damage-control" };
    }

    // 4. Patrones de bash peligrosos
    for (const rule of rules.bashToolPatterns || []) {
      if (!new RegExp(rule.pattern, "i").test(command)) continue;

      if (!rule.ask) {
        blockedCount++;
        ctx.ui.notify(`🛡 BLOQUEADO: ${rule.reason}`, "error");
        return { block: true, reason: rule.reason };
      }

      // Pide confirmación interactiva
      if (!ctx.hasUI) {
        blockedCount++;
        return { block: true, reason: `${rule.reason} (sin UI para confirmar)` };
      }

      askedCount++;
      // ctx.ui.confirm(title: string, message: string) → Promise<boolean>
      const confirmed: boolean = await ctx.ui.confirm(
        "⚠ Cortex Damage Control",
        `Comando peligroso detectado:\n\`${command}\`\n\nMotivo: ${rule.reason}\n\n¿Continuar de todas formas?`
      );

      if (!confirmed) {
        blockedCount++;
        return { block: true, reason: `Usuario canceló: ${rule.reason}` };
      }
      // Si confirmó, deja pasar
    }
  });

  // ── /damage-stats: muestra estadísticas de la sesión ──
  pi.registerCommand("damage-stats", {
    description: "Muestra estadísticas del damage-control en esta sesión",
    handler(_args: string, _ctx: any) {
      pi.sendMessage({
        customType: "cortex-damage-control",
        content:
          `Cortex Damage Control — Estadísticas\n\n` +
          `Comandos bloqueados: ${blockedCount}\n` +
          `Confirmaciones pedidas: ${askedCount}\n` +
          `Patrones activos: ${rules.bashToolPatterns?.length ?? 0}\n` +
          `Rutas protegidas: ${(rules.zeroAccessPaths?.length ?? 0) + (rules.readOnlyPaths?.length ?? 0) + (rules.noDeletePaths?.length ?? 0)}`,
        display: true,
      });
    },
  });
}
