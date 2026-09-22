# src/context/decay.rs

## Qué tiene adentro

`DEFAULT_DECAY_RATE = 0.995`. Tipos permanentes: adr, architecture, decision, project_intro, vault_doc. Tags permanentes: adr, architecture, decision, permanent, onboarding, getting-started, runbook, design, tech-spec.

`DecayConfig { decay_rate, half_life_hours, floor, min_age_hours=24 }`. `new(half_life, floor)`: si rate sigue default y half_life>0, `decay_rate = 0.5^(1/half_life)`.

`calculate_decay_factor(...)`: 1.0 si permanente o age < min_age; si no `max(rate^(age-min_age), floor)`. Parse RFC3339 o formatos naive.

## Para qué sirve

Bajar scores de memorias viejas no permanentes.

## Relaciones

### Recibe de

- timestamp/tipo/tags de `EnrichedItem`/`MemoryEntry` y `now`.

### Envía a

- `ContextEnricher` al ajustar `enriched_score`.

### Notas de implementación observadas en el código

El comentario cita «bug #9»: half_life deriva el rate solo si no se sobreescribió el default.
