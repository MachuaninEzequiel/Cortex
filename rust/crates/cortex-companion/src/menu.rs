//! Catálogo de capacidades del Companion (G-B2c): las 27 familias reales
//! del CLI agrupadas por dominio — la pieza anti-olvido.
//!
//! v1 = lista canónica FIJA (NO un shell). Cada entrada es un `CatalogEntry`
//! con la familia, args canónicos de lectura (dry-run donde existe) y su
//! dominio. `command_effect` clasifica la entrada en `Direct` (se ejecuta
//! sin aprobación) o `Guarded` (mutante ⇒ `run_guarded`, B2).
//!
//! El catálogo se deriva del dispatch real del CLI
//! (`cortex-cli/src/main.rs::dispatch_native`, 27 subárboles: los 26 del
//! doc 14 §0 + `init`).

/// Dominio de agrupación del catálogo (spec 14 §3, panel Menu).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Domain {
    Sessions,
    Memory,
    Search,
    Docs,
    Ci,
    Setup,
    Enterprise,
}

impl Domain {
    /// Etiqueta visible (UI ES por default, igual que el resto del repo).
    pub fn label(self) -> &'static str {
        match self {
            Domain::Sessions => "Sesiones",
            Domain::Memory => "Memoria",
            Domain::Search => "Búsqueda",
            Domain::Docs => "Docs",
            Domain::Ci => "CI",
            Domain::Setup => "Setup",
            Domain::Enterprise => "Enterprise",
        }
    }
}

/// Entrada del catálogo: familia + args canónicos + título + dominio.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CatalogEntry {
    pub family: &'static str,
    pub args: &'static [&'static str],
    pub title: &'static str,
    pub domain: Domain,
}

/// Efecto de una entrada del menú: qué camino toma al ejecutarse.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommandEffect {
    /// Lectura (o dry-run): se ejecuta directa, sin aprobación.
    Direct,
    /// Mutante: SIEMPRE detrás de `run_guarded` (B2) — nunca ejecución directa.
    Guarded,
}

/// Familias cuya simple invocación MUTA estado (sin excepción).
const UNCONDITIONAL_MUTATION: &[&str] = &[
    "remember",
    "forget",
    "install-skills",
    "init",
    "setup",
    "reindex",
];

/// Subcomandos mutantes por familia (primera palabra de args).
const MUTATING_ARGS: &[(&str, &[&str])] = &[
    (
        "session",
        &["finish", "close", "checkpoint", "abandon", "switch", "task"],
    ),
    ("docs", &["validate", "restore", "migrate"]),
    ("ide", &["setup", "remove"]),
    ("review-knowledge", &["approve", "reject"]),
    ("autopilot", &["start", "checkpoint", "finish"]),
    (
        "ci",
        &[
            "open-review-session",
            "report-checkpoint",
            "close-review-session",
        ],
    ),
    ("pr-context", &["store", "generate"]),
    ("hu", &["import"]),
    ("webgraph", &["export"]),
    ("promote-knowledge", &["--apply"]),
];

/// Clasifica familia+args sin necesidad de una entrada del catálogo (útil
/// para `RunCommand` arbitrarios del runtime/tests). `--dry-run` nunca muta.
fn family_args_guarded(family: &str, args: &[&str]) -> bool {
    if args.contains(&"--dry-run") {
        return false;
    }
    if UNCONDITIONAL_MUTATION.contains(&family) {
        return true;
    }
    if let Some((_, muts)) = MUTATING_ARGS.iter().find(|(f, _)| *f == family) {
        if args.iter().any(|a| muts.contains(a)) {
            return true;
        }
    }
    false
}

/// Clasifica una entrada: mutante ⇒ Guarded; dry-run y lecturas ⇒ Direct.
pub fn command_effect(e: &CatalogEntry) -> CommandEffect {
    if family_args_guarded(e.family, e.args) {
        CommandEffect::Guarded
    } else {
        CommandEffect::Direct
    }
}

/// Clasifica un comando arbitrario (family + args en `String`), igual que
/// `command_effect` pero para el runtime (B5) sin reconstruir el catálogo.
pub fn command_is_guarded(family: &str, args: &[String]) -> bool {
    let args: Vec<&str> = args.iter().map(|a| a.as_str()).collect();
    family_args_guarded(family, &args)
}

