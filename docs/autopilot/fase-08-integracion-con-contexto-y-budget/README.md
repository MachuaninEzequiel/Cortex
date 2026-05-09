# Fase 8 - Integracion con Contexto y Budget

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 8 - Integracion con Contexto y Budget`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

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

- El presupuesto de tokens manda: no agregues retrieval pesado sin perfil que lo justifique.
- `question_only` no debe usar embeddings.
- `finish_only` no debe hacer retrieval pesado.
- El estado debe guardar snapshot de budget para auditoria.

## Plan operativo original

## Fase 8 - Integracion con Contexto y Budget

### Objetivo

Hacer que Autopilot use contexto con presupuesto agresivo y medible.

### Archivos a crear

```text
cortex/autopilot/context.py
cortex/autopilot/budget_profiles.py
tests/unit/autopilot/test_context_budget.py
```

### Integracion

Usar:

- `AgentMemory.enrich()`
- `ContextEnricherConfig`
- `RetrievalResult.to_prompt(max_chars=...)`

### Profiles

```text
question_only
docs_only
fast_code
deep_code
finish_only
```

### Checklist

- [ ] `question_only` no llama embeddings.
- [ ] `fast_code` limita `max_chars`.
- [ ] `deep_code` requiere motivo de complejidad.
- [ ] `finish_only` no hace retrieval pesado.
- [ ] Estado guarda budget snapshot.

### Gate de salida

- Se puede explicar cuanto contexto inyecto Autopilot y por que.

---

