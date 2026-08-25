//! Puerto de `cortex.enterprise.knowledge_promotion`: descubrimiento de
//! candidatos, review con records JSONL append-only y promoción idempotente.
//!
//! Paridad clave:
//! - `discover_candidates` recarga org.yaml del disco en cada llamada
//!   (igual que Python; ver ruling en ledger).
//! - Los candidatos se recorren con `sorted(rglob("*.md"))` y los promovidos
//!   con fingerprint vigente NO reaparecen.
//! - `review`/`apply` reproducen mensajes ValueError textuales.

use std::collections::HashSet;
use std::fs::OpenOptions;
use std::io::Write as IoWrite;
use std::path::PathBuf;
use std::sync::Arc;

use cortex_app::doc_validator::{DocValidator, Severity};
use cortex_workspace::{runtime_context::slugify, WorkspaceLayout};

use crate::clock::{isoformat_seconds, Clock};
use crate::config::load_enterprise_config;
use crate::error::EnterpriseError;
use crate::frontmatter::{
    doc_type_from_rel_path, normalized_markdown_fingerprint, upsert_frontmatter,
};
use crate::governance;
use crate::models::EnterpriseOrgConfig;
use crate::promotion_models::{
    PromotionCandidate, PromotionDecision, PromotionDecisionType, PromotionEventKind,
    PromotionIssue, PromotionRecord, PromotionRecordEvent, PromotionStatus,
};

#[derive(Debug, Clone)]
pub struct PromotionPaths {
    pub project_root: PathBuf,
    pub local_vault: PathBuf,
    pub enterprise_vault: PathBuf,
    pub records_path: PathBuf,
}

/// Repositorio append-only de records (`records.jsonl`).
pub struct PromotionRepository {
    pub records_path: PathBuf,
}

impl PromotionRepository {
    pub fn new(records_path: PathBuf) -> Self {
        if let Some(parent) = records_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        Self { records_path }
    }

    /// `iter_records`: líneas inválidas (JSON roto o status fuera del
    /// Literal) se descartan silenciosamente, igual que Python.
    pub fn iter_records(&self) -> Result<Vec<PromotionRecord>, EnterpriseError> {
        if !self.records_path.exists() {
            return Ok(Vec::new());
        }
        let raw = std::fs::read_to_string(&self.records_path)?;
        let mut out = Vec::new();
        for line in raw.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            match serde_json::from_str::<PromotionRecord>(line) {
                Ok(record) => out.push(record),
                Err(_) => continue,
            }
        }
        Ok(out)
    }

    /// Último record por origin_id (orden de primera aparición preservado).
    pub fn load_latest_by_origin_id(
        &self,
    ) -> Result<Vec<(String, PromotionRecord)>, EnterpriseError> {
        let mut keys: Vec<String> = Vec::new();
        let mut latest: Vec<PromotionRecord> = Vec::new();
        for record in self.iter_records()? {
            match keys.iter().position(|k| *k == record.origin_id) {
                Some(i) => latest[i] = record,
                None => {
                    keys.push(record.origin_id.clone());
                    latest.push(record);
                }
            }
        }
        Ok(keys.into_iter().zip(latest).collect())
    }

    /// Append de una línea JSON + `\n`.
    pub fn append(&self, record: &PromotionRecord) -> Result<(), EnterpriseError> {
        if let Some(parent) = self.records_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let line = record.to_json_line()?;
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.records_path)?;
        file.write_all(line.as_bytes())?;
        file.write_all(b"\n")?;
        Ok(())
    }
}

/// Motor de reglas de promovibilidad por familia de documento.
pub struct PromotionRulesEngine {
    pub allowed_doc_types: HashSet<String>,
}

impl PromotionRulesEngine {
    pub fn new(allowed_doc_types: HashSet<String>) -> Self {
        Self { allowed_doc_types }
    }

    /// Devuelve `(promotable, reason)` con los textos exactos de Python.
    pub fn is_promotable(&self, rel_path: &str) -> (bool, String) {
        if rel_path.starts_with(".cortex/") {
            return (false, "internal cortex metadata".to_string());
        }
        let Some(doc_type) = doc_type_from_rel_path(rel_path) else {
            return (
                false,
                "unknown doc family (not under a recognized vault folder)".to_string(),
            );
        };
        if doc_type == "session" && !self.allowed_doc_types.contains("session") {
            return (
                false,
                "sessions excluded by default (not enabled in org promotion.allowed_doc_types)"
                    .to_string(),
            );
        }
        if !self.allowed_doc_types.contains(doc_type) {
            return (
                false,
                format!("doc_type '{doc_type}' not allowed by org promotion.allowed_doc_types"),
            );
        }
        (true, "allowed".to_string())
    }
}

