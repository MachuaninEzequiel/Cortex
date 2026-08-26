//! MITAD B — `cortex docs` validate/restore/list-backups nativos y
//! routing-table. TDD: RED contra el estado previo (subcomandos no
//! dispatchados ⇒ passthrough rc 127 con CORTEX_BIN falso) → GREEN con
//! servicios reales y fixtures en tmp.
use std::path::Path;
use std::process::Command;

const FINGERPRINT: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

fn cli(root: &Path, args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
        .args(args)
        .current_dir(root)
        .env("CORTEX_BIN", "/definitely/not/python-cortex")
        .output()
        .expect("run cortex-cli")
}

/// Vault con DOC_TYPE canónico válido y otro inválido (doc_type desconocido).
fn vault_con_invalido(root: &Path) {
    std::fs::create_dir_all(root.join("vault/decisions")).unwrap();
    std::fs::write(
        root.join("vault/decisions/ADR-001-ok.md"),
        format!(
            "---\ntitle: OK\ndoc_type: adr\nadr_number: 1\n\
             created_at: 2026-08-01T10:00:00+00:00\n\
             updated_at: 2026-08-01T10:00:00+00:00\nstatus: accepted\n\
             fingerprint: {FINGERPRINT}\n---\n\ncuerpo\n"
        ),
    )
    .unwrap();
    std::fs::write(
        root.join("vault/decisions/BROKEN.md"),
        "---\ntitle: Broken\ndoc_type: weird\n---\n\ncuerpo\n",
    )
    .unwrap();
}

#[test]
fn docs_validate_text_reports_issues() {
    let tmp = tempfile::tempdir().unwrap();
    vault_con_invalido(tmp.path());
    let out = cli(
        tmp.path(),
        &[
            "docs",
            "validate",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ],
    );
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout);
    let expected = format!(
        "Vault: {}/vault\nTotal notes: 2\nValid: 1\nInvalid: 1\nNo frontmatter: 0\n\nIssues:\n  - decisions/BROKEN.md: Unknown doc_type: 'weird'\n",
        tmp.path().display()
    );
    assert_eq!(text, expected);
}

#[test]
fn docs_validate_json_is_pretty_payload() {
    let tmp = tempfile::tempdir().unwrap();
    vault_con_invalido(tmp.path());
    let out = cli(
        tmp.path(),
        &[
            "docs",
            "validate",
            "--project-root",
            tmp.path().to_str().unwrap(),
            "--json",
        ],
    );
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout);
    let expected = format!(
        "{{\n  \"vault_path\": \"{}/vault\",\n  \"total\": 2,\n  \"valid\": 1,\n  \"invalid\": 1,\n  \"no_frontmatter\": 0,\n  \"issues\": [\n    {{\n      \"path\": \"decisions/BROKEN.md\",\n      \"error\": \"Unknown doc_type: 'weird'\"\n    }}\n  ]\n}}\n",
        tmp.path().display()
    );
    assert_eq!(text, expected);
}

#[test]
fn docs_list_backups_and_restore_roundtrip() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    std::fs::create_dir_all(root.join("vault/specs")).unwrap();
    std::fs::write(
        root.join("vault/specs/auth.md"),
        format!(
            "---\ntitle: Auth\ndoc_type: spec\ncreated_at: 2026-08-01T10:00:00+00:00\n\
             updated_at: 2026-08-01T10:00:00+00:00\nstatus: draft\nfingerprint: {FINGERPRINT}\n---\n\nJWT\n"
        ),
    )
    .unwrap();

    // Backup real con `tar czf` (patrón de create_backup).
    let backups = root.join(".cortex/backups");
    std::fs::create_dir_all(&backups).unwrap();
    let name = "vault-2026-08-26T120000Z.tar.gz";
    let backup_path = backups.join(name);
    let ok = Command::new("tar")
        .args(["-czf"])
        .arg(&backup_path)
        .args(["-C"])
        .arg(root)
        .arg("vault")
        .status()
        .unwrap();
    assert!(ok.success());

    // list-backups vacío en otro root.
    let empty = tempfile::tempdir().unwrap();
    let out = cli(
        empty.path(),
        &[
            "docs",
            "list-backups",
            "--project-root",
            empty.path().to_str().unwrap(),
        ],
    );
    let text = String::from_utf8_lossy(&out.stdout);
    assert_eq!(
        text,
        format!(
            "No backups found in {}/.cortex/backups\n",
            empty.path().display()
        )
    );

    // list-backups con 1 backup: nombre + tamaño.
    let out = cli(
        root,
        &[
            "docs",
            "list-backups",
            "--project-root",
            root.to_str().unwrap(),
        ],
    );
    let text = String::from_utf8_lossy(&out.stdout);
    let size = std::fs::metadata(&backup_path).unwrap().len();
    assert_eq!(text, format!("{name}\t{size} bytes\n"));

    // restore por nombre corto → target.
    let out = cli(
        root,
        &[
            "docs",
            "restore",
            "--backup",
            "vault-2026-08-26",
            "--project-root",
            root.to_str().unwrap(),
            "--target",
            root.join("rest-a").to_str().unwrap(),
        ],
    );
    let text = String::from_utf8_lossy(&out.stdout);
    assert_eq!(text, format!("Restored: {}/rest-a/vault\n", root.display()));
    assert!(root.join("rest-a/vault/specs/auth.md").is_file());

    // restore por ruta completa.
    let out = cli(
        root,
        &[
            "docs",
            "restore",
            "--backup",
            backup_path.to_str().unwrap(),
            "--project-root",
            root.to_str().unwrap(),
            "--target",
            root.join("rest-b").to_str().unwrap(),
        ],
    );
    let text = String::from_utf8_lossy(&out.stdout);
    assert_eq!(text, format!("Restored: {}/rest-b/vault\n", root.display()));

    // backup inexistente: error exacto del oráculo, rc 1.
    let out = cli(
        root,
        &[
            "docs",
            "restore",
            "--backup",
            "vault-zzz-no-existe",
            "--project-root",
            root.to_str().unwrap(),
        ],
    );
    assert_eq!(out.status.code(), Some(1));
    assert_eq!(
        String::from_utf8_lossy(&out.stderr),
        "Backup not found: vault-zzz-no-existe\n"
    );
}

