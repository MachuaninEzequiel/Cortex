# Fase 0 - Preparacion del Core

**Fuente:** `docs/BusinessSignal/plan/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

Esta fase resuelve los blockers tecnicos que impiden construir BusinessSignal. Sin estos cambios, la telemetria capturaria datos incompletos y todo el sistema se construiria sobre cimientos debiles.

Al terminar la realizacion de esta fase, es obligatorio documentar lo desarrollado dentro de esta misma carpeta en un archivo `REALIZACION.md`.

## Nota obligatoria para agentes implementadores

### Reglas generales heredadas del item 14 del plan global

- **No improvises.** Segui el alcance exacto de esta fase.
- **No saltees tests.** La fase no esta completa hasta cumplir su gate de salida.
- **Usa `WorkspaceLayout`.** No hardcodees `.cortex/`, `config.yaml` ni rutas legacy.
- **Si algo no esta claro, pregunta antes de asumir.**

### Aplicacion especifica en esta fase

- Esta fase toca modelos core de Cortex. Cada cambio debe tener test de regresion.
- No crees el modulo `business_signal` todavia. Solo preparas el core.
- No modifiques el formato de prompt de `EnrichedContext.to_prompt_format()`.
- Los campos nuevos en `EnrichedItem` deben ser opcionales con defaults.

## Plan operativo

### Objetivo

Resolver dos blockers:
1. `EnrichedItem` no preserva origin metadata de los hits.
2. No existe `project_id` como concepto formalizado.

### Tarea 1: Extender EnrichedItem

**Archivo a tocar:** `cortex/models.py`

Agregar campos opcionales a `EnrichedItem`:

```python
class EnrichedItem(BaseModel):
    # ... campos existentes ...
    memory_type: str | None = None
    origin_scope: Literal["local", "enterprise", "unknown"] = "unknown"
    origin_project_id: str | None = None
    origin_vault: str | None = None
```

**Reglas criticas:**
- Los campos son opcionales con defaults seguros.
- `to_prompt_format()` de `EnrichedContext` NO debe cambiar su output.
- Los tests existentes de `EnrichedItem` deben seguir pasando sin modificacion.

### Tarea 2: Propagar origin metadata en el enricher

**Archivo a tocar:** `cortex/context_enricher/enricher.py`

En los metodos `_unified_hit_to_enriched`, `_episodic_hit_to_enriched` y `_semantic_hit_to_enriched`, propagar los campos de origen que ya existen en `EpisodicHit` y `SemanticDocument`:

```python
# En _unified_hit_to_enriched, rama episodic:
return EnrichedItem(
    # ... campos existentes ...
    memory_type=hit.entry.memory_type,
    origin_scope=getattr(hit, 'origin_scope', 'unknown'),
    origin_project_id=getattr(hit, 'origin_project_id', None),
    origin_vault=getattr(hit, 'origin_vault', None),
)

# En _unified_hit_to_enriched, rama semantic:
return EnrichedItem(
    # ... campos existentes ...
    memory_type=None,
    origin_scope=getattr(hit.doc, 'origin_scope', 'unknown'),
    origin_project_id=getattr(hit.doc, 'origin_project_id', None),
    origin_vault=getattr(hit.doc, 'origin_vault', None),
)
```

**Nota para el implementador:** Usar `getattr` con default para evitar errores si el hit no tiene esos campos (compatibilidad con mocks y tests existentes).

Aplicar el mismo patron a `_episodic_hit_to_enriched` y `_semantic_hit_to_enriched`.

### Tarea 3: Formalizar project_id en config

**Archivo a revisar:** `cortex/workspace/layout.py` y el schema de `config.yaml`

Agregar soporte opcional para:

```yaml
project:
  id: "client-mobile-redesign"
  client_id: "acme-corp"
```

Si `project.id` no existe en config, derivar un id estable del nombre del directorio raiz del proyecto. NO fallar si no esta definido.

### Archivos de test a crear/verificar

```text
tests/unit/test_models.py  — verificar que EnrichedItem serializa con campos nuevos
tests/unit/context_enricher/test_enricher.py — verificar que origin se propaga
```

### Checklist

- [ ] `EnrichedItem` tiene `memory_type`, `origin_scope`, `origin_project_id`, `origin_vault`.
- [ ] Los campos nuevos son opcionales con defaults seguros.
- [ ] `EnrichedContext.to_prompt_format()` produce la misma salida que antes.
- [ ] `_unified_hit_to_enriched` propaga origin de `EpisodicHit`.
- [ ] `_unified_hit_to_enriched` propaga origin de `SemanticDocument`.
- [ ] `_episodic_hit_to_enriched` propaga origin.
- [ ] `_semantic_hit_to_enriched` propaga origin.
- [ ] Tests existentes del enricher siguen pasando.
- [ ] config.yaml soporta `project.id` opcional.
- [ ] Si `project.id` no existe, se deriva del directorio.

### Gate de salida

- `pytest tests/unit/test_models.py` pasa.
- `pytest tests/unit/context_enricher/` pasa.
- `EnrichedItem` con origin metadata serializa y deserializa correctamente.
- El formato de prompt no cambio (comparar output antes/despues).

---
