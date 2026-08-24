//! Paridad P1: el dump canónico de cortex-config debe ser byte-a-byte idéntico
//! al oráculo Python (bench/parity/config_dump.py) para cada fixture.

use std::fs;
use std::path::PathBuf;

fn parity_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../bench/parity")
}

#[test]
fn dumps_identicos_al_oraculo_python_para_cada_fixture() {
    let fixtures = parity_dir().join("fixtures_config");
    let goldens = parity_dir().join("golden_config");

    let mut revisados = 0;
    let entries = fs::read_dir(&fixtures)
        .expect("existe bench/parity/fixtures_config (corrélo desde el repo)");

    for entry in entries {
        let entry = entry.expect("entry legible");
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("yaml") {
            continue;
        }
        let stem = path.file_stem().unwrap().to_string_lossy().to_string();
        let yaml = fs::read_to_string(&path).expect("fixture legible");

        let rust_out = cortex_config::load_and_dump(&yaml);

        let golden_path = goldens.join(format!("{stem}.json"));
        let golden = fs::read_to_string(&golden_path).unwrap_or_else(|_| {
            panic!("falta golden {golden_path:?} — capturalo con capture_config_golden.py")
        });

        assert_eq!(
            rust_out, golden,
            "paridad rota para fixture {stem}: la implementación Rust difiere del oráculo Python"
        );
        revisados += 1;
    }
    assert!(revisados >= 8, "esperaba ≥8 fixtures, vi {revisados}");
}
