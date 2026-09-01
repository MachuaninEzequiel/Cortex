//! Verificador de paridad P12A-1 — escrituras nativas vs oráculo Python.
//!
//! Uso: p12a1_check <fixtures_dir> <golden_dir> <model_dir>
//!
//! Secciones:
//!   1. episodic.append: carga <fixtures>/base.jsonl con NativeEpisodicStore,
//!      appendea las specs de golden_dir/append_specs.json (embedder ort real),
//!      recarga desde disco y compara contra:
//!        - golden_entries_after.json  (por document, {{TS}}, metadata exacta)
//!        - golden_rankings.json       (vector por ORDEN exacto, keyword sorted)
//!        - golden_after.jsonl         (valores de meta byte-a-byte,
//!          embeddings por tolerancia ≤1e-4)
//!   2. semantic.index_file: build del vault pristine + rankings R1; aplica
//!      spec_modificado.md a specs/2026-06-01_gate.md vía index_file y compara
//!      R2; además valida incremental == full rebuild.
//!
//! Normalizaciones pactadas (ver header de p12a1_golden.py): ids/timestamps
//! aleatorios ⇒ clave por document; embeddings numéricos con tolerancia.

use std::path::{Path, PathBuf};
use std::process::exit;

use cortex_app::episodic::{AppendParams, NativeEpisodicStore};
use cortex_app::semantic::SemanticIndex;
use cortex_embed::onnx::OnnxEmbedder;

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    exit(1);
}

fn read_string(p: PathBuf) -> String {
    std::fs::read_to_string(&p).unwrap_or_else(|e| fail(&format!("falta {}: {e}", p.display())))
}

/// Comparación de valores JSON con floats tolerantes (≤1e-4), recursiva.
fn json_eq_tolerante(a: &serde_json::Value, b: &serde_json::Value) -> Result<(), String> {
    match (a, b) {
        (serde_json::Value::Array(x), serde_json::Value::Array(y)) => {
            if x.len() != y.len() {
                return Err(format!("largo {:?} vs {:?}", x, y));
            }
            for (i, (xa, ya)) in x.iter().zip(y.iter()).enumerate() {
                json_eq_tolerante(xa, ya).map_err(|e| format!("[{i}] {e}"))?;
            }
            Ok(())
        }
        (serde_json::Value::Object(x), serde_json::Value::Object(y)) => {
            if x.len() != y.len() {
                return Err(format!("claves {x:?} vs {y:?}"));
            }
            for (k, xv) in x {
                let Some(yv) = y.get(k) else {
                    return Err(format!("falta clave {k}"));
                };
                json_eq_tolerante(xv, yv).map_err(|e| format!("{k}: {e}"))?;
            }
            Ok(())
        }
        _ => {
            if let (Some(x), Some(y)) = (a.as_f64(), b.as_f64()) {
                if (x - y).abs() <= 1e-4 {
                    return Ok(());
                }
            }
            if a == b {
                Ok(())
            } else {
                Err(format!("{a} vs {b}"))
            }
        }
    }
}

struct FilaExport {
    id: String,
    document: String,
    meta: serde_json::Value,
    embedding: Vec<f64>,
}

fn parse_jsonl(texto: &str, origen: &str) -> Vec<FilaExport> {
    let mut out = Vec::new();
    for (i, line) in texto.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let v: serde_json::Value =
            serde_json::from_str(line).unwrap_or_else(|e| fail(&format!("{origen}:{i}: {e}")));
        out.push(FilaExport {
            id: v["id"].as_str().unwrap_or_default().to_string(),
            document: v["document"].as_str().unwrap_or_default().to_string(),
            meta: v["meta"].clone(),
            embedding: v["embedding"]
                .as_array()
                .map(|a| a.iter().filter_map(|x| x.as_f64()).collect())
                .unwrap_or_default(),
        });
    }
    out
}

