# Arquitectura de inserción (sin implementar)

Esto es un diseño. Cero código en `cortex/` o `rust/`.

## Dónde vive

Un backend de juicio, no un producto paralelo.

Nombre tentativo (no hay que usarlo): `JudgementBackend` / crate `cortex-judgement`.

```
superficies (CLI, MCP, Brain, TUI, Companion)
        │
   cortex-app / services / autopilot / actions / enterprise
        │
   JudgementBackend ──opt-in──► TypeSafe HTTP (system_one)
        │                        │
        └── NoOp / Lexicon ──────┘  (offline, 429, flag off)
        │
   cortex-core / embed / workspace / disco
```

No cuelga de `cortex-brain`. El Brain es un consumer más. Retrieval, documenter y autopilot no pueden depender de llama.cpp.

## Firma del backend (conceptual)

```text
JudgementRequest
  state: JSON
  questions: map id → {type, instructions, criteria}
  model: pin (jev-1.13.0 en prod)
  timeout
  purpose: retrieval_rerank | intent | contradiction | ...  # para métricas

JudgementResponse
  model_resolved: string
  answers: map id → typed
  usage: {input_tokens, output_tokens}
  backend: typesafe | noop | lexicon
```

Los módulos **no** hablan HTTP. Hablan el Protocol que ya tienen (`ContradictionDetector`, `QueryIntentDetector.detect`, …). Un adapter traduce Protocol → JudgementRequest.

Eso permite:

- tests unitarios del módulo con un backend fake (como `NoOpContradictionDetector`);
- shadow mode (llamar TypeSafe, ignorar answers, loguear);
- paridad Python/Rust: un golden de `JudgementRequest` JSON, no dos clientes divergentes.

## Config

Bloque nuevo en `config.yaml` / `.cortex/config.yaml` (SSoT `CortexConfig` / `cortex-config`):

```yaml
judgement:
  enabled: false          # default: Cortex no requiere red extra
  mode: off | shadow | on
  provider: typesafe
  model: jev-1.13.0       # pin en prod; jev-latest solo en playground
  timeout_ms: 800
  fail: open              # 429/timeout → lexicon/NoOp, nunca fail el search
  questions_path: .cortex/judgement/questions.yaml  # un solo lugar
```

Env: `TYPESAFE_API_KEY` (oficial TypeSafe). No meter la key en `org.yaml`. Doctor check nuevo: “judgement.enabled y no hay key” = warn, no fail (doctor es offline-friendly).

## Un solo archivo de questions

El agent skill de TypeSafe: *Put the constants (questions and thresholds) in a single place*.

Propuesta: `.cortex/judgement/questions.yaml` versionado en el repo de Cortex (defaults) + override por workspace. IDs estables. Thresholds nombrados (`τ_intent`, `τ_drop`, `τ_contradict`). Review humano = ese archivo, no un grep por el monorepo.

## Cliente HTTP

- Python: `typesafe-sdk` (`TypeSafeClient`) cuando el caller es el paquete 0.7.0.
- Rust: HTTP directo (`ureq` ya está en brain/download) o un crate fino. **No** FFI al SDK Python: el CLI nativo no delega a Python (`CORTEX_PY=1` avisa y sigue nativo). Un client Rust propio mantiene ese invariante.
- Retries: copiar la semántica del SDK (backoff, `retry-after`, 429 y 529). No inventar otra policy.

## Cache

Opcional, por hash(state canónico + questions ids + model). Retrieval de la misma query en el mismo segundo (CLI y MCP) no paga dos veces. No cachear finish/contradictions (el diff cambia). TTL corto. Invalidar no es crítico: es un juicio, no un store.

## Telemetría

JSONL al lado de enrichment-events: `.cortex/judgement-events.jsonl`. Campos: purpose, model, input_tokens, latency_ms, backend, answers compactas (ids + noul/choice/confidence, **no** el state: puede tener secretos de diffs). Bodies TypeSafe no se redactan en el SDK debug — **no loguear bodies en debug default de Cortex**.

## Feature flags por purpose

```yaml
judgement:
  purposes:
    retrieval_rerank: shadow
    query_intent: off
    contradictions: off
    autopilot: off
    brain_router: off
    promotion: off
```

El experimento 1 prende solo `retrieval_rerank`. Nada más. Ver `17`.

## Dependencias nuevas

Python extra: `typesafe-sdk` **opcional** (como `openai`, `flask`). Rust: no llama Python. Workspace no se vuelve “requiere TypeSafe para compile”: el crate judgement es opcional / feature.

## Relación con `cortex-py` / `_native`

Ninguna. `_native` es cosine/BM25/store. Jev no entra al binario de vectores.
