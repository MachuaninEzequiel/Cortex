---
title: cortex search, context, stats & reindex
description: Comandos de la familia de memoria cognitiva para búsqueda híbrida, extracción de contexto y métricas.
---

Los comandos de memoria permiten consultar, formatear e inspeccionar el conocimiento almacenado en Cortex.

---

## `cortex search`

Ejecuta una búsqueda cognitiva híbrida combinando el índice léxico BM25 y la similitud vectorial con el algoritmo RRF.

```bash
cortex search <QUERY> [OPCIONES]
```

### Opciones:
* `-k, --top-k <N>`: Número de resultados a retornar (por defecto: `5`).
* `--json`: Emite los resultados en formato JSON estructurado.
* `--show-scores`: Muestra los puntajes detallados de BM25, Coseno y RRF en la salida.

### Ejemplo:
```bash
cortex search "cómo funciona la verificación de handoffs" --top-k 3 --show-scores
```

---

## `cortex context`

Recupera y formatea el contexto más relevante para ser inyectado directamente en el prompt de un agente de IA.

```bash
cortex context <QUERY> [OPCIONES]
```

### Opciones:
* `-k, --top-k <N>`: Cantidad de fragmentos de contexto a incluir.
* `--json`: Formato JSON estructurado para integración programática con agentes.

### Ejemplo:
```bash
cortex context "arquitectura del servidor MCP"
```

Salida:
```text
=== CONTEXTO RELEVANTE DE CORTEX ===
[1] vault/adrs/002-mcp-server-rust.md (Relevancia RRF: 0.94)
> Implementación nativa del servidor MCP usando rmcp y tokio...

[2] memory/events.jsonl#mem_20260520_1100 (Relevancia RRF: 0.81)
> El servidor MCP expone 32 herramientas canónicas bajo la versión 2.2...
```

---

## `cortex stats`

Muestra las estadísticas y métricas cuantitativas de la memoria y el Vault:

```bash
cortex stats
cortex stats --json
```

### Información Reportada:
* Número total de eventos episódicos registrados en `.cortex/memory/`.
* Cantidad de notas en el Vault agrupadas por `doc_type` (ADRs, specs, runbooks, etc.).
* Dimensión del modelo de embeddings cargado (ej: 384).
* Tamaño en disco de los archivos de índice y caché de vectores.

---

## `cortex reindex`

Reconstruye los índices léxicos BM25 y vectoriales ONNX de todo el Vault:

```bash
cortex reindex
cortex reindex --dry-run
```

Útil tras clonar un repositorio, realizar un pull masivo de notas o modificar manualmente archivos en `.cortex/vault/`.
