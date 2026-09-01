//! Inventario y contrato de la familia de skills COMPOSED (Obra 08 stream A, G-A4a).
//!
//! El SSoT de la familia vive en este crate (`templates/composed/`): son archivos
//! NUEVOS sin constraint del oráculo Python (Ruling R10 del ledger de la obra), en
//! formato directorio (`SKILL.md` + `references/` + `agents/openai.yaml`, convención
//! mattpocock verificada en `docs/transformacion/investigacion-mattpocock-skills.md`).
//! `cortex setup composed` (A11) la despliega en `.cortex/skills/composed/` de los
//! proyectos; este test protege el inventario exacto y el contrato de checkpoint.

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

fn composed_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("templates/composed")
}

fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_else(|e| panic!("no se pudo leer {}: {e}", p.display()))
}

/// (skill, phase que emite, user_invoked)
const SKILLS: &[(&str, &str, bool)] = &[
    ("grill", "grill", true),
    ("to-spec", "spec", true),
    ("to-tickets", "plan", true),
    ("implement", "implement", false),
    ("tdd", "implement", false),
    ("diagnose", "implement", false),
    ("review", "review", true),
    ("glossary", "spec", true),
];

#[test]
fn family_inventory_is_exact() {
    let root = composed_dir();
    let mut dirs = BTreeSet::new();
    let mut files = BTreeSet::new();
    for entry in std::fs::read_dir(&root).expect("templates/composed debe existir") {
        let entry = entry.unwrap();
        let name = entry.file_name().to_string_lossy().to_string();
        if entry.path().is_dir() {
            dirs.insert(name);
        } else {
            files.insert(name);
        }
    }
    let expected: BTreeSet<String> = SKILLS.iter().map(|(s, _, _)| s.to_string()).collect();
    assert_eq!(
        dirs, expected,
        "los 8 dirs de la familia, sin extras ni faltantes"
    );
    assert!(
        files.contains("INSTALL-COMPOSED.md"),
        "INSTALL-COMPOSED.md al lado de los dirs"
    );

    for (skill, _, _) in SKILLS {
        let base = root.join(skill);
        assert!(
            base.join("SKILL.md").is_file(),
            "{skill}/SKILL.md debe existir"
        );
        assert!(
            base.join("agents/openai.yaml").is_file(),
            "{skill}/agents/openai.yaml (doble harness)"
        );
    }
    // referencias de craft on-demand (mínimo: implement, review, tdd)
    for skill in ["implement", "review", "tdd"] {
        let refs = root.join(skill).join("references");
        assert!(refs.is_dir(), "{skill}/references/ debe existir");
        assert!(
            std::fs::read_dir(&refs).unwrap().count() >= 1,
            "{skill}/references/ no vacío"
        );
    }
}

#[test]
fn skills_stay_thin() {
    // Contrato thin: 40-90 líneas (contenido real, no esqueletos; sin manuales de 300).
    for (skill, _, _) in SKILLS {
        let n = read(&composed_dir().join(skill).join("SKILL.md"))
            .lines()
            .count();
        assert!(
            (40..=90).contains(&n),
            "{skill}: {n} líneas fuera del rango thin [40,90]"
        );
    }
}

#[test]
fn each_skill_emits_the_phase_contract_checkpoint() {
    for (skill, phase, _) in SKILLS {
        let text = read(&composed_dir().join(skill).join("SKILL.md"));
        assert!(
            text.contains("cortex_session_checkpoint"),
            "{skill}: debe mostrar la llamada MCP exacta"
        );
        assert!(
            text.contains(&format!("\"phase\": \"{phase}\"")),
            "{skill}: debe usar el argumento explícito phase=\"{phase}\" — el inputSchema congelado no lo lista y hay que pasarlo igual"
        );
        assert!(
            text.contains("\"source\": \"user-skill\""),
            "{skill}: source user-skill (decisión 1.2 del spec 13)"
        );
        for field in [
            "verified_claims",
            "unverified_claims",
            "artifacts_touched",
            "note",
        ] {
            assert!(
                text.contains(field),
                "{skill}: el checkpoint debe mencionar {field}"
            );
        }
    }
}

