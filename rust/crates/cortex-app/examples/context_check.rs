//! Verificador de paridad P7 — ContextEnricher nativo vs oráculo Python.
//!
//! Uso: context_check <fixtures_dir> <golden_dir> <model_dir>
//!
//! Reconstruye el mismo pipeline del oráculo (`bench/parity/
//! context_golden_p7.py`) sobre las nativas episódica (P3) y semántica
//! (P2b): carga el export neutro, indexa el vault, corre los tres casos y
//! compara los bundles normalizados (floats a 6 decimales, matched_by
//! ordenado, {{ROOT}}) byte-a-byte contra los goldens commiteados.

use std::path::PathBuf;

use chrono::Utc;
use cortex_app::context::budget_resolver;
use cortex_app::context::models::{EnrichedBundle, WorkContext};
use cortex_app::context::{ContextEnricher, ContextEnricherConfig};
use cortex_app::episodic::NativeEpisodicStore;
use cortex_app::semantic::SemanticIndex;
use cortex_embed::onnx::OnnxEmbedder;

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    std::process::exit(1);
}

// ── mini-JSON parser que PRESERVA el orden de claves ───────────────────────

#[derive(Debug, Clone)]
enum Val {
    Obj(Vec<(String, Val)>),
    Arr(Vec<Val>),
    Str(String),
    Num(String), // token crudo; float si contiene . e/E
    Bool(bool),
    Null,
}

fn parse(src: &str) -> Val {
    let b = src.as_bytes();
    let mut i = 0usize;
    let v = parse_value(src, b, &mut i);
    skip_ws(b, &mut i);
    v
}

fn skip_ws(b: &[u8], i: &mut usize) {
    while *i < b.len() && matches!(b[*i], b' ' | b'\n' | b'\t' | b'\r') {
        *i += 1;
    }
}

fn parse_value(s: &str, b: &[u8], i: &mut usize) -> Val {
    skip_ws(b, i);
    match b[*i] {
        b'{' => {
            *i += 1;
            let mut fields = Vec::new();
            skip_ws(b, i);
            if b[*i] == b'}' {
                *i += 1;
                return Val::Obj(fields);
            }
            loop {
                skip_ws(b, i);
                let key = match parse_value(s, b, i) {
                    Val::Str(k) => k,
                    _ => fail("clave no-string"),
                };
                skip_ws(b, i);
                assert_eq!(b[*i], b':');
                *i += 1;
                let val = parse_value(s, b, i);
                fields.push((key, val));
                skip_ws(b, i);
                match b[*i] {
                    b',' => {
                        *i += 1;
                    }
                    b'}' => {
                        *i += 1;
                        return Val::Obj(fields);
                    }
                    _ => fail("objeto malformado"),
                }
            }
        }
        b'[' => {
            *i += 1;
            let mut items = Vec::new();
            skip_ws(b, i);
            if b[*i] == b']' {
                *i += 1;
                return Val::Arr(items);
            }
            loop {
                let val = parse_value(s, b, i);
                items.push(val);
                skip_ws(b, i);
                match b[*i] {
                    b',' => {
                        *i += 1;
                    }
                    b']' => {
                        *i += 1;
                        return Val::Arr(items);
                    }
                    _ => fail("array malformado"),
                }
            }
        }
        b'"' => {
            // Parser de string JSON sin escapes complejos (\uXXXX soportado).
            *i += 1;
            let mut out = String::new();
            while b[*i] != b'"' {
                if b[*i] == b'\\' {
                    *i += 1;
                    match b[*i] {
                        b'n' => out.push('\n'),
                        b't' => out.push('\t'),
                        b'r' => out.push('\r'),
                        b'u' => {
                            let hex = &s[*i + 1..*i + 5];
                            let cp = u32::from_str_radix(hex, 16).unwrap();
                            out.push(char::from_u32(cp).unwrap_or('\u{fffd}'));
                            *i += 4;
                        }
                        c => out.push(c as char),
                    }
                    *i += 1;
                } else {
                    // consumir bytes UTF-8 completos
                    let start = *i;
                    let len = utf8_len(b[*i]);
                    *i += len;
                    out.push_str(&s[start..*i]);
                }
            }
            *i += 1;
            Val::Str(out)
        }
        b't' => {
            *i += 4;
            Val::Bool(true)
        }
        b'f' => {
            *i += 5;
            Val::Bool(false)
        }
        b'n' => {
            *i += 4;
            Val::Null
        }
        _ => {
            let start = *i;
            while *i < b.len() && matches!(b[*i], b'0'..=b'9' | b'-' | b'+' | b'.' | b'e' | b'E') {
                *i += 1;
            }
            Val::Num(s[start..*i].to_string())
        }
    }
}

