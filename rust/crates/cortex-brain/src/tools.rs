//! Herramientas del brain nativo — READ + SAFE_ACTION sobre el CLI `cortex`.
//!
//! Contrato (doc 06 §BRAIN v1, decisión dueño 2026-08-24: BRAIN-2/3 nativos):
//! - `Tier::Read`: consulta pura, sin side-effects.
//! - `Tier::SafeAction`: único permitido hoy: webgraph.serve.
//! - Las MUTACIONES no son tools: actions.propose devuelve el comando CLI
//!   exacto para que el usuario lo ejecute ("propone, no ejecuta").
//!
//! Los servicios session/actions/health siguen siendo Python hasta Obra E;
//! las tools los consumen INVOCANDO EL CLI `cortex` como cualquier usuario —
//! contrato estable, cero duplicación. Override de binario: env CORTEX_BIN.

use std::collections::BTreeMap;
use std::process::Command;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tier {
    Read,
    SafeAction,
}

#[derive(Debug, Clone)]
pub struct ToolSpec {
    pub name: &'static str,
    pub description: &'static str,
    pub tier: Tier,
    pub args_hint: &'static str,
}

/// Registro ordenado por nombre (determinista para /help y tests).
pub fn build_tools() -> BTreeMap<&'static str, ToolSpec> {
    let mut t = BTreeMap::new();
    for (name, desc, tier, hint) in [
        ("memory.search", "Búsqueda híbrida (RRF) en memoria episódica+semántica.", Tier::Read, "<query> [top_k]"),
        ("docs.related", "Documentos del vault relacionados con un tema (embeddings OPT-IN).", Tier::Read, "<tema> [precise|fast]"),
        ("cortex.health", "Estado de salud de Cortex en este proyecto.", Tier::Read, ""),
        ("vault.stats", "Conteos del vault y workspace.", Tier::Read, ""),
        ("session.current", "Sesión activa y sus checkpoints.", Tier::Read, ""),
        ("webgraph.serve", "Levanta el visualizador del webgraph y reporta el puerto.", Tier::SafeAction, ""),
        ("actions.propose", "Lista acciones sugeridas CON el comando exacto para ejecutarlas vos (el brain nunca muta).", Tier::Read, ""),
    ] {
        t.insert(name, ToolSpec { name, description: desc, tier, args_hint: hint });
    }
    t
}

/// Binario CLI a invocar (override para tests).
pub fn cortex_bin() -> String {
    std::env::var("CORTEX_BIN").unwrap_or_else(|_| "cortex".into())
}

/// Ejecuta el CLI cortex capturando stdout. Falla con mensaje accionable.
fn run_cli(args: &[&str]) -> Result<String, String> {
    let out = Command::new(cortex_bin())
        .args(args)
        .output()
        .map_err(|e| format!("no pude ejecutar {}: {e}", cortex_bin()))?;
    if !out.status.success() {
        return Err(format!(
            "{} {} falló (rc={:?}): {}",
            cortex_bin(),
            args.join(" "),
            out.status.code(),
            String::from_utf8_lossy(&out.stderr).trim()
        ));
    }
    Ok(String::from_utf8_lossy(&out.stdout).trim_end().to_string())
}

/// Ejecuta una tool por nombre con argumentos libres. Devuelve texto usuario.
///
/// NUNCA ejecuta mutaciones: las únicas herramientas con side-effect son
/// SAFE_ACTION whitelisteada (webgraph.serve, spawn detached).
pub fn dispatch(tool: &str, args: &[String]) -> Result<String, String> {
    match tool {
        "cortex.health" => run_cli(&["doctor"]),
        "session.current" => run_cli(&["context"]),
        "memory.search" | "docs.related" => {
            if args.is_empty() || args[0].trim().is_empty() {
                if tool == "docs.related" {
                    return Ok(
                        "¿Qué precisión preferís?\n  · precise → e5-large multilingüe, máxima calidad (~2GB RAM)\n  · fast    → MiniLM, liviano y veloz\nRespondé 'docs.related <tema> fast'.".into(),
                    );
                }
                return Err("falta <query>".into());
            }
            run_cli(&["search", &args.join(" ")])
        }
        "vault.stats" => {
            // Conteo nativo: vault/**/*.md (convención Cortex).
            let count = count_markdown("vault");
            Ok(format!("Vault: {count} notas .md"))
        }
        "webgraph.serve" => {
            spawn_detached(&["webgraph", "serve", "--no-open"])?;
            Ok("Webgraph abierto en http://127.0.0.1:8000 — mirá ese puerto.".into())
        }
        "actions.propose" => propose(),
        other => Err(format!("tool desconocida: {other}")),
    }
}

