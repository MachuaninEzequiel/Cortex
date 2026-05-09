# Fase 0 - Contrato y Cimientos

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 0 - Contrato y Cimientos`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

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

- Esta fase es documental y contractual: no implementes runtime todavia.
- Usa el flowchart de la seccion 6.1.1 del plan global como marco obligatorio para validar que los contratos no contradigan el flujo.
- La realizacion debe registrar cualquier decision de contrato que cambie el alcance de fases futuras.

## Plan operativo original

## Fase 0 - Contrato y Cimientos

### Objetivo

Definir el contrato estable antes de tocar runtime.

### Archivos a crear

```text
docs/autopilot/README.md
docs/autopilot/contracts.md
docs/autopilot/testing-strategy.md
```

### Archivos a revisar

```text
cortex/cli/main.py
cortex/mcp/server.py
cortex/workspace/layout.py
cortex/setup/cortex_workspace.py
cortex/ide/adapters/*
```

### Entregables

- Contrato de estado.
- Contrato de eventos.
- Contrato de adapters.
- Contrato de presupuesto.
- Matriz de compatibilidad IDE.

### Checklist

- [ ] Documentar `AutopilotSessionState`.
- [ ] Documentar `AutopilotEvent`.
- [ ] Documentar modos `observe`, `assist`, `autopilot`.
- [ ] Documentar extension points.
- [ ] Documentar no objetivos.

### Gate de salida

- El equipo puede implementar Fase 1 sin decidir arquitectura nueva.
- No hay contradicciones con `WorkspaceLayout`.
- El plan mantiene el CLI actual como modo valido.

---

