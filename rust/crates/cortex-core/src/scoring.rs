//! Scoring vectorial batch (Gate G1) — paridad bit-a-bit con la ruta Python.
//!
//! La referencia es `VaultReader._cosine_similarity` (vault_reader.py):
//!
//! ```python
//! dot = sum(x * y for x, y in zip(a, b))
//! norm_a = math.sqrt(sum(x * x for x in a))
//! norm_b = math.sqrt(sum(x * x for x in b))
//! if norm_a == 0 or norm_b == 0: return 0.0
//! return dot / (norm_a * norm_b)
//! ```
//!
//! DECISIÓN DE PARIDAD (regla dura R5.2: resultado distinto = gate inválido):
//! - Acumulación **f64 con suma compensada de Neumaier**: CPython ≥3.12 usa
//!   ese mismo algoritmo en el builtin ``sum()`` para floats (verificado
//!   empíricamente 0/40000 discrepancias vs acumulador ingenuo 11549/20000).
//!   Sumar ingenuo en Rust NO es bit-exacto contra Python moderno.
//! - `f64::sqrt` es IEEE correctly-rounded igual que `math.sqrt`.
//! - Se RECHAZA f32/SIMD en este gate: cambiaría los bits de los scores y
//!   podría voltear empates del top-k. Un salto a f32+SIMD exige su propio
//!   ADR con re-validación de paridad sobre queries-synth.
//!
//! Supuesto documentado: componentes finitos (embeddings reales). CPython
//! lanza OverflowError ante ±inf intermedio en sum(); acá se propaga inf
//! IEEE sin error — irrelevante para vectores de embeddings válidos.
//!
//! Con f64 escalar release ya se supera holgadamente el gate G1 (≥5× p99):
//! el coste dominante era el intérprete (~1M ops de bytecode), no el FLOP.

use std::fmt;

/// Errores de validación del scoring batch. Falla RUIDOSA, jamás truncar
/// silenciosamente como `zip(strict=False)` de Python.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ScoringError {
    /// `dim == 0`: la dimensión SIEMPRE es un parámetro válido > 0.
    EmptyDim,
    /// El query no coincide con la dim de la matriz.
    DimMismatch { query_len: usize, dim: usize },
    /// La matriz plana no es un múltiplo exacto de `dim`.
    MatrixNotMultiple { matrix_len: usize, dim: usize },
}

impl fmt::Display for ScoringError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyDim => write!(
                f,
                "dim=0 inválida: la dimensión es parámetro y debe ser > 0"
            ),
            Self::DimMismatch { query_len, dim } => {
                write!(f, "query len={query_len} != dim={dim} de la matriz")
            }
            Self::MatrixNotMultiple { matrix_len, dim } => {
                write!(f, "matriz len={matrix_len} no es múltiplo de dim={dim}")
            }
        }
    }
}

impl std::error::Error for ScoringError {}

/// Suma compensada de Neumaier — replica el builtin ``sum()`` de CPython ≥3.12
/// para floats, bit a bit, en el mismo orden izquierda→derecha.
///
/// El término inicial 0 de Python equivale a arrancar con `s = 0.0`: agregar
/// un 0.0 primero deja `s = x`, `c += x - x = 0` (idempotente).
fn sum_neumaier(items: impl Iterator<Item = f64>) -> f64 {
    let mut s = 0.0f64;
    let mut c = 0.0f64;
    for x in items {
        let t = s + x;
        if s.abs() >= x.abs() {
            c += (s - t) + x;
        } else {
            c += (x - t) + s;
        }
        s = t;
    }
    s + c
}

