/**
 * cortex-mcp — Adaptador MCP para Pi
 *
 * Pi no tiene soporte nativo de MCP. Esta extensión lo implementa:
 *   1. Lee .pi/mcp.json al arrancar (formato idéntico a Claude Code)
 *   2. Lanza cada servidor MCP como subproceso stdio
 *   3. Registra las tools de cada servidor como tools de Pi con el prefijo mcp_<server>_<tool>
 *   4. Gestiona el ciclo de vida: startup, keep-alive, shutdown limpio
 *
 * Formato de .pi/mcp.json:
 * {
 *   "mcpServers": {
 *     "cortex-mcp": {
 *       "command": "python",
 *       "args": ["-m", "cortex.mcp.server"],
 *       "cwd": ".",                          ← opcional, relativo al proyecto
 *       "env": { "CORTEX_CONFIG_PATH": "config.yaml" }
 *     }
 *   }
 * }
 *
 * Variables disponibles en cwd/args/env:
 *   ${cwd}  → directorio del proyecto
 *
 * Comandos:
 *   /mcp          → muestra estado de todos los servidores y sus tools
 *   /mcp-restart  → reinicia todos los servidores (útil tras cambios en el server)
 *
 * Uso: pi -e .pi/extensions/cortex-mcp.ts
 * (o agregarlo a settings.json → extensions)
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Text } from "@mariozechner/pi-tui";
import { Type } from "@sinclair/typebox";
import { readFileSync, existsSync } from "fs";
import { join, resolve } from "path";
import { spawn, ChildProcess, execFileSync } from "child_process";
import { homedir } from "os";

// ── MCP Protocol types (subset) ────────────────────────────────────────────

interface McpJsonRpc {
  jsonrpc: "2.0";
  id?: number | string;
  method?: string;
  params?: any;
  result?: any;
  error?: { code: number; message: string; data?: any };
}

interface McpTool {
  name: string;
  description?: string;
  inputSchema: {
    type: "object";
    properties?: Record<string, any>;
    required?: string[];
  };
}

interface McpServerConfig {
  command: string;
  args?: string[];
  cwd?: string;
  env?: Record<string, string>;
}

interface McpConfig {
  mcpServers: Record<string, McpServerConfig>;
}

// ── Pipx Python resolver ──────────────────────────────────────────────────

/**
 * Dado el nombre del paquete instalado con pipx (ej: "cortex"),
 * devuelve la ruta absoluta al python.exe dentro de su venv.
 *
 * Estrategia en orden:
 *  1. PIPX_HOME env var si está definida
 *  2. Ruta estándar de Windows: %LOCALAPPDATA%\pipx\pipx\venvs
 *  3. Ruta estándar Unix:       ~/.local/pipx/venvs  o  ~/.local/share/pipx/venvs
 *  4. Fallback: "python" del PATH (puede no tener el paquete)
 */
function resolvePipxPython(packageName: string): string {
  const isWin = process.platform === "win32";
  const pythonBin = isWin ? "Scripts\\python.exe" : "bin/python";
  const home = homedir();
  const candidates: string[] = [];

  // 1. PIPX_HOME env var explícita
  if (process.env.PIPX_HOME) {
    candidates.push(join(process.env.PIPX_HOME, "venvs", packageName, pythonBin));
  }

  // 2. Preguntar a pipx directamente → obtiene PIPX_LOCAL_VENVS real
  try {
    const venvs = execFileSync("pipx", ["environment", "--value", "PIPX_LOCAL_VENVS"], {
      encoding: "utf-8",
      timeout: 5000,
    }).trim();
    if (venvs) candidates.push(join(venvs, packageName, pythonBin));
  } catch {}

  // 3. Rutas derivadas por plataforma
  if (isWin) {
    // pipx usa %USERPROFILE%\pipx cuando PIPX_HOME no está definido
    candidates.push(join(home, "pipx", "venvs", packageName, pythonBin));
    const localAppData = process.env.LOCALAPPDATA ?? join(home, "AppData", "Local");
    candidates.push(join(localAppData, "pipx", "pipx", "venvs", packageName, pythonBin));
    candidates.push(join(localAppData, "pipx", "venvs", packageName, pythonBin));
  } else {
    candidates.push(join(home, ".local", "pipx", "venvs", packageName, pythonBin));
    candidates.push(join(home, ".local", "share", "pipx", "venvs", packageName, pythonBin));
    candidates.push(join(home, "pipx", "venvs", packageName, pythonBin));
  }

  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }

  return isWin ? "python" : "python3";
}

// ── Pipx CLI binary resolver ──────────────────────────────────────────────

