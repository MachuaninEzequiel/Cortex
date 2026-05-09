# Cortex Autopilot — Evaluaciones End-to-End

**Fecha:** 2026-05-09  
**Fase:** 11 — Tests End-to-End y Evals  
**Estado:** Completado

---

## 1. Resumen ejecutivo

Esta fase mide el comportamiento real de Autopilot mediante escenarios determinísticos que ejecutan la capa CLI → Servicio → StateStore sin agentes externos, red ni consumo de tokens. Los tests se ejecutan con ``CliRunner`` (Typer) sobre workspaces temporales aislados.

**Hallazgo principal:** ``finish --auto`` registra ``session_note_path`` en el estado pero **no escribe el archivo físico** en vault. Este comportamiento es consistente con la implementación actual y se documenta explícitamente como limitación conocida.

---

## 2. Escenarios ejecutados

### 2.1 Pregunta simple (`question-only`)

| Métrica | Esperado | Actual |
|---|---|---|
| Task type | `question-only` | ✅ `question-only` |
| Spec creada | No | ✅ No se crea |
| Embeddings | No | ✅ No se disparan |
| Chars inyectados | 0 | ✅ 0 (sin `build_context`) |
| Items retrieved | 0 | ✅ 0 |
| Session note al `finish --auto` | Documented con draft minimal | ✅ Documented |

**Observación:** Aunque el perfil `question_only` tiene presupuesto cero, `finish --auto` igual genera un draft minimal y marca `documented`. Esto es aceptable porque el draft no inventa información y no implica costo de retrieval.

### 2.2 Cambio simple (`fast-code`)

| Métrica | Esperado | Actual |
|---|---|---|
| Task type | `fast-code` | ✅ `fast-code` |
| Complejidad | `fast` | ✅ `fast` |
| Session note path | Asignado en estado | ✅ Asignado |
| Archivo físico escrito | **No esperado** (limitación) | ✅ **No existe** |
| Draft confidence | `medium` / `auto-draft` | ✅ `medium` |

**Observación crítica:** `session_note_path` apunta a `vault/sessions/<id>-auto-draft.md`, pero el archivo no existe en disco. El servicio no invoca `save_session_note()` de `AgentMemory`. Si el usuario necesita persistencia real, debe hacerse vía MCP `cortex_save_session` o extender `finish()` en una fase posterior.

### 2.3 Docs-only (`docs-only`)

| Métrica | Esperado | Actual |
|---|---|---|
| Task type | `docs-only` | ✅ `docs-only` |
| Budget profile | `docs_only` | ✅ `docs_only` |
| Chars límite | ≤ 1200 | ✅ Perfil respeta 1200 |
| Subagentes | 0 | ✅ 0 |

### 2.4 Tarea compleja (`deep-code`)

| Métrica | Esperado | Actual |
|---|---|---|
| Task type | `deep-code` | ✅ `deep-code` (≥ 6 archivos o refactor) |
| Complejidad | `deep` | ✅ `deep` |
| Deep track reason | Persistido | ✅ Persistido en `budget.deep_track_reason` |
| Delegación | Review disponible (stub) | ✅ Two-stage review ejecuta vía MCP |
| Subagentes permitidos | Sí | ✅ Perfil `deep_code` permite `subagents=True` |

**Observación:** El registro de delegación (`_task_registry`) es en memoria de proceso. Los tests verifican que no hay persistencia cross-process.

### 2.5 Finish sin datos

| Métrica | Esperado | Actual |
|---|---|---|
| Draft confidence | `auto-draft` | ✅ `auto-draft` |
| Inventa archivos/tests | No | ✅ No inventa |
| Estado | `documented` | ✅ `documented` (policies no bloquean) |

### 2.6 Falla de herramienta / bloqueo de policy

| Métrica | Esperado | Actual |
|---|---|---|
| Degradación con warning | Sí | ✅ `warnings` en estado |
| No marca `documented` | Sí | ✅ Estado `finished` |
| Draft generado | Sí (conservador) | ✅ Draft `auto-draft` generado |

**Observación:** El proxy usado es `AutoCheckpointPolicy` en modo `autopilot` con >5 archivos cambiados sin checkpoint. Esto bloquea `finish` y emite warning, replicando el comportamiento esperado ante una falla de gobernanza.

### 2.7 Uninstall / cleanup / config

| Métrica | Esperado | Actual |
|---|---|---|
| `cleanup --older-than 30` archiva JSONL viejos | Sí | ✅ Archiva a `events_archive/` |
| `cleanup --older-than 30d` rechazado | Sí | ✅ Typer rechaza valor no entero |
| Config queda limpia | Sí | ✅ Solo archivos Autopilot en `run/autopilot` |

---

## 3. Métricas agregadas

| Métrica | Valor observado | Nota |
|---|---|---|
| Tests E2E ejecutados | 22 | 3 archivos de escenario |
| Tests unitarios (regresión) | 272 passed | Sin regresiones |
| Tiempo total E2E | ~7 s | Determinístico, sin red |
| Tokens consumidos | 0 | No se invocan LLMs |
| Embeddings ejecutados | 0 | Mocks / fallback vacío |
| Archivos temporales creados | 0 (salvo `.cortex/run`) | Fixtures aislados |

---

## 4. Riesgos residuales

1. **Session note no persiste físicamente** — `finish --auto` es un draft en memoria/estado. El usuario no obtiene un `.md` en vault sin llamar explícitamente a `cortex_save_session`.
2. **Delegación en memoria** — `_task_registry` se pierde entre procesos. Si el harness reinicia, los resultados de subagentes desaparecen.
3. **Doctor read-only con excepción de `_check_run_dir`** — Corregido en esta fase: ahora usa `os.access(..., W_OK)` en lugar de crear/borrar `.write_test`.
4. **Cleanup CLI inconsistente con docs** — La acción recomendada del doctor sugería `--older-than 30d` pero la CLI espera un entero. Corregido a `--older-than 30`.
5. **Auto-draft sin checkpoints** — `finish --auto` sin datos observados genera `auto-draft` con warnings, pero el usuario podría no notar la falta de calidad si solo lee el status `documented`.

---

## 5. Próximos pasos recomendados

- Fase 12 (packaging) puede asumir estos tests como baseline de regresión.
- Si se implementa persistencia física de session notes en `finish()`, se debe actualizar el test `test_fast_track_draft_on_finish` para verificar la existencia del archivo.
- Agregar test E2E de `review_delegation` vía MCP cuando el runtime de subagentes esté listo.
