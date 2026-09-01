//! Tests de tutor/hint del CLI nativo (P12B-8 Task 3).
//!
//! - `hint`: paridad byte-a-byte contra el oráculo Python (rich Panel,
//!   width=80 non-tty) — paneles congelados de corridas reales.
//! - `tutor <slug>`: self-golden sobre los recursos embebidos de
//!   cortex-tutor (divergencia cosmética ~98 col heredada de P12B-7).
//! - `tutor` sin args: menú embebido + prompt + comportamiento EOF.

use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
}

const EXPECTED_L0: &str = r#"
╭────────────── 🚀 Cortex no está inicializado en este proyecto ───────────────╮
│                                                                              │
│  Este directorio no tiene config.yaml.                                       │
│  Inicializá Cortex para empezar a construir memoria.                         │
│                                                                              │
│    $ cortex setup agent                                                      │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

"#;
const EXPECTED_L7: &str = r#"
╭───────────────── ✅ Tu proyecto Cortex está en buena forma ──────────────────╮
│                                                                              │
│  Vault: 5 docs | Specs: 3 | Sessions: 2                                      │
│  Buscá algo en tu memoria para verificar que todo funciona.                  │
│                                                                              │
│    $ cortex search "mi query"                                                │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

"#;

#[test]
fn hint_l0_empty_fixture_byte_parity() {
    let tmp = tempfile::tempdir().unwrap();
    let out = bin().current_dir(tmp.path()).arg("hint").output().unwrap();
    assert!(out.status.success());
    assert_eq!(String::from_utf8_lossy(&out.stdout), EXPECTED_L0);
}

#[test]
fn hint_l7_full_fixture_byte_parity() {
    // Receta fixture l7 (igual a tutor_golden_p12b.py): config + specs×3 +
    // sessions×2 + workflows + mcp.json + org.yaml + vault-enterprise.
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    std::fs::create_dir_all(root.join("vault/specs")).unwrap();
    std::fs::create_dir_all(root.join("vault/sessions")).unwrap();
    for i in 0..3 {
        std::fs::write(
            root.join(format!("vault/specs/s{i}.md")),
            format!("# s{i}\n"),
        )
        .unwrap();
    }
    for i in 0..2 {
        std::fs::write(
            root.join(format!("vault/sessions/x{i}.md")),
            format!("# x{i}\n"),
        )
        .unwrap();
    }
    std::fs::create_dir_all(root.join(".github/workflows")).unwrap();
    std::fs::write(root.join(".mcp.json"), "{}\n").unwrap();
    std::fs::create_dir_all(root.join(".cortex")).unwrap();
    std::fs::write(
        root.join(".cortex/org.yaml"),
        "schema_version: 1\norganization:\n  name: Acme Org\nmemory:\n  enterprise_semantic_enabled: true\npromotion:\n  enabled: true\n",
    )
    .unwrap();
    std::fs::create_dir_all(root.join("vault-enterprise")).unwrap();

    let out = bin().current_dir(root).arg("hint").output().unwrap();
    assert!(out.status.success());
    assert_eq!(String::from_utf8_lossy(&out.stdout), EXPECTED_L7);
}

#[test]
fn tutor_unknown_slug_lists_available_and_exits_1() {
    let out = bin().args(["tutor", "noexiste"]).output().unwrap();
    assert_eq!(out.status.code(), Some(1));
    let err = String::from_utf8_lossy(&out.stderr);
    assert!(
        err.starts_with("Tópico 'noexiste' no encontrado. Disponibles: "),
        "{err}"
    );
    assert!(err.contains("pipeline"));
}

#[test]
fn tutor_menu_eof_renders_embedded_menu_with_prompt() {
    let menu = include_str!("../../cortex-tutor/content/menu.txt");
    let out = bin()
        .arg("tutor")
        .stdin(std::process::Stdio::null())
        .output()
        .unwrap();
    assert!(out.status.success());
    let expected = format!("\n{menu}\n  Elegí un tema (1-7) o 'q' para salir: \n");
    assert_eq!(String::from_utf8_lossy(&out.stdout), expected);
}
