//! Tests P12B-1 — espejo de la especificación Python:
//! tests/unit/workspace/test_layout.py · tests/unit/handoff.py ·
//! tests/unit/runtime_context.py · tests/unit/skills/test_install_observability.py.
//! Los casos de quoting/folding de handoff están congelados contra salidas
//! reales de PyYAML (verificadas empíricamente; el oráculo las re-verifica).

use std::path::Path;

use cortex_workspace::handoff::{
    AgentHandoff, AgentName, ArtifactAction, ArtifactProduced, HandoffStatus,
};
use cortex_workspace::layout::{find_git_root, WorkspaceLayout};
use cortex_workspace::pyyaml::{implicitly_non_str, to_pyyaml_string, Node};
use cortex_workspace::runtime_context::{slugify, EpisodicNamespaceCfg};
use cortex_workspace::{git_policy, runtime_context, skills};

// ── fixtures (espejo de test_layout.py) ─────────────────────────────────────

fn new_layout_project(base: &Path) -> TempDirFixture {
    let repo = base.join("myproject");
    std::fs::create_dir_all(repo.join(".cortex/vault")).unwrap();
    std::fs::write(
        repo.join(".cortex/config.yaml"),
        "episodic:\n  persist_dir: memory\n",
    )
    .unwrap();
    std::fs::write(
        repo.join(".cortex/workspace.yaml"),
        "layout_version: 2\nprojects:\n- id: primary\n  path: .\n  role: owner\n",
    )
    .unwrap();
    std::fs::create_dir_all(repo.join(".git")).unwrap();
    let cortex = repo.join(".cortex");
    TempDirFixture { repo, cortex }
}

fn legacy_layout_project(base: &Path) -> TempDirFixture {
    let repo = base.join("legacyproject");
    std::fs::create_dir_all(repo.join("vault")).unwrap();
    std::fs::create_dir_all(repo.join(".memory")).unwrap();
    let cortex = repo.join(".cortex");
    std::fs::create_dir_all(cortex.join("skills")).unwrap();
    std::fs::create_dir_all(cortex.join("subagents")).unwrap();
    std::fs::write(
        repo.join("config.yaml"),
        "episodic:\n  persist_dir: .memory/chroma\n",
    )
    .unwrap();
    std::fs::write(cortex.join("org.yaml"), "schema_version: 1\n").unwrap();
    std::fs::create_dir_all(repo.join(".git")).unwrap();
    TempDirFixture { repo, cortex }
}

struct TempDirFixture {
    repo: std::path::PathBuf,
    cortex: std::path::PathBuf,
}

// ── discovery ───────────────────────────────────────────────────────────────

#[test]
fn discover_new_layout_con_workspace_yaml() {
    let tmp = tempfile::tempdir().unwrap();
    let f = new_layout_project(tmp.path());
    let layout = WorkspaceLayout::discover(&f.repo);
    assert!(layout.is_new_layout);
    assert!(!layout.is_legacy_layout);
    assert_eq!(layout.workspace_root, f.cortex);
    assert_eq!(layout.repo_root, f.repo);
}

#[test]
fn discover_new_layout_desde_subdirectorio() {
    let tmp = tempfile::tempdir().unwrap();
    let f = new_layout_project(tmp.path());
    let sub = f.cortex.join("vault").join("sessions");
    std::fs::create_dir_all(&sub).unwrap();
    let layout = WorkspaceLayout::discover(&sub);
    assert!(layout.is_new_layout);
    assert_eq!(layout.workspace_root, f.cortex);
}

#[test]
fn discover_legacy_layout() {
    let tmp = tempfile::tempdir().unwrap();
    let f = legacy_layout_project(tmp.path());
    let layout = WorkspaceLayout::discover(&f.repo);
    assert!(layout.is_legacy_layout);
    assert!(!layout.is_new_layout);
    assert_eq!(layout.workspace_root, f.repo);
}

#[test]
fn discover_bootstrap_sin_proyecto() {
    let tmp = tempfile::tempdir().unwrap();
    let empty = tmp.path().join("nowhere");
    std::fs::create_dir_all(&empty).unwrap();
    let layout = WorkspaceLayout::discover(&empty);
    // Bootstrap: nuevo layout apuntando al start.
    assert!(layout.is_new_layout);
    assert_eq!(layout.repo_root, empty);
}

