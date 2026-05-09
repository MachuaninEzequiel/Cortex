# Fase 4 — Session Builder y Persistencia Automática: Realización

**Fecha:** 2026-05-09  
**Estado:** Completada  
**Responsable:** Agente implementador (pi)

---

## 1. Qué se implementó

Se construyó el sistema de renderizado de session notes basado en estado observado, con self-review automático y reemplazo del placeholder `_minimal_render()` por `SessionBuilder`.

### Archivos de runtime creados

| Archivo | Responsabilidad |
|---------|-----------------|
| `cortex/autopilot/renderers/base.py` | Protocolo `SessionRenderer`. |
| `cortex/autopilot/renderers/minimal.py` | `MinimalSessionRenderer` — título, resumen, archivos, checkpoints. Para tareas simples. |
| `cortex/autopilot/renderers/implementation.py` | `ImplementationSessionRenderer` — cambios, decisiones, archivos, spec ref, budget snapshot. Para fast-code y deep-code. |
| `cortex/autopilot/renderers/docs_only.py` | `DocsOnlySessionRenderer` — documentos creados/modificados. Para docs-only. |
| `cortex/autopilot/renderers/fallback_draft.py` | `FallbackDraftRenderer` — draft seguro con `auto-draft` cuando faltan datos. |
| `cortex/autopilot/session_builder.py` | `SessionBuilder` — selecciona renderer según `task_type`, ejecuta `self_review()`, devuelve `SessionDraft`. Incluye `self_review()` con placeholder scan, file consistency y evidence check. |

### Archivos de runtime modificados

| Archivo | Cambio |
|---------|--------|
| `cortex/autopilot/service.py` | Eliminado `_minimal_render()`. `AutopilotService.__init__` ahora acepta `session_builder`. `finish()` usa `self._builder.build(state)`. `finish()` ya no duplica session notes si `session_note_path` ya existe. |

### Archivos de test creados

| Archivo | Tests |
|---------|-------|
| `tests/unit/autopilot/test_renderers.py` | 10 tests — todos los renderers: minimal, implementation, docs_only, fallback. Cobertura de checkpoints verificados/no-verificados, archivos faltantes, auto-draft. |
| `tests/unit/autopilot/test_session_builder.py` | 18 tests — `SessionBuilder` selección de renderer, `self_review()` placeholder/file/evidence, scan helpers, build end-to-end. |

---

## 2. Archivos creados / modificados

| Archivo | Acción |
|---------|--------|
| `cortex/autopilot/renderers/base.py` | Creado |
| `cortex/autopilot/renderers/minimal.py` | Creado |
| `cortex/autopilot/renderers/implementation.py` | Creado |
| `cortex/autopilot/renderers/docs_only.py` | Creado |
| `cortex/autopilot/renderers/fallback_draft.py` | Creado |
| `cortex/autopilot/session_builder.py` | Creado |
| `cortex/autopilot/service.py` | Modificado |
| `tests/unit/autopilot/test_renderers.py` | Creado |
| `tests/unit/autopilot/test_session_builder.py` | Creado |

---

## 3. Decisiones tomadas

### 3.1 Reglas de seguridad epistémica aplicadas
- **No invención:** Todos los renderers usan solo datos de `AutopilotSessionState`. No generan afirmaciones no observadas.
- **Especificidad de budget:** `ImplementationSessionRenderer` incluye el snapshot del budget (chars, items, embeddings, subagents).
- **Ausencia de spec:** Si no hay `spec_path`, se escribe "_No spec associated._" (exactamente como indica el contrato §7.3).
- **Ausencia de tests:** Si no hay checkpoints verificados, se agrega warning; no se afirma que los tests pasaron.

### 3.2 Self-review implementado (§7.3.1)
El `self_review()` ejecuta tres verificaciones:
1. **Placeholder scan:** Busca `TBD`, `TODO`, `FIXME`, `[pendiente]`, `XXX`, `???`, `fill me` en el body. Si encuentra, downgrada a `auto-draft`.
2. **File consistency:** Verifica que cada archivo en `state.changed_files` aparezca en el body. Si falta alguno, emite warning.
3. **Evidence check:** Si el body contiene claims de éxito (`"tests pass"`, `"build exitoso"`, `"linter clean"`, `"verificado"`, etc.) pero no hay checkpoints verificados, emite warning y downgrada a `auto-draft`.

**Nota sobre events:** El plan menciona verificar `event_type == "verification"` en los eventos, pero `AutopilotSessionState` no almacena eventos directamente. Se aproxima usando `checkpoint.verified` como proxy de evidencia de verificación. Esto es documentado como limitación conocida.

### 3.3 Selección de renderer por task type
```python
_DEFAULT_RENDERER_MAP = {
    "question-only": "minimal",
    "docs-only": "docs_only",
    "fast-code": "implementation",
    "deep-code": "implementation",
    "security": "implementation",
    "ambiguous": "fallback_draft",
    "noop": "fallback_draft",
}
```

