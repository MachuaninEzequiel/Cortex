//! Tests de org-config y promote-knowledge (P12B-8 Task 4).
//!
//! Bytes congelados del oráculo Python sobre el fixture l7
//! (normalizando la raíz del fixture como {{ROOT}}).

use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
}

/// Receta fixture l7 (idéntica a tutor_golden_p12b.py).
fn make_l7() -> tempfile::TempDir {
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
    tmp
}

#[test]
fn org_config_missing_nonrequired_prints_stdout_rc0() {
    let tmp = tempfile::tempdir().unwrap();
    let out = bin()
        .args(["org-config", "--project-root", tmp.path().to_str().unwrap()])
        .output()
        .unwrap();
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert_eq!(
        stdout,
        format!(
            "Enterprise config not found under {}/.cortex/org.yaml\n",
            tmp.path().display()
        )
    );
}

#[test]
fn org_config_missing_required_stderr_rc1() {
    let tmp = tempfile::tempdir().unwrap();
    let out = bin()
        .args([
            "org-config",
            "--project-root",
            tmp.path().to_str().unwrap(),
            "--required",
        ])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.starts_with("Enterprise config not found under "));
}

const ORG_CONFIG_JSON: &str = r#"{
  "schema_version": 1,
  "organization": {
    "name": "Acme Org",
    "slug": "acme-org",
    "profile": "small-company"
  },
  "memory": {
    "mode": "layered",
    "enterprise_vault_path": "vault-enterprise",
    "enterprise_memory_path": "memory/enterprise/chroma",
    "enterprise_semantic_enabled": true,
    "enterprise_episodic_enabled": false,
    "project_memory_mode": "isolated",
    "branch_isolation_enabled": false,
    "retrieval_default_scope": "local",
    "retrieval_local_weight": 1.0,
    "retrieval_enterprise_weight": 1.0
  },
  "promotion": {
    "enabled": true,
    "allowed_doc_types": [
      "spec",
      "decision",
      "runbook",
      "hu",
      "incident"
    ],
    "require_review": true,
    "default_targets": [
      "enterprise_vault"
    ]
  },
  "governance": {
    "git_policy": "balanced",
    "ci_profile": "advisory",
    "version_sessions_in_git": false
  },
  "integration": {
    "github_actions_enabled": true,
    "webgraph_workspace_enabled": true,
    "ide_profiles": []
  },
  "teams": [],
  "classifications": [
    "public",
    "internal",
    "confidential"
  ],
  "policies": {
    "confidential_visible_to": []
  },
  "retention_defaults": {
    "session": 365,
    "handoff": 30,
    "spec": 1095,
    "adr": 2555,
    "decision": 365,
    "incident": 1825,
    "postmortem": 2555,
    "runbook": 730,
    "architecture": 2555,
    "changelog": 0,
    "hu": 90,
    "glossary": 0
  }
}
"#;

#[test]
fn org_config_json_byte_parity_on_l7() {
    let tmp = make_l7();
    let out = bin()
        .args([
            "org-config",
            "--json",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(out.status.success());
    let got =
        String::from_utf8_lossy(&out.stdout).replace(tmp.path().to_str().unwrap(), "{{ROOT}}");
    // El JSON de config no contiene rutas; la normalización es inocua.
    assert_eq!(got, ORG_CONFIG_JSON);
}

#[test]
fn promote_knowledge_empty_plan_text() {
    let tmp = make_l7();
    let out = bin()
        .current_dir(tmp.path())
        .arg("promote-knowledge")
        .output()
        .unwrap();
    assert!(out.status.success());
    assert_eq!(
        String::from_utf8_lossy(&out.stdout),
        "No reviewed candidates ready for promotion.\n"
    );
}

const PROMOTE_JSON_EMPTY: &str = r#"{
  "project_root": "{{ROOT}}",
  "enterprise_vault": "{{ROOT}}/vault-enterprise",
  "dry_run": true,
  "planned": []
}
"#;

#[test]
fn promote_knowledge_empty_plan_json_payload_shape() {
    let tmp = make_l7();
    let out = bin()
        .current_dir(tmp.path())
        .args(["promote-knowledge", "--json"])
        .output()
        .unwrap();
    assert!(out.status.success());
    let got =
        String::from_utf8_lossy(&out.stdout).replace(tmp.path().to_str().unwrap(), "{{ROOT}}");
    assert_eq!(got, PROMOTE_JSON_EMPTY);
}
