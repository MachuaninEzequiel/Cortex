---
title: Incidente AppFutbol — MCP Duplicate-Loop
date: 2026-05-22
status: diagnosed
severity: high
affected_ides: [pi, claude_code, opencode]  # bug es del core, no de Pi
related:
  - ./../conversacion.md   # transcript completo del piloto AppFutbol
---

# AppFutbol — MCP Duplicate-Loop (2026-05-22)

## Qué pasó (TL;DR)

Durante el piloto de AppFutbol con el flujo `sync → SDDwork → documenter`, la primera spec (arquitectura) salió completa pero la segunda (Fase 1) cayó en un loop de duplicados que dejó el vault con **5 sesiones huérfanas + 1 archivo de spec fantasma**. La causa raíz no es de Pi; es del **core de Cortex**, y por eso los fixes van en `cortex/` (la fuente de verdad), no en `cortex-pi/`.

## Causa raíz — 5 capas que se amplificaron

### Capa 1 — Timeout cliente < tiempo real del server
`cortex_create_spec` tarda 30-80s legítimamente (write + `semantic.sync()` + `session_service.open` + `_store_episodic` con ONNX). El timeout del SDK MCP del cliente (en este caso Pi) es ~30-50s. Cuando el cliente corta, el server **sigue procesando y completa** silenciosamente: archivo escrito, sesión abierta, embedding indexado. El agente cree que falló y reintenta — el retry choca con el archivo recién escrito.

Evidencia: log MCP `mcp_calls_20260522_102306.log` líneas 23-30. Spec arquitectura completó a los 57s; Pi cortó a los ~50s; el retry vio `DuplicateDocumentError`.

### Capa 2 — Limpieza incompleta tras los falsos timeouts
Cada falso timeout deja: archivo en `vault/specs/`, sesión YAML en `.cortex/sessions/`, embedding en `chroma.sqlite3`. Cuando el usuario o el agente borran el archivo "fantasma" que conocen, los otros 3 artifacts paralelos quedan. El próximo intento choca con ellos.

### Capa 3 — SDDwork improvisa cuando `cortex_review_checkpoint` rechaza por scope
La spec de arquitectura no listaba `vault/designs/` en `files_in_scope`. Cuando SDDwork en Deep Track creó el design doc canónico, `cortex_review_checkpoint` lo rechazó con "files touched outside spec scope" (`cortex/session/quality_gates.py:133`). El skill de SDDwork **no tiene regla** para este caso → improvisó creando una spec nueva él mismo (violación: solo `cortex-sync` crea specs) → cuando eso falló por timeout, escribió spec a mano → entró en Capa 1+2.

### Capa 4 — Bugs de schema y serialización en el core
- `_serialize_reconstruction:76` (`cortex/mcp/server.py`) accede a `r.required` en un `VerificationHookResult` que no tiene ese atributo. Rompe `cortex_documenter_briefing` cuando la spec tiene hooks. Confirmado en log línea 170-194.
- `cortex_session_checkpoint` rechaza `source="cortex-code-designer"` (que SÍ existe en `CheckpointSource` enum en `cortex/session/models.py:106`). **Schema drift**: hay dos listas hardcoded en `cortex/mcp/server.py:835-840` y `:1893-1900` que olvidaron incluir `cortex-code-designer`.
- `DuplicateDocumentError` (`cortex/documentation/errors.py:22`) no hereda de `ValueError`, por lo que `_create_spec_text` en `cortex/mcp/server.py:1789` no la atrapa explícitamente y cae al `except Exception` genérico → marca el server como `degraded` en `cortex_ping` aunque sea un caso esperado.
- Validaciones inconsistentes entre tool descriptions y schemas Pydantic en `cortex_emit_proposal` y `write_design_note_canonical` — fuente de fricción que consume turnos del agente.

### Capa 5 — Error humano honesto del usuario amplificó la cascada
El usuario continuó en SDDwork (en vez de volver a sync) para la Fase 1 dentro de la sesión de arquitectura. El skill de SDDwork debería haberlo detenido al detectar scope mismatch; en su lugar entró en Capa 3.

---

