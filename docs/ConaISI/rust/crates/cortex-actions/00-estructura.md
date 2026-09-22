# rust/crates/cortex-actions — estructura interna

Puerto 1:1 de `cortex/action_engine/`. Ciclo OBSERVAR → PROPONER → APROBAR → EJECUTAR → APRENDER.

```
cortex-actions/
├── Cargo.toml
├── examples/actions_check.rs
└── src/
    ├── lib.rs
    ├── models.rs        # Action, Check, Costo, Categoria, Trigger, Decision
    ├── catalog.rs       # 10 acciones v1 + session.suggest_next_phase
    ├── context.rs       # ActionContext (rutas, sesiones)
    ├── registry.rs
    ├── scheduler.rs     # ranking, MAX_VISIBLE_DEFAULT=5
    ├── runner.rs        # dry-run, aprobación, log
    ├── store.rs         # action_log.jsonl + actions.yaml
    ├── learning.rs
    ├── metrics.rs
    └── signals.rs       # señales de memoria 14 días
```

## Catálogo registrado en `build_default_registry` (orden)

1. `setup.finish_bootstrap`
2. `session.close_stale`
3. `session.checkpoint_now`
4. `vault.reindex`
5. `vault.validate_docs`
6. `quality.run_gates`
7. `learn.topic`
8. `knowledge.promote`
9. `memory.prune`
10. `ide.resync`
11. `session.suggest_next_phase` (appendeada; no altera el orden de desempate de las 10)

Contratos en `lib.rs`: delegación a servicios, precondiciones antes de ofrecer, `reversible=false` ⇒ aprobación siempre, log en `.cortex/action_log.jsonl`, dry-run nativo.

## Relaciones

- **Recibe de:** `cortex-app` (session, reindex, doc_validator, quality_gates, episodic store), `cortex-setup` (templates/IDE), `cortex-enterprise` (promoción).
- **Envía a:** `cortex-cli` (`next`), `cortex-companion`, `cortex-tui`, archivos `.cortex/action_log.jsonl` y `.cortex/actions.yaml`.
