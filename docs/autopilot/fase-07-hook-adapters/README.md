# Fase 7 - Hook Adapters

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 7 - Hook Adapters`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

Al terminar la realizacion de esta fase, es obligatorio documentar lo desarrollado dentro de esta misma carpeta en un archivo `REALIZACION.md`. Esa realizacion debe incluir decisiones tomadas, archivos modificados, tests ejecutados, desviaciones respecto del plan, riesgos residuales y pendientes.

## Nota obligatoria para agentes implementadores

Esta nota baja a esta fase las reglas del item 18 del plan global. Es obligatoria antes de implementar.

### Reglas generales heredadas del item 18

- **No improvises.** Segui el alcance exacto de esta fase y no agregues campos, servicios ni adapters fuera de lo definido.
- **No saltees tests.** La fase no esta completa hasta cumplir su gate de salida.
- **Usa `WorkspaceLayout`.** No hardcodees `.cortex/`, `config.yaml`, `vault/` ni rutas legacy.
- **Cada archivo nuevo debe tener test unitario correspondiente** cuando la fase cree codigo runtime.
- **Si algo no esta claro, pregunta antes de asumir.** La racionalizacion es el enemigo del Autopilot.

### Aplicacion especifica en esta fase

- Cada adapter debe ser reversible y crear backup antes de modificar configuracion.
- No asumas que todos los IDEs soportan los mismos eventos.
- Los hooks deben llamar CLI/MCP; no deben reimplementar logica de memoria.
- Windows debe estar contemplado mediante wrapper o degradacion clara.

## Plan operativo original

## Fase 7 - Hook Adapters

### Objetivo

Instalar hooks por harness de forma segura y reversible.

### Archivos a crear

```text
cortex/autopilot/adapters/base.py
cortex/autopilot/adapters/registry.py
cortex/autopilot/adapters/platform_detect.py
cortex/autopilot/adapters/claude_code.py
cortex/autopilot/adapters/cursor.py
cortex/autopilot/adapters/opencode.py
cortex/autopilot/adapters/codex.py
cortex/autopilot/hooks/session_start.py
cortex/autopilot/hooks/session_finish.py
cortex/autopilot/hooks/run_hook.cmd
cortex/autopilot/hooks/run_hook.sh
tests/unit/autopilot/test_adapters.py
tests/unit/autopilot/test_platform_detect.py
```

### Detalle: `platform_detect.py`

Este modulo encapsula la deteccion de plataforma por variables de entorno. Es usado por todos los adapters y por el hook de session-start.

```python
from enum import Enum
import os

class Platform(Enum):
    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    COPILOT_CLI = "copilot-cli"
    OPENCODE = "opencode"
    CODEX = "codex"
    UNKNOWN = "unknown"

def detect_platform() -> Platform:
    if os.environ.get("CURSOR_PLUGIN_ROOT"):
        return Platform.CURSOR
    if os.environ.get("CLAUDE_PLUGIN_ROOT") and not os.environ.get("COPILOT_CLI"):
        return Platform.CLAUDE_CODE
    if os.environ.get("COPILOT_CLI"):
        return Platform.COPILOT_CLI
    # Agregar deteccion para OpenCode y Codex cuando se definan sus vars
    return Platform.UNKNOWN
```

### Detalle: `run_hook.cmd` (wrapper Windows)

Superpowers tiene un wrapper probado para resolver el problema bash-en-Windows. Cortex debe tener su propio wrapper Python que funcione cross-platform sin depender de bash:

```cmd
@echo off
python -m cortex.autopilot.hooks.%1 %2 %3 %4 %5
```

El equivalente `run_hook.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
python -m cortex.autopilot.hooks."$1" "${@:2}"
```

Nota para el implementador: usar Python como runtime del hook en lugar de bash puro. Esto garantiza compatibilidad Windows sin `WSL` ni `Git Bash`.

### Comandos relacionados

```bash
cortex autopilot install --ide claude-code
cortex autopilot install --ide cursor
cortex autopilot uninstall --ide cursor
```

### Inspiracion de Superpowers

Copiar el patron conceptual:

- wrapper cross-platform;
- hook de session start;
- salida JSON de additional context con formato por plataforma (ver 7.4.1);
- bootstrap minimo.

No copiar:

- contenido exacto;
- comportamiento que fuerce skills en cada micro-paso;
- dependencia de un solo harness.

### Checklist

- [x] Cada adapter declara eventos soportados.
- [x] Instalacion crea backup antes de modificar config.
- [x] Uninstall remueve solo bloques Autopilot.
- [x] Windows funciona con wrapper `.cmd` (sin dependencia de bash).
- [x] Si falta Python en PATH, falla con error claro.
- [x] Hook session-start emite JSON segun contrato 7.4.1.
- [x] `platform_detect.py` tiene tests para cada variable de entorno.
- [x] Hook session-start incluye contenido de `using-cortex-autopilot.md`.

### Gate de salida

- Al menos un adapter piloto funciona end-to-end.
- Los perfiles IDE actuales siguen intactos.
- Output JSON validado contra `HookSessionStartOutput` schema.

---

