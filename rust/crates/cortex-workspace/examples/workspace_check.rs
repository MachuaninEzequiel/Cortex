//! Verificador de paridad P12B-1 — cortex-workspace vs oráculo Python.
//!
//! Uso: workspace_check <fixtures_dir> <golden_dir>
//!
//! Reconstruye la secuencia completa del oráculo
//! (`bench/parity/workspace_golden_p12b.py`) sobre los fixtures dejados en
//! `<fixtures_dir>` (copiados a un workdir temporal para no mutarlos),
//! normaliza igual ({{ROOT}}) y compara byte-a-byte contra
//! `golden_workspace.txt`.

use cortex_workspace::git_policy;
use cortex_workspace::handoff::{
    AgentHandoff, AgentName, ArtifactAction, ArtifactProduced, HandoffStatus,
};
use cortex_workspace::layout::WorkspaceLayout;
use cortex_workspace::runtime_context::{
    detect_git_branch, detect_git_repo_path, resolve_episodic_persist_dir, slugify,
    EpisodicNamespaceCfg,
};
use cortex_workspace::skills;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    std::process::exit(1);
}

// ── utilidades ──────────────────────────────────────────────────────────────

fn copy_dir(src: &Path, dst: &Path) {
    fs::create_dir_all(dst).unwrap();
    if !src.exists() {
        panic!("copy_dir: no existe {}", src.display());
    }
    for entry in fs::read_dir(src).unwrap() {
        let e = match entry {
            Ok(e) => e,
            Err(_) => continue,
        };
        let ty = e.file_type().unwrap();
        let to = dst.join(e.file_name());
        if ty.is_dir() {
            copy_dir(&e.path(), &to);
        } else {
            if let Err(e) = fs::copy(e.path(), &to) {
                panic!("copy {} → {}: {e}", to.display(), to.display());
            }
        }
    }
}

fn json_string(s: &str) -> String {
    serde_json::to_string(s).unwrap()
}

/// Objeto JSON estilo `json.dumps(obj, indent=2, ensure_ascii=False)`
/// con valores ya serializados.
fn json_obj(fields: &[(&str, String)]) -> String {
    let mut out = String::from("{\n");
    for (i, (k, v)) in fields.iter().enumerate() {
        if i > 0 {
            out.push_str(",\n");
        }
        out.push_str("  ");
        out.push_str(&json_string(k));
        out.push_str(": ");
        out.push_str(v);
    }
    out.push_str("\n}");
    out
}

/// repr() de str en Python: comillas simples salvo que contenga '.
fn py_repr(s: &str) -> String {
    if s.contains('\'') && !s.contains('"') {
        format!("\"{s}\"")
    } else {
        format!("'{s}'")
    }
}

#[allow(dead_code)]
fn sha12(path: &Path) -> String {
    let bytes = fs::read(path).unwrap();
    let digest = Sha256::digest(&bytes);
    let hex: String = digest.iter().map(|b| format!("{b:02x}")).collect();
    hex[..12].to_string()
}

fn walk_files(dir: &Path, out: &mut Vec<PathBuf>) {
    for entry in fs::read_dir(dir).unwrap() {
        let p = entry.unwrap().path();
        if p.is_dir() {
            walk_files(&p, out);
        } else {
            out.push(p);
        }
    }
}

// ── escenarios de layout ────────────────────────────────────────────────────

const ESCENARIOS: &[(&str, &[&str])] = &[
    // (nombre, componentes RELATIVOS del start bajo fixtures)
    ("S01_new_full", &["s01_new_full"]),
    ("S02_new_no_wsyaml", &["s02_new_no_wsyaml"]),
    ("S03_legacy", &["s03_legacy"]),
    ("S04_bootstrap", &["s04_bootstrap"]),
    ("S05_both_configs", &["s05_both_configs"]),
    ("S06_ws_yaml_v1", &["s06_ws_yaml_v1"]),
    (
        "S07_legacy_subdir",
        &["s07_legacy_subdir", "vault", "specs"],
    ),
    (
        "S08_start_inside_cortex",
        &["s08_inside_cortex", ".cortex", "skills"],
    ),
];

type LayoutGetter = fn(&WorkspaceLayout) -> PathBuf;

