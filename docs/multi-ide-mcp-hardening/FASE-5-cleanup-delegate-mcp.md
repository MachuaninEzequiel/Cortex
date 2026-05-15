# FASE 5 — Cleanup del delegate experimental en MCP

**Semaforo:** Amarillo (cambia el contrato publico del MCP server).
**Pre-requisitos:** Fase 4 cerrada (cada IDE tiene su delegacion nativa generada por su adapter).
**Bloquea:** Fase 7.

---

## Objetivo

Eliminar `cortex_delegate_task`, `cortex_delegate_batch` y todo el codigo relacionado del MCP server. Estos tools eran un acoplamiento erroneo: la delegacion a subagentes es responsabilidad del IDE (Task tool en Claude Code, comando CLI en opencode, etc.), no del MCP server de Cortex.

Coherencia con principio rector #1 ("Cortex se comporta igual en todos los IDEs"): el MCP server expone tools de **memoria, busqueda, persistencia, validacion**. La **orquestacion de subagentes** es del IDE. Punto.

---

## Tasks

### Task 5.1 — Confirmar que no hay callers externos

Esto se basa en `INVENTARIO.md` Task 0.3. Para cada caller listado:
- Si esta en codigo de produccion del repo: verificar que Fase 4 lo migro a la delegacion nativa del IDE.
- Si esta en tests: actualizar/eliminar el test (los tests del delegate experimental dejan de tener sentido).
- Si esta en scripts/docs: actualizar la doc para reflejar el nuevo modelo.

Si Task 0.3 documento callers fuera del repo de Cortex (ej. en cortex-pi separado, en un proyecto de adopter conocido), notificar al creador antes de proceder.

### Task 5.2 — Eliminar tools del MCP server

**Archivo:** `cortex/mcp/server.py`.

**Cambios:**
- Eliminar `types.Tool(name="cortex_delegate_task", ...)` de `handle_list_tools` (linea 454-466).
- Eliminar `types.Tool(name="cortex_delegate_batch", ...)` de `handle_list_tools` (linea 467-489).
- Eliminar el handling en `handle_call_tool` (lineas 601 y 615 aproximadamente, segun el codigo actual).
- Eliminar metodos privados huerfanos:
  - `_delegate_task` (linea ~1083)
  - `_delegate_batch` (linea ~1155)
  - `_store_task_result` (linea ~1030)
  - `_get_task_result` (si queda huerfano)
- Eliminar imports huerfanos (`asyncio` se mantiene por otros usos; `shutil.which` se elimina si no hay otros usos).

### Task 5.3 — Eliminar dependencias en `cortex/autopilot/`

**Archivo posible:** `cortex/autopilot/delegation.py`, `cortex/autopilot/mcp_tools.py`.

Si estos modulos referencian el delegate del MCP, refactorizar para que NO lo hagan. Si quedan completamente huerfanos, eliminarlos.

NOTA: el `AutopilotMCPTools` del MCP server (linea 21-23 de `cortex/mcp/server.py`) NO es lo mismo que el delegate. Verificar con cuidado que esa parte sigue funcionando — solo se elimina lo del delegate experimental.

### Task 5.4 — Actualizar tests

**Archivos:**
- `tests/unit/mcp/test_delegate_*.py` (si existen): eliminar.
- `tests/integration/test_delegate_*.py` (si existen): eliminar.
- Cualquier test que referencie `cortex_delegate_task` / `cortex_delegate_batch`: limpiar.

### Task 5.5 — Actualizar documentacion

**Archivos:**
- `CHANGELOG.md`: nota de breaking change.
- `docs/architecture/mcp-server-resilience.md` (creado en Fase 1, ampliado en Fase 2): seccion "Delegacion: por que NO esta en el MCP".
- Cualquier README, guia de adopter, doc de prompt que mencione `cortex_delegate_task`: actualizar.

### Task 5.6 — Verificacion exhaustiva post-eliminacion

