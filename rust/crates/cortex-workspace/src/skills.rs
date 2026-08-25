//! Porteo de `cortex/skills/__init__.py` — instalación del bundle de skills
//! Obsidian embebido en el binario.
//!
//! Los recursos viven en `include_str!` sobre `cortex/skills/<nombre>/`
//! del monorepo (mismo patrón include_str! que cortex-setup desde P8): sin
//! dependencias nuevas y byte-idénticos por construcción. Si un skill no
//! puede instalarse (error de FS), se emite warning observable por stderr
//! y se continúa con el resto (review 9 #8: installs parciales visibles).

#![forbid(unsafe_code)]

use std::path::Path;

const SKILL_MARKDOWN_OBSIDIAN: &[(&str, &str)] = &[
    (
        "SKILL.md",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/skills/obsidian-markdown/SKILL.md"
        )),
    ),
    (
        "references/CALLOUTS.md",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/skills/obsidian-markdown/references/CALLOUTS.md"
        )),
    ),
    (
        "references/EMBEDS.md",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/skills/obsidian-markdown/references/EMBEDS.md"
        )),
    ),
    (
        "references/PROPERTIES.md",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/skills/obsidian-markdown/references/PROPERTIES.md"
        )),
    ),
];

const SKILL_JSON_CANVAS: &[(&str, &str)] = &[
    (
        "SKILL.md",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/skills/json-canvas/SKILL.md"
        )),
    ),
    (
        "references/EXAMPLES.md",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/skills/json-canvas/references/EXAMPLES.md"
        )),
    ),
];

const SKILL_OBSIDIAN_BASES: &[(&str, &str)] = &[
    (
        "SKILL.md",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/skills/obsidian-bases/SKILL.md"
        )),
    ),
    (
        "references/FUNCTIONS_REFERENCE.md",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/skills/obsidian-bases/references/FUNCTIONS_REFERENCE.md"
        )),
    ),
];

const SKILL_OBSIDIAN_CLI: &[(&str, &str)] = &[(
    "SKILL.md",
    include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../cortex/skills/obsidian-cli/SKILL.md"
    )),
)];

const SKILL_DEFUDDLE: &[(&str, &str)] = &[(
    "SKILL.md",
    include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../cortex/skills/defuddle/SKILL.md"
    )),
)];

/// Nombres canónicos del bundle (orden de `SKILL_NAMES`).
pub const SKILL_NAMES: &[&str] = &[
    "obsidian-markdown",
    "json-canvas",
    "obsidian-bases",
    "obsidian-cli",
    "defuddle",
];

fn bundle(name: &str) -> Option<&'static [(&'static str, &'static str)]> {
    match name {
        "obsidian-markdown" => Some(SKILL_MARKDOWN_OBSIDIAN),
        "json-canvas" => Some(SKILL_JSON_CANVAS),
        "obsidian-bases" => Some(SKILL_OBSIDIAN_BASES),
        "obsidian-cli" => Some(SKILL_OBSIDIAN_CLI),
        "defuddle" => Some(SKILL_DEFUDDLE),
        _ => None,
    }
}

/// Copia todos los skills embebidos a `target_dir` (típicamente
/// `.cortex/skills/`). Los destinos existentes se marcan
/// `"<name> (already exists)"`. Fallos por-skill ⇒ warning en stderr y
/// continúa. Devuelve los nombres instalados.
pub fn install_skills(target_dir: &Path) -> Vec<String> {
    if let Err(e) = std::fs::create_dir_all(target_dir) {
        eprintln!(
            "[cortex.skills] WARNING: no se pudo crear {}: {}",
            target_dir.display(),
            e
        );
        return Vec::new();
    }
    let mut installed = Vec::new();
    for name in SKILL_NAMES {
        let src = target_dir.join(name);
        if src.exists() {
            installed.push(format!("{name} (already exists)"));
            continue;
        }
        let files = match bundle(name) {
            Some(f) => f,
            None => continue,
        };
        match copy_bundle(files, &src) {
            Ok(()) => installed.push((*name).to_string()),
            Err(e) => {
                eprintln!("[cortex.skills] WARNING: Skill '{name}' no pudo instalarse: {e}");
            }
        }
    }
    installed
}

fn copy_bundle(files: &[(&str, &str)], dest: &Path) -> Result<(), String> {
    for (rel, content) in files {
        let target = dest.join(rel);
        if let Some(parent) = target.parent() {
            std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
        }
        std::fs::write(&target, content).map_err(|e| format!("{}: {e}", target.display()))?;
    }
    Ok(())
}
