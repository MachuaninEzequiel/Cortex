//! CLI Model Discovery Engine — Descubrimiento pasivo de modelos logueados en la máquina.
//!
//! Lee los almacenes locales de configuración de Pi, Antigravity y Claude Code para
//! devolver los modelos reales con el formato canónico `provider:model_id`.

use std::collections::HashSet;
use std::fs;
use std::path::Path;
use serde::{Deserialize, Serialize};

use super::host_detector::HostEnvironment;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProviderModelInfo {
    pub provider: String,
    pub model_id: String,
    pub canonical_id: String,
    pub display_name: String,
    pub source_cli: String,
    pub is_active: bool,
}

impl ProviderModelInfo {
    pub fn new(provider: &str, model_id: &str, display_name: &str, source_cli: &str) -> Self {
        Self {
            provider: provider.to_string(),
            model_id: model_id.to_string(),
            canonical_id: format!("{provider}:{model_id}"),
            display_name: display_name.to_string(),
            source_cli: source_cli.to_string(),
            is_active: true,
        }
    }
}

/// Descubre todos los modelos autenticados en los CLIs del usuario.
pub fn discover_all_cli_models(home: &Path) -> Vec<ProviderModelInfo> {
    let mut models = Vec::new();

    // 1. Descubrir modelos de Pi (~/.pi/agent/)
    discover_pi_models(home, &mut models);

    // 2. Descubrir modelos de Antigravity (~/.gemini/antigravity-cli/)
    discover_antigravity_models(home, &mut models);

    // 3. Descubrir modelos de Claude Code (~/.claude/)
    discover_claude_models(home, &mut models);

    models
}

/// Descubre modelos filtrados estrictamente por la política del Host activo.
pub fn discover_models_for_host(home: &Path, host: HostEnvironment) -> Vec<ProviderModelInfo> {
    let all = discover_all_cli_models(home);
    all.into_iter()
        .filter(|m| host.is_provider_allowed(&m.provider))
        .collect()
}

// ── Lector de Pi (~/.pi/agent) ────────────────────────────────────────────────

fn discover_pi_models(home: &Path, out: &mut Vec<ProviderModelInfo>) {
    let pi_agent = home.join(".pi").join("agent");
    let auth_file = pi_agent.join("auth.json");
    let models_file = pi_agent.join("models-store.json");

    if !models_file.is_file() {
        return;
    }

    // Proveedores autenticados en auth.json
    let mut authenticated_providers = HashSet::new();
    if let Ok(text) = fs::read_to_string(&auth_file) {
        if let Ok(val) = serde_json::from_str::<serde_json::Value>(&text) {
            if let Some(obj) = val.as_object() {
                for key in obj.keys() {
                    authenticated_providers.insert(key.clone());
                }
            }
        }
    }

    // Catálogo en models-store.json
    let Ok(text) = fs::read_to_string(&models_file) else {
        return;
    };
    let Ok(val) = serde_json::from_str::<serde_json::Value>(&text) else {
        return;
    };
    let Some(store_obj) = val.as_object() else {
        return;
    };

    for (provider, provider_data) in store_obj {
        // Si hay auth.json, solo tomamos proveedores que tengan sesión iniciada
        if !authenticated_providers.is_empty() && !authenticated_providers.contains(provider) {
            continue;
        }

        let Some(models_list) = provider_data.get("models").and_then(|m| m.as_array()) else {
            continue;
        };

        for m in models_list {
            if let Some(model_id) = m.get("id").and_then(|i| i.as_str()) {
                let name = m.get("name").and_then(|n| n.as_str()).unwrap_or(model_id);
                out.push(ProviderModelInfo::new(provider, model_id, name, "pi"));
            }
        }
    }
}

// ── Lector de Antigravity (~/.gemini/antigravity-cli) ──────────────────────────

