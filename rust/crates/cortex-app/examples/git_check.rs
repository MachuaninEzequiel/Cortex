//! Verificador P5b: reconstrucción GIT-AWARE en Rust vs oráculo Python.
//!
//! Uso: git_check <workspace> <session_id>
//! Emite el mismo JSON canónico que el oráculo (con SHAs→{{SHA}} y ws→{{ROOT}}).

use std::path::{Path, PathBuf};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        return Err("uso: git_check <workspace> <session_id>".into());
    }
    let ws = Path::new(&args[1]);
    let sid = &args[2];

    let storage = cortex_app::session::SessionStorage::from_workspace(ws);
    let record = storage.load(sid)?;

    // Spec real dentro del workspace vivo.
    let spec_path = ws.join(&record.spec_path);
    let _ = &spec_path;
    let mut spec = cortex_app::documenter::spec_loader::load_spec(&spec_path);
    spec.path = PathBuf::from(format!(
        "{{{{ROOT}}}}/specs/{}",
        spec_path
            .file_name()
            .ok_or("spec sin nombre")?
            .to_string_lossy()
    ));

    let out = cortex_app::documenter::reconstruct_git(&record, &spec, ws, vec![])?;
    let mut json = serde_json::to_string_pretty(&out)?;
    // Normalización idéntica al oráculo: SHAs y ruta del workspace.
    let ws_str = ws.to_string_lossy().to_string();
    json = json.replace(&ws_str, "{{ROOT}}");
    let re_sha = regex::Regex::new(r"\b[0-9a-f]{40}\b").unwrap();
    json = re_sha.replace_all(&json, "{{SHA}}").to_string();
    println!("{json}");
    Ok(())
}
// PathBuf usado por load_spec interno
#[allow(dead_code)]
fn _t(_: PathBuf) {}
