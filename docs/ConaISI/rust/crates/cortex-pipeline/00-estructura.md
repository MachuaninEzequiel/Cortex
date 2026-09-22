# rust/crates/cortex-pipeline — estructura interna

Puerto de `cortex.pipeline`: stages con gates + generador GitHub Actions.

```
cortex-pipeline/
├── Cargo.toml
├── examples/{pipeline_check,documentation_gate}.rs
├── src/
│   ├── lib.rs
│   ├── orchestrator.rs          # PipelineOrchestrator + trait PipelineStage
│   ├── domain/{mod,types,context}.rs
│   ├── stages/{mod,lint,test,security,documentation}.rs
│   └── runners/{mod,github}.rs
└── tests/{pipeline_core,documentation_stage}.rs
```

`StageType` / `StageStatus` / `StageResult` / `PipelineReport` / `PipelineContext`. Stages de lint/test/security corren comandos (`run_command` en `stages/mod.rs`). `DocumentationStage` valida docs.

## Relaciones

- **Recibe de:** `cortex-enterprise`, `cortex-app`, `cortex-services`, `cortex-workspace`.
- **Envía a:** `PipelineReport`; YAML de GitHub Actions (`GitHubActionsRunner`).
