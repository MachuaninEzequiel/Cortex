//! cortex-embed — wrapper de inferencia ONNX para embeddings (Obra 03).
//!
//! Rol (docs/transformacion/03 §6.1): envolver modelos ONNX con `ort`, el MISMO
//! runtime que usa la ruta Python hoy → paridad G5 trivial (cos ≥0.999).
//!
//! INVARIANTE ESTRUCTURAL: la dimensión de los embeddings es un PARÁMETRO que
//! sale del propio modelo (`output shape`), jamás una constante. El bug
//! `VECTOR_DIM=384` hardcodeado en vector_cache.py:41 queda prohibido acá.
//!
//! La implementación real (ort vs candle vs pre/post-en-Rust) se decide en
//! T-EMB-1 con spike + ADR; este esqueleto solo fija el contrato.

/// Dimensión de embedding reportada por el modelo cargado. Paramétrica por diseño.
///
/// En el esqueleto no hay modelo cargado: la API completa llega con G5.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EmbeddingDim(usize);

impl EmbeddingDim {
    /// Construye desde el shape de salida del modelo. Falla ruidosa si es inválida.
    ///
    /// ```ignore
    /// EmbeddingDim::from_model_output(shape)?  // p.ej. [batch, 384] o [batch, 1024]
    /// ```
    pub fn from_model_output(last_dim: usize) -> Result<Self, String> {
        if last_dim == 0 {
            return Err("dim de embedding = 0: modelo ONNX con salida inválida".into());
        }
        Ok(Self(last_dim))
    }

    pub fn get(self) -> usize {
        self.0
    }
}

#[cfg(test)]
mod tests {
    use super::EmbeddingDim;

    #[test]
    fn smoke_dim_parametrica_acepta_cualquier_valor_no_cero() {
        // La lección de vector_cache.py:41: NINGUNA dim es "la correcta".
        for dim in [384usize, 768, 1024] {
            assert_eq!(EmbeddingDim::from_model_output(dim).unwrap().get(), dim);
        }
    }

    #[test]
    fn smoke_dim_cero_falla_ruidosa() {
        assert!(EmbeddingDim::from_model_output(0).is_err());
    }
}
