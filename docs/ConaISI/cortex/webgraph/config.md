# cortex/webgraph/config.py

## Qué tiene adentro

- **Ruta de código:** `cortex/webgraph/config.py` (53 líneas).
- **Módulo Python:** `cortex.webgraph.config`.
- **Clases definidas:**
  - `WebGraphConfig` (BaseModel)
    - Métodos públicos/especiales: `default_path`, `load`, `save`

## Para qué sirve

Define WebGraphConfig. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.webgraph.contracts` (WebGraphMode)
- Dependencias externas/stdlib: `yaml`, `__future__`, `pathlib`, `typing`, `pydantic`

### Envía a

- `cortex.webgraph.graph_builder`
- `cortex.webgraph.relation_builder`
- `cortex.webgraph.server`
- `cortex.webgraph.service`
- `cortex.webgraph.setup`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 53.
Docstrings de símbolos públicos:
- `WebGraphConfig.default_path`: Return the config path for WebGraph.

---
Fuente: código de `cortex/webgraph/config.py` (AST + grafo de imports internos). No se usó documentación previa.
