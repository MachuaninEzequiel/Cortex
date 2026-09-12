//! Memoria Organizacional en Cortex Brain, cableada a `cortex-enterprise`.
//!
//! El panel de Brain es un adaptador UI sobre `KnowledgePromotionService`:
//! descubre candidatos del vault local, revisa y promulga al vault
//! enterprise, y persiste records append-only tipados (`PromotionRecord`).

use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use cortex_enterprise::clock::SystemClock;
use cortex_enterprise::frontmatter::doc_type_from_rel_path;
use cortex_enterprise::knowledge_promotion::KnowledgePromotionService;
use cortex_enterprise::promotion_models::{PromotionCandidate, PromotionRecord, PromotionStatus};
use cortex_workspace::WorkspaceLayout;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrgKnowledgeItem {
    pub origin_id: String,
    pub rel_path: String,
    pub doc_type: String,
    pub title: String,
    pub status: String,
    pub priority: String,
    pub issues: Vec<String>,
    pub reviewer: Option<String>,
    pub reason: Option<String>,
    pub updated_at: String,
    pub is_promoted: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrgMemoryPayload {
    pub enterprise_vault_path: String,
    pub total_promoted: usize,
    pub total_candidates: usize,
    pub items: Vec<OrgKnowledgeItem>,
}

fn open_service(project_root: &Path) -> Result<KnowledgePromotionService, String> {
    let mut svc =
        KnowledgePromotionService::from_project_root(project_root, None, Arc::new(SystemClock))
            .map_err(|e| e.to_string())?;
    let local = resolve_local_vault(project_root);
    if local.exists() && local != svc.paths.local_vault {
        svc.paths.local_vault = local;
    }
    Ok(svc)
}

fn resolve_local_vault(project_root: &Path) -> PathBuf {
    let p1 = project_root.join("vault");
    if p1.exists() {
        return p1;
    }
    let p2 = project_root.join(".cortex").join("vault");
    if p2.exists() {
        return p2;
    }
    WorkspaceLayout::discover(project_root).vault_path()
}

fn priority_for(doc_type: &str) -> &'static str {
    match doc_type {
        "spec" | "decision" | "adr" => "high",
        "runbook" | "hu" | "rfc" | "incident" => "medium",
        _ => "low",
    }
}

fn extract_title(path: &Path) -> String {
    let content = match fs::read_to_string(path) {
        Ok(c) => c,
        Err(_) => return String::new(),
    };
    if content.starts_with("---") {
        if let Some(end_idx) = content[3..].find("---") {
            let fm = &content[3..3 + end_idx];
            for line in fm.lines() {
                if let Some(t) = line.trim().strip_prefix("title:") {
                    let title = t.trim().trim_matches('"').trim_matches('\'').to_string();
                    if !title.is_empty() {
                        return title;
                    }
                }
            }
        }
    }
    for line in content.lines() {
        if let Some(h1) = line.trim().strip_prefix("# ") {
            return h1.trim().to_string();
        }
    }
    path.file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_default()
}

fn item_from_candidate(
    candidate: &PromotionCandidate,
    record: Option<&PromotionRecord>,
    local_vault: &Path,
) -> OrgKnowledgeItem {
    let status = record
        .map(|r| r.status.as_str().to_string())
        .unwrap_or_else(|| candidate.status.clone());
    let is_promoted = status == "promoted";
    let title = extract_title(&local_vault.join(&candidate.local_rel_path));
    OrgKnowledgeItem {
        origin_id: candidate.origin_id.clone(),
        rel_path: candidate.local_rel_path.clone(),
        doc_type: candidate.doc_type.clone(),
        title: if title.is_empty() {
            candidate.local_rel_path.clone()
        } else {
            title
        },
        status,
        priority: priority_for(&candidate.doc_type).to_string(),
        issues: candidate.issues.iter().map(|i| i.message.clone()).collect(),
        reviewer: record.and_then(|r| r.decision.as_ref().map(|d| d.actor.clone())),
        reason: record.and_then(|r| r.decision.as_ref().and_then(|d| d.reason.clone())),
        updated_at: record
            .map(|r| r.updated_at.clone())
            .unwrap_or_else(|| chrono::Utc::now().to_rfc3339()),
        is_promoted,
    }
}

