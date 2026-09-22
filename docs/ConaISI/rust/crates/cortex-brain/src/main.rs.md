# rust/crates/cortex-brain/src/main.rs

## Qué tiene adentro

Binario interactivo. Parsea flags:

- `--project-root`, `--model` / `--no-model`, `--temp`, `--seed`, `--window`, `-h/--help`

Flujo `main`:

1. `chdir` al project-root si se pasó.
2. `i18n::detectar` (`CORTEX_LANG` > `.cortex/config.yaml` > `config.yaml` > `es`) y `fijar`.
3. Si `--window`: relanza argv vía `window::launch_window` y sale.
4. Imprime `banner()` (ancho visible ≤ 80, assert).
5. Elige backend: con feature llama + `--model` + GGUF existente → `LlamaChatBackend`; si falla o falta → `DeterministicBackend`.
6. Loop stdin: `backend.generate` → `procesar_respuesta_modelo` con confirmación `[s/N]`.
7. `/quit` (router slash) o generate `"/quit"` termina.

`confirmar_ejecucion` imprime sugerencia i18n, lee stdin y llama `chat::confirma`. `catalogo_tools` arma el texto de tools para el prompt LLM.

## Para qué sirve

Chat de terminal del experto local. Default: cero tokens. Nunca muta: propone comando y pide confirmación antes de despachar tools.

## Relaciones

### Recibe de

- `chat` (backends, protocolo TOOL, banner, help)
- `i18n`, `router`, `tools`, `window`, `llama` (cfg)
- stdin del usuario, args, cwd, archivos de config

### Envía a

- stdout/stderr
- `tools::dispatch` (tras aprobación)
- `window::launch_window` (proceso de terminal)

### Notas de implementación observadas en el código

El system prompt del modo llama exige responder únicamente `TOOL: <nombre> <args>` cuando necesita datos. Temp default 0 (greedy), seed 42.
