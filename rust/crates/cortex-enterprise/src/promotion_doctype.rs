//! Puerto de `cortex.enterprise.promotion_doctype` (Fase 10): promoción
//! DocType-aware con modos `as-is` / `summarize` / `review-required`,
//! frontmatter enterprise con audit trail, y cola de drafts.
//!
//! La tabla canónica vive en `cortex_setup::routing::resolve_route`
//! (promotable/enterprise_subfolder). Los campos `promotion_mode` y
//! `requires_review_before_publish`, aún ausentes del RouteSpec nativo,
//! se espejan localmente 1:1 desde `cortex/documentation/routing.py`.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use cortex_setup::doc_type::DocType;
use cortex_setup::routing::resolve_route;
use cortex_setup::yaml as pyyaml;

use crate::clock::{isoformat_full, Clock};
use crate::error::EnterpriseError;
use crate::frontmatter::{split_frontmatter, yaml_value_to_node};
use crate::governance;
use crate::models::EnterpriseOrgConfig;

/// Modo de promoción por DocType (tabla Python routing.py).
fn promotion_mode(doc_type: DocType) -> &'static str {
    match doc_type {
        DocType::Session => "summarize",
        DocType::Runbook => "review-required",
        _ => "as-is",
    }
}

/// Requiere review antes de publicar (sólo postmortem y runbook).
fn requires_review_before_publish(doc_type: DocType) -> bool {
    matches!(doc_type, DocType::Postmortem | DocType::Runbook)
}

#[derive(Debug, Clone)]
pub struct PromotionResult {
    pub source_path: PathBuf,
    pub target_path: PathBuf,
    pub doc_type: &'static str,
    pub promotion_mode: String,
    pub summarized: bool,
    pub fingerprint: String,
    pub requires_review: bool,
}

pub struct PromoteArgs<'a> {
    pub source_path: &'a Path,
    pub enterprise_vault_root: &'a Path,
    pub org: &'a EnterpriseOrgConfig,
    pub project_id: &'a str,
    pub actor: &'a str,
    pub reason: Option<&'a str>,
    pub dry_run: bool,
    pub clock: &'a dyn Clock,
}

fn validation(message: impl Into<String>) -> EnterpriseError {
    EnterpriseError::Validation(message.into())
}

/// `_read_note`: (fm dict tolerante, body). FM inválido/no-mapping ⇒ {}.
fn read_note(path: &Path) -> Result<(serde_yaml::Value, String), EnterpriseError> {
    let raw = std::fs::read_to_string(path)?;
    let fm = match split_frontmatter(&raw) {
        Some(split) => split.fm,
        None => serde_yaml::Value::Mapping(Default::default()),
    };
    let fm = if matches!(fm, serde_yaml::Value::Mapping(_)) {
        fm
    } else {
        serde_yaml::Value::Mapping(Default::default())
    };
    // body = lo que sigue al bloque; re-split para obtener el cuerpo crudo.
    let body = split_body_of(&raw);
    Ok((fm, body))
}

/// Cuerpo crudo tras el frontmatter ("" si no hay bloque).
fn split_body_of(raw: &str) -> String {
    match split_frontmatter(raw) {
        Some(s) => s.body,
        None => raw.to_string(),
    }
}

fn fm_get<'a>(fm: &'a serde_yaml::Value, key: &str) -> Option<&'a serde_yaml::Value> {
    fm.get(key)
}

fn fm_str<'a>(fm: &'a serde_yaml::Value, key: &str) -> Option<&'a str> {
    fm_get(fm, key).and_then(|v| v.as_str())
}

