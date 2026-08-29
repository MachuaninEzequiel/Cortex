//! Integración con Herdr para Cortex Companion & Co-Pilot.

use serde::Deserialize;
use std::path::Path;
use std::process::{Command, Stdio};

#[derive(Debug, Clone, Default, Deserialize)]
pub struct HerdrAgentInfo {
    pub pane_id: String,
    pub agent: Option<String>,
    pub agent_status: Option<String>,
    pub cwd: Option<String>,
    pub focused: bool,
}

#[derive(Debug, Clone, Default, Deserialize)]
#[allow(dead_code)]
struct SnapshotPanes {
    #[serde(default)]
    panes: Vec<SnapshotPaneItem>,
    pub focused_pane_id: Option<String>,
}

#[derive(Debug, Clone, Default, Deserialize)]
struct SnapshotPaneItem {
    pub pane_id: String,
    pub agent: Option<String>,
    pub agent_status: Option<String>,
    pub cwd: Option<String>,
    pub focused: bool,
}

#[derive(Debug, Clone, Default, Deserialize)]
struct SnapshotWrapper {
    pub result: Option<SnapshotResult>,
}

#[derive(Debug, Clone, Default, Deserialize)]
struct SnapshotResult {
    pub snapshot: Option<SnapshotPanes>,
}

#[derive(Debug, Clone, Default, Deserialize)]
struct PluginPaneOpenedWrapper {
    pub result: Option<PluginPaneOpenedResult>,
}

#[derive(Debug, Clone, Default, Deserialize)]
struct PluginPaneOpenedResult {
    pub plugin_pane: Option<PluginPaneItem>,
}

#[derive(Debug, Clone, Default, Deserialize)]
struct PluginPaneItem {
    pub pane: Option<SnapshotPaneItem>,
}

/// Consulta a Herdr para detectar el pane de agente más relevante en el workspace.
pub fn detect_target_agent(project_root: &Path) -> Option<HerdrAgentInfo> {
    let output = Command::new("herdr")
        .args(["api", "snapshot"])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .output()
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let parsed: SnapshotWrapper = serde_json::from_slice(&output.stdout).ok()?;
    let snapshot = parsed.result?.snapshot?;
    let root_str = project_root
        .canonicalize()
        .ok()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|| project_root.to_string_lossy().to_string());

    let matching_panes: Vec<HerdrAgentInfo> = snapshot
        .panes
        .iter()
        .filter(|p| {
            if let Some(cwd) = &p.cwd {
                cwd.contains(&root_str) || root_str.contains(cwd)
            } else {
                false
            }
        })
        .map(|p| HerdrAgentInfo {
            pane_id: p.pane_id.clone(),
            agent: p.agent.clone(),
            agent_status: p.agent_status.clone(),
            cwd: p.cwd.clone(),
            focused: p.focused,
        })
        .collect();

    if let Some(agent_pane) = matching_panes.iter().find(|p| p.agent.is_some()) {
        return Some(agent_pane.clone());
    }

    if let Some(first) = matching_panes.into_iter().next() {
        return Some(first);
    }

    snapshot
        .panes
        .into_iter()
        .find(|p| p.agent.is_some())
        .map(|p| HerdrAgentInfo {
            pane_id: p.pane_id,
            agent: p.agent,
            agent_status: p.agent_status,
            cwd: p.cwd,
            focused: p.focused,
        })
}

/// Envía texto al pane del agente. **No usar desde el Companion** (doc 17 D4:
/// el HUD copia con OSC 52; el usuario pega). Queda por si un atajo de herdr
/// lo necesita fuera de producto.
#[allow(dead_code)]
pub fn send_text_to_pane(pane_id: &str, text: &str) -> Result<(), String> {
    let output = Command::new("herdr")
        .args(["pane", "send-text", pane_id, text])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .output()
        .map_err(|e| format!("Error al invocar herdr pane send-text: {e}"))?;

    if output.status.success() {
        Ok(())
    } else {
        let err = String::from_utf8_lossy(&output.stderr);
        Err(format!("herdr pane send-text falló: {err}"))
    }
}