fn utf8_len(byte: u8) -> usize {
    if byte < 0x80 {
        1
    } else if byte >> 5 == 0b110 {
        2
    } else if byte >> 4 == 0b1110 {
        3
    } else {
        4
    }
}

fn num_is_float(tok: &str) -> bool {
    tok.contains('.') || tok.contains('e') || tok.contains('E')
}

// ── normalización pactada ─────────────────────────────────────────────────

fn normalizar(v: &mut Val, root_prefix: &str) {
    match v {
        Val::Obj(fields) => {
            for (k, val) in fields.iter_mut() {
                if k == "matched_by" {
                    if let Val::Arr(items) = val {
                        let mut strs: Vec<String> = items
                            .iter()
                            .map(|x| match x {
                                Val::Str(s) => s.clone(),
                                _ => String::new(),
                            })
                            .collect();
                        strs.sort();
                        *val = Val::Arr(strs.into_iter().map(Val::Str).collect());
                    }
                }
                normalizar(val, root_prefix);
            }
        }
        Val::Arr(items) => {
            for it in items.iter_mut() {
                normalizar(it, root_prefix);
            }
        }
        Val::Str(s) => {
            if s.starts_with(root_prefix) {
                *s = format!("{{{{ROOT}}}}{}", &s[root_prefix.len()..]);
            }
        }
        Val::Num(tok) => {
            if num_is_float(tok) {
                let x: f64 = tok.parse().expect("float");
                let r = cortex_app::context::pyjson::redondear(x, 5);
                // Guardar el repr estilo Python ya formateado; se emite RAW.
                *tok = cortex_app::context::pyjson::py_float(r);
            }
        }
        Val::Bool(_) | Val::Null => {}
    }
}

fn val_to_pj(v: &Val) -> cortex_app::context::pyjson::Pj {
    use cortex_app::context::pyjson::Pj;
    match v {
        Val::Obj(fields) => Pj::Obj(
            fields
                .iter()
                .map(|(k, val)| (k.clone(), val_to_pj(val)))
                .collect(),
        ),
        Val::Arr(items) => Pj::Arr(items.iter().map(val_to_pj).collect()),
        Val::Str(s) => Pj::Str(s.clone()),
        // Tras normalizar, los floats ya traen repr Python ⇒ RAW; los ints
        // también son tokens crudos válidos.
        Val::Num(tok) => Pj::Raw(tok.clone()),
        Val::Bool(b) => Pj::Bool(*b),
        Val::Null => Pj::Null,
    }
}

fn dump(v: &Val) -> String {
    cortex_app::context::pyjson::dumps(&val_to_pj(v))
}

// ── casos espejo de CASOS en el oráculo ───────────────────────────────────

struct Caso {
    nombre: &'static str,
    work: WorkContext,
    top_k: Option<usize>,
    task_type: Option<&'static str>,
}

