# src/context/budget_resolver.rs

## Qué tiene adentro

Función pura `resolve_budget_profile(task_type, complexity) -> BudgetProfile { top_k, max_chars }`. `DEFAULT_PROFILE = FAST_CODE`. Perfiles son DATA en el fuente.

## Para qué sirve

Mapear tipo de tarea (autopilot/detectors) a presupuesto de retrieval.

## Relaciones

### Recibe de

- Strings `task_type` / `complexity` del detector de autopilot o caller.

### Envía a

- Callers que fijan `max_items`/`max_chars` del enricher.

### Notas de implementación observadas en el código

El comentario exige que si un test fija un valor, data y test se actualizan juntos.
