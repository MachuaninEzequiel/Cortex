---
title: Integración con OpenAI Codex y Google Antigravity
description: Conexión de Cortex con OpenAI Codex CLI y Google Antigravity.
---

Cortex soporta de forma nativa agentes basados en los modelos y plataformas de OpenAI y Google.

---

## 1. Integración con OpenAI Codex

### Configuración con el Plugin Nativo
Cortex incluye un plugin preconfigurado para Codex en `.codex-plugin/`.

```bash
cortex ide setup codex
```

### Configuración de MCP
En el archivo de configuración de Codex:

```json
{
  "mcp_servers": {
    "cortex": {
      "command": "cortex",
      "args": ["mcp-server"]
    }
  }
}
```

---

## 2. Integración con Google Antigravity

Antigravity puede interactuar con Cortex a través del servidor MCP o directamente mediante la invocación de subcomandos de `cortex-cli`.

### Configuración de Servidor MCP en Antigravity
Añada Cortex a la lista de servidores MCP de su entorno:

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

Al estar registrado, el agente Antigravity consulta automáticamente la memoria episódica y el Vault de Cortex para mantener consistencia a lo largo de tareas complejas de refactorización y arquitectura.
