# Estructura de `rust/crates/cortex-py`

Fachada PyO3. Compila `cdylib`+`rlib` con nombre `_native`. Maturin publica `cortex_core._native`.

```
cortex-py/
├── Cargo.toml
├── pyproject.toml
├── cortex_core/
│   └── __init__.py
└── src/
    └── lib.rs
```

No hay lógica de dominio aquí: solo adaptación de tipos hacia `cortex-core` y `cortex-embed`.
