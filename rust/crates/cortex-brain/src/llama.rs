//! Backend llama.cpp/GGUF (BRAIN-2) — LFM2.5-1.2B-Instruct Q4_K_M.
//!
//! Runtime: llama.cpp vía `llama-cpp-2` (decisión vigente del dueño:
//! runtime llama.cpp/GGUF, implementación Rust nativa). El chat template
//! se toma DEL GGUF y se aplica con el motor jinja de llama.cpp — nada
//! hardcodeado.
//!
//! Muestreo greedy determinista (v1); temperature/samplers quedan para
//! el pulido de BRAIN-3.

use std::path::{Path, PathBuf};

use llama_cpp_2::context::params::LlamaContextParams;
use llama_cpp_2::context::LlamaContext;
use llama_cpp_2::llama_backend::LlamaBackend;
use llama_cpp_2::llama_batch::LlamaBatch;
use llama_cpp_2::model::{AddBos, LlamaChatMessage, LlamaChatTemplate, LlamaModel};
use llama_cpp_2::token::data::LlamaTokenData;
use llama_cpp_2::token::LlamaToken;

use crate::chat::LlmBackend;

const N_CTX: u32 = 4096;
const MAX_GEN_TOKENS: usize = 512;

/// Ruta default del GGUF (`~/.cache/cortex/models/LFM2.5-1.2B-Instruct-Q4_K_M.gguf`).
///
/// **DEPRECADO desde C-L1.1:** delegar en [`crate::paths::default_model_path`].
/// Se conserva para no romper callers existentes (binario, tests); se
/// elimina cuando se migren.
#[must_use]
pub fn model_path_default() -> PathBuf {
    crate::paths::default_model_path()
}

/// Backend de chat sobre un GGUF ya descargado.
pub struct LlamaChatBackend {
    /// Debe vivir más que modelo/contexto (requerimiento de la crate).
    _backend: LlamaBackend,
    model: LlamaModel,
    template: LlamaChatTemplate,
    history: Vec<LlamaChatMessage>,
    /// Temperatura de muestreo; 0 = greedy determinista (default v1).
    temp: f32,
    /// Semilla para el muestreo estocástico (sólo si temp > 0).
    seed: u32,
}

impl LlamaChatBackend {
    /// Fija temperatura (>0 activa muestreo estocástico con dist).
    pub fn with_temp(mut self, temp: f32) -> Self {
        self.temp = temp;
        self
    }

    /// Fija semilla del muestreo estocástico.
    pub fn with_seed(mut self, seed: u32) -> Self {
        self.seed = seed;
        self
    }
}

impl LlamaChatBackend {
    /// Carga el GGUF. `system` es el prompt de sistema con el catálogo de
    /// herramientas y las reglas ("propone, no ejecuta").
    pub fn open(model_path: &Path, system: Option<&str>) -> Result<Self, String> {
        let backend = LlamaBackend::init().map_err(|e| format!("backend: {e}"))?;
        let model =
            LlamaModel::load_from_file(&backend, model_path, &Default::default()).map_err(|e| {
                format!(
                    "carga del GGUF falló (¿arquitectura soportada por esta versión de llama.cpp?): {e}"
                )
            })?;

        let template = model
            .chat_template(None)
            .map_err(|e| format!("el GGUF no trae chat template: {e}"))?;

        let mut this = Self {
            _backend: backend,
            model,
            template,
            history: Vec::new(),
            temp: 0.0,
            seed: 42,
        };
        if let Some(sys) = system {
            this.history.push(
                LlamaChatMessage::new("system".into(), sys.to_string())
                    .map_err(|e| format!("mensaje sistema: {e}"))?,
            );
        }
        Ok(this)
    }

