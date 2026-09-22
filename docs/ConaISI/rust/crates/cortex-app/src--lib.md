# src/lib.rs

## Qué tiene adentro

Raíz del crate. `#![forbid(unsafe_code)]`. Módulos públicos: `ci`, `context`, `doc_generator`, `doc_validator`, `doc_verifier`, `documenter`, `episodic`, `git`, `pr`, `reindex`, `security`, `semantic`, `session`, `workitems`.

`BUILD_TAG = concat!("cortex-app ", CARGO_PKG_VERSION)`. Test smoke: el tag empieza con `"cortex-app "`.

El comentario lista fases: P0 scaffolding, P2a semantic, P3 episódica, P4 sessions, P5 documenter, P7 context.

## Para qué sirve

Exportar la API de aplicación. El binario `cortex` (crate `cortex-cli`) y el MCP la consumen.

## Relaciones

### Recibe de

- Submódulos del crate.

### Envía a

- `cortex-cli`, `cortex-mcp`, `cortex-companion`, etc.

### Notas de implementación observadas en el código

El comentario menciona ActionEngine y setup: ActionEngine vive en `cortex-actions`; setup en `cortex-setup`. Este crate no declara esos módulos.
