---
title: ADR-003: Búsqueda de productos sin Elasticsearch
tags: [postgres]
---

## Context
El buscador de productos debe soportar filtros por categoría y precio.
## Decision
Mantuvimos la búsqueda full-text en Postgres con índices GIN, descartando Elasticsearch.
## Consequences
Menos infraestructura operativa; límite práctico de ~1M de SKUs antes de revisitar la decisión.
