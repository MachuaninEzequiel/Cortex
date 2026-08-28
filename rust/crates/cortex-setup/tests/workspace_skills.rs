//! Paridad del artefacto de skill `cortex-sync` (Obra 08 stream A, G-A3a).
//!
//! El SSoT de las skills vive en `cortex/setup/workspace_files/` (fuente única
//! V8, leída por `render_cortex_sync_skill`); la copia desplegada trackeada en
//! `.cortex/skills/` debe coincidir con el SSoT (test congelado del oráculo
//! `test_canonical_skill_files_in_disk_match_renders`), y el skill thin
//! referencia su craft on-demand. Este test lo protege del lado Rust.

use std::path::{Path, PathBuf};

fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../..")
}

fn workspace_files() -> PathBuf {
    repo_root().join("cortex/setup/workspace_files")
}

fn deployed_skills() -> PathBuf {
    repo_root().join(".cortex/skills")
}

fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_else(|e| panic!("no se pudo leer {}: {e}", p.display()))
}

#[test]
fn sync_skill_is_thin_and_references_craft_on_demand() {
    let text = read(&workspace_files().join("cortex-sync.md"));
    // thin: el original tenía 144 líneas; el contrato thin (Ruling R10) apunta a ~60.
    assert!(
        text.lines().count() <= 100,
        "cortex-sync.md no quedó thin ({} líneas)",
        text.lines().count()
    );
    // contrato: frontmatter + gobernanza + referencia on-demand a los craft files.
    assert!(
        text.starts_with("---\nname: cortex-sync\n"),
        "frontmatter exacto"
    );
    assert!(
        text.contains("cortex_sync_ticket"),
        "mandatory first step (gobernanza)"
    );
    assert!(
        text.contains("cortex-sync-spec-craft.md"),
        "referencia craft spec"
    );
    assert!(
        text.contains("cortex-sync-proposal-craft.md"),
        "referencia craft proposal"
    );
}

#[test]
fn spec_craft_file_exists_with_content() {
    let text = read(&workspace_files().join("cortex-sync-spec-craft.md"));
    assert!(
        text.starts_with("---\n"),
        "frontmatter (e2e _has_frontmatter)"
    );
    assert!(text.len() > 500, "contenido craft real");
    assert!(
        text.to_lowercase().contains("criterios de aceptación"),
        "sección acceptance criteria"
    );
}

#[test]
fn proposal_craft_file_exists_with_content() {
    let text = read(&workspace_files().join("cortex-sync-proposal-craft.md"));
    assert!(
        text.starts_with("---\n"),
        "frontmatter (e2e _has_frontmatter)"
    );
    assert!(text.len() > 500, "contenido craft real");
    assert!(text.contains("rejected_reason"), "sección rejected_reason");
}

#[test]
fn deployed_copy_matches_ssot_byte_identique() {
    for name in [
        "cortex-sync.md",
        "cortex-sync-spec-craft.md",
        "cortex-sync-proposal-craft.md",
    ] {
        let ssot = read(&workspace_files().join(name));
        let deployed = read(&deployed_skills().join(name));
        assert_eq!(ssot, deployed, ".cortex/skills/{name} drifteó del SSoT");
    }
}