/// Catálogo completo: EXACTAMENTE las 27 familias del dispatch nativo,
/// una entrada por familia, agrupadas por dominio (orden canónico).
pub fn catalog() -> Vec<CatalogEntry> {
    use Domain::*;
    vec![
        // ---- Sesiones ----
        CatalogEntry {
            family: "session",
            args: &[],
            title: "Sesiones",
            domain: Sessions,
        },
        CatalogEntry {
            family: "next",
            args: &[],
            title: "Siguiente acción",
            domain: Sessions,
        },
        CatalogEntry {
            family: "autopilot",
            args: &["status"],
            title: "Autopilot",
            domain: Sessions,
        },
        // ---- Memoria ----
        CatalogEntry {
            family: "remember",
            args: &[],
            title: "Recordar memoria",
            domain: Memory,
        },
        CatalogEntry {
            family: "forget",
            args: &[],
            title: "Olvidar memoria",
            domain: Memory,
        },
        CatalogEntry {
            family: "memory-report",
            args: &[],
            title: "Reporte de memoria",
            domain: Memory,
        },
        CatalogEntry {
            family: "stats",
            args: &[],
            title: "Conteos de memoria",
            domain: Memory,
        },
        CatalogEntry {
            family: "reindex",
            args: &["--dry-run"],
            title: "Reindexar vault (dry-run)",
            domain: Memory,
        },
        CatalogEntry {
            family: "webgraph",
            args: &["doctor"],
            title: "Webgraph",
            domain: Memory,
        },
        // ---- Búsqueda ----
        CatalogEntry {
            family: "search",
            args: &[],
            title: "Búsqueda híbrida",
            domain: Search,
        },
        CatalogEntry {
            family: "context",
            args: &["--format", "markdown"],
            title: "Contexto enriquecido",
            domain: Search,
        },
        // ---- Docs ----
        CatalogEntry {
            family: "docs",
            args: &["search"],
            title: "Documentación",
            domain: Docs,
        },
        CatalogEntry {
            family: "tutor",
            args: &[],
            title: "Guía tutor",
            domain: Docs,
        },
        CatalogEntry {
            family: "hint",
            args: &[],
            title: "Tip contextual",
            domain: Docs,
        },
        CatalogEntry {
            family: "install-skills",
            args: &[],
            title: "Instalar skills",
            domain: Docs,
        },
        CatalogEntry {
            family: "agent-guidelines",
            args: &[],
            title: "Guidelines del agente",
            domain: Docs,
        },
        // ---- CI ----
        CatalogEntry {
            family: "ci",
            args: &["validate-pr"],
            title: "CI: validar PR",
            domain: Ci,
        },
        CatalogEntry {
            family: "pr-context",
            args: &["search"],
            title: "Contexto de PR",
            domain: Ci,
        },
        // ---- Setup ----
        CatalogEntry {
            family: "setup",
            args: &["agent", "--dry-run"],
            title: "Setup inicial",
            domain: Setup,
        },
        CatalogEntry {
            family: "init",
            args: &[],
            title: "Init (setup agent)",
            domain: Setup,
        },
        CatalogEntry {
            family: "ide",
            args: &["list"],
            title: "IDEs",
            domain: Setup,
        },
        CatalogEntry {
            family: "mcp-server",
            args: &[],
            title: "Servidor MCP",
            domain: Setup,
        },
        CatalogEntry {
            family: "doctor",
            args: &[],
            title: "Doctor",
            domain: Setup,
        },
        // ---- Enterprise ----
        CatalogEntry {
            family: "org-config",
            args: &[],
            title: "Config de organización",
            domain: Enterprise,
        },
        CatalogEntry {
            family: "promote-knowledge",
            args: &["--dry-run"],
            title: "Promover conocimiento",
            domain: Enterprise,
        },
        CatalogEntry {
            family: "review-knowledge",
            args: &["pending"],
            title: "Revisar conocimiento",
            domain: Enterprise,
        },
        CatalogEntry {
            family: "hu",
            args: &["list"],
            title: "Historias de usuario",
            domain: Enterprise,
        },
    ]
}

/// Fila plana del menú (dominio + sus entradas, encabezados incluidos).
/// `flat_rows()` es la ÚNICA fuente del orden de filas: render y hit-test la
/// comparten estructuralmente, no pueden divergir.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FlatRow {
    Header(Domain),
    Entry(CatalogEntry),
}

/// Filas planas: 7 encabezados + 27 entradas = 34 (orden canónico).
pub fn flat_rows() -> Vec<FlatRow> {
    let mut rows = Vec::with_capacity(34);
    for d in [
        Domain::Sessions,
        Domain::Memory,
        Domain::Search,
        Domain::Docs,
        Domain::Ci,
        Domain::Setup,
        Domain::Enterprise,
    ] {
        rows.push(FlatRow::Header(d));
        for e in catalog().iter().filter(|e| e.domain == d) {
            rows.push(FlatRow::Entry(*e));
        }
    }
    rows
}

/// Fila plana en el índice `flat` (None si está fuera de rango).
pub fn row_at(flat: usize) -> Option<FlatRow> {
    flat_rows().get(flat).copied()
}

/// Entrada del catálogo para una familia+args (para reconstruir el título y
/// la clasificación desde un `RunCommand` del runtime o de tests).
pub fn entry_for(family: &str, args: &[String]) -> Option<CatalogEntry> {
    catalog()
        .into_iter()
        .find(|e| e.family == family && e.args.iter().copied().eq(args.iter().map(|a| a.as_str())))
}

