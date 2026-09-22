//! Detector de Entorno Host (Antigravity, Pi, Claude Code, etc.) y Políticas de Proveedor.
//!
//! Garantiza el cumplimiento de Términos de Servicio (ToS) y límites de runtime,
//! evitando que se utilicen credenciales de un host fuera de su CLI/IDE autorizado.

use std::path::Path;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HostEnvironment {
    Antigravity,
    Pi,
    ClaudeCode,
    Cursor,
    Codex,
    OpenCode,
    StandaloneDesktop,
}

impl HostEnvironment {
    pub fn as_str(&self) -> &'static str {
        match self {
            HostEnvironment::Antigravity => "antigravity",
            HostEnvironment::Pi => "pi",
            HostEnvironment::ClaudeCode => "claude_code",
            HostEnvironment::Cursor => "cursor",
            HostEnvironment::Codex => "codex",
            HostEnvironment::OpenCode => "opencode",
            HostEnvironment::StandaloneDesktop => "standalone_desktop",
        }
    }

    pub fn display_name(&self) -> &'static str {
        match self {
            HostEnvironment::Antigravity => "Google Antigravity (agy / Gemini CLI)",
            HostEnvironment::Pi => "Pi Agent (pi.dev)",
            HostEnvironment::ClaudeCode => "Claude Code (Anthropic)",
            HostEnvironment::Cursor => "Cursor IDE",
            HostEnvironment::Codex => "Codex Agent",
            HostEnvironment::OpenCode => "OpenCode Environment",
            HostEnvironment::StandaloneDesktop => "Cortex Brain Desktop",
        }
    }

    pub fn policy_description(&self) -> &'static str {
        match self {
            HostEnvironment::Antigravity => {
                "Política estricta de Google: Únicamente modelos Gemini / Google autorizados en la sesión de Antigravity."
            }
            HostEnvironment::Pi => {
                "Política Pi: Proveedores autenticados en ~/.pi/agent/auth.json (OpenRouter, Codex, xAI)."
            }
            HostEnvironment::ClaudeCode => {
                "Política Claude: Modelos de la suscripción directa de Anthropic."
            }
            HostEnvironment::Cursor => "Política Cursor: Modelos configurados en el IDE de Cursor.",
            HostEnvironment::Codex => "Política Codex: Modelos configurados para Codex.",
            HostEnvironment::OpenCode => "Política OpenCode: Modelos configurados para OpenCode.",
            HostEnvironment::StandaloneDesktop => {
                "Modo Standalone: Todos los modelos y proveedores de los CLIs instalados en la máquina."
            }
        }
    }

    /// Comprueba si un proveedor ('google', 'openrouter', 'anthropic', etc.) está legalmente
    /// y técnicamente autorizado en este host.
    pub fn is_provider_allowed(&self, provider: &str) -> bool {
        let prov = provider.trim().to_ascii_lowercase();
        match self {
            HostEnvironment::Antigravity => prov == "google" || prov == "gemini",
            HostEnvironment::Pi => {
                // Pi nunca debe consumir credenciales de Google Antigravity
                prov != "google" && prov != "gemini"
            }
            HostEnvironment::ClaudeCode => prov == "anthropic",
            HostEnvironment::Cursor => true,
            HostEnvironment::Codex => prov == "openai" || prov == "openai-codex",
            HostEnvironment::OpenCode => true,
            HostEnvironment::StandaloneDesktop => true,
        }
    }
}

/// Detecta el HostEnvironment activo a partir de variables de entorno y archivos del proyecto.
pub fn detect_host(project_root: Option<&Path>) -> HostEnvironment {
    // 1. Detección por Variables de Entorno del proceso
    if std::env::var_os("ANTIGRAVITY_SESSION").is_some()
        || std::env::var_os("GEMINI_CLI").is_some()
        || std::env::var_os("ANTIGRAVITY_IDE").is_some()
        || std::env::var_os("GOOGLE_CLOUD_PROJECT").is_some()
    {
        return HostEnvironment::Antigravity;
    }

    if std::env::var_os("PI_SESSION").is_some()
        || std::env::var_os("PI_AGENT").is_some()
        || std::env::var_os("PI_HOME").is_some()
    {
        return HostEnvironment::Pi;
    }

    if std::env::var_os("CLAUDE_CODE_ENTRYPOINT").is_some()
        || std::env::var_os("CLAUDE_SESSION_ID").is_some()
    {
        return HostEnvironment::ClaudeCode;
    }

    if std::env::var_os("CURSOR_PROJECT").is_some()
        || std::env::var_os("CURSOR_TRACE").is_some()
    {
        return HostEnvironment::Cursor;
    }

    // 2. Detección por artefactos y pistas en el Workspace
    if let Some(root) = project_root {
        if root.join("GEMINI.md").is_file() || root.join(".gemini").is_dir() {
            return HostEnvironment::Antigravity;
        }
        if root.join(".pi").is_dir() || root.join("cortex-pi").is_dir() {
            return HostEnvironment::Pi;
        }
        if root.join("CLAUDE.md").is_file() {
            return HostEnvironment::ClaudeCode;
        }
        if root.join(".cursor").is_dir() {
            return HostEnvironment::Cursor;
        }
    }

    // 3. Fallback a Standalone Desktop
    HostEnvironment::StandaloneDesktop
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn antigravity_blocks_external_providers() {
        let env = HostEnvironment::Antigravity;
        assert!(env.is_provider_allowed("google"));
        assert!(env.is_provider_allowed("gemini"));
        assert!(!env.is_provider_allowed("anthropic"));
        assert!(!env.is_provider_allowed("openrouter"));
        assert!(!env.is_provider_allowed("openai"));
    }

    #[test]
    fn pi_blocks_google_subscription_export() {
        let env = HostEnvironment::Pi;
        assert!(env.is_provider_allowed("openrouter"));
        assert!(env.is_provider_allowed("openai-codex"));
        assert!(env.is_provider_allowed("xai"));
        assert!(!env.is_provider_allowed("google"));
        assert!(!env.is_provider_allowed("gemini"));
    }

    #[test]
    fn claude_only_allows_anthropic() {
        let env = HostEnvironment::ClaudeCode;
        assert!(env.is_provider_allowed("anthropic"));
        assert!(!env.is_provider_allowed("google"));
        assert!(!env.is_provider_allowed("openai"));
    }
}
