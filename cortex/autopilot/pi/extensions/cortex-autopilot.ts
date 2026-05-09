// cortex-autopilot.ts — Pi extension for Cortex Autopilot lifecycle.
//
// This extension runs inside Pi and connects Pi session events to the
// Autopilot CLI.  It does NOT implement memory, vault access, or
// retrieval — it delegates everything to `cortex autopilot ...`.

interface PiContext {
  cwd: string;
  ui: {
    notify(message: string, level?: "info" | "warn" | "error"): void;
  };
}

interface PiEvent {
  type: string;
}

declare const pi: {
  on(
    event: string,
    handler: (event: PiEvent, ctx: PiContext) => void | Promise<void>
  ): void;
};

declare const process: {
  env: Record<string, string | undefined>;
};

function resolveCortexBin(): string {
  return process.env.CORTEX_BIN || "cortex";
}

function resolveAutopilotMode(): string {
  return process.env.CORTEX_AUTOPILOT_MODE || "assist";
}

async function runAutopilot(
  subcommand: string,
  args: Record<string, string>,
  ctx: PiContext
): Promise<{ ok: boolean; output?: string; error?: string }> {
  const bin = resolveCortexBin();
  const mode = resolveAutopilotMode();
  const flagPairs = Object.entries(args).map(
    ([k, v]) => `--${k} ${JSON.stringify(v)}`
  );
  const cmd = `${bin} autopilot ${subcommand} --json ${flagPairs.join(" ")}`;

  try {
    // Pi may not expose child_process; use a best-effort approach.
    // If spawn/exec is unavailable, the extension degrades gracefully.
    const { execSync } = require("child_process") as typeof import("child_process");
    const output = execSync(cmd, {
      cwd: ctx.cwd,
      encoding: "utf-8",
      timeout: 15000,
      stdio: ["pipe", "pipe", "pipe"],
    });
    return { ok: true, output: output.trim() };
  } catch (err: any) {
    const msg = err?.stderr?.toString?.() || err?.message || String(err);
    return { ok: false, error: msg };
  }
}

let sessionId: string | null = null;

pi.on("session_start", async (_event, ctx) => {
  const result = await runAutopilot(
    "start",
    {
      "project-root": ctx.cwd,
      "workspace-root": `${ctx.cwd}/.cortex`,
      mode: resolveAutopilotMode(),
    },
    ctx
  );

  if (!result.ok) {
    ctx.ui.notify(`Cortex Autopilot no pudo iniciar: ${result.error}`, "warn");
    return;
  }

  try {
    const data = JSON.parse(result.output || "{}");
    sessionId = data.session_id || null;
    ctx.ui.notify(
      `Cortex Autopilot activo${sessionId ? ` (session ${sessionId})` : ""}`,
      "info"
    );
  } catch {
    ctx.ui.notify("Cortex Autopilot activo", "info");
  }
});

pi.on("session_finish", async (_event, ctx) => {
  if (!sessionId) {
    // Degrade gracefully — no session means nothing to finish
    return;
  }

  const result = await runAutopilot(
    "finish",
    {
      "project-root": ctx.cwd,
      "session-id": sessionId,
      auto: "true",
    },
    ctx
  );

  if (!result.ok) {
    ctx.ui.notify(
      `Cortex Autopilot no pudo cerrar la sesion: ${result.error}`,
      "warn"
    );
    return;
  }

  try {
    const data = JSON.parse(result.output || "{}");
    const saved = data.saved ? "guardada" : "cerrada";
    ctx.ui.notify(`Cortex Autopilot cerro la sesion (${saved})`, "info");
  } catch {
    ctx.ui.notify("Cortex Autopilot cerro la sesion", "info");
  }

  sessionId = null;
});
