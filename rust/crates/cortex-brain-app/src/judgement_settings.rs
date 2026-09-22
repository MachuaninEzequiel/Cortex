//! Settings TypeSafe/Jev para Cortex Brain.
//! Toggle + purposes en config.yaml; API key solo en el llavero del OS.

use std::path::Path;

use cortex_config::{
    CortexConfig, FailMode, JudgementConfig, JudgementProvider, JudgementPurposes, PurposeMode,
};
use cortex_judgement::{
    build_handle, delete_api_key, key_configured, resolve_api_key, status, store_api_key,
    ClientOptions, JudgementHandle, JudgementStatus,
};
use cortex_setup::ide::{detect_host, discover_models_for_host, ProviderModelInfo};
use cortex_workspace::WorkspaceLayout;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JudgementSettingsPayload {
    pub enabled: bool,
    pub search_squeeze: bool,
    pub promotion: bool,
    pub context_pack: bool,
    pub utterance: bool,
    pub session_compact: bool,
    pub model_routing: bool,
    pub model: String,
    pub status: String,
    /// True si hay key (env o llavero). Nunca se devuelve el valor.
    pub key_configured: bool,
    pub has_project: bool,
    pub detected_host: String,
    pub host_id: String,
    pub host_policy: String,
    pub available_models: Vec<ProviderModelInfo>,
    pub designer_model: Option<String>,
    pub implementer_model: Option<String>,
    pub documenter_model: Option<String>,
    pub auditor_model: Option<String>,
}

impl JudgementSettingsPayload {
    fn from_cfg(cfg: &JudgementConfig, project: Option<&Path>) -> Self {
        let opts = options_from(cfg);
        let host = detect_host(project);
        let home = std::env::var_os("HOME")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| std::path::PathBuf::from("/home/chucho"));
        let available_models = discover_models_for_host(&home, host);
        let host_key = host.as_str().to_string();

        let host_cfg = cfg.model_router.hosts.get(&host_key);
        let designer_model = host_cfg.and_then(|h| h.designer.clone());
        let implementer_model = host_cfg.and_then(|h| h.implementer.clone());
        let documenter_model = host_cfg.and_then(|h| h.documenter.clone());
        let auditor_model = host_cfg.and_then(|h| h.auditor.clone());

        Self {
            enabled: cfg.enabled,
            search_squeeze: cfg.purposes.search_squeeze == PurposeMode::On,
            promotion: cfg.purposes.promotion == PurposeMode::On,
            context_pack: cfg.purposes.context_pack == PurposeMode::On,
            utterance: cfg.purposes.utterance == PurposeMode::On,
            session_compact: cfg.purposes.session_compact == PurposeMode::On,
            model_routing: cfg.purposes.model_routing == PurposeMode::On,
            model: cfg.model.clone(),
            status: status(&opts).as_str().to_string(),
            key_configured: key_configured(&cfg.api_key_env),
            has_project: project.is_some(),
            detected_host: host.display_name().to_string(),
            host_id: host_key,
            host_policy: host.policy_description().to_string(),
            available_models,
            designer_model,
            implementer_model,
            documenter_model,
            auditor_model,
        }
    }
}

pub fn options_from(cfg: &JudgementConfig) -> ClientOptions {
    ClientOptions {
        enabled: cfg.enabled,
        provider: match cfg.provider {
            JudgementProvider::None => "none".into(),
            JudgementProvider::Typesafe => "typesafe".into(),
        },
        model: cfg.model.clone(),
        timeout_ms: cfg.timeout_ms,
        api_key_env: cfg.api_key_env.clone(),
        search_squeeze: cfg.purposes.search_squeeze == PurposeMode::On,
        promotion: cfg.purposes.promotion == PurposeMode::On,
        context_pack: cfg.purposes.context_pack == PurposeMode::On,
        utterance: cfg.purposes.utterance == PurposeMode::On,
        session_compact: cfg.purposes.session_compact == PurposeMode::On,
        model_routing: cfg.purposes.model_routing == PurposeMode::On,
        base_url: std::env::var("TYPESAFE_BASE_URL").ok(),
        questions_override: None,
    }
}