fn item_from_record(record: &PromotionRecord, local_vault: &Path) -> OrgKnowledgeItem {
    let is_promoted = record.status == PromotionStatus::Promoted;
    let title = extract_title(&local_vault.join(&record.local_rel_path));
    OrgKnowledgeItem {
        origin_id: record.origin_id.clone(),
        rel_path: record.local_rel_path.clone(),
        doc_type: record.doc_type.clone(),
        title: if title.is_empty() {
            record.local_rel_path.clone()
        } else {
            title
        },
        status: record.status.as_str().to_string(),
        priority: priority_for(&record.doc_type).to_string(),
        issues: Vec::new(),
        reviewer: record.decision.as_ref().map(|d| d.actor.clone()),
        reason: record.decision.as_ref().and_then(|d| d.reason.clone()),
        updated_at: record.updated_at.clone(),
        is_promoted,
    }
}

fn payload_from_items(
    enterprise_vault_path: String,
    items: Vec<OrgKnowledgeItem>,
) -> OrgMemoryPayload {
    let total_promoted = items.iter().filter(|i| i.is_promoted).count();
    let total_candidates = items
        .iter()
        .filter(|i| !i.is_promoted && i.status != "rejected")
        .count();
    OrgMemoryPayload {
        enterprise_vault_path,
        total_promoted,
        total_candidates,
        items,
    }
}

fn payload_from_service(svc: &mut KnowledgePromotionService) -> OrgMemoryPayload {
    let candidates = svc.discover_candidates().unwrap_or_default();
    let latest = svc.repo.load_latest_by_origin_id().unwrap_or_default();
    let mut items = Vec::new();
    let mut seen = HashSet::new();

    for candidate in &candidates {
        let record = latest
            .iter()
            .find(|(id, _)| *id == candidate.origin_id)
            .map(|(_, r)| r);
        seen.insert(candidate.origin_id.clone());
        items.push(item_from_candidate(
            candidate,
            record,
            &svc.paths.local_vault,
        ));
    }

    for (id, record) in &latest {
        if seen.contains(id) {
            continue;
        }
        items.push(item_from_record(record, &svc.paths.local_vault));
    }

    payload_from_items(
        svc.paths.enterprise_vault.to_string_lossy().into_owned(),
        items,
    )
}

/// Fallback sin `.cortex/org.yaml`: lista el vault local con tipos enterprise.
fn payload_from_local_scan(project_root: &Path) -> OrgMemoryPayload {
    let layout = WorkspaceLayout::discover(project_root);
    let local_vault = resolve_local_vault(project_root);
    let mut items = Vec::new();
    let mut files = Vec::new();
    collect_md(&local_vault, &mut files);
    files.sort();

    for path in files {
        let rel = path
            .strip_prefix(&local_vault)
            .map(|p| p.to_string_lossy().replace('\\', "/"))
            .unwrap_or_else(|_| path.display().to_string());
        let Some(doc_type) = doc_type_from_rel_path(&rel) else {
            continue;
        };
        let title = extract_title(&path);
        items.push(OrgKnowledgeItem {
            origin_id: format!("{doc_type}:{rel}"),
            rel_path: rel.clone(),
            doc_type: doc_type.to_string(),
            title: if title.is_empty() { rel } else { title },
            status: "candidate".to_string(),
            priority: priority_for(doc_type).to_string(),
            issues: Vec::new(),
            reviewer: None,
            reason: None,
            updated_at: chrono::Utc::now().to_rfc3339(),
            is_promoted: false,
        });
    }

    payload_from_items(
        layout
            .enterprise_vault_path()
            .to_string_lossy()
            .into_owned(),
        items,
    )
}