#[test]
fn discover_prefiere_nuevo_cuando_ambos_presentes() {
    let tmp = tempfile::tempdir().unwrap();
    let repo = tmp.path().join("both");
    std::fs::create_dir_all(repo.join(".cortex")).unwrap();
    std::fs::write(repo.join("config.yaml"), "legacy: true\n").unwrap();
    std::fs::write(repo.join(".cortex/config.yaml"), "new: true\n").unwrap();
    std::fs::write(
        repo.join(".cortex/workspace.yaml"),
        "layout_version: 2\nprojects: []\n",
    )
    .unwrap();
    std::fs::create_dir_all(repo.join(".git")).unwrap();
    let layout = WorkspaceLayout::discover(&repo);
    assert!(layout.is_new_layout);
}

#[test]
fn workspace_yaml_v1_es_legacy() {
    let tmp = tempfile::tempdir().unwrap();
    let repo = tmp.path().join("v1project");
    std::fs::create_dir_all(repo.join(".cortex")).unwrap();
    std::fs::write(
        repo.join(".cortex/workspace.yaml"),
        "layout_version: 1\nprojects: []\n",
    )
    .unwrap();
    std::fs::write(repo.join("config.yaml"), "x: y\n").unwrap();
    std::fs::create_dir_all(repo.join(".git")).unwrap();
    let layout = WorkspaceLayout::discover(&repo);
    assert!(layout.is_legacy_layout);
}

#[test]
fn sin_workspace_yaml_cae_a_legacy() {
    let tmp = tempfile::tempdir().unwrap();
    let repo = tmp.path().join("nowsyaml");
    std::fs::create_dir_all(repo.join(".cortex/skills")).unwrap();
    std::fs::write(repo.join("config.yaml"), "x: y\n").unwrap();
    std::fs::create_dir_all(repo.join(".git")).unwrap();
    let layout = WorkspaceLayout::discover(&repo);
    assert!(layout.is_legacy_layout);
}

#[test]
fn from_repo_root_nuevo() {
    let tmp = tempfile::tempdir().unwrap();
    let repo = tmp.path().join("explicit");
    std::fs::create_dir_all(&repo).unwrap();
    let layout = WorkspaceLayout::from_repo_root(&repo);
    assert!(layout.is_new_layout);
    assert_eq!(layout.workspace_root, repo.join(".cortex"));
}

// ── rutas nuevo/legacy ──────────────────────────────────────────────────────

#[test]
fn rutas_nuevo_layout() {
    let tmp = tempfile::tempdir().unwrap();
    let f = new_layout_project(tmp.path());
    let l = WorkspaceLayout::discover(&f.repo);
    assert_eq!(l.config_path(), f.cortex.join("config.yaml"));
    assert_eq!(l.org_config_path(), f.cortex.join("org.yaml"));
    assert_eq!(l.vault_path(), f.cortex.join("vault"));
    assert_eq!(l.enterprise_vault_path(), f.cortex.join("vault-enterprise"));
    assert_eq!(l.episodic_memory_path(), f.cortex.join("memory"));
    assert_eq!(
        l.enterprise_memory_path(),
        f.cortex.join("enterprise-memory")
    );
    assert_eq!(l.skills_dir(), f.cortex.join("skills"));
    assert_eq!(l.sessions_dir(), f.cortex.join("sessions"));
    assert_eq!(l.subagents_dir(), f.cortex.join("subagents"));
    assert_eq!(l.agent_guidelines_path(), f.cortex.join("AGENT.md"));
    assert_eq!(l.system_prompt_path(), f.cortex.join("system-prompt.md"));
    assert_eq!(l.workspace_yaml_path(), f.cortex.join("workspace.yaml"));
    assert_eq!(l.webgraph_dir(), f.cortex.join("webgraph"));
    assert_eq!(
        l.webgraph_config_path(),
        f.cortex.join("webgraph/config.yaml")
    );
    assert_eq!(l.webgraph_cache_dir(), f.cortex.join("webgraph/cache"));
    assert_eq!(l.logs_dir(), f.cortex.join("logs"));
    assert_eq!(l.scripts_dir(), f.cortex.join("scripts"));
    assert_eq!(l.workflows_dir(), f.repo.join(".github/workflows"));
    assert_eq!(
        l.promotion_records_path(),
        f.cortex.join("vault-enterprise/promotion/records.jsonl")
    );
    assert_eq!(
        l.vault_index_path(),
        f.cortex.join("vault/.cortex_index.json")
    );
    assert_eq!(l.gitignore_path(), f.repo.join(".gitignore"));
}

