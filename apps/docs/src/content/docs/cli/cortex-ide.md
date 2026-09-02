---
title: cortex ide
description: Inyección automática de servidores MCP, prompts y perfiles de integración en entornos de desarrollo.
---

El comando `cortex ide` configura de forma automatizada la integración de Cortex con los principales editores de código e interfaces de agentes ([`cortex-setup::ide`](file:///home/chucho/Cortex/rust/crates/cortex-setup)).

---

## Editores e IDEs Compatibles por Niveles (Tiers)

Cortex clasifica los entornos de desarrollo según su grado de integración y soporte:

* **Target IDEs (Soporte Oficial Completo):**
  * `claude_code` (Claude Code CLI / `.claude/` / `claude.json`)
  * `codex` (OpenAI Codex CLI / `.codex-plugin/`)
  * `opencode` (OpenCode runtime)
  * `pi` (Pi IDE / `cortex-pi`)
* **Community IDEs (Ampliamente Validados):**
  * `cursor` (Cursor Rules `.cursor/rules/` y MCP)
  * `claude_desktop` (Claude Desktop App `claude_desktop_config.json`)
  * `vscode` (Visual Studio Code `.vscode/settings.json`)
  * `windsurf` (Windsurf IDE)
* **Experimental IDEs:**
  * `antigravity` (Google Antigravity CLI & IDE)
  * `zed` (Zed Editor)
  * `hermes` (Hermes Agent)

---

## Subcomandos

```text
Usage: cortex ide <COMMAND>

Commands:
  list    Lista todos los IDEs soportados y su estado de instalación
  setup   Inyecta la configuración MCP y reglas en el IDE especificado
  remove  Elimina la configuración de Cortex del IDE especificado
  status  Muestra el estado de los hooks y archivos de configuración
```

---

## Ejemplos de Configuración

### 1. Listar Entornos y Estado
```bash
cortex ide list
```
Salida en tabla:
```text
IDE               Tier          Status         Config Path
----------------------------------------------------------------------
claude_code       target        Installed      .claude/settings.json
cursor            community     Configured     .cursor/rules/cortex.mdc
pi                target        Not Installed  --
vscode            community     Configured     .vscode/settings.json
```

### 2. Configurar Claude Code
```bash
cortex ide setup claude_code
```
Inyecta la definición del servidor MCP de Cortex en la configuración local de Claude Code para que pueda invocar las 32 herramientas automáticamente.

### 3. Configurar Cursor
```bash
cortex ide setup cursor
```
Genera las reglas `.cursorrules` / `.cursor/rules/cortex.mdc` instruyendo al agente a consultar el Vault y registrar checkpoints al completar tareas.

### 4. Configurar Múltiples IDEs
```bash
cortex ide setup --all
```
