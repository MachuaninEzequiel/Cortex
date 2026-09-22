# Huecos de juicio en Cortex (inventario)

Fuentes: fichas ConaISI citadas por módulo. Hechos, no rediseño.

## 1. Retrieval — `cortex/retrieval/intent.py` (175 líneas)

`QueryIntentDetector` clasifica la query en EPISODIC / SEMANTIC / MIXED con `_EPISODIC_SIGNALS` y `_SEMANTIC_SIGNALS` (lexicon). Mapeo de pesos:

- EPISODIC → (2.0, 0.6)
- SEMANTIC → (0.6, 2.0)
- MIXED → (1.0, 1.0)

`HybridSearch` usa eso para RRF (`k=60`), over-fetch ×3. Si el lexicon falla (“el login volvió a romperse, ¿cómo está diseñado el token refresh?”), los pesos se van para el lado incorrecto y RRF privilegia la fuente equivocada.

No hay confidence. No hay “no sé” → MIXED solo si no matchean señales, no si matchean las dos.

## 2. DocIntent — `cortex/context_enricher/doc_intent.py` (159 líneas)

Lexicon `_DOC_PATTERNS` → boost 2.5× a un DocType (`RUNBOOK`, etc.). Ortogonal a QueryIntent. Mismo fallo: paráfrasis sin la palabra “runbook” no boostea runbooks.

La ficha nota que **ningún otro módulo lo importa por nombre** en el AST de `cortex/` — puede estar wired por import dinámico o subusado. Hueco doble: detector léxico *y* posiblemente desconectado.

## 3. DomainDetector — `domain_detector.py` (385 líneas)

Path 0.6 + keywords 0.4. Devuelve el mejor dominio solo si confidence > threshold. “Confidence” acá es score de reglas, no calibración. Fallback a embeddings. No entiende “esto es un cambio de auth” si los files se llaman `gateway.py`.

## 4. Enricher — `enricher.py` (658) + `budget_resolver.py` (58)

Multi-strategy (topic, files, keywords, pr_title, graph_expansion). Dedup, multi-match boost, co-occurrence, threshold, budget. `RetrievalResult.to_prompt` default **4000 chars**.

No hay un juicio “¿este hit responde la query?”. El budget se resuelve por `task_type` detectado (autopilot). Si el task_type está mal, se sub-sirve un refactor o se desperdician tokens en una pregunta.

## 5. ContradictionDetector — `documenter/contradiction_detector.py` (93 líneas)

Protocol + `NoOpContradictionDetector`. La ficha es explícita: el check del reconstructor §7.2 step 5 requiere `AgentMemory` completo, demasiado pesado para `cortex finish-session` CLI. El CLI pasa NoOp. El subagente MCP *puede* dar una implementación backed by `cortex_search`. Phase 02+ “may promote a default implementation”.

**Hoy el finish CLI no detecta contradicciones.** Es el hueco más honesto del inventario.

## 6. ADR evaluator — `adr_evaluator.py` (115 líneas)

La arquitectura del documenter subagent (§12) exige tres criterios para merecer ADR: hard to reverse, surprising without context, real trade-off. Cita de la ficha:

> Pure-Python evaluation cannot judge those qualities; what we *can* do is detect keyword signals in checkpoint notes and flag them as *candidates*.

`_DECISION_PATTERNS`. Sin checkpoints (BYO mode), cero candidatos.

## 7. Quality gates — `session/quality_gates.py` (203 líneas)

Dos stages puros:

- Stage 1: `artifacts_touched ⊆ spec.files_in_scope`; claims o artifacts no vacíos.
- Stage 2: no `TBD`/`FIXME`/`???`; si hay keywords de test/build, al menos un claim > 10 chars. Un `"tests"` desnudo no es evidencia.

Output: `accept | redelegate | warn`. Stage 1 es determinista y está bien. Stage 2 es un proxy de calidad de prosa, no de verdad del claim contra el diff.