/// Servicio de promoción legacy (copy + frontmatter injection).
pub struct KnowledgePromotionService {
    pub paths: PromotionPaths,
    pub org_slug: String,
    pub require_review: bool,
    pub repo: PromotionRepository,
    layout: Option<WorkspaceLayout>,
    validator: DocValidator,
    clock: Arc<dyn Clock>,
}

impl KnowledgePromotionService {
    /// Construcción directa (tests / wiring explícito). La config provista
    /// es la semilla; `discover_candidates` sigue recargando del disco.
    pub fn new(paths: PromotionPaths, config: EnterpriseOrgConfig, clock: Arc<dyn Clock>) -> Self {
        let _ = config; // la config vigente siempre se recarga del disco
        let repo = PromotionRepository::new(paths.records_path.clone());
        let validator = DocValidator::new(paths.local_vault.clone());
        Self {
            org_slug: slugify(
                &paths
                    .project_root
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy(),
                "project",
            ),
            paths,
            require_review: true,
            repo,
            layout: None,
            validator,
            clock,
        }
    }

    pub fn with_clock(mut self, clock: Arc<dyn Clock>) -> Self {
        self.clock = clock;
        self
    }

    /// `from_project_root`: layout discovery + carga required + resolución
    /// de vault enterprise. Error exacto si está deshabilitado.
    pub fn from_project_root(
        project_root: &std::path::Path,
        workspace_layout: Option<WorkspaceLayout>,
        clock: Arc<dyn Clock>,
    ) -> Result<Self, EnterpriseError> {
        let layout = workspace_layout.unwrap_or_else(|| WorkspaceLayout::discover(project_root));
        let config = load_enterprise_config(&layout.repo_root, true, None, Some(&layout))?
            .ok_or_else(|| {
                EnterpriseError::NotFound(
                    "Enterprise config (.cortex/org.yaml) is required for promotion.".to_string(),
                )
            })?;
        let enterprise_vault = config
            .resolve_enterprise_vault_path(&layout.repo_root, Some(&layout.workspace_root))
            .ok_or_else(|| {
                EnterpriseError::Validation(
                    "Enterprise vault is disabled (memory.enterprise_semantic_enabled=false)"
                        .to_string(),
                )
            })?;
        let paths = PromotionPaths {
            project_root: layout.repo_root.clone(),
            local_vault: layout.vault_path(),
            enterprise_vault,
            records_path: layout.promotion_records_path(),
        };
        let repo = PromotionRepository::new(paths.records_path.clone());
        let validator = DocValidator::new(paths.local_vault.clone());
        Ok(Self {
            org_slug: config.organization.slug.clone(),
            paths,
            require_review: config.promotion.require_review,
            repo,
            layout: Some(layout),
            validator,
            clock,
        })
    }

    fn project_slug(&self) -> String {
        slugify(
            &self
                .paths
                .project_root
                .file_name()
                .unwrap_or_default()
                .to_string_lossy(),
            "project",
        )
    }

    fn origin_id(&self, local_rel_path: &str) -> String {
        format!("{}:{local_rel_path}", self.project_slug())
    }

    fn dest_rel_path(&self, local_rel_path: &str) -> String {
        let (family, rest) = match local_rel_path.split_once('/') {
            Some((f, r)) => (f.to_string(), Some(r.to_string())),
            None => (local_rel_path.to_string(), None),
        };
        let name = local_rel_path.rsplit('/').next().unwrap_or(local_rel_path);
        match rest {
            Some(rest) if !rest.is_empty() => format!("{family}/{}/{rest}", self.project_slug()),
            _ => format!("{family}/{}/{name}", self.project_slug()),
        }
    }

    /// Config vigente recargada del disco (contrato Python).
    fn current_config(&self) -> Result<EnterpriseOrgConfig, EnterpriseError> {
        load_enterprise_config(&self.paths.project_root, true, None, self.layout.as_ref())?
            .ok_or_else(|| {
                EnterpriseError::NotFound(
                    "Enterprise config (.cortex/org.yaml) is required for promotion.".to_string(),
                )
            })
    }

