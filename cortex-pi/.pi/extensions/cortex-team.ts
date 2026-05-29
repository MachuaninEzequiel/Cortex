/**
 * cortex-team.ts — Auto-spawn portable de terminales para Cortex Pi 2.5+net
 *
 * F5 del overhaul UX (ver docs/multi-ide-mcp-hardening/PI-COCKPIT-UX/).
 *
 * Registra el slash command ``/cortex-team`` que:
 *
 *   1. Verifica que somos master (sólo el master puede spawnear).
 *   2. Filtra los roles ya conectados a la red.
 *   3. Muestra presets útiles (Deep Track full, Audit pair, etc.).
 *   4. Spawnea las terminales nuevas con detección de OS y terminal
 *      multiplexer disponible.
 *   5. Si la detección falla, copia los comandos al clipboard como
 *      fallback (universal).
 *   6. Trackea las hijas spawneadas en ``.pi/agent-sessions/team.json``.
 *
 * Estrategia de detección de terminal:
 *
 *   1. Terminal del usuario por env (cross-platform): WezTerm
 *      (WEZTERM_PANE / WEZTERM_EXECUTABLE → ``wezterm cli spawn``).
 *   2. Default del SO:
 *        Windows : wt.exe (Windows Terminal) → fallback ``start cmd``.
 *        Linux   : tmux (si TMUX env) → alacritty → kitty →
 *                  gnome-terminal → konsole → xterm.
 *        macOS   : osascript para Terminal.app.
 *   3. clipboard fallback (universal).
 *
 * Cada terminal hija arranca con ``pi`` (que carga el stack UX completo de
 * settings.json: cockpit/net/panel/etc.) y el rol forzado vía la env var
 * CORTEX_NET_ROLE. NO usa ``just`` (no todos lo tienen instalado).
 *
 * Coordinated shutdown: NO implementado en F5. Si el master cierra la
 * sesión, las hijas siguen funcionando pero el cortex-net del peer
 * detecta el cambio del session.lock (vía polling de F1) y la red
 * queda en standby. Iteración futura: flag ``shutdown: true`` en
 * team.json que las hijas chequean en turn_end.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { spawn, spawnSync, execSync } from "child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { join } from "path";
// Bugfix mayo 2026: import desde .pi/lib/ (ver cortex-cockpit.ts y
// docs/multi-ide-mcp-hardening/PI-COCKPIT-UX/README.md § 8).
import {
  cortexState,
  type CortexRole,
} from "../lib/cortex-state";

// ── Detección de comandos disponibles ───────────────────────────────────────

/**
 * Chequea si ``cmd`` existe en el PATH. Robusto: usa ``where`` en
 * Windows y ``which`` en *nix; cualquier error (no encontrado, permiso
 * denegado, etc.) devuelve false.
 */
function commandExists(cmd: string): boolean {
  try {
    if (process.platform === "win32") {
      execSync(`where ${cmd}`, { stdio: "ignore", windowsHide: true });
    } else {
      execSync(`which ${cmd}`, { stdio: "ignore" });
    }
    return true;
  } catch {
    return false;
  }
}

/**
 * Copia ``text`` al clipboard del SO. Usa ``clip`` en Windows,
 * ``pbcopy`` en macOS, ``xclip``/``xsel`` en Linux. Devuelve true si
 * alguna estrategia funcionó.
 */
function copyToClipboard(text: string): boolean {
  const platform = process.platform;
  const candidates: Array<{ cmd: string; args?: string[] }> =
    platform === "win32"
      ? [{ cmd: "clip" }]
      : platform === "darwin"
      ? [{ cmd: "pbcopy" }]
      : [
          { cmd: "xclip", args: ["-selection", "clipboard"] },
          { cmd: "xsel", args: ["--clipboard", "--input"] },
          { cmd: "wl-copy" }, // Wayland
        ];

  for (const c of candidates) {
    if (!commandExists(c.cmd)) continue;
    try {
      const proc = spawn(c.cmd, c.args ?? [], { stdio: ["pipe", "ignore", "ignore"] });
      proc.stdin.write(text);
      proc.stdin.end();
      return true;
    } catch {
      /* probar siguiente */
    }
  }
  return false;
}

// ── Spawn de terminales por OS ──────────────────────────────────────────────