### 3.4 Anti-duplicación en `finish()`
Si `state.session_note_path` ya existe, `finish()` retorna inmediatamente con `saved=False` y `reason="Session note already exists"`. Esto evita duplicar session notes si el usuario llama `finish` dos veces.

### 3.5 Inyección de `SessionBuilder`
`AutopilotService` acepta `session_builder` como parámetro opcible. Esto permite reemplazar renderers en tests sin modificar el código de producción.

---

## 4. Tests ejecutados y resultado

### 4.1 Tests unitarios de Autopilot (todos)
```bash
pytest tests/unit/autopilot/ tests/unit/cli/test_main.py -v -k "not e2e"
```
- **Resultado:** 149 passed, 0 failed.
- **Cobertura de módulos nuevos:**
  - `session_builder.py`: 100%
  - `renderers/minimal.py`: 89%
  - `renderers/implementation.py`: 96%
  - `renderers/docs_only.py`: 82%
  - `renderers/fallback_draft.py`: 96%
  - `renderers/base.py`: 100% (protocolo, no ejecutable)
  - `service.py`: 92%

### 4.2 Regresión CLI histórico
```bash
pytest tests/unit/cli/test_main.py -q
```
- **Resultado:** 16 passed, 0 failed.

---

## 5. Incidencia durante ejecución de tests

### 5.1 Síntoma
Al ejecutar `test_renderers.py` y `test_session_builder.py`, dos tests fallaron:

1. `TestDocsOnlySessionRenderer::test_no_docs` — esperaba `confidence="auto-draft"`, pero obtuvo `"medium"`.
2. `TestSelfReview::test_no_issues_keeps_confidence` — esperaba `confidence="high"`, pero obtuvo `"auto-draft"`.

### 5.2 Causa raíz

**Problema A — `DocsOnlySessionRenderer` no detectaba archivos no-docs:**
El renderer solo bajaba a `auto-draft` cuando `not doc_files and not state.changed_files`. Si había archivos no-docs (ej. `main.py`) pero ningún archivo de documentación, no emitía warning.

**Problema B — `self_review` verificaba consistencia de archivos en un body sin archivos:**
El test usaba `body="All good"` con `changed_files=["a.py"]`. El check `_check_file_consistency` verificaba que cada archivo en `changed_files` aparezca en el body. Como `"a.py"` no estaba en `"All good"`, generaba un warning y downgradaba a `auto-draft`. Este comportamiento es correcto por el contrato, pero el test era irrealista.

### 5.3 Solución aplicada

**Para A:** Se modificó la guarda en `DocsOnlySessionRenderer`:
```python
if not doc_files:
    confidence = "auto-draft"
    if state.changed_files:
        warnings.append("No documentation files observed (only non-doc files)")
    else:
        warnings.append("No documentation files observed")
```

**Para B:** Se actualizó el test para usar un body que contenga el archivo:
```python
draft = SessionDraft(title="X", body="All good with a.py", confidence="high", source_events=1)
```

### 5.4 Verificación final
Tras los ajustes, todos los tests pasaron: **28 passed, 0 failed** para los nuevos tests; **149 passed, 0 failed** para toda la suite.

---

## 6. Desviaciones respecto del plan

Ninguna desviación arquitectónica. Un ajuste menor de implementación:
- `DocsOnlySessionRenderer` se refinó para emitir warning cuando hay archivos no-docs pero no docs, en lugar de silenciosamente retornar `confidence="medium"`.

---

## 7. Riesgos residuales

| Riesgo | Nivel | Mitigación |
|--------|-------|------------|
| `self_review` usa `checkpoint.verified` como proxy de eventos de verificación | Bajo | El contrato menciona `event_type == "verification"` pero `state` no almacena eventos. En Fase 5+ se puede pasar eventos al `SessionBuilder` si es necesario. Por ahora, `checkpoint.verified` es suficiente para el MVP. |
| Los renderers no escriben archivos directamente | — | Intencional. El plan dice "renderers producen texto, no escriben archivos". La persistencia queda para Fase 5 (MCP) o comando explícito del usuario. |
| `service.py` `finish()` solo genera el path de la session note, no la escribe | Bajo | El plan dice "no full sync-vault como cierre default". La session note se genera como `SessionDraft`; la persistencia real en el vault se hará vía `AgentMemory.save_session_note()` cuando el MCP o CLI lo invoquen. |

---

## 8. Próximos pasos

1. **Fase 5 — MCP Tools Autopilot:**
   - Crear `cortex/autopilot/mcp_tools.py` con handlers para `cortex_autopilot_start`, `preflight`, `checkpoint`, `finish`, `status`.
   - Modificar `cortex/mcp/server.py` para registrar las tools MCP.
   - Tests: `test_mcp_tools.py`.

---

*Fin de la realización de la Fase 4.*
