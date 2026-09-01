//! Tabla de ruteo canónica — réplica de
//! `cortex/documentation/routing.py` (sólo lo que consume el writer:
//! subfolder, filename_template, plantilla, enterprise_subfolder).

use std::path::{Path, PathBuf};

use crate::doc_type::DocType;

#[derive(Debug, Clone)]
pub struct RouteSpec {
    pub doc_type: DocType,
    pub subfolder: &'static str,
    pub filename_template: &'static str,
    /// Nombre de archivo de la plantilla jinja (route.template_path.name).
    pub template_name: &'static str,
    pub promotable: bool,
    /// None = no promovible (enterprise_subfolder=None).
    pub enterprise_subfolder: Option<&'static str>,
}

pub fn resolve_route(doc_type: DocType) -> RouteSpec {
    use DocType::*;
    let (subfolder, filename_template, template_name, promotable, enterprise_subfolder) =
        match doc_type {
            Session => (
                "sessions",
                "{session_id}_{slug}.md",
                "session.md.j2",
                true,
                Some("sessions/{project_id}"),
            ),
            Handoff => ("handoffs", "{date}_{slug}.md", "handoff.md.j2", false, None),
            Spec => (
                "specs",
                "{date}_{slug}.md",
                "spec.md.j2",
                true,
                Some("specs/{project_id}"),
            ),
            Adr => (
                "decisions",
                "ADR-{number:03d}-{slug}.md",
                "adr.md.j2",
                true,
                Some("decisions/{project_id}"),
            ),
            Decision => (
                "decisions",
                "DEC-{date}-{slug}.md",
                "decision.md.j2",
                true,
                Some("decisions/{project_id}"),
            ),
            Incident => (
                "incidents",
                "INC-{number:03d}-{date}-{slug}.md",
                "incident.md.j2",
                true,
                Some("incidents/{project_id}"),
            ),
            Postmortem => (
                "postmortems",
                "PM-{incident_number:03d}-{slug}.md",
                "postmortem.md.j2",
                true,
                Some("postmortems/{project_id}"),
            ),
            Runbook => (
                "runbooks",
                "RB-{slug}.md",
                "runbook.md.j2",
                true,
                Some("runbooks/{project_id}"),
            ),
            Architecture => (
                "architecture",
                "{slug}.md",
                "architecture.md.j2",
                true,
                Some("architecture/{project_id}"),
            ),
            Changelog => (
                "changelog",
                "{version}.md",
                "changelog.md.j2",
                true,
                Some("changelog/{project_id}"),
            ),
            Hu => ("hu", "HU-{external_id}.md", "hu.md.j2", false, None),
            Glossary => (
                "glossary",
                "{term_slug}.md",
                "glossary.md.j2",
                true,
                Some("glossary"),
            ),
            Design => ("designs", "{session_id}.md", "design.md.j2", false, None),
        };
    RouteSpec {
        doc_type,
        subfolder,
        filename_template,
        template_name,
        promotable,
        enterprise_subfolder,
    }
}

/// Contexto de nombre de archivo (equivalente al dict que arma el writer).
#[derive(Debug, Clone, Default)]
pub struct FilenameCtx {
    pub date: String,
    pub slug: String,
    pub number: i64,
    pub incident_number: i64,
    pub session_id: String,
    pub external_id: String,
    pub version: String,
    pub term_slug: String,
}

impl FilenameCtx {
    /// `render_filename`: sustituye placeholders `{name}` y `{name:03d}`
    /// del template con el contexto. Los placeholders requeridos dependen
    /// del DocType; los campos se toman tal cual Python los setea en
    /// ``_build_filename_context``.
    pub fn render(&self, spec: &RouteSpec) -> Result<String, String> {
        let mut out = String::new();
        let tpl = spec.filename_template;
        let bytes = tpl.as_bytes();
        let mut i = 0;
        while i < bytes.len() {
            if bytes[i] == b'{' {
                if let Some(close) = tpl[i + 1..].find('}') {
                    let ph = &tpl[i + 1..i + 1 + close];
                    // separar format spec ":03d"
                    let (name, spec_part) = match ph.find(':') {
                        Some(c) => (&ph[..c], Some(&ph[c + 1..])),
                        None => (ph, None),
                    };
                    let value = match name {
                        "date" => self.date.clone(),
                        "slug" => self.slug.clone(),
                        "number" => self.number.to_string(),
                        "incident_number" => self.incident_number.to_string(),
                        "session_id" => self.session_id.clone(),
                        "external_id" => self.external_id.clone(),
                        "version" => self.version.clone(),
                        "term_slug" => self.term_slug.clone(),
                        other => return Err(format!("placeholder desconocido: {other}")),
                    };
                    match spec_part {
                        Some("03d") => {
                            let n: i64 =
                                value.parse().map_err(|_| "número inválido".to_string())?;
                            out.push_str(&format!("{n:03}"));
                        }
                        None => out.push_str(&value),
                        Some(other) => return Err(format!("format spec no soportado: {other}")),
                    }
                    i += 1 + close + 1;
                    continue;
                }
            }
            out.push(bytes[i] as char);
            i += 1;
        }
        Ok(out)
    }
}

/// `resolve_target_path`.
pub fn resolve_target_path(
    spec: &RouteSpec,
    ctx: &FilenameCtx,
    vault_root: &Path,
    vault_scope: &str,
    project_id: Option<&str>,
) -> Result<PathBuf, String> {
    let subfolder = match vault_scope {
        "enterprise" => {
            let tmpl = spec.enterprise_subfolder.ok_or_else(|| {
                format!(
                    "{} is not promotable (no enterprise_subfolder)",
                    spec.doc_type.as_str()
                )
            })?;
            if tmpl.contains("{project_id}") && project_id.is_none() {
                return Err(format!(
                    "project_id required for enterprise scope of {}",
                    spec.doc_type.as_str()
                ));
            }
            tmpl.replace("{project_id}", project_id.unwrap_or(""))
        }
        "local" => spec.subfolder.to_string(),
        other => {
            return Err(format!(
                "vault_scope must be 'local' or 'enterprise', got {other:?}"
            ))
        }
    };
    let filename = ctx.render(spec)?;
    Ok(vault_root.join(subfolder).join(filename))
}
