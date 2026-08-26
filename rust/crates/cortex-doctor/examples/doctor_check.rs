//! Gate P12B-4: reproduce `golden_doctor.txt` byte-a-byte.
//!
//! Uso: cargo run -p cortex-doctor --example doctor_check -- \
//!          ../bench/parity/.p12b-doctor

use std::path::{Path, PathBuf};

use cortex_doctor::checks::DoctorReport;
use cortex_doctor::doctor::{run_doctor, DoctorScope};
use cortex_enterprise::config::{build_enterprise_org_config, write_enterprise_config};

fn make_legacy(base: &Path, tag: &str, with_org: bool, with_sessions: bool) -> PathBuf {
    let root = base.join(tag).join("acme-api");
    std::fs::create_dir_all(root.join("vault/specs")).unwrap();
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    std::fs::write(
        root.join("vault/specs/spec.md"),
        "---\ntitle: Spec\ntags: [spec]\n---\n\n# Spec\n\nHello\n",
    )
    .unwrap();
    if with_org {
        let cfg = build_enterprise_org_config(
            "Acme Org",
            cortex_enterprise::models::OrgProfile::SmallCompany,
            true,
            false,
        )
        .unwrap();
        write_enterprise_config(&root, &cfg, None).unwrap();
        std::fs::create_dir_all(root.join("vault-enterprise")).unwrap();
    }
    if with_sessions {
        std::fs::create_dir_all(root.join(".cortex/sessions")).unwrap();
    }
    root
}

fn make_new_layout(base: &Path, tag: &str) -> PathBuf {
    let root = base.join(tag).join("acme-api");
    std::fs::create_dir_all(root.join(".cortex/vault/specs")).unwrap();
    std::fs::create_dir_all(root.join(".cortex/memory/chroma")).unwrap();
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    std::fs::write(
        root.join(".cortex/workspace.yaml"),
        "layout_version: 2\nprojects: []\n",
    )
    .unwrap();
    std::fs::write(
        root.join(".cortex/vault/specs/spec.md"),
        "---\ntitle: Spec\ntags: [spec]\n---\n\n# Spec\n\nHello\n",
    )
    .unwrap();
    root
}

