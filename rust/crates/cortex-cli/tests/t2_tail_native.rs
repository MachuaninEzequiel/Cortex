use std::io::Write;
use std::process::{Command, Stdio};

fn cli(root: &std::path::Path, args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
        .args(args)
        .current_dir(root)
        .env("CORTEX_BIN", "/definitely/not/python-cortex")
        .output()
        .expect("run cortex-cli")
}

#[test]
fn docs_migrate_and_session_text_are_native() {
    let tmp = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(tmp.path().join("vault/specs")).unwrap();
    let out = cli(tmp.path(), &["docs", "migrate", "--json"]);
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    assert!(String::from_utf8_lossy(&out.stdout).contains("\"total_scanned\": 0"));

    std::fs::create_dir_all(tmp.path().join(".cortex/sessions")).unwrap();
    let out = cli(tmp.path(), &["session", "list"]);
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    assert_eq!(
        String::from_utf8_lossy(&out.stdout),
        "(no sessions on disk)\n"
    );
}

#[test]
fn docs_search_uses_native_enricher() {
    let tmp = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(tmp.path().join(".cortex/vault/specs")).unwrap();
    std::fs::create_dir_all(tmp.path().join(".cortex/memory")).unwrap();
    std::fs::write(
        tmp.path().join(".cortex/workspace.yaml"),
        "layout_version: 2\n",
    )
    .unwrap();
    std::fs::write(
        tmp.path().join(".cortex/config.yaml"),
        "semantic:\n  vault_path: vault\n",
    )
    .unwrap();
    std::fs::write(tmp.path().join(".cortex/memory/episodic_export.jsonl"), "").unwrap();
    std::fs::write(
        tmp.path().join(".cortex/vault/specs/auth.md"),
        "---\ntitle: Auth\ndoc_type: spec\nstatus: draft\ntags: [jwt]\n---\nJWT authentication\n",
    )
    .unwrap();
    for format in ["text", "json"] {
        let out = cli(tmp.path(), &["docs", "search", "JWT", "--format", format]);
        assert!(
            out.status.success(),
            "{}",
            String::from_utf8_lossy(&out.stderr)
        );
        assert!(!out.stdout.is_empty());
    }
}

#[test]
fn ci_setup_and_pr_context_are_native() {
    let tmp = tempfile::tempdir().unwrap();
    let out = cli(tmp.path(), &["ci", "validate-pr", "--format", "bogus"]);
    assert_eq!(out.status.code(), Some(3));
    assert!(String::from_utf8_lossy(&out.stderr).contains("--format must be one of"));

    let out = cli(
        tmp.path(),
        &["setup", "agent", "--dry-run", "--non-interactive"],
    );
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    assert!(String::from_utf8_lossy(&out.stdout).contains("[dry-run] Setup agent profile"));

    let actual = tempfile::tempdir().unwrap();
    let out = cli(
        actual.path(),
        &["setup", "full", "--non-interactive", "--ide", "pi"],
    );
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    assert!(actual.path().join(".cortex/workspace.yaml").is_file());
    assert!(actual
        .path()
        .join(".github/workflows/ci-pull-request.yml")
        .is_file());
    // --ide pi en modo real (no dry): el bundle cortex-pi se copia al root
    // (oráculo: SetupOrchestrator._install_ide → cortex.ide.inject).
    assert!(
        actual.path().join(".pi/settings.json").is_file(),
        "setup full --ide pi debe inyectar la config de Pi en modo real"
    );
    let out = cli(
        actual.path(),
        &[
            "setup",
            "enterprise",
            "--non-interactive",
            "--preset",
            "small-company",
            "--json",
        ],
    );
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );

    let context = tmp.path().join("ctx.json");
    std::fs::write(&context, r#"{"pr_number":1,"title":"Demo","author":"ana","source_branch":"feat/x","commit_sha":"abc"}"#).unwrap();
    let out = cli(
        tmp.path(),
        &[
            "pr-context",
            "generate",
            "--context-file",
            context.to_str().unwrap(),
            "--vault",
            "vault",
        ],
    );
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    assert!(String::from_utf8_lossy(&out.stdout).contains("Generated 1 documents:"));
}

#[test]
fn mcp_aliases_start_native_stdio() {
    for alias in ["mcp-server", "mcp-serve"] {
        let tmp = tempfile::tempdir().unwrap();
        let mut child = Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
            .args([alias, "--project-root", tmp.path().to_str().unwrap()])
            .current_dir(tmp.path())
            .env("CORTEX_BIN", "/definitely/not/python-cortex")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        use std::io::{BufRead, BufReader};
        let mut stdin = child.stdin.take().unwrap();
        let mut stdout = BufReader::new(child.stdout.take().unwrap());
        let mut responses = String::new();
        for (request, expects_response) in [
            (
                r#"{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"gate","version":"1"}}}"#,
                true,
            ),
            (
                r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#,
                false,
            ),
            (
                r#"{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}"#,
                true,
            ),
            (
                r#"{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"cortex_ping","arguments":{}}}"#,
                true,
            ),
        ] {
            writeln!(stdin, "{request}").unwrap();
            stdin.flush().unwrap();
            if expects_response {
                let mut line = String::new();
                stdout.read_line(&mut line).unwrap();
                responses.push_str(&line);
            }
        }
        drop(stdin);
        let status = child.wait().unwrap();
        assert!(status.success());
        assert!(responses.contains("\"id\":1"));
        assert!(responses.contains("\"id\":2"));
        assert!(responses.contains("\"id\":3"));
        assert!(responses.contains("cortex_ping"));
    }
}