    pub fn discover_candidates(&mut self) -> Result<Vec<PromotionCandidate>, EnterpriseError> {
        let config = self.current_config()?;
        let allowed: HashSet<String> = config
            .promotion
            .allowed_doc_types
            .iter()
            .map(|t| t.as_str().to_string())
            .collect();
        let rules = PromotionRulesEngine::new(allowed);
        let latest = self.repo.load_latest_by_origin_id()?;
        let now = isoformat_seconds(self.clock.now());

        if !self.paths.local_vault.exists() {
            return Ok(Vec::new());
        }

        let mut files: Vec<PathBuf> = Vec::new();
        collect_md(&self.paths.local_vault, &mut files)?;
        files.sort();

        let mut candidates = Vec::new();
        for path in files {
            let rel = path
                .strip_prefix(&self.paths.local_vault)
                .expect("prefijo del vault")
                .to_string_lossy()
                .replace('\\', "/");
            let (ok, _reason) = rules.is_promotable(&rel);
            if !ok {
                continue;
            }

            let raw = std::fs::read_to_string(&path)?;
            let fingerprint = normalized_markdown_fingerprint(&raw);
            let origin_id = self.origin_id(&rel);
            let dest_rel = self.dest_rel_path(&rel);
            let doc_type = doc_type_from_rel_path(&rel)
                .unwrap_or("unknown")
                .to_string();

            let mut issues = Vec::new();
            for issue in self.validator.validate_file(&path).issues {
                issues.push(PromotionIssue {
                    file: issue.file,
                    field: issue.field,
                    message: issue.message,
                    severity: match issue.severity {
                        Severity::Error => "error".to_string(),
                        Severity::Warning => "warning".to_string(),
                        Severity::Info => "info".to_string(),
                    },
                });
            }

            // Promovido con fingerprint vigente ⇒ no reaparece.
            if let Some((_, existing)) = latest.iter().find(|(k, _)| *k == origin_id) {
                if existing.status == "promoted" && existing.fingerprint == fingerprint {
                    continue;
                }
            }

            let mut metadata = std::collections::BTreeMap::new();
            metadata.insert(
                "discovered_at".to_string(),
                serde_json::Value::String(now.clone()),
            );
            candidates.push(PromotionCandidate {
                origin_id,
                doc_type,
                local_rel_path: rel,
                local_abs_path: path.display().to_string(),
                dest_rel_path: dest_rel,
                fingerprint,
                status: "candidate".to_string(),
                issues,
                metadata,
            });
        }
        Ok(candidates)
    }

    pub fn review(
        &mut self,
        selector: &str,
        approve: bool,
        actor: &str,
        reason: Option<&str>,
    ) -> Result<PromotionRecord, EnterpriseError> {
        let candidates = self.discover_candidates()?;
        let matched = candidates
            .iter()
            .find(|c| c.origin_id == selector || c.local_rel_path == selector)
            .cloned();
        let Some(matched) = matched else {
            return Err(EnterpriseError::Validation(format!(
                "No candidate found for selector: {selector}"
            )));
        };

        if matched.issues.iter().any(|i| i.severity == "error") {
            return Err(EnterpriseError::Validation(
                "Cannot review a document with validation errors.".to_string(),
            ));
        }

        let now = isoformat_seconds(self.clock.now());
        let decision = PromotionDecision {
            decision: if approve {
                PromotionDecisionType::Approve
            } else {
                PromotionDecisionType::Reject
            },
            actor: actor.to_string(),
            decided_at: now.clone(),
            reason: reason.map(str::to_string),
        };
        let status = if approve {
            PromotionStatus::Reviewed
        } else {
            PromotionStatus::Rejected
        };
        let event_status = if approve {
            PromotionEventKind::ReviewedEvent
        } else {
            PromotionEventKind::RejectedEvent
        };

        let mut candidate_payload = std::collections::BTreeMap::new();
        candidate_payload.insert(
            "fingerprint".to_string(),
            serde_json::Value::String(matched.fingerprint.clone()),
        );
        let mut review_payload = std::collections::BTreeMap::new();
        if let Some(r) = reason {
            review_payload.insert(
                "reason".to_string(),
                serde_json::Value::String(r.to_string()),
            );
        }

        let record = PromotionRecord {
            origin_id: matched.origin_id.clone(),
            local_rel_path: matched.local_rel_path.clone(),
            doc_type: matched.doc_type.clone(),
            dest_rel_path: matched.dest_rel_path.clone(),
            fingerprint: matched.fingerprint.clone(),
            status,
            created_at: now.clone(),
            updated_at: now.clone(),
            decision: Some(decision),
            events: vec![
                PromotionRecordEvent {
                    event: PromotionEventKind::Candidate,
                    at: now.clone(),
                    actor: None,
                    payload: candidate_payload,
                },
                PromotionRecordEvent {
                    event: event_status,
                    at: now,
                    actor: Some(actor.to_string()),
                    payload: review_payload,
                },
            ],
        };
        self.repo.append(&record)?;
        Ok(record)
    }

