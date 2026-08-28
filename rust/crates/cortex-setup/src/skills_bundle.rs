//! Bundle embebido de la familia COMPOSED y de la tríada thin+craft, con el
//! instalador de árboles que consume `cortex setup composed` (Obra 08 A11).
//!
//! Mismo patrón que `cortex_workspace::skills` (bundle Obsidian, P12): los
//! recursos viven en `include_str!` sobre los SSoT del monorepo
//! (`templates/composed/` de este crate — patrón P8 de plantillas embebidas —
//! y `cortex/setup/workspace_files/`, leído sóLO como dato, sin tocar código
//! Python). Instalación byte-idéntica por construcción; destinos existentes
//! se marcan `"(already exists)"` y NUNCA se pisán (las ediciones del usuario
//! sobreviven); fallos por-archivo ⇒ warning observable por stderr y el
//! bundle continúa (regla del instalador Obsidian, review 9 #8).

#![forbid(unsafe_code)]

use std::path::Path;

macro_rules! composed_file {
    ($rel:literal) => {
        (
            $rel,
            include_str!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/templates/composed/",
                $rel
            )),
        )
    };
}

macro_rules! workspace_file {
    ($rel:literal) => {
        (
            $rel,
            include_str!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../../cortex/setup/workspace_files/",
                $rel
            )),
        )
    };
}

/// Familia COMPOSED (G-A4a, SSoT `templates/composed/`): (ruta-relativa-al-dir
/// de la familia, contenido). 8 skills en formato directorio (SKILL.md +
/// agents/openai.yaml [+ references/]) + INSTALL-COMPOSED.md.
pub const COMPOSED_FAMILY: &[(&str, &str)] = &[
    composed_file!("grill/SKILL.md"),
    composed_file!("grill/agents/openai.yaml"),
    composed_file!("to-spec/SKILL.md"),
    composed_file!("to-spec/agents/openai.yaml"),
    composed_file!("to-tickets/SKILL.md"),
    composed_file!("to-tickets/agents/openai.yaml"),
    composed_file!("implement/SKILL.md"),
    composed_file!("implement/agents/openai.yaml"),
    composed_file!("implement/references/implement-craft.md"),
    composed_file!("tdd/SKILL.md"),
    composed_file!("tdd/agents/openai.yaml"),
    composed_file!("tdd/references/tdd-craft.md"),
    composed_file!("diagnose/SKILL.md"),
    composed_file!("diagnose/agents/openai.yaml"),
    composed_file!("review/SKILL.md"),
    composed_file!("review/agents/openai.yaml"),
    composed_file!("review/references/review-craft.md"),
    composed_file!("glossary/SKILL.md"),
    composed_file!("glossary/agents/openai.yaml"),
    composed_file!("INSTALL-COMPOSED.md"),
];

/// Tríada triádica thin + sus craft on-demand (A7-A9, SSoT
/// `cortex/setup/workspace_files/` — dato, no código Python). Un proyecto
/// fresco que corre `setup composed` recibe el thin Y el craft juntos, para
/// que la referencia "Pericia on-demand" del thin nunca quede rota.
pub const TRIAD_SKILLS: &[(&str, &str)] = &[
    workspace_file!("cortex-sync.md"),
    workspace_file!("cortex-sync-spec-craft.md"),
    workspace_file!("cortex-sync-proposal-craft.md"),
    workspace_file!("cortex-SDDwork.md"),
    workspace_file!("cortex-SDDwork-implement-craft.md"),
    workspace_file!("cortex-documenter.md"),
    workspace_file!("cortex-documenter-close-craft.md"),
];

/// Unidad de despliegue de una ruta: primer segmento (`"grill"`) o el archivo
/// mismo en la raíz (`"INSTALL-COMPOSED.md"`, `"cortex-sync.md"`).
fn unit_of(rel: &str) -> &str {
    match rel.split_once('/') {
        Some((head, _)) => head,
        None => rel,
    }
}

