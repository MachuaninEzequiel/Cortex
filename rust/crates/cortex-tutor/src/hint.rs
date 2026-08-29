//! Puerto de `cortex.tutor.hint`: ProjectState + HintEngine con cadena de
//! prioridad L0..L7 (primer match gana; L7 interpola conteos como el
//! f-string de Python).

use std::path::Path;

use cortex_workspace::WorkspaceLayout;

#[derive(Debug, Clone, PartialEq)]
pub struct Hint {
    pub icon: &'static str,
    pub title: String,
    pub body: String,
    pub command: String,
}

#[derive(Debug, Clone, Default, PartialEq)]
pub struct ProjectState {
    pub has_config: bool,
    pub has_vault: bool,
    pub has_cortex_dir: bool,
    pub has_org_yaml: bool,
    pub has_memory: bool,
    pub has_specs: bool,
    pub has_sessions: bool,
    pub has_enterprise_vault: bool,
    pub spec_count: usize,
    pub session_count: usize,
    pub vault_doc_count: usize,
    pub has_github_workflows: bool,
    pub has_mcp_config: bool,
}

impl ProjectState {
    /// `detect(project_root)` — resuelve paths vía WorkspaceLayout.
    pub fn detect(project_root: &Path) -> Self {
        let mut s = Self::default();
        let layout = WorkspaceLayout::discover(project_root);
        s.has_config = layout.config_path().exists();
        s.has_vault = layout.vault_path().is_dir();
        s.has_cortex_dir = layout.workspace_root.exists();
        s.has_org_yaml = layout.org_config_path().exists();
        s.has_memory = layout.episodic_memory_path().is_dir();
        s.has_enterprise_vault = layout.enterprise_vault_path().is_dir();
        s.has_github_workflows = layout.workflows_dir().is_dir();

        let specs_dir = layout.vault_path().join("specs");
        if specs_dir.is_dir() {
            s.spec_count = count_md(&specs_dir);
            s.has_specs = s.spec_count > 0;
        }
        let sessions_dir = layout.vault_path().join("sessions");
        if sessions_dir.is_dir() {
            s.session_count = count_md(&sessions_dir);
            s.has_sessions = s.session_count > 0;
        }
        if s.has_vault {
            s.vault_doc_count = count_md_recursive(&layout.vault_path());
        }
        // Python busca la config MCP del IDE en el proyecto.
        s.has_mcp_config =
            project_root.join(".mcp.json").exists() || project_root.join(".cortex/mcp").exists();
        s
    }
}

fn count_md(dir: &Path) -> usize {
    std::fs::read_dir(dir)
        .map(|entries| {
            entries
                .flatten()
                .filter(|e| e.path().extension().and_then(|x| x.to_str()) == Some("md"))
                .count()
        })
        .unwrap_or(0)
}

fn count_md_recursive(dir: &Path) -> usize {
    let mut total = 0usize;
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                total += count_md_recursive(&path);
            } else if path.extension().and_then(|x| x.to_str()) == Some("md") {
                total += 1;
            }
        }
    }
    total
}

/// L7 — plantilla con placeholders que se interpolan con los conteos.
const BOXED_ALL_GOOD: &str =
    "Vault: {vault} docs | Specs: {specs} | Sessions: {sessions}\nBuscá algo en tu memoria para verificar que todo funciona.";

/// `HintEngine.get_hint` — cadena L0..L7, primer match gana.
pub fn get_hint(state: &ProjectState) -> Hint {
    // L0: no inicializado.
    if !state.has_config {
        return Hint {
            icon: "🚀",
            title: "Cortex no está inicializado en este proyecto".into(),
            body: "Este directorio no tiene config.yaml.\nInicializá Cortex para empezar a construir memoria.".into(),
            command: "cortex setup agent".into(),
        };
    }
    // L1: inicializado sin specs.
    if !state.has_specs {
        return Hint {
            icon: "📝",
            title: "No hay especificaciones creadas".into(),
            body: "Antes de codear, creá una spec para documentar qué vas a hacer.\nEsto alimenta el contexto para futuras búsquedas.".into(),
            command: "cortex session open --title \"Mi Feature\"".into(),
        };
    }
    // L2: specs pero sin sesiones.
    if !state.has_sessions {
        return Hint {
            icon: "💾",
            title: format!("Tenés {} spec(s) pero 0 sesiones guardadas", state.spec_count),
            body: "Después de trabajar, guardá tu sesión para alimentar la memoria.\nCortex usa estas sesiones para dar contexto en tareas futuras.".into(),
            command: "cortex finish --reason \"Lo que hice\"".into(),
        };
    }
    // L3: contenido creciendo sin pipeline.
    if state.vault_doc_count > 5 && !state.has_github_workflows {
        return Hint {
            icon: "⚙️",
            title: "Tu vault está creciendo pero no tenés pipeline CI".into(),
            body: "Configurá el pipeline DevSecDocOps para proteger la calidad\nautomáticamente en cada PR.".into(),
            command: "cortex setup pipeline".into(),
        };
    }
    // L4: todo local, sin enterprise.
    if state.vault_doc_count > 10 && !state.has_org_yaml {
        return Hint {
            icon: "🏢",
            title: "Tu knowledge base tiene sustancia. ¿Trabajás en equipo?".into(),
            body: "Podés compartir conocimiento con la capa enterprise.\nEsto permite retrieval cruzado entre proyectos.".into(),
            command: "cortex setup enterprise --preset small-company".into(),
        };
    }
    // L5: enterprise configurado, sin promociones.
    if state.has_org_yaml && !state.has_enterprise_vault {
        return Hint {
            icon: "📤",
            title: "Enterprise configurado pero sin conocimiento promovido".into(),
            body: "Revisá qué docs están listos para promover al vault corporativo.\nUsá --dry-run para ver el plan sin ejecutar.".into(),
            command: "cortex promote-knowledge --dry-run".into(),
        };
    }
    // L6: sin IDE conectado.
    if !state.has_mcp_config {
        return Hint {
            icon: "🔌",
            title: "Cortex no está conectado a ningún IDE".into(),
            body: "Conectá tu IDE para que el agente de IA use herramientas Cortex\n(búsqueda, specs, sessions) directamente.".into(),
            command: "cortex inject".into(),
        };
    }
    // L7: todo bien — f-string de Python interpola los conteos.
    Hint {
        icon: "✅",
        title: "Tu proyecto Cortex está en buena forma".into(),
        body: BOXED_ALL_GOOD
            .replace("{vault}", &state.vault_doc_count.to_string())
            .replace("{specs}", &state.spec_count.to_string())
            .replace("{sessions}", &state.session_count.to_string()),
        command: "cortex search \"mi query\"".into(),
    }
}
