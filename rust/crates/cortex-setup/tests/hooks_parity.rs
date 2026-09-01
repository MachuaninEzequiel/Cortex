//! Paridad P8e: installer/uninstaller de session hooks byte-a-byte contra
//! el oráculo Python (`bench/parity/archive/p8_hooks_golden.py` +
//! `bench/parity/archive/golden_setup/hooks/`).
//!
//! Cada paso es un fixture target_dir independiente con semántica espejo
//! exacta del capturador; se compara el payload del resultado (normalizado
//! `{{TARGET}}`) y el árbol de archivos resultante.
//!
//! NOTA de alcance: los casos con JSON inválido quedan FUERA del gate a
//! propósito — el detalle del error embebe el texto de json.JSONDecodeError
//! de Python, que no es replicable byte-a-byte desde serde_json (cosmética
//! de error-path documentada en p8_hooks_golden.py).

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU32, Ordering};

use serde_json::{json, Value};

use cortex_setup::session_hooks::default_installer;

const GOLDEN: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../bench/parity/archive/golden_setup/hooks"
);

// Preseeds — DEBEN ser idénticos a p8_hooks_golden.py.
const CLAUDE_EXISTING: &str = "{\n  \"permissions\": {\n    \"allow\": [\n      \"Bash\"\n    ]\n  },\n  \"hooks\": {\n    \"PostToolUse\": [\n      {\n        \"matcher\": \"WebSearch\",\n        \"hooks\": [\n          {\n            \"type\": \"command\",\n            \"command\": \"echo usuario\"\n          }\n        ]\n      }\n    ]\n  }\n}\n";
const CURSOR_EXISTING: &str = "#!/bin/sh\n# Mi propio hook.\necho 'post commit propio'\n";
const OPENCODE_EXISTING: &str = "# Mis hooks\n\nContenido propio del usuario.\n";
const PI_EXISTING: &str = "saludar:\n    echo hola\n";

const NOMARKER_CLAUDE: &str = "{\n  \"theme\": \"dark\"\n}\n";
const NOMARKER_CURSOR: &str = "#!/bin/sh\necho solo usuario\n";
const NOMARKER_OPENCODE: &str = "# Solo usuario\n";
const NOMARKER_PI: &str = "otra:\n    echo otra\n";

const CURSOR_NOSHEBANG: &str = "echo sin shebang\n";

static CASE_SEQ: AtomicU32 = AtomicU32::new(0);

fn seed(target: &Path, rel: &str, content: &str) {
    let p = target.join(rel);
    if let Some(parent) = p.parent() {
        std::fs::create_dir_all(parent).expect("mkdir seed");
    }
    std::fs::write(p, content).expect("write seed");
}

fn normalize(text: &str, target: &Path) -> String {
    text.replace(&target.to_string_lossy().to_string(), "{{TARGET}}")
}

fn snapshot(target: &Path) -> BTreeMap<String, String> {
    fn walk(dir: &Path, out: &mut Vec<PathBuf>) {
        if let Ok(entries) = std::fs::read_dir(dir) {
            for e in entries.flatten() {
                let p = e.path();
                if p.is_dir() {
                    walk(&p, out);
                } else if p.is_file() {
                    out.push(p);
                }
            }
        }
    }
    let mut files = BTreeMap::new();
    let mut paths = Vec::new();
    walk(target, &mut paths);
    for full in paths {
        let rel = full
            .strip_prefix(target)
            .expect("bajo target")
            .to_string_lossy()
            .replace('\\', "/");
        let content = std::fs::read_to_string(&full)
            .unwrap_or_else(|e| panic!("no UTF-8 en {}: {e}", full.display()));
        files.insert(rel, normalize(&content, target));
    }
    files
}

fn files_json(files: &std::collections::BTreeMap<String, String>) -> Value {
    Value::Object(files.iter().map(|(k, v)| (k.clone(), json!(v))).collect())
}

/// Prepara el fixture para un caso y devuelve el target.
fn setup_case(target: &Path, ide: &str, case: &str) {
    match case {
        "install_fresh"
        | "install_idempotent"
        | "status_missing"
        | "uninstall_installed"
        | "uninstall_missing"
        | "status_installed"
        | "status_uninstalled" => {}
        "install_existing" => match ide {
            "claude-code" => seed(target, ".claude/settings.json", CLAUDE_EXISTING),
            "cursor" => seed(target, ".git/hooks/post-commit", CURSOR_EXISTING),
            "opencode" => seed(target, ".opencode/hooks.md", OPENCODE_EXISTING),
            "pi" => seed(target, "justfile", PI_EXISTING),
            other => panic!("ide desconocido: {other}"),
        },
        "install_existing_noshebang" => seed(target, ".git/hooks/post-commit", CURSOR_NOSHEBANG),
        "install_error_nogit" => {}
        "uninstall_nomarker" => match ide {
            "claude-code" => seed(target, ".claude/settings.json", NOMARKER_CLAUDE),
            "cursor" => seed(target, ".git/hooks/post-commit", NOMARKER_CURSOR),
            "opencode" => seed(target, ".opencode/hooks.md", NOMARKER_OPENCODE),
            "pi" => seed(target, "justfile", NOMARKER_PI),
            other => panic!("ide desconocido: {other}"),
        },
        _ => panic!("caso sin setup: {case}"),
    }
}

