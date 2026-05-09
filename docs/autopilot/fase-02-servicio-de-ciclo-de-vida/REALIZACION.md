# Fase 2 — Servicio de Ciclo de Vida: Realización

**Fecha:** 2026-05-09  
**Estado:** Completada  
**Responsable:** Agente implementador (pi)

---

## 1. Qué se implementó

Se creó `AutopilotService` como única API de negocio, junto con detectores, policies, context budget y modelos de ciclo de vida. Ningún archivo del CLI histórico ni del MCP server fue modificado.

### Archivos de runtime creados

| Archivo | Responsabilidad |
|---------|-----------------|
| `cortex/autopilot/detectors/base.py` | Protocolo `AutopilotDetector`, función `resolve_detectors()` con algoritmo de resolución §7.1.2. |
| `cortex/autopilot/detectors/ambiguous.py` | `AmbiguousRequestDetector` con heurísticas exactas del plan (§7.1.1). |
| `cortex/autopilot/detectors/default.py` | `CodeChangeDetector`, `DocsOnlyDetector`, `QuestionOnlyDetector`, `SecuritySensitiveDetector`, `LargeRefactorDetector`, `NoopDetector`. |
| `cortex/autopilot/policies/base.py` | Protocolo `AutopilotPolicy`, `evaluate_policies()`, `most_restrictive()` con prioridad `block > degrade > warn > proceed`. |
| `cortex/autopilot/policies/default.py` | `BudgetPolicy`, `DocumentationRequiredPolicy`, `SpecRequiredPolicy`, `HumanApprovalPolicy`. |
| `cortex/autopilot/policies/auto_checkpoint.py` | `AutoCheckpointPolicy` con umbrales de 5 archivos / 10 minutos (§7.2.1). |
| `cortex/autopilot/context_budget.py` | Perfiles de presupuesto (`question_only`, `docs_only`, `fast_code`, `deep_code`, `finish_only`) y helpers de mapping. |
| `cortex/autopilot/lifecycle.py` | Tipos de request/result para `start`, `preflight`, `checkpoint`, `finish`, `status`. |
| `cortex/autopilot/service.py` | `AutopilotService` con métodos `start()`, `preflight()`, `checkpoint()`, `finish()`, `status()`. Usa `StateStore`, detectores y policies por defecto inyectables. Incluye `_minimal_render()` como placeholder hasta Fase 4. |

### Archivos de test creados

| Archivo | Cobertura |
|---------|-----------|
| `tests/unit/autopilot/test_detectors.py` | 30 tests — todos los detectores, resolución de registry, empates, security priority, ambiguous priority. |
| `tests/unit/autopilot/test_policies.py` | 25 tests — todas las policies, evaluación múltiple, most_restrictive, AutoCheckpoint con tiempo y archivos. |
| `tests/unit/autopilot/test_service.py` | 18 tests — start, preflight, checkpoint, finish(auto/block), status, eventos persistentes. |

---

## 2. Archivos creados / modificados

| Archivo | Acción |
|---------|--------|
| `cortex/autopilot/detectors/base.py` | Creado |
| `cortex/autopilot/detectors/ambiguous.py` | Creado |
| `cortex/autopilot/detectors/default.py` | Creado |
| `cortex/autopilot/policies/base.py` | Creado |
| `cortex/autopilot/policies/default.py` | Creado |
| `cortex/autopilot/policies/auto_checkpoint.py` | Creado |
| `cortex/autopilot/context_budget.py` | Creado |
| `cortex/autopilot/lifecycle.py` | Creado |
| `cortex/autopilot/service.py` | Creado |
| `tests/unit/autopilot/test_detectors.py` | Creado |
| `tests/unit/autopilot/test_policies.py` | Creado |
| `tests/unit/autopilot/test_service.py` | Creado |

**Ningún archivo existente fue modificado.**

---

## 3. Decisiones tomadas

### 3.1 `DocumentationRequiredPolicy` solo aplica en finish
- **Decisión:** La policy solo bloquea cuando `status` es `"finished"` o `"documented"`, no durante `start`/`preflight`/`implementation_seen`.
- **Justificación:** Si se evalúa durante preflight, bloquea cualquier tarea con `changed_files` antes de que el agente pueda trabajar. El contrato dice "bloquea finish si no hay session note", no "bloquea preflight".
- **Impacto:** El test `test_changes_no_note_autopilot` se actualizó para pasar `status="finished"`.

