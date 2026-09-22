# Contrato de datos (state shapes)

Cómo armar el `state` en cada purpose para no caer en context rot ni en jaggedness. Recortes siempre en **código Cortex** antes del call.

## Reglas generales

- Objeto JSON con keys nombradas, no un string enorme.
- Paths en instructions con backticks (`query`, `candidates[0].text`).
- Cada `text`/`body` = matched_chunk o slice, no el archivo.
- IDs de question para el código; el modelo no los ve: la instruction lleva todo.
- Enums Cortex se copian como `criteria` de Choice (closed set).
- Números ya computados (`age_hours`, `n_files`) — Jev no resta fechas ni cuenta.

## retrieval_rerank

```json
{
  "query": "how does session checkpoint verification work?",
  "candidates": [
    {
      "id": "semantic:.cortex/vault/spec/session.md",
      "source": "semantic",
      "doc_type": "spec",
      "title": "Session primitive",
      "text": "<matched_chunk ≤ ~1200 chars>"
    },
    {
      "id": "episodic:mem_a1b2c3d4",
      "source": "episodic",
      "memory_type": "session",
      "confidence": "verified",
      "text": "<entry content recortado>"
    }
  ]
}
```

Cap: 20–30 candidatos (over-fetch actual ×3 de un top_k típico). Recortar `text` al chunk del vault reader (`matched_chunk_id`).

## query_intent / doc_intent / task_type

```json
{
  "query": "...",
  "open_files": ["cortex/session/verification.py"],
  "session_title": "optional"
}
```

Sin hits. Barato. Se puede ir en el **mismo** call que rerank si el budget de tokens lo permite; si el state de candidatos es grande, **sí** vale un call chico de intent primero porque los pesos RRF se aplican *antes* del over-fetch… Ojo: hoy RRF usa intent **antes** de fusionar. Eso sí es una dependencia:

- Call A: intent (query only) → pesos RRF.
- Código: search con esos pesos.
- Call B: rerank de unified_hits.

Es de las pocas veces que dos calls están justificadas (la answer de A cambia el retrieve). Alternativa v1: dejar pesos MIXED (1/1), un solo call de rerank. Más simple, menos “correcto”. El experimento 1 puede ser **solo B**.

## contradictions (finish)

```json
{
  "spec_goal": "...",
  "files_in_scope": ["..."],
  "diff": {"name_status": "M cortex/session/verification.py\n...", "hunks": "<solo files in scope, cap N KB>"},
  "checkpoints": [{"source": "ide-hook", "note": "..."}],
  "candidates": [{"id": "adr-12", "title": "...", "body_chunk": "..."}]
}
```

Candidatos: top ADRs/decisions de un search previo (código). Cap 10.

## quality_gates

Ver `08`. Diff slice = artifacts_touched, no files_in_scope enteros si el checkpoint tocó 2 files.

## autopilot

```json
{
  "utterance": "...",
  "open_files": ["..."],
  "keywords": ["..."],
  "session": {"open": true, "spec_title": "..."},
  "n_files_touched": 12
}
```

`n_files_touched` ya contado. LargeRefactor no le pide a Jev que cuente.

## brain_intent

```json
{ "utterance": "...", "slash": null }
```

Slash se resuelve en código *antes*. Si hay slash, no hay call.

## skill_suggestion request 1 vs 2

Request 1: `{ "utterance": "...", "tools": [{"id": "cortex_search", "one_liner": "..."}] }` × 32.

Request 2: `{ "utterance": "...", "tools": [top3 con description + input schema] }`.

## promotion

Ver `11`. `existing_titles` no bodies. Segunda call solo para el duplicado sospechoso.

## remember

```json
{
  "content": "...",
  "files_hint": ["..."],
  "near_hits": [{"id": "...", "type": "adr", "snippet": "...", "confidence": "verified"}]
}
```

Top 5. No el store.

## Mapeo de answers → tipos Cortex

| Answer TypeSafe | Campo Cortex |
|---|---|
| `query_intent.choice` | `QueryIntent` enum |
| `query_intent.confidence < τ` | forzar `MIXED` |
| `rel_{id}.noul` | sort key de `UnifiedHit` (nuevo campo opcional `judgement_noul`, no pisar `score` RRF) |
| `contradicts_{id}.noul` | `ContradictionFinding` |
| `hard/surprising/tradeoff` noul | `ADRSuggestion` + rationale numérico |
| `action.choice` | `ReviewVerdict.action` |
| `task_kind.choice` | detector kind / budget profile |
| `needs_clarification.noul` | AmbiguousRequest |
| `disposition.choice` | PromotionDecision |
| `memory_type.choice` | `MemoryType` |
| `org_knowledge` + hooks | `MemoryEntry.confidence` tri-estado |

No serializar `probabilities` al vault en v1 (salvo JSONL de telemetría). El vault sigue siendo markdown + frontmatter que un humano lee.
