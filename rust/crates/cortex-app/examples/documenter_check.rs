//! Verificador P5a: reconstrucción gitless en Rust vs oráculo Python.
//!
//! Uso: documenter_check <golden_dir>

use std::path::{Path, PathBuf};

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    std::process::exit(1);
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        fail("uso: documenter_check <golden_dir>");
    }
    let gdir = Path::new(&args[1]);

    // Entradas commiteadas: session.yaml + spec_copy.md
    let yml_path = gdir.join("session.yaml");
    let yml = std::fs::read_to_string(&yml_path).expect("session.yaml");
    let record: cortex_app::session::SessionRecord =
        serde_yaml::from_str(&yml).expect("session.yaml inválido");
    record.validate().expect("session.yaml no valida");

    let spec_copy = gdir.join("spec_copy.md");
    let mut spec = cortex_app::documenter::spec_loader::load_spec(&spec_copy);
    // La ruta original se normaliza a {{ROOT}}/specs/<file> en el dump.
    spec.path = PathBuf::from(format!(
        "{{{{ROOT}}}}/specs/{}",
        spec_copy.file_name().unwrap().to_string_lossy()
    ));

    let out = cortex_app::documenter::reconstruct_gitless(&record, &spec, vec![])
        .unwrap_or_else(|e| fail(&format!("reconstruct: {e}")));

    let sid = std::fs::read_to_string(gdir.join("session_id.txt"))
        .unwrap_or_default()
        .trim()
        .to_string();
    if sid != out.session_id {
        fail(&format!("session_id difiere: {sid} vs {}", out.session_id));
    }

    let golden_text =
        std::fs::read_to_string(gdir.join(format!("dump_{sid}.json"))).expect("dump golden");
    let got = serde_json::to_string_pretty(&out).unwrap() + "\n";
    if got != golden_text {
        eprintln!("--- rust ---\n{got}\n--- golden ---\n{golden_text}");
        fail("dump del reconstructor difiere del oráculo");
    }
    println!(
        "✅ reconstrucción gitless idéntica: touched={:?} in_scope={:?} status={} adrs={}",
        out.files_touched,
        out.in_scope_files,
        out.suggested_status,
        out.suggested_adrs.len()
    );
    println!("\nPARIDAD DOCUMENTER COMPLETA");
}