pub fn load_config(project: &Path) -> JudgementConfig {
    let layout = WorkspaceLayout::discover(project);
    let path = layout.config_path();
    let Ok(text) = std::fs::read_to_string(&path) else {
        return JudgementConfig::default();
    };
    serde_yaml::from_str::<CortexConfig>(&text)
        .map(|c| c.judgement)
        .unwrap_or_default()
}

pub fn handle_for_project(project: &Path) -> Option<JudgementHandle> {
    let cfg = load_config(project);
    let layout = WorkspaceLayout::discover(project);
    let qpath = layout
        .workspace_root
        .join("judgement")
        .join("questions.yaml");
    let mut opts = options_from(&cfg);
    if qpath.exists() {
        opts.questions_override = Some(qpath);
    }
    build_handle(&opts)
}

pub fn get_settings(project: &str) -> JudgementSettingsPayload {
    if project.trim().is_empty() {
        return JudgementSettingsPayload::from_cfg(&JudgementConfig::default(), None);
    }
    let p = Path::new(project);
    let cfg = load_config(p);
    JudgementSettingsPayload::from_cfg(&cfg, Some(p))
}

#[derive(Debug, Deserialize)]
pub struct SaveJudgementArgs {
    pub project: String,
    pub enabled: bool,
    pub search_squeeze: bool,
    pub promotion: bool,
    pub context_pack: bool,
    pub utterance: bool,
    pub session_compact: bool,
    pub model_routing: Option<bool>,
    pub designer_model: Option<String>,
    pub implementer_model: Option<String>,
    pub documenter_model: Option<String>,
    pub auditor_model: Option<String>,
    /// None = no tocar. Some("") = borrar. Some(key) = guardar en llavero.
    pub api_key: Option<String>,
}

pub fn save_settings(args: SaveJudgementArgs) -> Result<JudgementSettingsPayload, String> {
    if args.project.trim().is_empty() {
        return Err("Abrí un proyecto para configurar TypeSafe.".into());
    }
    let root = Path::new(&args.project);
    let layout = WorkspaceLayout::discover(root);
    let path = layout.config_path();
    if !path.exists() {
        return Err(format!("No encuentro config.yaml en {}", path.display()));
    }
    let text = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let mut root_val: serde_yaml::Value =
        serde_yaml::from_str(&text).map_err(|e| format!("config.yaml inválido: {e}"))?;

    let mut cfg = load_config(root);
    cfg.enabled = args.enabled;
    cfg.provider = if args.enabled {
        JudgementProvider::Typesafe
    } else {
        JudgementProvider::None
    };
    cfg.fail = FailMode::Open;
    cfg.purposes = JudgementPurposes {
        search_squeeze: if args.search_squeeze {
            PurposeMode::On
        } else {
            PurposeMode::Off
        },
        promotion: if args.promotion {
            PurposeMode::On
        } else {
            PurposeMode::Off
        },
        context_pack: if args.context_pack {
            PurposeMode::On
        } else {
            PurposeMode::Off
        },
        utterance: if args.utterance {
            PurposeMode::On
        } else {
            PurposeMode::Off
        },
        session_compact: if args.session_compact {
            PurposeMode::On
        } else {
            PurposeMode::Off
        },
        model_routing: if args.model_routing.unwrap_or(false) {
            PurposeMode::On
        } else {
            PurposeMode::Off
        },
    };

    let mr_on = args.model_routing.unwrap_or(false);
    cfg.model_router.enabled = mr_on;

    let host = detect_host(Some(root));
    let host_key = host.as_str().to_string();

    if args.designer_model.is_some()
        || args.implementer_model.is_some()
        || args.documenter_model.is_some()
        || args.auditor_model.is_some()
    {
        let host_entry = cfg.model_router.hosts.entry(host_key).or_default();
        if let Some(m) = args.designer_model {
            host_entry.designer = if m.trim().is_empty() { None } else { Some(m.trim().to_string()) };
        }
        if let Some(m) = args.implementer_model {
            host_entry.implementer = if m.trim().is_empty() { None } else { Some(m.trim().to_string()) };
        }
        if let Some(m) = args.documenter_model {
            host_entry.documenter = if m.trim().is_empty() { None } else { Some(m.trim().to_string()) };
        }
        if let Some(m) = args.auditor_model {
            host_entry.auditor = if m.trim().is_empty() { None } else { Some(m.trim().to_string()) };
        }
    }

    if let Some(key) = args.api_key {
        if key.trim().is_empty() {
            delete_api_key(&cfg.api_key_env);
        } else {
            store_api_key(&cfg.api_key_env, &key)?;
            // Inyectar env para que `cortex search` hijo herede la key.
            unsafe { std::env::set_var(&cfg.api_key_env, key.trim()) }
        }
    } else if let Some(k) = resolve_api_key(&cfg.api_key_env) {
        unsafe { std::env::set_var(&cfg.api_key_env, k) }
    }

    let mapping = root_val
        .as_mapping_mut()
        .ok_or("config.yaml no es un mapping")?;
    mapping.insert(
        serde_yaml::Value::String("judgement".into()),
        serde_yaml::to_value(&cfg).map_err(|e| e.to_string())?,
    );
    let out = serde_yaml::to_string(&root_val).map_err(|e| e.to_string())?;
    std::fs::write(&path, out).map_err(|e| e.to_string())?;
    Ok(JudgementSettingsPayload::from_cfg(&cfg, Some(root)))
}

