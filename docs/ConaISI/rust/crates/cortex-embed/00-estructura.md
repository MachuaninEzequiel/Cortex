# Estructura de `rust/crates/cortex-embed`

Wrapper de inferencia ONNX. Feature `onnx` activa `ort` + `tokenizers`.

```
cortex-embed/
├── Cargo.toml
├── examples/
│   └── g5_spike.rs
└── src/
    ├── lib.rs
    └── onnx.rs          # solo compilado con feature onnx
```

Consumido por `cortex-py` (feature `onnx`) y `cortex-app` (dependencia con `features = ["onnx"]`).
