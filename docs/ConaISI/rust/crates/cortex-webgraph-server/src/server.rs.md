# rust/crates/cortex-webgraph-server/src/server.rs

## Qué tiene adentro

Router axum equivalente al `create_app` Flask (`cortex/webgraph/server.py`).  Contrato de respuestas: - JSON: `pyjson::Mode::Compact + "\n"` (jsonify de Flask 3.x), Content-Type `application/json`. - Guard `/api/*`: header `X-Cortex-WebGraph: 1` obligatorio, sino 403 (el body HTML de abort() de Flask NO es contrato — paridad de STATUS). - index: minijinja sobre el MISMO template con `url_for` expandido. - static: bytes idénticos servidos en /static/*.
Archivo de 453 líneas.
Símbolos públicos observados:
- `pub enum Backend`
- `pub struct AppState`
- `pub type SharedState = Arc<AppState>`
- `pub fn create_app(`
- `pub fn server_endpoint(config: &WebGraphConfig) -> (String, i64)`
- `pub fn run_server(router: Router, host: &str, port: i64) -> std::io::Result<()>`
- `pub fn build_serve_router(project_root: &Path, workspace_file: Option<&Path>) -> Router`
- `pub type PathBufAlias = PathBuf`

## Para qué sirve

Router axum equivalente al `create_app` Flask (`cortex/webgraph/server.py`).  Contrato de respuestas: - JSON: `pyjson::Mode::Compact + "\n"` (jsonify de Flask 3.x), Content-Type `application/json`. - Guard `/api/*`: header `X-Cortex-WebGraph: 1` obligatorio, sino 403 (el body HTML de abort() de Flask NO es contrato — paridad de STATUS). - index: minijinja sobre el MISMO template con `url_for` expandido. - static: bytes idénticos servidos en /static/*.

## Relaciones

### Recibe de

- `use crate::config::WebGraphConfig`
- `use crate::contracts::WEBGRAPH_MODES`
- `use crate::federation::FederatedWebGraphService`
- `use crate::openers::{open_path, resolve_safe_vault_path}`
- `use crate::service::WebGraphService`
- `use crate::sources::EmbedFn`
- `use crate::style::build_legend`
- `use cortex_workspace::WorkspaceLayout`
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/server.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