/// Cosine batch: 1 query × N filas → N scores.
///
/// * `query`  — vector de dimensión `dim`.
/// * `matrix` — matriz fila-major aplanada (`n_rows × dim`, contigua).
/// * `dim`    — dimensión paramétrica (jamás constante).
///
/// API GRUESA: una llamada procesa TODAS las filas (el loop-per-item mata el
/// win de FFI). Los ceros-vector producen score `0.0` exactamente como Python.
pub fn cosine_scores(query: &[f64], matrix: &[f64], dim: usize) -> Result<Vec<f64>, ScoringError> {
    if dim == 0 {
        return Err(ScoringError::EmptyDim);
    }
    if query.len() != dim {
        return Err(ScoringError::DimMismatch {
            query_len: query.len(),
            dim,
        });
    }
    if !matrix.len().is_multiple_of(dim) {
        return Err(ScoringError::MatrixNotMultiple {
            matrix_len: matrix.len(),
            dim,
        });
    }

    // Misma expresión y orden que Python: sqrt(sum(x*x)) — sum() es Neumaier.
    let norm_a = f64::sqrt(sum_neumaier(query.iter().map(|x| x * x)));

    let mut out = Vec::with_capacity(matrix.len() / dim);
    for row in matrix.chunks_exact(dim) {
        // dot: zip(query, row) en orden índice 0..dim, suma Neumaier (=sum()).
        let dot = sum_neumaier(query.iter().zip(row).map(|(a, b)| a * b));
        let norm_b = f64::sqrt(sum_neumaier(row.iter().map(|x| x * x)));
        if norm_a == 0.0 || norm_b == 0.0 {
            out.push(0.0);
            continue;
        }
        out.push(dot / (norm_a * norm_b));
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Réplica EXACTA del código Python de referencia (sum() = Neumaier en CPython ≥3.12).
    fn python_reference(a: &[f64], b: &[f64]) -> f64 {
        let dot: f64 = sum_neumaier(a.iter().zip(b).map(|(x, y)| x * y));
        let norm_a = f64::sqrt(sum_neumaier(a.iter().map(|x| x * x)));
        let norm_b = f64::sqrt(sum_neumaier(b.iter().map(|x| x * x)));
        if norm_a == 0.0 || norm_b == 0.0 {
            return 0.0;
        }
        dot / (norm_a * norm_b)
    }

    #[test]
    fn ortogonales_paralelos_ortogonales_cero() {
        let q = [1.0, 0.0];
        // filas: paralelo, ortogonal, vector cero
        let m = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0];
        let scores = cosine_scores(&q, &m, 2).unwrap();
        assert_eq!(scores[0], 1.0);
        assert_eq!(scores[1], 0.0);
        assert_eq!(scores[2], 0.0); // vector cero → 0.0 como Python
    }

    #[test]
    fn dim_parametrica_dim3_y_dim8() {
        // La dim JAMÁS es constante: misma función sirve para MiniLM(384),
        // e5-large(1024) o cualquier modelo futuro.
        let q: Vec<f64> = (0..3).map(|i| i as f64 + 1.0).collect();
        let m: Vec<f64> = (0..6).map(|i| i as f64 * 0.5).collect();
        assert_eq!(cosine_scores(&q, &m, 3).unwrap().len(), 2);

        let q8: Vec<f64> = (1..=8).map(|i| i as f64).collect();
        let m8: Vec<f64> = (0..16).map(|i| (i % 8) as f64 + 0.25).collect();
        assert_eq!(cosine_scores(&q8, &m8, 8).unwrap().len(), 2);
    }

    #[test]
    fn paridad_bitexacta_contra_python_en_vetores_reales() {
        // Vectores pseudoaleatorios deterministas (LCG simple, sin deps).
        let mut state: u64 = 42;
        let mut next = || {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            ((state >> 11) as f64) / ((1u64 << 53) as f64) - 0.5
        };
        let dim = 384usize;
        let n_rows = 50;
        let query: Vec<f64> = (0..dim).map(|_| next()).collect();
        let matrix: Vec<f64> = (0..n_rows * dim).map(|_| next()).collect();

        let scores = cosine_scores(&query, &matrix, dim).unwrap();
        for (row_idx, score) in scores.iter().enumerate() {
            let row = &matrix[row_idx * dim..(row_idx + 1) * dim];
            // Paridad BIT A BIT: == estricto, no aproximado.
            assert_eq!(*score, python_reference(&query, row), "fila {row_idx}");
        }
    }

    #[test]
    fn falla_ruidosa_en_malas_dimensiones() {
        assert_eq!(cosine_scores(&[], &[1.0], 0), Err(ScoringError::EmptyDim));
        assert_eq!(
            cosine_scores(&[1.0, 2.0], &[1.0, 2.0, 3.0, 4.0], 3),
            Err(ScoringError::DimMismatch {
                query_len: 2,
                dim: 3
            })
        );
        assert_eq!(
            cosine_scores(&[1.0, 2.0, 3.0], &[1.0, 2.0, 3.0, 4.0], 3),
            Err(ScoringError::MatrixNotMultiple {
                matrix_len: 4,
                dim: 3
            })
        );
    }

    #[test]
    fn matriz_vacia_devuelve_vacio() {
        let scores = cosine_scores(&[1.0, 2.0], &[], 2).unwrap();
        assert!(scores.is_empty());
    }
}
