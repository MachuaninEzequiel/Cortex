# Fase 3 - CLI Headless

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 3 - CLI Headless`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

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

- No toques el CLI existente salvo la conexion minima `app.add_typer(autopilot_app, name="autopilot")`.
- Mantene el grupo `cortex autopilot` aislado en `cortex/autopilot/cli.py`.
- No agregues preguntas interactivas en comandos pensados para hooks o `--json`.
- No toques el MCP server; eso pertenece a la Fase 5.

## Plan operativo original

## Fase 3 - CLI Headless

### Objetivo

Agregar `cortex autopilot` sin alterar los comandos actuales.

### Archivos a crear

```text
cortex/autopilot/cli.py
tests/unit/autopilot/test_cli.py
```

### Archivo a tocar

```text
cortex/cli/main.py
```

Solo para registrar:

```python
app.add_typer(autopilot_app, name="autopilot")
```

### Comandos

```bash
cortex autopilot start
cortex autopilot preflight
cortex autopilot checkpoint
cortex autopilot finish
cortex autopilot status
cortex autopilot doctor
```

### Checklist

- [ ] Todos aceptan `--project-root`.
- [ ] Todos aceptan `--json` si son consumidos por hooks.
- [ ] `start --json` devuelve `session_id`.
- [ ] `finish --auto --json` devuelve path o razon de no-op.
- [ ] `doctor` no modifica archivos.

### Gate de salida

- El CLI viejo sigue pasando sus tests.
- `cortex autopilot status --json` funciona en repo sin hooks instalados.

---

