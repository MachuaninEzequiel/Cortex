//! Puerto de `cortex.enterprise.reporting`: reporte de memoria con doctor
//! ejecutado UNA vez vía backend inyectado.
//!
//! Seam enterprise→doctor (diseño aprobado P12B-3): enterprise define las
//! vistas neutrales `DoctorReportView`/`DoctorCheckView` y el trait
//! `DoctorBackend`. El default `UnavailableDoctorBackend` falla explícito;
//! en P12B-4 cortex-doctor implementará `NativeDoctorBackend` y el ciclo
//! queda doctor → enterprise, nunca inverso.

use std::path::PathBuf;

use serde::{Deserialize, Serialize};

use crate::config::{discover_enterprise_config_path, load_enterprise_config};
use crate::error::EnterpriseError;
use crate::knowledge_promotion::KnowledgePromotionService;
use crate::models::EnterpriseOrgConfig;
use cortex_workspace::WorkspaceLayout;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DoctorScope {
    Project,
    Enterprise,
}

/// Vistas neutrales (equivalen a DoctorCheck/DoctorReport de cortex.doctor).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DoctorCheckView {
    pub name: String,
    pub ok: bool,
    pub severity: String,
    pub detail: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DoctorReportView {
    pub project_root: PathBuf,
    pub checks: Vec<DoctorCheckView>,
    pub has_failures: bool,
    pub has_warnings: bool,
}

pub trait DoctorBackend: Send + Sync {
    fn run(
        &self,
        project_root: &std::path::Path,
        scope: DoctorScope,
    ) -> Result<DoctorReportView, EnterpriseError>;
}

/// Backend por defecto hasta P12B-4: fallo explícito contractual.
pub struct UnavailableDoctorBackend;

