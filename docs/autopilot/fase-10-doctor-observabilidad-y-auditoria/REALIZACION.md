# Fase 10 — Doctor, Observabilidad y Auditoría: Realización

## Fecha
2026-05-09

## Resumen
Se implementó el diagnóstico completo de Autopilot (`doctor`), reportes de sesiones (`report`), y limpieza de eventos JSONL (`cleanup`). El doctor detecta 10 categorías de problemas incluyendo conflicto con Superpowers y rotación de JSONL. No modifica archivos salvo que se invoque `cleanup` explícitamente.

## Archivos creados
1. `cortex/autopilot/doctor.py` — `run_diagnosis()` con 10 checks:
   - `config`: config presente o defaults
   - `run_dir`: directorio escribible
   - `skills`: skills requeridas instaladas (`using-cortex-autopilot`)
   - `hooks`: adapters instalados (Cursor, Claude Code, OpenCode, Codex, Pi)
   - `adapters`: adapters conocidos en registry
   - `mcp_tools`: MCP server importable
   - `last_finish`: última sesión cerrada correctamente
   - `budget_warnings`: warnings en estado activo
   - `superpowers_conflict`: detección de plugin Superpowers
   - `jsonl_rotation`: archivos JSONL > 5MB o > 30 días

2. `cortex/autopilot/reporting.py` — `generate_report()` que genera reportes de las últimas N sesiones con métricas de budget, checkpoints, eventos y warnings.

3. `tests/unit/autopilot/test_doctor.py` — 14 tests cubriendo:
   - Diagnóstico completo en repo vacío
   - Detección de Superpowers por env var
   - Detección de hooks Cursor y Pi
   - Warning JSONL oversized
   - Reportes vacíos y con sesiones
   - Cleanup de archivos viejos y grandes

## Archivos modificados
1. `cortex/autopilot/cli.py`:
   - Reemplazado el comando `doctor` por versión completa que usa `run_diagnosis()`
   - Agregado comando `report` con `--last`
   - Agregado comando `cleanup` con `--older-than`
   - Importado `StateStore`

2. `cortex/autopilot/state_store.py`:
   - Agregado método `cleanup(older_than_days=30, max_size_mb=5.0)` que archiva JSONL viejos/grandes a `events_archive/`

3. `tests/unit/autopilot/test_cli.py`:
   - Ajustado `test_doctor_no_modifications` para no asumir `ok=True` en repo vacío (doctor correctamente reporta skills faltantes)

## Diseño clave

### Doctor read-only
- `doctor.py` nunca modifica archivos. Solo lee y reporta.
- Cada check retorna `DoctorCheck` con `name`, `ok`, `detail`, y `action` (recomendación al usuario).
- El reporte final incluye `ok` global (True solo si todos los checks pasan) y lista de `warnings`.

### Detección de Superpowers
- Verifica `CLAUDE_PLUGIN_ROOT` ending with "superpowers"
- Verifica paths conocidos: `.claude/plugins/superpowers`, `.cursor/plugins/superpowers`
- Si detecta, emite warning con recomendación clara de deshabilitar uno de los dos plugins.

### Rotación JSONL
- `StateStore.cleanup()` mueve archivos > 30 días o > 5MB a `events_archive/`
- CLI `cleanup --older-than 30` permite rotación manual
- Doctor verifica ambas condiciones y alerta si hay archivos que necesitan limpieza

### Reportes
- `generate_report()` carga los estados más recientes, los ordena por `updated_at`, y genera `SessionReport` con métricas agregadas.
- No requiere servicio activo; opera directamente sobre `StateStore`.

## Tests
- `pytest tests/unit/autopilot/test_doctor.py` — 14/14 passed.
- Suite completa Autopilot — 272/272 passed (sin regresiones).

## Incidentes y resoluciones
1. **`test_doctor_no_modifications` asumía `ok=True`**: El doctor completo detecta skills faltantes en un repo vacío, por lo que `ok=False`. Se ajustó el test para verificar estructura sin asumir el valor de `ok`.
2. **Cleanup requiere `workspace.yaml` para `WorkspaceLayout.discover()`**: En los tests de cleanup se crea un `workspace.yaml` mínimo para que el layout discovery funcione.

## Desviaciones respecto del plan
- Ninguna. Se implementaron todos los checks del doctor, reportes, y rotación JSONL exactamente según el plan.

## Riesgos residuales
- `doctor` detecta hooks por presencia de archivos marcadores. Si un adapter se instala de forma no estándar, podría no detectarse.
- La detección de Superpowers es heurística (paths conocidos + env var). Si Superpowers cambia su estructura, la detección podría fallar.

## Próximos pasos
- Fase 11 (Tests E2E y Evals) puede usar `doctor` para validar que el entorno está correctamente configurado antes de ejecutar tests.