interface SpawnResult {
  success: boolean;
  /** Comando manual a copiar/pegar si success === false. */
  fallback?: string;
  /** Mecanismo detectado/usado. Útil para diagnóstico. */
  mechanism?: string;
  /** Nota de diagnóstico (p.ej. el error real si wezterm falló). */
  note?: string;
}

/**
 * Resuelve el binario CLI de WezTerm (``wezterm``/``wezterm.exe``), que es el
 * que tiene el subcomando ``cli``. OJO: ``WEZTERM_EXECUTABLE`` suele apuntar a
 * ``wezterm-gui(.exe)``, que NO maneja ``cli spawn`` — por eso preferimos
 * ``wezterm(.exe)`` del mismo directorio y, si no, el del PATH.
 */
function weztermCli(): string {
  const cliName = process.platform === "win32" ? "wezterm.exe" : "wezterm";
  const exe = process.env.WEZTERM_EXECUTABLE;
  if (exe) {
    const dir = exe.replace(/[\\/][^\\/]*$/, "");
    const candidate = join(dir, cliName);
    if (existsSync(candidate)) return candidate;
  }
  return cliName; // del PATH
}

/**
 * Spawnea una terminal nueva en ``cwd`` y le hace correr ``pi`` con
 * ``CORTEX_NET_ROLE=<role>``. Cross-platform con fallback elegante.
 *
 * Devuelve ``{success: true, mechanism}`` si funcionó, o
 * ``{success: false, fallback}`` con el comando para que el usuario lo
 * pegue manualmente.
 */