/// Serializa un reporte al formato del golden: una línea JSON por check +
/// SUMMARY final con bools estilo Python.
fn render(report: &DoctorReport) -> String {
    let mut out = String::new();
    // Separadores por defecto de json.dumps: ", " y ": "; ensure_ascii=True.
    fn q(s: &str) -> String {
        let mut inner = String::new();
        for c in s.chars() {
            match c {
                '"' => inner.push_str("\\\""),
                '\\' => inner.push_str("\\\\"),
                '\n' => inner.push_str("\\n"),
                '\r' => inner.push_str("\\r"),
                '\t' => inner.push_str("\\t"),
                c if (c as u32) < 0x20 || (c as u32) > 0x7e => {
                    inner.push_str(&format!("\\u{:04x}", c as u32));
                }
                c => inner.push(c),
            }
        }
        format!("\"{inner}\"")
    }
    for c in &report.checks {
        out.push_str(&format!(
            "{{\"name\": {}, \"ok\": {}, \"severity\": {}, \"detail\": {}}}",
            q(&c.name),
            c.ok,
            q(&c.severity),
            q(&c.detail)
        ));
        out.push('\n');
    }
    out.push_str(&format!(
        "SUMMARY has_failures={} has_warnings={}\n",
        if report.has_failures() {
            "True"
        } else {
            "False"
        },
        if report.has_warnings() {
            "True"
        } else {
            "False"
        }
    ));
    out
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let golden_dir = args.get(1).expect("uso: doctor_check <golden_dir>");
    let expected =
        std::fs::read_to_string(Path::new(golden_dir).join("golden_doctor.txt")).unwrap();

    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let repo_root = manifest
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .parent()
        .unwrap();
    let workdir = repo_root
        .join("bench/parity")
        .join(Path::new(golden_dir).file_name().unwrap())
        .join(".work");
    if workdir.exists() {
        std::fs::remove_dir_all(&workdir).unwrap();
    }
    std::fs::create_dir_all(&workdir).unwrap();

    // 1. legacy project scope.
    let root = make_legacy(&workdir, "legacy", false, false);
    let s1 = render(&run_doctor(&root, DoctorScope::Project).unwrap());

    // 2. legacy + org.yaml → ALL.
    let root = make_legacy(&workdir, "legacy_all", true, false);
    let s2 = render(&run_doctor(&root, DoctorScope::All).unwrap());

    // 3. enterprise sin org.yaml: solo el bloque enterprise (early return).
    let root = make_legacy(&workdir, "ent_missing", false, false);
    let full = run_doctor(&root, DoctorScope::Enterprise).unwrap();
    let tail: Vec<_> = full
        .checks
        .iter()
        .filter(|c| c.name == "enterprise_config")
        .cloned()
        .collect();
    let s3 = render(&DoctorReport {
        project_root: full.project_root.clone(),
        checks: tail,
    });

    // 4. new layout v2.
    let root = make_new_layout(&workdir, "newlayout");
    let s4 = render(&run_doctor(&root, DoctorScope::Project).unwrap());

    // 5. legacy con sessions presentes.
    let root = make_legacy(&workdir, "with_sessions", false, true);
    let s5 = render(&run_doctor(&root, DoctorScope::Project).unwrap());

    // 6. autopilot.yaml con typo de modo → autopilot_mode_typo warn.
    let root = make_legacy(&workdir, "ap_typo", false, false);
    std::fs::write(root.join("autopilot.yaml"), "mode: auto\n").unwrap();
    let s6 = render(&run_doctor(&root, DoctorScope::Project).unwrap());

    // 7. autopilot end-to-end: policy real + sesión activa REAL abierta vía
    // SessionService nativo (gitless). Los checks de sesiones emiten stubs
    // contractuales; autopilot_policy refleja el YAML (espejo del golden).
    let root = make_legacy(&workdir, "ap_e2e", false, false);
    std::fs::write(
        root.join("autopilot.yaml"),
        "mode: assist\ndefault_budget_profile: deep_code\n",
    )
    .unwrap();
    {
        use cortex_app::session::service::SessionService;
        use cortex_app::session::SessionStorage;

        let storage = SessionStorage::new(root.join(".cortex").join("sessions"));
        SessionService::new(storage, &root)
            .open(
                "2026-05-16_demo",
                "vault/specs/2026-05-16_demo.md",
                "Demo summary",
            )
            .unwrap();
    }
    let s7 = render(&run_doctor(&root, DoctorScope::Project).unwrap());

    let names = [
        "legacy_project",
        "legacy_all",
        "enterprise_missing_org",
        "new_layout",
        "legacy_with_sessions",
        "autopilot_typo",
        "autopilot_e2e",
    ];
    let mut actual = String::new();
    for (name, section) in names.iter().zip([&s1, &s2, &s3, &s4, &s5, &s6, &s7]) {
        actual.push_str(&format!("### {name}\n{section}"));
    }

    if actual == expected {
        println!("[PASS] doctor_check byte-parity vs golden_doctor.txt");
        println!("✅ PARIDAD P12B-4");
    } else {
        let mut line = 1usize;
        for (e, a) in expected.chars().zip(actual.chars()) {
            if e != a {
                println!("[FAIL] primera diferencia en línea {line}: esperado {e:?} vs real {a:?}");
                break;
            }
            if e == '\n' {
                line += 1;
            }
        }
        if expected.len() != actual.len() && !expected.contains("[FAIL") {
            println!(
                "[FAIL] longitud distinta: {} vs {}",
                expected.len(),
                actual.len()
            );
        }
        let _ = std::fs::write("/tmp/doctor_expected.txt", &expected);
        let _ = std::fs::write("/tmp/doctor_actual.txt", &actual);
        eprintln!("detalle: /tmp/doctor_expected.txt vs /tmp/doctor_actual.txt");
        std::process::exit(1);
    }
}
