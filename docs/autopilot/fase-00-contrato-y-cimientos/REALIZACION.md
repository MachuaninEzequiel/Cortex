# Fase 0 — Contrato y Cimientos: Realización

**Fecha:** 2026-05-09  
**Estado:** Completada  
**Responsable:** Agente implementador (pi)

---

## 1. Qué se implementó

Esta fase es puramente documental y contractual. No se creó ni modificó código de runtime.

Se entregaron dos documentos de contrato estables:

1. **`docs/autopilot/contracts.md`** — Consolidación de todos los contratos del sistema:
   - `AutopilotSessionState` y `AutopilotBudgetSnapshot`.
   - `AutopilotEvent` y reglas de persistencia JSONL.
   - `DetectionRequest` / `DetectionResult` y algoritmo de resolución del registry.
   - `PolicyDecision` y semántica de acciones.
   - `SessionDraft` y reglas de seguridad epistémica.
   - Profiles de presupuesto (`question_only`, `docs_only`, `fast_code`, `deep_code`, `finish_only`).
   - Contrato de Hook Adapters (`AutopilotHookAdapter`), output de `session-start`, formato por plataforma y wrapper cross-platform.
   - Matriz de compatibilidad IDE (10 harnesses actuales vs adapters Autopilot futuros).
   - Contrato de Delegación con Two-Stage Review.
   - Extension points (registry de detectors, policies, renderers, adapters, budget profiles).
   - Reafirmación de los 12 no-objetivos.
   - Decisiones de contrato tomadas en esta fase (layout de persistencia, modo por defecto `assist`, capas finas CLI/MCP/Hook, versionado de estado, presupuesto agresivo por defecto).
   - Validación cruzada contra `WorkspaceLayout`, `cortex/cli/main.py`, `cortex/mcp/server.py`, `cortex/setup/cortex_workspace.py` y `cortex/ide/adapters/*`.

2. **`docs/autopilot/testing-strategy.md`** — Estrategia de testing completa:
   - Pirámide de tests (unitario → integración → E2E/evals).
   - Estructura de directorios propuesta.
   - Reglas por tipo de test (sin I/O real, sin Chroma/ONNX, sin Typer real en unitarios).
   - Patrones de mock para `AgentMemory` y `StateStore`.
   - Fixtures compartidos propuestos (`tmp_workspace`, `state_store`, `sample_state`).
   - Gates de salida por fase (tabla completa).
   - Cobertura mínima esperada por módulo.
   - Reglas de regresión del CLI histórico.

---

## 2. Archivos creados / modificados

| Archivo | Acción | Notas |
|---------|--------|-------|
| `docs/autopilot/contracts.md` | Creado | 15 758 bytes. Contratos estables para fases 1+. |
| `docs/autopilot/testing-strategy.md` | Creado | 7 302 bytes. Estrategia de testing para todo el módulo. |
| `docs/autopilot/fase-00-contrato-y-cimientos/REALIZACION.md` | Creado | Este archivo. |

**No se modificó código de runtime.**

---

## 3. Decisiones tomadas

### 3.1 Layout de persistencia Autopilot
- **Decisión:** Estado en `{workspace_root}/run/autopilot/sessions/{id}.json`, eventos en `{workspace_root}/run/autopilot/events/{id}.jsonl`.
- **Justificación:** `run/` ya es un directorio de runtime conceptual en el layout nuevo. En legacy, `workspace_root == project_root`, por lo que queda en `.cortex/run/autopilot` solo si se agrega helper; de lo contrario se usará `resolve_workspace_relative("run/autopilot")`. Esta observación se documentó como riesgo residual menor.

### 3.2 Modo por defecto
- **Decisión:** `assist` es el modo por defecto.
- **Justificación:** Minimiza riesgo de adopción; el usuario puede promocionar a `autopilot` explícitamente.

### 3.3 Presupuesto agresivo
- **Decisión:** `fast_code` es el default para tareas con cambios no ambiguos; `deep_code` requiere umbral claro.
- **Justificación:** Evita el problema observado en Superpowers (workflows potentes pero costosos por defecto).

### 3.4 CLI vs MCP vs Hook
- **Decisión:** Tres capas finas que delegan a `AutopilotService`; ninguna contiene lógica de negocio.
- **Justificación:** Garantiza comportamiento idéntico sin importar el punto de entrada.

### 3.5 Matriz de compatibilidad IDE
- **Decisión:** Documentar 10 harnesses actuales y marcar adapters Autopilot como futuros (fase 7).
- **Justificación:** Permite planificar el adapter piloto sin comprometer los adapters actuales.

---

## 4. Tests ejecutados y resultado

### 4.1 Regresión CLI histórico
```bash
pytest tests/unit/cli/test_main.py -q
```
- **Resultado:** 16 passed, 0 failed.
- **Cobertura del CLI:** 32% (esperado; los tests unitarios existentes cubren importación y estructura, no todos los branches interactivos).

### 4.2 Validación de documentos
- `contracts.md` y `testing-strategy.md` fueron revisados manualmente contra el plan global (`docs/autopilot/README.md`).
- No se detectaron contradicciones con:
  - `WorkspaceLayout` (new/legacy resolution).
  - `cortex/cli/main.py` (puede agregarse `app.add_typer` sin romper).
  - `cortex/mcp/server.py` (no se toca en esta fase; se validó que la arquitectura permite agregar tools en fase 5).
  - `cortex/setup/cortex_workspace.py` (meta-skill futura no colisiona con skills actuales).
  - `cortex/ide/adapters/*` (adapters actuales no conocen Autopilot; convivencia segura).

---

## 5. Desviaciones respecto del plan

Ninguna. El plan de la Fase 0 indicaba crear `docs/autopilot/contracts.md` y `docs/autopilot/testing-strategy.md`, y revisar archivos existentes. Todo se cumplió sin desviaciones.

---

## 6. Riesgos residuales

| Riesgo | Nivel | Mitigación planificada |
|--------|-------|------------------------|
| `WorkspaceLayout` no tiene propiedad `autopilot_run_dir` | Bajo | Usar `resolve_workspace_relative("run/autopilot")` en Fase 1; si se vuelve verboso, agregar helper opcional. |
| Layout legacy podría generar `run/autopilot` en repo root | Bajo | Aceptable; `workspace_root` en legacy es `repo_root`. Si es visualmente intrusivo, se evalúa migración a new layout. |
| Falta de helpers de test compartidos (`conftest.py`) | Bajo | Se documentó en `testing-strategy.md`; se implementará en Fase 1. |
| Adapter piloto no definido todavía | Medio | Se recomienda Claude Code o Cursor según matriz; decisión diferida a Fase 7. |

---

## 7. Próximos pasos

1. **Fase 1 — Skeleton del Módulo:**
   - Crear `cortex/autopilot/__init__.py`, `models.py`, `config.py`, `state_store.py`, `registry.py`, `errors.py`.
   - Implementar `StateStore` con JSON/JSONL y `WorkspaceLayout`.
   - Tests unitarios: `test_models.py`, `test_state_store.py`.
   - Gate: `pytest tests/unit/autopilot` pasa; el módulo importa sin inicializar Chroma ni ONNX.

2. **Preparar `conftest.py`** en `tests/unit/autopilot/` con fixtures `tmp_workspace`, `state_store`, `sample_state`.

3. **Evaluar** si `WorkspaceLayout` necesita `autopilot_run_dir` como property; si no, documentar el patrón estándar en Fase 1.

---

*Fin de la realización de la Fase 0.*
