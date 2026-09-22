# Context enricher

Módulos: `cortex/context_enricher/*`, `cortex-app/src/context/`, `AgentMemory.enrich()`, MCP `cortex_context`.

Depende de que retrieval ya produzca candidatos. Si el experimento 1 (rerank) gana, el enricher es el lugar donde se **elige qué entra al prompt** y **de qué tamaño**.

## Qué hace Cortex hoy

Observer → `WorkContext` (files, keywords, topic). Enricher: estrategias topic/files/keywords/pr_title/graph_expansion en paralelo. Dedup, multi-match boost, co-occurrence (grafo tipado de files), threshold, budget. Presenter: markdown / compact / JSON.

`budget_resolver`: mapea `task_type` + `complexity` a `(top_k, max_chars)`. Sin task_type, siempre `fast_code`. Docs-only desperdicia tokens; deep refactor se queda corto.

DomainDetector: path+keywords.

Filtros estructurales (`doc_type`, `status`, `tag`, `max_age_days`, `strict`) desvían `cortex_search` del RRF crudo al enricher. `max_age_days` es aritmética — código, no Jev.

## Qué agregar

### 1. Task type semántico (alimenta el budget que ya existe)

Hoy el task_type lo detecta Autopilot (lexicon). El enricher puede preguntar, **en el mismo call que el rerank** si la query es la misma:

```text
Choice task_type
  code_change, docs_only, question_only, security_sensitive, large_refactor, mixed

Score complexity
  0: Simple lookup or standard procedure
  1: Requires some judgment or multi-step process
  2: Unusual situation, edge case, or many files
```

Código: `resolve_budget_profile(task_type, complexity)` **sin cambiar la tabla de perfiles**. Solo mejora el input. Si `task_type.confidence < 0.5` → perfil default `fast_code` (no adivinar un deep-track caro).

Esto es Intent routing + el budget_resolver que Phase 08 ya reinstauró como datos.

### 2. Filtro de ítems enrichidos

Después de dedup y boosts, antes de recortar a `max_chars`:

Por `EnrichedItem`, Noul `belongs_in_prompt`:

```text
instructions: {
  question: "Should this item be injected into the agent's working prompt?",
  query: "...",
  task_type: "...",
  focus: "Useful, non-duplicative, current project knowledge. Not a restatement of the query."
}
```

Companion Noul `duplicates_higher_ranked` apuntando a los títulos ya aceptados (state chico: lista de ids aceptados, no los cuerpos). Código: greedy keep por noul descendente hasta `max_chars`.

### 3. DomainDetector como Choice, no como path-contains

```text
Choice domain
  auth, database, api, ci, docs, memory, retrieval, enterprise, other
```

State: files abiertos + keywords del observer (ya los tiene `WorkContext`). Si confidence baja → no boostear dominio (el detector actual ya exige threshold; acá el threshold es TypeSafe confidence).

El fallback embedding de DomainDetector puede quedarse para offline.

### 4. Co-occurrence

El grafo tipado de files es estructural (quién se menciona con quién). No reemplazar. Opcional: Noul “¿este vecino de co-occurrence es relevante a la query?” solo sobre los top vecinos, para no expandir el grafo entero (context rot).

## Presenter

No cambia. Sigue compact/full/JSON. TypeSafe no formatea.

Telemetry JSONL (`.cortex/enrichment-events.jsonl`): agregar `judgement.nouls`, `task_type.choice`, `task_type.confidence` para poder plotear después confidence vs “el agente usó este ítem” (si algún día hay feedback_loop conectado).

## Mejora esperada

El MCP `cortex_context` es lo que el agente IDE llama para no reinventar el repo. Hoy puede inyectar un runbook viejo porque el topic overlapó. Con filtro Noul + budget bien tipeado:

- docs-only → envelope chico, hits de vault semántico, cero episodios de bugs.
- security_sensitive → envelope grande, boost de ADRs/security, Noul injection/stale más agresivo.
- question_only → no gastar 4000 chars; 800 de un runbook bien elegido ganan.

Eso es dinero (tokens del agente IDE, no de Jev) y calidad. Jev cuesta $0.042/MTok; un Claude call de contexto inflado cuesta órdenes de magnitud más y además pudre al agente.
