# Estructura de `rust/crates/cortex-app`

Capa de aplicación nativa. Portea servicios Python (sesión, documenter, retrieval híbrido, CI, workitems, PR). `#![forbid(unsafe_code)]`. Dependencias Cortex: `cortex-embed` (onnx), `cortex-setup`, `cortex-config`, `cortex-core`.

```
cortex-app/
├── Cargo.toml
├── src/
│   ├── lib.rs
│   ├── git.rs
│   ├── security.rs
│   ├── reindex.rs
│   ├── pr.rs
│   ├── workitems.rs
│   ├── doc_generator.rs
│   ├── doc_validator.rs
│   ├── doc_verifier.rs
│   ├── ci/
│   │   ├── mod.rs
│   │   ├── diff_io.rs
│   │   ├── markdown_formatter.rs
│   │   ├── result.rs
│   │   ├── review_session.rs
│   │   ├── session_matcher.rs
│   │   └── validator.rs
│   ├── context/
│   │   ├── mod.rs
│   │   ├── budget_resolver.rs
│   │   ├── cooccurrence.rs
│   │   ├── decay.rs
│   │   ├── doc_intent.rs
│   │   ├── domain_detector.rs
│   │   ├── feedback.rs
│   │   ├── filters.rs
│   │   ├── hybrid.rs
│   │   ├── intent.rs
│   │   ├── models.rs
│   │   ├── observer.rs
│   │   ├── presenter.rs
│   │   ├── pyjson.rs
│   │   └── telemetry.rs
│   ├── documenter/
│   │   ├── mod.rs
│   │   ├── diff_parser.rs
│   │   ├── handoff.rs
│   │   ├── interactive.rs
│   │   ├── persister.rs
│   │   └── spec_loader.rs
│   ├── episodic/
│   │   ├── mod.rs
│   │   └── entities.rs
│   ├── semantic/
│   │   ├── mod.rs
│   │   ├── parser.rs
│   │   ├── chunker.rs
│   │   └── routing.rs
│   └── session/
│       ├── mod.rs
│       ├── quality_gates.rs
│       ├── service.rs
│       └── verification.rs
├── examples/          # checkers de paridad (binarios)
└── tests/
    └── compute_diff.rs
```

Consumidores: `cortex-cli`, `cortex-mcp`, `cortex-actions`, `cortex-autopilot`, `cortex-companion`, `cortex-doctor`, `cortex-enterprise`, `cortex-pipeline`, `cortex-services`, `cortex-tui`, `cortex-webgraph-server`.
