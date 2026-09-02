//! Módulo de integración de Memoria Organizacional (Enterprise Vault) en Cortex Brain.
//!
//! Permite descubrir candidatos locales a conocimiento institucional (ADRs, Specs, Guías),
//! consultar la cola de revisión, priorizarlos, aprobarlos (promulgarlos) y rechazarlos.

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use cortex_workspace::WorkspaceLayout;

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

/// Resuelve la ruta del vault local existente.
fn resolve_local_vault(project_root: &Path) -> PathBuf {
    let p1 = project_root.join("vault");
    if p1.exists() {
        return p1;
    }
    let p2 = project_root.join(".cortex").join("vault");
    if p2.exists() {
        return p2;
    }
    let layout = WorkspaceLayout::discover(project_root);
    layout.vault_path()
}

/// Extrae metadatos y candidatos de memoria organizacional para un proyecto.
pub fn get_project_org_memory(project_root: &Path) -> OrgMemoryPayload {
    let layout = WorkspaceLayout::discover(project_root);
    let enterprise_vault = layout.enterprise_vault_path();
    let local_vault = resolve_local_vault(project_root);

    let mut items: Vec<OrgKnowledgeItem> = Vec::new();

    // 1. Escanear vault local en busca de documentos candidatos
    if local_vault.exists() {
        scan_vault_for_org_candidates(&local_vault, &mut items);
    }

    // 2. Si existe records.jsonl de enterprise, fusionar estados autoritativos
    let records_file = project_root.join(".cortex").join("enterprise").join("records.jsonl");
    if records_file.exists() {
        if let Ok(content) = fs::read_to_string(&records_file) {
            for line in content.lines() {
                let line = line.trim();
                if line.is_empty() {
                    continue;
                }
                if let Ok(v) = serde_json::from_str::<serde_json::Value>(line) {
                    let rel = v.get("local_rel_path").and_then(|s| s.as_str()).unwrap_or("");
                    let status = v.get("status").and_then(|s| s.as_str()).unwrap_or("");
                    if let Some(item) = items.iter_mut().find(|i| i.rel_path == rel) {
                        item.status = status.to_string();
                        item.is_promoted = status == "promoted" || status == "accepted";
                        if let Some(dec) = v.get("decision") {
                            item.reviewer = dec.get("actor").and_then(|s| s.as_str()).map(String::from);
                            item.reason = dec.get("reason").and_then(|s| s.as_str()).map(String::from);
                        }
                    }
                }
            }
        }
    }

    let total_promoted = items.iter().filter(|i| i.is_promoted).count();
    let total_candidates = items.iter().filter(|i| !i.is_promoted && i.status != "rejected").count();

    OrgMemoryPayload {
        enterprise_vault_path: enterprise_vault.to_string_lossy().into_owned(),
        total_promoted,
        total_candidates,
        items,
    }
}

/// Escanea recursivamente el vault local buscando archivos markdown candidatos.
fn scan_vault_for_org_candidates(vault_dir: &Path, out: &mut Vec<OrgKnowledgeItem>) {
    let walker = match fs::read_dir(vault_dir) {
        Ok(w) => w,
        Err(_) => return,
    };

    for entry in walker.flatten() {
        let path = entry.path();
        if path.is_dir() {
            scan_vault_for_org_candidates(&path, out);
        } else if path.extension().and_then(|s| s.to_str()) == Some("md") {
            let rel_path = path.file_name().unwrap_or_default().to_string_lossy().into_owned();
            let parent_dir = path.parent().and_then(|p| p.file_name()).unwrap_or_default().to_string_lossy();
            
            let full_rel = if parent_dir == "vault" {
                rel_path.clone()
            } else {
                format!("{parent_dir}/{rel_path}")
            };

            let doc_type = match parent_dir.as_ref() {
                "decisions" | "adrs" => "adr",
                "specs" => "spec",
                "guides" => "guide",
                "rfc" => "rfc",
                _ => if rel_path.contains("ADR") { "adr" } else if rel_path.contains("spec") { "spec" } else { "doc" },
            };

            let priority = match doc_type {
                "adr" => "high",
                "spec" => "high",
                "rfc" => "medium",
                _ => "low",
            };

            let (title, status) = extract_title_and_status(&path);
            let is_promoted = status == "promoted" || status == "accepted";

            out.push(OrgKnowledgeItem {
                origin_id: format!("{doc_type}:{full_rel}"),
                rel_path: full_rel,
                doc_type: doc_type.to_string(),
                title: if title.is_empty() { rel_path } else { title },
                status,
                priority: priority.to_string(),
                issues: Vec::new(),
                reviewer: None,
                reason: None,
                updated_at: chrono::Utc::now().to_rfc3339(),
                is_promoted,
            });
        }
    }
}

/// Extrae título y estado de un archivo markdown leyendo el frontmatter.
fn extract_title_and_status(path: &Path) -> (String, String) {
    let content = match fs::read_to_string(path) {
        Ok(c) => c,
        Err(_) => return (String::new(), "draft".to_string()),
    };

    let mut title = String::new();
    let mut status = "candidate".to_string();

    if content.starts_with("---") {
        if let Some(end_idx) = content[3..].find("---") {
            let fm = &content[3..3 + end_idx];
            for line in fm.lines() {
                let line = line.trim();
                if let Some(t) = line.strip_prefix("title:") {
                    title = t.trim().trim_matches('"').trim_matches('\'').to_string();
                } else if let Some(s) = line.strip_prefix("status:") {
                    status = s.trim().trim_matches('"').trim_matches('\'').to_string();
                }
            }
        }
    }

    if title.is_empty() {
        for line in content.lines() {
            let line = line.trim();
            if let Some(h1) = line.strip_prefix("# ") {
                title = h1.trim().to_string();
                break;
            }
        }
    }

    (title, status)
}