/// `promote_note_doctype_aware`.
pub fn promote_note_doctype_aware(
    args: PromoteArgs<'_>,
) -> Result<PromotionResult, EnterpriseError> {
    // 1. Permisos antes que existencia (precedencia Python).
    governance::assert_can_promote(args.actor, args.org)?;

    if !args.source_path.exists() {
        return Err(validation(format!(
            "source not found: {}",
            args.source_path.display()
        )));
    }

    let (fm, body) = read_note(args.source_path)?;
    let has_fm = matches!(fm, serde_yaml::Value::Mapping(ref m) if !m.is_empty());
    if !has_fm {
        return Err(validation(format!(
            "missing or invalid frontmatter: {}",
            args.source_path.display()
        )));
    }

    let Some(raw_doc_type) = fm_str(&fm, "doc_type") else {
        return Err(validation(format!(
            "source has no doc_type: {}",
            args.source_path.display()
        )));
    };
    let Some(doc_type) = DocType::parse(raw_doc_type) else {
        return Err(validation(format!(
            "unknown doc_type '{raw_doc_type}' in {}",
            args.source_path.display()
        )));
    };

    let route = resolve_route(doc_type);
    if !route.promotable {
        return Err(validation(format!(
            "'{}' is not promotable (promotable=False in RouteSpec)",
            route.doc_type.as_str()
        )));
    }

    // Incident severity gate: sólo el string exacto "low" bloquea.
    if doc_type == DocType::Incident && fm_str(&fm, "severity") == Some("low") {
        return Err(validation(
            "INCIDENT with severity=low is not promoted (gate by Fase 10)",
        ));
    }

    // Target: subfolder.format(project_id) / filename fuente.
    let Some(subfolder_tpl) = route.enterprise_subfolder else {
        return Err(validation(format!(
            "'{}' has no enterprise_subfolder configured",
            route.doc_type.as_str()
        )));
    };
    let subfolder = subfolder_tpl.replace("{project_id}", args.project_id);
    let file_name = args
        .source_path
        .file_name()
        .ok_or_else(|| validation("source sin nombre de archivo"))?
        .to_os_string();
    let target_path = args.enterprise_vault_root.join(subfolder).join(file_name);

    // Transformación por modo.
    let mode = promotion_mode(doc_type);
    let mut new_body = body.clone();
    let mut summarized = false;
    let mut new_status: Option<String> = fm_str(&fm, "status").map(str::to_string);
    if mode == "summarize" {
        new_body = summarize_session(&fm, &body);
        summarized = true;
        if doc_type == DocType::Session {
            new_status = Some("completed".to_string());
        }
    } else if mode == "review-required" {
        new_status = Some("draft".to_string());
    }

    // Fingerprint directo del cuerpo nuevo (sin normalización).
    use sha2::{Digest, Sha256};
    let fingerprint = {
        let digest = Sha256::digest(new_body.as_bytes());
        digest
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<String>()
    };

    let now_full = isoformat_full(args.clock.now());
    let new_fm = build_enterprise_frontmatter(FrontmatterCtx {
        fm: &fm,
        fingerprint: &fingerprint,
        org: args.org,
        actor: args.actor,
        reason: args.reason,
        new_status: new_status.as_deref(),
        promotion_mode: mode,
        now_full: &now_full,
    });

    if !args.dry_run {
        if let Some(parent) = target_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let payload = format!("---\n{}---\n\n{new_body}", pyyaml::dump_with(&new_fm, true));
        std::fs::write(&target_path, payload)?;
    }

    Ok(PromotionResult {
        source_path: args.source_path.to_path_buf(),
        target_path,
        doc_type: route.doc_type.as_str(),
        promotion_mode: mode.to_string(),
        summarized,
        fingerprint,
        requires_review: requires_review_before_publish(doc_type),
    })
}

/// `_build_enterprise_frontmatter`: orden fijo de claves + extras + audit.
struct FrontmatterCtx<'a> {
    fm: &'a serde_yaml::Value,
    fingerprint: &'a str,
    org: &'a EnterpriseOrgConfig,
    actor: &'a str,
    reason: Option<&'a str>,
    new_status: Option<&'a str>,
    promotion_mode: &'a str,
    now_full: &'a str,
}