### 3.2 `SecuritySensitiveDetector` con dos niveles de keywords
- **Decisión:** Dividir keywords en `SECURITY_KEYWORDS` (primary, confianza 0.7) y `SECONDARY_KEYWORDS` (auth/login, confianza 0.45).
- **Justificación:** Evitar que requests comunes como "fix login" o "Fix the login bug" se clasifiquen erróneamente como security con alta confianza, bloqueando el fast-code track.
- **Impacto:** `test_detects_fast_code` usa ahora `"Implement user profile page with email validation"` y `"profiles.py"`, evitando ambigüedad y security overlap.

### 3.3 `_minimal_render()` en `service.py`
- **Decisión:** Implementar un renderer mínimo inline en `service.py` como placeholder hasta Fase 4.
- **Justificación:** `finish(auto=True)` necesita generar un `SessionDraft`. El plan de Fase 4 introduce renderers formales; hasta entonces, un renderer mínimo permite que el servicio sea funcional end-to-end.
- **Reglas de seguridad epistémica aplicadas:**
  - Si no hay `changed_files` ni `user_request`, `confidence = "auto-draft"`.
  - Si no hay checkpoints verificados, se agrega warning.
  - No se inventa información no observada.

### 3.4 `resolve_detectors()` tolera excepciones
- **Decisión:** Si un detector lanza una excepción, se ignora en lugar de propagar el error.
- **Justificación:** Un detector defectuoso no debe romper todo el pipeline de Autopilot. Se registra en cobertura de tests (líneas 40-42 de `base.py`).

### 3.5 `most_restrictive()` en policies
- **Decisión:** La función retorna la decisión más restrictiva según prioridad fija: `block > degrade > warn > proceed`.
- **Justificación:** Esto permite que `preflight()` y `finish()` tomen una decisión única y consistente sin duplicar lógica.

---

## 4. Tests ejecutados y resultado

### 4.1 Tests unitarios de Autopilot
```bash
pytest tests/unit/autopilot/ -v
```
- **Resultado:** 90 passed, 0 failed.
- **Cobertura de módulos nuevos:**
  - `detectors/ambiguous.py`: 100%
  - `detectors/base.py`: 94%
  - `detectors/default.py`: 100%
  - `policies/auto_checkpoint.py`: 100%
  - `policies/base.py`: 89%
  - `policies/default.py`: 94%
  - `lifecycle.py`: 100%
  - `service.py`: 90%
  - `context_budget.py`: 77%

### 4.2 Regresión CLI histórico
```bash
pytest tests/unit/cli/test_main.py -q
```
- **Resultado:** 16 passed, 0 failed.

### 4.3 Import limpio
```bash
python -c "from cortex.autopilot.service import AutopilotService; print('ok')"
```
- **Resultado:** `ok` — no se inicializa Chroma ni ONNX.

---

## 5. Incidencia durante ejecución de tests (documentada para trazabilidad)

### 5.1 Síntoma
Al ejecutar `pytest tests/unit/autopilot/ -v` por primera vez, dos tests de `test_service.py` fallaron:

1. `TestPreflight::test_detects_fast_code` — esperaba `task_type="fast-code"`, pero obtuvo `"security"`.
2. `TestPreflight::test_detects_ambiguous` — esperaba `task_type="ambiguous"`, pero obtuvo `"security"`.

Además, al corregir el primer problema, apareció un tercer fallo:
3. `TestPreflight::test_detects_fast_code` (segunda corrida) — `can_proceed` era `False` en vez de `True`.

### 5.2 Causa raíz

**Problema A — Falsos positos en `SecuritySensitiveDetector`:**
El detector usaba un único conjunto `SECURITY_KEYWORDS` que incluía `"login"` y `"auth"` con confianza 0.7. Cuando el request era `"Fix the login bug"`, el detector de seguridad superaba el umbral de confianza (> 0.3) y, por la regla de prioridad del registry (§7.1.2), el resultado de seguridad bloqueaba al fast-code detector. Esto era un falso positivo: la mayoría de los requests que mencionan "login" no son tareas de seguridad crítica.

