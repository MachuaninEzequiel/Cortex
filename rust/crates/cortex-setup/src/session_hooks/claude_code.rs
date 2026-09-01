//! Porteo de cortex/session/hooks/adapters/claude_code.py (P8e).
//!
//! Instala una entrada `_cortex_managed` en el bloque nativo `hooks` de
//! `.claude/settings.json` (PostToolUse sobre Edit|Write|MultiEdit) que
//! emite un checkpoint a la Session activa.

use std::path::{Path, PathBuf};

use serde_json::{json, Value};

use super::{HookAdapter, HookStatus, InstallResult, UninstallResult};
use crate::ide::base::json_dump_utf8;

pub const CORTEX_HOOK_MARKER: &str = "_cortex_managed";
pub const CLAUDE_SETTINGS_RELATIVE: &str = ".claude/settings.json";
pub const HOOK_MATCHER: &str = "Edit|Write|MultiEdit";
pub const HOOK_COMMAND: &str = "cortex session checkpoint --source ide-hook --note 'edit via Claude Code' >/dev/null 2>&1 || true";

pub struct ClaudeCodeHookAdapter;

impl ClaudeCodeHookAdapter {
    #[allow(dead_code)]
    pub fn new() -> Self {
        ClaudeCodeHookAdapter
    }

    fn settings_path(&self, target_dir: &Path) -> PathBuf {
        target_dir.join(CLAUDE_SETTINGS_RELATIVE)
    }

    /// `_load`: {} si falta o está vacío; ValueError ante JSON inválido o
    /// raíz no-objeto (mensajes espejo).
    fn load(&self, path: &Path) -> Result<Value, String> {
        if !path.exists() {
            return Ok(json!({}));
        }
        let text =
            std::fs::read_to_string(path).map_err(|e| format!("read {}: {e}", path.display()))?;
        if text.trim().is_empty() {
            return Ok(json!({}));
        }
        let data: Value = serde_json::from_str(&text)
            .map_err(|e| format!("Invalid JSON in {}: {e}", path.display()))?;
        if !data.is_object() {
            return Err(format!(
                "Expected an object at the root of {}, got {}",
                path.display(),
                python_type_name(&data)
            ));
        }
        Ok(data)
    }
}

impl Default for ClaudeCodeHookAdapter {
    fn default() -> Self {
        Self::new()
    }
}

/// Nombre de tipo estilo Python para los mensajes de error.
fn python_type_name(v: &Value) -> &'static str {
    match v {
        Value::Object(_) => "dict",
        Value::Array(_) => "list",
        Value::String(_) => "str",
        Value::Number(_) => {
            if v.is_i64() || v.is_u64() {
                "int"
            } else {
                "float"
            }
        }
        Value::Bool(_) => "bool",
        Value::Null => "NoneType",
    }
}

fn cortex_hook_entry() -> Value {
    json!({
        "matcher": HOOK_MATCHER,
        "hooks": [{"type": "command", "command": HOOK_COMMAND}],
        CORTEX_HOOK_MARKER: true,
    })
}

fn has_cortex_hook(settings: &Value) -> bool {
    let Some(hooks) = settings.get("hooks").filter(|h| h.is_object()) else {
        return false;
    };
    let Some(Value::Array(entries)) = hooks.get("PostToolUse") else {
        return false;
    };
    entries.iter().any(|e| {
        e.is_object()
            && e.get(CORTEX_HOOK_MARKER)
                .is_some_and(|v| v.as_bool() == Some(true))
    })
}

/// `_inject_cortex_hook` con las validaciones de tipos de Python
/// (setdefault primero, chequeo de tipo después).
fn inject_cortex_hook(settings: &mut Value) -> Result<(), String> {
    let obj = settings.as_object_mut().expect("settings es objeto");
    if let Some(existing) = obj.get("hooks") {
        if !existing.is_object() {
            let got = python_type_name(existing);
            return Err(format!("settings.hooks must be an object, got {got}"));
        }
    }
    let hooks = obj.entry("hooks".to_string()).or_insert_with(|| json!({}));
    let hooks = hooks.as_object_mut().expect("hooks verificado objeto");
    if let Some(existing) = hooks.get("PostToolUse") {
        if !existing.is_array() {
            let got = python_type_name(existing);
            return Err(format!(
                "settings.hooks.PostToolUse must be a list, got {got}"
            ));
        }
    }
    hooks
        .entry("PostToolUse".to_string())
        .or_insert_with(|| json!([]))
        .as_array_mut()
        .expect("PostToolUse verificado lista")
        .push(cortex_hook_entry());
    Ok(())
}