const PROPIEDADES_GETTERS: &[(&str, LayoutGetter)] = &[
    ("config_path", WorkspaceLayout::config_path),
    ("org_config_path", WorkspaceLayout::org_config_path),
    ("vault_path", WorkspaceLayout::vault_path),
    (
        "enterprise_vault_path",
        WorkspaceLayout::enterprise_vault_path,
    ),
    (
        "episodic_memory_path",
        WorkspaceLayout::episodic_memory_path,
    ),
    (
        "enterprise_memory_path",
        WorkspaceLayout::enterprise_memory_path,
    ),
    ("skills_dir", WorkspaceLayout::skills_dir),
    ("sessions_dir", WorkspaceLayout::sessions_dir),
    ("subagents_dir", WorkspaceLayout::subagents_dir),
    (
        "agent_guidelines_path",
        WorkspaceLayout::agent_guidelines_path,
    ),
    ("system_prompt_path", WorkspaceLayout::system_prompt_path),
    ("workspace_yaml_path", WorkspaceLayout::workspace_yaml_path),
    ("webgraph_dir", WorkspaceLayout::webgraph_dir),
    (
        "webgraph_config_path",
        WorkspaceLayout::webgraph_config_path,
    ),
    (
        "webgraph_workspace_path",
        WorkspaceLayout::webgraph_workspace_path,
    ),
    ("webgraph_cache_dir", WorkspaceLayout::webgraph_cache_dir),
    ("logs_dir", WorkspaceLayout::logs_dir),
    ("scripts_dir", WorkspaceLayout::scripts_dir),
    ("workflows_dir", WorkspaceLayout::workflows_dir),
    (
        "promotion_records_path",
        WorkspaceLayout::promotion_records_path,
    ),
    ("promotion_dir", WorkspaceLayout::promotion_dir),
    ("context_md_path", WorkspaceLayout::context_md_path),
    ("vault_index_path", WorkspaceLayout::vault_index_path),
    ("gitignore_path", WorkspaceLayout::gitignore_path),
    ("legacy_config_path", WorkspaceLayout::legacy_config_path),
    ("legacy_vault_path", WorkspaceLayout::legacy_vault_path),
    ("legacy_memory_path", WorkspaceLayout::legacy_memory_path),
    (
        "legacy_org_config_path",
        WorkspaceLayout::legacy_org_config_path,
    ),
];

fn dump_layout(nombre: &str, start: &Path, base: &Path) -> String {
    let l = WorkspaceLayout::discover(start);
    let mut fields: Vec<(&str, String)> = vec![
        ("escenario", json_string(nombre)),
        ("repo_root", json_string(&l.repo_root.to_string_lossy())),
        (
            "workspace_root",
            json_string(&l.workspace_root.to_string_lossy()),
        ),
        ("is_legacy_layout", l.is_legacy_layout.to_string()),
        ("is_new_layout", l.is_new_layout.to_string()),
    ];
    for (name, getter) in PROPIEDADES_GETTERS {
        fields.push((name, json_string(&getter(&l).to_string_lossy())));
    }
    fields.push((
        "resolve_vault",
        json_string(
            &l.resolve_workspace_relative(Path::new("vault"))
                .to_string_lossy(),
        ),
    ));
    fields.push((
        "resolve_memory",
        json_string(
            &l.resolve_workspace_relative(Path::new(".memory"))
                .to_string_lossy(),
        ),
    ));
    let abs = base.join("abs").join("passthrough.md");
    fields.push((
        "resolve_abs",
        json_string(&l.resolve_workspace_relative(&abs).to_string_lossy()),
    ));
    fields.push(("repr", json_string(&l.repr())));
    json_obj(&fields)
}

// ── handoff ─────────────────────────────────────────────────────────────────

const CLAIMS_ZOO: &[&str] = &[
    "Decisión: usar RRF",
    "123",
    "yes",
    "null",
    "abc # comment",
    "- item",
    "con espacio ",
    "ver https://x.io/a",
    "[algo], {otro}",
    "*ref",
    "&ancla",
    "%tag",
    "@user",
    "`code`",
    "'citado",
    "dijo \"hola\"",
    "d'junio",
    "-> flecha",
    "? duda",
];

fn handoff_base(agent: AgentName, status: HandoffStatus) -> AgentHandoff {
    AgentHandoff {
        agent,
        status,
        verified_claims: vec![],
        unverified_claims: vec![],
        artifacts_produced: vec![],
        context_for_next: vec![],
        suggested_adr: false,
        suggested_adr_reason: String::new(),
        suggested_context_terms: vec![],
    }
}

