/**
 * cortex-dashboard — Ultra Premium Edition
 *
 * Dashboard central de Cortex Release 2.5 con branding de alta fidelidad.
 * Implementa un degradado TrueColor: Violeta -> Ciruela/Borgoña -> Carmesí.
 */

import type { Extension, PiContext } from "@mariozechner/pi-coding-agent";

const extension: Extension = {
  name: "cortex-dashboard",
  version: "2.5.0",

  async init(ctx: PiContext) {
    // ─── Estado ────────────────────────────────────────────────────────────
    let pipelineStage:
      | "idle"
      | "sync"
      | "code"
      | "security"
      | "test"
      | "document"
      | "done" = "idle";
    let sessionSpec = "";
    let vaultStats = { sessions: 0, patterns: 0, episodic: 0, specs: 0 };
    let isBooting = true;
    let bootTick = 0;

    // ─── Sistema de Diseño (TrueColor RGB) ─────────────────────────────────
    const C = {
      reset: "\x1b[0m",
      bold: "\x1b[1m",
      dim: "\x1b[2m",
      italic: "\x1b[3m",
      // Colores del degradado solicitado
      violet:  "\x1b[38;2;124;58;237m",   // #7c3aed
      plum:    "\x1b[38;2;139;0;139m",    // #8b008b (tono ciruela/borgoña)
      crimson: "\x1b[38;2;220;20;60m",    // #dc143c
      // Colores funcionales
      success: "\x1b[38;2;63;185;80m",   // #3fb950
      warn:    "\x1b[38;2;210;153;34m",   // #d29922
      danger:  "\x1b[38;2;248;81;73m",    // #f85149
      muted:   "\x1b[38;2;110;118;129m",  // #6e7681
      border:  "\x1b[38;2;33;38;45m",     // #21262d
      white:   "\x1b[38;2;230;237;243m",  // #e6edf3
    };

    const LOGO = `
  ${C.violet}▟████▙      ▟████▙     ▟█████▙    ▟███████▛  ▟████████▛  ▟█▙    ▟█▙
 ${C.violet}▟█▘  ▝▙    ${C.plum}▟█▘    ▝█▙   ${C.plum}█▌    ▝█▙  ${C.plum}▝▜██████▛▘  ${C.crimson}█▌          ${C.crimson}▝█▙  ▟█▘ 
 ${C.violet}█▌         ${C.plum}█▌      ▐█   ${C.plum}█▌    ▟█▛     ${C.plum}█▌      ${C.crimson}█▌▟█████▙    ${C.crimson}▝█▙▟█▘  
 ${C.violet}▜█▖  ▟▛    ${C.plum}▜█▖    ▟█▛   ${C.plum}█▌ ▟███▛      ${C.plum}█▌      ${C.crimson}█▌            ${C.crimson}▟█▘▝█▙  
  ${C.violet}▜████▛      ${C.plum}▜██████▛    ${C.plum}█▌ ▝█▙        ${C.plum}█▌      ${C.crimson}▜████████▛  ${C.crimson}▟█▘  ▝█▙ 
${C.reset}
          ${C.bold}${C.violet}G O B E R N A N Z A${C.reset}   ${C.border}│${C.reset}   ${C.bold}${C.crimson}R E L E A S E   2 . 5${C.reset}
`;

    // ─── UI Components ─────────────────────────────────────────────────────

    const renderPipeline = () => {
      const stages = ["sync", "code", "security", "test", "document"];
      const labels: Record<string, string> = {
        sync: "SYNC", code: "CODE", security: "SEC", test: "TEST", document: "DOC"
      };
      const currentIndex = stages.indexOf(pipelineStage);
      
      return stages.map((s, i) => {
        const active = s === pipelineStage;
        const past = i < currentIndex;
        const label = labels[s];
        if (active) return `${C.violet}${C.bold}▶ ${label}${C.reset}`;
        if (past) return `${C.success}✔ ${label}${C.reset}`;
        return `${C.muted}○ ${label}${C.reset}`;
      }).join(` ${C.border}─${C.reset} `);
    };

    const renderFooter = () => {
      if (isBooting) {
        const dots = ".".repeat((bootTick % 3) + 1);
        return `${C.violet}${C.bold}CORTEX${C.reset} ${C.dim}Synchronizing Governance Engine${dots}${C.reset}`;
      }

      const stageBar = pipelineStage === "idle" 
        ? `${C.muted}READY — Use /sdd to start implementation${C.reset}`
        : renderPipeline();

      const stats = [
        `${C.violet}VAULT: ${vaultStats.sessions}${C.reset}`,
        `${C.plum}EPISODIC: ${vaultStats.episodic}${C.reset}`,
        `${C.crimson}SPECS: ${vaultStats.specs}${C.reset}`
      ].join(`${C.border} │ ${C.reset}`);

      const spec = sessionSpec 
        ? `\n${C.violet}${C.bold}SPEC:${C.reset} ${C.italic}${C.white}${sessionSpec.slice(0, 50)}${sessionSpec.length > 50 ? '...' : ''}${C.reset}`
        : "";

      return [
        `${C.violet}${C.bold}CORTEX${C.reset} ${C.border}│${C.reset} ${stageBar}`,
        `${stats}${spec}`
      ].join("\n");
    };

    // ─── Governance Interceptor ────────────────────────────────────────────
    
    ctx.on("tool_call", async (tool: any) => {
      if (tool.name !== "bash") return;
      const cmd: string = tool.input?.command ?? "";

      // Bloqueo de herramientas externas
      const forbidden = ["engram", "mem_", "save_memory", "session_summary"];
      for (const word of forbidden) {
        if (cmd.includes(word)) {
          ctx.ui.showAlert({
            title: "🛡️ CORTEX GOVERNANCE BREACH",
            message: `External tool detected: ${word}\nCortex strictly prohibits non-native memory systems.`,
            type: "error"
          });
          return { blocked: true, reason: "Forbidden external memory tool." };
        }
      }

      // Damage Control
      const destructive = [
        { regex: /rm\s+-rf?\s+(vault|\.cortex|\.memory)/, msg: "Attempted deletion of Cortex infrastructure." },
        { regex: /git\s+push\s+.*--force(?!-with-lease)/, msg: "Unsafe git push --force detected." }
      ];
      for (const rule of destructive) {
        if (rule.regex.test(cmd)) {
          ctx.ui.showAlert({ title: "🛡️ DAMAGE CONTROL", message: rule.msg, type: "error" });
          return { blocked: true, reason: rule.msg };
        }
      }
    });

    // ─── Comandos ──────────────────────────────────────────────────────────

    ctx.addCommand("/sdd", async (args: string) => {
      if (!args.trim()) {
        ctx.ui.showMessage("Uso: /sdd <descripcion_tarea>");
        return;
      }
      sessionSpec = args.trim();
      pipelineStage = "sync";
      ctx.ui.refresh();
      ctx.sendMessage(`[CORTEX] Iniciando pipeline SDDwork para: "${args.trim()}"\nEjecutando cortex-sync...`);
    });

    ctx.addCommand("/cortex", async (args: string) => {
      const sub = args.trim().toLowerCase();
      if (sub === "stats") {
        await updateStats();
        ctx.ui.showMessage(`CORTEX MEMORY SYSTEM\n\nEpisodic (ChromaDB): ${vaultStats.episodic}\nSemantic (Vault): ${vaultStats.sessions}\nTechnical Specs: ${vaultStats.specs}`);
      } else {
        ctx.ui.showMessage(`CORTEX COMMANDS:\n/sdd <tarea>   - Iniciar pipeline completo\n/team <nombre>  - Cambiar equipo de agentes\n/reset          - Reiniciar estado\n/cortex stats   - Ver estadísticas de memoria`);
      }
    });

    ctx.addCommand("/reset", async () => {
      pipelineStage = "idle";
      sessionSpec = "";
      ctx.ui.refresh();
      ctx.ui.showMessage("Pipeline de gobernanza reiniciado.");
    });

    // ─── Lifecycle ─────────────────────────────────────────────────────────

    ctx.on("turn_start", async () => {
      if (pipelineStage !== "idle" && pipelineStage !== "done") {
        const stageReminders: Record<string, string> = {
          sync: "GOVERNANCE: Fase SYNC — Llama a `cortex_sync_ticket` obligatoriamente.",
          code: "GOVERNANCE: Fase CODE — Implementa siguiendo la especificación.",
          security: "GOVERNANCE: Fase SECURITY — Audita secretos y vulnerabilidades.",
          test: "GOVERNANCE: Fase TEST — Objetivo cobertura >85%.",
          document: "GOVERNANCE: Fase DOCUMENT — `cortex_save_session` es OBLIGATORIO."
        };
        return stageReminders[pipelineStage];
      }
    });

    const updateStats = async () => {
      try {
        const result = await ctx.tools.bash({ command: "cortex stats 2>/dev/null" });
        if (result.stdout) {
          const sM = result.stdout.match(/sessions:\s*(\d+)/);
          const eM = result.stdout.match(/episodic:\s*(\d+)/);
          const spM = result.stdout.match(/specs:\s*(\d+)/);
          if (sM) vaultStats.sessions = parseInt(sM[1]);
          if (eM) vaultStats.episodic = parseInt(eM[1]);
          if (spM) vaultStats.specs = parseInt(spM[1]);
          ctx.ui.refresh();
        }
      } catch {}
    };

    // ─── Boot Sequence ─────────────────────────────────────────────────────

    ctx.ui.setFooter({ render: renderFooter });

    const bootInterval = setInterval(() => {
      bootTick++;
      if (bootTick > 12) {
        clearInterval(bootInterval);
        isBooting = false;
        ctx.ui.refresh();
        ctx.ui.showMessage(`${LOGO}\n${C.success}✔ Motor de Gobernanza Operativo${C.reset}\n${C.success}✔ Memoria Híbrida RRF Sincronizada${C.reset}\n\nEscribe ${C.violet}/cortex${C.reset} para ver los comandos disponibles.`);
        updateStats();
      }
      ctx.ui.refresh();
    }, 120);

    setInterval(updateStats, 60000);
  }
};

export default extension;