/// `_remove_cortex_hook`: filtra la entrada marcada y colapsa contenedores
/// vacíos (PostToolUse → hooks → settings). Espejo exacto del orden de
/// operaciones de Python, incluido `{"hooks": {}}` → `{}`.
fn remove_cortex_hook(settings: &mut Value) {
    let Some(obj) = settings.as_object_mut() else {
        return;
    };
    // Python: hooks = settings.get("hooks", {}) — clave ausente o no-dict ⇒ no-op.
    if !matches!(obj.get("hooks"), Some(Value::Object(_))) {
        return;
    }
    let hooks = obj.get_mut("hooks").unwrap().as_object_mut().unwrap();
    // Python: entries = hooks.get("PostToolUse", []) — no-lista ⇒ no-op.
    if matches!(hooks.get("PostToolUse"), Some(v) if !v.is_array()) {
        return;
    }
    if let Some(Value::Array(entries)) = hooks.get_mut("PostToolUse") {
        entries.retain(|e| {
            !(e.is_object()
                && e.get(CORTEX_HOOK_MARKER)
                    .is_some_and(|v| v.as_bool() == Some(true)))
        });
    }
    let post_tool_use_vacia =
        !matches!(hooks.get("PostToolUse"), Some(Value::Array(a)) if !a.is_empty());
    if post_tool_use_vacia {
        hooks.remove("PostToolUse");
    }
    if hooks.is_empty() {
        obj.remove("hooks");
    }
}

impl HookAdapter for ClaudeCodeHookAdapter {
    fn name(&self) -> &'static str {
        "claude-code"
    }

    fn install(&self, target_dir: &Path) -> Result<InstallResult, String> {
        let path = self.settings_path(target_dir);
        let mut settings = self.load(&path)?;
        if has_cortex_hook(&settings) {
            return Ok(InstallResult {
                ide: self.name(),
                installed: true,
                modified_paths: vec![],
                message: format!("already installed in {}", path.display()),
            });
        }
        inject_cortex_hook(&mut settings)?;
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| format!("mkdir: {e}"))?;
        }
        std::fs::write(&path, format!("{}\n", json_dump_utf8(&settings)))
            .map_err(|e| format!("write {}: {e}", path.display()))?;
        Ok(InstallResult {
            ide: self.name(),
            installed: true,
            modified_paths: vec![path.clone()],
            message: format!("installed PostToolUse hook in {}", path.display()),
        })
    }

    fn uninstall(&self, target_dir: &Path) -> Result<UninstallResult, String> {
        let path = self.settings_path(target_dir);
        if !path.exists() {
            return Ok(UninstallResult {
                ide: self.name(),
                uninstalled: false,
                removed_paths: vec![],
                message: format!("{} does not exist", path.display()),
            });
        }
        let mut settings = self.load(&path)?;
        if !has_cortex_hook(&settings) {
            return Ok(UninstallResult {
                ide: self.name(),
                uninstalled: false,
                removed_paths: vec![],
                message: format!("no cortex-managed entry in {}", path.display()),
            });
        }
        remove_cortex_hook(&mut settings);
        let content = if !settings.as_object().expect("objeto").is_empty() {
            format!("{}\n", json_dump_utf8(&settings))
        } else {
            "{}\n".to_string()
        };
        std::fs::write(&path, content).map_err(|e| format!("write {}: {e}", path.display()))?;
        Ok(UninstallResult {
            ide: self.name(),
            uninstalled: true,
            removed_paths: vec![path.clone()],
            message: format!("removed cortex-managed entry from {}", path.display()),
        })
    }

    fn status(&self, target_dir: &Path) -> HookStatus {
        let path = self.settings_path(target_dir);
        if !path.exists() {
            return HookStatus {
                ide: self.name(),
                installed: false,
                detail: format!("{} does not exist", path.display()),
            };
        }
        let settings = match self.load(&path) {
            Ok(s) => s,
            Err(exc) => {
                return HookStatus {
                    ide: self.name(),
                    installed: false,
                    detail: format!("could not parse {}: {exc}", path.display()),
                }
            }
        };
        if has_cortex_hook(&settings) {
            HookStatus {
                ide: self.name(),
                installed: true,
                detail: format!("PostToolUse hook present in {}", path.display()),
            }
        } else {
            HookStatus {
                ide: self.name(),
                installed: false,
                detail: format!("no cortex-managed entry in {}", path.display()),
            }
        }
    }
}