fn seccion_handoff(bloques: &mut Vec<String>) {
    let mut emitir = |tag: &str, h: &AgentHandoff| {
        let yaml = h.to_yaml();
        let rt = AgentHandoff::from_yaml(&yaml)
            .map(|back| back == *h)
            .unwrap_or(false);
        bloques.push(format!(
            "### {tag}\n{yaml}roundtrip: {}",
            if rt { "OK" } else { "FAIL" }
        ));
    };

    emitir(
        "H01_tipico",
        &AgentHandoff {
            suggested_adr: true,
            suggested_adr_reason: "decisión de tokens".into(),
            verified_claims: vec!["auth refactorizada a JWT".into()],
            ..handoff_base(AgentName::CortexCodeImplementer, HandoffStatus::Complete)
        },
    );
    emitir(
        "H02_artifacts",
        &AgentHandoff {
            verified_claims: vec!["docs generados".into()],
            artifacts_produced: vec![
                ArtifactProduced {
                    path: "src/auth.py".into(),
                    action: ArtifactAction::Modified,
                    lines_changed: 47,
                    lines_added: 0,
                },
                ArtifactProduced {
                    path: "docs/nuevo.md".into(),
                    action: ArtifactAction::Created,
                    lines_changed: 0,
                    lines_added: 120,
                },
            ],
            context_for_next: vec!["revisar gates de calidad".into()],
            ..handoff_base(AgentName::CortexDocumenter, HandoffStatus::Partial)
        },
    );
    emitir(
        "H03_folding",
        &AgentHandoff {
            verified_claims: vec!["una afirmación bastante larga que supera los \
                                  ochenta caracteres de ancho para ver el plegado"
                .into()],
            ..handoff_base(AgentName::CortexSync, HandoffStatus::Complete)
        },
    );
    emitir(
        "H04_zoo",
        &AgentHandoff {
            verified_claims: CLAIMS_ZOO.iter().map(|s| s.to_string()).collect(),
            ..handoff_base(AgentName::CortexSecurityAuditor, HandoffStatus::Blocked)
        },
    );
    emitir(
        "H05_multiline_tab",
        &AgentHandoff {
            verified_claims: vec!["linea1\nlinea2".into(), "tab\taqui".into()],
            ..handoff_base(AgentName::CortexTestVerifier, HandoffStatus::Partial)
        },
    );
    emitir(
        "H06_minimo",
        &handoff_base(AgentName::CortexSddwork, HandoffStatus::Complete),
    );

    let invalidos = [
        "- solo\n- lista\n",
        "agent: desconocido\nstatus: complete\n",
        "agent: cortex-sync\nstatus: done\n",
        "agent: cortex-sync\n",
    ];
    for (i, texto) in invalidos.iter().enumerate() {
        match AgentHandoff::from_yaml(texto) {
            Ok(_) => bloques.push(format!(
                "### invalid_{}\nFALLO: aceptó entrada inválida",
                i + 1
            )),
            Err(_) => bloques.push(format!("### invalid_{}\nRECHAZADO", i + 1)),
        }
    }
    match AgentHandoff::from_yaml("agent: cortex-sync\nstatus: complete\nextra: se ignora\n") {
        Ok(h) => bloques.push(format!(
            "### unknown_field\nOK(agent={},status={})",
            h.agent.as_str(),
            h.status.as_str()
        )),
        Err(e) => bloques.push(format!("### unknown_field\nFALLO: {e}")),
    }
}

// ── políticas + runtime_context + skills ────────────────────────────────────

const SLUGIFY_CASOS: &[&str] = &[
    "Mi Rama Feature",
    "¡Hola, Mundo!",
    "feature/Mi_Rama",
    "   ",
    "---",
    "ya-tiene-formato.ok_v1",
];

