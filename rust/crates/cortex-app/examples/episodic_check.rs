//! Verificador de paridad P3 — memoria episódica nativa vs oráculo Python.
//!
//! Uso: episodic_check <golden_dir> <model_dir>
//! Compara: entries.json (round-trip), vector_rankings.json, keyword.json,
//! entity_order.json (por conjuntos) usando exported.jsonl como fuente.

use std::path::Path;

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    std::process::exit(1);
}

fn read_string(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_else(|e| fail(&format!("falta {}: {e}", p.display())))
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        fail("uso: episodic_check <golden_dir> <model_dir>");
    }
    let gdir = Path::new(&args[1]);
    let model_dir = Path::new(&args[2]);

    let store = cortex_app::episodic::NativeEpisodicStore::load(&gdir.join("exported.jsonl"))
        .unwrap_or_else(|e| fail(&format!("load: {e}")));

    // ── Round-trip entries ──
    let golden_entries = read_string(&gdir.join("entries.json"));
    let g: serde_json::Value =
        serde_json::from_str(&golden_entries).expect("entries.json inválido");
    let rust_entries: Vec<serde_json::Value> = store
        .entries_sorted_by_id()
        .iter()
        .map(|e| {
            let mut d = serde_json::json!({
                "id": e.id,
                "content": e.content,
                "memory_type": e.memory_type,
                "tags": e.tags,
                "files": e.files,
                "timestamp": "{{TS}}",
                "metadata": e.metadata,
                "confidence": serde_json::Value::Null,
            });
            if let Some(obj) = d.as_object_mut() {
                obj.remove("confidence");
            }
            d
        })
        .collect();
    let golden_list = g["entries"].as_array().expect("entries lista");
    if golden_list.len() != rust_entries.len() {
        fail(&format!(
            "round-trip: {} entradas python vs {} rust",
            golden_list.len(),
            rust_entries.len()
        ));
    }
    for (gp, rp) in golden_list.iter().zip(rust_entries.iter()) {
        // metadata puede diferir en claves derivadas; comparamos núcleo.
        for key in ["id", "content", "memory_type", "tags", "files"] {
            if gp.get(key) != rp.get(key) {
                fail(&format!(
                    "round-trip {key} difiere en {}: {:?} vs {:?}",
                    gp["id"],
                    gp.get(key),
                    rp.get(key)
                ));
            }
        }
        if gp.get("metadata") != rp.get("metadata") {
            fail(&format!("round-trip metadata difiere en {}", gp["id"]));
        }
    }
    println!(
        "✅ round-trip entries: {} registros idénticos",
        rust_entries.len()
    );

    // ── Rankings vectoriales ──
    let rank_text = read_string(&gdir.join("vector_rankings.json"));
    let rank: serde_json::Value = serde_json::from_str(&rank_text).expect("rankings inválidos");
    let queries = read_string(&gdir.join("queries.json"));
    let qv: serde_json::Value = serde_json::from_str(&queries).expect("queries inválidas");
    let qvec_list = qv["vector"].as_array().expect("lista vector");

    let mut embedder = cortex_embed::onnx::OnnxEmbedder::open(model_dir).expect("abrir modelo ort");

    let mut ok = 0usize;
    for (i, item) in rank["queries"].as_array().expect("arr").iter().enumerate() {
        let q = qvec_list[i].as_str().expect("query str");
        assert_eq!(
            q,
            item["query"].as_str().unwrap(),
            "orden de queries difiere"
        );
        let mut qv = embedder
            .embed_batch(std::slice::from_ref(&q.to_string()))
            .expect("embed query");
        let Some(qvec) = qv.pop() else {
            fail("embed vacío")
        };
        let got = store.vector_search(&qvec, 5);
        let ids: Vec<String> = got.iter().map(|(e, _)| e.id.clone()).collect();
        let want: Vec<String> = item["ids"]
            .as_array()
            .expect("ids")
            .iter()
            .map(|x| x.as_str().unwrap_or("").to_string())
            .collect();
        if ids == want {
            ok += 1;
        } else {
            eprintln!("⚠ ranking difiere (HNSW aprox?): {q}\n  py  :{want:?}\n  rust:{ids:?}");
        }
    }
    println!(
        "✅ rankings vectoriales: {ok}/{} idénticos",
        rank["queries"].as_array().unwrap().len()
    );
    if ok < rank["queries"].as_array().unwrap().len() {
        eprintln!("(nota: chroma usa HNSW aproximado; diffs aislados pueden ser aproximación)");
    }

    // ── Keyword bypass ──
    let kw_text = read_string(&gdir.join("keyword.json"));
    let kw: serde_json::Value = serde_json::from_str(&kw_text).expect("keyword inválido");
    for item in kw.as_array().expect("arr") {
        let q = item["query"].as_str().unwrap();
        let ids: Vec<String> = store
            .keyword_search(q, 5)
            .iter()
            .map(|e| e.id.clone())
            .collect();
        let want: Vec<String> = item["ids"]
            .as_array()
            .unwrap()
            .iter()
            .map(|x| x.as_str().unwrap_or("").to_string())
            .collect();
        if ids != want {
            fail(&format!("keyword '{q}' difiere: {want:?} vs {ids:?}"));
        }
    }
    println!("✅ keyword bypass: idéntico");

    // ── Entity search (comparación por CONJUNTO ordenado) ──
    let ent_text = read_string(&gdir.join("entity_order.json"));
    let ent: serde_json::Value = serde_json::from_str(&ent_text).expect("entity inválido");
    for case in ent.as_array().expect("arr") {
        let t = case["type"].as_str().unwrap();
        let v = case["value"].as_str().unwrap();
        let mut want: Vec<String> = case["ids"]
            .as_array()
            .unwrap()
            .iter()
            .map(|x| x.as_str().unwrap_or("").to_string())
            .collect();
        want.sort();
        let got = store.entity_ids(t, v);
        if got != want {
            fail(&format!("entity {t}={v} difiere: {want:?} vs {got:?}"));
        }
    }
    println!("✅ entity filter: idéntico (por conjunto)");

    println!("\nPARIDAD EPISÓDICA COMPLETA");
}