/**
 * Resuelve el ejecutable CLI (ej: cortex.exe) dentro del venv de pipx,
 * a diferencia de resolvePipxPython que resuelve python.exe.
 */
function resolvePipxBin(packageName: string, binName: string): string {
  const isWin = process.platform === "win32";
  const bin = isWin ? `${binName}.exe` : binName;
  const home = homedir();
  const candidates: string[] = [];

  if (process.env.PIPX_HOME) {
    const scriptDir = isWin ? "Scripts" : "bin";
    candidates.push(join(process.env.PIPX_HOME, "venvs", packageName, scriptDir, bin));
  }

  try {
    const venvs = execFileSync("pipx", ["environment", "--value", "PIPX_LOCAL_VENVS"], {
      encoding: "utf-8", timeout: 5000,
    }).trim();
    if (venvs) {
      const scriptDir = isWin ? "Scripts" : "bin";
      candidates.push(join(venvs, packageName, scriptDir, bin));
    }
  } catch {}

  if (isWin) {
    candidates.push(join(home, "pipx", "venvs", packageName, "Scripts", bin));
    const localAppData = process.env.LOCALAPPDATA ?? join(home, "AppData", "Local");
    candidates.push(join(localAppData, "pipx", "pipx", "venvs", packageName, "Scripts", bin));
  } else {
    candidates.push(join(home, ".local", "pipx", "venvs", packageName, "bin", bin));
    candidates.push(join(home, "pipx", "venvs", packageName, "bin", bin));
  }

  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }

  // Fallback: el bin en el PATH global (pipx lo instala en ~/.local/bin)
  return bin;
}

// ── MCP Client (stdio transport) ────────────────────────────────────────────

class McpClient {
  private proc: ChildProcess | null = null;
  public lastStderr: string = "";
  private pending = new Map<number, { resolve: (r: any) => void; reject: (e: any) => void }>();
  private nextId = 1;
  private buf = "";
  public tools: McpTool[] = [];
  public status: "stopped" | "starting" | "ready" | "error" = "stopped";
  public error: string = "";

  constructor(
    public readonly name: string,
    private readonly cfg: McpServerConfig,
    private readonly cwd: string
  ) {}

  private interpolate(s: string): string {
    return s.replace(/\$\{cwd\}/g, this.cwd);
  }

  async start(): Promise<void> {
    this.status = "starting";
    this.error = "";

    const serverCwd = this.cfg.cwd
      ? resolve(this.cwd, this.interpolate(this.cfg.cwd))
      : this.cwd;

    const env: Record<string, string> = {
      ...process.env as Record<string, string>,
      ...Object.fromEntries(
        Object.entries(this.cfg.env ?? {}).map(([k, v]) => [k, this.interpolate(v)])
      ),
    };

    const args = (this.cfg.args ?? []).map((a) => this.interpolate(a));

    // Resuelve el comando:
    //   "pipx:<paquete>"     → python.exe del venv pipx de ese paquete
    //   "pipx-bin:<paquete>" → ejecutable CLI del venv pipx (ej: cortex.exe)
    //   "python" o "python3" → intenta auto-detectar el paquete desde los args
    let command = this.interpolate(this.cfg.command);
    if (command.startsWith("pipx-bin:")) {
      // Sintaxis: "pipx-bin:<package>:<binname>"
      // Ejemplo:  "pipx-bin:cortex-memory:cortex" → cortex.exe en el venv de cortex-memory
      const parts = command.slice(9).split(":");
      const pkg = parts[0].trim();
      const binName = (parts[1] ?? "").trim() || pkg.split("-")[0];
      command = resolvePipxBin(pkg, binName);
    } else if (command.startsWith("pipx:")) {
      const pkg = command.slice(5).trim();
      command = resolvePipxPython(pkg);
    } else if (command === "python" || command === "python3") {
      const mIdx = args.indexOf("-m");
      if (mIdx !== -1 && args[mIdx + 1]) {
        const pkg = args[mIdx + 1].split(".")[0];
        const resolved = resolvePipxPython(pkg);
        if (resolved !== "python" && resolved !== "python3") {
          command = resolved;
        }
      }
    }


    try {
      this.proc = spawn(command, args, {
        cwd: serverCwd,
        env,
        stdio: ["pipe", "pipe", "pipe"],
      });

      let stderrBuf = "";
      this.proc.stderr?.setEncoding("utf-8");
      this.proc.stderr?.on("data", (d: string) => {
        stderrBuf += d;
        this.lastStderr = (this.lastStderr + "\n" + stderrBuf).slice(-2000);
      });

      this.proc.stdout?.setEncoding("utf-8");
      this.proc.stdout?.on("data", (chunk: string) => {
        this.buf += chunk;
        const lines = this.buf.split("\n");
        this.buf = lines.pop() ?? "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const msg: McpJsonRpc = JSON.parse(trimmed);
            if (msg.id !== undefined) {
              const p = this.pending.get(msg.id as number);
              if (p) {
                this.pending.delete(msg.id as number);
                if (msg.error) p.reject(new Error(msg.error.message));
                else p.resolve(msg.result);
              }
            }
          } catch {}
        }
      });