pub fn hydrate_process_env() {
    if let Some(k) = resolve_api_key("TYPESAFE_API_KEY") {
        unsafe { std::env::set_var("TYPESAFE_API_KEY", k) }
    }
}

pub fn status_str(project: &str) -> &'static str {
    if project.trim().is_empty() {
        return JudgementStatus::Disabled.as_str();
    }
    let cfg = load_config(Path::new(project));
    status(&options_from(&cfg)).as_str()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_project_is_disabled() {
        let p = get_settings("");
        assert!(!p.has_project);
        assert_eq!(p.status, "disabled");
        assert!(!p.enabled);
        assert!(!p.context_pack);
        assert!(!p.utterance);
        assert!(!p.session_compact);
        assert!(!p.model_routing);
    }

    #[test]
    fn test_save_settings_with_model_routing() {
        let temp_dir = tempfile::tempdir().unwrap();
        let cortex_dir = temp_dir.path().join(".cortex");
        std::fs::create_dir_all(&cortex_dir).unwrap();
        let config_path = cortex_dir.join("config.yaml");
        std::fs::write(&config_path, "episodic:\n  enabled: true\n").unwrap();

        let saved = save_settings(SaveJudgementArgs {
            project: temp_dir.path().to_string_lossy().to_string(),
            enabled: true,
            search_squeeze: true,
            promotion: false,
            context_pack: false,
            utterance: false,
            session_compact: false,
            model_routing: Some(true),
            designer_model: Some("google:gemini-2.5-pro".to_string()),
            implementer_model: Some("google:gemini-2.5-pro".to_string()),
            documenter_model: Some("google:gemini-2.5-flash".to_string()),
            auditor_model: Some("google:gemini-2.5-flash".to_string()),
            api_key: None,
        })
        .unwrap();

        assert!(saved.enabled);
        assert!(saved.model_routing);
        assert_eq!(saved.designer_model.as_deref(), Some("google:gemini-2.5-pro"));
        assert_eq!(saved.documenter_model.as_deref(), Some("google:gemini-2.5-flash"));

        let reloaded = get_settings(&temp_dir.path().to_string_lossy());
        assert!(reloaded.enabled);
        assert!(reloaded.model_routing);
        assert_eq!(reloaded.designer_model.as_deref(), Some("google:gemini-2.5-pro"));
    }
}