fn seccion_politicas(work: &Path, bloques: &mut Vec<String>) {
    let nuevo = work.join("s01_new_full");
    let legacy = work.join("s03_legacy");
    let real = work.join("s09_real_git");

    let ln = WorkspaceLayout::discover(&nuevo);
    let ll = WorkspaceLayout::discover(&legacy);

    bloques.push(format!(
        "### snippet_new\n{}",
        git_policy::recommended_gitignore_snippet(Some(&ln))
    ));
    bloques.push(format!(
        "### snippet_legacy\n{}",
        git_policy::recommended_gitignore_snippet(Some(&ll))
    ));
    bloques.push(format!(
        "### snippet_default\n{}",
        git_policy::recommended_gitignore_snippet(None)
    ));

    fs::write(
        nuevo.join(".gitignore"),
        "# comentario\n\n.memory/\n  *.chroma/  \n",
    )
    .unwrap();
    let filas: Vec<String> = [
        ".memory/",
        "  .memory/  ",
        "*.chroma/",
        "vault/sessions/",
        "# comentario",
    ]
    .iter()
    .map(|c| {
        // Python interpola bools como True/False en f-strings.
        let v = if git_policy::gitignore_contains(&nuevo, c) {
            "True"
        } else {
            "False"
        };
        format!("{}={}", py_repr(c), v)
    })
    .collect();
    bloques.push(format!("### gitignore_contains\n{}", filas.join("\n")));

    let filas: Vec<String> = SLUGIFY_CASOS
        .iter()
        .map(|v| format!("{}={}", py_repr(v), py_repr(&slugify(v, "default"))))
        .chain(std::iter::once(format!(
            "fallback={}",
            py_repr(&slugify("   ", "fb"))
        )))
        .collect();
    bloques.push(format!("### slugify\n{}", filas.join("\n")));

    // Fake git: fallbacks deterministas.
    let fake = work.join("fake_git");
    fs::create_dir_all(fake.join(".git")).unwrap();
    let toplevel = detect_git_repo_path(&fake);
    bloques.push(format!(
        "### git_fake\nbranch={}\ntoplevel=PosixPath('{}')",
        py_repr(&detect_git_branch(&fake)),
        toplevel.to_string_lossy()
    ));

    for (pd, mode, ns) in [
        ("memory", "project", ""),
        (".memory/chroma", "branch", ""),
        ("memory", "custom", "Mi Equipo!"),
        ("memory", "custom", "  "),
    ] {
        let cfg = EpisodicNamespaceCfg::new(pd, mode, ns);
        let out = resolve_episodic_persist_dir(&fake, &cfg);
        bloques.push(format!(
            "persist({mode},{},{})=PosixPath('{}')",
            py_repr(pd),
            py_repr(ns),
            out.to_string_lossy()
        ));
    }

    // Repo git REAL.
    let branch_real = detect_git_branch(&real);
    bloques.push(format!(
        "### git_real\nbranch={}\ntoplevel={{ROOT}}",
        py_repr(&branch_real)
    ));
    for (pd, mode) in [("memory", "project"), (".memory/c", "branch")] {
        let cfg = EpisodicNamespaceCfg::new(pd, mode, "");
        let out = resolve_episodic_persist_dir(&real, &cfg)
            .to_string_lossy()
            .replace(&real.to_string_lossy().to_string(), "{{ROOT}}");
        bloques.push(format!("real_persist({mode},{})={out}", py_repr(pd)));
    }

    // Skills.
    let destino = work.join("work").join("skills");
    let primera = skills::install_skills(&destino);
    let segunda = skills::install_skills(&destino);
    let mut filas = Vec::new();
    for nombre in &primera {
        let base_skill_name = nombre.split(' ').next().unwrap();
        let base_skill = destino.join(base_skill_name);
        let mut archivos: Vec<PathBuf> = Vec::new();
        walk_files(&base_skill, &mut archivos);
        archivos.sort();
        let hashes: Vec<String> = archivos
            .iter()
            .map(|p| {
                let rel = p.strip_prefix(&base_skill).unwrap().to_string_lossy();
                format!("{rel}:{}", sha12(p))
            })
            .collect();
        filas.push(format!("{nombre}::{}", hashes.join(";")));
    }
    bloques.push(format!("### skills_fresh\n{}", filas.join("\n")));
    bloques.push(format!("### skills_again\n{}", segunda.join("\n")));
}

// ── main ────────────────────────────────────────────────────────────────────

fn difflines(a: &str, b: &str) -> Vec<String> {
    let mut out = Vec::new();
    let al: Vec<&str> = a.split('\n').collect();
    let bl: Vec<&str> = b.split('\n').collect();
    let mut i = 0;
    while i < al.len() || i < bl.len() {
        let av = al.get(i).copied();
        let bv = bl.get(i).copied();
        if av != bv {
            out.push(format!("@@ línea {}\n- {av:?}\n+ {bv:?}", i + 1));
            if out.len() >= 240 {
                break;
            }
        }
        i += 1;
    }
    out.truncate(80);
    out
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        fail("uso: workspace_check <fixtures_dir> <golden_dir>");
    }
    let fixtures = Path::new(&args[1]);
    let golden_dir = Path::new(&args[2]);

    // Copiar los escenarios necesarios a un workdir temporal.
    let work = tempfile::tempdir().unwrap();
    let wb = work.path().join("fixtures");
    fs::create_dir_all(&wb).unwrap();
    for (_, rel) in ESCENARIOS {
        let dir = fixtures.join(rel[0]);
        copy_dir(&dir, &wb.join(rel[0]));
    }
    copy_dir(&fixtures.join("s09_real_git"), &wb.join("s09_real_git"));

    let mut bloques: Vec<String> = Vec::new();
    for (nombre, rel) in ESCENARIOS {
        let mut start = wb.clone();
        for c in *rel {
            start = start.join(c);
        }
        bloques.push(dump_layout(nombre, &start, &wb));
    }
    seccion_handoff(&mut bloques);
    seccion_politicas(&wb, &mut bloques);

    let mut salida = bloques.join("\n");
    salida.push('\n');
    let salida = salida.replace(&wb.to_string_lossy().to_string(), "{{ROOT}}");

    let esperado = fs::read_to_string(golden_dir.join("golden_workspace.txt")).unwrap();
    if salida == esperado {
        println!("[PASS] workspace_check byte-parity vs golden_workspace.txt");
        println!("\n✅ PARIDAD P12B-1");
    } else {
        for l in difflines(&esperado, &salida) {
            println!("{l}");
        }
        eprintln!("\n❌ diferencias vs golden");
        std::process::exit(1);
    }
}