## Plan de cambios — todos sobre `cortex/` (core, no Pi)

> Los fixes van en el árbol estructural de Cortex para que se propaguen a **todos los IDEs** (Claude Code, opencode, Pi, etc.) en cualquier instalación futura. El cliente Pi no se toca — el problema es del server y del comportamiento canónico del flujo, ambos owned por `cortex/`.

### Bloque inmediato (destranca el piloto)

| # | Fix | Archivo:línea | Esfuerzo |
|---|---|---|---|
| 1 | **Idempotencia de `cortex_create_spec` por fingerprint**: si el archivo existe Y el body fingerprint coincide → éxito silencioso (retorna el path existente). Si existe pero el contenido difiere → error accionable sugiriendo nuevo slug o `overwrite=true`. | `cortex/documentation/writers.py:359-382` (`_write_note`) + `cortex/services/spec_service.py:204` (pasar fingerprint) | Medio |
| 2 | **Atrapar `DuplicateDocumentError` explícito** en `_create_spec_text` y devolver mensaje limpio sin marcar server como degraded | `cortex/mcp/server.py:1789` | Bajo |
| 3 | **Fix `_serialize_reconstruction`**: derivar `required` desde el hook original (no desde `VerificationHookResult`) o agregar el campo al result | `cortex/mcp/server.py:76` | Bajo |
| 4 | **Limpieza del vault AppFutbol**: borrar las 5 sesiones huérfanas + spec fantasma + embeddings stale | `C:/AppFutbol/.cortex/` (manual, no commit) | Cero |

### Bloque secundario (refuerza Deep Track)

| # | Fix | Archivo:línea | Esfuerzo |
|---|---|---|---|
| 5 | **Excluir artifacts del proceso del scope check**: `vault/designs/`, `vault/sessions/`, `vault/handoffs/`, `vault/specs/` no deberían contar como "out of spec scope" en `quality_gates` | `cortex/session/quality_gates.py:128-134` | Bajo |
| 6 | **Sincronizar enum de `source` checkpoint**: las dos listas hardcoded en `cortex/mcp/server.py:835-840` y `:1893-1900` deben derivarse del enum `CheckpointSource` (DRY). Mientras tanto, agregar `cortex-code-designer` a ambas. | `cortex/mcp/server.py:835-840, 1893-1900` | Bajo |
| 7 | **Regla nueva en skill SDDwork**: "si `cortex_review_checkpoint` rechaza por scope mismatch (ej. el design doc cae fuera del scope), **NO intentes crear una nueva spec; devolvele al usuario al `cortex-sync`**". Va en el skill canónico para que todos los IDEs lo hereden. | `.cortex/skills/cortex-SDDwork.md` (canónico fuente) + replicar a `cortex-pi/.pi/agents/cortex-SDDwork.md` vía sync | Bajo |

### Bloque opcional (mejora latencia y consistencia)

| # | Fix | Archivo:línea | Esfuerzo |
|---|---|---|---|
| 8 | **`sync_vault=False` por default en `cortex_create_spec`** o sync incremental del solo archivo nuevo (no full re-index) | `cortex/services/spec_service.py:211-212` + `cortex/mcp/server.py:1785` | Medio |
| 9 | **Alinear schemas de tool description vs Pydantic validators** (`cortex_emit_proposal` rejected_reason, `verification_hooks` `description` field, etc.) | varios en `cortex/mcp/server.py` | Medio |
| 10 | **Investigar si el cliente del SDK MCP de Pi tiene timeout configurable**; si sí, alinearlo con los timeouts del server | no es código de cortex/ — investigación externa | Alto |

---

## Log de cambios aplicados

