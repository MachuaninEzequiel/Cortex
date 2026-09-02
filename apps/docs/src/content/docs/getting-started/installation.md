---
title: Instalación y Requisitos
description: Requisitos del sistema, métodos de instalación de cortex-cli y configuración de modelos de inferencia local.
---

Cortex está construido en Rust y se distribuye como un binario nativo independiente o compilable desde el código fuente.

---

## Requisitos del Sistema

* **Sistema Operativo:** Linux (x86_64, aarch64), macOS (Apple Silicon / Intel), Windows (WSL2 o nativo).
* **Compilador Rust:** Rust 1.80 o superior (edición 2021).
* **Almacenamiento:** ~150 MB para el modelo ONNX local y cache de embeddings.
* **Memoria RAM:** Mínimo 512 MB disponibles para inferencia de embeddings en CPU.

---

## Métodos de Instalación

### Opción A: Compilación desde el Código Fuente (Recomendado para desarrollo)

Clone el repositorio de Cortex y compile el binario optimizado con `cargo`:

```bash
git clone https://github.com/MachuaninEzequiel/Cortex.git
cd Cortex/rust
cargo install --path crates/cortex-cli
```

Esto instalará el ejecutable `cortex-cli` (y su alias `cortex`) en `$HOME/.cargo/bin`. Asegúrese de tener este directorio en su variable `PATH`:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
```

### Opción B: Build de Release Local

Si prefiere compilar un binario de producción sin instalarlo globalmente:

```bash
cd Cortex/rust
cargo build --release --bin cortex-cli
```

El ejecutable resultante estará ubicado en:
`Cortex/rust/target/release/cortex-cli`

---

## Modelo de Inferencia ONNX Local

Cortex utiliza el crate [`cortex-embed`](file:///home/chucho/Cortex/rust/crates/cortex-embed) junto con `ort` (ONNX Runtime) para generar embeddings vectoriales de forma 100% offline y privada.

Por defecto, Cortex busca el modelo `all-MiniLM-L6-v2` en el directorio de caché estándar:

```text
$HOME/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/model.onnx
```

Si el modelo no se encuentra presente, Cortex puede descargarlo automáticamente durante la ejecución del asistente inicial o al invocar:

```bash
cortex setup --profile agent
```

---

## Verificación de la Instalación

Compruebe que el binario responde correctamente:

```bash
cortex --version
# cortex-cli 0.1.0
```

Y ejecute el verificador de salud general:

```bash
cortex doctor
```

Si todos los checks indican `[OK]`, Cortex está listo para operar en su entorno.
