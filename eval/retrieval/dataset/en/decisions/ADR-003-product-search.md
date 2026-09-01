---
title: ADR-003: Product search without Elasticsearch
tags: [doc]
---

## Context
The product search must filter by category and price range.
## Decision
We kept full-text search in Postgres with GIN indexes and dropped Elasticsearch.
## Consequences
Less operational burden; practical ceiling around 1M SKUs before revisiting.