#[test]
fn session_hooks_parity() {
    // Orden espejo del capturador: casos base por adapter + extras cursor.
    let mut plan: Vec<(&str, &str)> = Vec::new();
    for ide in ["claude-code", "cursor", "opencode", "pi"] {
        for case in [
            "install_fresh",
            "install_idempotent",
            "install_existing",
            "uninstall_installed",
            "uninstall_missing",
            "uninstall_nomarker",
            "status_missing",
            "status_installed",
            "status_uninstalled",
        ] {
            plan.push((ide, case));
        }
    }
    plan.push(("cursor", "install_existing_noshebang"));
    plan.push(("cursor", "install_error_nogit"));

    let installer = default_installer();
    for (ide, case) in plan {
        let seq = CASE_SEQ.fetch_add(1, Ordering::SeqCst);
        let tmp =
            std::env::temp_dir().join(format!("cortex-hooks-parity-{seq}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        let target = tmp.join("target");
        std::fs::create_dir_all(&target).expect("mkdir target");
        if ide == "cursor" && case != "install_error_nogit" {
            // El capturador crea .git/ para todos los pasos de cursor menos
            // el caso de error explícito.
            std::fs::create_dir_all(target.join(".git")).expect("mkdir .git");
        }
        setup_case(&target, ide, case);

        let adapter = installer
            .get(ide)
            .unwrap_or_else(|e| panic!("adapter {ide}: {e}"));

        // Ejecutar las operaciones previas del caso (espejo del oráculo).
        if case == "install_idempotent"
            || case == "uninstall_installed"
            || case == "status_installed"
            || case == "status_uninstalled"
        {
            adapter
                .install(&target)
                .unwrap_or_else(|e| panic!("{ide}/{case}: pre-install: {e}"));
        }
        if case == "status_uninstalled" {
            adapter
                .uninstall(&target)
                .unwrap_or_else(|e| panic!("{ide}/{case}: pre-uninstall: {e}"));
        }

        // Operación capturada + payload JSON (mismas claves que asdict()).
        let (kind, payload): (&str, Value) = match case {
            c if c.starts_with("install") && c != "install_error_nogit" => {
                match adapter.install(&target) {
                    Ok(r) => (
                        "result",
                        json!({
                            "ide": r.ide,
                            "installed": r.installed,
                            "modified_paths": r.modified_paths.iter().map(|p| normalize(&p.to_string_lossy(), &target)).collect::<Vec<_>>(),
                            "message": normalize(&r.message, &target),
                            "removed_paths": [],
                        }),
                    ),
                    Err(e) => panic!("{ide}/{case}: install falló: {e}"),
                }
            }
            "install_error_nogit" => match adapter.install(&target) {
                Ok(r) => (
                    "error-or-result",
                    json!({
                        "ide": r.ide,
                        "installed": r.installed,
                        "modified_paths": r.modified_paths.iter().map(|p| normalize(&p.to_string_lossy(), &target)).collect::<Vec<_>>(),
                        "message": normalize(&r.message, &target),
                        "removed_paths": [],
                    }),
                ),
                Err(e) => (
                    "error-or-result",
                    json!({ "error": normalize(e.as_str(), &target) }),
                ),
            },
            c if c.starts_with("uninstall") => match adapter.uninstall(&target) {
                Ok(r) => (
                    "result",
                    json!({
                        "ide": r.ide,
                        "uninstalled": r.uninstalled,
                        "modified_paths": [],
                        "removed_paths": r.removed_paths.iter().map(|p| normalize(&p.to_string_lossy(), &target)).collect::<Vec<_>>(),
                        "message": normalize(&r.message, &target),
                    }),
                ),
                Err(e) => panic!("{ide}/{case}: uninstall falló: {e}"),
            },
            c if c.starts_with("status_") => {
                let s = adapter.status(&target);
                (
                    "status",
                    json!({
                        "ide": s.ide,
                        "installed": s.installed,
                        "supported": true,
                        "detail": normalize(&s.detail, &target),
                    }),
                )
            }
            other => panic!("caso desconocido: {other}"),
        };

        let manifest = json!({
            "ide": ide,
            "kind": kind,
            "payload": payload,
            "files": files_json(&snapshot(&target)),
            "step": case,
        });

        let golden_path = format!("{GOLDEN}/{ide}__{case}/manifest.json");
        let raw = std::fs::read_to_string(&golden_path)
            .unwrap_or_else(|e| panic!("falta golden {golden_path}: {e}"));
        let golden: Value = serde_json::from_str(&raw).expect("manifest inválido");

        assert_eq!(
            manifest, golden,
            "{ide}__{case}: difiere del oráculo Python"
        );

        let _ = std::fs::remove_dir_all(&tmp);
    }
}
