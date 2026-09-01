//! Runner de ranking BM25 para paridad P2a (espejo de VaultReader._bm25_search).
//!
//! Uso: bm25_search <vault> <queries.jsonl> <top_k> <limit>
//! Emite JSON: {"queries":[{"query":…,"paths":[rel,…]},…]} — paths en el
//! ORDEN del ranking, que es lo que compara el harness.

use std::io::BufRead;

fn main() -> Result<(), String> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 5 {
        return Err("uso: bm25_search <vault> <queries.jsonl> <top_k> <limit>".into());
    }
    let vault = std::path::Path::new(&args[1]);
    let queries_path = &args[2];
    let top_k: usize = args[3].parse().map_err(|e| format!("top_k: {e}"))?;
    let limit: usize = args[4].parse().map_err(|e| format!("limit: {e}"))?;

    let index = cortex_app::semantic::SemanticIndex::build(vault)?;

    let f = std::fs::File::open(queries_path).map_err(|e| e.to_string())?;
    let reader = std::io::BufReader::new(f);
    let mut out = String::from("{\"queries\":[");
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
        let query = v["query"]
            .as_str()
            .ok_or("query sin campo 'query'")?
            .to_string();

        let hits = index.bm25_search(&query, top_k);
        if n > 0 {
            out.push(',');
        }
        out.push_str(&format!(
            "{{\"query\":{},\"paths\":[",
            serde_json::to_string(&query).unwrap()
        ));
        for (i, (doc, _score)) in hits.iter().enumerate() {
            if i > 0 {
                out.push(',');
            }
            // Python golden emite rel_paths (path relativo al vault).
            out.push_str(&serde_json::to_string(&doc.rel).unwrap());
        }
        out.push_str("]}");
        n += 1;
    }
    out.push_str("]}\n");
    print!("{out}");
    Ok(())
}