#[test]
fn rutas_legacy_layout() {
    let tmp = tempfile::tempdir().unwrap();
    let f = legacy_layout_project(tmp.path());
    let l = WorkspaceLayout::discover(&f.repo);
    assert_eq!(l.config_path(), f.repo.join("config.yaml"));
    assert_eq!(l.org_config_path(), f.cortex.join("org.yaml"));
    assert_eq!(l.vault_path(), f.repo.join("vault"));
    assert_eq!(l.enterprise_vault_path(), f.repo.join("vault-enterprise"));
    assert_eq!(l.episodic_memory_path(), f.repo.join(".memory"));
    assert_eq!(
        l.enterprise_memory_path(),
        f.repo.join(".memory/enterprise")
    );
    assert_eq!(l.skills_dir(), f.cortex.join("skills"));
    assert_eq!(l.sessions_dir(), f.cortex.join("sessions"));
    assert_eq!(
        l.promotion_records_path(),
        f.repo
            .join("vault-enterprise/.cortex/promotion/records.jsonl")
    );
    assert_eq!(l.scripts_dir(), f.repo.join("scripts"));
}

#[test]
fn sin_cortex_anidado() {
    let tmp = tempfile::tempdir().unwrap();
    let f = new_layout_project(tmp.path());
    let l = WorkspaceLayout::discover(&f.repo);
    for p in [
        l.config_path(),
        l.vault_path(),
        l.skills_dir(),
        l.sessions_dir(),
        l.org_config_path(),
        l.promotion_records_path(),
        l.webgraph_dir(),
        l.scripts_dir(),
    ] {
        let s = p.to_string_lossy();
        assert!(!s.contains(".cortex/.cortex"), "nested: {s}");
    }
}

#[test]
fn resolve_workspace_relative() {
    let tmp = tempfile::tempdir().unwrap();
    let f = new_layout_project(tmp.path());
    let l = WorkspaceLayout::discover(&f.repo);
    assert_eq!(
        l.resolve_workspace_relative(Path::new("vault")),
        f.cortex.join("vault")
    );

    let lf = legacy_layout_project(tmp.path());
    let ll = WorkspaceLayout::discover(&lf.repo);
    assert_eq!(
        ll.resolve_workspace_relative(Path::new("vault")),
        lf.repo.join("vault")
    );

    let abs = f.repo.join("abs/path");
    let r = l.resolve_workspace_relative(&abs);
    assert!(r.is_absolute());
}

#[test]
fn compatibilidad_legacy_helpers() {
    let tmp = tempfile::tempdir().unwrap();
    let f = new_layout_project(tmp.path());
    let l = WorkspaceLayout::discover(&f.repo);
    assert_eq!(l.legacy_config_path(), f.repo.join("config.yaml"));
    assert_eq!(l.legacy_vault_path(), f.repo.join("vault"));
    assert_eq!(l.legacy_memory_path(), f.repo.join(".memory"));
}

#[test]
fn repr_formato_python() {
    let tmp = tempfile::tempdir().unwrap();
    let f = new_layout_project(tmp.path());
    let l = WorkspaceLayout::discover(&f.repo);
    let r = l.repr();
    assert!(r.starts_with("WorkspaceLayout(repo_root=PosixPath('"));
    assert!(r.contains("mode=new"));
    let lf = legacy_layout_project(tmp.path());
    let ll = WorkspaceLayout::discover(&lf.repo);
    assert!(ll.repr().contains("mode=legacy"));
}

#[test]
fn find_git_root_espejo() {
    let tmp = tempfile::tempdir().unwrap();
    let project = tmp.path().join("myproject");
    std::fs::create_dir_all(project.join(".git")).unwrap();
    assert_eq!(find_git_root(&project), Some(project.clone()));
    let sub = project.join("src/pkg");
    std::fs::create_dir_all(&sub).unwrap();
    assert_eq!(find_git_root(&sub), Some(project.clone()));
    let nogit = tmp.path().join("nogit");
    std::fs::create_dir_all(&nogit).unwrap();
    assert_eq!(find_git_root(&nogit), None);
}

// ── handoff: quoting zoo congelado contra PyYAML real ────────────────────────

fn handoff_claims(claims: &[&str]) -> AgentHandoff {
    AgentHandoff {
        agent: AgentName::CortexSync,
        status: HandoffStatus::Complete,
        verified_claims: claims.iter().map(|s| s.to_string()).collect(),
        ..AgentHandoff {
            agent: AgentName::CortexSync,
            status: HandoffStatus::Complete,
            verified_claims: vec![],
            unverified_claims: vec![],
            artifacts_produced: vec![],
            context_for_next: vec![],
            suggested_adr: false,
            suggested_adr_reason: String::new(),
            suggested_context_terms: vec![],
        }
    }
}

