//! Tests de memory-report (P12B-8 Task 6).

use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
}

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
fn mr_invalid_scope_stderr_rc1() {
    let tmp = make_l7();
    let out = bin()
        .current_dir(tmp.path())
        .args(["memory-report", "--scope", "bogus"])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(1));
    assert_eq!(
        String::from_utf8_lossy(&out.stderr),
        "Invalid --scope value. Use one of: local, enterprise, all.\n"
    );
}

const MR_LOCAL_TEXT: &str = r#"
Cortex Enterprise Memory Report
-----------------------------
Project root: {{ROOT}}
Enterprise enabled: True
Scope: local

[local] vault={{ROOT}}/vault
  markdown_files: 5
  validation_errors: 0
  validation_warnings: 5

Promotion
---------
enabled: False
"#;

#[test]
fn mr_local_text_byte_parity() {
    // Sin timestamps en modo texto ⇒ bytes deterministas con {{ROOT}}.
    let tmp = make_l7();
    let out = bin()
        .current_dir(tmp.path())
        .args(["memory-report", "--scope", "local"])
        .output()
        .unwrap();
    assert!(out.status.success());
    let got =
        String::from_utf8_lossy(&out.stdout).replace(tmp.path().to_str().unwrap(), "{{ROOT}}");
    assert_eq!(got, MR_LOCAL_TEXT);
}

