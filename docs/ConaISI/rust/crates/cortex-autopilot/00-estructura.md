# rust/crates/cortex-autopilot — estructura interna

Puerto de `cortex.autopilot`: capa de decisión + orquestación de sesión.

```
cortex-autopilot/
├── Cargo.toml
├── examples/cierre_autopilot_check.rs
├── src/
│   ├── lib.rs
│   ├── config.rs          # autopilot.yaml, default mode=assist, budget=fast_code
│   ├── errors.rs
│   ├── models.rs          # DetectionRequest/Result, TASK_TYPES
│   ├── session_models.rs
│   ├── lifecycle.rs       # AutopilotStartRequest, PreflightResult
│   ├── policies.rs        # AutopilotMode, PolicyEnforcer
│   ├── service.rs         # start/preflight/checkpoint/finish/status
│   └── detectors/
│       ├── mod.rs         # AutopilotDetector, default_detectors(), resolve_detectors
│       ├── ambiguous.rs
│       └── default.rs     # code/docs/question/security/refactor/noop
└── tests/decision_layer.rs
```

Detectores canónicos (orden Python): ambiguous → question-only → docs-only → security → large-refactor → code-change → noop.

`finish` con documenter exige `DocumenterFinalize` inyectado; sin él falla explícito.

## Relaciones

- **Recibe de:** `cortex-app::session`, `cortex-workspace`, `cortex-enterprise` (errores/clock), `cortex-mcp` (dep Cargo).
- **Envía a:** `cortex-cli autopilot`, handlers MCP autopilot.