| Fecha | Fix # | Archivo:línea | Quién | Estado |
|---|---|---|---|---|
| 2026-05-22 | — | `pyproject.toml:32` | claude | ✅ agregó `jinja2>=3.0` (incidente previo, jinja2 missing) |
| 2026-05-22 | 3 | `cortex/mcp/server.py:29-83` (`_serialize_reconstruction`) | claude | ✅ deriva `required` desde `out.spec.verification_hooks` por nombre; default `True` ante miss. Desbloquea `cortex_documenter_briefing` cuando la spec tiene hooks. |
| 2026-05-22 | 1a | `cortex/documentation/writers.py:32-36, 359-389` (`_write_note`) | claude | ✅ idempotencia por fingerprint: si el archivo on-disk tiene el mismo SHA-256, return silencioso. Si difiere → `DuplicateDocumentError` con mensaje accionable. |
| 2026-05-22 | 1b | `cortex/session/service.py:117-156` (`SessionService.open`) | claude | ✅ idempotencia complementaria: si ya existe sesión OPEN con el mismo `spec_id`, retorna la existente sin crear `-2`. Solo CLOSED/HANDOFF/ABANDONED genera nuevo sufijo. |
| 2026-05-22 | 2 | `cortex/mcp/server.py:1781-1808` (`_create_spec_text`) | claude | ✅ atrapa `DuplicateDocumentError` explícito; devuelve mensaje accionable sin marcar server como degraded. |
| 2026-05-22 | 4 | `C:/AppFutbol/.cortex/` | claude | ✅ borradas 5 sesiones huérfanas + 2 specs fantasma; `active.txt` reseteado. Quedan solo `arquitectura-...md` + su sesión closed. |
| 2026-05-22 | 14 | `cortex/mcp/server.py:_TOOL_TIMEOUTS` | claude | ✅ `cortex_documenter_briefing` timeout subido a 180s. Acomoda hooks lentos (`npm ci && npm run build`) que excedían los 30s default. |
| 2026-05-22 | 15 | `cortex/documentation/routing.py:78` | claude | ✅ Filename template de SESSION cambiado de `{date}_{session_id}_{slug}.md` a `{session_id}_{slug}.md`. El `session_id` ya empieza con la fecha; se eliminó la duplicación. |
| 2026-05-22 | 16 | `cortex/mcp/server.py:_write_doc_text` | claude | ✅ Validación fail-fast de required fields per `doc_type` antes de armar el dataclass. Mensajes accionables, evita propagación de `SchemaValidationError` desde writers. |
| 2026-05-22 | 11+12 | `cortex/session/storage.py` | claude | ✅ Retry exponencial sobre `os.replace` ante WinError 5/32 + EACCES/EBUSY. Lock por final-path serializa concurrent writers desde el ThreadPoolExecutor. Mitiga sharing violations en Windows (AV/indexer + double-dispatch del cliente). |
| 2026-05-22 | 5 | `cortex/session/quality_gates.py:_stage_1_spec_compliance` | claude | ✅ Excluidos artifacts canónicos (`vault/designs/`, `vault/sessions/`, `vault/handoffs/`, `vault/specs/`, `vault/decisions/`, etc.) del scope check. Deep Track ahora puede emitir design docs sin que `cortex_review_checkpoint` los rechace como scope creep. |
| 2026-05-22 | 6 | `cortex/mcp/server.py:_CHECKPOINT_SOURCE_VALUES` | claude | ✅ Enum `source` de `cortex_session_checkpoint` derivado de `CheckpointSource` (single source of truth). Incluye `cortex-code-designer`, antes faltante. |
| 2026-05-22 | 7 | **`cortex/setup/cortex_workspace.py`** (fuente canónica) + `.cortex/skills/cortex-SDDwork.md` + `cortex-pi/.pi/agents/cortex-SDDwork.md` (copias derivadas) | claude | ✅ Sección nueva "Manejo de rechazos del cortex_review_checkpoint" en el string template del skill SDDwork. Regla explícita: si rechazo por scope, NO crear spec; devolver al usuario a `cortex-sync`. Propaga a workspaces nuevos automáticamente en `cortex setup agent`. |
| 2026-05-22 | 17 | `cortex/mcp/server.py` (schema + `_normalize_string_list`) | claude | ✅ `cortex_sync_ticket` ahora acepta `keywords` / `changed_files` como array O string CSV. Schema usa `oneOf`; el handler splitea por coma. Reduce fricción cuando el LLM serializa lista como CSV. |
| 2026-05-22 | 18 | `cortex/session/proposal.py:Alternative` | claude | ✅ Límite de `description` y `rejected_reason` subido de 500 → 1500 chars. Permite alternativas detalladas con riesgos/tradeoffs sin truncar. |
| 2026-05-22 | 19 | `cortex/mcp/server.py:_ping_text + _ERROR_RECENT_WINDOW_SECONDS` | claude | ✅ TTL para `last_error_seen`: solo errores en los últimos 300s mueven `status` a `degraded`. Pasada la ventana, server auto-recupera a `ok`. Agrega `recent_errors_count` y `error_window_seconds` al payload. Mata el bug del "degraded sticky permanente" que paralizó el documenter de Fase 3. Smoke-tested 3 escenarios (stale/recent/mixed). |
| 2026-05-22 | 14b | `cortex/documenter/reconstruction.py:ReconstructionInput` + `cortex/mcp/server.py:_documenter_briefing_text` | claude | ✅ `cortex_documenter_briefing` ahora skipea verification_hooks por default (`run_hooks=False`). El briefing es read-only contextual; SDDwork ya corrió los hooks antes de cerrar. Si el documenter quiere re-ejecutarlos, pasa `run_hooks=true` explícito. Elimina la causa real del timeout del briefing (npm ci + build > 180s). |
| 2026-05-22 | 20 | **`cortex/setup/cortex_workspace.py`** (fuente canónica) + `.cortex/skills/cortex-documenter.md` + `cortex-pi/.pi/agents/cortex-documenter.md` (copias derivadas) | claude | ✅ Pre-flight check del documenter en el string template del skill: `status=degraded` ya NO bloquea. Sólo `status=error` o desconocido aborta. `degraded` se reporta como warning al usuario y el flujo sigue. Complementa #19. Propaga a workspaces nuevos automáticamente. |

