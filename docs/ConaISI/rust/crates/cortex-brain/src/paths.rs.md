# rust/crates/cortex-brain/src/paths.rs

## Qué tiene adentro

Convenciones de rutas del modelo, independientes del feature `llama`:

- `DEFAULT_MODEL_FILENAME` = `LFM2.5-1.2B-Instruct-Q4_K_M.gguf`
- `default_model_dir()` = `$HOME/.cache/cortex/models`
- `default_model_path()`, `default_model_path_if_exists()`
- `sha_sidecar_path()` = dir + `.sha256`
- `lockfile_path()` = dir + `.lock`
- `partial_dir()` = dir + `.partial`

Sin `XDG_CACHE_HOME` ni `~/Library/Caches` en v1.

## Para qué sirve

Que el binario, `download`, Tauri y Companion acuerden el mismo path sin compilar llama.cpp.

## Relaciones

### Recibe de

- env `HOME`

### Envía a

- `download.rs`, `llama.rs` (`model_path_default`), `cortex-brain-app` (list_models/download), tests

### Notas de implementación observadas en el código

`lockfile_path` y `partial_dir` se exponen; `download` escribe `.partial.<filename>` al lado del dest, no necesariamente en `partial_dir()`.
