# cortex/enterprise/retrieval_service.py

## Qué tiene adentro

- `RetrievalSourceConfig` (pesos local vs enterprise, default 1.0/1.0).
- `EnterpriseRetrievalService.search(query, scope, top_k, use_embeddings, project_id)`:
  - arma `VaultSource` / `EpisodicSource` según scope;
  - `MultiVaultReader` + `MultiEpisodicReader`;
  - RRF con `_RRF_K = 60` (mismo k que hybrid local);
  - error si scope enterprise y no hay sources habilitados.

## Para qué sirve

Retrieval multi-vault/multi-chroma cuando `AgentMemory.retrieve(scope!=local)`.

## Relaciones

### Recibe de

- `EnterpriseOrgConfig`.
- Paths locales (vault, persist dir) + embedding model/backend.
- `cortex.enterprise.sources`.
- Modelos `RetrievalResult` / `UnifiedHit`.

### Envía a

- Solo `AgentMemory.retrieve` (AST).

---
Fuente: lectura de `cortex/enterprise/retrieval_service.py`. No se usó documentación previa.
