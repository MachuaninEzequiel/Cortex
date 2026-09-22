# Estructura de `rust/crates/cortex-config`

Porteo serde de la configuración de `cortex/core.py`. Sin crates Cortex hermanos.

```
cortex-config/
├── Cargo.toml
├── src/
│   └── lib.rs
└── tests/
    └── parity_fixtures.rs
```

Consumido por `cortex-app` (reindex, y otros callers de `CortexConfig`) y `cortex-cli`.
