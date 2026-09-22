# Estructura de `rust/crates/cortex-core`

Crate de dominio puro. `Cargo.toml` declara una sola dependencia: `rayon`. No depende de PyO3 ni de otros crates Cortex. Compila y se testea offline.

```
cortex-core/
├── Cargo.toml
└── src/
    ├── lib.rs
    ├── scoring.rs
    ├── store.rs
    ├── bm25.rs
    └── webgraph.rs
```

Módulos públicos reexportados desde `src/lib.rs`: `bm25`, `scoring`, `store`, `webgraph`. Constante `VERSION` = `CARGO_PKG_VERSION` (`0.1.0` del workspace).

Relación externa: `cortex-py` lo consume vía FFI; `cortex-app` y `cortex-webgraph-server` lo usan como librería nativa.
