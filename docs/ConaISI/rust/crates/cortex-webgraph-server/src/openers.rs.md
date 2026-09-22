# rust/crates/cortex-webgraph-server/src/openers.rs

## Qué tiene adentro

Porteo de `cortex/webgraph/openers.py`.
Archivo de 34 líneas.
Símbolos públicos observados:
- `pub fn resolve_safe_vault_path(vault_root: &Path, relative_path: &str) -> Result<PathBuf, String>`
- `pub fn open_path(path: &Path)`

## Para qué sirve

Porteo de `cortex/webgraph/openers.py`.

## Relaciones

### Recibe de

- `use cortex_workspace::layout::resolve_lexical`
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/openers.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
