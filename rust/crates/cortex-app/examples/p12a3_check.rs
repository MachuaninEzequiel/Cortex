//! Verificador de paridad P12A-3 — pr_capture + PRContext + PRService.
//!
//! Uso: p12a3_check <golden_dir>
//!
//! Reproduce los escenarios S01–S12 de bench/parity/p12a3_golden.py sobre los
//! portes cortex_app::pr y compara el reporte normalizado byte-a-byte contra
//! golden_p12a3.txt. Los escenarios de captura corren con cwd en un tmp SIN
//! repo git (misma ruta de código que el oráculo: llamadas git ⇒ vacío).
//!
//! hu_references se emite ORDENADO: Python usa set() (orden no contrato).

use std::collections::BTreeMap;
use std::process::exit;

use cortex_app::pr::{
    capture_from_env, capture_from_json, capture_manual, capture_manual_in, detect_api_changes,
    detect_db_migrations, enrich_with_pipeline, save_context, CaptureManualArgs, PRContext,
};
use cortex_app::workitems::{EpisodicMemoryRequest, EpisodicSink};

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    exit(1);
}

/// repr Python de lista de strings: ['a', 'b'] / [].
fn py_list(items: &[String]) -> String {
    format!(
        "[{}]",
        items
            .iter()
            .map(|s| format!("'{s}'"))
            .collect::<Vec<_>>()
            .join(", ")
    )
}

// ── mini-JSON estilo json.dumps(indent=1, sort_keys=True) ───────────────────

enum Jv {
    Obj(Vec<(String, Jv)>),
    Arr(Vec<Jv>),
    Str(String),
}

fn escape(s: &str) -> String {
    let mut out = String::new();
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

fn emit(v: &Jv, nivel: usize, out: &mut String) {
    let pad = " ".repeat(nivel);
    let pad_inner = " ".repeat(nivel + 1);
    match v {
        Jv::Obj(campos) => {
            if campos.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push('{');
            for (i, (k, val)) in campos.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push('\n');
                out.push_str(&pad_inner);
                out.push_str(&escape(k));
                out.push_str(": ");
                emit(val, nivel + 1, out);
            }
            out.push('\n');
            out.push_str(&pad);
            out.push('}');
        }
        Jv::Arr(items) => {
            if items.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push('\n');
                out.push_str(&pad_inner);
                emit(item, nivel + 1, out);
            }
            out.push('\n');
            out.push_str(&pad);
            out.push(']');
        }
        Jv::Str(s) => out.push_str(&escape(s)),
    }
}

// ── fake episódico captor ───────────────────────────────────────────────────

#[derive(Default)]
struct CaptorEpisodic {
    llamadas: Vec<EpisodicMemoryRequest>,
}

impl EpisodicSink for CaptorEpisodic {
    fn add_memory(
        &mut self,
        req: EpisodicMemoryRequest,
    ) -> Result<cortex_app::episodic::MemoryEntry, String> {
        self.llamadas.push(req);
        Ok(cortex_app::episodic::MemoryEntry {
            id: "mem_oraculo0".into(),
            content: String::new(),
            memory_type: String::new(),
            tags: vec![],
            files: vec![],
            timestamp: String::new(),
            metadata: BTreeMap::new(),
        })
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        fail("uso: p12a3_check <golden_dir>");
    }
    let gdir = std::fs::canonicalize(&args[1]).expect("golden_dir");

    // cwd sin repo para las capturas (igual que el oráculo).
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let work = std::env::temp_dir().join(format!("p12a3_work_{nanos}"));
    std::fs::create_dir_all(work.join("vault")).expect("work");
    std::env::set_current_dir(&work).expect("chdir");

    // Entorno limpio para S08 (sin filtraciones del anfitrión).
    for k in [
        "PR_NUMBER",
        "PR_TITLE",
        "PR_BODY",
        "PR_AUTHOR",
        "PR_BRANCH",
        "TARGET_BRANCH",
        "PR_COMMIT",
        "PR_LABELS",
        "GITHUB_HEAD_REF",
        "GITHUB_BASE_REF",
        "GITHUB_SHA",
    ] {
        std::env::remove_var(k);
    }

    let mut bloques: Vec<String> = Vec::new();

