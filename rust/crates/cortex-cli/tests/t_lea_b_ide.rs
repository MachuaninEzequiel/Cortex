//! MITAD B — `cortex ide` nativo (list/setup/remove/status) sobre
//! `cortex_setup::ide` + `HookInstaller`. TDD: RED contra el stub
//! (`run` devuelve `false` ⇒ passthrough a un CORTEX_BIN inexistente,
//! rc 127) → GREEN con glue nativo. Servicios reales + fixtures tmp.
use std::process::Command;

fn cli(root: &std::path::Path, args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
        .args(args)
        .current_dir(root)
        .env("CORTEX_BIN", "/definitely/not/python-cortex")
        .output()
        .expect("run cortex-cli")
}

#[test]
fn ide_list_json_is_native_array_of_11() {
    let tmp = tempfile::tempdir().unwrap();
    let out = cli(tmp.path(), &["ide", "list", "--json"]);
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(text.starts_with("[{\"name\": \"antigravity\""), "{text}");
    assert!(text.contains("\"name\": \"pi\", \"display_name\": \"Pi Coding Agent\""));
    assert!(text.contains("\"validated\": true"));
    // 11 adapters, orden sorted por nombre (oráculo registry.py).
    let names: Vec<&str> = text
        .split("\"name\": \"")
        .skip(1)
        .map(|s| s.split('"').next().unwrap())
        .collect();
    assert_eq!(
        names,
        [
            "antigravity",
            "claude_code",
            "claude_desktop",
            "codex",
            "cursor",
            "hermes",
            "opencode",
            "pi",
            "vscode",
            "windsurf",
            "zed"
        ]
    );
}

#[test]
fn ide_list_text_is_native_table() {
    let tmp = tempfile::tempdir().unwrap();
    let out = cli(tmp.path(), &["ide", "list"]);
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(text.starts_with("┏━━━━"), "{text}");
    assert!(text.contains("│ antigravity    │"));
    assert!(text.contains("experimental"));
    assert!(text.contains("DISPLAY NAME"));
}

#[test]
fn ide_status_unknown_ide_error_matches_oracle() {
    let tmp = tempfile::tempdir().unwrap();
    let out = cli(
        tmp.path(),
        &[
            "ide",
            "status",
            "--ide",
            "nope",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ],
    );
    // Oráculo: KeyError str = repr del mensaje ⇒ comillas + \n literales.
    assert_eq!(out.status.code(), Some(2));
    let err = String::from_utf8_lossy(&out.stderr);
    assert!(
        err.starts_with("Error: \"Unknown IDE: 'nope'.\\n  Target"),
        "{err}"
    );
    assert!(err.contains("claude_code, codex, opencode, pi"));
    assert!(err.contains("antigravity, hermes, zed\""));
}

#[test]
fn ide_setup_requires_ide_flag() {
    let tmp = tempfile::tempdir().unwrap();
    let out = cli(
        tmp.path(),
        &[
            "ide",
            "setup",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ],
    );
    assert_eq!(out.status.code(), Some(2));
    let err = String::from_utf8_lossy(&out.stderr);
    assert!(
        err.contains("--ide is required for `cortex ide setup`"),
        "{err}"
    );
    assert!(err.contains("  target:       claude_code, codex, opencode, pi"));
    assert!(err.contains("  experimental: antigravity, hermes, zed"));
}

#[test]
fn ide_setup_pi_writes_bundle_then_remove_cleans() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    std::fs::create_dir_all(root.join(".cortex")).unwrap();
    std::fs::write(root.join(".cortex/workspace.yaml"), "layout_version: 2\n").unwrap();

    let out = cli(
        root,
        &[
            "ide",
            "setup",
            "--ide",
            "pi",
            "--project-root",
            root.to_str().unwrap(),
        ],
    );
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(
        text.contains("[Cortex IDE] Injecting profiles for Pi Coding Agent..."),
        "{text}"
    );
    assert!(text.contains("  [OK] .pi/"), "{text}");
    assert!(
        text.contains("✅ Setup complete for Pi Coding Agent. Setup is idempotent; re-run `cortex ide setup --ide pi` anytime to re-sync."),
        "{text}"
    );
    assert!(root.join(".pi/settings.json").is_file());
    assert!(root.join("justfile").is_file());

    // Hooks de sesión vía HookInstaller: el justfile escrito por setup no
    // tiene recetas cortex ⇒ status HOOKS ✗ con detalle del oráculo.
    let out = cli(
        root,
        &[
            "ide",
            "status",
            "--ide",
            "pi",
            "--project-root",
            root.to_str().unwrap(),
            "--json",
        ],
    );
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let status = String::from_utf8_lossy(&out.stdout);
    assert!(status.contains("\"hooks_installed\": false"), "{status}");
    assert!(
        status.contains(&format!(
            "{}/justfile exists but no cortex recipes",
            root.display()
        )),
        "{status}"
    );

    let out = cli(
        root,
        &[
            "ide",
            "remove",
            "--ide",
            "pi",
            "--project-root",
            root.to_str().unwrap(),
        ],
    );
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(
        text.contains(
            "Remove complete for Pi Coding Agent: 8 entradas procesadas, 0 paths restantes."
        ),
        "{text}"
    );
    assert!(!root.join(".pi").exists());
    assert!(!root.join("AGENTS.md").exists());
}

#[test]
fn ide_status_all_json_has_hooks_and_config_checks() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    let out = cli(
        root,
        &[
            "ide",
            "status",
            "--project-root",
            root.to_str().unwrap(),
            "--json",
        ],
    );
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(text.starts_with("[{\"ide\": \"antigravity\""), "{text}");
    assert!(text.contains("\"config_checks\": {\"claude_md\": false"));
    assert!(text.contains(&format!(
        "\"hooks_detail\": \"{}/.claude/settings.json does not exist\"",
        root.display()
    )));
}