      this.proc.on("exit", (code) => {
        // Espera un tick para que los datos de stderr lleguen antes de marcar el error
        setTimeout(() => {
          if (this.status !== "stopped") {
            this.status = "error";
            const hint = this.lastStderr
              ? `\n  stderr: ${this.lastStderr.split("\n").filter(l => l.trim()).slice(-5).join(" | ").slice(0, 400)}`
              : " (sin output en stderr — ¿está el servidor MCP instalado?)";
            this.error = `Proceso terminó con código ${code}${hint}`;
          }
          for (const p of this.pending.values()) p.reject(new Error(this.error || "MCP server exited"));
          this.pending.clear();
        }, 100);
      });

      this.proc.on("error", (err) => {
        this.status = "error";
        this.error = err.message;
      });

      // Handshake: initialize → initialized → tools/list
      await this.send("initialize", {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "pi-cortex-mcp", version: "1.0.0" },
      });

      this.sendNotification("notifications/initialized", {});

      const result = await this.send("tools/list", {});
      this.tools = result?.tools ?? [];
      this.status = "ready";
    } catch (err: any) {
      // Espera 150ms para que el evento stderr llegue antes del exit
      await new Promise(r => setTimeout(r, 150));
      this.status = "error";
      const baseMsg = err.message ?? String(err);
      const stderrLines = this.lastStderr
        .split("\n").filter((l: string) => l.trim()).slice(-8).join("\n");
      this.error = stderrLines
        ? `${baseMsg}\nstderr:\n${stderrLines}`
        : `${baseMsg}\n(sin stderr — verificá que .venv esté activo y cortex.mcp.server instalado)`;
      throw new Error(this.error);
    }
  }

  private send(method: string, params: any): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.proc?.stdin?.writable) {
        reject(new Error("MCP server not running"));
        return;
      }
      const id = this.nextId++;
      const msg: McpJsonRpc = { jsonrpc: "2.0", id, method, params };
      this.pending.set(id, { resolve, reject });

      // Timeout de 30s por request
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`MCP request timed out: ${method}`));
      }, 30_000);
      this.pending.get(id)!.resolve = (r) => { clearTimeout(timer); resolve(r); };
      this.pending.get(id)!.reject = (e) => { clearTimeout(timer); reject(e); };

      this.proc!.stdin!.write(JSON.stringify(msg) + "\n");
    });
  }

  private sendNotification(method: string, params: any) {
    if (!this.proc?.stdin?.writable) return;
    const msg: McpJsonRpc = { jsonrpc: "2.0", method, params };
    this.proc.stdin.write(JSON.stringify(msg) + "\n");
  }

  async callTool(toolName: string, args: Record<string, any>): Promise<string> {
    const result = await this.send("tools/call", { name: toolName, arguments: args });
    // MCP tools/call → { content: [{type, text}] }
    if (Array.isArray(result?.content)) {
      return result.content
        .filter((c: any) => c.type === "text")
        .map((c: any) => c.text)
        .join("\n");
    }
    return JSON.stringify(result);
  }

  stop() {
    this.status = "stopped";
    try { this.proc?.stdin?.end(); } catch {}
    try { this.proc?.kill(); } catch {}
    this.proc = null;
    this.pending.clear();
  }
}

