# rust/Cargo.toml

## Qué tiene adentro

Manifest del workspace Cargo. Declara `resolver = "2"` y los 22 members en `crates/`. `[workspace.package]` fija version `0.1.0`, edition `2021`, license `MIT`. `[workspace.dependencies]` comparte serde, serde_json, serde_yaml, unicode-normalization, chrono, minijinja, sha2, rmcp 0.8 (server + transport-io), tokio (rt-multi-thread), ureq 3. `[profile.release]` usa LTO thin y un codegen-unit.

Comentarios en el propio archivo anclan cada crate a una fase de migración (P6 actions, P8/P9 setup+MCP, P10 branding+TUI, P12 servicios, Obra 08 companion, Obra 20 brain-app) y reiteran las reglas: core puro, embed ONNX con dim paramétrica, pyo3 grueso, feature `extension-module` no default.

## Para qué sirve

Es el contrato de compilación de la versión nativa. Define qué crates existen, cómo se versionan juntos y qué dependencias externas están aprobadas a nivel workspace.

## Relaciones

### Recibe de
Nada en runtime. Lo editan los crates al agregarse como members.

### Envía a
Cargo/rustc. Cada `crates/*/Cargo.toml` hereda version/edition y puede tomar `workspace.dependencies`.

### Notas de implementación observadas en el código
`cortex-brain-app` aparece como shell Tauri del binario unificado `cortex-brain`. `ureq` se justifica porque ya estaba en el lock (ort-sys).
