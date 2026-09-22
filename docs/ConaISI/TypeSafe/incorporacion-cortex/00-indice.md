# Índice — incorporación TypeSafe → Cortex

Síntesis. No es código. No es un PR. Cada ficha nombra el módulo ConaISI que tocaría y la primitiva TypeSafe que usaría.

Cortex de referencia: inventario `ConaISI/` (Python 0.7.0 / Rust 0.1.0, 2026-09-04). TypeSafe de referencia: `../typesafe/` (docs oficiales 2026-09-17).

## Orden de lectura

| # | Archivo | Pregunta que responde |
|---|---------|------------------------|
| 01 | [Tesis](01-tesis.md) | ¿Por qué esto no es un plugin más, sino la capa que le falta a Cortex? |
| 02 | [Huecos](02-huecos-en-cortex.md) | ¿Dónde Cortex “piensa” hoy, y con qué (regex/fórmula/NoOp)? |
| 03 | [Principio de encaje](03-principio-de-encaje.md) | ¿Qué contrato hay que respetar para no romper Cortex? |
| 04 | [Qué no hacer](04-lo-que-typesafe-no-debe-hacer.md) | ¿Dónde Jev 1.13 empeoraría el producto? |
| 05 | [Retrieval](05-retrieval-rerank-intent.md) | El multiplicador más grande |
| 06 | [Enricher](06-context-enricher.md) | Qué se inyecta al agente en 4000 chars |
| 07 | [Documenter](07-documenter-contradicciones-adr.md) | ContradictionDetector NoOp → juicio real |
| 08 | [Quality gates](08-session-quality-gates.md) | Claims vs diff |
| 09 | [Autopilot](09-autopilot.md) | Detectores lexicon → Choice+confidence |
| 10 | [Brain / MCP](10-brain-mcp-tools.md) | Router regex y 32 tools |
| 11 | [Enterprise](11-enterprise-promotion.md) | Auto-promote vs review |
| 12 | [ActionEngine](12-action-engine.md) | `cortex next` |
| 13 | [Escritura de memoria](13-escritura-memoria.md) | `remember` tipado |
| 14 | [Guardrails y CI](14-guardrails-ci.md) | Brain LLM + validate-pr |
| 15 | [Arquitectura de inserción](15-arquitectura-de-insercion.md) | Dónde vive el cliente, sin romper paridad |
| 16 | [Contrato de datos](16-contrato-de-datos.md) | State shapes y mapeo a modelos Cortex |
| 17 | [Orden de experimentos](17-orden-de-experimentos.md) | Qué probar primero, fuera del árbol de Cortex |
| 18 | [Métricas](18-metricas-y-eval.md) | Cómo saber si gana |
| 19 | [Paridad Python/Rust](19-paridad-python-rust.md) | Cómo no romper el contrato nativo |
| 20 | [Riesgos](20-riesgos.md) | Rate limit, literalness, costo, vendor |

## Mapa rápido módulo → primitiva

| Módulo Cortex (ConaISI) | Juicio | TypeSafe |
|---|---|---|
| `retrieval/intent.py` | EPISODIC/SEMANTIC/MIXED | Choice + confidence |
| `context_enricher/doc_intent.py` | DocType boost | Choice |
| `retrieval/hybrid_search.py` | Ranking de hits | Noul/Score por candidato (rerank) |
| `context_enricher/enricher.py` | ¿Este ítem entra al prompt? | Noul keep/drop/flag |
| `context_enricher/domain_detector.py` | auth/db/api/… | Choice |
| `documenter/contradiction_detector.py` | ¿Diff vs ADR? | Noul por par |
| `documenter/adr_evaluator.py` | ¿Mérito de ADR? | 3 Noul + composite |
| `session/quality_gates.py` | accept/redelegate/warn | Choice + Noul de evidencia |
| `autopilot/detectors/*` | tipo de tarea | Choice + Score complejidad + Noul ambiguous |
| `brain/router.py` / `cortex-brain` | intent de utterance | Choice + skill-suggestion sobre 32 tools |
| `enterprise/knowledge_promotion.py` | ¿promotable? | Noul + Score + confidence gate |
| `action_engine/scheduler.py` | ¿esta acción ahora? | Noul por candidata |
| `episodic/memory_store.py` + `models.py` | tipo, tags, contradicción | Choice + Noul |
| `episodic/summarizer.py` | no reemplazar | Jev no genera |
| `cortex-core` BM25/cosine | no tocar | matemáticas |
