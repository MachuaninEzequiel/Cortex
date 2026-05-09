# Fase 11 - Tests End-to-End y Evals

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 11 - Tests End-to-End y Evals`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

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

- Los e2e y evals son parte del producto, no una formalidad.
- Medir presupuesto es obligatorio: chars, retrievals, subagentes y tiempo de startup.
- No declares lista la fase si no cubre pregunta simple, cambio simple y cierre automatico.
- Documenta cualquier desviacion detectada por evals en la realizacion de esta fase.

## Plan operativo original

## Fase 11 - Tests End-to-End y Evals

### Objetivo

Probar comportamiento real con tareas representativas.

### Archivos a crear

```text
tests/e2e/scenarios/test_autopilot_basic.py
tests/e2e/scenarios/test_autopilot_finish.py
tests/e2e/scenarios/test_autopilot_budget.py
docs/autopilot/evals.md
```

### Escenarios minimos

1. Pregunta simple: no crea spec ni session.
2. Cambio simple: Fast Track, session auto.
3. Docs-only: session docs-only.
4. Tarea compleja: Deep Track sugerido o ejecutado segun modo.
5. Cierre sin datos: draft seguro.
6. Tool failure: warning y no invencion.
7. Uninstall: deja config limpia.

### Metricas

- session note creada cuando corresponde;
- no session note cuando no corresponde;
- chars de contexto;
- cantidad de retrievals;
- cantidad de subagentes;
- tiempo de startup;
- numero de archivos tocados por instalacion.

### Gate de salida

- Acceptance test documentado por harness piloto.
- Evals muestran que no hay consumo excesivo en casos simples.

---

