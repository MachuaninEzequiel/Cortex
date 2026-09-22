# Arquitectura modular

## Hexágono, no un “módulo TypeSafe” esparcido

TypeSafe es un **puerto**. Cortex ya piensa así: `ContradictionDetector` Protocol, `EmbedderFactory`, `SearchBackend` enterprise, `DocumenterFinalize` de Autopilot. El juicio entra por la misma puerta.

```
                    CLI  MCP  TUI  Brain  Companion
                              │
                         cortex-app
              (retrieval, documenter, session, context)
                              │
                    Option<JudgementClient>
                         ╱              ╲
            None / off              TypesafeClient
         (código actual)            (HTTP system_one)
                         ╲              ╱
                          fail-open ───╝
```

Regla de dependencia:

```
cortex-judgement  ──no conoce──►  UnifiedHit, SessionRecord, ADRSuggestion
cortex-app        ──conoce──►     JudgementClient + sus propios tipos
cortex-core       ──no conoce──►  judgement (BM25/cosine intactos)
cortex-mcp        ──no conoce──►  typesafe (llama a app, como hoy)
cortex-brain      ──conoce──►     JudgementClient solo para route_intent
```

Si `cortex-judgement` importara `UnifiedHit`, el crate dejaría de ser reusable y nacería un ciclo con `cortex-app`. El client habla JSON (`state` + `questions` + `answers`). El **adapter** (vive al lado del consumer) traduce `Vec<UnifiedHit>` → state y answers → reorder.

## El único tipo que cruza la frontera

```text
Purpose = retrieval_rerank | query_intent | contradictions | adr_suggest
        | quality_gate | autopilot | brain_intent | promotion
        | next_action | remember | guardrail

JudgementRequest  { purpose, state: JsonValue, question_ids?: [str] }
JudgementResponse { model, answers: map, usage, backend: typesafe|skipped }
JudgementError    { timeout, http(status), validation, no_key }

trait JudgementClient
    fn enabled(&self, Purpose) -> bool
    fn evaluate(&self, JudgementRequest) -> Result<JudgementResponse, JudgementError>
```

Nada más. Ni `rerank()`, ni `detect_intent()` en el trait. Esas son funciones del adapter en `cortex-app`. Si mañana hay un segundo provider (otro System One, un modelo local), implementa el mismo trait. TypeSafe no es el nombre del puerto; es un adapter.

## Inyección

Mismo estilo que `AgentMemory.__init__` hoy (ficha `raiz/core.md`): la fachada **inyecta**, no reimplementa.

Python:

```text
AgentMemory.__init__:
    ...
    self._judgement = build_judgement_client(config, env)  # None o TypesafeClient

HybridSearch.__init__(..., judgement=None)
ContradictionDetector: TypesafeContradictionDetector(client) | NoOp
AutopilotService(..., judgement=None)
```

Rust:

```text
cortex-app construye Arc<dyn JudgementClient>
lo pasa a HybridSearch, Documenter, AutopilotService
cortex-cli / cortex-mcp / cortex-brain-app reciben el mismo Arc
```

`build_judgement_client`:

```
si !config.judgement.enabled or provider==none or no key:
    return None
si provider==typesafe:
    return TypesafeClient { base_url, key, model, purposes, timeout, catalog }
```

`None` es el modo community. No hay un objeto Passthrough que reimplemente lexicon: **el lexicon nunca se mueve**. Evita dos implementaciones del mismo detector.

## Catálogo de questions (datos, no código)

`.cortex/judgement/questions.yaml` (override de workspace) + defaults embebidos en el crate (`include_str!` / package data).

```yaml
version: 1
model: jev-1.13.0
thresholds:
  intent_mixed_below: 0.50
  rerank_drop_below: 0.25
  contradict_finding_above: 0.70
  ambiguous_above: 0.70
purposes:
  retrieval_rerank:
    mode: off          # off | shadow | on
    questions:
      rel:
        type: noul
        instructions: "Does `candidate.text` answer `query` ..."
        criteria: { true: "...", false: "..." }
```

El adapter de retrieval, para cada hit, instancia `rel_{id}` clonando el template `rel` y sustituyendo el path. El humano reviewa **este YAML**. El agent skill de TypeSafe lo pide: un solo lugar.

Cambiar una instruction no es un PR de Rust. Es un cambio de datos. Versionar `version: 1` por si el schema crece.

## Dónde se ancla cada purpose (un if)

| Purpose | Archivo que gana el `if` | Si None / off |
|---|---|---|
| `query_intent` | `hybrid_search.py` / `context/hybrid.rs` **antes** de RRF | `QueryIntentDetector` actual |
| `retrieval_rerank` | mismo, **después** de RRF | `unified_hits` crudo |
| `contradictions` | `reconstruction.py` paso 5 | `NoOpContradictionDetector` |
| `adr_suggest` | `adr_evaluator.suggest_adrs` | `_DECISION_PATTERNS` |
| `quality_gate` | `quality_gates.review_checkpoint` stage 2 | placeholders / 10 chars |
| `autopilot` | `detectors` resolution | `default.py` |
| `brain_intent` | `cortex-brain/src/router.rs` | `_PATRONES` |
| `promotion` | `PromotionRulesEngine` **después** de ACL | reglas estructurales |
| `next_action` | `Scheduler.propose` **después** de precondiciones | fórmula sola |
| `remember` | `AgentMemory.remember` | tipo/tags del caller |
| `guardrail` | `cortex-brain` chat loop | nada (hoy no hay) |

Cada `if` es local. Encender `retrieval_rerank` no enciende `contradictions`. Eso es la palanca `purposes.*.mode`.

## Orden de encendido recomendado (producto)

No prender los 11. El binario los *tiene*; el default YAML los deja `off`.

v1 shippable: `retrieval_rerank` (y opcional `query_intent`) + doctor/setup/status.
v1.1: `contradictions` + `adr_suggest` (write path).
v1.2: `autopilot` + `brain_intent`.
v1.3: `quality_gate`, `next_action`, `promotion`.
Nunca default-on para `guardrail` fail-closed ni CI fail.

## Paralelismo interno

Un `evaluate()` = un HTTP `system_one` = N questions en paralelo **dentro** de TypeSafe. Cortex no spawnea N HTTP. El adapter de rerank arma **un** request con 15–30 nouls. Eso es la modularidad de costo: el fan-out es de ellos, no un thread pool nuestro.

## Lo que queda fuera del crate

- Embeddings, BM25, RRF, decay, layout, MCP catalog, Jinja, llama.cpp.
- ACL enterprise (`assert_can_promote`) **antes** del client.
- Git diff slice **antes** del client.
- Contar files / hours_old **antes** del client.

El crate no “entiende Cortex”. Entiende system_one. Por eso se puede testear con un mock HTTP y un JSON de la docs de TypeSafe, sin vault.