    macro_rules! emitir {
        ($titulo:expr, $body:expr) => {{
            let resultado: Result<String, String> = ($body)();
            bloques.push(match resultado {
                Ok(salida) => format!("### {}\nrc=0\n{salida}", $titulo),
                Err(e) => format!("### {}\nrc=1\nException: {}", $titulo, e),
            });
        }};
    }

    let vault = work.join("vault");

    // S01 json mínimo
    emitir!("S01 json mínimo", || -> Result<String, String> {
        let ctx = PRContext {
            title: "Fix login bug".into(),
            author: "dev1".into(),
            source_branch: "fix/login".into(),
            commit_sha: "abc123".into(),
            ..Default::default()
        };
        assert_eq!(ctx.target_branch, "main");
        assert!(ctx.files_changed.is_empty());
        assert!(ctx.labels.is_empty());
        let path = save_context(&ctx, &work.join("ctx_min.json"))?;
        std::fs::read_to_string(path).map_err(|e| e.to_string())
    });

    // S02 json completo
    emitir!("S02 json completo", || -> Result<String, String> {
        let ctx = PRContext {
            pr_number: 42,
            title: "Implementar búsqueda semántica".into(),
            body: "Cuerpo con acentos: búsqueda\ny salto de línea".into(),
            author: "chucho".into(),
            source_branch: "feature/hu-42".into(),
            target_branch: "develop".into(),
            commit_sha: "deadbeefcafe".into(),
            files_changed: vec!["src/routes/users.js".into(), "migrations/001.sql".into()],
            diff_summary: " src/routes/users.js | 10 ++++\n 1 file changed".into(),
            labels: vec!["rag".into(), "backend".into()],
            lint_result: Some("pass".into()),
            ..Default::default()
        };
        let path = save_context(&ctx, &work.join("ctx_full.json"))?;
        std::fs::read_to_string(path).map_err(|e| e.to_string())
    });

    // S03 hu_references (ordenado)
    emitir!("S03 hu_references", || -> Result<String, String> {
        let ctx = PRContext {
            title: "Implement HU-42".into(),
            body:
                "This PR addresses HU-42 and also references HU-100. Related to #200, hu-7 y us-9."
                    .into(),
            author: "dev1".into(),
            source_branch: "feature/hu-42".into(),
            commit_sha: "abc123".into(),
            ..Default::default()
        };
        Ok(ctx.hu_references().join("\n"))
    });

    // S04 has_db_changes
    emitir!("S04 has_db_changes", || -> Result<String, String> {
        let con = PRContext {
            title: "Add migration".into(),
            author: "dev1".into(),
            source_branch: "feature/db".into(),
            commit_sha: "abc123".into(),
            files_changed: vec!["migrations/001_add_users.sql".into(), "src/app.js".into()],
            ..Default::default()
        };
        let sin = PRContext {
            title: "Fix typo".into(),
            author: "dev1".into(),
            source_branch: "fix/typo".into(),
            commit_sha: "abc123".into(),
            files_changed: vec!["README.md".into()],
            ..Default::default()
        };
        Ok(format!(
            "con={}\nsin={}",
            py_bool(con.has_db_changes()),
            py_bool(sin.has_db_changes())
        ))
    });

    // S05 has_api_changes
    emitir!("S05 has_api_changes", || -> Result<String, String> {
        let con = PRContext {
            title: "Add endpoint".into(),
            author: "dev1".into(),
            source_branch: "feature/api".into(),
            commit_sha: "abc123".into(),
            files_changed: vec![
                "src/routes/users.js".into(),
                "src/controllers/users.js".into(),
            ],
            ..Default::default()
        };
        let sin = PRContext {
            title: "Fix CSS".into(),
            author: "dev1".into(),
            source_branch: "fix/css".into(),
            commit_sha: "abc123".into(),
            files_changed: vec!["src/styles/main.css".into()],
            ..Default::default()
        };
        Ok(format!(
            "con={}\nsin={}",
            py_bool(con.has_api_changes()),
            py_bool(sin.has_api_changes())
        ))
    });