function spawnTerminal(cwd: string, role: CortexRole): SpawnResult {
  const platform = process.platform;
  const isWin = platform === "win32";
  // Bugfix may 2026: lanzamos `pi` directamente (que carga
  // settings.json defaultExtensions = stack UX completo) con el rol forzado
  // por env var. Antes corría `just role-<role>`, que (a) requería tener
  // `just` instalado y (b) cargaba un stack reducido SIN cockpit/UX.
  // cortex-net.resolveRole() respeta CORTEX_NET_ROLE.
  const winCmd = `$env:CORTEX_NET_ROLE='${role}'; pi`; // PowerShell
  const cmdCmd = `set "CORTEX_NET_ROLE=${role}" && pi`; // cmd.exe
  const nixCmd = `CORTEX_NET_ROLE=${role} pi`; // bash
  // Comando seguro para PEGAR a mano (clipboard fallback). PowerShell-safe
  // en Windows (cd /d y && fallan en PowerShell) — fix del hallazgo #14.
  const pasteCmd = isWin
    ? `Set-Location '${cwd}'; $env:CORTEX_NET_ROLE='${role}'; pi`
    : `cd '${cwd}' && CORTEX_NET_ROLE=${role} pi`;

  // ── Terminal del usuario, detectada por env (cross-platform) ──
  // Respeta la terminal REAL (p.ej. WezTerm con tu config gráfica) en vez de
  // abrir la default del SO. WezTerm setea WEZTERM_PANE / WEZTERM_EXECUTABLE
  // en cada panel y expone `wezterm cli spawn`, que abre una pestaña nueva en
  // tu ventana actual usando tu configuración.
  if (process.env.WEZTERM_PANE || process.env.WEZTERM_EXECUTABLE) {
    const wez = weztermCli();
    const wezArgs = isWin
      ? ["cli", "spawn", "--cwd", cwd, "--", "powershell", "-NoExit", "-Command", winCmd]
      : ["cli", "spawn", "--cwd", cwd, "--", "bash", "-lc", `${nixCmd}; exec bash`];
    // spawnSync (NO async): así sabemos DE VERDAD si abrió la pestaña.
    // `wezterm cli spawn` es rápido — le pide al mux y sale con el pane id.
    const r = spawnSync(wez, wezArgs, {
      stdio: ["ignore", "ignore", "pipe"],
      windowsHide: true,
      encoding: "utf-8",
    });
    if (!r.error && r.status === 0) {
      return { success: true, mechanism: "wezterm" };
    }
    // Falló de verdad → devolvemos el error REAL (antes reportaba "ok"
    // optimista aunque no abriera nada). El usuario ve el motivo + el
    // comando para pegar a mano.
    const why = (
      r.error?.message ||
      (typeof r.stderr === "string" ? r.stderr : "") ||
      `exit ${r.status}`
    )
      .toString()
      .trim()
      .slice(0, 300);
    return {
      success: false,
      mechanism: "wezterm",
      fallback: pasteCmd,
      note: `wezterm cli falló (bin: ${wez}): ${why}`,
    };
  }

  // ── Windows (terminal default del SO) ──
  if (platform === "win32") {
    if (commandExists("wt")) {
      // Windows Terminal: nueva tab en la ventana actual.
      try {
        spawn(
          "wt.exe",
          [
            "-w",
            "0",
            "nt",
            "--title",
            role,
            "-d",
            cwd,
            "powershell",
            "-NoExit",
            "-Command",
            winCmd,
          ],
          { detached: true, stdio: "ignore", windowsHide: false }
        ).unref();
        return { success: true, mechanism: "windows-terminal" };
      } catch {
        /* caer a cmd start */
      }
    }
    // Fallback: cmd.exe start abre nueva ventana cmd.
    try {
      spawn(
        "cmd.exe",
        ["/c", "start", "cmd.exe", "/K", `cd /d "${cwd}" && ${cmdCmd}`],
        { detached: true, stdio: "ignore", windowsHide: false }
      ).unref();
      return { success: true, mechanism: "cmd-start" };
    } catch {
      return {
        success: false,
        fallback: pasteCmd,
      };
    }
  }

  // ── macOS ──
  if (platform === "darwin") {
    // osascript abre Terminal.app y le manda el comando.
    const script =
      `tell application "Terminal" to do script "cd '${cwd.replace(
        /'/g,
        "'\\''"
      )}' && ${nixCmd}"`;
    try {
      spawn("osascript", ["-e", script], {
        detached: true,
        stdio: "ignore",
      }).unref();
      return { success: true, mechanism: "osascript-terminal" };
    } catch {
      return {
        success: false,
        fallback: pasteCmd,
      };
    }
  }

  // ── Linux / otro Unix ──
  // Preferimos tmux si ya estamos dentro de una sesión.
  if (process.env.TMUX) {
    try {
      spawn(
        "tmux",
        ["split-window", "-h", "-c", cwd, nixCmd],
        { detached: true, stdio: "ignore" }
      ).unref();
      return { success: true, mechanism: "tmux-split" };
    } catch {
      /* caer a otros */
    }
  }

  // Terminales gráficas (en orden de preferencia).
  const linuxTerminals: Array<{ cmd: string; argsFn: () => string[] }> = [
    {
      cmd: "alacritty",
      argsFn: () => [
        "--working-directory",
        cwd,
        "-t",
        role,
        "-e",
        "bash",
        "-c",
        `${nixCmd}; exec bash`,
      ],
    },
    {
      cmd: "kitty",
      argsFn: () => [
        "--directory",
        cwd,
        "--title",
        role,
        "bash",
        "-c",
        `${nixCmd}; exec bash`,
      ],
    },
    {
      cmd: "gnome-terminal",
      argsFn: () => [
        "--tab",
        "--title",
        role,
        "--working-directory",
        cwd,
        "--",
        "bash",
        "-c",
        `${nixCmd}; exec bash`,
      ],
    },
    {
      cmd: "konsole",
      argsFn: () => [
        "--workdir",
        cwd,
        "-e",
        "bash",
        "-c",
        `${nixCmd}; exec bash`,
      ],
    },
    {
      cmd: "xterm",
      argsFn: () => [
        "-T",
        role,
        "-e",
        `cd '${cwd}' && ${nixCmd}; exec bash`,
      ],
    },
  ];

  for (const term of linuxTerminals) {
    if (!commandExists(term.cmd)) continue;
    try {
      spawn(term.cmd, term.argsFn(), {
        detached: true,
        stdio: "ignore",
      }).unref();
      return { success: true, mechanism: term.cmd };
    } catch {
      /* probar siguiente */
    }
  }

  // Ninguna terminal detectada: fallback a clipboard.
  return {
    success: false,
    fallback: pasteCmd,
  };
}

// ── Tracking en team.json ──────────────────────────────────────────────────

interface TeamEntry {
  master_pid: number;
  session_id: string;
  cwd: string;
  spawned: Array<{
    role: CortexRole;
    spawned_at: string;
    mechanism: string;
  }>;
}

