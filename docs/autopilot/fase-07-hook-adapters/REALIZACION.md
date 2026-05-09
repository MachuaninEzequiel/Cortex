# Fase 7 — Hook Adapters: Realización

## Fecha
2026-05-09

## Resumen
Se implementaron los adapters de hook por harness de forma segura y reversible. Se crearon 4 adapters (Cursor, Claude Code, OpenCode, Codex), detección de plataforma, hooks de session-start/session-finish, wrappers cross-platform, y tests correspondientes.

## Archivos creados

### Adapters
1. `cortex/autopilot/adapters/platform_detect.py` — detecta el IDE activo por variables de entorno (`CURSOR_PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, `COPILOT_CLI`, `OPENCODE_PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`).
2. `cortex/autopilot/adapters/base.py` — protocolo `AutopilotHookAdapter`, utilidades de backup/restore, eliminación de bloques Autopilot, y formateo del output JSON según contrato §7.4.1.
3. `cortex/autopilot/adapters/cursor.py` — `CursorAutopilotAdapter`.
4. `cortex/autopilot/adapters/claude_code.py` — `ClaudeCodeAutopilotAdapter`.
5. `cortex/autopilot/adapters/opencode.py` — `OpenCodeAutopilotAdapter`.
6. `cortex/autopilot/adapters/codex.py` — `CodexPluginAutopilotAdapter`.
7. `cortex/autopilot/adapters/registry.py` — registro central de adapters (`get_adapter`, `list_adapters`, `get_adapter_for_current_platform`).

### Hooks
8. `cortex/autopilot/hooks/session_start.py` — emite el payload `HookSessionStartOutput` formateado para la plataforma detectada, incluyendo el contenido de `using-cortex-autopilot.md` como bootstrap.
9. `cortex/autopilot/hooks/session_finish.py` — emite el estado de cierre de sesión.
10. `cortex/autopilot/hooks/run_hook.cmd` — wrapper Windows que invoca `python -m cortex.autopilot.hooks.<module>`.
11. `cortex/autopilot/hooks/run_hook.sh` — wrapper Unix equivalente.

### Tests
12. `tests/unit/autopilot/test_platform_detect.py` — 6 tests cubriendo todas las variables de entorno y prioridad.
13. `tests/unit/autopilot/test_adapters.py` — 27 tests cubriendo install/uninstall, backup/restore, emisión de JSON por plataforma, registro, y hooks end-to-end.

## Diseño clave

### Reversibilidad y backup
- `_write_with_backup()` renombra el archivo original a `*.autopilot-backup` antes de escribir.
- `_restore_backup()` recupera el archivo desde su backup.
- `_remove_autopilot_blocks()` elimina únicamente bloques delimitados por el marker de cada adapter (ej. `<!-- AUTOPILOT-CURSOR -->`), sin tocar el resto del archivo.

### Output JSON por plataforma (contrato §7.4.1)
- **Cursor**: `{"additional_context": "<payload_json>"}` (snake_case top-level)
- **Claude Code**: `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "<payload_json>"}}`
- **Otros** (OpenCode, Codex, Copilot CLI): `{"additionalContext": "<payload_json>"}` (SDK standard)

### Cross-platform
- Los wrappers `.cmd` y `.sh` delegan a `python -m`, garantizando que Windows funcione sin WSL ni Git Bash.
- Si Python no está en PATH, los wrappers emiten un JSON de error claro.

### Presupuesto de tokens
- `_budget_profile_for_state()` deriva el perfil del estado (`question_only`, `fast_code`, `deep_task`) sin reconsultar el vault.

## Tests
- `pytest tests/unit/autopilot/test_platform_detect.py` — 6/6 passed.
- `pytest tests/unit/autopilot/test_adapters.py` — 27/27 passed.
- Suite completa Autopilot — 194/194 passed (sin regresiones).

## Incidentes y resoluciones
1. **AutopilotSessionState requiere campos obligatorios**: `project_root` y `workspace_root` son requeridos por el modelo Pydantic. En los tests de adapters se ajustaron las instanciaciones para incluirlos.
2. **`WorkspaceLayout.discover` crea `.cortex/` automáticamente**: esto causó que `from_project_root()` usara `workspace_root = tmp_path/.cortex` mientras que los tests creaban `StateStore(tmp_path)`. Se resolvió usando `AutopilotService.from_project_root()` tanto en el setup como en la invocación del hook, garantizando el mismo `workspace_root`.
3. **`complexity` es Literal["none", "fast", "deep"]**: `_budget_profile_for_state()` originalmente usaba "low"/"high". Se corrigió para alinearse con el modelo.