fn discover_antigravity_models(home: &Path, out: &mut Vec<ProviderModelInfo>) {
    let gemini_dir = home.join(".gemini").join("antigravity-cli");
    let token_file = gemini_dir.join("antigravity-oauth-token");
    let settings_file = gemini_dir.join("settings.json");

    let is_present = token_file.is_file() || settings_file.is_file();
    if !is_present {
        return;
    }

    // Modelos oficiales de Google autorizados en Antigravity
    let gemini_models = [
        ("gemini-2.5-pro", "Google: Gemini 2.5 Pro (Razonamiento & Código)"),
        ("gemini-2.5-flash", "Google: Gemini 2.5 Flash (Rápido & Documentación)"),
        ("gemini-2.0-flash", "Google: Gemini 2.0 Flash (Baja Latencia)"),
        ("gemini-2.0-pro", "Google: Gemini 2.0 Pro Experimental"),
    ];

    for (id, name) in gemini_models {
        out.push(ProviderModelInfo::new("google", id, name, "antigravity"));
    }
}

// ── Lector de Claude Code (~/.claude) ─────────────────────────────────────────

fn discover_claude_models(home: &Path, out: &mut Vec<ProviderModelInfo>) {
    let claude_dir = home.join(".claude");
    let creds_file = claude_dir.join(".credentials.json");

    if !creds_file.is_file() {
        return;
    }

    let claude_models = [
        ("claude-3-5-sonnet-20241022", "Anthropic: Claude 3.5 Sonnet (Recomendado Código)"),
        ("claude-3-5-haiku-20241022", "Anthropic: Claude 3.5 Haiku (Rápido Documentador)"),
        ("claude-3-opus-20240229", "Anthropic: Claude 3 Opus (Arquitectura Compleja)"),
    ];

    for (id, name) in claude_models {
        out.push(ProviderModelInfo::new("anthropic", id, name, "claude"));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_test_home(name: &str) -> std::path::PathBuf {
        let p = std::env::temp_dir().join(format!("cortex_cli_test_{}_{}", name, std::process::id()));
        let _ = fs::remove_dir_all(&p);
        fs::create_dir_all(&p).unwrap();
        p
    }

    #[test]
    fn discovers_from_mock_pi_directory() {
        let home = make_test_home("pi");
        let pi_agent = home.join(".pi").join("agent");
        fs::create_dir_all(&pi_agent).unwrap();

        fs::write(
            pi_agent.join("auth.json"),
            r#"{"openrouter": {"token": "xyz"}}"#,
        ).unwrap();

        fs::write(
            pi_agent.join("models-store.json"),
            r#"{
                "openrouter": {
                    "models": [
                        {"id": "anthropic/claude-3.5-sonnet", "name": "Anthropic: Claude 3.5 Sonnet"},
                        {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B"}
                    ]
                },
                "unauthenticated_provider": {
                    "models": [{"id": "foo", "name": "Foo"}]
                }
            }"#,
        ).unwrap();

        let models = discover_all_cli_models(&home);
        assert_eq!(models.len(), 2);
        assert_eq!(models[0].canonical_id, "openrouter:anthropic/claude-3.5-sonnet");
        assert_eq!(models[1].canonical_id, "openrouter:meta-llama/llama-3.3-70b-instruct");
    }

    #[test]
    fn filters_strictly_by_host_environment() {
        let home = make_test_home("filter");
        let pi_agent = home.join(".pi").join("agent");
        fs::create_dir_all(&pi_agent).unwrap();
        fs::write(pi_agent.join("auth.json"), r#"{"openrouter": {}}"#).unwrap();
        fs::write(
            pi_agent.join("models-store.json"),
            r#"{"openrouter": {"models": [{"id": "model-1", "name": "Model 1"}]}}"#,
        ).unwrap();

        let gemini = home.join(".gemini").join("antigravity-cli");
        fs::create_dir_all(&gemini).unwrap();
        fs::write(gemini.join("antigravity-oauth-token"), "token").unwrap();

        // Si el host es Antigravity, NUNCA debe incluir openrouter de Pi
        let agy_models = discover_models_for_host(&home, HostEnvironment::Antigravity);
        assert!(!agy_models.is_empty());
        assert!(agy_models.iter().all(|m| m.provider == "google"));

        // Si el host es Pi, NUNCA debe incluir google de Antigravity
        let pi_models = discover_models_for_host(&home, HostEnvironment::Pi);
        assert_eq!(pi_models.len(), 1);
        assert_eq!(pi_models[0].provider, "openrouter");
    }
}
