//! Verificador de paridad P4 — Session primitive nativa vs oráculo Python.
//!
//! Uso: session_check <golden_dir>

use std::path::{Path, PathBuf};

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    std::process::exit(1);
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        fail("uso: session_check <golden_dir>");
    }
    let gdir = Path::new(&args[1]);

    // ── Cargar y validar cada YAML con los modelos serde ──
    let mut yamls: Vec<PathBuf> = std::fs::read_dir(gdir)
        .expect("golden dir")
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("yaml"))
        .collect();
    yamls.sort();

    if yamls.is_empty() {
        fail("sin YAMLs en el golden dir");
    }

    for yml in &yamls {
        let text = std::fs::read_to_string(yml).unwrap_or_else(|e| fail(&format!("{e}")));
        let record: cortex_app::session::SessionRecord = serde_yaml::from_str(&text)
            .unwrap_or_else(|e| fail(&format!("{} no deserializa: {e}", yml.display())));
        record
            .validate()
            .unwrap_or_else(|e| fail(&format!("{} inválido: {e}", yml.display())));

        // Raíz del workspace para normalización: padre del directorio del spec.
        let spec = Path::new(&record.spec_path);
        let ws = spec
            .parent()
            .and_then(|p| p.parent())
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_default();

        let got = cortex_app::session::canonical_json_normalized(&record, &ws);
        let stem = yml.file_stem().unwrap().to_string_lossy().to_string();
        let golden_dump = std::fs::read_to_string(gdir.join(format!("dump_{stem}.json")))
            .unwrap_or_else(|e| fail(&format!("falta dump_{stem}.json: {e}")));
        if got != golden_dump {
            eprintln!("--- rust ---\n{got}\n--- golden ---\n{golden_dump}");
            fail(&format!("dump canónico difiere para {stem}"));
        }
        println!("✅ {} carga+valida+dump idéntico", stem);
    }

    // ── Active pointer ──
    let pointer_golden =
        std::fs::read_to_string(gdir.join("active_pointer.txt")).expect("active_pointer");
    // El verificador reconstruye el storage apuntando al MISMO dir dorado.
    let storage = cortex_app::session::SessionStorage::new(gdir.to_path_buf());
    match storage.get_active_session_id() {
        // Python escribe el puntero sin newline; comparamos trimmeado.
        Some(id) if id == pointer_golden.trim() => {}
        other => fail(&format!(
            "active pointer difiere: golden={pointer_golden:?} rust={other:?}"
        )),
    }
    println!("✅ active pointer idéntico");

    // ── load() desde storage (validación en lectura) ──
    for yml in &yamls {
        let sid = yml.file_stem().unwrap().to_string_lossy().to_string();
        let rec = storage
            .load(&sid)
            .unwrap_or_else(|e| fail(&format!("storage.load({sid}): {e}")));
        assert_eq!(rec.session_id, sid);
    }
    println!("✅ storage.load valida todos");

    // ── infer_mode table ──
    let tabla_texto = std::fs::read_to_string(gdir.join("infer_mode.json")).expect("infer_mode");
    let tabla: serde_json::Value = serde_json::from_str(&tabla_texto).expect("json");
    let mk = |source: &str, ts: &str| cortex_app::session::Checkpoint {
        timestamp: ts.to_string(),
        source: serde_yaml::from_str(&format!("\"{source}\"")).unwrap(),
        verified_claims: vec![],
        unverified_claims: vec![],
        artifacts_touched: vec![],
        note: String::new(),
        phase: None,
    };
    let casos: Vec<(&str, Vec<cortex_app::session::Checkpoint>)> = vec![
        ("vacio", vec![]),
        ("ci_review", vec![mk("ci-bot", "2026-08-24T00:00:00+00:00")]),
        (
            "managed",
            vec![
                mk("cortex-sync", "2026-08-24T00:00:00+00:00"),
                mk("cortex-code-implementer", "2026-08-24T00:00:01+00:00"),
            ],
        ),
        (
            "observed",
            vec![
                mk("ide-hook", "2026-08-24T00:00:00+00:00"),
                mk("cortex-sync", "2026-08-24T00:00:01+00:00"),
            ],
        ),
    ];
    for (nombre, cps) in casos {
        let got = cortex_app::session::infer_mode(&cps);
        let want = tabla[nombre].as_str().unwrap();
        let mode_str = serde_json::to_value(got)
            .unwrap()
            .as_str()
            .unwrap_or("")
            .to_string();
        if mode_str != want {
            fail(&format!(
                "infer_mode[{nombre}] = {mode_str}, esperaba {want}"
            ));
        }
    }
    println!("✅ infer_mode: 4/4 casos idénticos");

    println!("\nPARIDAD SESSION COMPLETA");
}
