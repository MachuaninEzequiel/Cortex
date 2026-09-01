//! `cortex setup composed` (Obra 08 stream A, G-A4b): instala la familia
//! COMPOSED + la tríada thin+craft en `.cortex/skills/` y escribe el bloque
//! `## Agent skills` en CLAUDE.md/AGENTS.md. fixture = tempdir (patrón
//! cli_commands_basic).

use std::path::{Path, PathBuf};
use std::process::Command;

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_cortex-cli"))
}

fn composed_template(rel: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../cortex-setup/templates/composed")
        .join(rel)
}

fn sso(rel: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../cortex/setup/workspace_files")
        .join(rel)
}

fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_else(|e| panic!("no se pudo leer {}: {e}", p.display()))
}

#[test]
fn setup_composed_installs_family_triad_and_agents_block() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    let out = bin()
        .args([
            "setup",
            "composed",
            "--non-interactive",
            "--project-root",
            root.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "rc {:?} stderr: {}",
        out.status.code(),
        String::from_utf8_lossy(&out.stderr)
    );

    // familia byte-igual al template
    assert_eq!(
        read(&root.join(".cortex/skills/composed/grill/SKILL.md")),
        read(&composed_template("grill/SKILL.md")),
        "grill/SKILL.md byte-exact"
    );
    assert_eq!(
        read(&root.join(".cortex/skills/composed/tdd/references/tdd-craft.md")),
        read(&composed_template("tdd/references/tdd-craft.md")),
        "references/ se despliega"
    );
    assert!(root
        .join(".cortex/skills/composed/INSTALL-COMPOSED.md")
        .exists());
    assert!(root
        .join(".cortex/skills/composed/glossary/agents/openai.yaml")
        .exists());

    // ítem 1 cross-task: los craft files acompañan al thin en proyecto fresco
    assert_eq!(
        read(&root.join(".cortex/skills/cortex-sync.md")),
        read(&sso("cortex-sync.md")),
        "thin byte-igual al SSoT"
    );
    for craft in [
        "cortex-sync-spec-craft.md",
        "cortex-sync-proposal-craft.md",
        "cortex-SDDwork-implement-craft.md",
        "cortex-documenter-close-craft.md",
    ] {
        assert!(
            root.join(".cortex/skills").join(craft).exists(),
            "craft {craft} desplegado"
        );
    }

    // sin docs previos ⇒ nace AGENTS.md con el bloque marcado (R12:
    // marcadores DEDICADOS, no los canónicos de la sección codex)
    let agents = read(&root.join("AGENTS.md"));
    assert!(agents.contains("## Agent skills"), "AGENTS.md: {agents}");
    assert!(
        agents.contains("BEGIN CORTEX AGENT SKILLS"),
        "bloque con marcadores dedicados"
    );
}

#[test]
fn setup_composed_upserts_existing_docs_and_preserves_user_edits() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    std::fs::write(root.join("CLAUDE.md"), "# Mi proyecto\n\nreglas\n").unwrap();
    let args = [
        "setup",
        "composed",
        "--non-interactive",
        "--project-root",
        root.to_str().unwrap(),
    ];

    assert!(bin().args(args).output().unwrap().status.success());
    assert!(bin().args(args).output().unwrap().status.success());

    let claude = read(&root.join("CLAUDE.md"));
    assert!(
        claude.starts_with("# Mi proyecto"),
        "contenido original intacto"
    );
    assert_eq!(
        claude.matches("BEGIN CORTEX AGENT SKILLS").count(),
        1,
        "el bloque se reemplaza, no se duplica"
    );
    assert!(
        !root.join("AGENTS.md").exists(),
        "no se crea el doc que no existía"
    );

    // skip-if-exists: ediciones del usuario nunca se pisan
    std::fs::write(root.join(".cortex/skills/cortex-sync.md"), b"custom").unwrap();
    assert!(bin().args(args).output().unwrap().status.success());
    assert_eq!(read(&root.join(".cortex/skills/cortex-sync.md")), "custom");
}

#[test]
fn setup_composed_coexists_with_codex_agents_section() {
    // R12 (gate A13): la sección codex (marcadores canónicos) y el bloque
    // composed (marcadores dedicados) conviven en el mismo AGENTS.md sin
    // pisarse — antes compartían span y upsert se comía al otro.
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    let codex_block = "<!-- BEGIN CORTEX SECTION (auto-generated, do not edit) -->\n## Codex workflow\ntriad anchors\n<!-- END CORTEX SECTION -->";
    std::fs::write(
        root.join("AGENTS.md"),
        format!("# Mi proyecto\n\n{codex_block}\n"),
    )
    .unwrap();
    let args = [
        "setup",
        "composed",
        "--non-interactive",
        "--project-root",
        root.to_str().unwrap(),
    ];

    assert!(bin().args(args).output().unwrap().status.success());
    let agents = read(&root.join("AGENTS.md"));
    assert!(
        agents.contains("## Codex workflow"),
        "la sección codex sobrevive el setup composed"
    );
    assert!(agents.contains("## Agent skills"), "composed se escribe");
    assert_eq!(
        agents.matches("BEGIN CORTEX SECTION").count(),
        1,
        "codex no duplicado"
    );
    assert_eq!(
        agents.matches("BEGIN CORTEX AGENT SKILLS").count(),
        1,
        "composed no duplicado"
    );

    // replay: ni duplicación ni pisado
    assert!(bin().args(args).output().unwrap().status.success());
    let agents = read(&root.join("AGENTS.md"));
    assert!(agents.contains("## Codex workflow"), "codex sigue vivo");
    assert_eq!(
        agents.matches("BEGIN CORTEX SECTION").count(),
        1,
        "codex no duplicado tras replay"
    );
    assert_eq!(
        agents.matches("BEGIN CORTEX AGENT SKILLS").count(),
        1,
        "composed no duplicado tras replay"
    );
}

#[test]
fn setup_composed_dry_run_writes_nothing() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    let out = bin()
        .args([
            "setup",
            "composed",
            "--dry-run",
            "--project-root",
            root.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("dry-run"), "stdout: {stdout}");
    assert!(
        !root.join(".cortex").exists() && !root.join("AGENTS.md").exists(),
        "sin efectos"
    );
}

#[test]
fn setup_composed_requires_non_interactive() {
    let tmp = tempfile::tempdir().unwrap();
    let out = bin()
        .args([
            "setup",
            "composed",
            "--project-root",
            tmp.path().to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&out.stderr).contains("Interactive setup"),
        "rechazo interactivo igual que los otros perfiles"
    );
}

#[test]
fn installed_docs_match_fixed_sso_items_2_and_3() {
    // ítem 2: la verificacion rapida ya no promete `mode` en `session current`
    // ítem 3: to-tickets documenta el scope de .scratch para specs con files_in_scope
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    assert!(bin()
        .args([
            "setup",
            "composed",
            "--non-interactive",
            "--project-root",
            root.to_str().unwrap()
        ])
        .output()
        .unwrap()
        .status
        .success());
    let doc = read(&root.join(".cortex/skills/composed/INSTALL-COMPOSED.md"));
    assert!(
        !doc.contains("cortex session current --json     # mode"),
        "INSTALL-COMPOSED no debe prometer mode en `session current`"
    );
    assert!(
        doc.contains("cortex session list --json"),
        "la verificacion correcta usa session list"
    );
    let tickets = read(&root.join(".cortex/skills/composed/to-tickets/SKILL.md"));
    assert!(
        tickets.contains("files_in_scope"),
        "to-tickets documenta el scope de .scratch"
    );
}
