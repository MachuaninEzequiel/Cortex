# rust/crates/cortex-webgraph-server/src/style.rs

## Qué tiene adentro

Estilos del WebGraph — porteo de `cortex/webgraph/style.py` + `infer_doc_type_from_path` (doc_type.py Fase 13) + tabla webgraph_color/ shape de `cortex/documentation/routing.py`.
Archivo de 282 líneas.
Símbolos públicos observados:
- `pub const DEFAULT_NODE_COLOR: &str = "#cccccc"`
- `pub const DEFAULT_NODE_SHAPE: &str = "ellipse"`
- `pub struct NodeStyle`
- `pub fn style_for_doc_type(doc_type: Option<&str>) -> NodeStyle`
- `pub struct EdgeStyle`
- `pub const EDGE_TYPES: &[EdgeStyle] = &[`
- `pub fn style_for_edge(edge_type: &str) -> (String, String, String)`
- `pub fn build_legend() -> serde_json::Value`
- `pub fn infer_doc_type_from_path(path: &str) -> Option<&'static str>`
- `pub fn is_adr_filename(stem: &str) -> bool`

## Para qué sirve

Estilos del WebGraph — porteo de `cortex/webgraph/style.py` + `infer_doc_type_from_path` (doc_type.py Fase 13) + tabla webgraph_color/ shape de `cortex/documentation/routing.py`.

## Relaciones

### Recibe de

- `use cortex_setup::doc_type::DocType`
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/style.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
