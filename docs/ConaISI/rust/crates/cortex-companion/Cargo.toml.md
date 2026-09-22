# rust/crates/cortex-companion/Cargo.toml

## Qué tiene adentro

Archivo de 61 líneas.
G-B1 / documento de diseño: cortex-companion inyecta los MISMOS servicios que usa el CLI ⇒ paridad byte-a-byte POR CONSTRUCCIÓN. Desviación consciente vs la lista del plan (G-B1 del plan): se agrega cortex-cli como librería porque es el ÚNICO glue nativo de retrieval existente (NativeMemory + pyjson + paths). La alternativa era duplicar ~250 LOC de lógica de apertura/retrieval con riesgo de drift — rechazada. B7: ts del feedback en el formato exacto del oráculo (`datetime.now(UTC).isoformat(timespec="milliseconds")`). chrono YA está en Cargo.lock (workspace dep de cortex-app) — cero paquetes nuevos. G-B2a: app mouse-first. ratatui 0.30 + crossterm 0.29 ya están en Cargo.lock (usados por cortex-tui) — cero paquetes nuevos. B8: backend LLM real del brain (llama.cpp/GGUF) — passthrough OPCIONAL,
Manifiesto Cargo. Líneas de deps Cortex observadas:
- `cortex-cli = { path = "../cortex-cli" }`
- `cortex-actions = { path = "../cortex-actions" }`
- `cortex-app = { path = "../cortex-app" }`
- `cortex-config = { path = "../cortex-config" }`
- `cortex-workspace = { path = "../cortex-workspace" }`
- `cortex-branding = { path = "../cortex-branding" }`
- `cortex-brain = { path = "../cortex-brain" }`
- `path = "src/lib.rs"`
- `path = "src/bin/companion.rs"`
- `path = "src/bin/sidecar.rs"`
- `path = "src/bin/float.rs"`
- `path = "src/bin/copilot.rs"`
Nombres de package/bin: cortex-companion, cortex_companion, cortex-companion, cortex-herdr-sidecar, cortex-herdr-float, cortex-herdr-copilot

## Para qué sirve

G-B1 / documento de diseño: cortex-companion inyecta los MISMOS servicios que usa el CLI ⇒ paridad byte-a-byte POR CONSTRUCCIÓN. Desviación consciente vs la lista del plan (G-B1 del plan): se agrega cortex-cli como librería porque es el ÚNICO glue nativo de retrieval existente (NativeMemory + pyjson + paths). La alternativa era duplicar ~250 LOC de lógica de apertura/retrieval con riesgo de drift — rechazada. B7: ts del feedback en el formato exacto del oráculo (`datetime.now(UTC).isoformat(timespec="milliseconds")`). chrono YA está en Cargo.lock (workspace dep de cortex-app) — cero paquetes nuevos. G-B2a: app mouse-first. ratatui 0.30 + crossterm 0.29 ya están en Cargo.lock (usados por cortex-tui) — cero paquetes nuevos. B8: backend LLM real del brain (llama.cpp/GGUF) — passthrough OPCIONAL,

## Relaciones

### Recibe de

- Sin imports Cortex en el extracto (manifiesto, lock, html, gitignore o JSON).

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/Cargo.toml`. 61 líneas.
