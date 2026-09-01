---
title: Spec gate paridad v2
doc_type: spec
---

Objetivo v2: el gate ahora cubre además el reindex incremental semántico.
index_file re-parsea un solo archivo y recalcula BM25 completo.
Los chunks viejos del padre se purgan antes de regenerar.