const MR_ALL_JSON_SELFGOLDEN: &str = r#"{
  "generated_at": "{{TS}}",
  "project_root": "{{ROOT}}",
  "enterprise_enabled": true,
  "sources": [
    {
      "scope": "local",
      "vault_path": "{{ROOT}}/vault",
      "markdown_files": 5,
      "validation_errors": 0,
      "validation_warnings": 5,
      "notes": []
    },
    {
      "scope": "enterprise",
      "vault_path": "{{ROOT}}/vault-enterprise",
      "markdown_files": 0,
      "validation_errors": 0,
      "validation_warnings": 0,
      "notes": []
    }
  ],
  "promotion": {
    "enabled": true,
    "require_review": true,
    "records_path": "{{ROOT}}/vault-enterprise/.cortex/promotion/records.jsonl",
    "candidates_discovered": 3,
    "candidates_ready_to_promote": 0,
    "latest_events": [],
    "warnings": []
  },
  "doctor": {
    "project_root": "{{ROOT}}",
    "checks": [
      {
        "name": "project_root",
        "ok": true,
        "severity": "fail",
        "detail": "{{ROOT}}"
      },
      {
        "name": "layout_mode",
        "ok": true,
        "severity": "info",
        "detail": "legacy (workspace_root={{ROOT}})"
      },
      {
        "name": "config_yaml",
        "ok": true,
        "severity": "fail",
        "detail": "{{ROOT}}/config.yaml"
      },
      {
        "name": "config_validation",
        "ok": true,
        "severity": "info",
        "detail": "config.yaml is valid"
      },
      {
        "name": "vault_dir",
        "ok": true,
        "severity": "fail",
        "detail": "{{ROOT}}/vault"
      },
      {
        "name": "episodic_store",
        "ok": false,
        "severity": "fail",
        "detail": "{{ROOT}}/memory"
      },
      {
        "name": "cortex_workspace",
        "ok": true,
        "severity": "warn",
        "detail": "{{ROOT}}"
      },
      {
        "name": "agent_guidelines",
        "ok": false,
        "severity": "warn",
        "detail": "{{ROOT}}/.cortex/AGENT.md"
      },
      {
        "name": "workspace_yaml",
        "ok": false,
        "severity": "info",
        "detail": "Missing: {{ROOT}}/.cortex/workspace.yaml"
      },
      {
        "name": "git_repository",
        "ok": false,
        "severity": "warn",
        "detail": "{{ROOT}}"
      },
      {
        "name": "git_branch",
        "ok": false,
        "severity": "warn",
        "detail": "no-git-branch"
      },
      {
        "name": "gitignore:.memory/",
        "ok": false,
        "severity": "fail",
        "detail": ".memory/"
      },
      {
        "name": "gitignore:vault/sessions/",
        "ok": false,
        "severity": "warn",
        "detail": "vault/sessions/"
      },
      {
        "name": "gitignore:.cortex/session.lock",
        "ok": false,
        "severity": "warn",
        "detail": ".cortex/session.lock"
      },
      {
        "name": "webgraph_dependencies",
        "ok": false,
        "severity": "warn",
        "detail": "backend no nativo a\u00fan (cortex.webgraph.setup)"
      },
      {
        "name": "vault_validation_errors",
        "ok": true,
        "severity": "fail",
        "detail": "0 error(s) across 5 markdown file(s)"
      },
      {
        "name": "vault_validation_warnings",
        "ok": false,
        "severity": "warn",
        "detail": "5 warning(s) across 5 markdown file(s)"
      },
      {
        "name": "sessions_dir",
        "ok": false,
        "severity": "warn",
        "detail": "Missing: {{ROOT}}/.cortex/sessions \u2014 run `cortex setup agent`."
      },
      {
        "name": "autopilot_policy",
        "ok": true,
        "severity": "info",
        "detail": "mode=assist, budget_profile=fast_code"
      },
      {
        "name": "session_hooks_installed",
        "ok": true,
        "severity": "info",
        "detail": "session hooks infrastructure active"
      },
      {
        "name": "pm_workspace_layout_v2",
        "ok": false,
        "severity": "warn",
        "detail": "running on legacy layout"
      },
      {
        "name": "pm_documenter_module",
        "ok": true,
        "severity": "info",
        "detail": "native documenter module ready"
      },
      {
        "name": "pm_documenter_interactive",
        "ok": false,
        "severity": "warn",
        "detail": "backend no nativo a\u00fan (cortex.documenter.interactive)"
      },
      {
        "name": "pm_documenter_default_mode",
        "ok": true,
        "severity": "info",
        "detail": "documenter.default_mode = auto"
      },
      {
        "name": "pm_verification_runner",
        "ok": false,
        "severity": "warn",
        "detail": "backend no nativo a\u00fan (cortex.session.verification)"
      },
      {
        "name": "pm_mcp_tools_registered",
        "ok": true,
        "severity": "info",
        "detail": "native MCP tools registered and operational"
      },
      {
        "name": "pm_git_available",
        "ok": false,
        "severity": "info",
        "detail": "no git repository at workspace root \u2014 sessions will open in gitless mode (documenter relies on checkpoints only)"
      },
      {
        "name": "enterprise_config",
        "ok": true,
        "severity": "fail",
        "detail": "{{ROOT}}/.cortex/org.yaml"
      },
      {
        "name": "enterprise_config_validation",
        "ok": true,
        "severity": "info",
        "detail": "Enterprise org config is valid"
      },
      {
        "name": "enterprise_topology",
        "ok": true,
        "severity": "info",
        "detail": "profile=small-company, mode=layered, project_memory=isolated, branch_isolation=off, retrieval_default=local, promotion=on, ci=advisory, enterprise_vault={{ROOT}}/vault-enterprise"
      },
      {
        "name": "enterprise_vault_dir",
        "ok": true,
        "severity": "fail",
        "detail": "{{ROOT}}/vault-enterprise"
      },
      {
        "name": "enterprise_vault_markdown",
        "ok": false,
        "severity": "warn",
        "detail": "No markdown files found under vault-enterprise/"
      },
      {
        "name": "enterprise_promotion_allowed_doc_types",
        "ok": true,
        "severity": "fail",
        "detail": "promotion.allowed_doc_types must be non-empty when promotion is enabled"
      },
      {
        "name": "enterprise_promotion_dir",
        "ok": true,
        "severity": "fail",
        "detail": "{{ROOT}}/vault-enterprise/.cortex/promotion"
      },
      {
        "name": "enterprise_promotion_records_presence",
        "ok": false,
        "severity": "warn",
        "detail": "{{ROOT}}/vault-enterprise/.cortex/promotion/records.jsonl"
      },
      {
        "name": "enterprise_branch_isolation_alignment",
        "ok": true,
        "severity": "warn",
        "detail": "config.yaml namespace_mode=project, org.yaml branch_isolation_enabled=False"
      },
      {
        "name": "enterprise_retrieval_scope",
        "ok": true,
        "severity": "warn",
        "detail": "default_scope=local, enterprise_semantic_enabled=True"
      }
    ],
    "has_failures": true,
    "has_warnings": true
  }
}
"#;

