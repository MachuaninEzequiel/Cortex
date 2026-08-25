//! Router axum equivalente al `create_app` Flask (`cortex/webgraph/server.py`).
//!
//! Contrato de respuestas:
//! - JSON: `pyjson::Mode::Compact + "\n"` (jsonify de Flask 3.x),
//!   Content-Type `application/json`.
//! - Guard `/api/*`: header `X-Cortex-WebGraph: 1` obligatorio, sino 403
//!   (el body HTML de abort() de Flask NO es contrato — paridad de STATUS).
//! - index: minijinja sobre el MISMO template con `url_for` expandido.
//! - static: bytes idénticos servidos en /static/*.

#![forbid(unsafe_code)]

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use axum::extract::{Path as AxumPath, Query, State};
use axum::http::{header, HeaderMap, HeaderValue, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::Router;
use serde_json::Value;

use crate::config::WebGraphConfig;
use crate::contracts::WEBGRAPH_MODES;
use crate::federation::FederatedWebGraphService;
use crate::openers::{open_path, resolve_safe_vault_path};
use crate::service::WebGraphService;
use crate::sources::EmbedFn;
use crate::style::build_legend;
use cortex_workspace::WorkspaceLayout;

const INDEX_TEMPLATE: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../cortex/webgraph/templates/index.html"
));
const STATIC_STYLE_CSS: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../cortex/webgraph/static/style.css"
));
const STATIC_APP_JS: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../cortex/webgraph/static/app.js"
));

pub enum Backend {
    Single(Box<WebGraphService>),
    Federated(Box<FederatedWebGraphService>),
}

pub struct AppState {
    pub backend: Backend,
    pub config: WebGraphConfig,
    /// None ⇒ modo single (open usa resolve_safe_vault_path); Some ⇒ federado
    /// (open usa resolve_node_path directo), igual que el branch de Python.
    pub workspace_mode: bool,
}

pub type SharedState = Arc<AppState>;

/// create_app: construye el Router axum. `episodic_entries` y `embedder`
/// son inyectables para determinismo del gate (igual que Python acepta
/// store/embedder custom).
#[allow(clippy::too_many_arguments)]
pub fn create_app(
    project_root: &Path,
    episodic_entries: Vec<cortex_app::episodic::MemoryEntry>,
    embedder: Option<EmbedFn>,
    workspace_file: Option<&Path>,
) -> Router {
    let layout = WorkspaceLayout::discover(project_root);
    let (backend, config, workspace_mode) = match workspace_file {
        Some(ws) => {
            let service = FederatedWebGraphService::new(ws, embedder);
            let config = WebGraphConfig::default();
            (Backend::Federated(Box::new(service)), config, true)
        }
        None => {
            let service = WebGraphService::new(
                project_root,
                None,
                None,
                None,
                episodic_entries,
                embedder,
                Some(layout.clone()),
            );
            let config = WebGraphConfig::load(Some(project_root), Some(&layout));
            (Backend::Single(Box::new(service)), config, false)
        }
    };
    let state = Arc::new(AppState {
        backend,
        config,
        workspace_mode,
    });

    Router::new()
        .route("/", get(index))
        .route("/static/style.css", get(static_css))
        .route("/static/app.js", get(static_js))
        .route("/api/snapshot", get(api_snapshot))
        .route("/api/node/{node_id}", get(api_node_detail))
        .route("/api/subgraph", get(api_subgraph))
        .route("/api/open", post(api_open))
        .fallback(not_found)
        .with_state(state)
}

// ── helpers de respuesta ────────────────────────────────────────────────────

fn json_response(status: StatusCode, payload: &Value) -> Response {
    let mut body = crate::pyjson::dumps(payload, crate::pyjson::Mode::Compact, true);
    body.push('\n');
    (
        status,
        [(
            axum::http::header::CONTENT_TYPE,
            HeaderValue::from_static("application/json"),
        )],
        body,
    )
        .into_response()
}

async fn not_found() -> Response {
    // Flask default 404 HTML (no contrato byte-parity; sólo status).
    (
        StatusCode::NOT_FOUND,
        [(header::CONTENT_TYPE, "text/html; charset=utf-8")],
        "<!doctype html>\n<html lang=en>\n<title>404 Not Found</title>\n<h1>Not Found</h1>\n",
    )
        .into_response()
}

fn check_api_headers(headers: &HeaderMap) -> Option<Response> {
    if headers
        .get("X-Cortex-WebGraph")
        .and_then(|v| v.to_str().ok())
        != Some("1")
    {
        return Some((
            StatusCode::FORBIDDEN,
            [(header::CONTENT_TYPE, "text/html; charset=utf-8")],
            "<!doctype html>\n<html lang=en>\n<title>403 Forbidden</title>\n<h1>Forbidden</h1>\n",
        )
            .into_response());
    }
    None
}