#[test]
fn yaml_quoting_zoo_parity() {
    let cases: &[(&str, &str)] = &[
        ("Decisión: usar RRF", "- 'Decisión: usar RRF'"),
        ("123", "- '123'"),
        ("yes", "- 'yes'"),
        ("null", "- 'null'"),
        ("abc # comment", "- 'abc # comment'"),
        ("- item", "- '- item'"),
        ("con espacio ", "- 'con espacio '"),
        ("ver https://x.io/a", "- ver https://x.io/a"),
        ("[algo], {otro}", "- '[algo], {otro}'"),
        ("*ref", "- '*ref'"),
        ("&ancla", "- '&ancla'"),
        ("%tag", "- '%tag'"),
        ("@user", "- '@user'"),
        ("`code`", "- '`code`'"),
        ("'citado", "- '''citado'"),
        ("dijo \"hola\"", "- dijo \"hola\""),
        ("d'junio", "- d'junio"),
        ("a\tb", "- \"a\\tb\""),
        ("-> flecha", "- -> flecha"),
        ("? duda", "- '? duda'"),
    ];
    for (input, esperada_linea) in cases {
        let out = handoff_claims(&[input]).to_yaml();
        let linea = out
            .lines()
            .find(|l| l.starts_with("- ") || *l == "-" || l.starts_with('\''))
            .unwrap_or_else(|| panic!("{input:?}: sin línea de claim en:\n{out}"));
        assert_eq!(linea.trim_end(), *esperada_linea, "input={input:?}\n{out}");
    }
    // Multilínea (abarca varias líneas): contains sobre el YAML completo,
    // congelado contra safe_dump real.
    let out_ml = handoff_claims(&["linea1\nlinea2"]).to_yaml();
    assert!(out_ml.contains("- 'linea1\n\n  linea2'\n"), "{out_ml}");
}

#[test]
fn yaml_folding_80_columnas_parity() {
    // Congelado contra yaml.safe_dump real (misma frase en ambos lados).
    let largo =
        "una afirmación bastante larga que supera los ochenta caracteres de ancho para ver el plegado";
    let out = handoff_claims(&[largo]).to_yaml();
    assert!(
        out.contains("- una afirmación bastante larga que supera los ochenta caracteres de ancho para ver\n  el plegado\n"),
        "{out}"
    );
    // Y vacío ⇒ ''.
    let out = handoff_claims(&[]).to_yaml();
    assert!(out.contains("verified_claims: []\n"), "{out}");
}

#[test]
fn yaml_handoff_completo_parity() {
    let h = AgentHandoff {
        agent: AgentName::CortexCodeImplementer,
        status: HandoffStatus::Partial,
        verified_claims: vec!["auth ok".into()],
        unverified_claims: vec![],
        artifacts_produced: vec![ArtifactProduced {
            path: "src/auth.py".into(),
            action: ArtifactAction::Modified,
            lines_changed: 47,
            lines_added: 0,
        }],
        context_for_next: vec![],
        suggested_adr: true,
        suggested_adr_reason: "decisión de tokens".into(),
        suggested_context_terms: vec![],
    };
    let esperado = "agent: cortex-code-implementer\n\
                    status: partial\n\
                    verified_claims:\n\
                    - auth ok\n\
                    unverified_claims: []\n\
                    artifacts_produced:\n\
                    - path: src/auth.py\n  action: modified\n  lines_changed: 47\n  lines_added: 0\n\
                    context_for_next: []\n\
                    suggested_adr: true\n\
                    suggested_adr_reason: decisión de tokens\n\
                    suggested_context_terms: []\n";
    assert_eq!(h.to_yaml(), esperado);
}