### Validación end-to-end (piloto Fase 2)

Durante la prueba de creación de spec para Fase 2 confirmamos:

- **Fix #1 (idempotencia por fingerprint) disparó en producción**: `cortex_create_spec` timeouteó del lado Pi, el retry vio fingerprint match y devolvió `Specification saved` silenciosamente. Antes habría sido `Document already exists` + loop.
- **Fix #1b (session.open idempotente)**: cero sesiones huérfanas. La sesión `fase-2-entidades-tacticas-y-tool-system` quedó única.
- **Fix #3 (briefing sin AttributeError)**: confirmado activo (no se invocó briefing en este turno pero el código está sano).
- **Fixes #17 y #18 detectados durante este mismo piloto**: el agente tropezó con ambos schemas y los reintentos consumieron turnos. Fixes aplicados arriba.

### Deuda residual / hallazgos abiertos

- **Embeddings stale en `chroma.sqlite3`**: el vector store conserva embeddings de specs eliminadas. Próximo `cortex_sync_ticket` puede devolverlos como hits aunque el archivo no exista. Mitigación: correr `cortex sync-vault` desde CLI cuando se retome el piloto. No bloqueante.

- **Fix #1a — fingerprint match raramente dispara en la práctica** (investigación cerrada): los templates Jinja2 son 100% determinísticos (sin timestamps en body) — el código está OK. Sin embargo, los retries observados en producción (cliente Pi + agente LLM) **no preservan byte-equality del payload** entre intentos. Evidencia en log MCP del piloto: dos retries del mismo `cortex_create_spec` con verification_hooks formateados distinto (uno con `success_criteria`, otro sin). El fix #1a sigue siendo defensa en profundidad — dispara cuando el SDK del cliente retransmite el payload original byte-a-byte — pero no cubre el caso "retry semánticamente igual, sintácticamente distinto". El fix #2 (mensaje accionable) cubre ese caso restante.

_Esta tabla se actualiza a medida que se aplican los fixes del plan._

---

## Referencias

- Transcript completo del piloto: [`../conversacion.md`](../conversacion.md)
- Log MCP del incidente: `C:/AppFutbol/.cortex/logs/mcp_calls_20260522_102306.log`
- Estado del vault tras el incidente: `C:/AppFutbol/.cortex/vault/specs/`, `.../sessions/`
- Incidente previo (jinja2 missing): mismo día, resuelto agregando dep al manifest
