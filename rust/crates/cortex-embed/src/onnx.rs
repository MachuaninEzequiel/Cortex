//! Embedder ONNX productivo (Gate G5-integración) — all-MiniLM-L6-v2 sobre
//! los MISMOS artefactos que cachea chromadb (`model.onnx` + `tokenizer.json`).
//!
//! Pipeline idéntico a `chromadb.utils.embedding_functions.ONNXMiniLM_L6_V2`
//! (ver ADR-EMBEDDINGS.md):
//! 1. Tokenización HF (misma crate oficial) con truncation 256 — chroma fija
//!    padding a 256; acá el padding es DINÁMICO al máximo del lote: las
//!    posiciones enmascaradas no aportan al mean-pooling, así que el resultado
//!    es idéntico (verificado cos=1.00000000 vs OnnxEmbedder) y ~2× más barato.
//! 2. Inferencia ort (misma librería C++ onnxruntime, optimización Level3 ==
//!    ORT_ENABLE_ALL).
//! 3. Mean-pooling con attention mask + L2 (guards 1e-9 / 1e-12 como chroma).
//!
//! dim SIEMPRE sale del modelo (paramétrica, jamás constante).

use std::path::Path;

use tokenizers::Tokenizer;

/// Límite de chroma/sentence-transformers para MiniLM ("usa 256 aunque la
/// config del HF diga 128").
const MAX_SEQ: usize = 256;
/// Tamaño de sub-lote interno (igual al batch_size default de chroma).
const CHUNK: usize = 32;

/// Embedder ONNX thread-unsafe por diseño: el binding lo envuelve en un Mutex
/// y Python lo usa como singleton class-level.
pub struct OnnxEmbedder {
    tokenizer: Tokenizer,
    session: ort::session::Session,
    /// Dimensión reportada por el modelo tras la primera inferencia.
    dim: Option<usize>,
}

impl OnnxEmbedder {
    /// Abre `model_dir/tokenizer.json` + `model_dir/model.onnx` (layout chroma).
    pub fn open(model_dir: &Path) -> Result<Self, String> {
        Self::open_with_threads(model_dir, None)
    }

    /// `intra_threads`: hilos intra-op de ORT. Para queries de 1 secuencia los
    /// pools grandes PENALIZAN (coordinación > cómputo); None = default ORT.
    pub fn open_with_threads(
        model_dir: &Path,
        intra_threads: Option<usize>,
    ) -> Result<Self, String> {
        let tokenizer_path = model_dir.join("tokenizer.json");
        let model_path = model_dir.join("model.onnx");
        let mut tokenizer =
            Tokenizer::from_file(&tokenizer_path).map_err(|e| format!("tokenizer: {e}"))?;
        // Igual que chroma: Right/LongestFirst/stride 0 con max 256.
        let trunc = tokenizers::TruncationParams {
            direction: tokenizers::TruncationDirection::Right,
            max_length: MAX_SEQ,
            strategy: tokenizers::TruncationStrategy::LongestFirst,
            stride: 0,
        };
        tokenizer
            .with_truncation(Some(trunc))
            .map_err(|e| format!("truncation: {e}"))?;
        // Padding dinámico por lote: se resuelve en embed_batch según max_len.

        let mut builder = ort::session::builder::SessionBuilder::new()
            .map_err(|e| format!("session builder: {e}"))?
            .with_optimization_level(ort::session::builder::GraphOptimizationLevel::Level3)
            .map_err(|e| format!("optimization: {e}"))?;
        if let Some(t) = intra_threads {
            builder = builder
                .with_intra_threads(t)
                .map_err(|e| format!("intra_threads: {e}"))?;
        }
        let session = builder
            .commit_from_file(&model_path)
            .map_err(|e| format!("modelo onnx: {e}"))?;

        Ok(Self {
            tokenizer,
            session,
            dim: None,
        })
    }

    pub fn dim(&self) -> Option<usize> {
        self.dim
    }

    /// Embeddings de un lote. Textos vacíos son responsabilidad del caller
    /// (el wrapper Python valida antes, paridad con ValueError de chroma-path).
    pub fn embed_batch(&mut self, texts: &[String]) -> Result<Vec<Vec<f64>>, String> {
        if texts.is_empty() {
            return Ok(Vec::new());
        }
        let mut out = Vec::with_capacity(texts.len());
        for chunk in texts.chunks(CHUNK) {
            out.extend(self.embed_chunk(chunk)?);
        }
        Ok(out)
    }

    fn embed_chunk(&mut self, chunk: &[String]) -> Result<Vec<Vec<f64>>, String> {
        let encodings = self
            .tokenizer
            .encode_batch(chunk.to_vec(), true)
            .map_err(|e| format!("encode: {e}"))?;
        let batch = encodings.len();
        let width = encodings
            .iter()
            .map(|e| e.get_ids().len())
            .max()
            .unwrap_or(0)
            .max(1);

        let mut input_ids = Vec::with_capacity(batch * width);
        let mut attention_mask = Vec::with_capacity(batch * width);
        let mut token_type_ids = Vec::with_capacity(batch * width);
        for enc in &encodings {
            let ids = enc.get_ids();
            let mask = enc.get_attention_mask();
            let type_ids = enc.get_type_ids();
            for k in 0..width {
                let within = k < ids.len();
                input_ids.push(if within { ids[k] as i64 } else { 0 });
                attention_mask.push(if within && k < mask.len() {
                    mask[k] as i64
                } else {
                    0
                });
                token_type_ids.push(if within && k < type_ids.len() {
                    type_ids[k] as i64
                } else {
                    0
                });
            }
        }

        let outputs = self
            .session
            .run(
                ort::inputs![
                    "input_ids" => ort::value::Tensor::from_array(([batch as i64, width as i64], input_ids.clone())).map_err(|e| e.to_string())?,
                    "attention_mask" => ort::value::Tensor::from_array(([batch as i64, width as i64], attention_mask.clone())).map_err(|e| e.to_string())?,
                    "token_type_ids" => ort::value::Tensor::from_array(([batch as i64, width as i64], token_type_ids.clone())).map_err(|e| e.to_string())?,
                ],
            )
            .map_err(|e| format!("inferencia: {e}"))?;

        let (shape, data) = outputs[0]
            .try_extract_tensor::<f32>()
            .map_err(|e| format!("salida: {e}"))?;
        let dims: Vec<usize> = shape.iter().map(|&d| d as usize).collect();
        if dims.len() != 3 || dims[0] != batch {
            return Err(format!("shape de salida inesperada: {dims:?}"));
        }
        let seq = dims[1];
        let dim = dims[2];
        if self.dim.is_none() {
            self.dim = Some(dim);
        }

        // Mean-pooling con máscara + L2 (chroma: clip denom 1e-9, norm guard).
        let mut pooled = Vec::with_capacity(batch);
        for i in 0..batch {
            let mut acc = vec![0f64; dim];
            let mut denom = 0f64;
            for t in 0..seq {
                let m = attention_mask[i * width + t] as f64;
                if m == 0.0 {
                    continue;
                }
                denom += m;
                let base = i * seq * dim + t * dim;
                for d in 0..dim {
                    acc[d] += data[base + d] as f64 * m;
                }
            }
            let denom = denom.max(1e-9);
            for v in &mut acc {
                *v /= denom;
            }
            let norm = acc.iter().map(|v| v * v).sum::<f64>().sqrt().max(1e-12);
            for v in &mut acc {
                *v /= norm;
            }
            pooled.push(acc);
        }
        Ok(pooled)
    }
}
