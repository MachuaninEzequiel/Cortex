//! Comandos `cortex hu …` (Cierre T2) — espejo de cli/hu.py sobre
//! WorkItemService nativo (P12A-2). `import` construye providers desde
//! config (integrations.jira), igual que `_get_workitem_service`;
//! sin providers configurados falla con el mensaje canónico (igual que
//! Python sin integraciones).

use std::collections::{BTreeMap, HashMap};
use std::io::Write as _;

use clap::Parser;
use cortex_app::workitems::{
    TrackedItem, WorkItemKind, WorkItemProvider, WorkItemService, WorkItemSource,
};
use cortex_config::JiraIntegrationConfig;
use serde_json::Value;

fn echo(s: &str) {
    let mut out = std::io::stdout();
    let _ = writeln!(out, "{s}");
}

fn eecho(s: &str) {
    let mut out = std::io::stderr();
    let _ = writeln!(out, "{s}");
}

/// Puerto de `cortex/workitems/providers/jira.py` sobre el trait nativo
/// (ADF flatten + mapping `_to_tracked_item` + errores de Python).
/// Solo soporta esquema `file://` (gate hermético; sin cliente HTTP en
/// cortex-cli, Cargo.toml congelado). Los errores de fetch usan el texto
/// del oráculo (`Jira connection failed: …` / `Jira request failed: …`).
pub struct JiraProvider {
    base_url: String,
    email: String,
    api_token: String,
}

impl JiraProvider {
    fn from_config(cfg: &JiraIntegrationConfig) -> Self {
        let email = std::env::var(cfg.email_env.as_str())
            .unwrap_or_default()
            .trim()
            .to_string();
        let token = std::env::var(cfg.token_env.as_str())
            .unwrap_or_default()
            .trim()
            .to_string();
        Self {
            base_url: cfg.base_url.trim().trim_end_matches('/').to_string(),
            email,
            api_token: token,
        }
    }

    /// `_request_json`: file:// → lectura local; http(s) sin cliente nativo.
    fn request_json(&self, path: &str) -> Result<Value, String> {
        let url = format!("{}{}", self.base_url, path);
        let Some(local) = url.strip_prefix("file://") else {
            // Equivalente al URLError del oráculo para esquemas no-file.
            return Err(
                "Jira connection failed: unsupported URL scheme (native CLI only reads file://)"
                    .into(),
            );
        };
        let bytes = std::fs::read(local).map_err(|e| format!("Jira connection failed: {e}"))?;
        let text = String::from_utf8_lossy(&bytes).to_string();
        let data = serde_json::from_str::<Value>(&text)
            .map_err(|e| format!("Jira request failed: {e}"))?;
        if !data.is_object() {
            return Err("Unexpected Jira response payload.".into());
        }
        Ok(data)
    }

    fn to_tracked_item(&self, issue: &serde_json::Map<String, Value>) -> TrackedItem {
        let fields = issue
            .get("fields")
            .and_then(|f| f.as_object())
            .cloned()
            .unwrap_or_default();
        let issue_type = fields
            .get("issuetype")
            .and_then(|t| t.get("name"))
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_lowercase();
        let description = extract_description(fields.get("description"));
        let acceptance = extract_acceptance(&description);
        let labels = fields
            .get("labels")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default()
            .into_iter()
            .filter_map(|l| {
                let s = l.as_str().unwrap_or("");
                if s.trim().is_empty() {
                    None
                } else {
                    Some(s.to_string())
                }
            })
            .collect::<Vec<String>>();
        let assignee = fields
            .get("assignee")
            .and_then(|a| a.get("displayName"))
            .and_then(|v| v.as_str())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty());
        let status = fields
            .get("status")
            .and_then(|s| s.get("name"))
            .and_then(|v| v.as_str())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty());
        let external_id = issue
            .get("key")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .trim()
            .to_string();
        let title = fields
            .get("summary")
            .and_then(|v| v.as_str())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| external_id.clone());
        let priority = fields
            .get("priority")
            .and_then(|p| p.get("name"))
            .and_then(|v| v.as_str())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty());
        let mut metadata: BTreeMap<String, Value> = BTreeMap::new();
        metadata.insert(
            "issue_type".into(),
            if issue_type.is_empty() {
                Value::Null
            } else {
                Value::String(issue_type.clone())
            },
        );
        metadata.insert(
            "priority".into(),
            match priority {
                Some(p) => Value::String(p),
                None => Value::Null,
            },
        );
        let now = chrono::Utc::now().to_rfc3339();
        TrackedItem {
            id: external_id.clone(),
            external_id: external_id.clone(),
            source: WorkItemSource::Jira,
            kind: map_kind(&issue_type),
            title,
            description,
            acceptance_criteria: acceptance,
            status,
            labels,
            assignee,
            metadata,
            vault_path: None,
            external_url: Some(format!("{}/browse/{}", self.base_url, external_id)),
            sync_timestamp: Some(now),
        }
    }
}

