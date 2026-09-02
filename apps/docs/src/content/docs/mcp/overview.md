---
title: Catálogo del Protocolo MCP (32 Tools)
description: Arquitectura del servidor MCP nativo en rmcp, transporte stdio y catálogo completo de las 32 herramientas para LLMs.
---

Cortex implementa un servidor nativo de **Model Context Protocol (MCP)** en el crate [`cortex-mcp`](file:///home/chucho/Cortex/rust/crates/cortex-mcp), desarrollado sobre `rmcp` y `tokio`.

El servidor expone exactamente **32 herramientas canónicas** bajo la versión de protocolo **2.2**, garantizando paridad estricta y contratos validados mediante snapshots de pruebas doradas (*golden contracts*).

---

## Cómo Iniciar el Servidor MCP

El servidor se ejecuta a través del comando:

```bash
cortex mcp-server
# o el alias: cortex mcp-serve
```

Se comunica mediante transporte estándar **`stdio` (JSON-RPC)**, haciéndolo compatible de forma nativa con Claude Desktop, Claude Code, Cursor, Windsurf, OpenCode, Codex y Google Antigravity.

---

## Catálogo de las 32 Herramientas MCP

| # | Nombre de la Tool | Categoría | Propósito Principal |
| :-: | :--- | :--- | :--- |
| 1 | **`cortex_ping`** | Health | Health check ultrarrápido (&lt;50ms) para verificar disponibilidad. |
| 2 | **`cortex_search_vector`** | Búsqueda | Búsqueda semántica conceptual profunda con modelo ONNX. |
| 3 | **`cortex_search`** | Búsqueda | Búsqueda léxica instantánea con filtros estructurales. |
| 4 | **`cortex_context`** | Búsqueda | Extracción de contexto enriquecido para inyección en prompts. |
| 5 | **`cortex_sync_ticket`** | Integración | Sincronización de tickets externos y requerimientos. |
| 6 | **`cortex_create_spec`** | Documentos | Creación formal de especificaciones técnicas en el Vault. |
| 7 | **`cortex_emit_proposal`** | Arquitectura | Emisión de propuestas técnicas preliminares. |
| 8 | **`cortex_save_session`** | Sesiones | Guardado y snapshot del estado de la sesión. |
| 9 | **`cortex_validate_handoff`** | Sesiones | Validación de handoffs antes de transferir control. |
| 10 | **`cortex_verify_session_claims`** | Calidad | Verificación automática de reclamos de tests y tareas. |
| 11 | **`cortex_import_hu`** | Requisitos | Importación de Historias de Usuario desde fuentes externas. |
| 12 | **`cortex_get_hu`** | Requisitos | Consulta de una historia de usuario por su ID. |
| 13 | **`cortex_sync_vault`** | Vault | Sincronización e indexación del Vault Markdown. |
| 14 | **`cortex_autopilot_start`** | Autopilot | Inicio de una sesión de autopilot bajo políticas de supervisión. |
| 15 | **`cortex_autopilot_preflight`** | Autopilot | Chequeo de seguridad preventivo antes de acciones destructivas. |
| 16 | **`cortex_autopilot_checkpoint`** | Autopilot | Checkpoint en el ciclo de ejecución de autopilot. |
| 17 | **`cortex_autopilot_finish`** | Autopilot | Finalización formal de la tarea de autopilot. |
| 18 | **`cortex_autopilot_status`** | Autopilot | Consulta de políticas activas y advertencias. |
| 19 | **`cortex_session_open`** | Sesiones | Apertura de una nueva sesión de desarrollo. |
| 20 | **`cortex_session_checkpoint`** | Sesiones | Registro de puntos de control intermedios con fuentes tipadas. |
| 21 | **`cortex_session_close`** | Sesiones | Cierre de la sesión activa. |
| 22 | **`cortex_session_status`** | Sesiones | Inspección del estado y tiempo de la sesión actual. |
| 23 | **`cortex_finish_session`** | Sesiones | Finalización con consolidación de evidencia y notas. |
| 24 | **`cortex_documenter_briefing`** | Documentos | Briefing para el agente documentador de Cortex. |
| 25 | **`cortex_close_session`** | Sesiones | Cierre legacy de sesiones con persistencia de resumen. |
| 26 | **`cortex_session_list`** | Sesiones | Listado tabular y filtrado de sesiones históricas. |
| 27 | **`cortex_self_review_note`** | Calidad | Creación de nota de auto-revisión de código e impacto. |
| 28 | **`cortex_write_doc`** | Documentos | Escritor canónico genérico para los 11 `DocTypes` del Vault. |
| 29 | **`write_design_note_canonical`**| Documentos | Persistencia canónica de notas de diseño técnico. |
| 30 | **`cortex_session_task_list`** | Tareas | Lista ordenada de tareas granulares de la sesión. |
| 31 | **`cortex_session_task_update`** | Tareas | Actualización del estado de una tarea (`pending`, `in-progress`, `done`, `blocked`). |
| 32 | **`cortex_review_checkpoint`** | Calidad | Checkpoint formal de revisión de código y entregables. |

---

## Directrices de Uso para Agentes de IA

1. **Verificar antes de gastar tokens:** Ejecutar siempre `cortex_ping` al inicio de la conversación. Si `status != 'ok'`, abortar con un error claro al usuario en lugar de degradar la operación.
2. **Búsqueda antes de asumir:** Usar `cortex_search` o `cortex_context` antes de responder preguntas sobre la arquitectura o contratos existentes del proyecto.
3. **Persistir decisiones canónicas:** No escribir archivos Markdown con nombres inventados; utilizar `cortex_write_doc` para que el sistema valide el frontmatter y mantenga los índices actualizados.