/// Salida de un comando del menú (para el panel de salida de la pantalla).
#[derive(Debug, Clone)]
pub struct MenuOutput {
    pub text: String,
    pub is_error: bool,
}

impl MenuOutput {
    pub fn ok(text: impl Into<String>) -> Self {
        MenuOutput {
            text: text.into(),
            is_error: false,
        }
    }
    pub fn err(text: impl Into<String>) -> Self {
        MenuOutput {
            text: text.into(),
            is_error: true,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    #[test]
    fn catalog_has_all_27_families_grouped() {
        let cat = catalog();
        let mut families: HashSet<&'static str> = HashSet::new();
        for e in &cat {
            assert!(families.insert(e.family), "familia duplicada: {}", e.family);
        }
        assert_eq!(families.len(), 27, "catálogo debe tener 27 familias");
        assert!(families.contains("session"), "falta session");
        assert!(families.contains("next"), "falta next");
        assert!(families.contains("webgraph"), "falta webgraph");
        assert!(families.contains("init"), "falta init (27º subárbol real)");
        // Todos los dominios tienen al menos una entrada.
        for d in [
            Domain::Sessions,
            Domain::Memory,
            Domain::Search,
            Domain::Docs,
            Domain::Ci,
            Domain::Setup,
            Domain::Enterprise,
        ] {
            assert!(cat.iter().any(|e| e.domain == d), "dominio {:?} vacío", d);
        }
        // flat_rows: 7 headers + 27 entries, mismas entradas en orden.
        let rows = flat_rows();
        assert_eq!(rows.len(), 34);
        assert_eq!(
            rows.iter()
                .filter(|r| matches!(r, FlatRow::Entry(_)))
                .count(),
            27
        );
        assert_eq!(
            rows.iter()
                .filter(|r| matches!(r, FlatRow::Header(_)))
                .count(),
            7
        );
    }

    #[test]
    fn menu_entry_mutation_requires_approval_flow() {
        let e = CatalogEntry {
            family: "session",
            args: &["finish"],
            title: "x",
            domain: Domain::Sessions,
        };
        let fx = command_effect(&e);
        assert!(matches!(fx, CommandEffect::Guarded));
    }

    #[test]
    fn classification_table_sane() {
        // Lecturas / dry-run ⇒ Direct.
        let reads = [
            ("stats", &[][..]),
            ("doctor", &[][..]),
            ("session", &[][..]),
            ("session", &["list"]),
            ("session", &["current"]),
            ("docs", &["search"]),
            ("docs", &["routing-table"]),
            ("ide", &["list"]),
            ("ide", &["status"]),
            ("reindex", &["--dry-run"]),
            ("promote-knowledge", &["--dry-run"]),
            ("promote-knowledge", &[][..]),
            ("review-knowledge", &["pending"]),
            ("autopilot", &["status"]),
            ("webgraph", &["doctor"]),
            ("ci", &["validate-pr"]),
            ("pr-context", &["search"]),
            ("hu", &["list"]),
        ];
        for (f, a) in reads {
            let e = CatalogEntry {
                family: f,
                args: a,
                title: "t",
                domain: Domain::Sessions,
            };
            assert_eq!(
                command_effect(&e),
                CommandEffect::Direct,
                "{f} {a:?} debería ser Direct"
            );
        }
        // Mutantes ⇒ Guarded.
        let writes = [
            ("remember", &[][..]),
            ("forget", &[][..]),
            ("init", &[][..]),
            ("setup", &["agent"]),
            ("install-skills", &[][..]),
            ("session", &["checkpoint"]),
            ("session", &["abandon"]),
            ("docs", &["validate"]),
            ("docs", &["restore"]),
            ("ide", &["remove"]),
            ("reindex", &[][..]),
            ("promote-knowledge", &["--apply"]),
            ("review-knowledge", &["approve"]),
            ("autopilot", &["finish"]),
            ("ci", &["open-review-session"]),
            ("pr-context", &["generate"]),
            ("hu", &["import"]),
            ("webgraph", &["export"]),
        ];
        for (f, a) in writes {
            let e = CatalogEntry {
                family: f,
                args: a,
                title: "t",
                domain: Domain::Sessions,
            };
            assert_eq!(
                command_effect(&e),
                CommandEffect::Guarded,
                "{f} {a:?} debería ser Guarded"
            );
        }
    }

    #[test]
    fn entry_for_matches_catalog() {
        // reconstructivo del runtime: familia+args ⇒ misma entrada del catálogo.
        let e = entry_for("session", &[]);
        assert_eq!(e.map(|e| e.title), Some("Sesiones"));
        let e = entry_for("reindex", &["--dry-run".to_string()]);
        assert_eq!(e.map(|e| e.title), Some("Reindexar vault (dry-run)"));
        assert!(entry_for("nope", &[]).is_none(), "familia inexistente");
    }
}