#[test]
fn mr_all_json_selfgolden_with_canonical_key_order() {
    // Self-golden: congelado del binario normalizado. La paridad live vs
    // Python (módulo stubs contractuales) quedó demostrada y el gate la
    // verifica con STUB_TABLE; acá se fija orden de claves canónico
    // ("project_root" antes de "checks") y contenido.
    let tmp = make_l7();
    let out = bin()
        .current_dir(tmp.path())
        .args(["memory-report", "--scope", "all", "--json"])
        .output()
        .unwrap();
    assert!(out.status.success());
    let got =
        String::from_utf8_lossy(&out.stdout).replace(tmp.path().to_str().unwrap(), "{{ROOT}}");
    let got = re_ts(&got);
    assert_eq!(got, MR_ALL_JSON_SELFGOLDEN);
}

/// Reemplaza ISO timestamps (`2026-08-25T22:44:56+00:00`) por {{TS}}.
fn re_ts(s: &str) -> String {
    let bytes = s.as_bytes();
    let mut out = String::with_capacity(s.len());
    let mut i = 0;
    while i < s.len() {
        if i + 25 <= s.len() && bytes[i] == b'2' {
            let cand = &s[i..i + 25];
            let digits_ok = cand.as_bytes().iter().enumerate().all(|(j, b)| match j {
                4 | 7 => *b == b'-',
                10 => *b == b'T',
                13 | 16 | 22 => *b == b':',
                19 => *b == b'+',
                20..=21 | 23..=24 => *b == b'0',
                _ => b.is_ascii_digit(),
            });
            if digits_ok && cand.ends_with("+00:00") {
                out.push_str("{{TS}}");
                i += 25;
                continue;
            }
        }
        let ch_len = utf8_len(bytes[i]);
        out.push_str(&s[i..i + ch_len]);
        i += ch_len;
    }
    out
}

fn utf8_len(b: u8) -> usize {
    if b < 0x80 {
        1
    } else if b >> 5 == 0b110 {
        2
    } else if b >> 4 == 0b1110 {
        3
    } else {
        4
    }
}

#[test]
fn mr_telemetry_fails_explicitly_no_passthrough() {
    // --telemetry no es nativo y la baja física eliminó el passthrough:
    // fallo explícito documentado, rc 1, sin delegar (CORTEX_BIN no efecto).
    let tmp = make_l7();
    let out = bin()
        .env("CORTEX_PY", "1")
        .env("CORTEX_BIN", "/bin/echo")
        .current_dir(tmp.path())
        .args(["memory-report", "--telemetry"])
        .output()
        .unwrap();
    assert_eq!(
        out.status.code(),
        Some(1),
        "stdout: {}",
        String::from_utf8_lossy(&out.stdout)
    );
    let err = String::from_utf8_lossy(&out.stderr);
    // El aviso histórico de CORTEX_PY=1 está presente y el fallo explícito
    // de --telemetry también (sin reenvío a /bin/echo).
    assert!(
        err.contains("memory-report --telemetry no nativo en build Rust"),
        "mensaje de fallo ausente: {err}"
    );
    assert_eq!(String::from_utf8_lossy(&out.stdout), "");
}
