//! Entorno Jinja2-compatible sobre minijinja.
//!
//! Réplica de `cortex.documentation.templates_engine`:
//!
//! ```python
//! Environment(
//!     loader=FileSystemLoader(TEMPLATES_DIR),
//!     autoescape=select_autoescape(disabled_extensions=("md.j2",)),
//!     trim_blocks=True,
//!     lstrip_blocks=True,
//!     keep_trailing_newline=True,
//! )
//! ```
//!
//! Las plantillas embebidas son copias byte-a-byte de los archivos reales
//! `cortex/documentation/templates/*.md.j2`; [`embedded_matches_disk`]
//! verifica la sincronía en tests (patrón del test de sincronía de
//! devsecdocops.sh).

use std::sync::OnceLock;

use minijinja::{Environment, Value};

/// Nombres canónicos de las 13 plantillas (sin extensión).
pub const TEMPLATE_NAMES: [&str; 13] = [
    "adr",
    "architecture",
    "changelog",
    "decision",
    "design",
    "glossary",
    "handoff",
    "hu",
    "incident",
    "postmortem",
    "runbook",
    "session",
    "spec",
];

/// Par (nombre estático, fuente embebida) de cada plantilla canónica.
pub const EMBEDDED_TEMPLATES: &[(&str, &str)] = &[
    (
        "adr.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/adr.md.j2"
        )),
    ),
    (
        "architecture.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/architecture.md.j2"
        )),
    ),
    (
        "changelog.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/changelog.md.j2"
        )),
    ),
    (
        "decision.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/decision.md.j2"
        )),
    ),
    (
        "design.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/design.md.j2"
        )),
    ),
    (
        "glossary.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/glossary.md.j2"
        )),
    ),
    (
        "handoff.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/handoff.md.j2"
        )),
    ),
    (
        "hu.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/hu.md.j2"
        )),
    ),
    (
        "incident.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/incident.md.j2"
        )),
    ),
    (
        "postmortem.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/postmortem.md.j2"
        )),
    ),
    (
        "runbook.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/runbook.md.j2"
        )),
    ),
    (
        "session.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/session.md.j2"
        )),
    ),
    (
        "spec.md.j2",
        include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../cortex/documentation/templates/spec.md.j2"
        )),
    ),
];

/// Fuente embebida de una plantilla canónica (byte-paridad con disco).
pub fn embedded_template_source(name: &str) -> Option<&'static str> {
    EMBEDDED_TEMPLATES
        .iter()
        .find(|(n, _)| *n == name)
        .map(|(_, src)| *src)
}

/// Construye el entorno con la semántica EXACTA del engine Python.
///
/// Nota de paridad: `autoescape=select_autoescape(disabled_extensions=
/// ("md.j2",))` deja sin escapado a las plantillas `.md.j2`, que es también
/// el default de minijinja para texto. Los flags de whitespace se setean
/// uno-a-uno con los valores de `_build_environment()`.
pub fn build_environment() -> Environment<'static> {
    let mut env = Environment::new();
    env.set_trim_blocks(true);
    env.set_lstrip_blocks(true);
    env.set_keep_trailing_newline(true);
    for (template, source) in EMBEDDED_TEMPLATES {
        env.add_template(template, source)
            .unwrap_or_else(|e| panic!("plantilla inválida {template}: {e}"));
    }
    env
}

/// Entorno global perezoso (equivalente al `_env` module-level de Python).
pub fn global_environment() -> &'static Environment<'static> {
    static ENV: OnceLock<Environment<'static>> = OnceLock::new();
    ENV.get_or_init(build_environment)
}

/// Renderiza `name` (ej. `"adr.md.j2"`) con `data` como contexto.
///
/// Espejo exacto de `render_template(name, data)`: el nombre lleva la
/// extensión `.md.j2`.
pub fn render_template(name: &str, data: &Value) -> Result<String, String> {
    let env = global_environment();
    let template = env
        .get_template(name)
        .map_err(|e| format!("Failed to render {name}: {e}"))?;
    template
        .render(data)
        .map_err(|e| format!("Failed to render {name}: {e}"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::PY_TEMPLATES_DIR;
    use minijinja::Value;
    use serde_json::json;

    #[test]
    fn embedded_templates_match_disk() {
        for name in TEMPLATE_NAMES {
            let file = format!("{name}.md.j2");
            let disk = std::fs::read_to_string(format!("{}/{file}", PY_TEMPLATES_DIR))
                .unwrap_or_else(|e| panic!("no se pudo leer {file}: {e}"));
            assert_eq!(
                embedded_template_source(&file).unwrap(),
                disk,
                "la copia embebida de {file} difiere del archivo real"
            );
        }
    }

    #[test]
    fn renders_simple_context() {
        // Paridad mínima contra el engine Python (ver golden completo en
        // tests/jinja_parity.rs).
        let data = json!({
            "context": "ctx",
            "decision": "dec",
            "alternative_rejected": "alt",
            "reason": "why",
            "reversible_within_days": 30,
        });
        let out = render_template("decision.md.j2", &Value::from_serialize(&data)).unwrap();
        assert!(out.starts_with("## Context\n\nctx\n"));
        assert!(out.contains("reverted within 30 days"));
    }

    #[test]
    fn trim_blocks_semantics_active() {
        // Con trim_blocks+lstrip_blocks activos, `{% if %}` en su propia
        // línea no deja líneas vacías: espeja el comportamiento jinja2 del
        // engine canónico (tests/unit/documentation/test_session_template_
        // conditional.py es LA spec).
        let data = json!({
            "title": "t", "session_id": "s", "spec_path": "p",
            "architecture_decision": "", "gitless": false,
            "task_type": "", "tasks": [], "spec_summary": "",
            "changes_made": [], "files_touched": [], "key_decisions": [],
            "next_steps": [], "verified_state": [], "unverified_claims": [],
            "blockers": [], "suggested_skills": [],
        });
        let out = render_template("session.md.j2", &Value::from_serialize(&data)).unwrap();
        // Sin gitless ni task_type security, NO debe aparecer la sección.
        assert!(!out.contains("Gitless Session"));
        assert!(out.starts_with("## Original Specification"));
    }
}
