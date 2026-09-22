# src/context/presenter.rs

## Qué tiene adentro

`to_markdown`, `to_compact` (prompt injection), `to_markdown_grouped`, `to_compact_grouped` (Fase 08, agrupado). JSON vive en `EnrichedBundle::to_json`.

## Para qué sirve

Serializar el bundle a comentarios de PR, prompts y CI.

## Relaciones

### Recibe de

- `EnrichedBundle`.

### Envía a

- CLI/CI/MCP que piden presentaciones.

### Notas de implementación observadas en el código

El rendering rich de Python no es contrato; aquí es texto.
