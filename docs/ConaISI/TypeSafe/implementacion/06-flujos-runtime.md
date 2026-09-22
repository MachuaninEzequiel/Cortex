# Flujos runtime (con y sin API)

Cada flujo: izquierda community, derecha judgement on. El recuadro `if` es el único gancho.

---

## Search / context (v1, el que se implementa primero)

```
                    cortex search | cortex_context | MCP cortex_search
                                      │
                         QueryIntentDetector lexicon
                                      │
                    VaultReader.search + Episodic.search   (over-fetch ×3)
                                      │
                                   RRF k=60
                                      │
                    ┌─────────────────┴─────────────────┐
                    │ judgement is None or purpose off  │
                    │ o fail-open                       │
                    └─────────────────┬─────────────────┘
                                      │ sí
                                      ▼
                              unified_hits actual
                                      │
                    ┌─────────────────┴─────────────────┐
                    │ enabled(retrieval_rerank)==on     │
                    └─────────────────┬─────────────────┘
                                      │ sí
                         adapter arma state {query, candidates[0..15]}
                         client.evaluate(purpose=retrieval_rerank)
                                      │
                         ┌────────────┼────────────┐
                         │ timeout/429│ 200 OK     │ shadow
                         ▼            ▼            ▼
                      hits RRF    reorder/drop   hits RRF
                                  por noul       + log jsonl
                                      │
                                      ▼
                         to_prompt / TUI / MCP result
```

Latencia extra solo en la rama derecha: ~100–200 ms + red. Community: 0 ms extra.

`cortex_context` después sigue con enricher, budget, presenter. Si más adelante `query_intent` está on, el lexicon se salta **antes** del RRF (segunda palanca, otro if). v1 puede no prenderlo.

---

## Finish / documenter

```
Reconstructor pasos 1–4 (spec, diff, hooks, scope)     ← idénticos
      paso 5 find_contradictions(detector)
                    │
         detector is NoOp? ──sí──► []          (community / purpose off)
                    │no
         search ADRs top 8 (HybridSearch, modo A o B da igual)
         evaluate(contradictions)
         map nouls → ContradictionFinding[]
      pasos 6–8 handoff, status, suggest_adrs
                    │
         adr_suggest off? ──sí──► _DECISION_PATTERNS
                    │no
         evaluate(3 nouls) → ADRSuggestion[]
      Persister escribe notas + confidence tri-estado
```

Community: paso 5 vacío, ADRs keyword. Nadie se entera de TypeSafe.

---

## Autopilot start

```
DetectionRequest
    │
    purpose autopilot off? ──sí──► detectors/default.py  (community)
    │no
    evaluate(task_kind, complexity, needs_clarification, touches_secrets)
    map → DetectionResult
    │
Policies + budget_profile     ← no se tocan
Lifecycle start/preflight/...
```

---

## Brain utterance

```
slash command? ──sí──► tool READ, 0 Jev, 0 GGUF
    │no
purpose brain_intent off? ──sí──► router regex (community)
    │no
evaluate(Choice brain_intent)
    confidence baja o conversation → llama.cpp (si feature llama)
    otro → tools.rs dispatch READ
```

Community Brain: regex como hoy. Judgement: menos GGUF. Guardrail es otro if *dentro* del path llama.cpp, default off.

---

## next / ActionEngine

```
precondiciones + score fórmula          ← siempre
    │
purpose next_action off? ──sí──► top 5 fórmula (community)
    │no
evaluate(noul por candidata)
score_final = fórmula * noul
filtrar noul < 0.35
top 5
```

Approval Companion: igual.

---

## Promote

```
ACL assert_can_promote                  ← siempre, código
RouteSpec.promotion_mode                ← siempre
    │
purpose promotion off? ──sí──► is_promotable estructural
    │no
evaluate(disposition, org_knowledge, ...)
mode review-required gana a auto_promote
```

---

## Arranque del proceso (CLI / MCP / Brain-app)

```
load WorkspaceLayout
load CortexConfig          # bloque judgement ausente → defaults disabled
build_judgement_client()
    enabled false o no key → None
    else TypesafeClient { catalog from default.yaml ∪ override }
inject Arc<Option<Client>> en app/services
serve / run command
```

Un MCP de larga vida reusa el client (connection pool ureq/sdk). No un TCP por tool call más allá de HTTP keep-alive.

---

## Fallos

| Evento | Qué ve el usuario |
|---|---|
| 401 | doctor: key inválida; search modo A; stderr warn una vez |
| 429 / 529 | search modo A esta call; status cuenta skip |
| timeout 800 ms | modo A esta call |
| YAML questions corrupto | doctor fail de check judgement; **no** se prende B; modo A |
| sin red | modo A |
| purpose on, feature cargo sin typesafe | compile no incluye client → enabled se ignora, doctor warn “binary without typesafe feature” |

Nunca: lista de hits vacía por culpa de Jev. Nunca: sesión que no cierra. Nunca: MCP tool que tira 500 porque TypeSafe está down.

---

## Resumen de anclaje

1. Un crate `cortex-judgement` (HTTP + catálogo).
2. `Option<Client>` inyectado como el resto de infraestructura.
3. Un `if` por purpose, default off.
4. Adapters al lado del consumer, no al revés.
5. Config ausente ≡ community.
6. Fail-open.
7. MCP/TUI/Brain no se rediseñan.
8. El gasto de v1, en uso real de agente, es **centavos al mes**; el valor es ahorrar turnos del LLM caro.

Eso es el Cortex nuevo: el de siempre, con un motor de juicio que se enchufa cuando hay key y se desaparece cuando no.