// ── Extension ──────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  const clients = new Map<string, McpClient>();

  // Renderer para los mensajes de status de esta extensión
  pi.registerMessageRenderer("cortex-mcp", (message, _options, theme) => {
    const content = typeof message.content === "string" ? message.content : "";
    return new Text(theme.fg("cyan", "⬡ mcp: ") + content, 0, 0);
  });

  // ── Carga la config y levanta los servidores ───────────────────────────
  async function loadAndStart(cwd: string, ctx: any) {
    // Primero intenta .pi/mcp.json; si no existe, intenta pi-mcp-adapter.json en la raíz
    const candidates = [
      join(cwd, ".pi", "mcp.json"),
      join(cwd, "pi-mcp-adapter.json"),
    ];

    let config: McpConfig | null = null;
    let configPath = "";

    for (const candidate of candidates) {
      if (existsSync(candidate)) {
        try {
          config = JSON.parse(readFileSync(candidate, "utf-8")) as McpConfig;
          configPath = candidate;
          break;
        } catch (err: any) {
          ctx.ui.notify(`⚠ MCP: error leyendo ${candidate}: ${err.message}`, "warning");
        }
      }
    }

    if (!config || !config.mcpServers || Object.keys(config.mcpServers).length === 0
        || (config as any)._disabled === true) {
      // Sin servidores activos (o deshabilitado intencionalmente) → silencio
      return;
    }

    ctx.ui.notify(`⬡ MCP: levantando servidores desde ${configPath}…`, "info");

    for (const [name, cfg] of Object.entries(config.mcpServers)) {
      const client = new McpClient(name, cfg, cwd);
      clients.set(name, client);

      try {
        await client.start();
        ctx.ui.notify(`✓ MCP: "${name}" listo — ${client.tools.length} tool(s)`, "success");

        // Registra cada tool del servidor como tool de Pi
        for (const tool of client.tools) {
          // Naming: si el nombre completo resultante tendría el segmento "cortex" duplicado
          // (mcp_cortex_cortex_search), lo colapsamos a cortex_search directamente.
          const serverSlug = name.replace(/-/g, "_");
          const rawName = `mcp_${serverSlug}_${tool.name}`;
          // Detecta duplicado: mcp_cortex_cortex_* → cortex_*
          const dupPattern = new RegExp(`^mcp_${serverSlug}_${serverSlug}_`);
          const piToolName = dupPattern.test(rawName)
            ? rawName.replace(`mcp_${serverSlug}_`, "")
            : rawName;
          const schema = tool.inputSchema?.properties ?? {};

          // Construye el schema Typebox equivalente al inputSchema del MCP tool
          const tbProps: Record<string, any> = {};
          const required: string[] = tool.inputSchema?.required ?? [];

          for (const [key, def] of Object.entries(schema)) {
            const d = def as any;
            if (d.type === "string") {
              tbProps[key] = required.includes(key)
                ? Type.String({ description: d.description ?? key })
                : Type.Optional(Type.String({ description: d.description ?? key }));
            } else if (d.type === "number" || d.type === "integer") {
              tbProps[key] = required.includes(key)
                ? Type.Number({ description: d.description ?? key })
                : Type.Optional(Type.Number({ description: d.description ?? key }));
            } else if (d.type === "boolean") {
              tbProps[key] = required.includes(key)
                ? Type.Boolean({ description: d.description ?? key })
                : Type.Optional(Type.Boolean({ description: d.description ?? key }));
            } else {
              // Tipos complejos (array, object) → string serializado
              tbProps[key] = Type.Optional(Type.String({ description: `(JSON) ${d.description ?? key}` }));
            }
          }

          pi.registerTool({
            name: piToolName,
            label: `MCP: ${name}/${tool.name}`,
            description: tool.description ?? `MCP tool ${tool.name} del servidor ${name}`,
            parameters: Type.Object(tbProps),
            async execute(_toolCallId: string, params: Record<string, any>, _signal: AbortSignal) {
              // Deserializa strings JSON para tipos complejos
              const callArgs: Record<string, any> = {};
              for (const [k, v] of Object.entries(params)) {
                if (v === undefined || v === null) continue;
                if (typeof v === "string") {
                  try { callArgs[k] = JSON.parse(v); } catch { callArgs[k] = v; }
                } else {
                  callArgs[k] = v;
                }
              }

              try {
                const result = await client.callTool(tool.name, callArgs);
                return {
                  content: [{ type: "text" as const, text: result }],
                  details: { server: name, tool: tool.name, args: callArgs },
                };
              } catch (err: any) {
                return {
                  content: [{ type: "text" as const, text: `Error MCP: ${err.message}` }],
                  details: { error: err.message },
                };
              }
            },
          });
        }
      } catch (err: any) {
        const clientErr = clients.get(name);
        const stderrInfo = clientErr?.lastStderr
          ? `\nstderr:\n${clientErr.lastStderr.split("\n").slice(-8).join("\n")}`
          : "";
        ctx.ui.notify(
          `⚠ MCP: "${name}" falló al iniciar: ${err.message}${stderrInfo}`,
          "warning"
        );
      }
    }
  }

  // ── Arranca al inicio de sesión ────────────────────────────────────────
  pi.on("session_start", async (_event, ctx) => {
    await loadAndStart(ctx.cwd, ctx);
  });

  // ── Shutdown limpio al cerrar ──────────────────────────────────────────
  pi.on("session_shutdown", async () => {
    for (const client of clients.values()) client.stop();
    clients.clear();
  });

  // ── /mcp — estado de servidores ────────────────────────────────────────
  pi.registerCommand("mcp", {
    description: "Muestra el estado de los servidores MCP de Cortex",
    handler(_args: string, ctx: any) {
      if (clients.size === 0) {
        ctx.ui.notify("Sin servidores MCP activos. Verificá .pi/mcp.json", "warning");
        return;
      }

      const lines = [...clients.entries()].map(([name, client]) => {
        const icon =
          client.status === "ready" ? "✓" :
          client.status === "error" ? "✗" :
          client.status === "starting" ? "◉" : "○";

        const toolList = client.tools.length > 0
          ? client.tools.map(t => `mcp_${name.replace(/-/g, "_")}_${t.name}`).join(", ")
          : "(sin tools)";

        const errorPart = client.error ? `\n  Error: ${client.error}` : "";
        const stderrPart = client.lastStderr
          ? `\n  Stderr (últimas líneas):\n${client.lastStderr.split("\n").filter((l: string) => l.trim()).slice(-6).map((l: string) => "    " + l).join("\n")}`
          : "";
        return `${icon} ${name} [${client.status}]\n  Tools: ${toolList}${errorPart}${stderrPart}`;
      });

      pi.sendMessage({
        customType: "cortex-mcp",
        content: `Servidores MCP:\n\n${lines.join("\n\n")}`,
        display: true,
      });
    },
  });

  // ── /mcp-debug — muestra rutas resueltas sin levantar el servidor ───────
  pi.registerCommand("mcp-debug", {
    description: "Muestra las rutas de Python que la extensión usaría para cada servidor MCP",
    handler(_args: string, ctx: any) {
      const cwd = ctx.cwd;
      const candidates = [
        join(cwd, ".pi", "mcp.json"),
        join(cwd, "pi-mcp-adapter.json"),
      ];

      let config: McpConfig | null = null;
      let configPath = "(no encontrado)";
      for (const c of candidates) {
        if (existsSync(c)) {
          try { config = JSON.parse(readFileSync(c, "utf-8")) as McpConfig; configPath = c; break; } catch {}
        }
      }

      if (!config) {
        ctx.ui.notify("⚠ No se encontró .pi/mcp.json ni pi-mcp-adapter.json", "warning");
        return;
      }

      const isWin = process.platform === "win32";
      const lines = [`Config: ${configPath}`, ""];

      for (const [name, cfg] of Object.entries(config.mcpServers)) {
        let command = cfg.command;
        let resolved = command;

        if (command.startsWith("pipx:")) {
          const pkg = command.slice(5).trim();
          resolved = resolvePipxPython(pkg);
        } else if (command === "python" || command === "python3") {
          const args = cfg.args ?? [];
          const mIdx = args.indexOf("-m");
          if (mIdx !== -1 && args[mIdx + 1]) {
            const pkg = args[mIdx + 1].split(".")[0];
            const r = resolvePipxPython(pkg);
            if (r !== "python" && r !== "python3") resolved = r;
          }
        }

        const exists = existsSync(resolved);
        const icon = exists ? "✓" : (resolved === command ? "?" : "✗");
        lines.push(`${icon} Servidor: ${name}`);
        lines.push(`  command en config : ${command}`);
        lines.push(`  python resuelto   : ${resolved}`);
        lines.push(`  existe en disco   : ${exists ? "sí" : "NO — ruta incorrecta"}`);
        lines.push(`  platform          : ${process.platform}`);
        if (!exists && !isWin) {
          lines.push(`  sugerencia: corré 'pipx environment' en tu terminal para ver PIPX_LOCAL_VENVS`);
        }
        if (!exists && isWin) {
          const local = process.env.LOCALAPPDATA ?? "no definido";
          lines.push(`  LOCALAPPDATA: ${local}`);
        }
        lines.push("");
      }

      pi.sendMessage({
        customType: "cortex-mcp",
        content: lines.join("\n"),
        display: true,
      });
    },
  });

  // ── /mcp-restart — reinicia todos los servidores ──────────────────────
  pi.registerCommand("mcp-restart", {
    description: "Reinicia todos los servidores MCP de Cortex",
    async handler(_args: string, ctx: any) {
      ctx.ui.notify("⬡ MCP: reiniciando servidores…", "info");
      for (const client of clients.values()) client.stop();
      clients.clear();
      await loadAndStart(ctx.cwd, ctx);
    },
  });
}
