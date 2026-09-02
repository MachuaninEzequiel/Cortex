---
title: Herramientas MCP para Tickets, Vault y Calidad
description: cortex_sync_ticket, cortex_import_hu, cortex_sync_vault, cortex_validate_handoff y cortex_verify_session_claims.
---

Herramientas para sincronizar requerimientos externos, verificar entregables e indexar el Vault.

---

## 1. `cortex_sync_ticket`
Sincroniza un ticket de Jira u otro sistema de seguimiento con el Vault local:

* **Parámetros:**
  * `ticket_id` (string, requerido): Clave del ticket (ej: `PROJ-456`).
  * `update_status` (boolean, default `false`): Si debe actualizar el estado del ticket remoto.

---

## 2. `cortex_import_hu` y `cortex_get_hu`
* **`cortex_import_hu`**: Importa una historia de usuario y la transforma en una nota estructurada en `vault/hu/`.
* **`cortex_get_hu`**: Consulta los criterios de aceptación y estado de una historia de usuario por su ID.

---

## 3. `cortex_sync_vault`
Fuerza una re-sincronización y actualización inmediata de los índices léxicos BM25 y la caché de vectores para todas las notas del Vault.

---

## 4. `cortex_validate_handoff`
Verifica que un documento de handoff cumpla con la estructura formal antes de que un agente ceda el control a otro o finalice su turno.

* **Parámetros:**
  * `handoff_path` (string, requerido): Ruta al archivo Markdown de handoff.

---

## 5. `cortex_verify_session_claims`
Comprueba de forma determinista que los reclamos declarados en la sesión (por ejemplo: *"se añadieron 5 tests unitarios que pasan exitosamente"*) se correspondan con la evidencia real de ejecución de comandos y diffs de Git.
