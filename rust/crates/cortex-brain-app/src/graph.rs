//! Extractor de Grafo de Conocimiento (WebGraph), Estado de Sesión y Auditoría Doctor (Obra 20 / Línea A).
//!
//! Escanea el árbol del proyecto de forma eficiente para construir el grafo
//! visual (nodos y aristas), leer el estado de gobernanza (.cortex/sessions/)
//! y diagnosticar la salud del repositorio sin dependencias externas.

use std::fs;
use std::path::{Path, PathBuf};
use serde::{Deserialize, Serialize};

/// Nodo del grafo de conocimiento del proyecto.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct GraphNode {
    pub id: String,
    pub label: String,
    pub kind: String, // "file" | "spec" | "adr" | "module"
    pub path: String,
}

/// Arista de relación entre dos nodos del grafo.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct GraphEdge {
    pub source: String,
    pub target: String,
    pub relation: String, // "imports" | "documents" | "tests" | "depends_on"
}

/// Payload completo del grafo para renderizar en WebGraph.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct ProjectGraphPayload {
    pub nodes: Vec<GraphNode>,
    pub edges: Vec<GraphEdge>,
}

/// Estado de la sesión de trabajo activa en `.cortex/sessions/`.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct SessionStatusPayload {
    pub active: bool,
    pub session_id: Option<String>,
    pub spec_path: Option<String>,
    pub checkpoints_count: usize,
    pub last_checkpoint: Option<String>,
}

/// Chequeo individual de salud del proyecto.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct DoctorCheck {
    pub name: String,
    pub status: String, // "ok" | "warn" | "fail"
    pub message: String,
    pub auto_fix_tool: Option<String>,
}

/// Reporte completo de auditoría de salud (Cortex Doctor).
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct DoctorReportPayload {
    pub is_healthy: bool,
    pub checks: Vec<DoctorCheck>,
}

/// Evento emitido al frontend cuando el Brain hace referencia a nodos específicos.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct NodeHighlightEvent {
    pub node_ids: Vec<String>,
    pub topic: String,
}

/// Extrae el grafo de conocimiento del proyecto escaneando módulos, specs, ADRs y archivos clave.
pub fn extract_project_graph(project_root: &Path) -> ProjectGraphPayload {
    let mut nodes = Vec::new();
    let mut edges = Vec::new();

    if !project_root.is_dir() {
        return ProjectGraphPayload { nodes, edges };
    }

    let root_name = project_root
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("project");

    // 1. Nodo raíz del proyecto
    let root_id = "root".to_string();
    nodes.push(GraphNode {
        id: root_id.clone(),
        label: root_name.to_string(),
        kind: "module".to_string(),
        path: project_root.display().to_string(),
    });

    // 2. Módulos / Crates en rust/crates o packages
    let rust_crates = project_root.join("rust").join("crates");
    if rust_crates.is_dir() {
        if let Ok(entries) = fs::read_dir(&rust_crates) {
            for entry in entries.flatten() {
                let p = entry.path();
                if p.is_dir() {
                    let crate_name = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
                    if !crate_name.is_empty() && !crate_name.starts_with('.') {
                        let rel_id = format!("rust/crates/{crate_name}");
                        nodes.push(GraphNode {
                            id: rel_id.clone(),
                            label: crate_name.to_string(),
                            kind: "module".to_string(),
                            path: p.display().to_string(),
                        });
                        edges.push(GraphEdge {
                            source: root_id.clone(),
                            target: rel_id,
                            relation: "depends_on".to_string(),
                        });
                    }
                }
            }
        }
    }

    // 3. Apps en apps/
    let apps_dir = project_root.join("apps");
    if apps_dir.is_dir() {
        if let Ok(entries) = fs::read_dir(&apps_dir) {
            for entry in entries.flatten() {
                let p = entry.path();
                if p.is_dir() {
                    let app_name = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
                    if !app_name.is_empty() && !app_name.starts_with('.') {
                        let rel_id = format!("apps/{app_name}");
                        nodes.push(GraphNode {
                            id: rel_id.clone(),
                            label: app_name.to_string(),
                            kind: "module".to_string(),
                            path: p.display().to_string(),
                        });
                        edges.push(GraphEdge {
                            source: root_id.clone(),
                            target: rel_id,
                            relation: "depends_on".to_string(),
                        });
                    }
                }
            }
        }
    }

    // 4. Specs en vault/specs/ o docs/specs/
    for specs_dir_name in &["vault/specs", "docs/specs", "specs"] {
        let specs_dir = project_root.join(specs_dir_name);
        if specs_dir.is_dir() {
            if let Ok(entries) = fs::read_dir(&specs_dir) {
                for entry in entries.flatten() {
                    let p = entry.path();
                    if p.is_file() && p.extension().is_some_and(|ext| ext == "md") {
                        let fname = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
                        let id = format!("{specs_dir_name}/{fname}");
                        nodes.push(GraphNode {
                            id: id.clone(),
                            label: fname.trim_end_matches(".md").to_string(),
                            kind: "spec".to_string(),
                            path: p.display().to_string(),
                        });
                        edges.push(GraphEdge {
                            source: root_id.clone(),
                            target: id,
                            relation: "documents".to_string(),
                        });
                    }
                }
            }
        }
    }

    // 5. ADRs en vault/adrs/ o docs/adrs/ o vault/
    for adr_dir_name in &["vault/adrs", "docs/adrs", "vault/session-notes", "docs"] {
        let adr_dir = project_root.join(adr_dir_name);
        if adr_dir.is_dir() {
            if let Ok(entries) = fs::read_dir(&adr_dir) {
                for entry in entries.flatten() {
                    let p = entry.path();
                    if p.is_file() && p.extension().is_some_and(|ext| ext == "md") {
                        let fname = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
                        if fname.starts_with("ADR") || fname.starts_with("adr") || fname.contains("SESSION") || fname.contains("PLAN") {
                            let id = format!("{adr_dir_name}/{fname}");
                            nodes.push(GraphNode {
                                id: id.clone(),
                                label: fname.trim_end_matches(".md").to_string(),
                                kind: "adr".to_string(),
                                path: p.display().to_string(),
                            });
                            edges.push(GraphEdge {
                                source: root_id.clone(),
                                target: id,
                                relation: "documents".to_string(),
                            });
                        }
                    }
                }
            }
        }
    }

    // 6. Archivos clave de código en src/ o lib.rs
    scan_key_source_files(project_root, &mut nodes, &mut edges);

    ProjectGraphPayload { nodes, edges }
}

