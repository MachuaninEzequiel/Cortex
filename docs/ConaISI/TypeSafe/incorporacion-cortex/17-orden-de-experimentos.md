# Orden de experimentos

Nada de esto vive en `cortex/` hasta que el experimento gane. El directorio `/home/chucho/TypeSafeAI` (o un subdir de este árbol, si se prefiere no mezclar) es el laboratorio. Cortex se **lee** (export de queries/hits), no se escribe.

## Principio

Un purpose por vez. Flag `shadow` primero. Métrica antes de `on`. Si no hay lift, no se encadenan más purposes: la tesis del multiplicador se testea en retrieval.

## Experimento 0 — sanity del cliente

- Call `POST /v1/systemone` con el ticket Stripe de la docs.
- Verificar `choice` / `score` / `noul` / `usage`.
- Medir latencia p50/p95. Esperado: ~100–300 ms, no segundos.
- Verificar 401 sin key, 422 con question malformada.

Si esto falla, no hay incorporación.

## Experimento 1 — rerank de `unified_hits` (go/no-go del producto)

1. Exportar de un repo real con vault Cortex: N queries (20–40) que un humano ya hizo o haría (`how does X`, `what did we decide about Y`, `runbook for Z`).
2. Para cada query, dump de `HybridSearch.search` actual (top 30).
3. Label humano: ids que deberían estar en top 5, y el #1 ideal.
4. Correr Jev: Noul `rel_{id}` por candidato, un call por query (fan-out).
5. Comparar nDCG@5, Recall@5, hit@1 vs baseline RRF.

Criterio de seguir:

- Lift claro en hit@1 o nDCG@5 (el cookbook CLERC: 5→18 y 38→62; no se espera copiar esos números, sí un lift no trivial).
- p95 latencia aceptable para CLI/MCP (< 500 ms extra, ideal < 200).
- Costo por query despreciable (input tokens × $0.042/MTok).

Si no hay lift: parar. No tiene sentido Autopilot ni documenter encima de un juez que no rankea.

Modo shadow en Cortex (si algún día se mergea): loguear ranking Jev vs ranking RRF, no cambiar lo que ve el agente.

## Experimento 2 — intent vs lexicon

Mismo set de queries, label EPISODIC/SEMANTIC/MIXED. Comparar `QueryIntentDetector` vs Choice TypeSafe. Métrica: accuracy y, más importante, **downstream nDCG** cuando se usan esos pesos en RRF.

Si TypeSafe gana en accuracy pero no en nDCG, el lexicon basta y no se toca.

## Experimento 3 — ContradictionDetector sobre finishes reales

Tomar 10–20 `finish-session` pasados (diff + ADRs del vault). Humano: ¿había contradicción? Comparar NoOp (cero) vs Jev. Precisión/recall de findings. False positives son caros (asusta al finish); umbral conservador.

Si recall alto con precision aceptable: implementar el Protocol. Es el primer write-path.

## Experimento 4 — Autopilot detectors

Utterances reales (si hay logs) o un set sintético pero **literal** (jaggedness: Jev es literal; el set tiene que ser lenguaje de humanos, no de la docs). Label task_kind. Comparar vs `default.py`.

## Experimento 5 — Brain router

Utterances del Companion/Brain si existen. Regex vs Choice. Métrica: % routed a tool READ correcta vs caídos a llama.cpp (cada caída cuesta GPU local y latencia).

## Experimento 6 — Promotion ranking

Cola `review-knowledge pending` si hay org. Ordenar por org_knowledge × quality. El reviewer dice si el orden ayuda. No auto-promote en este experimento.

## Explicitamente después (o nunca)

- Skill suggestion de 32 tools (golden MCP intocable; el hint en guidelines es suficiente al principio).
- Guardrails Brain (útil, no es el multiplicador).
- CatBoost sobre probabilities (AutoResearch) — necesita labels de 1–5.
- Semantic lint fail-closed en CI — no.

## Qué se puede hacer mañana sin tocar Cortex

En `/home/chucho/TypeSafeAI`:

1. Cliente Python `typesafe-sdk`.
2. Script que lee un JSONL `{query, candidates[]}` exportado a mano desde `cortex search --json` (si no hay --json, pegar output).
3. Escribe `{query, baseline_order, jev_order, nouls}`.
4. Una planilla de labels.

Eso es el experimento 1. Cero PRs al insignia.