fn casos() -> Vec<Caso> {
    vec![
        Caso {
            nombre: "caso_a_topic",
            work: WorkContext {
                source: "manual".into(),
                search_queries: vec!["bug de autenticación en el login".into()],
                ..Default::default()
            },
            top_k: None,
            task_type: None,
        },
        Caso {
            nombre: "caso_b_multi",
            work: WorkContext {
                source: "manual".into(),
                changed_files: vec!["src/auth.py".into(), "docs/runbook-deploy.md".into()],
                keywords: vec!["autenticación".into(), "login".into(), "rollback".into()],
                function_names: vec!["authenticate_user".into()],
                class_names: vec!["FeedbackStore".into()],
                search_queries: vec![
                    "bug de autenticación en el login".into(),
                    "src auth py".into(),
                    "rollback del deploy".into(),
                    "error ValueError parser".into(),
                ],
                ..Default::default()
            },
            top_k: None,
            task_type: None,
        },
        Caso {
            nombre: "caso_c_budget_prtitle",
            work: WorkContext {
                source: "manual".into(),
                changed_files: vec!["cortex/feedback_store.py".into()],
                keywords: vec!["feedback".into(), "persistencia".into()],
                class_names: vec!["FeedbackStore".into()],
                search_queries: vec![
                    "persistencia del feedback".into(),
                    "feedback_store".into(),
                    "FeedbackStore rotación".into(),
                    "FeedbackStore persistente".into(),
                ],
                ..Default::default()
            },
            top_k: None,
            task_type: Some("deep-code"),
        },
    ]
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 {
        fail("uso: context_check <fixtures_dir> <golden_dir> <model_dir>");
    }
    // Canonicalizar antes de cualquier chdir potencial.
    let fixtures = std::fs::canonicalize(&args[1]).expect("fixtures_dir");
    let golden_dir = std::fs::canonicalize(&args[2]).expect("golden_dir");
    let model_dir = PathBuf::from(&args[3]);

    let root = fixtures.join("proyecto");
    let export = root.join("episodic_export.jsonl");
    let vault = root.join("vault");

    let store = NativeEpisodicStore::load(&export).unwrap_or_else(|e| fail(&format!("load: {e}")));
    let mut semantic =
        SemanticIndex::build(&vault).unwrap_or_else(|e| fail(&format!("vault: {e}")));
    let mut embedder =
        OnnxEmbedder::open(&model_dir).unwrap_or_else(|e| fail(&format!("embedder: {e}")));
    // Los embeddings de chunks son parte del sync() del oráculo (P2b).
    semantic
        .attach_embeddings_with(&mut embedder)
        .unwrap_or_else(|e| fail(&format!("attach_embeddings: {e}")));

    let config = ContextEnricherConfig::default();
    let max_chars = config.max_chars;
    let enricher = ContextEnricher {
        episodic: &store,
        semantic: &semantic,
        config,
    };

    let now = Utc::now();
    let root_prefix = root.to_string_lossy().to_string();

    let mut fallas = 0usize;
    for caso in casos() {
        let mut top_k = caso.top_k;
        if let Some(task) = caso.task_type {
            top_k = Some(budget_resolver::resolve_budget_profile(Some(task), None).top_k);
        }
        let bundle: EnrichedBundle = enricher.enrich(&caso.work, &mut embedder, top_k, now);
        let raw = bundle.to_json(max_chars);

        let mut parsed = parse(&raw);
        normalizar(&mut parsed, &root_prefix);
        let obtenido = dump(&parsed);

        let destino = golden_dir.join(format!("{}.json", caso.nombre));
        let esperado = std::fs::read_to_string(&destino)
            .unwrap_or_else(|e| fail(&format!("falta golden {}: {e}", destino.display())));

        // El oráculo deja UN \n final; nuestro dump no lo agrega.
        let esperado = esperado.strip_suffix('\n').unwrap_or(&esperado).to_string();
        if obtenido == esperado {
            println!("[PASS] {}", caso.nombre);
        } else {
            println!("[FAIL] {} difiere ({})", caso.nombre, destino.display());
            println!("--- esperado ---\n{esperado}\n--- obtenido ---\n{obtenido}");
            fallas += 1;
        }
    }

    if fallas == 0 {
        println!("\nPARIDAD P7 COMPLETA ✅ (bundles --json idénticos al oráculo)");
    } else {
        fail(&format!("{fallas} diferencias de paridad"));
    }
}