`verification.py` (156) corre hooks de la spec (comandos). Eso **sí** es evidencia. No es juicio semántico.

## 8. Autopilot detectors — `detectors/default.py` (298) + `ambiguous.py` (63)

CodeChange, DocsOnly, QuestionOnly, SecuritySensitive, LargeRefactor, Noop, AmbiguousRequest. Protocol en `base.py`. Policies en `policies.py` (374) — modos, enforcement, `DEFAULT_BUDGET_PROFILE = "fast_code"`.

Los detectores son el input de policies y del budget_resolver. Si SecuritySensitive depende de paths/keywords, un cambio de crypto en `core/util.rs` pasa de largo.

AmbiguousRequest es el caso TypeSafe por excelencia (confidence baja), implementado como detector más.

## 9. Brain router — `cortex/brain/router.py` (61) / `cortex-brain/src/router.rs`

`route_intent(texto)`: slash commands primero, después `_PATRONES` regex. Fallback degradado, 0 tokens. El LLM se agrega encima.

Tools nativos (`tools.rs`): memory.search, docs.related, cortex.health, vault.stats, session.current, webgraph.serve (SafeAction), actions.propose (Read, no ejecuta).

32 tools MCP en `tools_catalog.rs`. No hay un juez semántico de “qué tool para este utterance” más allá del regex.

## 10. ActionEngine scheduler — `scheduler.py` (100)

`score = impacto × frescura − costo`, top 5. Signals de 14 días. Catálogo de 10–11 acciones fijas. No pregunta “¿el usuario está trabado en una sesión stale?” en lenguaje natural: pregunta precondiciones booleanas.

## 11. Enterprise promotion

`PromotionRulesEngine.is_promotable` + `promotion_doctype.py` (as-is / summarize / review-required según `RouteSpec`). Governance de equipos y clasificación. No hay juicio “¿esta nota de sesión es conocimiento de org o ruido?”. SESSION se summariza por split de H2, no por calidad.

MCP **no** tiene tools de promote (no están en `tools_catalog.rs`). Eso queda en CLI/UI.

## 12. Memoria: confidence tri-estado

`MemoryEntry.confidence` ∈ {verified, asserted, contradicted, None}. Nace en documenter según Verification Gate contra el diff. No es P(correcto). Recuerdos pre-0.5.0 pueden no tenerlo.

Decay (`memory_decay.py`): fórmula `base * (decay_rate ^ hours)`, half-life 7 días, floor 0.10, tipos permanentes (adr, architecture, decision…). Correcto que sea fórmula. No hay juicio “este asserted de hace 3 días fue superado por este verified de hoy” más allá del detector de contradicciones que en CLI es NoOp.

## 13. Summarizer — `episodic/summarizer.py` (115)

Sí usa LLM (OpenAI/Anthropic/Ollama) para comprimir logs. Fallback truncate. **Este hueco no es de TypeSafe**: Jev no genera. El summarizer se queda. TypeSafe puede, como máximo, **elegir** si un log merece compress, o scorear el summary resultante contra el log (citation check).

## Resumen

| Hueco | Gravedad | Seam ya existente |
|---|---|---|
| ContradictionDetector NoOp | crítica (escribe vault sucio) | Protocol |
| Intent/DocIntent lexicon | alta (envenena todo retrieval) | `QueryIntentDetector`, `DocIntentDetector` |
| Rerank inexistente | alta (4000 chars de contexto) | post-RRF en `HybridSearch` |
| ADR keywords | media-alta | `suggest_adrs` |
| Autopilot detectors | media-alta | detector protocol |
| Quality stage 2 | media | `review_checkpoint` → 3 literales |
| Brain/MCP routing | media | router + tools catalog |
| Promotion calidad | media | `is_promotable` / review queue |
| Scheduler | baja-media | `_score` |
| Summarizer | n/a para Jev | — |
