# cortex/webgraph/static/app.js

## Qué tiene adentro

Cliente del grafo:
- Lee DOM: mode, project/type/time filters, depth, search, reload, reset, open-node, load-subgraph.
- Paleta nodos: `semantic_spec/session/doc`, `episodic_spec/session/general` (color+shape).
- Paleta edges: `wikilink`, `same_spec_reference`, `same_file_reference`, `shared_entity`, `shared_tag`, `semantic_neighbor`.
- Estado: `network` (vis-network), snapshots (`rootSnapshot`, `currentBaseSnapshot`, `currentSnapshot`), `selectedNode`.
- El resto del archivo (518 líneas) pide JSON al backend Flask y redibuja.

## Para qué sirve

Interacción del “cerebro visible”: filtrar, buscar, abrir nodo, subgrafo.

## Relaciones

### Recibe de

- HTML `index.html`.
- API HTTP de `cortex.webgraph.server` (snapshots/nodos).

### Envía a

- vis-network en `#network`.
- Botón open-node → opener del server (ruta segura al vault).

---
Fuente: lectura del inicio de `cortex/webgraph/static/app.js`. No se usó documentación previa.
