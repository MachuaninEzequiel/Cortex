# rust/crates/cortex-webgraph-server/src/sources.rs

## Qué tiene adentro

Fuentes de records — porteo de `cortex/webgraph/semantic_source.py` y `cortex/webgraph/episodic_source.py`.  El lado nativo consume los motores ya gateados: el vault se recorre con `cortex-app::semantic::SemanticIndex` (P2, orden sorted por rel_path) y la memoria episódica llega como entradas `MemoryEntry` (P3/P12A-1, orden canónico por id). El embedder es INYECTABLE para que el gate sea determinista sin modelos ONNX (misma función pura en ambos lados).  GAP documentado (no simulado): `origin_project_id`/`origin_scope` del VaultReader federado no están en SemDoc nativo ⇒ metadata queda con vault_scope="local"; la superficie federada real usa ids prefijados y no
Archivo de 343 líneas.
Símbolos públicos observados:
- `pub type EmbedFn = Arc<dyn Fn(&str) -> Vec<f64> + Send + Sync>`
- `pub fn normalize_summary(text: &str, max_chars: usize) -> String`
- `pub(crate) fn read_project_config(config_path: &Path) -> BTreeMap<String, serde_yaml::Value>`
- `pub struct SemanticSource`
- `pub(crate) fn yaml_str(v: Option<&serde_yaml::Value>, default: &str) -> String`
- `pub fn parse_frontmatter_lenient(path: &Path) -> Option<serde_yaml::Mapping>`
- `pub fn yaml_to_json(v: &serde_yaml::Value) -> Value`
- `pub struct EpisodicSource`
- `pub(crate) fn boxed_or_default<'a>(v: &'a str, default: &'a str) -> &'a str`

## Para qué sirve

Fuentes de records — porteo de `cortex/webgraph/semantic_source.py` y `cortex/webgraph/episodic_source.py`.  El lado nativo consume los motores ya gateados: el vault se recorre con `cortex-app::semantic::SemanticIndex` (P2, orden sorted por rel_path) y la memoria episódica llega como entradas `MemoryEntry` (P3/P12A-1, orden canónico por id). El embedder es INYECTABLE para que el gate sea determinista sin modelos ONNX (misma función pura en ambos lados).  GAP documentado (no simulado): `origin_project_id`/`origin_scope` del VaultReader federado no están en SemDoc nativo ⇒ metadata queda con vault_scope="local"; la superficie federada real usa ids prefijados y no

## Relaciones

### Recibe de

- `use crate::contracts::{EpisodicRecord, SemanticRecord}`
- `use crate::style::{infer_doc_type_from_path, style_for_doc_type}`
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/sources.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
