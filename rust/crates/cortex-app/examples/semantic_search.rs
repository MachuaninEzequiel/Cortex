//! Runner de ranking semántico para paridad P2b.
//!
//! Uso: semantic_search <vault> <model_dir> <queries.jsonl> <top_k> <limit>

fn main() -> Result<(), String> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 6 {
        return Err(
            "uso: semantic_search <vault> <model_dir> <queries.jsonl> <top_k> <limit>".into(),
        );
    }
    let vault = std::path::Path::new(&args[1]);
    let model_dir = std::path::Path::new(&args[2]);
    let queries_path = &args[3];
    let top_k: usize = args[4].parse().map_err(|e| format!("top_k: {e}"))?;
    let limit: usize = args[5].parse().map_err(|e| format!("limit: {e}"))?;

    let mut index = cortex_app::semantic::SemanticIndex::build(vault)?;
    let mut embedder = cortex_embed::onnx::OnnxEmbedder::open(model_dir)?;
    index.attach_embeddings_with(&mut embedder)?;

    use std::io::BufRead;
    let f = std::fs::File::open(queries_path).map_err(|e| e.to_string())?;
    let reader = std::io::BufReader::new(f);
    let mut out = String::from("{\"modo\":\"hibrido\",\"queries\":[");
    let mut n = 0usize;
    for line in reader.lines() {
        if n >= limit {
            break;
        }
        let line = line.map_err(|e| e.to_string())?;
        if line.trim().is_empty() {
            continue;
        }
        let v: serde_json::Value = serde_json::from_str(&line).map_err(|e| e.to_string())?;
        let query = v["query"].as_str().ok_or("sin 'query'")?.to_string();
        let hits = index.semantic_search(&query, top_k, &mut embedder);
        if n > 0 {
            out.push(',');
        }
        out.push_str(&format!(
            "{{\"query\":{},\"paths\":[",
            serde_json::to_string(&query).unwrap()
        ));
        for (i, (doc, _)) in hits.iter().enumerate() {
            if i > 0 {
                out.push(',');
            }
            out.push_str(&serde_json::to_string(&doc.rel).unwrap());
        }
        out.push_str("]}");
        n += 1;
    }
    out.push_str("]}\n");
    print!("{out}");
    Ok(())
}