fn collect_md(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = fs::read_dir(dir) else {
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

/// Extrae metadatos y candidatos de memoria organizacional para un proyecto.
pub fn get_project_org_memory(project_root: &Path) -> OrgMemoryPayload {
    match open_service(project_root) {
        Ok(mut svc) => payload_from_service(&mut svc),
        Err(_) => payload_from_local_scan(project_root),
    }
}

/// Aprueba y promulga un documento al conocimiento organizacional.
pub fn approve_org_knowledge(
    project_root: &Path,
    rel_path: &str,
    reviewer: &str,
    reason: &str,
) -> Result<String, String> {
    let mut svc = open_service(project_root)?;
    svc.review(rel_path, true, reviewer, Some(reason))
        .map_err(|e| e.to_string())?;
    let plan = svc.plan_promotion().map_err(|e| e.to_string())?;
    let matched: Vec<_> = plan
        .into_iter()
        .filter(|c| c.local_rel_path == rel_path || c.origin_id == rel_path)
        .collect();
    if matched.is_empty() {
        return Err(format!(
            "No hay candidato aprobable para '{rel_path}' (¿errores de validación o sin review?)"
        ));
    }
    svc.apply_promotion(&matched, reviewer)
        .map_err(|e| e.to_string())?;
    Ok(format!(
        "Documento '{rel_path}' promulgado al Vault Organizacional."
    ))
}

/// Rechaza un candidato a conocimiento organizacional con motivo documentado.
pub fn reject_org_knowledge(
    project_root: &Path,
    rel_path: &str,
    reviewer: &str,
    reason: &str,
) -> Result<String, String> {
    let mut svc = open_service(project_root)?;
    svc.review(rel_path, false, reviewer, Some(reason))
        .map_err(|e| e.to_string())?;
    Ok(format!("Documento '{rel_path}' marcado como rechazado."))
}

#[cfg(test)]
mod tests {
    use super::*;
    use cortex_enterprise::promotion_models::{PromotionRecord, PromotionStatus};
    use tempfile::TempDir;

    fn seed_enterprise_project(root: &Path) -> PathBuf {
        let cfg = cortex_enterprise::config::build_enterprise_org_config(
            "test-org",
            cortex_enterprise::models::OrgProfile::SmallCompany,
            false,
            false,
        )
        .unwrap();
        cortex_enterprise::config::write_enterprise_config(root, &cfg, None).unwrap();
        fs::write(root.join("config.yaml"), "lang: es\n").unwrap();
        let vault = root.join("vault").join("decisions");
        fs::create_dir_all(&vault).unwrap();
        vault
    }

    #[test]
    fn test_scan_and_approve_org_knowledge() {
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();
        let vault = seed_enterprise_project(root);

        let doc_path = vault.join("ADR-001-test.md");
        fs::write(
            &doc_path,
            "---\ntitle: ADR de prueba\nstatus: candidate\n---\n\n# Contexto",
        )
        .unwrap();

        let mem = get_project_org_memory(root);
        assert_eq!(mem.total_candidates, 1, "items: {:?}", mem.items);
        assert_eq!(mem.items.len(), 1);
        assert_eq!(mem.items[0].priority, "high");
        assert_eq!(mem.items[0].doc_type, "decision");

        let res = approve_org_knowledge(
            root,
            "decisions/ADR-001-test.md",
            "tech-lead",
            "Aprobado para la organizacion",
        );
        assert!(res.is_ok(), "approve: {res:?}");

        let mem_after = get_project_org_memory(root);
        assert_eq!(mem_after.total_promoted, 1, "items: {:?}", mem_after.items);
        assert_eq!(mem_after.total_candidates, 0);

        let layout = WorkspaceLayout::discover(root);
        let records = fs::read_to_string(layout.promotion_records_path())
            .expect("records.jsonl canónico de enterprise");
        let last = records.lines().last().unwrap();
        let rec: PromotionRecord = serde_json::from_str(last).expect("PromotionRecord tipado");
        assert_eq!(rec.status, PromotionStatus::Promoted);
        assert_eq!(rec.local_rel_path, "decisions/ADR-001-test.md");
        assert_ne!(rec.fingerprint, "norm-fp-ok");

        let dest = layout.enterprise_vault_path().join(&rec.dest_rel_path);
        assert!(dest.is_file(), "promovido a {}", dest.display());
        let dest_raw = fs::read_to_string(&dest).unwrap();
        assert!(dest_raw.contains("promotion_status"));
    }

    #[test]
    fn test_reject_org_knowledge_escribe_record_tipado() {
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();
        let vault = seed_enterprise_project(root);
        fs::write(
            vault.join("ADR-002-skip.md"),
            "---\ntitle: No va\nstatus: candidate\n---\n\n# No",
        )
        .unwrap();

        let res = reject_org_knowledge(
            root,
            "decisions/ADR-002-skip.md",
            "tech-lead",
            "fuera de alcance",
        );
        assert!(res.is_ok(), "reject: {res:?}");

        let mem = get_project_org_memory(root);
        assert_eq!(mem.total_promoted, 0);
        assert_eq!(mem.total_candidates, 0);
        assert!(
            mem.items.iter().any(|i| i.status == "rejected"),
            "items: {:?}",
            mem.items
        );
    }
}
