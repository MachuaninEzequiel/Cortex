//! El bundle embebido de la familia COMPOSED y la tríada thin+craft debe
//! coincidir byte-a-byte con sus SSoT en disco (patrón include_str! P8:
//! "copia embebida == disco"). Protege `cortex setup composed` (A11) de
//! templates agregados sin registrar o includes desactualizados.

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

fn manifest_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).to_path_buf()
}

fn composed_sso() -> PathBuf {
    manifest_dir().join("templates/composed")
}

fn workspace_files_sso() -> PathBuf {
    manifest_dir().join("../../../cortex/setup/workspace_files")
}

fn walk(root: &Path, rel: &str, out: &mut BTreeSet<String>) {
    for entry in std::fs::read_dir(root).expect("dir SSoT debe existir") {
        let entry = entry.unwrap();
        let name = entry.file_name().to_string_lossy().to_string();
        let child_rel = if rel.is_empty() {
            name.clone()
        } else {
            format!("{rel}/{name}")
        };
        if entry.file_type().unwrap().is_dir() {
            walk(&entry.path(), &child_rel, out);
        } else {
            out.insert(child_rel);
        }
    }
}

fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_else(|e| panic!("no se pudo leer {}: {e}", p.display()))
}

#[test]
fn composed_family_embedded_matches_disk_sso() {
    let mut disk = BTreeSet::new();
    walk(&composed_sso(), "", &mut disk);
    let embedded: BTreeSet<&str> = cortex_setup::skills_bundle::COMPOSED_FAMILY
        .iter()
        .map(|(p, _)| *p)
        .collect();
    let disk_refs: BTreeSet<&str> = disk.iter().map(String::as_str).collect();
    assert_eq!(
        embedded, disk_refs,
        "inventario embebido != SSoT en disco (¿template nuevo sin include?)"
    );
    for (rel, content) in cortex_setup::skills_bundle::COMPOSED_FAMILY {
        assert_eq!(
            *content,
            read(&composed_sso().join(rel)),
            "include_str! desactualizado para {rel}"
        );
    }
    // cordura: los 20 archivos esperados (8 SKILL.md + 8 openai.yaml + 3 references + INSTALL)
    assert_eq!(embedded.len(), 20, "inventario exacto de la familia");
}

#[test]
fn triad_thin_and_craft_embedded_matches_disk_sso() {
    let expected = [
        "cortex-sync.md",
        "cortex-sync-spec-craft.md",
        "cortex-sync-proposal-craft.md",
        "cortex-SDDwork.md",
        "cortex-SDDwork-implement-craft.md",
        "cortex-documenter.md",
        "cortex-documenter-close-craft.md",
    ];
    let embedded: BTreeSet<&str> = cortex_setup::skills_bundle::TRIAD_SKILLS
        .iter()
        .map(|(p, _)| *p)
        .collect();
    assert_eq!(
        embedded,
        expected.iter().copied().collect::<BTreeSet<&str>>()
    );
    for (rel, content) in cortex_setup::skills_bundle::TRIAD_SKILLS {
        assert_eq!(
            *content,
            read(&workspace_files_sso().join(rel)),
            "include_str! desactualizado para {rel}"
        );
    }
}

#[test]
fn agent_skills_block_carries_the_contract() {
    let block = cortex_setup::skills_bundle::agent_skills_block();
    assert!(block.contains("## Agent skills"), "titulo del bloque");
    assert!(block.contains("phase"), "contrato: checkpoint con phase");
    assert!(
        block.contains("cortex_session_checkpoint"),
        "contrato: tool de checkpoint"
    );
    // las 8 skills nombradas + referencia al INSTALL
    for name in [
        "grill",
        "to-spec",
        "to-tickets",
        "implement",
        "tdd",
        "diagnose",
        "review",
        "glossary",
    ] {
        assert!(block.contains(name), "bloque nombra {name}");
    }
    assert!(
        block.contains("INSTALL-COMPOSED.md"),
        "puntero al doc de import"
    );
}

#[test]
fn install_bundles_are_idempotent_and_partial_safe() {
    // patrón de dirs temporales del crate (hooks_parity/setup_parity): temp_dir + id único
    static SEQ: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
    let seq = SEQ.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    let tmp =
        std::env::temp_dir().join(format!("cortex-skills-bundle-{seq}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&tmp);

    // primera corrida: escribe todo
    let fam = cortex_setup::skills_bundle::install_composed_family(&tmp.join("composed"));
    assert!(
        fam.iter().any(|n| n == "grill"),
        "primera corrida instala grill: {fam:?}"
    );
    assert!(
        tmp.join("composed/grill/SKILL.md").exists()
            && tmp.join("composed/tdd/references/tdd-craft.md").exists(),
        "arboles con references/"
    );
    // segunda corrida: todo ya existe
    let fam2 = cortex_setup::skills_bundle::install_composed_family(&tmp.join("composed"));
    assert!(
        fam2.iter().all(|n| n.contains("(already exists)")),
        "segunda corrida: {fam2:?}"
    );
    // edicion del usuario NUNCA se pisa
    std::fs::write(tmp.join("composed/grill/SKILL.md"), b"custom").unwrap();
    cortex_setup::skills_bundle::install_composed_family(&tmp.join("composed"));
    assert_eq!(read(&tmp.join("composed/grill/SKILL.md")), "custom");
    // parcial: falta un archivo de un skill ya iniciado ⇒ se completa sin pisar el resto
    std::fs::remove_file(tmp.join("composed/tdd/agents/openai.yaml")).unwrap();
    cortex_setup::skills_bundle::install_composed_family(&tmp.join("composed"));
    assert!(tmp.join("composed/tdd/agents/openai.yaml").exists());
    assert_eq!(read(&tmp.join("composed/grill/SKILL.md")), "custom");

    // triada: idemipotente y crea los 7 planos
    let tri = cortex_setup::skills_bundle::install_triad_skills(&tmp.join("skills"));
    assert!(tri.iter().any(|n| n == "cortex-sync.md"), "triada: {tri:?}");
    assert!(tmp.join("skills/cortex-sync-spec-craft.md").exists());
    let tri2 = cortex_setup::skills_bundle::install_triad_skills(&tmp.join("skills"));
    assert!(
        tri2.iter().all(|n| n.contains("(already exists)")),
        "replay triada: {tri2:?}"
    );

    let _ = std::fs::remove_dir_all(&tmp);
}