    // S06 has_adr_label
    emitir!("S06 has_adr_label", || -> Result<String, String> {
        let con = PRContext {
            title: "Architecture change".into(),
            author: "dev1".into(),
            source_branch: "feature/arch".into(),
            commit_sha: "abc123".into(),
            labels: vec!["adr".into(), "breaking".into()],
            ..Default::default()
        };
        let sin = PRContext {
            title: "Small fix".into(),
            author: "dev1".into(),
            source_branch: "fix/small".into(),
            commit_sha: "abc123".into(),
            labels: vec!["bugfix".into()],
            ..Default::default()
        };
        Ok(format!(
            "con={}\nsin={}",
            py_bool(con.has_adr_label()),
            py_bool(sin.has_adr_label())
        ))
    });

    // S07 capture_manual sin repo
    emitir!(
        "S07 capture_manual sin repo",
        || -> Result<String, String> {
            let ctx = capture_manual(CaptureManualArgs {
                title: "Test PR".into(),
                author: "dev1".into(),
                branch: "test".into(),
                commit: "abc123".into(),
                body: "Fixed the refresh token issue".into(),
                ..Default::default()
            });
            Ok(format!(
                "title={}\nauthor={}\nbranch={}\nbody={}\ntarget={}\nfiles={}\ndiff='{}'",
                ctx.title,
                ctx.author,
                ctx.source_branch,
                ctx.body,
                ctx.target_branch,
                py_list(&ctx.files_changed),
                ctx.diff_summary
            ))
        }
    );

    // S08 capture_from_github env fijo
    emitir!(
        "S08 capture_from_github env",
        || -> Result<String, String> {
            let vars: Vec<(&str, String)> = vec![
                ("PR_NUMBER", "7".into()),
                ("PR_TITLE", "Env captured PR".into()),
                ("PR_BODY", "cuerpo con acentos: búsqueda".into()),
                ("PR_AUTHOR", "alice".into()),
                ("PR_BRANCH", "feature/env".into()),
                ("TARGET_BRANCH", "develop".into()),
                ("PR_COMMIT", "deadbeef".into()),
                ("PR_LABELS", "ci, deploy".into()),
            ];
            let getenv = |k: &str| -> Option<String> {
                vars.iter()
                    .find(|(name, _)| *name == k)
                    .map(|(_, v)| v.clone())
            };
            let ctx = capture_from_env(&getenv);
            let mut labels = ctx.labels.clone();
            labels.sort();
            Ok(format!(
            "number={}\ntitle={}\nauthor={}\nsource={}\ntarget={}\ncommit={}\nlabels={}\nfiles={}",
            ctx.pr_number,
            ctx.title,
            ctx.author,
            ctx.source_branch,
            ctx.target_branch,
            ctx.commit_sha,
            py_list(&labels),
            py_list(&ctx.files_changed)
        ))
        }
    );

    // S09 detectores directos
    emitir!("S09 detectores directos", || -> Result<String, String> {
        let db_files: Vec<String> = vec![
            "migrations/001.sql".into(),
            "src/app.js".into(),
            "schema.sql".into(),
        ];
        let api_files: Vec<String> = vec![
            "src/routes/users.js".into(),
            "src/controllers/auth.js".into(),
            "README.md".into(),
        ];
        Ok(format!(
            "db={:?}\napi={:?}",
            detect_db_migrations(&db_files),
            detect_api_changes(&api_files)
        ))
    });

    // S10 enrich inmutabilidad
    emitir!("S10 enrich inmutabilidad", || -> Result<String, String> {
        let ctx = capture_manual_in(
            CaptureManualArgs {
                title: "Test PR".into(),
                author: "dev1".into(),
                branch: "test".into(),
                commit: "abc123".into(),
                ..Default::default()
            },
            Some(&work),
        );
        let enriched = enrich_with_pipeline(
            &ctx,
            Some("pass"),
            Some("fail: 2 high vulnerabilities"),
            Some("pass"),
        );
        Ok(format!(
            "enriched_lint={}\nenriched_audit={}\nenriched_test={}\noriginal_lint={}",
            enriched.lint_result.as_deref().unwrap_or("None"),
            enriched.audit_result.as_deref().unwrap_or("None"),
            enriched.test_result.as_deref().unwrap_or("None"),
            ctx.lint_result.as_deref().unwrap_or("None")
        ))
    });

