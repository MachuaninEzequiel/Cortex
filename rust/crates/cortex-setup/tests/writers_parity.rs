//! Paridad P8b: los writers canónicos de cortex-setup reproducen
//! byte-a-byte los archivos que escribe `cortex.documentation.writers`
//! sobre los casos congelados en bench/parity/golden_setup/writers.
//!
//! Oráculo: bench/parity/p8_writers_golden.py (reloj fijo 2026-08-24).

use std::path::PathBuf;

use chrono::{DateTime, Utc};
use serde_json::Value;

use cortex_setup::writers::{build_note, NoteRequest};

const GOLDEN: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../bench/parity/golden_setup/writers"
);

fn frozen_now() -> DateTime<Utc> {
    DateTime::parse_from_rfc3339("2026-08-24T12:34:56.789012Z")
        .expect("reloj del fixture")
        .with_timezone(&Utc)
}

#[test]
fn writers_byte_parity_over_golden_cases() {
    let raw = std::fs::read_to_string(format!("{GOLDEN}/inputs.json")).expect("inputs.json");
    let doc: Value = serde_json::from_str(&raw).expect("inputs.json válido");
    let cases = doc["cases"].as_array().expect("cases");

    let base = std::env::temp_dir().join(format!(
        "cortex-setup-writers-parity-{}",
        std::process::id()
    ));
    let _ = std::fs::remove_dir_all(&base);
    std::fs::create_dir_all(&base).unwrap();

    let now = frozen_now();
    let mut checked = 0usize;
    for case in cases {
        let name = case["case"].as_str().unwrap();
        let doc_type = case["doc_type"].as_str().unwrap();
        let scope = case["scope"].as_str().unwrap();
        let project_id = case["project_id"].as_str();
        let actor = case["actor"].as_str();

        let case_dir: PathBuf = base.join(name);
        let vault = case_dir.join("vault");
        std::fs::create_dir_all(&vault).unwrap();

        // pre_files (ej. ADR previo para auto-numeración).
        if let Some(pre) = case["pre_files"].as_object() {
            for (rel, content) in pre {
                let p = vault.join(rel);
                if let Some(parent) = p.parent() {
                    std::fs::create_dir_all(parent).unwrap();
                }
                std::fs::write(p, content.as_str().unwrap()).unwrap();
            }
        }

        let fields = case["fields"].as_object().expect("fields objeto").clone();
        let mut req =
            NoteRequest::from_json(doc_type, fields).unwrap_or_else(|e| panic!("{name}: {e}"));

        let out = build_note(&mut req, &vault, scope, project_id, actor, now)
            .unwrap_or_else(|e| panic!("{name}: build_note falló: {e}"));

        // La ruta debe coincidir con la del golden.
        let expected_rel = case["expected_rel"].as_str().unwrap();
        assert_eq!(
            out.path.strip_prefix(&case_dir).unwrap().to_string_lossy(),
            expected_rel,
            "{name}: ruta generada difiere"
        );

        // Byte-parity contra el archivo capturado de Python.
        let golden_bytes =
            std::fs::read(format!("{GOLDEN}/{name}/{expected_rel}")).expect("golden existe");
        assert_eq!(
            out.content.as_bytes(),
            golden_bytes.as_slice(),
            "{name}: contenido difiere del oráculo Python"
        );
        checked += 1;
    }
    assert_eq!(checked, 15, "cantidad de casos del fixture");
    let _ = std::fs::remove_dir_all(&base);
}
