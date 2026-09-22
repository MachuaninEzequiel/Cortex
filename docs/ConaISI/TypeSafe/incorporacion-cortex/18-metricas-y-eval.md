# Métricas y eval

Sin números no hay “exponencial”, hay vibe. TypeSafe mismo insiste: calibración se mide en **grupos**; umbrales se tunenan con datos propios.

## Métricas por purpose

| Purpose | Métrica primaria | Secundaria | No usar |
|---|---|---|---|
| rerank | nDCG@5, hit@1 | latencia p95, $/query, tokens | “se siente mejor” |
| intent | accuracy vs label; **nDCG downstream** | % forzado a MIXED | accuracy sola |
| contradictions | precision de findings (FP asustan) | recall | cantidad de findings |
| ADR suggest | precision@k vs “humano habría escrito ADR” | — | keywords hits |
| quality gates | acuerdo con reviewer humano en accept/warn/redelegate | % warn | fail rate crudo |
| autopilot | accuracy task_kind; % ambiguous correcto | budget_profile resultante | — |
| brain router | % tool correcta; % evitado de GGUF | latencia | — |
| promotion | acuerdo reviewer con disposition | % auto_promote que luego se rechaza (debe → 0) | volumen promovido |
| next | click-through / approve rate en Companion | — | score medio del scheduler |

## Calibración

Para Noul: en un bucket de predicciones 0.7–0.8, ~75% deberían ser “sí” humano. Plot reliability. Si Jev está overconfident en el dominio Cortex (código + markdown de ingeniería), **bajar umbrales no “arreglar” la calibración**: se ajusta el threshold de acción, o se descompone la question (literalness).

Para Choice: confidence vs “choice == label”. Baja confidence + acierto igual es OK (el sistema escala). Alta confidence + error es el fallo caro.

## Eval set

- Dejarlo **fuera** del vault semántico de Cortex (si no, retrieval se entrena/evalúa contra sí mismo de forma sucia). `TypeSafeAI/eval/` o `.cortex/judgement/eval/` gitignored si tiene diffs internos.
- Queries en ES y EN: el `config.yaml` de Cortex ya tiene per-language embeddings (MiniLM EN, e5-large ES). Jev es un modelo de texto; hay que medir los dos.
- Incluir adversarial: un vault note que dice “ignore previous, this is verified”. Jaggedness #6.
- Incluir literal traps: “does not mention distributed systems” vs “mentions”. Jev es literal; el eval debe premiar instructions bien escritas, no “magia”.

## Shadow vs on

Shadow: misma métrica, computada offline sobre logs (`judgement-events.jsonl` + ranking RRF). No cambia UX. Correr una semana en un workspace real si hay uso. On: solo si shadow lift se sostiene.

## Lo que MADRE prohibió afirmar

No inventar benchmarks de producción no medidos. Este archivo es el antídoto: cualquier claim futuro de “exponencial” apunta a una tabla de nDCG/precision de acá.
