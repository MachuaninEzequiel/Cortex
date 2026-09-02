---
title: Integración con Claude Code y Claude Desktop
description: Configuración del servidor MCP de Cortex en Claude Code CLI y la aplicación de escritorio Claude Desktop.
---

Cortex se integra de forma transparente con el ecosistema de **Anthropic Claude**, tanto en su herramienta de línea de comandos (**Claude Code**) como en su cliente de escritorio (**Claude Desktop**).

---

## 1. Integración con Claude Code (CLI)

### Configuración Automática
Ejecute en la raíz de su repositorio:

```bash
cortex ide setup claude_code
```

### Configuración Manual (`.claude/settings.json` o `claude.json`)
Añada la definición del servidor MCP de Cortex:

```json
{
  "mcpServers": {
    "cortex": {
      "command": "cortex",
      "args": ["mcp-server"]
    }
  }
}
```

### Verificación
Inicie Claude Code y compruebe que las herramientas están disponibles:

```bash
claude
> /mcp
```
Claude listará las 32 herramientas de Cortex (`cortex_ping`, `cortex_search`, `cortex_session_open`, etc.).

---

## 2. Integración con Claude Desktop

Edite el archivo de configuración de Claude Desktop:
* **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Linux:** `~/.config/Claude/claude_desktop_config.json`
* **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cortex": {
      "command": "cortex",
      "args": ["mcp-server"]
    }
  }
}
```

Reinicie la aplicación Claude Desktop. El icono de herramientas (martillo) mostrará todas las capacidades cognitivas de Cortex.
