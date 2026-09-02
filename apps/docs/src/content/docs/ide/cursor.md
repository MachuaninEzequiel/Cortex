---
title: Integración con Cursor y Windsurf
description: Configuración de Cursor Rules (.cursor/rules/) y conexión MCP en Cursor y Windsurf IDE.
---

Cortex potencia la experiencia en **Cursor** y **Windsurf** inyectando directrices de memoria y exponiendo el servidor MCP para el agente de Composer.

---

## 1. Integración en Cursor

### Configuración Automática
```bash
cortex ide setup cursor
```

Este comando genera:
1. `.cursor/rules/cortex.mdc`: Reglas de comportamiento para que el agente consulte el Vault antes de responder.
2. Definición MCP en la configuración de Cursor (`~/.cursor/mcp.json` o settings locales).

### Configuración Manual de MCP en Cursor
En **Settings > Features > MCP**:
* **Name:** `cortex`
* **Type:** `command`
* **Command:** `cortex mcp-server`

---

## 2. Reglas del Agente (`.cursor/rules/cortex.mdc`)

Las directrices canónicas de Cortex instruyen al agente en Cursor a:
1. Ejecutar `cortex_ping` para validar disponibilidad.
2. Consultar `cortex_context` o `cortex_search` antes de modificar código existente.
3. Registrar checkpoints con `cortex_session_checkpoint` tras completar refactorizaciones significativas.
4. Redactar notas con `cortex_write_doc` en lugar de crear archivos arbitrarios.

---

## 3. Integración en Windsurf

En el archivo `~/.codeium/windsurf/mcp_config.json`:

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
Cascade (el agente de Windsurf) detectará automáticamente las herramientas de Cortex para navegación y retención contextual.