#[test]
fn yaml_roundtrip_y_validaciones() {
    let h = AgentHandoff {
        agent: AgentName::CortexDocumenter,
        status: HandoffStatus::Blocked,
        verified_claims: vec!["x: y".into(), "2026-08-24".into()],
        unverified_claims: vec!["pend".into()],
        artifacts_produced: vec![
            ArtifactProduced {
                path: "a.md".into(),
                action: ArtifactAction::Created,
                lines_changed: 3,
                lines_added: 9,
            },
            ArtifactProduced {
                path: "b.md".into(),
                action: ArtifactAction::Renamed,
                lines_changed: 0,
                lines_added: 0,
            },
        ],
        context_for_next: vec!["revisar gates".into()],
        suggested_adr: false,
        suggested_adr_reason: String::new(),
        suggested_context_terms: vec!["rrf".into()],
    };
    let text = h.to_yaml();
    let back = AgentHandoff::from_yaml(&text).unwrap();
    assert_eq!(back, h);

    // Raíz no-mapping.
    assert_eq!(
        AgentHandoff::from_yaml("- solo\n- lista\n").unwrap_err(),
        "Handoff YAML must be a mapping at the root"
    );
    // Literal inválido.
    assert!(AgentHandoff::from_yaml("agent: agente-desconocido\nstatus: complete\n").is_err());
    assert!(AgentHandoff::from_yaml("agent: cortex-sync\nstatus: done\n").is_err());
    // Required faltante.
    assert!(AgentHandoff::from_yaml("agent: cortex-sync\n").is_err());
    // Campos desconocidos se ignoran (pydantic default).
    let ok = AgentHandoff::from_yaml("agent: cortex-sync\nstatus: complete\nextra: se ignora\n")
        .unwrap();
    assert_eq!(ok.agent, AgentName::CortexSync);
}

#[test]
fn resolver_implicito_no_str() {
    for s in [
        "",
        "~",
        "null",
        "NULL",
        "yes",
        "OFF",
        "123",
        "-7",
        "0x1F",
        "0b101",
        "010",
        "1.5",
        ".5e+3",
        ".inf",
        ".NaN",
        "1:30",
        "2026-08-24",
        "2026-08-24T10:30:00",
        "2026-8-4 10:30:00Z",
        "2026-13-45",
    ] {
        assert!(implicitly_non_str(s), "{s:?} debía ser no-str");
    }
    // Nota: la regex del resolver NO valida rangos (2026-13-45 es
    // timestamp); "1.5e3" NO es float en PyYAML instalado (exige signo).
    for s in [
        "hola",
        "auth.py",
        "https://x.io/a",
        "-> flecha",
        "08",
        "d'junio",
        "-",
        "?",
        ":",
    ] {
        assert!(!implicitly_non_str(s), "{s:?} debía resolver str");
    }
}

#[test]
fn pyyaml_emisor_arbol_generico() {
    // Congelado contra safe_dump real (misma frase en ambos lados):
    // fold tras la 10ª palabra (col>80), continuación a col 2.
    let largo: String = "palabra ".repeat(20);
    let esperado = "k: 'palabra palabra palabra palabra palabra palabra palabra palabra palabra palabra\n  palabra palabra palabra palabra palabra palabra palabra palabra palabra palabra '\n";
    assert_eq!(
        to_pyyaml_string(&Node::Map(vec![("k".into(), Node::s(largo.clone()))])),
        esperado
    );
    assert_eq!(
        to_pyyaml_string(&Node::Map(vec![(
            "k".into(),
            Node::Seq(vec![Node::s("corta")])
        )])),
        "k:\n- corta\n"
    );
    assert_eq!(
        to_pyyaml_string(&Node::Map(vec![("k".into(), Node::Seq(vec![]))])),
        "k: []\n"
    );
    let nested = Node::Map(vec![(
        "k".into(),
        Node::Seq(vec![Node::Map(vec![("g".into(), Node::s(largo.clone()))])]),
    )]);
    let out = to_pyyaml_string(&nested);
    assert!(out.starts_with("k:\n- g: 'palabra "), "{out}");
    assert!(out.contains("\n    palabra"), "continuación a col 4: {out}");
}

// ── git_policy ──────────────────────────────────────────────────────────────

#[test]
fn snippet_gitignore_por_layout() {
    let tmp = tempfile::tempdir().unwrap();
    let f = new_layout_project(tmp.path());
    let l = WorkspaceLayout::discover(&f.repo);
    let esperado_new = "# Cortex local state (new layout)\n.cortex/memory/\n*.chroma/\n\n# Cortex vault policy\n# Track: vault/specs, vault/decisions, vault/runbooks, vault/hu, vault/incidents\n# Ignore session churn by default unless your team explicitly audits sessions in Git\n.cortex/vault/sessions/";
    assert_eq!(
        git_policy::recommended_gitignore_snippet(Some(&l)),
        esperado_new
    );

    let lf = legacy_layout_project(tmp.path());
    let ll = WorkspaceLayout::discover(&lf.repo);
    let esperado_legacy = "# Cortex local state\n.memory/\n*.chroma/\n\n# Cortex vault policy\n# Track: vault/specs, vault/decisions, vault/runbooks, vault/hu, vault/incidents\n# Ignore session churn by default unless your team explicitly audits sessions in Git\nvault/sessions/";
    assert_eq!(
        git_policy::recommended_gitignore_snippet(Some(&ll)),
        esperado_legacy
    );

    assert_eq!(
        git_policy::recommended_gitignore_snippet(None),
        esperado_legacy
    );
    assert_eq!(
        git_policy::RECOMMENDED_GITIGNORE_PATTERNS,
        [".memory/", "*.chroma/", "vault/sessions/"]
    );
}

