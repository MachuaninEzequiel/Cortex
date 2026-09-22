# ActionEngine (`cortex next`)

Módulos: `cortex/action_engine/{catalog,scheduler,signals,learning,runner}.py`, `cortex-actions`, CLI `next`, TUI Home, Companion `actions_screen` approve/deny, Brain `actions.propose` (Read).

Ciclo Obra 05: OBSERVAR → PROPONER → APROBAR → EJECUTAR → APRENDER. Las acciones delegan a servicios existentes (no reimplementan). Log JSONL.

## Scheduler actual

Precondiciones booleanas + preferencias. `score = impacto × frescura − costo`. Top 5 (`MAX_VISIBLE_DEFAULT`). Signals de memoria, ventana 14 días (fechas = código). `explain_why_not` lista precondiciones fallidas.

Catálogo (ficha + contexto/04): setup_finish_bootstrap, session_close_stale, session_checkpoint_now, vault_reindex, vault_validate_docs, quality_run_gates, learn_topic, knowledge_promote, memory_prune, ide_resync, session_suggest_next_phase.

## Qué no reemplazar

La fórmula. Las precondiciones (sesión open, git dirty, vault desindexado). El runner. El approval humano (Companion / HERDR `run_guarded`). Brain sigue **proponiendo**, no ejecutando.

14 días de signals: `hours_old` en código, no Jev.

## Qué agregar: veto / reorder semántico sobre las candidatas que **ya pasaron** precondiciones

State:

```json
{
  "session": {"status": "open", "age_hours": 36, "has_uncommitted": true, "spec_title": "..."},
  "vault": {"docs_invalid": 2, "last_index_hours": 80},
  "signals_14d": {"category_counts": {"session": 12, "incident": 1}},
  "candidates": [
    {"id": "session_close_stale", "why_eligible": "open > N hours, no checkpoint"},
    {"id": "vault_validate_docs", "why_eligible": "invalid docs > 0"}
  ]
}
```

`age_hours` lo calcula código. Jev lee el número ya computado (jaggedness: pasar el bucket, no pedir que reste fechas).

Por candidata:

```text
Noul appropriate_now_{id}
  "Given this project state, is this the right next action for the human or agent to take now?"
  criteria:
    true: unblocks work or prevents knowledge loss, and is not redundant with a more urgent candidate
    false: technically eligible but the wrong priority or would interrupt in-flight work
```

Código:

```text
score_final = scheduler_score * appropriate.noul
si appropriate < 0.35 → no mostrar (explain_why_not += "judgement: not appropriate now")
ordenar por score_final, top 5
```

Composite scoring: se **preserva** el score interpretable del scheduler y se multiplica por un noul. Si el ranking no matchea lo que el dueño haría, se tocan pesos de impacto (ya existen `IMPACTO_BASE`) o el umbral de noul, no un prompt de 40 líneas.

## Learning v0

`learning.py` (27 líneas) es un paso APRENDER mínimo. Las probabilities de `appropriate_now` son features para un modelo clásico (cookbook AutoResearch + CatBoost) el día que haya labels de approve/deny del Companion. No hace falta para v1. El store de preferencias ya existe.

## Mejora

`cortex next` y el Home de la TUI dejan de proponer `vault_reindex` en medio de un Deep Track porque el índice tiene 80 horas. El noul ve la sesión in-flight. El dueño sigue aprobando. Brain sigue sin mutar.