#[test]
fn frontmatter_matches_invocation_convention() {
    for (skill, _, user_invoked) in SKILLS {
        let text = read(&composed_dir().join(skill).join("SKILL.md"));
        assert!(
            text.starts_with(&format!("---\nname: {skill}\n")),
            "{skill}: frontmatter name exacto"
        );
        assert!(
            text.contains("\ndescription: "),
            "{skill}: description presente"
        );
        assert!(
            text.contains("\nwhen-to-use: "),
            "{skill}: when-to-use presente"
        );
        if *user_invoked {
            assert!(
                text.contains("disable-model-invocation: true"),
                "{skill}: user-invoked ⇒ flag obligatorio"
            );
        } else {
            assert!(
                !text.contains("disable-model-invocation"),
                "{skill}: model-invoked ⇒ sin flag"
            );
            assert!(
                text.contains("Usar cuando") || text.contains("Use when"),
                "{skill}: model-invoked necesita phrasing de disparador en la descripción"
            );
        }
    }
}

#[test]
fn openai_yaml_mirrors_policy() {
    for (skill, _, user_invoked) in SKILLS {
        let yaml = read(&composed_dir().join(skill).join("agents/openai.yaml"));
        assert!(
            yaml.contains("display_name"),
            "{skill}: metadata de interface"
        );
        assert!(
            yaml.contains("instructions"),
            "{skill}: instrucciones = resumen del SKILL.md"
        );
        if *user_invoked {
            assert!(
                yaml.contains("allow_implicit_invocation: false"),
                "{skill}: user-invoked ⇒ policy false (convención Codex verificada en la investigación)"
            );
        } else {
            assert!(
                !yaml.contains("allow_implicit_invocation"),
                "{skill}: model-invoked ⇒ omitir el bloque de policy (default)"
            );
        }
    }
}

#[test]
fn phase_gate_thresholds_are_documented() {
    // El gate de A3 (cortex-app quality_gates::check_phase_gate) exige evidencia
    // >10 chars por fase; las skills deben decirlo para que el checkpoint PASE.
    for skill in [
        "to-spec",
        "implement",
        "tdd",
        "diagnose",
        "review",
        "glossary",
    ] {
        let text = read(&composed_dir().join(skill).join("SKILL.md"));
        assert!(
            text.contains(">10 chars"),
            "{skill}: documenta el umbral de evidencia >10 chars del gate"
        );
    }
    // plan/implement exigen artifacts_touched no vacío ⇒ las skills que los emiten lo nombran
    for skill in ["to-tickets", "implement", "tdd", "diagnose"] {
        let text = read(&composed_dir().join(skill).join("SKILL.md"));
        assert!(
            text.contains("artifacts_touched"),
            "{skill}: artifacts_touched del gate"
        );
    }
    // implement sin evidencia ⇒ redelegate: la consecuencia debe estar dicha
    let imp = read(&composed_dir().join("implement/SKILL.md"));
    assert!(
        imp.contains("redelegate"),
        "implement: documenta la consecuencia dura del gate"
    );
    // grill no tiene gate de evidencia (spec 13 §3) ⇒ no debe exigir el umbral
    let grill = read(&composed_dir().join("grill/SKILL.md"));
    assert!(!grill.contains(">10 chars"), "grill: sin gate, sin umbral");
}

#[test]
fn grill_carries_anti_rationalization_signals() {
    // La tabla anti-racionalización (dropeada del thin de A7) vive en grill.
    let grill = read(&composed_dir().join("grill/SKILL.md"));
    assert!(
        grill.contains("Anti-Rationalization"),
        "grill: sección real de Anti-Rationalization Signals"
    );
}

#[test]
fn craft_references_are_linked_from_skills() {
    for skill in ["implement", "review", "tdd"] {
        let text = read(&composed_dir().join(skill).join("SKILL.md"));
        assert!(
            text.contains("references/"),
            "{skill}: referencia su craft on-demand"
        );
    }
}

#[test]
fn install_doc_covers_import_and_own_skill() {
    let doc = read(&composed_dir().join("INSTALL-COMPOSED.md"));
    assert!(
        doc.contains("cortex setup composed"),
        "instrucción de instalación (A11)"
    );
    assert!(
        doc.contains("skills.sh") || doc.contains("mattpocock"),
        "cómo importar flujos mattpocock-style"
    );
    assert!(
        doc.contains("superpowers"),
        "cómo importar flujos superpowers-style"
    );
    assert!(
        doc.contains("cortex_session_checkpoint") && doc.contains("phase"),
        "contrato para escribir una skill propia"
    );
}