/// Reporta estado del agente de Cortex al sidebar nativo de Herdr.
pub fn report_agent_status(
    pane_id: Option<&str>,
    agent_label: &str,
    state: &str,
    status_text: &str,
) {
    let mut cmd = Command::new("herdr");
    cmd.args(["pane", "report-agent"]);
    if let Some(pid) = pane_id {
        cmd.arg(pid);
    } else {
        cmd.arg("--current");
    }
    cmd.args([
        "--source",
        "cortex",
        "--agent",
        agent_label,
        "--state",
        state,
        "--custom-status",
        status_text,
    ]);
    cmd.stdin(Stdio::null());
    cmd.stdout(Stdio::null());
    cmd.stderr(Stdio::null());
    let _ = cmd.output();
}

/// Reporta metadatos de Cortex al sidebar nativo de Herdr.
pub fn report_metadata(pane_id: Option<&str>, status_text: &str) -> Result<(), String> {
    let mut cmd = Command::new("herdr");
    cmd.args(["pane", "report-metadata"]);
    if let Some(pid) = pane_id {
        cmd.arg(pid);
    } else {
        cmd.arg("--current");
    }
    cmd.args([
        "--source",
        "cortex",
        "--title",
        "Cortex",
        "--display-agent",
        "Cortex",
        "--custom-status",
        status_text,
    ]);
    cmd.stdin(Stdio::null());
    cmd.stdout(Stdio::null());
    cmd.stderr(Stdio::null());

    let output = cmd
        .output()
        .map_err(|e| format!("Error al invocar herdr report-metadata: {e}"))?;
    if output.status.success() {
        Ok(())
    } else {
        Err("herdr report-metadata no pudo actualizarse".into())
    }
}

/// Abre un dock lateral izquierdo (30% Cortex / 70% Agente) en Herdr.
pub fn spawn_split_sidecar(project_root: &Path) -> Result<(), String> {
    let cwd_str = project_root.to_string_lossy().to_string();
    let target = detect_target_agent(project_root);

    let mut cmd = Command::new("herdr");
    cmd.args([
        "plugin",
        "pane",
        "open",
        "--plugin",
        "cortex.companion",
        "--entrypoint",
        "sidecar",
        "--placement",
        "split",
        "--direction",
        "right",
        "--cwd",
        &cwd_str,
    ]);
    cmd.stdin(Stdio::null());
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());

    let output = cmd
        .output()
        .map_err(|e| format!("Error al invocar herdr plugin pane open: {e}"))?;
    if !output.status.success() {
        let err = String::from_utf8_lossy(&output.stderr);
        return Err(format!("herdr plugin pane open falló: {err}"));
    }

    let parsed: Option<PluginPaneOpenedWrapper> = serde_json::from_slice(&output.stdout).ok();
    if let Some(opened) = parsed.and_then(|p| p.result?.plugin_pane?.pane) {
        let new_id = opened.pane_id;
        if let Some(tgt) = target {
            // Pone a Cortex a la izquierda y al agente a la derecha
            let _ = Command::new("herdr")
                .args([
                    "pane",
                    "swap",
                    "--source-pane",
                    &new_id,
                    "--target-pane",
                    &tgt.pane_id,
                ])
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .output();
        }
        // Ajusta el ratio al 30% para el dock lateral
        let _ = Command::new("herdr")
            .args([
                "pane",
                "resize",
                "--direction",
                "right",
                "--amount",
                "-0.20",
                "--pane",
                &new_id,
            ])
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .output();

        report_agent_status(Some(&new_id), "cortex", "working", "Sidecar 30%");
        let _ = report_metadata(Some(&new_id), "30% Dock");
    }

    Ok(())
}

/// Abre el HUD flotante inferior (Bottom Drawer a 25% altura) en Herdr.
pub fn spawn_float_hud(project_root: &Path) -> Result<(), String> {
    let cwd_str = project_root.to_string_lossy().to_string();
    let mut cmd = Command::new("herdr");
    cmd.args([
        "plugin",
        "pane",
        "open",
        "--plugin",
        "cortex.companion",
        "--entrypoint",
        "float",
        "--placement",
        "split",
        "--direction",
        "down",
        "--cwd",
        &cwd_str,
    ]);
    cmd.stdin(Stdio::null());
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());

    let output = cmd
        .output()
        .map_err(|e| format!("Error al abrir HUD inferior en herdr: {e}"))?;
    if !output.status.success() {
        let err = String::from_utf8_lossy(&output.stderr);
        return Err(format!("herdr plugin pane open falló: {err}"));
    }

    let parsed: Option<PluginPaneOpenedWrapper> = serde_json::from_slice(&output.stdout).ok();
    if let Some(opened) = parsed.and_then(|p| p.result?.plugin_pane?.pane) {
        let new_id = opened.pane_id;
        // Ajusta la altura a 25% para que el agente quede al 75% arriba
        let _ = Command::new("herdr")
            .args([
                "pane",
                "resize",
                "--direction",
                "down",
                "--amount",
                "-0.25",
                "--pane",
                &new_id,
            ])
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .output();

        report_agent_status(Some(&new_id), "cortex", "working", "Bottom HUD");
        let _ = report_metadata(Some(&new_id), "Bottom HUD");
    }

    Ok(())
}