#[allow(clippy::vec_init_then_push)]
fn build_enterprise_frontmatter(ctx: FrontmatterCtx<'_>) -> pyyaml::Yaml {
    let FrontmatterCtx {
        fm,
        fingerprint,
        org,
        actor,
        reason,
        new_status,
        promotion_mode,
        now_full,
    } = ctx;
    let empty = serde_yaml::Mapping::new();
    let mapping = match fm {
        serde_yaml::Value::Mapping(m) => m,
        _ => &empty,
    };

    let get_int = |key: &str| -> Option<i64> {
        mapping
            .get(serde_yaml::Value::String(key.into()))
            .and_then(|v| v.as_i64())
    };
    let get_str = |key: &str| -> Option<String> {
        mapping
            .get(serde_yaml::Value::String(key.into()))
            .and_then(|v| match v {
                serde_yaml::Value::String(s) => Some(s.clone()),
                other if !other.is_null() => serde_yaml::to_string(other)
                    .ok()
                    .map(|s| s.trim().to_string()),
                _ => None,
            })
    };
    let get_list = |key: &str| -> Vec<pyyaml::Yaml> {
        mapping
            .get(serde_yaml::Value::String(key.into()))
            .and_then(|v| v.as_sequence())
            .map(|seq| seq.iter().map(yaml_value_to_node).collect())
            .unwrap_or_default()
    };

    let mut out: Vec<(String, pyyaml::Yaml)> = Vec::new();
    out.push((
        "schema_version".into(),
        pyyaml::Yaml::Int(get_int("schema_version").unwrap_or(1)),
    ));
    out.push((
        "doc_type".into(),
        get_str("doc_type")
            .map(pyyaml::Yaml::Str)
            .unwrap_or(pyyaml::Yaml::Null),
    ));
    out.push((
        "title".into(),
        pyyaml::Yaml::Str(get_str("title").unwrap_or_else(|| "(untitled)".to_string())),
    ));
    out.push((
        "created_at".into(),
        pyyaml::Yaml::Str(get_str("created_at").unwrap_or_else(|| now_full.to_string())),
    ));
    out.push(("updated_at".into(), pyyaml::Yaml::Str(now_full.to_string())));
    out.push(("tags".into(), pyyaml::Yaml::Seq(get_list("tags"))));
    out.push((
        "status".into(),
        pyyaml::Yaml::Str(
            new_status
                .map(str::to_string)
                .or_else(|| get_str("status"))
                .unwrap_or_default(),
        ),
    ));
    out.push(("links".into(), pyyaml::Yaml::Seq(get_list("links"))));
    out.push(("vault_scope".into(), pyyaml::Yaml::Str("enterprise".into())));
    out.push((
        "fingerprint".into(),
        pyyaml::Yaml::Str(fingerprint.to_string()),
    ));
    out.push((
        "owner".into(),
        pyyaml::Yaml::Str(get_str("owner").unwrap_or_else(|| actor.to_string())),
    ));
    let team = get_str("team")
        .or_else(|| org.teams.first().map(|t| t.id.clone()))
        .unwrap_or_else(|| governance::ADMIN_TEAM.to_string());
    out.push(("team".into(), pyyaml::Yaml::Str(team)));
    out.push((
        "classification".into(),
        pyyaml::Yaml::Str(get_str("classification").unwrap_or_else(|| "internal".into())),
    ));

    // retention_days: override explícito int (incluye negativos) o default.
    let retention_explicit = mapping
        .get(serde_yaml::Value::String("retention_days".into()))
        .and_then(|v| v.as_i64());
    let retention_days = retention_explicit.unwrap_or_else(|| {
        org.retention_defaults
            .for_doc_type(get_str("doc_type").unwrap_or_default().as_str())
    });
    out.push(("retention_days".into(), pyyaml::Yaml::Int(retention_days)));

    // Extras tipo-específicos (no conocidos), en orden fuente.
    let known: &[&str] = &[
        "schema_version",
        "doc_type",
        "title",
        "created_at",
        "updated_at",
        "tags",
        "status",
        "links",
        "vault_scope",
        "fingerprint",
        "owner",
        "team",
        "classification",
        "retention_days",
        "audit_trail",
    ];
    for (k, v) in mapping {
        let Some(key_str) = k.as_str() else { continue };
        if known.contains(&key_str) {
            continue;
        }
        out.push((key_str.to_string(), yaml_value_to_node(v)));
    }

    // Audit trail preservado + evento promoted.
    let mut trail: Vec<pyyaml::Yaml> = mapping
        .get(serde_yaml::Value::String("audit_trail".into()))
        .and_then(|v| v.as_sequence())
        .map(|seq| seq.iter().map(yaml_value_to_node).collect())
        .unwrap_or_default();
    let mut event: Vec<(String, pyyaml::Yaml)> = Vec::new();
    event.push(("actor".into(), pyyaml::Yaml::Str(actor.to_string())));
    event.push(("action".into(), pyyaml::Yaml::Str("promoted".into())));
    event.push(("timestamp".into(), pyyaml::Yaml::Str(now_full.to_string())));
    event.push((
        "reason".into(),
        reason
            .map(|r| pyyaml::Yaml::Str(r.to_string()))
            .unwrap_or(pyyaml::Yaml::Null),
    ));
    event.push((
        "promotion_mode".into(),
        pyyaml::Yaml::Str(promotion_mode.to_string()),
    ));
    trail.push(pyyaml::Yaml::Map(event));
    out.push(("audit_trail".into(), pyyaml::Yaml::Seq(trail)));

    pyyaml::Yaml::Map(out)
}

const SESSION_INTRO: &str = "**Promoted session digest.** Full session lives at the source path.";

