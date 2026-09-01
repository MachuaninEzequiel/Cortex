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
    // cierre: comando REAL wireado en dispatch_native (R13: `finish-session`
    // no existe ⇒ rc 2; el flujo verificado es `cortex autopilot finish`)
    assert!(
        block.contains("cortex autopilot finish"),
        "cierre: debe instruir un comando wireado"
    );
    assert!(
        !block.contains("finish-session"),
        "cierre: no debe instruir comandos muertos"
    );
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

// ── R12 (Obra 08 A13): el bloque composed debe usar marcadores DEDICADOS ──
// Los marcadores canónicos CORTEX_MARKER_OPEN/CLOSE son los de la sección
// codex en AGENTS.md; compartirlos hace que `setup composed` y
// `setup agent --ide codex` se pisen en silencio (upsert reemplaza todo span).

#[test]
fn agent_skills_block_uses_dedicated_markers() {
    let block = cortex_setup::skills_bundle::agent_skills_block();
    assert!(
        block.contains(cortex_setup::skills_bundle::COMPOSED_MARKER_OPEN),
        "el bloque abre con el marcador dedicado"
    );
    assert!(
        block.contains(cortex_setup::skills_bundle::COMPOSED_MARKER_CLOSE),
        "el bloque cierra con el marcador dedicado"
    );
    assert!(
        !block.contains(cortex_setup::ide::base::CORTEX_MARKER_OPEN),
        "NO debe llevar los marcadores canónicos (colisión codex, R12)"
    );
}

#[test]
fn composed_and_codex_blocks_coexist_in_one_agents_md() {
    use cortex_setup::ide::base::{
        upsert_marker_block, upsert_marker_block_with, CORTEX_MARKER_CLOSE, CORTEX_MARKER_OPEN,
    };
    let codex_block =
        format!("{CORTEX_MARKER_OPEN}\n## Codex workflow\ntriad anchors\n{CORTEX_MARKER_CLOSE}");
    let composed_block = cortex_setup::skills_bundle::agent_skills_block();

    // estado inicial: sección codex escrita por `setup agent --ide codex`
    let mut doc = format!("# Mi proyecto\n\n{codex_block}\n");

    // setup composed NO debe tocar la sección codex
    doc = upsert_marker_block_with(
        &doc,
        &composed_block,
        cortex_setup::skills_bundle::COMPOSED_MARKER_OPEN,
        cortex_setup::skills_bundle::COMPOSED_MARKER_CLOSE,
    );
    assert!(doc.contains("## Codex workflow"), "codex sobrevive");
    assert!(doc.contains("## Agent skills"), "composed se escribe");

    // codex re-upsert (setup agent --ide codex otra vez) NO debe tocar composed
    let codex_block2 =
        format!("{CORTEX_MARKER_OPEN}\n## Codex workflow\ntriad anchors v2\n{CORTEX_MARKER_CLOSE}");
    doc = upsert_marker_block(&doc, &codex_block2);
    assert!(doc.contains("## Agent skills"), "composed sobrevive");
    assert!(doc.contains("triad anchors v2"), "codex se actualiza");
    assert!(
        !doc.contains("triad anchors\n"),
        "el reemplazo codex sigue siendo reemplazo"
    );

    // idempotencia por ambos lados: un span de cada tras replay
    doc = upsert_marker_block_with(
        &doc,
        &composed_block,
        cortex_setup::skills_bundle::COMPOSED_MARKER_OPEN,
        cortex_setup::skills_bundle::COMPOSED_MARKER_CLOSE,
    );
    doc = upsert_marker_block(&doc, &codex_block2);
    assert_eq!(
        doc.matches(cortex_setup::skills_bundle::COMPOSED_MARKER_OPEN)
            .count(),
        1,
        "composed no se duplica"
    );
    assert_eq!(
        doc.matches(CORTEX_MARKER_OPEN).count(),
        1,
        "codex no se duplica"
    );
}