/// Abre el modo Co-Pilot en split en Herdr.
pub fn spawn_copilot_split(project_root: &Path) -> Result<(), String> {
    let cwd_str = project_root.to_string_lossy().to_string();
    let mut cmd = Command::new("herdr");
    cmd.args([
        "plugin",
        "pane",
        "open",
        "--plugin",
        "cortex.companion",
        "--entrypoint",
        "copilot",
        "--placement",
        "split",
        "--direction",
        "right",
        "--cwd",
        &cwd_str,
    ]);
    cmd.stdin(Stdio::null());
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());

    let output = cmd
        .output()
        .map_err(|e| format!("Error al abrir copilot en herdr: {e}"))?;
    if !output.status.success() {
        let err = String::from_utf8_lossy(&output.stderr);
        return Err(format!("herdr plugin pane open falló: {err}"));
    }

    let parsed: Option<PluginPaneOpenedWrapper> = serde_json::from_slice(&output.stdout).ok();
    if let Some(opened) = parsed.and_then(|p| p.result?.plugin_pane?.pane) {
        let new_id = opened.pane_id;
        let _ = Command::new("herdr")
            .args([
                "pane",
                "resize",
                "--direction",
                "right",
                "--amount",
                "-0.15",
                "--pane",
                &new_id,
            ])
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .output();

        report_agent_status(Some(&new_id), "cortex", "working", "Co-Pilot Activo");
        let _ = report_metadata(Some(&new_id), "Co-Pilot");
    }

    Ok(())
}

pub const DEFAULT_SIDECAR_RATIO: f32 = 0.30;
pub const DEFAULT_FLOAT_RATIO: f32 = 0.25;
pub const DEFAULT_COPILOT_RATIO: f32 = 0.35;

pub fn build_plugin_open_args<'a>(
    entrypoint: &'a str,
    direction: &'a str,
    cwd: &'a str,
) -> Vec<&'a str> {
    vec![
        "plugin",
        "pane",
        "open",
        "--plugin",
        "cortex.companion",
        "--entrypoint",
        entrypoint,
        "--placement",
        "split",
        "--direction",
        direction,
        "--cwd",
        cwd,
    ]
}

pub fn build_resize_args<'a>(
    direction: &'a str,
    amount: &'a str,
    pane_id: &'a str,
) -> Vec<&'a str> {
    vec![
        "pane",
        "resize",
        "--direction",
        direction,
        "--amount",
        amount,
        "--pane",
        pane_id,
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_ratios_are_honest() {
        assert!((DEFAULT_SIDECAR_RATIO - 0.30).abs() < f32::EPSILON);
        assert!((DEFAULT_FLOAT_RATIO - 0.25).abs() < f32::EPSILON);
        assert!((DEFAULT_COPILOT_RATIO - 0.35).abs() < f32::EPSILON);
    }

    #[test]
    fn sidecar_spawn_args_match_protocol() {
        let args = build_plugin_open_args("sidecar", "right", "/tmp/proj");
        assert_eq!(args[0], "plugin");
        assert_eq!(args[1], "pane");
        assert_eq!(args[2], "open");
        assert_eq!(args[4], "cortex.companion");
        assert_eq!(args[6], "sidecar");
        assert_eq!(args[10], "right");
        assert_eq!(args[12], "/tmp/proj");
    }

    #[test]
    fn resize_args_match_protocol() {
        let args = build_resize_args("right", "-0.20", "pane-123");
        assert_eq!(args[0], "pane");
        assert_eq!(args[1], "resize");
        assert_eq!(args[3], "right");
        assert_eq!(args[5], "-0.20");
        assert_eq!(args[7], "pane-123");
    }
}