    pub fn plan_promotion(&mut self) -> Result<Vec<PromotionCandidate>, EnterpriseError> {
        let candidates = self.discover_candidates()?;
        let latest = self.repo.load_latest_by_origin_id()?;
        let mut promotable = Vec::new();

        for candidate in candidates {
            let record = latest
                .iter()
                .find(|(k, _)| *k == candidate.origin_id)
                .map(|(_, r)| r);
            if self.require_review {
                let approved = record
                    .map(|r| r.status == "reviewed" && r.fingerprint == candidate.fingerprint)
                    .unwrap_or(false);
                if !approved {
                    continue;
                }
            }
            if candidate.issues.iter().any(|i| i.severity == "error") {
                continue;
            }
            promotable.push(candidate);
        }
        Ok(promotable)
    }

    pub fn apply_promotion(
        &mut self,
        candidates: &[PromotionCandidate],
        actor: &str,
    ) -> Result<Vec<PromotionRecord>, EnterpriseError> {
        let latest = self.repo.load_latest_by_origin_id()?;
        let mut written = Vec::new();

        for candidate in candidates {
            let existing = latest
                .iter()
                .find(|(k, _)| *k == candidate.origin_id)
                .map(|(_, r)| r);
            if let Some(existing) = existing {
                if existing.status == "promoted" && existing.fingerprint == candidate.fingerprint {
                    continue;
                }
            }

            let src = self.paths.local_vault.join(&candidate.local_rel_path);
            let dest = self.paths.enterprise_vault.join(&candidate.dest_rel_path);
            if let Some(parent) = dest.parent() {
                std::fs::create_dir_all(parent)?;
            }

            let raw = std::fs::read_to_string(&src)?;
            let promoted_raw = upsert_frontmatter(
                &raw,
                vec![
                    (
                        "promotion_status".into(),
                        Some(serde_yaml::Value::String("promoted".into())),
                    ),
                    (
                        "promotion_origin_id".into(),
                        Some(serde_yaml::Value::String(candidate.origin_id.clone())),
                    ),
                    (
                        "promotion_origin_path".into(),
                        Some(serde_yaml::Value::String(candidate.local_rel_path.clone())),
                    ),
                    (
                        "promotion_origin_project".into(),
                        Some(serde_yaml::Value::String(self.project_slug())),
                    ),
                    (
                        "promotion_fingerprint".into(),
                        Some(serde_yaml::Value::String(candidate.fingerprint.clone())),
                    ),
                    (
                        "promotion_promoted_at".into(),
                        Some(serde_yaml::Value::String(isoformat_seconds(
                            self.clock.now(),
                        ))),
                    ),
                ],
            );
            std::fs::write(&dest, promoted_raw)?;

            let now = isoformat_seconds(self.clock.now());
            let mut candidate_payload = std::collections::BTreeMap::new();
            candidate_payload.insert(
                "fingerprint".to_string(),
                serde_json::Value::String(candidate.fingerprint.clone()),
            );

            let record = PromotionRecord {
                origin_id: candidate.origin_id.clone(),
                local_rel_path: candidate.local_rel_path.clone(),
                doc_type: candidate.doc_type.clone(),
                dest_rel_path: candidate.dest_rel_path.clone(),
                fingerprint: candidate.fingerprint.clone(),
                status: PromotionStatus::Promoted,
                created_at: now.clone(),
                updated_at: now,
                decision: existing.and_then(|e| e.decision.clone()),
                events: vec![
                    PromotionRecordEvent {
                        event: PromotionEventKind::Candidate,
                        at: isoformat_seconds(self.clock.now()),
                        actor: None,
                        payload: candidate_payload,
                    },
                    PromotionRecordEvent {
                        event: PromotionEventKind::Promoted,
                        at: isoformat_seconds(self.clock.now()),
                        actor: Some(actor.to_string()),
                        payload: Default::default(),
                    },
                ],
            };
            self.repo.append(&record)?;
            written.push(record);
        }
        Ok(written)
    }

    /// Governance helpers re-exportados para callers del CLI (P12B-8).
    pub fn assert_can_promote(&self, actor: &str) -> Result<String, EnterpriseError> {
        let config = self.current_config()?;
        governance::assert_can_promote(actor, &config)
    }
}

/// rglob("*.md") recursivo ordenable.
fn collect_md(dir: &std::path::Path, out: &mut Vec<PathBuf>) -> Result<(), EnterpriseError> {
    let entries = std::fs::read_dir(dir)?;
    for entry in entries {
        let path = entry?.path();
        if path.is_dir() {
            collect_md(&path, out)?;
        } else if path.extension().and_then(|e| e.to_str()) == Some("md") {
            out.push(path);
        }
    }
    Ok(())
}