/// Aprueba y promulga un documento al conocimiento organizacional.
pub fn approve_org_knowledge(
    project_root: &Path,
    rel_path: &str,
    reviewer: &str,
    reason: &str,
) -> Result<String, String> {
    let local_vault = resolve_local_vault(project_root);
    let full_path = local_vault.join(rel_path);

    if !full_path.exists() {
        return Err(format!("No se encontró el documento local: {rel_path}"));
    }

    // Actualizar frontmatter en el archivo local
    update_doc_frontmatter(&full_path, "accepted", reviewer, reason)?;

    // Registrar en .cortex/enterprise/records.jsonl
    let records_dir = project_root.join(".cortex").join("enterprise");
    let _ = fs::create_dir_all(&records_dir);
    let records_file = records_dir.join("records.jsonl");

    let record = serde_json::json!({
        "origin_id": format!("doc:{rel_path}"),
        "local_rel_path": rel_path,
        "doc_type": if rel_path.contains("ADR") || rel_path.contains("decision") { "adr" } else { "spec" },
        "dest_rel_path": format!("enterprise/{rel_path}"),
        "fingerprint": "norm-fp-ok",
        "status": "promoted",
        "created_at": chrono::Utc::now().to_rfc3339(),
        "updated_at": chrono::Utc::now().to_rfc3339(),
        "decision": {
            "decision": "approve",
            "actor": reviewer,
            "decided_at": chrono::Utc::now().to_rfc3339(),
            "reason": reason
        },
        "events": []
    });

    let mut f = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&records_file)
        .map_err(|e| format!("No se pudo escribir records.jsonl: {e}"))?;

    use std::io::Write;
    writeln!(f, "{}", record).map_err(|e| format!("Error al escribir record: {e}"))?;

    Ok(format!("Documento '{rel_path}' promulgado exitosamente al Vault Organizacional."))
}

/// Rechaza un candidato a conocimiento organizacional con motivo documentado.
pub fn reject_org_knowledge(
    project_root: &Path,
    rel_path: &str,
    reviewer: &str,
    reason: &str,
) -> Result<String, String> {
    let local_vault = resolve_local_vault(project_root);
    let full_path = local_vault.join(rel_path);

    if !full_path.exists() {
        return Err(format!("No se encontró el documento local: {rel_path}"));
    }

    update_doc_frontmatter(&full_path, "rejected", reviewer, reason)?;

    let records_dir = project_root.join(".cortex").join("enterprise");
    let _ = fs::create_dir_all(&records_dir);
    let records_file = records_dir.join("records.jsonl");

    let record = serde_json::json!({
        "origin_id": format!("doc:{rel_path}"),
        "local_rel_path": rel_path,
        "doc_type": "doc",
        "dest_rel_path": rel_path,
        "fingerprint": "norm-fp-ok",
        "status": "rejected",
        "created_at": chrono::Utc::now().to_rfc3339(),
        "updated_at": chrono::Utc::now().to_rfc3339(),
        "decision": {
            "decision": "reject",
            "actor": reviewer,
            "decided_at": chrono::Utc::now().to_rfc3339(),
            "reason": reason
        },
        "events": []
    });

    let mut f = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&records_file)
        .map_err(|e| format!("No se pudo escribir records.jsonl: {e}"))?;

    use std::io::Write;
    writeln!(f, "{}", record).map_err(|e| format!("Error al escribir record: {e}"))?;

    Ok(format!("Documento '{rel_path}' marcado como rechazado."))
}

/// Actualiza o inyecta campos de frontmatter en un archivo markdown.
fn update_doc_frontmatter(
    path: &Path,
    new_status: &str,
    reviewer: &str,
    reason: &str,
) -> Result<(), String> {
    let raw = fs::read_to_string(path).map_err(|e| format!("Lectura de {}: {e}", path.display()))?;
    let now = chrono::Utc::now().to_rfc3339();

    let updated = if raw.starts_with("---") {
        if let Some(end_idx) = raw[3..].find("---") {
            let body = &raw[3 + end_idx + 3..];
            format!(
                "---\nstatus: {new_status}\nreviewer: \"{reviewer}\"\nreview_reason: \"{reason}\"\nreviewed_at: \"{now}\"\n---\n{body}"
            )
        } else {
            format!("---\nstatus: {new_status}\nreviewer: \"{reviewer}\"\n---\n{raw}")
        }
    } else {
        format!("---\nstatus: {new_status}\nreviewer: \"{reviewer}\"\n---\n\n{raw}")
    };

    fs::write(path, updated).map_err(|e| format!("Escritura de {}: {e}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_scan_and_approve_org_knowledge() {
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();
        let vault = root.join("vault").join("decisions");
        fs::create_dir_all(&vault).unwrap();

        let doc_path = vault.join("ADR-001-test.md");
        fs::write(&doc_path, "---\ntitle: ADR de prueba\nstatus: candidate\n---\n\n# Contexto").unwrap();

        let mem = get_project_org_memory(root);
        assert_eq!(mem.total_candidates, 1);
        assert_eq!(mem.items.len(), 1);
        assert_eq!(mem.items[0].priority, "high");

        let res = approve_org_knowledge(root, "decisions/ADR-001-test.md", "tech-lead", "Aprobado para la organizacion");
        assert!(res.is_ok());

        let mem_after = get_project_org_memory(root);
        assert_eq!(mem_after.total_promoted, 1);
        assert_eq!(mem_after.total_candidates, 0);
    }
}
