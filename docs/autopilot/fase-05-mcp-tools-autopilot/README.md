# Fase 5 - MCP Tools Autopilot

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 5 - MCP Tools Autopilot`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

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

- Esta es la primera fase donde esta permitido tocar `cortex/mcp/server.py`.
- No dupliques logica dentro del MCP server: delega en `AutopilotService`.
- Las tools Autopilot deben convivir con las tools `cortex_*` existentes sin romper compatibilidad.
- Si una tool falla, registra evento y devuelve error claro.

## Plan operativo original

## Fase 5 - MCP Tools Autopilot

### Objetivo

Exponer Autopilot al agente por MCP, sin duplicar logica.

### Archivos a crear

```text
cortex/autopilot/mcp_tools.py
tests/unit/autopilot/test_mcp_tools.py
```

### Archivo a tocar

```text
cortex/mcp/server.py
```

Cambio esperado:

- importar definiciones desde `cortex.autopilot.mcp_tools`;
- registrar tools;
- delegar llamadas a `AutopilotService`.

### Tools

```text
cortex_autopilot_start
cortex_autopilot_preflight
cortex_autopilot_checkpoint
cortex_autopilot_finish
cortex_autopilot_status
```

### Checklist

- [x] Tools aparecen en `list_tools`.
- [x] Tools devuelven texto compacto y JSON si conviene.
- [x] Errores se registran como eventos.
- [x] `cortex_save_session` puede marcar estado si recibe `session_id`.

### Gate de salida

- MCP server sigue soportando todas las tools anteriores.
- Autopilot no rompe `cortex_create_spec` sin session id.

---

