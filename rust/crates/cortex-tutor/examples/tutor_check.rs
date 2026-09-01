//! Gate P12B-7: reproduce golden_tutor.txt byte-a-byte.
//! JSON estilo Python: ensure_ascii=True ⇒ \uXXXX y pares sustitutos para
//! caracteres fuera del BMP.

use std::path::{Path, PathBuf};

use cortex_tutor::hint::{get_hint, ProjectState};
use cortex_tutor::topics::get_all_topics;

/// Escape JSON de Python (`json.dumps` default): ensure_ascii + \uXXXX.
fn py_str(s: &str) -> String {
    let mut out = String::new();
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c if (c as u32) <= 0x7e => out.push(c),
            c if (c as u32) <= 0xffff => {
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c => {
                // Par sustituto para códigos > 0xFFFF.
                let cp = c as u32 - 0x10000;
                let hi = 0xd800 + (cp >> 10);
                let lo = 0xdc00 + (cp & 0x3ff);
                out.push_str(&format!("\\u{:04x}\\u{:04x}", hi, lo));
            }
        }
    }
    format!("\"{out}\"")
}

fn py_null_or(s: Option<&str>) -> String {
    match s {
        Some(v) => py_str(v),
        None => "null".to_string(),
    }
}

fn make_fixture(kind: &str) -> PathBuf {
    let root = std::env::temp_dir().join(format!("tutor_gate_{}_{}", kind, std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    std::fs::create_dir_all(&root).unwrap();

    if kind == "l0" {
        return root;
    }
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    if kind == "l1" {
        return root;
    }
    // l7
    let vault = root.join("vault");
    std::fs::create_dir_all(vault.join("specs")).unwrap();
    std::fs::create_dir_all(vault.join("sessions")).unwrap();
    for i in 0..3 {
        std::fs::write(
            vault.join("specs").join(format!("s{i}.md")),
            format!("# s{i}\n"),
        )
        .unwrap();
    }
    for i in 0..2 {
        std::fs::write(
            vault.join("sessions").join(format!("x{i}.md")),
            format!("# x{i}\n"),
        )
        .unwrap();
    }
    std::fs::create_dir_all(root.join(".github/workflows")).unwrap();
    std::fs::write(root.join(".mcp.json"), "{}\n").unwrap();
    let org = root.join(".cortex");
    std::fs::create_dir_all(&org).unwrap();
    std::fs::write(
        org.join("org.yaml"),
        "schema_version: 1\norganization:\n  name: Acme Org\nmemory:\n  enterprise_semantic_enabled: true\npromotion:\n  enabled: true\n",
    )
    .unwrap();
    std::fs::create_dir_all(root.join("vault-enterprise")).unwrap();
    root
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let dir = args.get(1).expect("uso: tutor_check <golden_dir>");
    let expected = std::fs::read_to_string(Path::new(dir).join("golden_tutor.txt")).unwrap();

    let mut actual = String::from("### TOPICS\n");
    for t in get_all_topics() {
        actual.push_str(&format!(
            "{{\"title\": {}, \"icon\": {}, \"slug\": {}, \"one_liner\": {}, \"guide_path\": {}}}\n",
            py_str(t.title),
            py_str(t.icon),
            py_str(t.slug),
            py_str(t.one_liner),
            py_null_or(t.guide_path),
        ));
    }

    actual.push_str("### HINTS\n");
    for kind in ["l0", "l1", "l7"] {
        let fixture_tag = match kind {
            "l0" => "l0_empty",
            "l1" => "l1_config_only",
            _ => "l7_full",
        };
        let root = make_fixture(kind);
        let state = ProjectState::detect(&root);
        let hint = get_hint(&state);
        actual.push_str(&format!(
            "{{\"fixture\": {}, \"icon\": {}, \"title\": {}, \"body\": {}, \"command\": {}}}\n",
            py_str(fixture_tag),
            py_str(hint.icon),
            py_str(&hint.title),
            py_str(&hint.body),
            py_str(&hint.command),
        ));
        let _ = std::fs::remove_dir_all(&root);
    }

    if actual == expected {
        println!("[PASS] tutor_check byte-parity vs golden_tutor.txt");
        println!("✅ PARIDAD P12B-7");
    } else {
        let mut line = 1usize;
        'outer: for (e, a) in expected.chars().zip(actual.chars()) {
            if e != a {
                println!("[FAIL] línea {line}: esperado {e:?} vs real {a:?}");
                break 'outer;
            }
            if e == '\n' {
                line += 1;
            }
        }
        let _ = std::fs::write("/tmp/tutor_exp.txt", &expected);
        let _ = std::fs::write("/tmp/tutor_act.txt", &actual);
        eprintln!("detalle: /tmp/tutor_exp.txt vs /tmp/tutor_act.txt");
        std::process::exit(1);
    }
}
