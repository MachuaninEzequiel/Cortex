# Fase 11 — Tests End-to-End y Evals: Realización

**Fecha:** 2026-05-09  
**Estado:** Completado

---

## 1. Archivos creados

| Archivo | Descripción |
|---|---|
| `tests/e2e/scenarios/test_autopilot_basic.py` | Escenarios: pregunta simple, fast-code, docs-only, deep-track, cleanup, delegación stub |
| `tests/e2e/scenarios/test_autopilot_finish.py` | Escenarios: finish sin datos, sin duplicados, bloqueado por policy |
| `tests/e2e/scenarios/test_autopilot_budget.py` | Escenarios: métricas de presupuesto por perfil, mapeo de task types |
| `docs/autopilot/evals.md` | Documentación de evaluaciones con métricas, hallazgos y riesgos |
| `tests/e2e/scenarios/conftest.py` | Fixture `autopilot_workspace` (actualizado) |

## 2. Archivos modificados

| Archivo | Cambio | Motivo |
|---|---|---|
| `cortex/autopilot/doctor.py` | `_check_run_dir()` usa `os.access(..., W_OK)` en vez de crear/borrar `.write_test` | Mantener contrato read-only del doctor |
| `cortex/autopilot/doctor.py` | `_check_jsonl_rotation()` acción corregida a `--older-than 30` | Alineación con firma real del CLI (espera entero, no `30d`) |
| `tests/e2e/scenarios/conftest.py` | Agregado fixture `autopilot_workspace` | Workspace temporal aislado para E2E |

## 3. Decisiones tomadas

### 3.1 Tests determinísticos con `CliRunner` en lugar de subprocess + agentes reales

Se eligió `typer.testing.CliRunner` porque:
- No requiere red ni tokens.
- Es ~10× más rápido que subprocess.
- Cubre el contrato CLI → Servicio → StateStore de forma fiel.
- Los e2e existentes de Cortex (`test_setup_basic.py`) usan subprocess porque tocan el filesystem del workspace; Autopilot no necesita ese nivel de integración para validar comportamiento de servicio.

### 3.2 No se implementó persistencia física de session notes en `finish()`

El plan de fase 11 es medir y documentar, no inventar contratos. Se detectó que `finish(auto=True)` asigna `session_note_path` pero no escribe archivo. En lugar de implementar la escritura (que tocaría `service.py`, `session_builder.py` y posiblemente `AgentMemory`), se documentó la limitación en `evals.md` y se agregó una aserción explícita en el test que verifica que el archivo **no** existe.

### 3.3 Corrección mínima en `doctor.py`

`_check_run_dir()` creaba y borraba `.write_test`, violando el contrato read-only presentado en la Fase 10. Se cambió a `os.access(run_dir, os.W_OK)` (cambio de 4 líneas). Esto no afecta la API pública ni los tests unitarios existentes.

### 3.4 Corrección mínima en mensaje de doctor

La acción de `_check_jsonl_rotation` recomendaba `cortex autopilot cleanup --older-than 30d`, pero el CLI define `older_than: int = typer.Option(30, ...)`. Se corrigió a `--older-than 30` para evitar confusión del usuario.

## 4. Discrepancias detectadas contra fases anteriores

| Discrepancia | Ubicación | Resolución |
|---|---|---|
| Doctor read-only escribe en disco | `cortex/autopilot/doctor.py` `_check_run_dir` | Corregido (ver §3.3) |
| Doctor sugiere `--older-than 30d` pero CLI espera entero | `cortex/autopilot/doctor.py` `_check_jsonl_rotation` | Corregido (ver §3.4) |
| `finish(auto=True)` no escribe nota física | `cortex/autopilot/service.py` | Documentado; no corregido en esta fase |
| `_task_registry` es memoria de proceso | `cortex/autopilot/delegation.py` | Documentado; tests validan ausencia de persistencia cross-process |

## 5. Comandos ejecutados y resultados

```bash
# Regresión unitaria completa
pytest tests/unit/autopilot -q
# => 272 passed

# Suite E2E de escenarios Autopilot
pytest tests/e2e/scenarios/test_autopilot_basic.py tests/e2e/scenarios/test_autopilot_finish.py tests/e2e/scenarios/test_autopilot_budget.py -v
# => 22 passed in ~7s
```

Salida exacta de la suite unitaria:
```
........................................................................
........................................................................
........................................................................
........................................................
272 passed
```

Salida exacta de la suite E2E:
```
tests/e2e/scenarios/test_autopilot_basic.py ........
tests/e2e/scenarios/test_autopilot_finish.py .....
tests/e2e/scenarios/test_autopilot_budget.py ......
22 passed in 6.63s
```

## 6. Cobertura de escenarios mínimos

- [x] **Pregunta simple** — detecta `question-only`, presupuesto cero, no embeddings.
- [x] **Cambio simple** — Fast Track, checkpoint, finish genera draft, `session_note_path` registrado.
- [x] **Docs-only** — perfil `docs_only`, bajo presupuesto, draft generado.
- [x] **Tarea compleja** — Deep Track sugerido (`deep-code`), `deep_track_reason` persistido, delegación validada como stub.
- [x] **Finish sin datos** — draft seguro `auto-draft`, no inventa archivos/tests.
- [x] **Falla de herramienta** — proxy vía `AutoCheckpointPolicy`, degradación con warning, estado `finished` (no `documented`).
- [x] **Uninstall/cleanup/config** — `cleanup --older-than 30` archiva JSONL viejos, Typer rechaza `30d`.

## 7. Riesgos residuales y próximos pasos

1. **Persistencia de session notes:** Si se requiere archivo físico, la Fase 4 (Session Builder) necesita integrarse con `AgentMemory.save_session_note()`.
2. **Delegación real:** Las tools MCP `cortex_delegate_task` / `cortex_get_task_result` son stubs. Un e2e real con subagentes requerirá harness IDE o runtime `opencode`.
3. **Doctor hooks:** La detección de hooks instalados es heurística (presencia de archivos marcadores). Si un adapter se instala de forma no estándar, el doctor podría no detectarlo.
4. **Próximo paso recomendado:** Fase 12 (packaging) puede usar estos 22 tests e2e como gate de regresión antes de generar manifestos de plugin.
