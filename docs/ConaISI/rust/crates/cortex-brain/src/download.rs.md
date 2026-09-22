# rust/crates/cortex-brain/src/download.rs

## Qué tiene adentro

Descarga/copia de GGUF:

- `DownloadResult { path, bytes }`, `DownloadProgress { bytes_done, bytes_total }`
- `DownloadError`: Empty, Io, Http, NotImplemented
- Trait `ModelSource::fetch(dest, on_progress)`
- `LocalSource`: copia local con chunks 64 KiB, escribe `.partial.<nombre>` junto al dest y `rename` atómico; 0 bytes → Empty y borra partial
- `HttpSource`: GET con `ureq` a HuggingFace por default (`LiquidAI/LFM2.5-1.2B-Instruct-GGUF` + `paths::DEFAULT_MODEL_FILENAME`); mismo esquema partial+rename; intenta sidecar `.sha256` vía `paths::sha_sidecar_path()`
- `DEFAULT_REPO`, `default_url()`, `default_sha256_url()`, `HttpSource::with_url`

## Para qué sirve

Instalar el modelo local sin acoplarse a llama.cpp. Tests usan `LocalSource`; la app Tauri usa `HttpSource` en `download_model`.

## Relaciones

### Recibe de

- `crate::paths` (filename, sidecar)
- filesystem local o HTTP (`ureq`)
- callback opcional de progreso

### Envía a

- archivo GGUF en `dest`
- sidecar sha256 en `paths::sha_sidecar_path()`
- `DownloadProgress` a callers (`cortex-brain-app` emite evento Tauri)

### Notas de implementación observadas en el código

El `.partial` va en el mismo filesystem que el destino para que `rename` no falle con EXDEV. Comentarios C-L1.2/C-L1.3 quedan desfasados: `HttpSource::fetch` ya está implementado (tests con mock TCP).
