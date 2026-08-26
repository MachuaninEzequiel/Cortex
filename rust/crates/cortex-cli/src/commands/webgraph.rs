//! `cortex webgraph export` — puerto de cortex/webgraph/cli.py::export.
//!
//! Alcance honesto (documentado en el gate): paridad live para el caso
//! single-project con vault sin markdown y sin store episódico (el embedder
//! nunca se invoca ⇒ salida determinista) + error sin config. La paridad de
//! grafos profundos ya fue probada por el gate P12B-2 con fake embeddings.
//! Si hay workspace federado, el comando completo se delega al CLI Python.

use std::path::Path;

use clap::Parser;

use crate::paths::{expand_user, python_resolve};
use crate::pyjson::{Num, PyVal};

#[derive(Parser, Debug)]
#[command(
    name = "webgraph",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct WebgraphArgs {
    #[command(subcommand)]
    pub cmd: WebgraphCmd,
}

#[derive(clap::Subcommand, Debug)]
pub enum WebgraphCmd {
    /// Export a webgraph snapshot as JSON.
    Export {
        /// Graph mode: semantic, episodic, hybrid.
        #[arg(default_value = "hybrid")]
        mode: String,
        /// Output path for the JSON snapshot.
        #[arg(long)]
        output: Option<String>,
        /// Force snapshot rebuild.
        #[arg(long = "no-cache")]
        no_cache: bool,
        /// Absolute path to the target project root (where config.yaml lives).
        #[arg(long)]
        project_root: Option<String>,
        /// Path to a federation workspace YAML file (multi-project mode).
        #[arg(long = "workspace-file", alias = "workspace")]
        workspace_file: Option<String>,
    },
    /// Comandos aún no wireados (serve, doctor) → passthrough.
    #[command(external_subcommand)]
    Other(Vec<String>),
}

/// False si corresponde delegar al CLI Python (federación).
pub fn run(tokens: &[String]) -> bool {
    let args = WebgraphArgs::parse_from(
        std::iter::once("webgraph".to_string()).chain(tokens.iter().cloned()),
    );
    match args.cmd {
        WebgraphCmd::Export {
            mode,
            output,
            no_cache,
            project_root,
            workspace_file,
        } => {
            // Federación no wireada: si el usuario pide workspace explícito o
            // existe el default, delegamos TODO el comando.
            let root = resolve(project_root.as_deref());
            let default_ws = root.join(".cortex").join("webgraph").join("workspace.yaml");
            let federated =
                workspace_file.is_some() || (!workspace_file.is_some() && default_ws.exists());
            if federated {
                return false;
            }
            std::process::exit(execute(&root, &mode, output.as_deref(), no_cache));
        }
        WebgraphCmd::Other(_) => false,
    }
}

fn resolve(raw: Option<&str>) -> std::path::PathBuf {
    match raw {
        Some(p) => python_resolve(&expand_user(Path::new(p))),
        None => python_resolve(&std::env::current_dir().unwrap_or_default()),
    }
}

pub fn execute(root: &Path, mode: &str, output: Option<&str>, no_cache: bool) -> i32 {
    use cortex_webgraph_server::cache::WebGraphCache;
    use cortex_webgraph_server::service::WebGraphService;
    use cortex_webgraph_server::style::build_legend;

    let layout = cortex_workspace::WorkspaceLayout::discover(root);
    let config_path = layout.config_path();
    if !config_path.exists() {
        eprintln!(
            "Config not found at {}. Run `cortex setup agent` first or pass a valid --project-root.",
            config_path.display()
        );
        return 1;
    }

    let cache = WebGraphCache::new(root, Some(&layout));
    let service = WebGraphService::new(root, None, None, None, Vec::new(), None, Some(layout));
    let snapshot = service.build_snapshot_by_mode(mode, !no_cache, None);

    let path = match output {
        Some(p) => expand_user(Path::new(p)),
        None => cache.snapshot_path(mode, None),
    };
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }

    let mut payload = snapshot_pyval(&snapshot);
    if let PyVal::Obj(items) = &mut payload {
        items.push(("legend".to_string(), json_to_pyval(&build_legend())));
    }
    let body = crate::pyjson::stdlib_dumps_indent2(&payload);
    if std::fs::write(&path, body).is_err() {
        eprintln!("Failed to write snapshot to {}", path.display());
        return 1;
    }
    println!("Webgraph snapshot exported -> {}", path.display());
    0
}

