# Principio de encaje

## Contrato en una línea

```
Cortex arma el state  →  TypeSafe juzga  →  Cortex ramifica y persiste
```

Jev no entra al ciclo de vida. No abre sesiones, no escribe YAML, no lanza hooks, no mueve files del vault, no spawnea `webgraph serve`. Devuelve un mapa id → {choice|score|noul, probabilities?, confidence?} que un wrapper de Cortex traduce a los tipos que el módulo **ya** consume.

## Reglas (invariantes)

1. **Código dueño del workflow.** Autopilot policies, SessionService, ActionEngine runner, Brain “no muta”, enterprise `assert_can_promote` siguen siendo la ley. TypeSafe no tiene side effects.
2. **Un juicio atómico por question.** “¿Es spam el ticket?” no. Los Noul que Cortex ya tendría que tener (credentials, mismatch, reward) sí. Ver `typesafe/11` step 4: el concepto más importante del guide.
3. **Fan-out, no waterfall.** Todo lo que se puede preguntar contra el state actual va en **un** `system_one`. Segunda call solo si la answer cambia el state (fetch de las 3 skills top, construir bloques que no existían, bajar un nivel de taxonomía).
4. **Filtrar el state antes.** Jev sufre context rot. No mandar el vault. Mandar query + top-N hits, o diff + ADRs candidatos, o checkpoint + spec slice. Cortex ya over-fetchea ×3 y ya tiene budget: usarlo como prefiltro.
5. **Confidence / noul cerca de 0.5 = path que Cortex ya tiene.** Humano, `warn`, `review-required`, `MIXED`, `AmbiguousRequest`, `asserted`. No inventar un cuarto flujo.
6. **No generar.** Writers Jinja, summarizer, llama.cpp, `cortex_write_doc` siguen generando. TypeSafe elige tipo de doc, no escribe el cuerpo.
7. **Determinista cuando se puede.** Paths in-scope, git name-status, BM25, cosine, decay, days_overdue, verification hooks: código. Jev no cuenta, no resta fechas, no hace RRF.
8. **Questions y thresholds en un solo lugar.** El agent skill de TypeSafe lo exige. En Cortex: un módulo (p. ej. futuro `cortex.judgement` / `cortex-judgement`) con las questions versionadas, no strings inline en 12 crates.
9. **Pinnear modelo en producción.** `jev-1.13.0`, no `jev-latest`, el día que los umbrales se calibren contra datos del vault. Loguear `response.model`.
10. **Opt-in.** Feature flag. Paridad Python/Rust: el oráculo Python puede seguir sin Jev; el nativo también. Un backend `NoOpJudgement` equivalente a `NoOpContradictionDetector` hasta que el experimento gane.

## Traducción de primitivas al vocabulario Cortex

| TypeSafe | En Cortex se parece a | No confundir con |
|---|---|---|
| Choice | enum que ya ramifica (QueryIntent, ReviewVerdict.action, detector kind, MemoryType, DocType) | un string generado |
| Score | ranking / budget / prioridad (severity, complexity, report_quality) | `UnifiedHit.score` de RRF (ese se queda) |
| Noul | boolean con incertidumbre (contradicts, is_promotable, needs_tool, claim_supported) | `MemoryEntry.confidence` enum — se *alimenta* del noul, no se reemplaza el campo sin migración |
| TypeSafe `confidence` | segundo eje para actuar o no | DomainDetector “confidence” de reglas; RRF score; decay score |
| `probabilities` | beam search, segundo equipo a notificar, features para un modelo clásico | — |

## Dónde se inyecta (seams, no rewrites)

Los seams que ConaISI ya nombra:

- `QueryIntentDetector.detect(query) -> IntentResult`
- `DocIntentDetector.detect(query) -> DocIntentResult`
- `HybridSearch.search` *después* del RRF (nueva etapa, no reemplazo)
- `ContradictionDetector.find_contradictions(...)` (Protocol; hoy NoOp)
- `suggest_adrs(checkpoints, diff_text)`
- `review_checkpoint(checkpoint, spec) -> ReviewVerdict`
- detector protocol de Autopilot (`detect(request) -> DetectionResult`)
- `route_intent(texto)` del Brain
- `PromotionRulesEngine.is_promotable` / review queue
- `Scheduler._score` / `propose`
- `AgentMemory.remember` (clasificar antes de persistir)

Cada seam recibe un backend. El backend TypeSafe implementa la misma firma y por dentro arma `state` + `questions`. Tests de paridad del seam (mismos tipos de salida) siguen verdes; tests de *calidad* del backend son evals nuevos.

## Relación con el Brain y con los agentes IDE

TypeSafe no es el Brain. El Brain es un LLM local que **habla** y llama tools READ. TypeSafe es un juez que esas tools (y el CLI, y el MCP) pueden consultar.

Los agentes IDE (Claude Code, Cursor, Pi…) ya hablan MCP. No necesitan saber que existe Jev. `cortex_search` / `cortex_context` / `cortex_finish_session` mejoran por dentro. Eso es el win de producto: 11 IDEs ganan sin cambiar adapters.

El único lugar donde un utterance del usuario llega crudo a TypeSafe es el Brain (y el Companion). Ahí sí: Choice de intent + skill suggestion sobre tools, y llama.cpp solo si el Choice dice `conversation`.