#[test]
fn gitignore_contains_comportamiento() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    assert!(!git_policy::gitignore_contains(root, ".memory/"));
    std::fs::write(
        root.join(".gitignore"),
        "# comentario\n\n.memory/\n  *.chroma/  \n",
    )
    .unwrap();
    assert!(git_policy::gitignore_contains(root, ".memory/"));
    assert!(git_policy::gitignore_contains(root, "  .memory/  "));
    assert!(git_policy::gitignore_contains(root, "*.chroma/"));
    assert!(!git_policy::gitignore_contains(root, "vault/sessions/"));
}

// ── runtime_context ─────────────────────────────────────────────────────────

#[test]
fn slugify_tabla() {
    assert_eq!(slugify("Mi Rama Feature", "default"), "mi-rama-feature");
    assert_eq!(slugify("¡Hola, Mundo!", "default"), "hola-mundo");
    assert_eq!(slugify("feature/Mi_Rama", "detached"), "feature-mi_rama");
    assert_eq!(slugify("   ", "fallback"), "fallback");
    assert_eq!(slugify("---", "fb"), "fb");
    assert_eq!(
        slugify("ya-tiene-formato.ok_v1", "fb"),
        "ya-tiene-formato.ok_v1"
    );
}

#[test]
fn git_fallbacks_sin_repo_real() {
    let tmp = tempfile::tempdir().unwrap();
    // Fake .git dir (no es repo válido) ⇒ fallbacks deterministas.
    std::fs::create_dir_all(tmp.path().join(".git")).unwrap();
    assert_eq!(
        runtime_context::detect_git_branch(tmp.path()),
        "no-git-branch"
    );
    assert_eq!(
        runtime_context::detect_git_repo_path(tmp.path()),
        tmp.path()
    );
}

#[test]
fn resolve_episodic_modes_sobre_fake_git() {
    let tmp = tempfile::tempdir().unwrap();
    std::fs::create_dir_all(tmp.path().join(".git")).unwrap();
    let root = tmp.path();

    let project = EpisodicNamespaceCfg::new("memory", "project", "");
    assert_eq!(
        runtime_context::resolve_episodic_persist_dir(root, &project),
        root.join("memory")
    );

    let branch = EpisodicNamespaceCfg::new(".memory/chroma", "branch", "");
    assert_eq!(
        runtime_context::resolve_episodic_persist_dir(root, &branch),
        root.join(".memory/chroma/branches/no-git-branch")
    );

    let custom = EpisodicNamespaceCfg::new("memory", "custom", "Mi Equipo!");
    assert_eq!(
        runtime_context::resolve_episodic_persist_dir(root, &custom),
        root.join("memory/custom/mi-equipo")
    );

    let custom_empty = EpisodicNamespaceCfg::new("memory", "custom", "  ");
    assert_eq!(
        runtime_context::resolve_episodic_persist_dir(root, &custom_empty),
        root.join("memory/custom/default")
    );
}

// ── skills ──────────────────────────────────────────────────────────────────

#[test]
fn install_skills_copia_bundle_completo() {
    let tmp = tempfile::tempdir().unwrap();
    let target = tmp.path().join("skills");
    let instaladas = skills::install_skills(&target);
    assert_eq!(instaladas.len(), skills::SKILL_NAMES.len());
    assert_eq!(
        instaladas,
        skills::SKILL_NAMES
            .iter()
            .map(|s| s.to_string())
            .collect::<Vec<_>>()
    );
    for name in skills::SKILL_NAMES {
        assert!(
            target.join(name).join("SKILL.md").is_file(),
            "{name}/SKILL.md"
        );
    }
    // Re-instalación ⇒ "(already exists)".
    let segunda = skills::install_skills(&target);
    for (i, nombre) in segunda.iter().enumerate() {
        assert_eq!(
            nombre,
            &format!("{} (already exists)", skills::SKILL_NAMES[i])
        );
    }
}