impl DoctorBackend for UnavailableDoctorBackend {
    fn run(
        &self,
        _project_root: &std::path::Path,
        _scope: DoctorScope,
    ) -> Result<DoctorReportView, EnterpriseError> {
        Err(EnterpriseError::BackendUnavailable(
            "doctor backend unavailable until P12B-4",
        ))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ReportingScope {
    #[serde(rename = "local")]
    Local,
    #[serde(rename = "enterprise")]
    Enterprise,
    #[serde(rename = "all")]
    All,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PromotionEventSummary {
    pub origin_id: String,
    pub status: String,
    pub actor: Option<String>,
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PromotionReport {
    pub enabled: bool,
    pub require_review: bool,
    pub records_path: Option<String>,
    pub candidates_discovered: usize,
    pub candidates_ready_to_promote: usize,
    pub latest_events: Vec<PromotionEventSummary>,
    pub warnings: Vec<String>,
}

impl Default for PromotionReport {
    fn default() -> Self {
        Self {
            enabled: false,
            require_review: true,
            records_path: None,
            candidates_discovered: 0,
            candidates_ready_to_promote: 0,
            latest_events: vec![],
            warnings: vec![],
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MemorySourceReport {
    pub scope: ReportingScope,
    pub vault_path: Option<String>,
    pub markdown_files: usize,
    pub validation_errors: usize,
    pub validation_warnings: usize,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MemoryReportPayload {
    pub generated_at: String,
    pub project_root: String,
    pub enterprise_enabled: bool,
    pub sources: Vec<MemorySourceReport>,
    pub promotion: PromotionReport,
    pub doctor: serde_json::Value,
}

pub struct EnterpriseReportingService {
    project_root: PathBuf,
    layout: WorkspaceLayout,
    doctor: Box<dyn DoctorBackend>,
    clock: std::sync::Arc<dyn crate::clock::Clock>,
}

impl EnterpriseReportingService {
    /// Constructor por defecto: layout discovery + backend no disponible.
    pub fn from_project_root(
        project_root: &std::path::Path,
        layout: Option<WorkspaceLayout>,
    ) -> Result<Self, EnterpriseError> {
        let root = crate::review_knowledge::python_resolve(project_root);
        let layout = layout.unwrap_or_else(|| WorkspaceLayout::discover(&root));
        Ok(Self {
            project_root: root,
            layout,
            doctor: Box::new(UnavailableDoctorBackend),
            clock: std::sync::Arc::new(crate::clock::SystemClock),
        })
    }

    /// Inyecta el backend doctor (builder).
    pub fn with_doctor_backend(mut self, backend: impl DoctorBackend + 'static) -> Self {
        self.doctor = Box::new(backend);
        self
    }

    /// Inyecta el reloj para `generated_at` determinista (tests/gate).
    pub fn with_clock(mut self, clock: std::sync::Arc<dyn crate::clock::Clock>) -> Self {
        self.clock = clock;
        self
    }

    /// `build_memory_report`: doctor UNA vez; local→project,
    /// enterprise/all→enterprise. Las fuentes consumen el reporte por
    /// parámetro (igual que Python pasa `doctor` a `_local_source`).
    pub fn build_memory_report(
        &self,
        scope: ReportingScope,
    ) -> Result<MemoryReportPayload, EnterpriseError> {
        let doctor_scope = match scope {
            ReportingScope::Local => DoctorScope::Project,
            ReportingScope::Enterprise | ReportingScope::All => DoctorScope::Enterprise,
        };
        let doctor_report = self.doctor.run(&self.project_root, doctor_scope)?;
        let doctor_payload = doctor_to_payload(&doctor_report);

        let mut payload = MemoryReportPayload {
            generated_at: crate::clock::isoformat_seconds(self.clock.now()),
            project_root: self.project_root.display().to_string(),
            enterprise_enabled: discover_enterprise_config_path(
                &self.project_root,
                Some(&self.layout),
            )
            .is_some(),
            sources: Vec::new(),
            promotion: PromotionReport::default(),
            doctor: doctor_payload,
        };

        if matches!(scope, ReportingScope::Local | ReportingScope::All) {
            payload.sources.push(self.local_source(&doctor_report)?);
        }
        if matches!(scope, ReportingScope::Enterprise | ReportingScope::All) {
            if let Some(enterprise) = self.enterprise_source(&doctor_report)? {
                payload.sources.push(enterprise);
            }
            payload.promotion = self.promotion_report()?;
        }

        Ok(payload)
    }

    fn local_source(
        &self,
        doctor: &DoctorReportView,
    ) -> Result<MemorySourceReport, EnterpriseError> {
        let vault_path = self.layout.vault_path();
        let md_count = count_markdown_files(Some(&vault_path));
        let errors = extract_check_count(&doctor.checks, "vault_validation_errors");
        let warnings = extract_check_count(&doctor.checks, "vault_validation_warnings");
        let mut notes = Vec::new();
        if !vault_path.exists() {
            notes.push("vault directory missing".to_string());
        }
        Ok(MemorySourceReport {
            scope: ReportingScope::Local,
            vault_path: Some(vault_path.display().to_string()),
            markdown_files: md_count,
            validation_errors: errors,
            validation_warnings: warnings,
            notes,
        })
    }

    fn enterprise_source(
        &self,
        doctor: &DoctorReportView,
    ) -> Result<Option<MemorySourceReport>, EnterpriseError> {
        let Some(_cfg_path) =
            discover_enterprise_config_path(&self.project_root, Some(&self.layout))
        else {
            return Ok(None);
        };
        let cfg: EnterpriseOrgConfig =
            load_enterprise_config(&self.project_root, true, None, Some(&self.layout))?
                .ok_or_else(|| EnterpriseError::NotFound("org.yaml".to_string()))?;
        let workspace_root = self.layout.workspace_root.clone();
        let enterprise_vault =
            cfg.resolve_enterprise_vault_path(&self.project_root, Some(&workspace_root));
        let md_count = count_markdown_files(enterprise_vault.as_deref());
        let errors = extract_check_count(&doctor.checks, "enterprise_vault_validation_errors");
        let warnings = extract_check_count(&doctor.checks, "enterprise_vault_validation_warnings");
        let mut notes = Vec::new();
        if enterprise_vault.is_none() {
            notes.push(
                "enterprise vault disabled (memory.enterprise_semantic_enabled=false)".to_string(),
            );
        } else if !enterprise_vault.as_deref().is_some_and(|p| p.exists()) {
            notes.push("enterprise vault directory missing".to_string());
        }
        Ok(Some(MemorySourceReport {
            scope: ReportingScope::Enterprise,
            vault_path: enterprise_vault.map(|p| p.display().to_string()),
            markdown_files: md_count,
            validation_errors: errors,
            validation_warnings: warnings,
            notes,
        }))
    }

    fn promotion_report(&self) -> Result<PromotionReport, EnterpriseError> {
        let Some(_) = discover_enterprise_config_path(&self.project_root, Some(&self.layout))
        else {
            return Ok(PromotionReport {
                enabled: false,
                warnings: vec!["enterprise config missing (.cortex/org.yaml)".to_string()],
                ..PromotionReport::default()
            });
        };
        let cfg: EnterpriseOrgConfig =
            load_enterprise_config(&self.project_root, true, None, Some(&self.layout))?
                .ok_or_else(|| EnterpriseError::NotFound("org.yaml".to_string()))?;
        if !cfg.promotion.enabled {
            return Ok(PromotionReport {
                enabled: false,
                require_review: cfg.promotion.require_review,
                ..PromotionReport::default()
            });
        }

        let mut svc = match KnowledgePromotionService::from_project_root(
            &self.project_root,
            Some(self.layout.clone()),
            self.clock.clone(),
        ) {
            Ok(svc) => svc,
            Err(exc) => {
                return Ok(PromotionReport {
                    enabled: true,
                    require_review: cfg.promotion.require_review,
                    warnings: vec![format!("promotion reporting unavailable: {exc}")],
                    ..PromotionReport::default()
                });
            }
        };

        let candidates = svc.discover_candidates()?;
        let ready = svc.plan_promotion()?;
        let latest = svc.repo.load_latest_by_origin_id()?;
        let latest_events = summarize_latest_events(&latest, 10);
        Ok(PromotionReport {
            enabled: true,
            require_review: svc.require_review,
            records_path: Some(svc.paths.records_path.display().to_string()),
            candidates_discovered: candidates.len(),
            candidates_ready_to_promote: ready.len(),
            latest_events,
            warnings: vec![],
        })
    }
}

/// `_doctor_to_payload`.
fn doctor_to_payload(report: &DoctorReportView) -> serde_json::Value {
    serde_json::json!({
        "project_root": report.project_root.display().to_string(),
        "checks": report.checks.iter().map(|c| serde_json::json!({
            "name": c.name,
            "ok": c.ok,
            "severity": c.severity,
            "detail": c.detail,
        })).collect::<Vec<_>>(),
        "has_failures": report.has_failures,
        "has_warnings": report.has_warnings,
    })
}

/// `_extract_check_count`: parsea "<n> error(s)..." del detail; 0 si ok.
fn extract_check_count(checks: &[DoctorCheckView], name: &str) -> usize {
    for check in checks {
        if check.name != name {
            continue;
        }
        let first = check.detail.trim().split(' ').next().unwrap_or("");
        return match first.parse::<usize>() {
            Ok(n) => n,
            Err(_) => {
                if check.ok {
                    0
                } else {
                    1
                }
            }
        };
    }
    0
}

fn count_markdown_files(root: Option<&std::path::Path>) -> usize {
    let Some(root) = root else { return 0 };
    if !root.exists() {
        return 0;
    }
    let mut files = Vec::new();
    collect_md(root, &mut files);
    files.len()
}

/// `_summarize_latest_events`: sort desc por (updated_at, origin_id), top N.
fn summarize_latest_events(
    latest_by_origin: &[(String, crate::promotion_models::PromotionRecord)],
    limit: usize,
) -> Vec<PromotionEventSummary> {
    let mut items: Vec<PromotionEventSummary> = latest_by_origin
        .iter()
        .map(|(origin_id, rec)| {
            let last = rec.events.last();
            PromotionEventSummary {
                origin_id: origin_id.clone(),
                status: rec.status.as_str().to_string(),
                actor: last.and_then(|e| e.actor.clone()),
                updated_at: last.map(|e| e.at.clone()),
            }
        })
        .collect();
    items.sort_by(|a, b| {
        let ka = (
            a.updated_at.clone().unwrap_or_default(),
            a.origin_id.clone(),
        );
        let kb = (
            b.updated_at.clone().unwrap_or_default(),
            b.origin_id.clone(),
        );
        kb.cmp(&ka)
    });
    items.truncate(limit);
    items
}

fn collect_md(dir: &std::path::Path, out: &mut Vec<PathBuf>) {
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
