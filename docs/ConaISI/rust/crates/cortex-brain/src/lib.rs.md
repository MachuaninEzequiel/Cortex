# rust/crates/cortex-brain/src/lib.rs

## Qué tiene adentro

Raíz de la librería. Declara módulos públicos:

- `chat`, `download`, `paths`, `i18n`, `router`, `tools`, `window`
- `llama` solo con `#[cfg(feature = "llama")]`

El docstring de crate describe el estado: router 1:1 con Python, tools READ/SAFE_ACTION, protocolo TOOL testeable, i18n ES/EN, samplers temp/seed, ventana multiplataforma. Backend real: llama.cpp/GGUF LFM2.5 con `--features llama`.

## Para qué sirve

Punto de entrada de la API que reutilizan el binario, Tauri (`cortex-brain-app`) y Companion. Permite usar el motor sin abrir el CLI interactivo.

## Relaciones

### Recibe de

- Nada externo en este archivo (solo `mod`).

### Envía a

- Expone los módulos a `main.rs`, `cortex-brain-app::chat`, `cortex-companion::brain_panel`.

### Notas de implementación observadas en el código

`llama` no se compila sin feature: `paths` y `download` viven fuera de ese módulo para que `cortex brain install` no requiera cmake.
