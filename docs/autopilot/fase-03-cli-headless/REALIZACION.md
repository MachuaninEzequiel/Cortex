# Fase 3 — CLI Headless: Realización

**Fecha:** 2026-05-09  
**Estado:** Completada  
**Responsable:** Agente implementador (pi)

---

## 1. Qué se implementó

Se agregó el grupo CLI `cortex autopilot` como subcomando aislado, sin alterar los comandos históricos. Toda la lógica delega a `AutopilotService`.

### Archivos de runtime creados / modificados

| Archivo | Acción | Responsabilidad |
|---------|--------|-----------------|
| `cortex/autopilot/cli.py` | Creado | Grupo Typer `autopilot` con comandos `start`, `preflight`, `checkpoint`, `finish`, `status`, `doctor`. Todos aceptan `--project-root`. Los comandos de hooks/JSON aceptan `--json`. |
| `cortex/cli/main.py` | Modificado | Se agregó `from cortex.autopilot.cli import app as autopilot_app` y `app.add_typer(autopilot_app, name="autopilot")`. **Única** modificación al CLI histórico. |

### Comandos implementados

| Comando | `--project-root` | `--json` | `--auto` | Notas |
|---------|------------------|----------|----------|-------|
| `cortex autopilot start` | ✅ | ✅ | — | Devuelve `session_id`, `status`, `mode`. |
| `cortex autopilot preflight` | ✅ | ✅ | — | Devuelve `task_type`, `confidence`, `can_proceed`, `policy_decisions`. |
| `cortex autopilot checkpoint` | ✅ | ✅ | — | Devuelve `checkpoints_count`, `status`. |
| `cortex autopilot finish` | ✅ | ✅ | ✅ | Devuelve `saved`, `draft_title`/`reason`. |
| `cortex autopilot status` | ✅ | ✅ | — | Devuelve `active`, `session_id`, `event_count`, `warnings`. |
| `cortex autopilot doctor` | ✅ | ✅ | — | Solo lectura: verifica config, run_dir, state_store. |

### Archivos de test creados

| Archivo | Tests |
|---------|-------|
| `tests/unit/autopilot/test_cli.py` | 15 tests — start (default, json, mode, request), preflight (success, error), checkpoint (success, error), finish (auto, no-auto, error), status (empty, with session), doctor (json, text, read-only). |

---

## 2. Archivos creados / modificados

| Archivo | Acción |
|---------|--------|
| `cortex/autopilot/cli.py` | Creado |
| `tests/unit/autopilot/test_cli.py` | Creado |
| `cortex/cli/main.py` | Modificado (2 líneas: import + add_typer) |

---

## 3. Decisiones tomadas

### 3.1 Patrón `--json` uniforme
- **Decisión:** Todos los comandos aceptan `--json`. En modo JSON se imprime un dict serializable; en modo texto se imprime `key: value` línea por línea.
- **Justificación:** Los hooks (Fase 7) necesitan parsear la salida por stdout. Un formato JSON estructurado y predecible es obligatorio. El helper `_output()` centraliza esto.

### 3.2 Manejo de `SessionNotFoundError`
- **Decisión:** Si un comando recibe un `session_id` inexistente, imprime `{"error": "..."}` (o texto) por stderr y sale con código 1.
- **Justificación:** Los consumidores automáticos (hooks, scripts) necesitan detectar fallos por exit code, no por parseo de stdout.

### 3.3 `doctor` es read-only
- **Decisión:** `doctor` solo lee config, verifica que `run_dir` sea escribible (sin crear archivos permanentes) y prueba que `AutopilotService` sea inicializable.
- **Justificación:** El checklist de la fase exige que `doctor` no modifique archivos. `mkdir(parents=True, exist_ok=True)` es idempotente; no crea nada si ya existe.

### 3.4 `_resolve_service()` usa `WorkspaceLayout.discover()`
- **Decisión:** Cada comando descubre el layout desde `--project-root` o `cwd`.
- **Justificación:** Respeta la regla de no hardcodear `.cortex/`. El `AutopilotService.from_project_root()` encapsula esto.

### 3.5 Sin preguntas interactivas
- **Decisión:** Ningún comando hace `typer.prompt()` o input interactivo.
- **Justificación:** Los comandos deben funcionar en pipes y hooks sin stdin. Todos los parámetros se pasan por flags.

---

## 4. Tests ejecutados y resultado

### 4.1 Tests unitarios de Autopilot (incluyendo CLI)
```bash
pytest tests/unit/autopilot/ tests/unit/cli/test_main.py -v -k "not e2e"
```
- **Resultado:** 121 passed, 0 failed.
- **Cobertura del módulo CLI:** `cortex/autopilot/cli.py` 89%.

### 4.2 Regresión CLI histórico
```bash
pytest tests/unit/cli/test_main.py -q
```
- **Resultado:** 16 passed, 0 failed.
- **Observación:** La única modificación a `cortex/cli/main.py` fue el import y `app.add_typer`. Los tests existentes no se ven afectados.

### 4.3 Gate de salida verificado
- ✅ `cortex autopilot status --json` funciona en repo sin hooks instalados (test `test_status_no_sessions`).
- ✅ `start --json` devuelve `session_id` (test `test_start_json`).
- ✅ `finish --auto --json` devuelve draft info o reason (test `test_finish_auto`).
- ✅ `doctor` no modifica archivos (test `test_doctor_no_modifications`).
- ✅ Todos los comandos aceptan `--project-root`.

---

## 5. Incidencia durante ejecución de tests

Ninguna. Los 15 tests de `test_cli.py` pasaron en la primera ejecución. No hubo desviaciones del plan ni ajustes de heurísticas.

---

## 6. Desviaciones respecto del plan

Ninguna. El alcance exacto de la fase se cumplió:
- Solo se tocó `cortex/cli/main.py` para registrar el typer.
- No se modificó MCP server.
- No se agregaron comandos fuera de los 6 definidos.

---

## 7. Riesgos residuales

| Riesgo | Nivel | Mitigación |
|--------|-------|------------|
| `doctor` solo verifica 3 checks básicos | Bajo | Fase 10 expandirá doctor con detección de conflictos, hooks, adapters y rotación de JSONL. |
| `--json` no incluye todos los campos del estado | Bajo | Es intencional: los comandos CLI exponen solo los campos útiles para el usuario/agente. El estado completo está en `StateStore`. |
| Falta de comandos `enable`/`disable`/`install`/`uninstall` | Bajo | Pertenece a Fase 7 (Hook Adapters). No se anticiparon. |

---

## 8. Próximos pasos

1. **Fase 4 — Session Builder y Persistencia Automática:**
   - Crear `cortex/autopilot/session_builder.py` con renderers formales.
   - Reemplazar `_minimal_render()` en `service.py`.
   - Tests: `test_session_builder.py`.

2. **Fase 5 — MCP Tools Autopilot:**
   - Crear `cortex/autopilot/mcp_tools.py`.
   - Modificar `cortex/mcp/server.py` para registrar tools.

---

*Fin de la realización de la Fase 3.*