/// `_summarize_session`: conserva Key Decisions y Verified State por H2.
fn summarize_session(fm: &serde_yaml::Value, body: &str) -> String {
    let sections = split_sections(body);
    let mut parts: Vec<String> = vec![SESSION_INTRO.to_string()];
    for header in ["Key Decisions", "Verified State"] {
        if let Some(block) = sections.get(header) {
            parts.push(format!("\n## {header}\n\n{}", block.trim()));
        }
    }
    let title = fm_str(fm, "title").unwrap_or("Session");
    format!("# {title}\n\n{}\n", parts.join("\n").trim())
}

/// `_split_sections`: `{título H2 → cuerpo}` por líneas `^##\s+(.+?)\s*$`
/// (duplicados: gana el último).
fn split_sections(body: &str) -> BTreeMap<String, String> {
    // Anclas: (inicio_del_cuerpo_tras_header, inicio_de_la_línea, título).
    let mut anchors: Vec<(usize, usize, String)> = Vec::new();
    let mut offset = 0usize;
    for line in body.split_inclusive('\n') {
        let bare = line.strip_suffix('\n').unwrap_or(line);
        if let Some(rest) = bare.strip_prefix("##") {
            let title_raw = rest.trim_start_matches([' ', '\t']);
            let title = title_raw.trim();
            if title_raw.len() < rest.len() && !title.is_empty() {
                anchors.push((offset + line.len(), offset, title.to_string()));
            }
        }
        offset += line.len();
    }

    let mut out = BTreeMap::new();
    for (i, (body_start, _, title)) in anchors.iter().enumerate() {
        let end = anchors
            .get(i + 1)
            .map(|(_, next_line_start, _)| *next_line_start)
            .unwrap_or(body.len());
        out.insert(title.clone(), body[*body_start..end].trim().to_string());
    }
    out
}

pub fn mark_as_accepted(
    path: &Path,
    reviewer: &str,
    reason: &str,
    clock: &dyn Clock,
) -> Result<(), EnterpriseError> {
    if !path.exists() {
        return Err(validation(format!("note not found: {}", path.display())));
    }
    let (fm, _body) = read_note(path)?;
    let has_fm = matches!(fm, serde_yaml::Value::Mapping(ref m) if !m.is_empty());
    if !has_fm {
        return Err(validation(format!(
            "missing or invalid frontmatter: {}",
            path.display()
        )));
    }
    let current = fm_str(&fm, "status").unwrap_or("");
    if current != "draft" {
        return Err(validation(format!(
            "cannot accept {}: status is '{}', expected 'draft'",
            path.display(),
            current
        )));
    }
    // Status + audit append con el mismo orden de claves que Python.
    let updated_raw = upsert_with_audit(
        &std::fs::read_to_string(path)?,
        "accepted",
        reviewer,
        reason,
        clock,
        None,
    );
    std::fs::write(path, updated_raw)?;
    Ok(())
}

/// `mark_as_rejected`: draft → rejected; mueve a `rejected/` o borra.
/// Con `delete=true` el evento de auditoría NO persiste (destructivo).
pub fn mark_as_rejected(
    path: &Path,
    reviewer: &str,
    reason: &str,
    delete: bool,
    clock: &dyn Clock,
) -> Result<Option<PathBuf>, EnterpriseError> {
    if !path.exists() {
        return Err(validation(format!("note not found: {}", path.display())));
    }
    let (fm, _body) = read_note(path)?;
    let has_fm = matches!(fm, serde_yaml::Value::Mapping(ref m) if !m.is_empty());
    if !has_fm {
        return Err(validation(format!(
            "missing or invalid frontmatter: {}",
            path.display()
        )));
    }
    let current = fm_str(&fm, "status").unwrap_or("");
    if current != "draft" {
        return Err(validation(format!(
            "cannot reject {}: status is '{}', expected 'draft'",
            path.display(),
            current
        )));
    }

    if delete {
        std::fs::remove_file(path)?;
        return Ok(None);
    }

    let raw = std::fs::read_to_string(path)?;
    let rejected_dir = path.parent().unwrap_or(Path::new(".")).join("rejected");
    std::fs::create_dir_all(&rejected_dir)?;
    let target = rejected_dir.join(
        path.file_name()
            .ok_or_else(|| validation("path sin nombre"))?,
    );
    let updated_raw = upsert_with_audit(&raw, "rejected", reviewer, reason, clock, None);
    std::fs::write(&target, updated_raw)?;
    std::fs::remove_file(path)?;
    Ok(Some(target))
}

