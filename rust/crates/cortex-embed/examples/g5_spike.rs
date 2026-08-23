//! Spike G5 (T-EMB-1): inferencia all-MiniLM-L6-v2 con `ort` + tokenizador HF
//! oficial sobre los MISMOS artefactos que usa chromadb en Python.
//!
//! Uso:
//!   cargo run -p cortex-embed --features onnx --example g5_spike -- \
//!       <model.onnx> <tokenizer.json> <texts.json>
//!
//! texts.json: array JSON de strings (mismos textos que la referencia Python
//! de bench/g5_reference.py). Imprime dim + vector por texto para comparar
//! coseno bit a bit contra Python.

use std::time::Instant;

use ort::session::{builder::GraphOptimizationLevel, Session};
use tokenizers::Tokenizer;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let model_path = args.next().expect("falta ruta del model.onnx");
    let tokenizer_path = args.next().expect("falta ruta del tokenizer.json");
    let texts_path = args.next().expect("falta ruta del texts.json");

    let texts: Vec<String> = serde_json::from_str(&std::fs::read_to_string(&texts_path)?)?;
    println!("textos: {}", texts.len());

    // ── Tokenización (HF tokenizers sobre el MISMO tokenizer.json) ──
    let tok = Tokenizer::from_file(&tokenizer_path).map_err(|e| format!("tokenizer: {e}"))?;
    let t_tok = Instant::now();
    let encodings = tok
        .encode_batch(texts.clone(), true)
        .map_err(|e| format!("encode: {e}"))?;
    let tok_ms = t_tok.elapsed().as_secs_f64() * 1000.0;
    let max_len = encodings.iter().map(|e| e.get_ids().len()).max().unwrap_or(0);
    println!(
        "tokenización: {tok_ms:.1}ms · max_len={max_len} · padding dinámico por batch"
    );
    if std::env::var("G5_DEBUG").is_ok() {
        let e0 = &encodings[0];
        println!("DEBUG ids[0..12]={:?} mask={:?}", &e0.get_ids()[..12.min(e0.get_ids().len())], &e0.get_attention_mask()[..12.min(e0.get_attention_mask().len())]);
        println!("DEBUG len_ids={} type_ids[:6]={:?}", e0.get_ids().len(), &e0.get_type_ids()[..6.min(e0.get_type_ids().len())]);
    }

    // ── Sesión ONNX ──
    let t_load = Instant::now();
    let mut session = Session::builder()?
        .with_optimization_level(GraphOptimizationLevel::Level3)?
        .commit_from_file(&model_path)?;
    let load_ms = t_load.elapsed().as_secs_f64() * 1000.0;
    println!(
        "sesión onnxruntime cargada en {load_ms:.1}ms · entradas={:?}",
        session.inputs().iter().map(|i| i.name().to_string()).collect::<Vec<_>>()
    );

    // Padding dinámico a max_len del batch (igual que chroma: pad fijo 128 —
    // probamos ambos y reportamos).
    let batch = encodings.len();
    let width = max_len;

    let mut input_ids = Vec::with_capacity(batch * width);
    let mut attention_mask = Vec::with_capacity(batch * width);
    let mut token_type_ids = Vec::with_capacity(batch * width);
    for enc in &encodings {
        let ids = enc.get_ids();
        let mask = enc.get_attention_mask();
        let type_ids = enc.get_type_ids();
        for k in 0..width {
            let within = k < ids.len();
            // El modelo ONNX declara entradas int64 (tensor(int64)).
            input_ids.push(if within { ids[k] as i64 } else { 0 });
            attention_mask.push(if within && k < mask.len() { mask[k] as i64 } else { 0 });
            token_type_ids.push(if within && k < type_ids.len() { type_ids[k] as i64 } else { 0 });
        }
    }

    let attention_mask_for_pool = attention_mask.clone();
    let t_inf = Instant::now();
    let outputs = session.run(ort::inputs![
        "input_ids" => ort::value::Tensor::from_array(([batch as i64, width as i64], input_ids))?,
        "attention_mask" => ort::value::Tensor::from_array(([batch as i64, width as i64], attention_mask))?,
        "token_type_ids" => ort::value::Tensor::from_array(([batch as i64, width as i64], token_type_ids))?,
    ])?;
    let inf_ms = t_inf.elapsed().as_secs_f64() * 1000.0;

    let (shape, data) = outputs[0].try_extract_tensor::<f32>()?;
    let attention_mask = &attention_mask_for_pool;
    if std::env::var("G5_DEBUG").is_ok() {
        let seq_w = width;
        let head: Vec<f32> = data[384..388].to_vec(); // flat = [doc0][token1][dim0..4]
        println!("DEBUG hidden[0][1][0..4]={head:?}");
    }
    let dims: Vec<usize> = shape.iter().map(|&d| d as usize).collect();
    println!(
        "inferencia: {inf_ms:.1}ms · salida shape={dims:?}"
    );

    // El modelo emite tokens (batch × seq × hidden): MEAN POOLING con máscara
    // + L2 normalize — idéntico a ONNXMiniLM_L6_V2 de chroma.
    let batch_n = dims[0];
    let seq = dims[1];
    let dim = dims[2];
    let mut vectors: Vec<Vec<f64>> = Vec::with_capacity(batch_n);
    for i in 0..batch_n {
        let mut acc = vec![0f64; dim];
        let mut denom = 0f64;
        for t in 0..seq {
            let m = attention_mask[i * seq + t] as f64;
            if m == 0.0 {
                continue;
            }
            denom += m;
            for d in 0..dim {
                acc[d] += data[i * seq * dim + t * dim + d] as f64 * m;
            }
        }
        if denom < 1e-9 {
            denom = 1e-9;
        }
        for d in &mut acc {
            *d /= denom;
        }
        let norm = acc.iter().map(|v| v * v).sum::<f64>().sqrt();
        for d in &mut acc {
            *d /= norm;
        }
        vectors.push(acc);
    }
    println!("mean-pooling + L2: listo");
    // Volcar vectores POOLEADOS para comparación exacta desde Python.
    let out_path = std::env::var("G5_OUT").unwrap_or_else(|_| "/tmp/g5_rust.json".into());
    std::fs::write(&out_path, serde_json::to_string(&vectors)?)?;
    println!("vectores → {out_path}");
    Ok(())
}