/// `WorkItemProvider` port del oráculo (jira.py).
impl WorkItemProvider for JiraProvider {
    fn source_name(&self) -> &str {
        "jira"
    }

    fn is_configured(&self) -> bool {
        !self.base_url.is_empty() && !self.email.is_empty() && !self.api_token.is_empty()
    }

    fn get_item(&self, external_id: &str) -> Result<TrackedItem, String> {
        if !self.is_configured() {
            return Err("Jira provider is not configured.".into());
        }
        let issue_key = external_id.trim().to_uppercase();
        let path = format!("/rest/api/3/issue/{}", percent_quote(&issue_key));
        let data = self.request_json(&path)?;
        let obj = match data.as_object() {
            Some(o) => o,
            None => return Err("Unexpected Jira response payload.".into()),
        };
        Ok(self.to_tracked_item(obj))
    }
}

/// `urllib.parse.quote` con safe="/" (alnum + `_.-~` + `/`).
fn percent_quote(s: &str) -> String {
    let mut out = String::new();
    for b in s.bytes() {
        let keep = b.is_ascii_alphanumeric() || matches!(b, b'_' | b'.' | b'-' | b'~' | b'/');
        if keep {
            out.push(b as char);
        } else {
            out.push_str(&format!("%{b:02X}"));
        }
    }
    out
}

/// `_extract_description` / `_flatten_adf` del oráculo.
fn extract_description(value: Option<&Value>) -> String {
    match value {
        Some(Value::String(s)) => s.trim().to_string(),
        Some(Value::Object(obj)) => flatten_adf(&Value::Object(obj.clone())).trim().to_string(),
        _ => String::new(),
    }
}

fn flatten_adf(node: &Value) -> String {
    match node {
        Value::String(s) => s.clone(),
        Value::Array(items) => items.iter().map(flatten_adf).collect::<String>(),
        Value::Null => String::new(),
        _ => {
            if let Some(obj) = node.as_object() {
                match obj.get("type").and_then(|t| t.as_str()) {
                    Some("paragraph") | Some("heading") => {
                        let content = obj.get("content").map(flatten_adf).unwrap_or_default();
                        format!("{content}\n\n")
                    }
                    Some("text") => obj
                        .get("text")
                        .and_then(|t| t.as_str())
                        .unwrap_or("")
                        .to_string(),
                    Some("bulletList") => {
                        let mut items = Vec::new();
                        if let Some(Value::Array(list)) = obj.get("content") {
                            for item in list {
                                let text = flatten_adf(item).trim().to_string();
                                if !text.is_empty() {
                                    items.push(format!("- {text}"));
                                }
                            }
                        }
                        format!("{}\n", items.join("\n"))
                    }
                    _ => obj.get("content").map(flatten_adf).unwrap_or_default(),
                }
            } else {
                String::new()
            }
        }
    }
}

/// `_extract_acceptance_criteria` del oráculo (líneas `- `, `* `, `[ ] `).
fn extract_acceptance(description: &str) -> Vec<String> {
    let mut out = Vec::new();
    for line in description.lines() {
        let stripped = line.trim().to_string();
        let lowered = stripped.to_lowercase();
        if lowered.starts_with("- ") || lowered.starts_with("* ") || lowered.starts_with("[ ] ") {
            out.push(
                stripped
                    .trim_start_matches(['-', '*', ' '])
                    .trim()
                    .to_string(),
            );
        }
    }
    out
}

