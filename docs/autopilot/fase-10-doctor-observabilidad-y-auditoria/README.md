# Fase 10 - Doctor, Observabilidad y Auditoria

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 10 - Doctor, Observabilidad y Auditoria`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

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

- Doctor y reportes no deben modificar archivos salvo que el comando lo declare explicitamente.
- Detecta conflictos con Superpowers sin desinstalar ni pisar configuraciones ajenas.
- La rotacion de JSONL debe preservar auditoria y evitar crecimiento sin limite.
- Cualquier warning debe ser accionable para el usuario.

## Plan operativo original

## Fase 10 - Doctor, Observabilidad y Auditoria

### Objetivo

Hacer visible el estado de Autopilot y detectar conflictos.

### Archivos a crear

```text
cortex/autopilot/doctor.py
cortex/autopilot/reporting.py
tests/unit/autopilot/test_doctor.py
```

### Comandos

```bash
cortex autopilot doctor
cortex autopilot status --session-id <id>
cortex autopilot report --last 10
```

### Doctor debe validar

- config presente o defaults;
- hooks instalados;
- adapter reconocido;
- MCP tools disponibles;
- run dir escribible;
- skills instaladas;
- ultimo cierre documentado;
- warnings de presupuesto;
- **conflicto con Superpowers** (ver detalle abajo);
- **rotacion de JSONL de eventos** (ver detalle abajo).

### Deteccion de conflicto con Superpowers

Si un usuario tiene Superpowers instalado simultaneamente con Cortex Autopilot, ambos van a intentar inyectar bootstraps al inicio de sesion, causando conflictos e inflacion de tokens.

Doctor debe detectar:

```python
def check_superpowers_conflict(project_root: Path) -> str | None:
    """Detecta si Superpowers esta instalado en el mismo proyecto."""
    indicators = [
        project_root / ".claude" / "plugins" / "superpowers",
        project_root / ".cursor" / "plugins" / "superpowers",
    ]
    # Tambien verificar por variable de entorno
    if os.environ.get("CLAUDE_PLUGIN_ROOT", "").endswith("superpowers"):
        return "Superpowers detected via CLAUDE_PLUGIN_ROOT env var"
    for path in indicators:
        if path.exists():
            return f"Superpowers detected at {path}"
    return None
```

Si se detecta, doctor debe emitir:

```text
⚠ WARNING: Superpowers plugin detected alongside Cortex Autopilot.
  Both inject bootstraps at session start, which may cause:
  - Duplicate instructions
  - Token budget inflation
  - Conflicting workflow rules
  
  Recommendation: Disable one of the two plugins.
  Run `cortex autopilot uninstall` or remove Superpowers.
```

### Rotacion de JSONL de eventos

El archivo `.cortex/run/autopilot/events/<session-id>.jsonl` puede crecer sin limite en sesiones largas. Doctor debe verificar:

- Si algun archivo JSONL supera 5MB, emitir warning.
- `StateStore` debe implementar rotacion: archivar sesiones de mas de 30 dias.
- Rotacion manual: `cortex autopilot cleanup --older-than 30d`.

### Gate de salida

- Un usuario puede diagnosticar por que Autopilot no se activo.
- Conflictos con Superpowers se detectan automaticamente.

---