function teamFilePath(cwd: string): string {
  return join(cwd, ".pi", "agent-sessions", "team.json");
}

function readTeamFile(cwd: string): TeamEntry | null {
  const p = teamFilePath(cwd);
  if (!existsSync(p)) return null;
  try {
    return JSON.parse(readFileSync(p, "utf-8"));
  } catch {
    return null;
  }
}

function writeTeamFile(cwd: string, entry: TeamEntry): void {
  const p = teamFilePath(cwd);
  try {
    mkdirSync(join(cwd, ".pi", "agent-sessions"), { recursive: true });
    writeFileSync(p, JSON.stringify(entry, null, 2), "utf-8");
  } catch {
    /* best-effort */
  }
}

// ── Presets de team ────────────────────────────────────────────────────────

interface Preset {
  id: string;
  label: string;
  roles: CortexRole[];
}

const PRESETS: Preset[] = [
  {
    id: "deep_full",
    label: "Deep Track full (designer + implementer + documenter)",
    roles: ["designer", "implementer", "documenter"],
  },
  {
    id: "deep_with_audit",
    label: "Deep Track + audit (designer + implementer + security + test-verifier + documenter)",
    roles: ["designer", "implementer", "security", "test-verifier", "documenter"],
  },
  {
    id: "design_pair",
    label: "Design pair (designer + implementer)",
    roles: ["designer", "implementer"],
  },
  {
    id: "audit_pair",
    label: "Audit pair (security + test-verifier)",
    roles: ["security", "test-verifier"],
  },
  {
    id: "explorer_only",
    label: "Explorer (análisis read-only)",
    roles: ["explorer"],
  },
  {
    id: "documenter_only",
    label: "Documenter observer (escuchar in-flight)",
    roles: ["documenter"],
  },
];