fn validate_mode(state: &AppState, raw_mode: Option<&String>) -> Result<String, Box<Response>> {
    let mode = raw_mode
        .cloned()
        .unwrap_or_else(|| state.config.default_mode.clone());
    if !WEBGRAPH_MODES.contains(&mode.as_str()) {
        let mut sorted_modes: Vec<String> = WEBGRAPH_MODES.iter().map(|s| s.to_string()).collect();
        sorted_modes.sort();
        let msg = format!(
            "Invalid mode '{}'. Expected one of: [{}]",
            mode,
            sorted_modes
                .iter()
                .map(|m| format!("'{m}'"))
                .collect::<Vec<_>>()
                .join(", ")
        );
        return Err(Box::new(json_response(
            StatusCode::BAD_REQUEST,
            &serde_json::json!({"error": msg}),
        )));
    }
    Ok(mode)
}

fn with_backend(state: &AppState, mode: &str) -> Value {
    match &state.backend {
        Backend::Single(svc) => {
            let snap = svc.build_snapshot(mode, true, None);
            snapshot_payload(&snap)
        }
        Backend::Federated(svc) => {
            let snap = svc.build_snapshot(mode, true, None);
            snapshot_payload(&snap)
        }
    }
}

fn snapshot_payload(snap: &crate::contracts::WebGraphSnapshot) -> Value {
    // model_dump() → jsonify(sort_keys=True). Serializar vía serde_json y
    // re-dump con pyjson Compact sorted.
    let mut value = serde_json::to_value(snap).unwrap_or(Value::Null);
    if let Value::Object(map) = &mut value {
        map.insert("legend".into(), build_legend());
    }
    value
}

fn detail_payload(detail: &crate::contracts::WebGraphNodeDetail) -> Value {
    serde_json::to_value(detail).unwrap_or(Value::Null)
}

fn subgraph_payload(snap: &crate::contracts::WebGraphSnapshot) -> Value {
    serde_json::to_value(snap).unwrap_or(Value::Null)
}

// ── handlers ────────────────────────────────────────────────────────────────

async fn index(State(state): State<SharedState>) -> Response {
    // render_template("index.html", default_mode=...) con url_for expandido
    // a su salida literal de Flask ("/static/style.css").
    // Flask expande TODOS los url_for estáticos a sus URLs literales.
    let re_urlfor =
        regex::Regex::new(r#"\{\{ url_for\('static', filename='([^']+)'\) \}\}"#).unwrap();
    let template = re_urlfor
        .replace_all(INDEX_TEMPLATE, "/static/$1")
        .to_string();
    let mut engine = minijinja::Environment::new();
    let _ = engine.add_template("index.html", &template);
    let ctx = minijinja::context! {
        default_mode => state.config.default_mode.clone(),
    };
    match engine
        .get_template("index.html")
        .and_then(|t| t.render(minijinja::Value::from_serialize(&ctx)))
    {
        Ok(html) => (
            StatusCode::OK,
            [(header::CONTENT_TYPE, "text/html; charset=utf-8")],
            html,
        )
            .into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            [(header::CONTENT_TYPE, "text/plain; charset=utf-8")],
            format!("template error: {e}"),
        )
            .into_response(),
    }
}

async fn static_css() -> Response {
    (
        StatusCode::OK,
        [("content-type", "text/css; charset=utf-8")],
        STATIC_STYLE_CSS.to_vec(),
    )
        .into_response()
}

async fn static_js() -> Response {
    (
        StatusCode::OK,
        [("content-type", "text/javascript; charset=utf-8")],
        STATIC_APP_JS.to_vec(),
    )
        .into_response()
}