    // S11 PRService.store_pr_context payload
    emitir!(
        "S11 PRService.store_pr_context",
        || -> Result<String, String> {
            let mut ep = CaptorEpisodic::default();
            {
                let ctx_meta: BTreeMap<String, serde_json::Value> = BTreeMap::from([(
                    "workspace".to_string(),
                    serde_json::Value::String("obra07".into()),
                )]);
                let mut svc = cortex_app::pr::PRService::new(&vault, Some(&mut ep))
                    .with_context_metadata(ctx_meta);
                let ctx = PRContext {
                    pr_number: 42,
                    title: "Fix login bug".into(),
                    body: "refresh token".into(),
                    author: "dev1".into(),
                    source_branch: "fix/login".into(),
                    target_branch: "main".into(),
                    commit_sha: "abc123def456".into(),
                    diff_summary: " src/main.py | 2 +-\n 1 file changed".into(),
                    files_changed: (0..30).map(|i| format!("f{i}.py")).collect(),
                    labels: vec!["bugfix".into()],
                    ..Default::default()
                };
                svc.store_pr_context(&ctx, Some("pass"), None, Some("pass"))?;
            }
            let episodico: Vec<Jv> = ep
                .llamadas
                .iter()
                .map(|r| {
                    Jv::Obj(vec![
                        ("content".into(), Jv::Str(r.content.clone())),
                        (
                            "extra_metadata".into(),
                            Jv::Obj(vec![("workspace".into(), Jv::Str("obra07".into()))]),
                        ),
                        (
                            "files".into(),
                            Jv::Arr(r.files.iter().cloned().map(Jv::Str).collect()),
                        ),
                        ("memory_type".into(), Jv::Str(r.memory_type.clone())),
                        (
                            "tags".into(),
                            Jv::Arr(r.tags.iter().cloned().map(Jv::Str).collect()),
                        ),
                    ])
                })
                .collect();
            let payload = Jv::Obj(vec![("episodico".into(), Jv::Arr(episodico))]);
            let mut s = String::new();
            emit(&payload, 0, &mut s);
            Ok(s)
        }
    );

    // S12 roundtrip json
    emitir!("S12 roundtrip json", || -> Result<String, String> {
        let ctx = PRContext {
            pr_number: 9,
            title: "Roundtrip".into(),
            body: "ida y vuelta".into(),
            author: "dev1".into(),
            source_branch: "rt".into(),
            commit_sha: "ffeeddcc".into(),
            labels: vec!["rt".into()],
            ..Default::default()
        };
        let p1 = save_context(&ctx, &work.join("rt1.json"))?;
        let loaded = capture_from_json(&p1)?;
        let p2 = save_context(&loaded, &work.join("rt2.json"))?;
        let iguales = std::fs::read(&p1).unwrap() == std::fs::read(&p2).unwrap();
        Ok(format!(
            "iguales={}\ntitle={}\nlabels={}\npr_number={}",
            py_bool(iguales),
            loaded.title,
            py_list(&loaded.labels),
            loaded.pr_number
        ))
    });

    // Normalización idéntica al oráculo.
    let crudo = bloques.join("");
    let ruta = work.to_string_lossy().to_string();
    let mut normalizado = crudo.replace(ruta.as_str(), "{{ROOT}}");
    if !normalizado.ends_with('\n') {
        normalizado.push('\n');
    }

    let esperado = std::fs::read_to_string(gdir.join("golden_p12a3.txt"))
        .unwrap_or_else(|e| fail(&format!("falta golden: {e}")));
    if normalizado == esperado {
        println!("[PASS] golden_p12a3.txt");
        println!("\nPARIDAD P12A-3 COMPLETA ✅ (pr_capture + PRContext + PRService)");
    } else {
        println!("[FAIL] golden_p12a3.txt difiere");
        let mut n = 0usize;
        for (l1, l2) in esperado.lines().zip(normalizado.lines()) {
            if l1 != l2 {
                println!("  py:   {l1}\n  rust: {l2}");
                n += 1;
                if n > 20 {
                    break;
                }
            }
        }
        fail("diferencias de paridad");
    }
    std::fs::remove_dir_all(&work).ok();
}

/// `True`/`False` de Python en los reportes.
fn py_bool(b: bool) -> &'static str {
    if b {
        "True"
    } else {
        "False"
    }
}
