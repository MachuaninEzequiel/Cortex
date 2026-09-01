//! Puerto de `cortex.enterprise.maintenance`: escaneo de retención y
//! archivo a `<vault>/_archived/` preservando estructura.

use std::path::{Path, PathBuf};

use chrono::{DateTime, Utc};

use crate::models::{EnterpriseOrgConfig, RetentionPolicy};

const ARCHIVE_FOLDER: &str = "_archived";

#[derive(Debug, Clone)]
pub struct RetentionViolation {
    pub path: PathBuf,
    pub doc_type: Option<String>,
    pub retention_days: i64,
    pub created_at: DateTime<Utc>,
    pub days_overdue: i64,
}

/// `scan_retention_violations`:
/// - precedencia: `defaults` explícito > org.retention_defaults > default;
/// - salta `_archived`, sin frontmatter, sin doc_type, sin fecha o <=0 días;
/// - frontera inclusiva `elapsed.days >= retention_days`;
/// - orden estable descendente por days_overdue.
pub fn scan_retention_violations(
    vault_root: &Path,
    org: Option<&EnterpriseOrgConfig>,
    defaults: Option<&RetentionPolicy>,
    now: DateTime<Utc>,
) -> Vec<RetentionViolation> {
    let policy_owned = RetentionPolicy::default();
    let policy: &RetentionPolicy = match defaults.or(org.map(|o| &o.retention_defaults)) {
        Some(p) => p,
        None => &policy_owned,
    };

    let mut violations = Vec::new();
    if !vault_root.exists() {
        return violations;
    }

    let mut files = Vec::new();
    collect_md(vault_root, &mut files);
    files.sort();

    for path in files {
        // Salta notas ya archivadas (cualquier componente `_archived`).
        if path
            .components()
            .any(|c| c.as_os_str().to_string_lossy() == ARCHIVE_FOLDER)
        {
            continue;
        }
        let fm = parse_frontmatter_lenient(&path);
        let fm = match fm {
            Some(fm) => fm,
            None => continue,
        };
        let get_str = |key: &str| -> Option<String> {
            fm.get(serde_yaml::Value::String(key.into()))
                .and_then(|v| v.as_str().map(str::to_string))
        };
        let doc_type = get_str("doc_type");
        let retention_days = resolve_retention(
            serde_yaml::Value::Mapping(fm.clone()),
            doc_type.as_deref(),
            policy,
        );
        if retention_days <= 0 {
            continue;
        }
        let Some(created_at) = parse_dt(get_str("created_at")) else {
            continue;
        };
        let elapsed_secs = (now - created_at).num_seconds();
        let elapsed_days = elapsed_secs.div_euclid(86_400);
        if elapsed_days >= retention_days {
            violations.push(RetentionViolation {
                path,
                doc_type,
                retention_days,
                created_at,
                days_overdue: elapsed_days - retention_days,
            });
        }
    }

    violations.sort_by_key(|v| std::cmp::Reverse(v.days_overdue));
    violations
}

/// `archive_violations`: mueve a `_archived/<rel>`; dry-run sólo planifica.
/// El target se agrega ANTES del move (quirk Python: falla de move igual
/// devuelve el path planificado).
pub fn archive_violations(
    violations: &[RetentionViolation],
    vault_root: &Path,
    dry_run: bool,
) -> Vec<PathBuf> {
    let archive_root = vault_root.join(ARCHIVE_FOLDER);
    let mut moved = Vec::new();
    for violation in violations {
        let Ok(rel) = violation.path.strip_prefix(vault_root) else {
            continue;
        };
        let target = archive_root.join(rel);
        moved.push(target.clone());
        if dry_run {
            continue;
        }
        if let Some(parent) = target.parent() {
            if std::fs::create_dir_all(parent).is_err() {
                continue;
            }
        }
        // shutil.move ⇒ si falla, warning-only y continúa.
        let _ = std::fs::rename(&violation.path, &target);
    }
    moved
}

// ── helpers internos ───────────────────────────────────────────────────────

fn _resolve_retention_python_order(
    fm: serde_yaml::Value,
    doc_type: Option<&str>,
    policy: &RetentionPolicy,
) -> i64 {
    resolve_retention(fm, doc_type, policy)
}

fn resolve_retention(
    fm: serde_yaml::Value,
    doc_type: Option<&str>,
    policy: &RetentionPolicy,
) -> i64 {
    let explicit = fm
        .get(serde_yaml::Value::String("retention_days".into()))
        .and_then(|v| match v {
            serde_yaml::Value::Number(n) => n.as_i64(),
            // Python isinstance(True, int) ⇒ bool cuenta como int.
            serde_yaml::Value::Bool(b) => Some(*b as i64),
            _ => None,
        });
    if let Some(days) = explicit.filter(|d| *d >= 0) {
        return days;
    }
    match doc_type {
        Some(dt) => policy.for_doc_type(dt),
        None => 0,
    }
}

/// `_parse_dt`: ISO string (Z→+00:00), naive ⇒ UTC, date-only ⇒ medianoche.
fn parse_dt(value: Option<String>) -> Option<DateTime<Utc>> {
    let value = value?;
    let normalized = value.replace('Z', "+00:00");
    if let Ok(dt) = DateTime::parse_from_rfc3339(&normalized) {
        return Some(dt.into());
    }
    for fmt in ["%Y-%m-%dT%H:%M:%S%.f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"] {
        if let Ok(dt) = chrono::NaiveDateTime::parse_from_str(&normalized, fmt) {
            return Some(dt.and_utc());
        }
        if fmt == "%Y-%m-%d" {
            if let Ok(d) = chrono::NaiveDate::parse_from_str(&normalized, fmt) {
                return Some(d.and_hms_opt(0, 0, 0)?.and_utc());
            }
        }
    }
    None
}

/// `parse_frontmatter_lenient`: dict crudo tolerante ({} ante cualquier fallo).
fn parse_frontmatter_lenient(path: &Path) -> Option<serde_yaml::Mapping> {
    let raw = std::fs::read_to_string(path).ok()?;
    let split = crate::frontmatter::split_frontmatter(&raw)?;
    match split.fm {
        serde_yaml::Value::Mapping(map) if !map.is_empty() => Some(map),
        _ => None,
    }
}

fn collect_md(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            collect_md(&path, out);
        } else if path.extension().and_then(|e| e.to_str()) == Some("md") {
            out.push(path);
        }
    }
}
