# rust/crates/cortex-brain/src/llama.rs

## Qué tiene adentro

Backend `LlamaChatBackend` (solo con feature `llama`):

- Carga GGUF con `llama-cpp-2` (`LlamaBackend`, `LlamaModel`)
- Chat template **del propio GGUF** (`model.chat_template`, jinja de llama.cpp)
- Historial `Vec<LlamaChatMessage>`
- `with_temp` / `with_seed`
- Contexto `N_CTX = 4096`, `MAX_GEN_TOKENS = 512`
- `generate_raw`: tokeniza prompt, decode, loop hasta EOS/max/ctx
  - temp=0: greedy (max logit)
  - temp>0: chain temp + top_k(40) + dist(seed)
- Streaming: cada piece UTF-8 (`encoding_rs`) sale por callback
- `turn`: push user (mensaje + bloque `[Herramientas disponibles]`), generate, push assistant
- `model_path_default()` delega a `paths::default_model_path` (deprecado)

Implementa `LlmBackend` (`name` = `"llama.cpp (GGUF)"`).

## Para qué sirve

Generación real local LFM2.5 Instruct Q4_K_M. El chat template no está hardcodeado.

## Relaciones

### Recibe de

- archivo GGUF en disco
- `crate::chat::LlmBackend`
- `crate::paths`
- system prompt opcional (catálogo + reglas “propone, no ejecuta”)

### Envía a

- texto/stream al loop de chat
- historial interno en RAM (se pierde al drop)

### Notas de implementación observadas en el código

`_backend` debe vivir más que modelo/contexto (requisito de la crate). Prompt demasiado largo respecto de `N_CTX - max_tokens` falla ruidoso.
