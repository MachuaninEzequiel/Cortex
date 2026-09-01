//! Tests de review-knowledge ×4 (P12B-8 Task 5).
//!
//! Cada test arma su fixture (vault-enterprise con drafts) para que las
//! mutaciones de approve/reject sean independientes. El stdout contractual es
//! determinista; los timestamps caen dentro del archivo mutado y se verifican
//! estructuralmente (sin igualdad byte del reloj real).

use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
}

const DRAFT_ONE: &str =
    "---\ntitle: Draft One\ndoc_type: spec\nowner: alice\nstatus: draft\n---\n\nBody one\n";
const DRAFT_TWO: &str =
    "---\ntitle: Draft Two\ndoc_type: runbook\nstatus: draft\n---\n\nBody two\n";

fn make_vault() -> tempfile::TempDir {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    std::fs::create_dir_all(root.join("vault")).unwrap();
    std::fs::create_dir_all(root.join("vault-enterprise/specs")).unwrap();
    std::fs::write(root.join("vault-enterprise/specs/draft1.md"), DRAFT_ONE).unwrap();
    std::fs::write(root.join("vault-enterprise/specs/draft2.md"), DRAFT_TWO).unwrap();
    tmp
}

#[test]
fn rk_pending_text_matches_oracle_layout() {
    let tmp = make_vault();
    let out = bin()
        .args([
            "review-knowledge",
            "pending",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ])
        .envs([
            ("USER", "tester"),
            ("LOGNAME", "tester"),
            ("LNAME", "tester"),
            ("USERNAME", "tester"),
        ])
        .output()
        .unwrap();
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    // Orden (doc_type, path): runbook/draft2 antes que spec/draft1.
    let expected = "Pending review (2):\n\
                    \x20 - specs/draft2.md                                              doc_type=runbook    owner=-\n\
                    \x20 - specs/draft1.md                                              doc_type=spec       owner=alice\n";
    assert_eq!(stdout, expected);
}

#[test]
fn rk_pending_json_null_fields_and_order() {
    let tmp = make_vault();
    let out = bin()
        .args([
            "review-knowledge",
            "pending",
            "--json",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(out.status.success());
    let expected = r#"[
  {
    "path": "specs/draft2.md",
    "doc_type": "runbook",
    "title": "Draft Two",
    "owner": null,
    "team": null,
    "created_at": null
  },
  {
    "path": "specs/draft1.md",
    "doc_type": "spec",
    "title": "Draft One",
    "owner": "alice",
    "team": null,
    "created_at": null
  }
]
"#;
    assert_eq!(String::from_utf8_lossy(&out.stdout), expected);
}

#[test]
fn rk_approve_mutates_status_and_prints_ok() {
    let tmp = make_vault();
    let out = bin()
        .envs([
            ("USER", "tester"),
            ("LOGNAME", "tester"),
            ("LNAME", "tester"),
            ("USERNAME", "tester"),
        ])
        .args([
            "review-knowledge",
            "approve",
            "specs/draft1.md",
            "--reviewer",
            "tester",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(out.status.success());
    assert_eq!(
        String::from_utf8_lossy(&out.stdout),
        "[OK] specs/draft1.md -> status: accepted (reviewer=tester)\n"
    );
    let note =
        std::fs::read_to_string(tmp.path().join("vault-enterprise/specs/draft1.md")).unwrap();
    assert!(note.contains("status: accepted"));
    assert!(note.contains("audit_trail:"));
    assert!(note.contains("actor: tester"));
    assert!(note.contains("action: accepted"));
}

#[test]
fn rk_reject_moves_to_rejected_folder() {
    let tmp = make_vault();
    let out = bin()
        .envs([
            ("USER", "tester"),
            ("LOGNAME", "tester"),
            ("LNAME", "tester"),
            ("USERNAME", "tester"),
        ])
        .args([
            "review-knowledge",
            "reject",
            "specs/draft2.md",
            "--reason",
            "no sirve",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(out.status.success());
    assert_eq!(
        String::from_utf8_lossy(&out.stdout),
        "[OK] specs/draft2.md -> specs/rejected/draft2.md (reviewer=tester)\n"
    );
    assert!(
        tmp.path()
            .join("vault-enterprise/specs/rejected/draft2.md")
            .exists(),
        "el draft debe moverse a rejected/"
    );
    assert!(!tmp.path().join("vault-enterprise/specs/draft2.md").exists());
}

#[test]
fn rk_escape_path_stderr_rc1() {
    let tmp = make_vault();
    let out = bin()
        .envs([
            ("USER", "tester"),
            ("LOGNAME", "tester"),
            ("LNAME", "tester"),
            ("USERNAME", "tester"),
        ])
        .args([
            "review-knowledge",
            "approve",
            "../escape.md",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(1));
    assert_eq!(
        String::from_utf8_lossy(&out.stderr),
        "Path escapes enterprise vault: ../escape.md\n"
    );
}

#[test]
fn rk_reject_without_reason_is_usage_error() {
    // Self-golden: --reason requerido ⇒ clap corta con usage error rc=2.
    let tmp = make_vault();
    let out = bin()
        .envs([
            ("USER", "tester"),
            ("LOGNAME", "tester"),
            ("LNAME", "tester"),
            ("USERNAME", "tester"),
        ])
        .args([
            "review-knowledge",
            "reject",
            "specs/draft2.md",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(2));
}

#[test]
fn rk_candidate_unknown_selector_stderr_rc1() {
    // Fixture con org.yaml (promoción habilitada) para que el service cargue.
    let tmp = make_vault();
    let root = tmp.path();
    std::fs::create_dir_all(root.join(".cortex")).unwrap();
    std::fs::write(
        root.join(".cortex/org.yaml"),
        "schema_version: 1\norganization:\n  name: Acme Org\nmemory:\n  enterprise_semantic_enabled: true\npromotion:\n  enabled: true\n",
    )
    .unwrap();

    let out = bin()
        .envs([
            ("USER", "tester"),
            ("LOGNAME", "tester"),
            ("LNAME", "tester"),
            ("USERNAME", "tester"),
        ])
        .args([
            "review-knowledge",
            "candidate",
            "no-existe",
            "--project-root",
            root.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert_eq!(
        stderr, "No candidate found for selector: no-existe\n",
        "stderr: {stderr}"
    );
}