Ejecutar en el repo:
```
grep -rE "cortex_delegate_task|cortex_delegate_batch|_delegate_task|_delegate_batch|_store_task_result" \
  --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.json"
```

**Criterio:** 0 resultados.

Si aparece algun resultado, decidir caso por caso:
- Es un comentario historico justificable -> reescribir el comentario para no usar el nombre como referencia viva.
- Es un caller olvidado -> eliminar / migrar.
- Es documentacion de "version anterior" -> actualizar.

---

## Archivos involucrados

- Modificados:
  - `cortex/mcp/server.py` (eliminacion de ~150 lineas).
  - `cortex/autopilot/delegation.py`, `cortex/autopilot/mcp_tools.py` (refactor o eliminacion segun corresponda).
  - `CHANGELOG.md`.
  - `docs/architecture/mcp-server-resilience.md`.
- Eliminados:
  - Tests del delegate experimental.
  - Modulos huerfanos de autopilot (si aplica).

---

## Criterios de aceptacion

- [ ] `cortex_delegate_task` y `cortex_delegate_batch` no aparecen en `handle_list_tools`.
- [ ] El MCP server arranca limpio (sin warnings, sin errores) tras la eliminacion.
- [ ] Todos los tests pasan despues del cleanup (los del delegate fueron eliminados, no rotos).
- [ ] `grep` exhaustivo de los nombres devuelve 0 resultados activos.
- [ ] CHANGELOG documenta el breaking change con migration note.
- [ ] La documentacion arquitectural explica por que la delegacion vive en el IDE, no en el MCP.

---

## Gate de cero deuda tecnica

- [ ] CERO `# DEPRECATED` comments dejados en el codigo. La eliminacion es total, no soft-deprecate.
- [ ] CERO funciones huerfanas (`_delegate_*`, `_store_task_result`, etc.) sobrevivientes en el codigo.
- [ ] CERO tests skipeados con razon "delegate eliminado". Los tests se eliminan.
- [ ] CERO referencias en docs internos a "antes era posible delegar via MCP". El relato del repo se actualiza limpiamente.
- [ ] CERO entradas en YAML/JSON de configuracion para los tools eliminados.
- [ ] El smoke test en Claude Code post-Fase 4 sigue verde (la delegacion nativa funciona).
- [ ] El smoke test en opencode post-Fase 4 sigue verde (la delegacion nativa funciona).

---

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Algun adopter externo dependia de `cortex_delegate_task` directamente | Notificar via CHANGELOG y, si aplica, en el canal de comunicacion con early adopters. La migracion es: dejar que el IDE delegue nativamente (Fase 4 ya lo configura). |
| La eliminacion descubre dependencias ocultas que no estaban en `INVENTARIO.md` | Task 5.6 es el safety net (grep exhaustivo). Si algo aparece, no se mergea hasta resolverlo. |
| Los modulos `autopilot/delegation.py` y `autopilot/mcp_tools.py` tienen logica que NO es solo del delegate experimental | Inspeccionar individualmente. Solo eliminar lo que es exclusivo del delegate; preservar la logica que sirve al `AutopilotService` general. |

---

## Estimacion

1 sesion. El trabajo principal es chequeo exhaustivo y limpieza, no diseño nuevo.

---

## Handoff a Fase 6 / Fase 7

```yaml
agent: fase-5-cleanup-delegate-mcp
status: completed
artifacts_modified:
  - cortex/mcp/server.py (~150 lineas eliminadas)
  - CHANGELOG.md
  - docs/architecture/mcp-server-resilience.md
artifacts_removed:
  - tests/unit/mcp/test_delegate_*.py (si existian)
  - cortex/autopilot/delegation.py (si quedo huerfano)
verified_claims:
  - "grep exhaustivo de cortex_delegate_* devuelve 0 resultados activos"
  - "MCP server arranca limpio sin tools delegate"
  - "Smoke test multi-IDE pos-eliminacion sigue verde"
context_for_next:
  - "Fase 7 (validacion E2E) puede empezar; Fase 6 (setup full) es independiente"
```