    fn ctx(&self) -> Result<LlamaContext<'_>, String> {
        self.model
            .new_context(
                &self._backend,
                LlamaContextParams::default()
                    .with_n_ctx(Some(std::num::NonZeroU32::new(N_CTX).expect("n_ctx > 0"))),
            )
            .map_err(|e| format!("contexto: {e}"))
    }

    /// Prompt formateado con el template embebido en el GGUF + historial.
    fn prompt(&self) -> Result<String, String> {
        self.model
            .apply_chat_template(&self.template, &self.history, true)
            .map_err(|e| format!("chat template: {e}"))
    }

    /// Convierte un token a texto (incluye especiales para ver EOS/etc).
    fn piece(&self, tok: LlamaToken) -> String {
        let mut decoder = encoding_rs::UTF_8.new_decoder();
        self.model
            .token_to_piece(tok, &mut decoder, true, None)
            .unwrap_or_default()
    }

    /// Genera hasta EOS/max tokens/fin de contexto. Greedy determinista.
    /// `on_piece` recibe cada fragmento a medida que se genera (streaming).
    fn generate_raw(
        &mut self,
        prompt: &str,
        max_tokens: usize,
        mut on_piece: impl FnMut(&str),
    ) -> Result<String, String> {
        let mut ctx = self.ctx()?;
        let eos = self.model.token_eos();

        let tokens = self
            .model
            .str_to_token(prompt, AddBos::Never)
            .map_err(|e| format!("tokenización del prompt: {e}"))?;
        if tokens.is_empty() {
            return Err(String::from("prompt tokenizó a vacío"));
        }
        #[allow(
            clippy::cast_possible_truncation,
            clippy::cast_sign_loss,
            clippy::cast_possible_wrap
        )]
        let limite_prompt = (N_CTX - max_tokens as u32) as usize;
        if tokens.len() > limite_prompt {
            return Err(format!(
                "prompt demasiado largo: {} tokens (límite {})",
                tokens.len(),
                limite_prompt
            ));
        }

        // Sampler: greedy (determinista, default) o temp+top_k+dist si temp>0.
        let mut sampler = if self.temp > 0.0 {
            Some(llama_cpp_2::sampling::LlamaSampler::chain_simple([
                llama_cpp_2::sampling::LlamaSampler::temp(self.temp),
                llama_cpp_2::sampling::LlamaSampler::top_k(40),
                llama_cpp_2::sampling::LlamaSampler::dist(self.seed),
            ]))
        } else {
            None
        };
        let mut generados: Vec<String> = Vec::with_capacity(max_tokens);
        let mut batch = LlamaBatch::new(tokens.len().max(8), 0);
        for (i, t) in tokens.iter().enumerate() {
            let last = i + 1 == tokens.len();
            batch
                .add(*t, i as i32, &[0], last)
                .map_err(|e| format!("batch: {e}"))?;
        }
        ctx.decode(&mut batch)
            .map_err(|e| format!("decode del prompt: {e}"))?;

        let mut pos = tokens.len() as i32;
        while generados.len() < max_tokens && pos < N_CTX as i32 - 1 {
            // Greedy (temp=0) o muestreo temp+top_k+dist (temp>0).
            let tok: LlamaToken = if self.temp > 0.0 {
                let s = sampler.as_mut().expect("sampler activo si temp > 0");
                s.sample(&ctx, pos - 1)
            } else {
                let mejor: Option<LlamaTokenData> = ctx
                    .candidates()
                    .max_by(|a, b| a.logit().total_cmp(&b.logit()));
                match mejor {
                    Some(m) => m.id(),
                    None => return Err(String::from("sin logits")),
                }
            };
            if tok == eos {
                break;
            }
            let piece = self.piece(tok);
            on_piece(&piece);
            generados.push(piece);

            batch.clear();
            batch
                .add(tok, pos, &[0], true)
                .map_err(|e| format!("batch de generación: {e}"))?;
            pos += 1;
            ctx.decode(&mut batch)
                .map_err(|e| format!("decode incremental: {e}"))?;
        }
        Ok(generados.concat())
    }

    /// Una llamada de generación sobre la conversación actual.
    fn complete_turn(&mut self) -> Result<String, String> {
        let prompt = self.prompt()?;
        self.generate_raw(&prompt, MAX_GEN_TOKENS, |_| {})
    }
}

impl LlmBackend for LlamaChatBackend {
    fn name(&self) -> &str {
        "llama.cpp (GGUF)"
    }

    fn generate(&mut self, user_msg: &str, tools_help: &str) -> Result<String, String> {
        let contenido = if tools_help.is_empty() {
            user_msg.to_string()
        } else {
            format!("{user_msg}\n\n[Herramientas disponibles]\n{tools_help}")
        };
        self.history.push(
            LlamaChatMessage::new("user".into(), contenido)
                .map_err(|e| format!("mensaje usuario: {e}"))?,
        );
        let respuesta = self.complete_turn()?;
        self.history.push(
            LlamaChatMessage::new("assistant".into(), respuesta.clone())
                .map_err(|e| format!("mensaje assistant: {e}"))?,
        );
        Ok(respuesta)
    }
}
