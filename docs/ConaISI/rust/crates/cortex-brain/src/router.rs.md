# rust/crates/cortex-brain/src/router.rs

## Qué tiene adentro

`Intent { tool, args, slash, razon }`. `route_intent(texto)`:

1. Slash `/cmd resto` si `cmd` ∈ `{help,doctor,stats,session,webgraph,actions,quit,search}`; slash desconocido → razón, sin tool.
2. Patrones regex (mismo orden que Python): health, vault.stats, session.current, webgraph.serve, actions.propose.
3. Verbos de búsqueda (`busca|buscá|search|encontrá|encontrar|relacionad`) → `memory.search` con query (prefijo recortado).
4. Pregunta abierta (≥3 palabras y termina en `?`) → `docs.related`.
5. Sin match → razón “sin match — el brain lista qué sabe hacer”.

## Para qué sirve

Ruteo determinista 1:1 con `cortex/brain/router.py` para el modo sin modelo y para tests de paridad conductual.

## Relaciones

### Recibe de

- texto del usuario (`chat::DeterministicBackend`, tests)

### Envía a

- `Intent` hacia `DeterministicBackend` (tool/slash/args)

### Notas de implementación observadas en el código

Los patrones son case-insensitive (`(?i)`). El render de respuestas no vive aquí: es de `tools`.