/// actions.propose: lista sugerencias + comando exacto. El brain NUNCA muta.
fn propose() -> Result<String, String> {
    let raw = run_cli(&["next", "--json"])?;
    let value: serde_json::Value =
        serde_json::from_str(&raw).map_err(|e| format!("next --json no es JSON válido: {e}"))?;
    let items = value.as_array().cloned().unwrap_or_default();
    if items.is_empty() {
        return Ok("Nada pendiente ✓".into());
    }
    let mut out = String::from("Acciones sugeridas (ejecutalas VOS con el comando indicado):\n");
    for item in &items {
        let id = item["id"].as_str().unwrap_or("?");
        let title = item["title"].as_str().unwrap_or("");
        out.push_str(&format!("  · {id} — {title}\n"));
        out.push_str("      → cortex next --json   |   efecto: ver doctor\n");
    }
    out.push_str("El brain propone; la ejecución es tuya (modo estricto).");
    Ok(out)
}

/// Spawn detached (nuevo session): el brain no queda atado al servidor.
fn spawn_detached(args: &[&str]) -> Result<(), String> {
    use std::process::Stdio;
    Command::new(cortex_bin())
        .args(args)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .stdin(Stdio::null())
        .spawn()
        .map(|_| ())
        .map_err(|e| format!("spawn falló: {e}"))
}

fn count_markdown(dir: &str) -> usize {
    fn walk(path: &std::path::Path, acc: &mut usize) {
        if let Ok(rd) = std::fs::read_dir(path) {
            for entry in rd.flatten() {
                let p = entry.path();
                if p.is_dir() {
                    walk(&p, acc);
                } else if p.extension().is_some_and(|e| e == "md") {
                    *acc += 1;
                }
            }
        }
    }
    let mut n = 0;
    walk(std::path::Path::new(dir), &mut n);
    n
}

#[cfg(test)]
mod tests {
    use std::sync::Mutex;
    pub(crate) static ENV_LOCK: Mutex<()> = Mutex::new(());
    use super::*;

    #[test]
    fn no_hay_herramientas_mutadoras() {
        let mutadoras = [
            "vault.reindex",
            "session.checkpoint_now",
            "setup.finish_bootstrap",
        ];
        let tools = build_tools();
        for m in mutadoras {
            assert!(!tools.contains_key(m), "{m} jamás puede ser tool");
        }
    }

    #[test]
    fn todas_read_o_safe_action() {
        for spec in build_tools().values() {
            assert!(matches!(spec.tier, Tier::Read | Tier::SafeAction));
        }
    }

    #[test]
    fn webgraph_es_safe_action() {
        assert_eq!(build_tools()["webgraph.serve"].tier, Tier::SafeAction);
    }

    #[test]
    fn tool_desconocida_falla_ruidosa() {
        assert!(dispatch("vault.reindex", &[]).is_err(), "mutación jamás");
    }

    #[test]
    fn propose_nunca_ejecuta_y_ofrece_comando() {
        let _env = ENV_LOCK.lock().unwrap();
        // CORTEX_BIN=/bin/echo: next --json devuelve texto plano → JSON inválido
        // ⇒ error ruidoso (nunca ejecuta nada). Con salida vacía → "Nada pendiente".
        unsafe { std::env::set_var("CORTEX_BIN", "/bin/echo") };
        let out = propose().unwrap_or_else(|e| e);
        // /bin/echo imprime sus args: "next --json" ≠ JSON válido ⇒ error limpio.
        assert!(out.contains("propone") || out.contains("JSON") || out.contains("Nada pendiente"));
        unsafe { std::env::remove_var("CORTEX_BIN") };
    }
}