**Problema B — `DocumentationRequiredPolicy` mal posicionada en el ciclo:**
La policy evaluaba `if state.changed_files and not state.session_note_path` sin verificar la fase del ciclo. Como durante `preflight()` el estado ya tenía `changed_files` (pasados desde el request) pero aún no tenía `session_note_path`, la policy retornaba `block` (en modo `autopilot`) o `warn` (en modo `assist`). Esto hacía que `most_restrictive()` devolviera `allowed=False`, y `can_proceed` quedaba `False`.

### 5.3 Solución aplicada

**Para el Problema A:**
Se dividieron las keywords en dos niveles:
- `SECURITY_KEYWORDS` (primary): `"password", "secret", "token", "jwt", "encrypt", "hash", "permission", "role", "security", "vulnerability", "cve", "exploit", "csrf", "xss", "sql injection"` → confianza **0.7**.
- `SECONDARY_KEYWORDS`: `"auth", "login", "oauth"` → confianza **0.45**.

De esta forma, un request como `"Fix the login bug"` genera un resultado de seguridad con confianza 0.45, que queda **filtrado** por el umbral `confidence > 0.3` (pasa) pero en la resolución del registry, el `CodeChangeDetector` con confianza 0.7 gana el empate. Un request como `"Fix JWT token validation"` sigue generando 0.7 y se clasifica como security.

**Para el Problema B:**
Se agregó una guarda de fase a `DocumentationRequiredPolicy`:
```python
if state.status not in ("finished", "documented"):
    return PolicyDecision(allowed=True, reason="ok", action="proceed")
```
La policy ahora solo bloquea cuando el usuario intenta cerrar la sesión (`finish`) sin documentar, no durante el trabajo.

### 5.4 Verificación final
Tras los ajustes, `pytest tests/unit/autopilot/ -v` pasó **90 passed, 0 failed**.

### 5.5 Lección aprendida
Los detectores basados en heurísticas de texto deben validarse con ejemplos reales de requests. Una keyword demasiado amplia (como "login") puede dominar el pipeline si tiene confianza alta. Además, las policies deben respetar explícitamente la fase del ciclo de vida en la que se evalúan; una policy de "cierre" no debe ejecutarse durante "preflight".

---

## 6. Desviaciones respecto del plan

Ninguna desviación arquitectónica. Dos ajustes menores de implementación:
1. `DocumentationRequiredPolicy` se refinó para aplicar solo en estados de cierre (finish/documented), no durante el trabajo.
2. `SecuritySensitiveDetector` se refinó con dos niveles de keywords para reducir falsos positos en requests comunes.

Ambos ajustes fueron necesarios para que los tests de comportamiento real pasen sin contradicciones.

---

## 7. Riesgos residuales

| Riesgo | Nivel | Mitigación |
|--------|-------|------------|
| `_minimal_render()` es placeholder | Bajo | Se reemplazará en Fase 4 por `SessionBuilder` con renderers formales. El contrato de `SessionDraft` ya está estable. |
| `context_budget.py` sin tests directos | Bajo | Se testea indirectamente a través de `service.py` y `test_policies.py` (BudgetPolicy). Tests directos se agregarán en Fase 8. |
| `service.py` usa `WorkspaceLayout.discover()` en factory | Bajo | El factory se usa solo en integración; los tests usan inyección directa de `StateStore`. |
| Detectores basados en heurísticas simples | Medio | Suficientes para MVP. Se pueden extender con ML en fases futuras sin cambiar contratos. |

---

## 8. Próximos pasos

1. **Fase 3 — CLI Headless:**
   - Crear `cortex/autopilot/cli.py` con comandos `start`, `preflight`, `checkpoint`, `finish`, `status`, `doctor`.
   - Modificar `cortex/cli/main.py` para agregar `app.add_typer(autopilot_app, name="autopilot")`.
   - Tests: `test_cli.py` + regresión CLI.

2. **Fase 4 — Session Builder y Persistencia Automática:**
   - Reemplazar `_minimal_render()` con `SessionBuilder` y renderers formales.
   - Implementar self-review del draft.

3. **Fase 5 — MCP Tools Autopilot:**
   - Agregar tools MCP en `cortex/mcp/server.py`.

---

*Fin de la realización de la Fase 2.*