/// Escanea recursivamente archivos clave de código (hasta un límite de 40 archivos).
fn scan_key_source_files(root: &Path, nodes: &mut Vec<GraphNode>, edges: &mut Vec<GraphEdge>) {
    let mut count = 0;
    let max_files = 40;

    fn walk_dir(
        dir: &Path,
        root: &Path,
        nodes: &mut Vec<GraphNode>,
        edges: &mut Vec<GraphEdge>,
        count: &mut usize,
        max_files: usize,
        depth: usize,
    ) {
        if depth > 4 || *count >= max_files {
            return;
        }

        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.flatten() {
                if *count >= max_files {
                    break;
                }
                let p = entry.path();
                let name = p.file_name().and_then(|n| n.to_str()).unwrap_or("");

                // Ignorar carpetas pesadas
                if name.starts_with('.')
                    || name == "target"
                    || name == "node_modules"
                    || name == "dist"
                    || name == "build"
                    || name == "vendor"
                {
                    continue;
                }

                if p.is_dir() {
                    walk_dir(&p, root, nodes, edges, count, max_files, depth + 1);
                } else if p.is_file() {
                    let ext = p.extension().and_then(|e| e.to_str()).unwrap_or("");
                    if matches!(ext, "rs" | "ts" | "tsx" | "py" | "go") {
                        if let Ok(rel) = p.strip_prefix(root) {
                            let rel_str = rel.to_string_lossy().to_string();
                            // Priorizar archivos principales
                            if name == "lib.rs"
                                || name == "main.rs"
                                || name == "App.tsx"
                                || name == "main.tsx"
                                || name == "index.ts"
                                || depth <= 3
                            {
                                *count += 1;
                                let id = rel_str.clone();
                                nodes.push(GraphNode {
                                    id: id.clone(),
                                    label: name.to_string(),
                                    kind: "file".to_string(),
                                    path: p.display().to_string(),
                                });

                                // Conectar con módulo padre si existe
                                if let Some(parent) = rel.parent() {
                                    let parent_str = parent.to_string_lossy().to_string();
                                    if !parent_str.is_empty() {
                                        edges.push(GraphEdge {
                                            source: parent_str,
                                            target: id,
                                            relation: "imports".to_string(),
                                        });
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    walk_dir(root, root, nodes, edges, &mut count, max_files, 0);
}

/// Extrae el estado actual de la sesión de trabajo en el proyecto.
pub fn inspect_session_status(project_root: &Path) -> SessionStatusPayload {
    let sessions_dir = project_root.join(".cortex").join("sessions");
    if !sessions_dir.is_dir() {
        return SessionStatusPayload {
            active: false,
            session_id: None,
            spec_path: None,
            checkpoints_count: 0,
            last_checkpoint: None,
        };
    }

    let mut newest_file: Option<PathBuf> = None;
    let mut newest_time = std::time::UNIX_EPOCH;

    if let Ok(entries) = fs::read_dir(&sessions_dir) {
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_file() {
                if let Ok(meta) = p.metadata() {
                    if let Ok(modified) = meta.modified() {
                        if modified > newest_time {
                            newest_time = modified;
                            newest_file = Some(p);
                        }
                    }
                }
            }
        }
    }

    if let Some(session_path) = newest_file {
        let fname = session_path.file_name().and_then(|n| n.to_str()).unwrap_or("");
        let session_id = fname.trim_end_matches(".json").trim_end_matches(".jsonl").to_string();

        let mut checkpoints_count = 0;
        let mut last_checkpoint = None;

        if let Ok(content) = fs::read_to_string(&session_path) {
            // Conteo de checkpoints por líneas jsonl o bloques json
            for line in content.lines() {
                let trimmed = line.trim();
                if !trimmed.is_empty() {
                    checkpoints_count += 1;
                    last_checkpoint = Some(trimmed.to_string());
                }
            }
        }

        return SessionStatusPayload {
            active: true,
            session_id: Some(session_id),
            spec_path: Some(format!("vault/specs/spec-{}.md", fname)),
            checkpoints_count: checkpoints_count.max(1),
            last_checkpoint: last_checkpoint.or_else(|| Some("Inicio de sesión".to_string())),
        };
    }

    SessionStatusPayload {
        active: false,
        session_id: None,
        spec_path: None,
        checkpoints_count: 0,
        last_checkpoint: None,
    }
}

/// Ejecuta diagnóstico de salud de Cortex sobre el proyecto.
pub fn inspect_doctor_health(project_root: &Path) -> DoctorReportPayload {
    let mut checks = Vec::new();

    // 1. Check de directorio .cortex
    let dot_cortex = project_root.join(".cortex");
    if dot_cortex.is_dir() {
        checks.push(DoctorCheck {
            name: "Cortex Layout (.cortex)".to_string(),
            status: "ok".to_string(),
            message: "Directorio de gobernanza .cortex presente y estructurado".to_string(),
            auto_fix_tool: None,
        });
    } else {
        checks.push(DoctorCheck {
            name: "Cortex Layout (.cortex)".to_string(),
            status: "fail".to_string(),
            message: "Falta el directorio .cortex. El proyecto no está inicializado con Cortex".to_string(),
            auto_fix_tool: Some("setup init".to_string()),
        });
    }

    // 2. Check de configuración (workspace.yaml o config.yaml)
    let config_cortex = dot_cortex.join("config.yaml");
    let config_root = project_root.join("config.yaml");
    if config_cortex.is_file() || config_root.is_file() {
        checks.push(DoctorCheck {
            name: "Configuración (config.yaml)".to_string(),
            status: "ok".to_string(),
            message: "Archivo de configuración detectado".to_string(),
            auto_fix_tool: None,
        });
    } else {
        checks.push(DoctorCheck {
            name: "Configuración (config.yaml)".to_string(),
            status: "warn".to_string(),
            message: "No se encontró config.yaml. Se utilizan valores por defecto".to_string(),
            auto_fix_tool: Some("config init".to_string()),
        });
    }

    // 3. Check de Vault (vault/ o docs/)
    let vault_dir = project_root.join("vault");
    let docs_dir = project_root.join("docs");
    if vault_dir.is_dir() || docs_dir.is_dir() {
        checks.push(DoctorCheck {
            name: "Vault de Documentación".to_string(),
            status: "ok".to_string(),
            message: "Directorio de notas y especificaciones presente".to_string(),
            auto_fix_tool: None,
        });
    } else {
        checks.push(DoctorCheck {
            name: "Vault de Documentación".to_string(),
            status: "warn".to_string(),
            message: "No se encontró carpeta vault/ ni docs/".to_string(),
            auto_fix_tool: Some("docs init".to_string()),
        });
    }

    // 4. Check de Memoria Episódica (.cortex/memory.jsonl / action_log.jsonl)
    let memory_file = dot_cortex.join("action_log.jsonl");
    let memory_alt = dot_cortex.join("enrichment-events.jsonl");
    if memory_file.is_file() || memory_alt.is_file() {
        checks.push(DoctorCheck {
            name: "Memoria Episódica".to_string(),
            status: "ok".to_string(),
            message: "Eventos de memoria episódica y acciones registrados".to_string(),
            auto_fix_tool: None,
        });
    } else {
        checks.push(DoctorCheck {
            name: "Memoria Episódica".to_string(),
            status: "ok".to_string(),
            message: "Memoria lista para registrar nuevos eventos de sesión".to_string(),
            auto_fix_tool: None,
        });
    }

    let is_healthy = !checks.iter().any(|c| c.status == "fail");
    DoctorReportPayload { is_healthy, checks }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn graph_extraction_empty_or_nonexistent_returns_empty() {
        let p = Path::new("/nonexistent_path_cortex_xyz");
        let g = extract_project_graph(p);
        assert!(g.nodes.is_empty());
        assert!(g.edges.is_empty());
    }

    #[test]
    fn doctor_health_reports_status() {
        let temp = std::env::temp_dir().join(format!("cortex_doc_test_{}", std::process::id()));
        let _ = fs::create_dir_all(temp.join(".cortex"));
        let _ = fs::create_dir_all(temp.join("vault"));

        let report = inspect_doctor_health(&temp);
        assert!(report.is_healthy);
        assert!(report.checks.iter().any(|c| c.name.contains("Cortex Layout") && c.status == "ok"));

        let _ = fs::remove_dir_all(&temp);
    }
}