async fn api_snapshot(
    State(state): State<SharedState>,
    headers: HeaderMap,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Response {
    if let Some(resp) = check_api_headers(&headers) {
        return resp;
    }
    let mode = match validate_mode(&state, params.get("mode")) {
        Ok(m) => m,
        Err(resp) => return *resp,
    };
    json_response(StatusCode::OK, &with_backend(&state, &mode))
}

async fn api_node_detail(
    State(state): State<SharedState>,
    headers: HeaderMap,
    AxumPath(node_id): AxumPath<String>,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Response {
    if let Some(resp) = check_api_headers(&headers) {
        return resp;
    }
    let mode = match validate_mode(&state, params.get("mode")) {
        Ok(m) => m,
        Err(resp) => return *resp,
    };
    let detail = match &state.backend {
        Backend::Single(svc) => svc.get_node_detail(&node_id, &mode),
        Backend::Federated(svc) => svc.get_node_detail(&node_id, &mode),
    };
    match detail {
        None => json_response(
            StatusCode::NOT_FOUND,
            &serde_json::json!({"error": format!("Unknown node: {node_id}")}),
        ),
        Some(d) => json_response(StatusCode::OK, &detail_payload(&d)),
    }
}

async fn api_subgraph(
    State(state): State<SharedState>,
    headers: HeaderMap,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Response {
    if let Some(resp) = check_api_headers(&headers) {
        return resp;
    }
    let mode = match validate_mode(&state, params.get("mode")) {
        Ok(m) => m,
        Err(resp) => return *resp,
    };
    let node_id = match params.get("node_id") {
        Some(n) => n.clone(),
        None => return not_found().await, // KeyError de Python ⇒ 500; gate no lo ejercita
    };
    let depth: i64 = params
        .get("depth")
        .and_then(|d| d.parse().ok())
        .unwrap_or(1);
    let edge_types: Option<BTreeSet<String>> = params.get("edge_types").map(|raw| {
        raw.split(',')
            .filter(|s| !s.is_empty())
            .map(String::from)
            .collect()
    });
    let snap = match &state.backend {
        Backend::Single(svc) => svc.get_subgraph(&node_id, depth, &mode, edge_types.as_ref()),
        Backend::Federated(svc) => svc.get_subgraph(&node_id, depth, &mode, edge_types.as_ref()),
    };
    json_response(StatusCode::OK, &subgraph_payload(&snap))
}

async fn api_open(State(state): State<SharedState>, headers: HeaderMap, body: String) -> Response {
    if let Some(resp) = check_api_headers(&headers) {
        return resp;
    }
    let parsed: Result<Value, _> = serde_json::from_str(&body);
    let payload: Value = match parsed {
        Ok(v) if v.is_object() => v,
        _ => Value::Null,
    };
    let node_id: Option<String> = payload
        .as_object()
        .and_then(|o| o.get("node_id"))
        .and_then(|v| v.as_str())
        .map(String::from)
        .filter(|s| !s.is_empty());
    let Some(node_id) = node_id else {
        return json_response(
            StatusCode::BAD_REQUEST,
            &serde_json::json!({"error": "Missing node_id"}),
        );
    };
    // Python fija mode="hybrid" para open.
    let mode = "hybrid";
    let detail_exists = match &state.backend {
        Backend::Single(svc) => svc.get_node_detail(&node_id, mode).is_some(),
        Backend::Federated(svc) => svc.get_node_detail(&node_id, mode).is_some(),
    };
    if !detail_exists {
        return json_response(
            StatusCode::NOT_FOUND,
            &serde_json::json!({"error": format!("Unknown node: {node_id}")}),
        );
    }
    let resolved_path = match &state.backend {
        Backend::Single(svc) => svc.resolve_node_path(&node_id, mode),
        Backend::Federated(svc) => svc.resolve_node_path(&node_id, mode),
    };
    let Some(resolved_path) = resolved_path else {
        return json_response(
            StatusCode::BAD_REQUEST,
            &serde_json::json!({"error": "Selected node has no local document"}),
        );
    };

    let path = if state.workspace_mode {
        resolved_path
    } else {
        // Single: rel_path obligatorio + resolución segura contra vault.
        let rel = match &state.backend {
            Backend::Single(svc) => svc
                .get_node_detail(&node_id, mode)
                .and_then(|d| d.node.rel_path.clone())
                .filter(|r| !r.is_empty()),
            _ => None,
        };
        let Some(rel) = rel else {
            return json_response(
                StatusCode::BAD_REQUEST,
                &serde_json::json!({"error": "Selected node has no local document"}),
            );
        };
        let vault_root = match &state.backend {
            Backend::Single(svc) => svc.semantic_source.vault_path.clone(),
            _ => unreachable!(),
        };
        match resolve_safe_vault_path(&vault_root, &rel) {
            Ok(p) => p,
            Err(_) => {
                return json_response(
                    StatusCode::BAD_REQUEST,
                    &serde_json::json!({"error": "Selected node has no local document"}),
                )
            }
        }
    };
    // En el gate la apertura real se stubbea (sin side-effects del SO).
    if std::env::var("CORTEX_WEBGRAPH_OPEN_DISABLE").as_deref() != Ok("1") {
        open_path(&path);
    }
    json_response(
        StatusCode::OK,
        &serde_json::json!({"status": "ok", "path": path.to_string_lossy()}),
    )
}

/// Utilidad para el checker: puerto/host configurados.
pub fn server_endpoint(config: &WebGraphConfig) -> (String, i64) {
    (config.server_host.clone(), config.server_port)
}

pub type PathBufAlias = PathBuf;
