//! Puerto de `cortex/session/verification.py` — ejecución de hooks.
//!
//! Contrato idéntico: cada hook produce SIEMPRE un resultado (falla ⇒
//! passed=false, jamás panic); timeout ⇒ exit_code=-1; salida mergeada
//! (stderr con marcador `[stderr]`) y truncada conservando la cola.

use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use super::{truncate_output, VerificationHookResult, MAX_VERIFICATION_OUTPUT_BYTES};

const TIMEOUT_EXIT_CODE: i32 = -1;

pub struct VerificationRunner {
    repo_root: PathBuf,
    /// Capa soft adicional (paridad de firma con Python; el modelo trunca).
    #[allow(dead_code)]
    max_output_bytes: usize,
}

impl VerificationRunner {
    pub fn new(repo_root: PathBuf) -> Self {
        Self {
            repo_root,
            max_output_bytes: MAX_VERIFICATION_OUTPUT_BYTES,
        }
    }

    /// Ejecuta un hook vía `sh -c` con timeout por polling. Nunca entra en
    /// pánico por fallas del hook (non-zero/timeout); solo infraestructura.
    pub fn run_hook(&self, hook: &super::VerificationHook) -> VerificationHookResult {
        let start = Instant::now();
        let mut child = match Command::new("sh")
            .arg("-c")
            .arg(&hook.command)
            .current_dir(&self.repo_root)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
        {
            Ok(c) => c,
            Err(e) => {
                // Infraestructura rota: espejo del SubprocessError de Python.
                panic!("infra falla ejecutando hook {}: {e}", hook.name);
            }
        };

        let deadline = Duration::from_secs(hook.timeout_seconds);
        loop {
            match child.try_wait() {
                Ok(Some(status)) => {
                    let duration_ms = start.elapsed().as_millis() as u64;
                    let mut stdout_bytes = Vec::new();
                    let mut stderr_bytes = Vec::new();
                    if let Some(mut out) = child.stdout.take() {
                        use std::io::Read;
                        let _ = out.read_to_end(&mut stdout_bytes);
                    }
                    if let Some(mut err) = child.stderr.take() {
                        use std::io::Read;
                        let _ = err.read_to_end(&mut stderr_bytes);
                    }
                    let stdout = String::from_utf8_lossy(&stdout_bytes).to_string();
                    let stderr = String::from_utf8_lossy(&stderr_bytes).to_string();
                    return VerificationHookResult {
                        name: hook.name.clone(),
                        command: hook.command.clone(),
                        passed: status.success(),
                        exit_code: status.code().unwrap_or(TIMEOUT_EXIT_CODE),
                        // El modelo Python trunca al validar la construcción.
                        output: truncate_output(&self.compose_output(&stdout, &stderr)),
                        duration_ms,
                        run_at: now_iso(),
                    };
                }
                Ok(None) => {
                    if start.elapsed() >= deadline {
                        let _ = child.kill();
                        let _ = child.wait();
                        let duration_ms = start.elapsed().as_millis() as u64;
                        return VerificationHookResult {
                            name: hook.name.clone(),
                            command: hook.command.clone(),
                            passed: false,
                            exit_code: TIMEOUT_EXIT_CODE,
                            output: truncate_output(&format!(
                                "(timeout after {}s)",
                                hook.timeout_seconds
                            )),
                            duration_ms,
                            run_at: now_iso(),
                        };
                    }
                    std::thread::sleep(Duration::from_millis(25));
                }
                Err(e) => panic!("wait error: {e}"),
            }
        }
    }

    pub fn run_all(&self, hooks: &[super::VerificationHook]) -> Vec<VerificationHookResult> {
        hooks.iter().map(|h| self.run_hook(h)).collect()
    }

    /// `stdout` + `\n[stderr]\n` + stderr si hay ambos; stderr solo si único.
    fn compose_output(&self, stdout: &str, stderr: &str) -> String {
        if !stderr.is_empty() {
            if !stdout.is_empty() {
                format!("{stdout}\n[stderr]\n{stderr}")
            } else {
                stderr.to_string()
            }
        } else {
            stdout.to_string()
        }
    }
}

/// ISO-8601 UTC con microsegundos, formato compatible pydantic mode="json".
pub fn now_iso() -> String {
    let now = chrono::Utc::now();
    now.to_rfc3339_opts(chrono::SecondsFormat::Micros, true)
}
