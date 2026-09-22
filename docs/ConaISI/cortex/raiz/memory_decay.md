# cortex/memory_decay.py

## Qué tiene adentro

- `DecayConfig`: `score = base_score * (decay_rate ^ hours_old)`. Default `decay_rate=0.995`, `half_life_hours=168` (7 días), `floor=0.10`, `min_age_hours=24`.
- `__post_init__`: si el caller no pisó `decay_rate` (sigue el default), lo deriva de `half_life_hours` (`0.5 ** (1/half_life)`). Si pisó `decay_rate`, se respeta (comentario bug #9).
- `PERMANENT_TYPES`: adr, architecture, decision, project_intro, vault_doc — decay reducido/piso.
- Funciones de aplicación de decay al score (resto del archivo).

## Para qué sirve

Bajar relevancia de recuerdos viejos en retrieval/enricher, sin borrar ADRs.

## Relaciones

### Recibe de

- Timestamps de `MemoryEntry` / items enricher.
- No importa otros `cortex.*` en las primeras 80 líneas.

### Envía a

- Context enricher / retrieval (importadores según AST del paquete enricher/filters).

---
Fuente: lectura de `cortex/memory_decay.py`. No se usó documentación previa.