#[test]
fn docs_routing_table_text_all_types() {
    let tmp = tempfile::tempdir().unwrap();
    let out = cli(tmp.path(), &["docs", "routing-table"]);
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout);
    let header = "DocType        Subfolder      Filename pattern                       Writer                 Indexer  Promote       \n";
    assert_eq!(&text[..header.len()], header);
    assert!(text.contains("session        sessions       {session_id}_{slug}.md                 write_session_note_canonical auto     summarize     \n"));
    assert!(text.contains("adr            decisions      ADR-{number:03d}-{slug}.md             write_adr_note         auto     as-is         \n"));
    assert!(text.contains("design         designs        {session_id}.md                        write_design_note      auto     no            \n"));
    // 13 filas + header + separador.
    assert_eq!(text.lines().count(), 15);
}

#[test]
fn docs_routing_table_single_doc_type_json_matches_oracle() {
    let tmp = tempfile::tempdir().unwrap();
    let out = cli(
        tmp.path(),
        &["docs", "routing-table", "--doc-type", "adr", "--json"],
    );
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    // Plantilla: el template_path es el dir de templates del repo Python
    // (misma ruta absoluta que el oráculo en esta máquina).
    let text = String::from_utf8_lossy(&out.stdout);
    assert!(text.starts_with("{\n  \"doc_type\": \"adr\",\n"), "{text}");
    assert!(text.contains("\"filename_template\": \"ADR-{number:03d}-{slug}.md\""));
    assert!(text.contains("\"writer\": \"write_adr_note\""));
    assert!(text.contains("\"promotable\": true"));
    assert!(text.contains("\"retrieval_boost_per_intent\": {\n    \"decision\": 2.0"));
    assert!(text.ends_with("}\n"));
}

#[test]
fn docs_routing_table_invalid_doc_type_error() {
    let tmp = tempfile::tempdir().unwrap();
    let out = cli(
        tmp.path(),
        &["docs", "routing-table", "--doc-type", "bogus"],
    );
    assert_eq!(out.status.code(), Some(2));
    let err = String::from_utf8_lossy(&out.stderr);
    assert!(
        err.starts_with("Usage: cortex docs routing-table [OPTIONS]\n"),
        "{err}"
    );
    assert!(
        err.contains("Invalid value: Unknown doc_type: 'bogus'. Valid: ['session', 'handoff',"),
        "{err}"
    );
    assert!(
        err.contains("'architecture', 'changelog', 'hu', 'glossary', 'design']"),
        "{err}"
    );
}

#[test]
fn docs_routing_table_json_all_has_13_types_in_order() {
    let tmp = tempfile::tempdir().unwrap();
    let out = cli(tmp.path(), &["docs", "routing-table", "--json"]);
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let text = String::from_utf8_lossy(&out.stdout);
    let first = text
        .find("\"doc_type\": \"session\"")
        .expect("session first");
    let last = text.rfind("\"doc_type\": \"design\"").expect("design last");
    assert!(first < last);
    assert_eq!(text.matches("\"doc_type\": \"").count(), 13);
    assert!(text.starts_with("[\n  {\n    \"doc_type\": \"session\""));
}
