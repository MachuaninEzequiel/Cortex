# rust/crates/cortex-webgraph-server/src/federation.rs

## Qué tiene adentro

Porteo de `cortex/webgraph/federation.py` — grafo federado multi-proyecto.
Archivo de 412 líneas.
Símbolos públicos observados:
- `pub struct WorkspaceProject`
- `pub fn default_workspace_file(`
- `pub fn resolve_workspace_file(`
- `pub fn write_workspace_file(workspace_file: &Path, projects: &[WorkspaceProject]) -> PathBuf`
- `pub fn load_workspace_projects(workspace_file: &Path) -> Vec<WorkspaceProject>`
- `pub struct FederatedWebGraphService`
- `pub(crate) fn prefixed(project_id: &str, item_id: &str) -> String`
- `pub(crate) fn split_prefixed(value: &str) -> (String, String)`

## Para qué sirve

Porteo de `cortex/webgraph/federation.py` — grafo federado multi-proyecto.

## Relaciones

### Recibe de

- `use crate::contracts::{`
- `use crate::service::WebGraphService`
- `use crate::sources::EmbedFn`
- `use cortex_workspace::WorkspaceLayout`
- `use cortex_workspace::pyyaml::{to_pyyaml_string, Node}`
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/federation.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
