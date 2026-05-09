# Fase 7.1 — Pi Autopilot Adapter: Realización

## Fecha
2026-05-09

## Resumen
Se implementó un adapter Autopilot dedicado para Pi Coding Agent, project-local, basado en extensión TypeScript. Pi se integra al contrato de adapters de la Fase 7 sin romper ningún adapter existente.

## Archivos creados

### Adapter Python
1. `cortex/autopilot/adapters/pi.py` — `PiAutopilotAdapter` con:
   - `install()`: copia extensión TS y skill MD, mergea `.pi/settings.json` preservando config existente, crea backup.
   - `uninstall()`: remueve solo archivos/entries Autopilot, preserva el resto.
   - `emit_session_start()`: delega a `format_session_start_output(..., "pi")` (formato default SDK).
   - Helpers testeables: `_load_settings`, `_merge_settings`, `_remove_settings_entries`.

### Templates Pi
2. `cortex/autopilot/pi/extensions/cortex-autopilot.ts` — extensión Pi que:
   - Registra handlers `session_start` y `session_finish`.
   - Llama `cortex autopilot start/finish --json` vía `child_process.execSync`.
   - Respeta `CORTEX_BIN` y `CORTEX_AUTOPILOT_MODE` del entorno.
   - Degrada gracefulmente si `execSync` no está disponible.
   - Guarda `sessionId` localmente entre eventos.

3. `cortex/autopilot/pi/skills/using-cortex-autopilot/SKILL.md` — skill Pi con:
   - Reglas de memoria aislada (solo `cortex_*`).
   - Presupuesto de contexto por perfil.
   - Fast Track / Deep Track.
   - ~200 palabras (bien bajo el límite de 1500).

### Tests
4. `tests/unit/autopilot/test_pi_adapter.py` — 27 tests cubriendo:
   - Helpers de settings (load, merge, remove, idempotencia, invalid JSON).
   - Install (crea archivos, mergea settings existentes, backup, idempotencia, error JSON).
   - Uninstall (remueve solo Autopilot, preserva otros settings).
   - Emit (formato JSON default).
   - Registry (`"pi"` en listado).
   - Platform detect (`PI_PLUGIN_ROOT`, `PI_CODING_AGENT`).
   - Templates (extensión menciona CLI, skill prohíbe memoria externa).

## Archivos modificados

1. `cortex/autopilot/adapters/platform_detect.py`:
   - Agregado `Platform.PI = "pi"`.
   - Agregada detección por `PI_PLUGIN_ROOT` y `PI_CODING_AGENT` (después de Codex, antes de UNKNOWN).

2. `cortex/autopilot/adapters/registry.py`:
   - Importado `PiAutopilotAdapter`.
   - Agregado `"pi": PiAutopilotAdapter` al diccionario `_ADAPTERS`.

3. `tests/unit/autopilot/test_platform_detect.py`:
   - Agregados tests `test_pi_plugin_root` y `test_pi_coding_agent`.
   - Actualizado `test_unknown` para desactivar también `PI_PLUGIN_ROOT` y `PI_CODING_AGENT`.

4. `tests/unit/autopilot/test_adapters.py`:
   - Actualizado `test_list_adapters` para incluir `"pi"`.
   - Actualizado `test_get_adapter_for_current_platform_unknown` para desactivar env vars de Pi.

## Diseño clave

### Dos capas
- **Python adapter**: maneja instalación/desinstalación de archivos y merge de settings.
- **TypeScript extension**: corre dentro de Pi y delega todo a `cortex autopilot` CLI. No implementa memoria propia.

### Merge conservador de settings
- `_merge_settings()` crea/usa listas existentes sin pisar otras claves (`model`, `theme`, `agents`, `tools`, etc.).
- `_remove_settings_entries()` elimina solo las entradas Autopilot, dejando el resto intacto.
- Backup `.autopilot-backup` se crea antes de cualquier modificación de settings.json.

### Rutas relativas consistentes
- `defaultExtensions`: `extensions/cortex-autopilot.ts` (sin `.pi/`)
- `skills`: `.pi/skills/using-cortex-autopilot/SKILL.md`

### Degradación graceful
- Si `.pi/` no existe, `install()` lo crea con settings mínimos.
- Si `settings.json` es JSON inválido, se lanza `ValueError` claro y el archivo original NO se pisa.
- La extensión TS maneja fallos de `execSync` con notificaciones `warn`, sin bloquear Pi.

## Tests
- `pytest tests/unit/autopilot/test_pi_adapter.py` — 27/27 passed.
- `pytest tests/unit/autopilot/test_platform_detect.py` — 8/8 passed.
- `pytest tests/unit/autopilot/test_adapters.py` — 27/27 passed.
- Suite completa Autopilot — 245/245 passed (sin regresiones).

## Incidentes y resoluciones
1. **`--project-root` vs `"project-root"` en test de template**: El template TS usa `"project-root"` como key del objeto de args, no `--project-root` como string literal. Se corrigió el test para buscar `"project-root"` en el texto.
2. **`get_adapter_for_current_platform()` retornaba Pi en lugar de None**: El test `test_get_adapter_for_current_platform_unknown` no desactivaba las env vars de Pi. Se actualizó para desactivar `PI_PLUGIN_ROOT` y `PI_CODING_AGENT`.

## Desviaciones respecto del plan
- Ninguna. El alcance se cumplió exactamente según el README de la fase.

## Riesgos residuales
- La extensión TypeScript no se compiló ni se ejecutó en un entorno Pi real en esta fase. Los tests verifican que el template contiene las strings esperadas, pero no validan comportamiento runtime de Pi.
- `session_finish` en Pi depende de que Pi exponga un evento con ese nombre. Si Pi usa otro nombre, la extensión no se registrará para el evento correcto. Esto está documentado en los comentarios del template TS.

## Próximos pasos
- Fase 8 ya está implementada y compatible (no requiere cambios).
- Fase 9+ pueden avanzar; Pi ya está registrado en el registry y detectado por env vars.