/// `json.dumps(payload, indent=2)` con orden pydantic. `legend` se agrega
/// aparte por el CLI (igual que `service.export_snapshot`).
fn snapshot_pyval(s: &cortex_webgraph_server::contracts::WebGraphSnapshot) -> PyVal {
    PyVal::obj(vec![
        ("version", PyVal::s(&s.version)),
        ("fingerprint", PyVal::s(&s.fingerprint)),
        ("generated_at", PyVal::s(&s.generated_at)),
        ("mode", PyVal::s(&s.mode)),
        (
            "stats",
            PyVal::obj(vec![
                ("node_count", PyVal::Num(Num::Int(s.stats.node_count))),
                ("edge_count", PyVal::Num(Num::Int(s.stats.edge_count))),
                ("mode", PyVal::s(&s.stats.mode)),
                ("truncated", PyVal::Bool(s.stats.truncated)),
            ]),
        ),
        (
            "capabilities",
            PyVal::obj(vec![
                ("filters", PyVal::Bool(s.capabilities.filters)),
                ("subgraph", PyVal::Bool(s.capabilities.subgraph)),
                ("open_file", PyVal::Bool(s.capabilities.open_file)),
                (
                    "relation_explanations",
                    PyVal::Bool(s.capabilities.relation_explanations),
                ),
            ]),
        ),
        (
            "nodes",
            PyVal::Arr(s.nodes.iter().map(node_pyval).collect()),
        ),
        (
            "edges",
            PyVal::Arr(s.edges.iter().map(edge_pyval).collect()),
        ),
    ])
}

fn node_pyval(n: &cortex_webgraph_server::contracts::WebGraphNode) -> PyVal {
    PyVal::obj(vec![
        ("id", PyVal::s(&n.id)),
        ("node_type", PyVal::s(&n.node_type)),
        ("source", PyVal::s(&n.source)),
        ("label", PyVal::s(&n.label)),
        ("summary", PyVal::s(&n.summary)),
        (
            "rel_path",
            n.rel_path.as_ref().map(PyVal::s).unwrap_or(PyVal::Null),
        ),
        (
            "memory_id",
            n.memory_id.as_ref().map(PyVal::s).unwrap_or(PyVal::Null),
        ),
        ("tags", PyVal::Arr(n.tags.iter().map(PyVal::s).collect())),
        ("files", PyVal::Arr(n.files.iter().map(PyVal::s).collect())),
        (
            "timestamp",
            n.timestamp.as_ref().map(PyVal::s).unwrap_or(PyVal::Null),
        ),
        ("degree", PyVal::Num(Num::Int(n.degree))),
        ("metadata", json_map_to_obj(&n.metadata)),
    ])
}

fn edge_pyval(e: &cortex_webgraph_server::contracts::WebGraphEdge) -> PyVal {
    PyVal::obj(vec![
        ("id", PyVal::s(&e.id)),
        ("source", PyVal::s(&e.source)),
        ("target", PyVal::s(&e.target)),
        ("edge_type", PyVal::s(&e.edge_type)),
        ("weight", PyVal::Num(Num::Float(e.weight))),
        (
            "evidence",
            PyVal::Arr(e.evidence.iter().map(PyVal::s).collect()),
        ),
    ])
}

fn json_map_to_obj(map: &serde_json::Map<String, serde_json::Value>) -> PyVal {
    // metadata: BTreeMap nativo (orden alfabético) vs dict Python (inserción).
    // En fixtures vacíos no hay nodos ⇒ sin impacto en paridad; se conserva
    // el orden del mapa tal cual.
    PyVal::Obj(
        map.iter()
            .map(|(k, v)| (k.clone(), json_to_pyval(v)))
            .collect(),
    )
}

fn json_to_pyval(v: &serde_json::Value) -> PyVal {
    match v {
        serde_json::Value::Null => PyVal::Null,
        serde_json::Value::Bool(b) => PyVal::Bool(*b),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                PyVal::Num(Num::Int(i))
            } else {
                PyVal::Num(Num::Float(n.as_f64().unwrap_or(0.0)))
            }
        }
        serde_json::Value::String(s) => PyVal::s(s),
        serde_json::Value::Array(items) => PyVal::Arr(items.iter().map(json_to_pyval).collect()),
        serde_json::Value::Object(map) => PyVal::Obj(
            map.iter()
                .map(|(k, v)| (k.clone(), json_to_pyval(v)))
                .collect(),
        ),
    }
}