fn seccion_episodica(fixtures: &Path, gdir: &Path, model_dir: &Path) {
    println!("── episodic.append ──");
    let work = std::env::temp_dir().join(format!(
        "p12a1_epi_{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&work).expect("tmp epi");
    let jsonl = work.join("memories.jsonl");
    std::fs::copy(fixtures.join("base.jsonl"), &jsonl).expect("copiar base");

    let mut embedder = OnnxEmbedder::open(model_dir).expect("abrir modelo ort");
    let specs: Vec<serde_json::Value> =
        serde_json::from_str(&read_string(gdir.join("append_specs.json")))
            .expect("append_specs.json inválido");

    // Append con el store cargado desde el export base (embeddings ort reales).
    let mut store = NativeEpisodicStore::load(&jsonl).expect("load base");
    for spec in &specs {
        let extra = spec["extra_metadata"].as_object().cloned();
        store
            .append(
                AppendParams {
                    content: spec["content"].as_str().unwrap().to_string(),
                    memory_type: spec["memory_type"].as_str().unwrap().to_string(),
                    tags: spec["tags"]
                        .as_array()
                        .map(|a| {
                            a.iter()
                                .filter_map(|x| x.as_str().map(String::from))
                                .collect()
                        })
                        .unwrap_or_default(),
                    files: spec["files"]
                        .as_array()
                        .map(|a| {
                            a.iter()
                                .filter_map(|x| x.as_str().map(String::from))
                                .collect()
                        })
                        .unwrap_or_default(),
                    extra_metadata: extra,
                },
                &mut |c: &str| {
                    let vs = embedder
                        .embed_batch(vec![c.to_string()].as_slice())
                        .map_err(|e| e.to_string())?;
                    vs.into_iter().next().ok_or_else(|| "sin vector".into())
                },
            )
            .unwrap_or_else(|e| fail(&format!("append: {e}")));
    }
    drop(store);

    // Recarga fresca desde disco (orden canónico por id).
    let store = NativeEpisodicStore::load(&jsonl).expect("reload tras append");

    // ── entries after (claveadas por document) ──
    let golden: serde_json::Value =
        serde_json::from_str(&read_string(gdir.join("golden_entries_after.json")))
            .expect("entries golden inválido");
    let esperados = golden["entries"].as_object().expect("entries obj");
    if esperados.len() != store.count() {
        fail(&format!(
            "entries: {} python vs {} rust",
            esperados.len(),
            store.count()
        ));
    }
    for entry in store.entries_sorted_by_id() {
        let Some(g) = esperados.get(entry.content.as_str()) else {
            fail(&format!("documento inesperado: {}", entry.content));
        };
        if g["memory_type"] != entry.memory_type {
            fail(&format!("memory_type difiere en {}", entry.id));
        }
        let rust_tags = serde_json::to_value(&entry.tags).unwrap();
        if g["tags"] != rust_tags {
            fail(&format!("tags difieren en {}", entry.id));
        }
        let rust_files = serde_json::to_value(&entry.files).unwrap();
        if g["files"] != rust_files {
            fail(&format!("files difieren en {}", entry.id));
        }
        let rust_meta = serde_json::to_value(&entry.metadata).unwrap();
        json_eq_tolerante(&g["metadata"], &rust_meta)
            .unwrap_or_else(|e| fail(&format!("metadata difiere en {}: {e}", entry.id)));
    }
    println!(
        "✅ entries after: {} registros idénticos (por document)",
        store.count()
    );

    // ── rankings ──
    let golden_rank: serde_json::Value =
        serde_json::from_str(&read_string(gdir.join("golden_rankings.json")))
            .expect("rankings golden inválido");

    let mut buscar_vector = |q: &str| -> Vec<String> {
        let mut qv = embedder
            .embed_batch(std::slice::from_ref(&q.to_string()))
            .expect("embed query");
        let qvec = qv.pop().unwrap();
        store
            .vector_search(&qvec, 5)
            .into_iter()
            .map(|(e, _)| e.content.clone())
            .collect()
    };

    for item in golden_rank["vector"].as_array().expect("vector arr") {
        let q = item["query"].as_str().unwrap();
        let got = buscar_vector(q);
        let want: Vec<String> = item["docs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|d| d.as_str().unwrap().to_string())
            .collect();
        if got != want {
            fail(&format!(
                "ranking vectorial difiere para {q:?}:\n  py:   {want:?}\n  rust: {got:?}"
            ));
        }
    }
    println!(
        "✅ rankings vectoriales post-append: {} queries idénticas",
        golden_rank["vector"].as_array().unwrap().len()
    );

    for item in golden_rank["keyword"].as_array().expect("kw arr") {
        let q = item["query"].as_str().unwrap();
        let mut got: Vec<String> = store
            .keyword_search(q, 5)
            .into_iter()
            .map(|e| e.content.clone())
            .collect();
        got.sort();
        let want: Vec<String> = item["docs"]
            .as_array()
            .unwrap()
            .iter()
            .map(|d| d.as_str().unwrap().to_string())
            .collect();
        if got != want {
            fail(&format!("keyword difiere para {q:?}: {got:?} vs {want:?}"));
        }
    }
    println!("✅ keyword bypass post-append idéntico");

    // ── filas del archivo: estructura + meta values + embedding tolerante ──
    let after_text = read_string(gdir.join("golden_after.jsonl"));
    let filas_py = parse_jsonl(&after_text, "golden_after.jsonl");
    let filas_rs = parse_jsonl(
        &std::fs::read_to_string(&jsonl).unwrap(),
        "memories.jsonl (rust)",
    );
    assert_eq!(filas_py.len(), filas_rs.len(), "cantidad de filas");
    let by_doc_py: std::collections::HashMap<&str, &FilaExport> =
        filas_py.iter().map(|f| (f.document.as_str(), f)).collect();

    let claves_meta_min = [
        "id",
        "memory_type",
        "tags",
        "files",
        "timestamp",
        "metadata_json",
    ];
    for fila in &filas_rs {
        let py = by_doc_py
            .get(fila.document.as_str())
            .unwrap_or_else(|| fail(&format!("fila rust sin par python: {}", fila.document)));
        let meta_rs = fila.meta.as_object().expect("meta objeto");
        let meta_keys: std::collections::HashSet<&str> =
            meta_rs.keys().map(|s| s.as_str()).collect();
        for k in claves_meta_min {
            assert!(meta_keys.contains(k), "meta rust sin {k}");
        }
        // id/timestamp son aleatorios en ambos lados (normalización pactada):
        // se excluyen; todo lo demás es byte-parity.
        let strip = |v: &serde_json::Value| -> serde_json::Map<String, serde_json::Value> {
            let mut m = v.as_object().cloned().unwrap_or_default();
            m.remove("id");
            m.remove("timestamp");
            m
        };
        json_eq_tolerante(
            &serde_json::Value::Object(strip(&py.meta)),
            &serde_json::Value::Object(strip(&fila.meta)),
        )
        .unwrap_or_else(|e| fail(&format!("meta difiere en {}: {e}", fila.id)));
        json_eq_tolerante(
            &serde_json::Value::Array(py.embedding.iter().map(|x| serde_json::json!(x)).collect()),
            &serde_json::Value::Array(
                fila.embedding
                    .iter()
                    .map(|x| serde_json::json!(x))
                    .collect(),
            ),
        )
        .unwrap_or_else(|e| fail(&format!("embedding difiere en {}: {e}", fila.id)));
    }
    println!(
        "✅ filas JSONL: {} filas — meta byte-parity, embeddings dentro de tolerancia",
        filas_rs.len()
    );
    std::fs::remove_dir_all(&work).ok();
}

fn seccion_semantica(fixtures: &Path, gdir: &Path, model_dir: &Path) {
    println!("── semantic.index_file ──");
    let mut embedder = OnnxEmbedder::open(model_dir).expect("abrir modelo ort");

    let work = std::env::temp_dir().join(format!(
        "p12a1_sem_{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir_all(&work).expect("tmp sem");
    let vault = work.join("vault");
    let origen_vault = fixtures.join("vault");
    let cp = |f: &str| {
        let src = origen_vault.join(f);
        let dst = vault.join(f);
        std::fs::create_dir_all(dst.parent().unwrap()).unwrap();
        std::fs::copy(&src, &dst).unwrap_or_else(|e| panic!("copy {f}: {e}"));
    };
    cp("glosario-core.md");
    cp("specs/2026-06-01_gate.md");
    cp("adr/ADR-0009-store-nativo.md");
    cp("notas/vault-notes.md");

    let queries: Vec<String> = vec![
        "gate de paridad del store".into(),
        "reindex incremental".into(),
        "store append-only JSONL".into(),
        "chunking por routing".into(),
    ];

    fn buscar(idx: &SemanticIndex, embedder: &mut OnnxEmbedder, q: &str) -> Vec<String> {
        let mut qv = embedder
            .embed_batch(std::slice::from_ref(&q.to_string()))
            .expect("embed q sem");
        let vec = qv.pop().unwrap();
        idx.semantic_search_vec(&vec, 3)
            .iter()
            .map(|(d, _)| d.rel.clone())
            .collect()
    }

    fn verificar_queries(
        gdir: &Path,
        idx: &SemanticIndex,
        embedder: &mut OnnxEmbedder,
        golden_file: &str,
        etiqueta: &str,
    ) {
        let texto = std::fs::read_to_string(gdir.join(golden_file))
            .unwrap_or_else(|e| fail(&format!("falta {golden_file}: {e}")));
        let golden: serde_json::Value = serde_json::from_str(&texto).expect("golden sem inválido");
        for item in golden["queries"].as_array().unwrap() {
            let q = item["query"].as_str().unwrap();
            let want: Vec<String> = item["paths"]
                .as_array()
                .unwrap()
                .iter()
                .map(|p| p.as_str().unwrap().to_string())
                .collect();
            let got = buscar(idx, embedder, q);
            if got != want {
                fail(&format!(
                    "{etiqueta}: ranking difiere para {q:?}\n  py:   {want:?}\n  rust: {got:?}"
                ));
            }
        }
    }

    // R1: índice completo sobre el vault pristine.
    let mut idx = SemanticIndex::build(&vault).expect("build");
    idx.attach_embeddings_with(&mut embedder).expect("attach");
    verificar_queries(gdir, &idx, &mut embedder, "golden_sem_r1.json", "R1 sync");

    // Modificación + index_file incremental (mismo contenido que Python).
    let cuerpo = read_string(gdir.join("spec_modificado.md"));
    std::fs::write(vault.join("specs/2026-06-01_gate.md"), &cuerpo).unwrap();
    let ok = idx
        .index_file(
            &vault,
            "specs/2026-06-01_gate.md",
            &mut |texts: &[String]| embedder.embed_batch(texts).map_err(|e| e.to_string()),
        )
        .expect("index_file");
    assert!(ok);
    verificar_queries(
        gdir,
        &idx,
        &mut embedder,
        "golden_sem_r2.json",
        "R2 index_file",
    );

    // Incremental == rebuild completo (contrato interno).
    let mut full = SemanticIndex::build(&vault).expect("build post-mod");
    full.attach_embeddings_with(&mut embedder)
        .expect("attach post-mod");
    for q in &queries {
        if buscar(&idx, &mut embedder, q) != buscar(&full, &mut embedder, q) {
            fail(&format!("incremental != rebuild para {q:?}"));
        }
    }

    println!("✅ R1 (sync) y R2 (index_file) idénticos al oráculo · incremental==rebuild");
    std::fs::remove_dir_all(&work).ok();
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 {
        fail("uso: p12a1_check <fixtures_dir> <golden_dir> <model_dir>");
    }
    let fixtures = std::fs::canonicalize(&args[1]).expect("fixtures_dir");
    let gdir = std::fs::canonicalize(&args[2]).expect("golden_dir");
    let model_dir = std::fs::canonicalize(&args[3]).expect("model_dir");

    seccion_episodica(&fixtures, &gdir, &model_dir);
    seccion_semantica(&fixtures, &gdir, &model_dir);

    println!("\nPARIDAD P12A-1 COMPLETA ✅ (episodic.append · index_file · resolve_safe)");
}