/// Escribe `entries` bajo `target_dir` omitiendo destinos existentes. Una
/// unidad se reporta `"<unit> (already exists)"` solo si TODOS sus archivos
/// ya estaban; si faltaba alguno, se completa sin pisar los existentes.
fn install_bundle(target_dir: &Path, entries: &[(&str, &str)]) -> Vec<String> {
    if let Err(e) = std::fs::create_dir_all(target_dir) {
        eprintln!("warning: no se pudo crear {}: {e}", target_dir.display());
        return Vec::new();
    }
    let mut units: Vec<&str> = Vec::new();
    for (rel, _) in entries {
        let u = unit_of(rel);
        if !units.contains(&u) {
            units.push(u);
        }
    }
    let mut made = Vec::new();
    for unit in units {
        let mut all_exist = true;
        for (rel, content) in entries.iter().filter(|(rel, _)| unit_of(rel) == unit) {
            let dest = target_dir.join(rel);
            if dest.exists() {
                continue;
            }
            all_exist = false;
            if let Some(dir) = dest.parent() {
                if let Err(e) = std::fs::create_dir_all(dir) {
                    eprintln!("warning: mkdir {}: {e}", dir.display());
                    continue;
                }
            }
            match std::fs::write(&dest, content) {
                Ok(()) => {}
                Err(e) => eprintln!("warning: write {}: {e}", dest.display()),
            }
        }
        made.push(if all_exist {
            format!("{unit} (already exists)")
        } else {
            unit.to_string()
        });
    }
    made
}

/// Instala la familia COMPOSED en `target_dir` (típicamente
/// `<proyecto>/.cortex/skills/composed`). Devuelve las unidades instaladas o
/// marcadas como ya existentes.
pub fn install_composed_family(target_dir: &Path) -> Vec<String> {
    install_bundle(target_dir, COMPOSED_FAMILY)
}

/// Instala la tríada thin + craft (planos) en `target_dir` (típicamente
/// `<proyecto>/.cortex/skills`). Devuelve las unidades (nombres de archivo).
pub fn install_triad_skills(target_dir: &Path) -> Vec<String> {
    install_bundle(target_dir, TRIAD_SKILLS)
}

/// Marcadores DEDICADOS del bloque `## Agent skills` (R12, Obra 08 A13).
/// No son los canónicos (`CORTEX_MARKER_OPEN/CLOSE`, usados por la sección
/// codex en AGENTS.md): compartirlos hacía que `setup composed` y
/// `setup agent --ide codex` se pisaran en silencio (upsert reemplaza todo
/// el span). Cada sección vive entre sus propios marcadores.
pub const COMPOSED_MARKER_OPEN: &str =
    "<!-- BEGIN CORTEX AGENT SKILLS (auto-generated, do not edit) -->";
pub const COMPOSED_MARKER_CLOSE: &str = "<!-- END CORTEX AGENT SKILLS -->";

/// Bloque `## Agent skills` para CLAUDE.md/AGENTS.md, entre los marcadores
/// DEDICADOS `COMPOSED_MARKER_*` (R12: los canónicos están reservados para
/// la sección codex; `upsert_marker_block_with` da reemplazo idempotente
/// por sección, precedente codex AGENTS.md).
pub fn agent_skills_block() -> String {
    let body = "\
## Agent skills

Este proyecto usa la familia de skills COMPOSED de Cortex (en \
`.cortex/skills/composed/`). Cada skill termina su etapa emitiendo un \
checkpoint con `phase` via `cortex_session_checkpoint` (source `user-skill`) \
— asi Cortex infiere el modo `composed`, mide la linea de fases y cierra con \
evidencia.

- User-invoked (el humano las invoca): `grill`, `to-spec`, `to-tickets`, \
`review`, `glossary`.
- Model-invoked (el modelo las alcanza por descripcion): `implement`, `tdd`, \
`diagnose`.
- Cadena de fases: grill -> spec -> plan -> implement -> review -> close \
(cierre: `cortex finish-session`).
- La pericia de cada skill vive on-demand en sus `references/` y en los \
craft hermanos de `.cortex/skills/` (`cortex-sync-spec-craft.md`, \
`cortex-sync-proposal-craft.md`, `cortex-SDDwork-implement-craft.md`, \
`cortex-documenter-close-craft.md`).
- Skills de terceros (mattpocock, superpowers, propias): solo deben cumplir \
el contrato del checkpoint — ver `.cortex/skills/composed/INSTALL-COMPOSED.md`.
";
    format!(
        "{}\n\n{body}\n{}",
        COMPOSED_MARKER_OPEN, COMPOSED_MARKER_CLOSE
    )
}