// ── Extension ──────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  pi.registerCommand("cortex-team", {
    description:
      "Spawnear terminales adicionales para los roles del medio (Pi 2.5+net multi-terminal)",
    async handler(_args: string, ctx: any) {
      // ── Guards ──
      // ctx.cwd siempre está disponible en el handler. Usamos cortexState.cwd
      // si está, sino fallback al ctx.cwd. Cubre el caso (raro pero observado)
      // donde el singleton no tiene cwd cuando se invoca el comando, mientras
      // que Pi sí sabe el cwd actual.
      const cwd: string = cortexState.cwd ?? ctx.cwd ?? "";
      if (!cwd) {
        ctx.ui.notify(
          "⬢ /cortex-team: no se pudo determinar el cwd. ¿Pi arrancó sin proyecto?",
          "warning"
        );
        return;
      }
      if (!cortexState.sessionId) {
        ctx.ui.notify(
          "⬢ /cortex-team: no hay Cortex Session activa. Tipeá tu tarea para que cortex-sync abra una.",
          "warning"
        );
        return;
      }
      // Diferenciar entre "no registrado en la red" y "registrado como worker".
      // Sólo el último es realmente un worker; el primero es un estado transitorio
      // donde cortex-net todavía no levantó el hub (típicamente porque el agent
      // activo es cortex-sync, que vive afuera de la red).
      if (!cortexState.myRole) {
        ctx.ui.notify(
          cortexState.activeAgentName === "cortex-sync"
            ? "⬢ /cortex-team: estás en cortex-sync (afuera de la red por diseño B'). " +
                "Cambiá a un agent del medio (/system → cortex-SDDwork) y volvé a intentar."
            : "⬢ /cortex-team: todavía no estás registrado en la red. Esperá unos " +
                "segundos a que cortex-net detecte el lock, o cambiá de agent con /system.",
          "warning"
        );
        return;
      }
      if (!cortexState.isMaster) {
        ctx.ui.notify(
          "⬢ /cortex-team: sólo el master (proceso que levantó el hub) puede " +
            "spawnear terminales. Vos sos worker — el spawn lo hace el master.",
          "warning"
        );
        return;
      }

      // ── Calcular qué presets tiene sentido mostrar ──
      const connected = new Set<CortexRole>(
        cortexState.peers.map((p) => p.role)
      );

      const labeledPresets = PRESETS.map((preset) => {
        const toOpen = preset.roles.filter((r) => !connected.has(r));
        const status =
          toOpen.length === 0
            ? "(todos ya conectados)"
            : toOpen.length === preset.roles.length
            ? `(abrir: ${toOpen.join(", ")})`
            : `(faltan: ${toOpen.join(", ")})`;
        return {
          preset,
          toOpen,
          label: `${preset.label}  ${status}`,
        };
      });

      // ── Selector ──
      const selected = await ctx.ui.select(
        "⬡ Cortex Team — Elegí qué roles abrir:",
        labeledPresets.map((p) => p.label)
      );
      if (selected === undefined) {
        ctx.ui.notify("Cancelado.", "info");
        return;
      }

      const choice = labeledPresets.find((p) => p.label === selected);
      if (!choice) return;
      if (choice.toOpen.length === 0) {
        ctx.ui.notify(
          "Todos los roles del preset ya están conectados. No hay nada que abrir.",
          "info"
        );
        return;
      }

      // ── Spawn ──
      ctx.ui.notify(
        `⬢ Spawneando ${choice.toOpen.length} terminal(es): ${choice.toOpen.join(", ")}…`,
        "info"
      );

      const results = choice.toOpen.map((role) => ({
        role,
        result: spawnTerminal(cwd, role),
      }));

      // ── Tracking en team.json ──
      const team: TeamEntry = readTeamFile(cwd) ?? {
        master_pid: process.pid,
        session_id: cortexState.sessionId,
        cwd: cwd,
        spawned: [],
      };
      for (const r of results) {
        if (r.result.success) {
          team.spawned.push({
            role: r.role,
            spawned_at: new Date().toISOString(),
            mechanism: r.result.mechanism ?? "unknown",
          });
        }
      }
      writeTeamFile(cwd, team);

      // ── Reporte ──
      const ok = results.filter((r) => r.result.success);
      const failed = results.filter((r) => !r.result.success);

      if (ok.length > 0) {
        const mechanisms = [...new Set(ok.map((r) => r.result.mechanism))];
        ctx.ui.notify(
          `✓ Spawn ok: ${ok.map((r) => r.role).join(", ")} ` +
            `(via ${mechanisms.join(", ")}). ` +
            `Los peers van a aparecer en el cockpit cuando se conecten al hub.`,
          "success"
        );
      }

      if (failed.length > 0) {
        // Notas de diagnóstico (p.ej. el error REAL de wezterm cli).
        const notes = [...new Set(failed.map((r) => r.result.note).filter(Boolean))];
        // Fallback: armar bloque con todos los comandos y copiarlo.
        const block = failed
          .map(
            (r) =>
              `# ${r.role}\n${r.result.fallback ?? `Set-Location '${cwd}'; $env:CORTEX_NET_ROLE='${r.role}'; pi`}`
          )
          .join("\n\n");
        const copied = copyToClipboard(block);
        ctx.ui.notify(
          (notes.length ? notes.join("\n") + "\n\n" : "") +
            `⚠ No se pudieron abrir terminales para: ${failed
              .map((r) => r.role)
              .join(", ")}.\n` +
            (copied
              ? "Copié al clipboard el comando para abrir cada una a mano. " +
                "Pegalo en una pestaña/ventana nueva de tu terminal."
              : "Abrí esas terminales a mano y ejecutá:\n" + block),
          "warning"
        );
      }
    },
  });

  // ── /cortex-team-status ─ pequeño helper de debug ──────────────────
  pi.registerCommand("cortex-team-status", {
    description: "Mostrar el contenido actual de team.json (debug)",
    async handler(_args: string, ctx: any) {
      const cwd = cortexState.cwd ?? ctx.cwd ?? "";
      if (!cwd) {
        ctx.ui.notify("Sin cwd cacheado ni cwd en el contexto.", "warning");
        return;
      }
      const team = readTeamFile(cwd);
      if (!team) {
        ctx.ui.notify("No hay team.json todavía (nadie spawneó nada).", "info");
        return;
      }
      ctx.ui.notify(
        `master_pid=${team.master_pid} · session_id=${team.session_id.slice(0, 16)}… · ` +
          `spawned=[${team.spawned.map((s) => s.role).join(", ")}]`,
        "info"
      );
    },
  });
}
