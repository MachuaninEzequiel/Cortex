# Estructura interna — `rust/crates/cortex-services`

Servicios de dominio P12A-5/P12A-6: crear specs, crear notas de sesión con rollback, migrar bóvedas legacy al esquema canónico.

Dependencias: `chrono`, `cortex-app`, `cortex-setup`, `serde`, `serde_json`, `serde_yaml`, `regex`, `uuid` (v4).

```
cortex-services/
├── Cargo.toml
├── examples/
│   ├── p12a5_check.rs
│   └── p12a6_check.rs
└── src/
    ├── lib.rs
    ├── spec.rs
    ├── note.rs
    └── migration.rs
```

## Puertos (hexagonal)

Definidos en `lib.rs`:

- `EpisodicPort::add` — memoria episódica.
- `SemanticPort::index_file` / `sync` — índice semántico (rollback).
- `SessionOpener::open` — abre Session tras crear spec (impl para `cortex_app::session::service::SessionService`).

Persistencia común: `persist_note` llama `cortex_setup::writers::build_note` e implementa idempotencia por fingerprint + error de duplicado.

## Relación con el lote 2

- CLI `docs migrate/validate/restore` → `migration`.
- MCP `NativeSpecBackend` → `SpecService`.
- MCP finish/docs y CLI finish no instancian NoteService directamente en todos los caminos; el writer canónico de setup sí.
