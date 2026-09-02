---
title: Embeddings Locales con ONNX Runtime
description: Cómo Cortex ejecuta inferencia vectorial 100% offline, dimensión paramétrica y zero fugas a la nube mediante cortex-embed y ort.
---

Una de las premisas fundamentales de Cortex es la **privacidad total y la independencia de APIs externas para la memoria**. Cortex integra un motor de inferencia local basado en **ONNX Runtime (`ort`)** en el crate [`cortex-embed`](file:///home/chucho/Cortex/rust/crates/cortex-embed).

---

## Modelo Predeterminado: `all-MiniLM-L6-v2`

Por defecto, Cortex utiliza el modelo de embeddings `sentence-transformers/all-MiniLM-L6-v2`:
* **Dimensión vectorial:** 384 dimensiones.
* **Tamaño del modelo:** ~80 MB en formato ONNX cuantizado.
* **Rendimiento:** ~2 a 5 ms por fragmento de texto en CPUs estándar modernas.
* **Calidad semántica:** Excelente balance entre captura conceptual y velocidad de cálculo en inglés y español técnico.

---

## Invariante Arquitectónico: Dimensión Paramétrica

En muchas implementaciones ingenuas de sistemas RAG, la dimensión del vector está *hardcodeada* como una constante (`const DIM = 384`). Cortex rechaza explícitamente este antipatrón.

En [`cortex-embed/src/lib.rs`](file:///home/chucho/Cortex/rust/crates/cortex-embed/src/lib.rs), la dimensión es **dinámicamente paramétrica**:

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EmbeddingDim(usize);

impl EmbeddingDim {
    pub fn from_model_output(last_dim: usize) -> Result<Self, String> {
        if last_dim == 0 {
            return Err("dim de embedding = 0: modelo ONNX con salida inválida".into());
        }
        Ok(Self(last_dim))
    }
}
```

Esto permite:
* Cambiar de modelo en cualquier momento (ej: a modelos de 768 o 1024 dimensiones) sin recompilar el código fuente.
* Validar que el almacén binario (`store.rs` schema v2) detecte cualquier incompatibilidad dimensional y falle de forma ruidosa y controlada antes de corromper los índices.

---

## Configuración de Modelos en `config.yaml`

El bloque de configuración de embeddings en `.cortex/config.yaml` admite personalización global o por lenguaje:

```yaml
episodic:
  embedding_model: "all-MiniLM-L6-v2"
  embedding_backend: onnx # onnx | local | openai | fastembed

embedding:
  language_detection: off # off | heuristic
  per_language:
    es:
      model: "all-MiniLM-L6-v2"
      backend: onnx
    en:
      model: "all-MiniLM-L6-v2"
      backend: onnx
```

---

## Caché Local y Descarga Automática

Cortex almacena el archivo ONNX en:
```text
$HOME/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/model.onnx
```

Si el modelo no existe localmente, el comando `cortex setup` o `cortex doctor` avisará y procederá a su descarga usando un cliente HTTP determinista, dejándolo listo para su uso sin necesidad de Python ni herramientas externas.