/// Reescritura con `status` nuevo y evento de auditoría appended
/// (orden de claves del evento: actor/action/timestamp/reason).
fn upsert_with_audit(
    raw: &str,
    status: &str,
    reviewer: &str,
    reason: &str,
    clock: &dyn Clock,
    extra: Option<()>,
) -> String {
    let _ = extra;
    let timestamp = isoformat_full(clock.now());
    // El evento se agrega al audit_trail existente dentro del YAML.
    let split = crate::frontmatter::split_frontmatter(raw);
    let mut fm_yaml = match &split {
        Some(s) => match &s.fm {
            serde_yaml::Value::Mapping(m) => m.clone(),
            _ => serde_yaml::Mapping::new(),
        },
        None => serde_yaml::Mapping::new(),
    };
    use serde_yaml::Value;
    fm_yaml.insert(Value::String("status".into()), Value::String(status.into()));
    let key = Value::String("audit_trail".into());
    let mut trail: Vec<Value> = match fm_yaml.get(&key) {
        Some(Value::Sequence(seq)) => seq.clone(),
        _ => Vec::new(),
    };
    let mut event = serde_yaml::Mapping::new();
    event.insert(
        Value::String("actor".into()),
        Value::String(reviewer.into()),
    );
    event.insert(
        Value::String("action".into()),
        Value::String(
            if status == "accepted" {
                "accepted"
            } else {
                "rejected"
            }
            .into(),
        ),
    );
    event.insert(Value::String("timestamp".into()), Value::String(timestamp));
    event.insert(
        Value::String("reason".into()),
        if reason.is_empty() {
            Value::Null
        } else {
            Value::String(reason.into())
        },
    );
    trail.push(Value::Mapping(event));
    fm_yaml.insert(key, Value::Sequence(trail));

    let node = yaml_value_to_node(&Value::Mapping(fm_yaml));
    let emitted = pyyaml::dump_with(&node, true);
    let body = match split {
        Some(s) => s.body,
        None => raw.to_string(),
    };
    format!("---\n{emitted}---\n\n{body}")
}

#[derive(Debug, Clone, PartialEq)]
pub struct PendingDraft {
    pub path: String,
    pub doc_type: Option<String>,
    pub title: Option<String>,
    pub owner: Option<String>,
    pub team: Option<String>,
    pub created_at: Option<String>,
}

/// `list_pending_drafts`: notas `status: draft` bajo vault_root, excluyendo
/// la carpeta `rejected/`, ordenadas por (doc_type, path).
pub fn list_pending_drafts(vault_root: &Path, doc_types: Option<&[String]>) -> Vec<PendingDraft> {
    let mut pending = Vec::new();
    if !vault_root.exists() {
        return pending;
    }
    let mut files = Vec::new();
    collect_markdown(vault_root, &mut files);
    files.sort();

    for md_path in files {
        // Salta cualquier componente "rejected".
        if md_path
            .components()
            .any(|c| c.as_os_str() == std::ffi::OsStr::new("rejected"))
        {
            continue;
        }
        let Ok(raw) = std::fs::read_to_string(&md_path) else {
            continue;
        };
        let Some(split) = split_frontmatter(&raw) else {
            continue;
        };
        let serde_yaml::Value::Mapping(map) = split.fm else {
            continue;
        };
        if map.is_empty() {
            continue;
        }
        let get_str = |key: &str| -> Option<String> {
            map.get(serde_yaml::Value::String(key.into()))
                .and_then(|v| v.as_str().map(str::to_string))
        };
        if get_str("status").as_deref() != Some("draft") {
            continue;
        }
        let doc_type = get_str("doc_type");
        if let (Some(filter), Some(dt)) = (doc_types, doc_type.as_deref()) {
            if !filter.iter().any(|f| f == dt) {
                continue;
            }
        }
        pending.push(PendingDraft {
            path: md_path
                .strip_prefix(vault_root)
                .unwrap_or(&md_path)
                .to_string_lossy()
                .replace('\\', "/"),
            doc_type,
            title: get_str("title"),
            owner: get_str("owner"),
            team: get_str("team"),
            created_at: get_str("created_at"),
        });
    }

    pending.sort_by(|a, b| {
        let ka = (a.doc_type.clone().unwrap_or_default(), a.path.clone());
        let kb = (b.doc_type.clone().unwrap_or_default(), b.path.clone());
        ka.cmp(&kb)
    });
    pending
}

fn collect_markdown(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            collect_markdown(&path, out);
        } else if path.extension().and_then(|e| e.to_str()) == Some("md") {
            out.push(path);
        }
    }
}