/// `_map_kind` del oráculo (issue_type → WorkItemKind).
fn map_kind(issue_type: &str) -> WorkItemKind {
    match issue_type {
        "story" | "user story" => WorkItemKind::Story,
        "task" | "sub-task" => WorkItemKind::Task,
        "bug" => WorkItemKind::Bug,
        "epic" => WorkItemKind::Epic,
        "incident" => WorkItemKind::Incident,
        _ => WorkItemKind::Other,
    }
}

/// Providers desde config (`_get_workitem_service`): si
/// `integrations.jira.enabled` ⇒ registra jira; si no, mapa vacío.
fn providers_from_config(
    layout: &cortex_workspace::WorkspaceLayout,
) -> HashMap<String, Box<dyn WorkItemProvider>> {
    let mut providers: HashMap<String, Box<dyn WorkItemProvider>> = HashMap::new();
    let config_path = layout.config_path();
    let Ok(text) = std::fs::read_to_string(&config_path) else {
        return providers;
    };
    let Ok(config) = serde_yaml::from_str::<cortex_config::CortexConfig>(&text) else {
        return providers;
    };
    if config.integrations.jira.enabled {
        providers.insert(
            "jira".to_string(),
            Box::new(JiraProvider::from_config(&config.integrations.jira)),
        );
    }
    providers
}

/// Servicio con vault del layout y providers desde config.
///
/// Leak controlado de una sola configuración por proceso: los comandos hu
/// son one-shot (el CLI termina tras ejecutarlos).
fn service_for() -> WorkItemService<'static> {
    let start = crate::paths::resolve_project_root(None);
    let layout = cortex_workspace::WorkspaceLayout::discover(&start);
    let vault: &'static std::path::PathBuf = Box::leak(Box::new(layout.vault_path()));
    let providers = providers_from_config(&layout);
    WorkItemService::new(vault.as_path(), providers, None, None)
}

#[derive(Parser, Debug)]
#[command(
    name = "hu",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct HuArgs {
    #[command(subcommand)]
    pub cmd: HuCmd,
}

#[derive(clap::Subcommand, Debug)]
pub enum HuCmd {
    /// Import one external tracked item into ``vault/hu/``.
    Import {
        external_id: String,
        #[arg(long, default_value = "jira")]
        provider: String,
        #[arg(long)]
        no_remember: bool,
    },
    /// List tracked item notes already stored in ``vault/hu/``.
    List,
    /// Show the local vault note path for one tracked item.
    Show { item_id: String },
}

pub fn run(argv: &[String]) -> bool {
    let args =
        match HuArgs::try_parse_from(std::iter::once("hu".to_string()).chain(argv.iter().cloned()))
        {
            Ok(a) => a,
            Err(e) => {
                eprint!("{e}");
                return true;
            }
        };
    match args.cmd {
        HuCmd::Import {
            external_id,
            provider,
            no_remember,
        } => {
            let mut svc = service_for();
            match svc.import_item(&external_id, &provider, !no_remember, chrono_utc_now()) {
                Ok(path) => echo(&format!("Tracked item imported -> {}", path.display())),
                Err(e) => {
                    eecho(&e);
                    std::process::exit(1);
                }
            }
        }
        HuCmd::List => {
            let svc = service_for();
            let notes = svc.list_item_notes();
            if notes.is_empty() {
                echo("No tracked items imported yet.");
            } else {
                for n in notes {
                    echo(&n.to_string_lossy());
                }
            }
        }
        HuCmd::Show { item_id } => match service_for().get_item_note(&item_id) {
            Ok(path) => echo(&path.to_string_lossy()),
            Err(e) => {
                eecho(&e);
                std::process::exit(1);
            }
        },
    }
    true
}

fn chrono_utc_now() -> chrono::DateTime<chrono::Utc> {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;
    chrono::DateTime::from_timestamp(secs, 0).unwrap_or_default()
}
