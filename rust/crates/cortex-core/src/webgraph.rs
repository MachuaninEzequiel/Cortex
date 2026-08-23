//! Vecinos semánticos del webgraph (Gate G4) — réplica EXACTA de
//! `RelationBuilder._add_semantic_neighbors`.
//!
//! Semántica replicada (bit a bit):
//! - Coseno idéntico al de scoring: suma compensada de Neumaier (= `sum()` de
//!   CPython ≥3.12), normas sobre el vector COMPLETO y dot truncado a
//!   `min(len)` (`zip(strict=False)`), 0.0 si falta/vacío/norma cero.
//! - Pasada 1: pares i<j en orden de índice; `score >= threshold` se queda
//!   (Python hace `if score < threshold: continue`).
//! - Ranking por nodo: `sorted(neighbors, reverse=True)` sobre tuplas
//!   `(score, node_id)` ⇒ score DESC y node_id DESC en empates.
//! - allowed_pairs con `(min(id), max(id))` por orden lexicográfico
//!   (UTF-8 bytes == orden de code points).
//! - Pasada 2: emisión en el MISMO orden de loops anidados que Python
//!   (i externo, j interno, condición `ids[i] < ids[j]`), re-computando el
//!   coseno (determinista ⇒ mismos bits).
//!
//! La paralelización con rayon es POR PAR i<j en la pasada 1 (el O(n²) real);
//! cada comparación es independiente y la emisión final respeta el orden.

use rayon::prelude::*;
use std::cmp::Ordering;
use std::collections::HashMap;

/// Suma compensada de Neumaier — réplica del builtin `sum()` de CPython ≥3.12.
/// (misma implementación que cortex_core::scoring; duplicada aquí para mantener
/// cortex-core sin dependencias internas entre módulos de dominio.)
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

/// Coseno con la semántica exacta de `_cosine_similarity` del relation builder:
/// dot truncado a min(len) (zip strict=False), normas completas, 0.0 defensivo.
fn cosine_truncated(a: &[f64], b: &[f64]) -> f64 {
    let dot = sum_neumaier(a.iter().zip(b).map(|(x, y)| x * y));
    let norm_a = f64::sqrt(sum_neumaier(a.iter().map(|x| x * x)));
    let norm_b = f64::sqrt(sum_neumaier(b.iter().map(|y| y * y)));
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    dot / (norm_a * norm_b)
}

/// Calcula los pares `semantic_neighbor` a emitir, EN EL ORDEN de emisión de
/// Python. Devuelve `(índice_i, índice_j, score)` con `ids[i] < ids[j]`.
///
/// * `embeddings[i] == None` equivale a registro sin embedding (todo 0.0).
pub fn semantic_neighbor_pairs(
    ids: &[String],
    embeddings: &[Option<Vec<f64>>],
    threshold: f64,
    max_edges_per_node: usize,
) -> Vec<(usize, usize, f64)> {
    let n = ids.len();
    debug_assert_eq!(n, embeddings.len());
    if n < 2 || max_edges_per_node == 0 {
        return Vec::new();
    }

    // Normas precalculadas (los vectores son constantes durante el build;
    // Python recalcula norm_a por par — mismo valor, sin efecto en los bits).
    let norms: Vec<Option<f64>> = embeddings
        .iter()
        .map(|emb| {
            emb.as_ref()
                .filter(|v| !v.is_empty())
                .map(|v| f64::sqrt(sum_neumaier(v.iter().map(|x| x * x))))
        })
        .collect();

    // ── Pasada 1: vecinos por par i<j, en paralelo por fila i ──
    // neighbors_by_node[i] = lista de (score, other_index)
    let neighbors_per_row: Vec<Vec<(f64, u32)>> = (0..n)
        .into_par_iter()
        .map(|i| {
            let mut local: Vec<(f64, u32)> = Vec::new();
            let Some(emb_i) = embeddings[i].as_ref() else {
                return local;
            };
            let empty = Vec::new();
            for j in (i + 1)..n {
                // Mitad superior: (score, j) para el nodo i…
                let emb_j = embeddings[j].as_ref().unwrap_or(&empty);
                let score = if norms[i].unwrap_or(0.0) == 0.0 || norms[j].unwrap_or(0.0) == 0.0 {
                    0.0
                } else {
                    cosine_truncated(emb_i, emb_j)
                };
                if score >= threshold {
                    local.push((score, j as u32));
                }
            }
            local
        })
        .collect();

    // Reconstruir ambas direcciones como el defaultdict de Python:
    // neighbors[node] = [(score, other_node_id)] para TODA relación detectada.
    let mut neighbors_by_node: HashMap<usize, Vec<(f64, u32)>> = HashMap::new();
    for (i, row) in neighbors_per_row.iter().enumerate() {
        for &(score, j) in row {
            neighbors_by_node.entry(i).or_default().push((score, j));
            neighbors_by_node
                .entry(j as usize)
                .or_default()
                .push((score, i as u32));
        }
    }

    // ── Ranking por nodo + allowed_pairs ──
    // Python: sorted(neighbors, reverse=True)[:max] sobre tuplas (score,
    // node_id) ⇒ score DESC, y en empate node_id DESC. Aquí trabajamos por
    // índice pero comparamos los IDs reales para respetar ese desempate.
    let mut allowed_pairs: std::collections::HashSet<(u32, u32)> = std::collections::HashSet::new();
    for (_node, neighbors) in neighbors_by_node.iter() {
        let mut ranked = neighbors.clone();
        ranked.sort_by(|a, b| {
            b.0.total_cmp(&a.0) // score DESC (total_cmp: determinista)
                .then_with(|| ids[b.1 as usize].cmp(&ids[a.1 as usize])) // id DESC
        });
        for &(_, other) in ranked.iter().take(max_edges_per_node) {
            let a_idx = *_node as u32;
            let b_idx = other;
            let key = if ids[a_idx as usize] <= ids[b_idx as usize] {
                (a_idx, b_idx)
            } else {
                (b_idx, a_idx)
            };
            allowed_pairs.insert(key);
        }
    }

    // ── Pasada 2: emisión en el orden de loops anidados de Python ──
    let mut out = Vec::new();
    for i in 0..n {
        for j in 0..n {
            if ids[i] >= ids[j] {
                continue;
            }
            // Par canónico por orden de STRING (== code points):
            let canon = if ids[i] <= ids[j] {
                (i as u32, j as u32)
            } else {
                (j as u32, i as u32)
            };
            if !allowed_pairs.contains(&canon) {
                continue;
            }
            let Some(emb_i) = embeddings[i].as_ref() else {
                continue;
            };
            let Some(emb_j) = embeddings[j].as_ref() else {
                continue;
            };
            let score = cosine_truncated(emb_i, emb_j);
            if score < threshold {
                continue;
            }
            out.push((i, j, score));
        }
    }
    out
}

/// Edge final construido (campos idénticos a WebGraphEdge de Python).
#[derive(Debug, Clone, PartialEq)]
pub struct BuiltEdge {
    pub id: String,
    pub source: String,
    pub target: String,
    pub edge_type: String,
    pub weight: f64,
    pub evidence: Vec<String>,
}

/// Acumulador con la semántica EXACTA de `RelationBuilder._add_edge`:
/// key canónica ((type,source,target) en direccionales; (type,min,max) en el
/// resto, orden de STRING), id/source/target de la PRIMERA inserción,
/// evidence deduplicada preservando primeras apariciones
/// (= list(dict.fromkeys(old + new))), weight = max(existing, new).
struct EdgeAccumulator {
    index: HashMap<(String, String, String), usize>,
    edges: Vec<BuiltEdge>,
}

impl EdgeAccumulator {
    fn new() -> Self {
        Self {
            index: HashMap::new(),
            edges: Vec::new(),
        }
    }

    fn add(
        &mut self,
        source: &str,
        target: &str,
        edge_type: &str,
        evidence: &[String],
        weight: f64,
    ) {
        if source == target {
            return;
        }
        let directional = matches!(edge_type, "wikilink" | "supersedes" | "superseded_by");
        let key = if directional {
            (
                edge_type.to_string(),
                source.to_string(),
                target.to_string(),
            )
        } else {
            let (lo, hi) = if source <= target {
                (source.to_string(), target.to_string())
            } else {
                (target.to_string(), source.to_string())
            };
            (edge_type.to_string(), lo, hi)
        };
        match self.index.get(&key) {
            Some(&slot) => {
                let e = &mut self.edges[slot];
                for ev in evidence {
                    if !e.evidence.contains(ev) {
                        e.evidence.push(ev.clone());
                    }
                }
                if weight > e.weight {
                    e.weight = weight;
                }
            }
            None => {
                self.index.insert(key, self.edges.len());
                self.edges.push(BuiltEdge {
                    id: format!("{edge_type}:{source}:{target}"),
                    source: source.to_string(),
                    target: target.to_string(),
                    edge_type: edge_type.to_string(),
                    weight,
                    evidence: evidence.to_vec(),
                });
            }
        }
    }
}

fn interseccion_ordenada(a: &[String], b: &[String]) -> Vec<String> {
    // Ambas vienen ordenadas (byte-order UTF-8 == orden code points de Python
    // para sorted(set)); merge-style: misma intersección y mismo orden.
    let mut out = Vec::new();
    let (mut i, mut j) = (0usize, 0usize);
    while i < a.len() && j < b.len() {
        match a[i].cmp(&b[j]) {
            Ordering::Equal => {
                out.push(a[i].clone());
                i += 1;
                j += 1;
            }
            Ordering::Less => i += 1,
            Ordering::Greater => j += 1,
        }
    }
    out
}

/// Escaneo cross-source COMPLETO (Gate G4): genera los edges finales con la
/// semántica exacta de `_add_cross_source_edges`, incluyendo same_file_reference
/// intercalado ANTES de los pares de cada episódico y el merge/dedupe de
/// `_add_edge`. Orden de inserción == orden del dict Python.
///
/// Paralelizado con rayon POR EPISÓDICO (collect preserva orden); el merge
/// secuencial posterior replica la secuencia exacta de llamadas de Python.
///
/// * `epi_files_targets[e]`: pares (file_ref_original, node_id_destino) ya
///   resueltos contra semantic_by_path (los no resueltos van fuera).
#[allow(clippy::too_many_arguments)] // datos paralelos por registro; agruparlos
                                     // obligaría a clonar sin beneficio.
pub fn cross_source_build(
    epi_ids: &[String],
    epi_files_targets: &[Vec<(String, String)>],
    epi_tags: &[Vec<String>],
    epi_entities: &[Vec<String>],
    epi_tokens: &[Vec<String>],
    sem_ids: &[String],
    sem_tags: &[Vec<String>],
    sem_entities: &[Vec<String>],
    sem_tokens: &[Vec<String>],
    sem_is_spec: &[bool],
) -> Vec<BuiltEdge> {
    let n_epi = epi_ids.len();
    debug_assert_eq!(n_epi, epi_files_targets.len());
    debug_assert_eq!(n_epi, epi_tags.len());

    // Fase rayon: specs crudos por episódico (en orden de llamada Python).
    let per_epi: Vec<Vec<(&str, String, String, f64)>> = (0..n_epi)
        .into_par_iter()
        .map(|e| {
            let mut calls: Vec<(&str, String, String, f64)> = Vec::new();
            for s in 0..sem_ids.len() {
                let shared_tags = interseccion_ordenada(&epi_tags[e], &sem_tags[s]);
                if !shared_tags.is_empty() {
                    calls.push((
                        "shared_tag",
                        sem_ids[s].clone(),
                        shared_tags
                            .into_iter()
                            .take(3)
                            .collect::<Vec<_>>()
                            .join("\u{1}"),
                        1.0,
                    ));
                }
                let shared_entities = interseccion_ordenada(&epi_entities[e], &sem_entities[s]);
                if !shared_entities.is_empty() {
                    calls.push((
                        "shared_entity",
                        sem_ids[s].clone(),
                        shared_entities
                            .into_iter()
                            .take(4)
                            .collect::<Vec<_>>()
                            .join("\u{1}"),
                        1.1,
                    ));
                }
                if !sem_is_spec[s] {
                    continue;
                }
                let overlap = interseccion_ordenada(&epi_tokens[e], &sem_tokens[s]);
                if overlap.len() >= 3 {
                    calls.push((
                        "same_spec_reference",
                        sem_ids[s].clone(),
                        overlap
                            .into_iter()
                            .take(4)
                            .collect::<Vec<_>>()
                            .join("\u{1}"),
                        1.2,
                    ));
                }
            }
            calls
        })
        .collect();

    // Merge secuencial (orden exacto de _add_edge de Python).
    let mut acc = EdgeAccumulator::new();
    for (e, calls) in per_epi.iter().enumerate() {
        for (file_ref, target_id) in &epi_files_targets[e] {
            acc.add(
                &epi_ids[e],
                target_id,
                "same_file_reference",
                std::slice::from_ref(file_ref),
                1.3,
            );
        }
        for (edge_type, target_id, joined, weight) in calls {
            let evidence: Vec<String> = joined.split('\u{1}').map(str::to_string).collect();
            acc.add(&epi_ids[e], target_id, edge_type, &evidence, *weight);
        }
    }
    acc.edges
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ids(n: usize) -> Vec<String> {
        (0..n).map(|i| format!("node-{i:02}")).collect()
    }

    #[test]
    fn pares_ortogonales_y_umbral_incluye_igualdad() {
        let idsv = ids(2);
        let embs = vec![Some(vec![1.0, 0.0]), Some(vec![1.0, 0.0])];
        // score=1.0 >= threshold=1.0 debe incluirse (Python: `if score < th: continue`)
        let out = semantic_neighbor_pairs(&idsv, &embs, 1.0, 2);
        assert_eq!(out.len(), 1);
        assert_eq!(out[0], (0, 1, 1.0));
    }

    #[test]
    fn embedding_faltante_o_vacio_da_cero() {
        let idsv = ids(3);
        let embs = vec![None, Some(vec![]), Some(vec![1.0, 1.0])];
        let out = semantic_neighbor_pairs(&idsv, &embs, 0.5, 5);
        assert!(out.is_empty(), "sin embedding no hay similitud");
    }

    #[test]
    fn desempate_score_igual_gana_mayor_id_desc() {
        // nodo A con tres vecinos de score idéntico 0.9: reverse=True deja
        // primero el node_id MAYOR. Con max_edges_per_node=1 sólo sobrevive
        // el vecino con mayor id.
        let idsv = vec![
            "a".to_string(),
            "z".to_string(),
            "m".to_string(),
            "b".to_string(),
        ];
        let target = vec![1.0, 0.0];
        let same = |k: f64| vec![k, 0.0];
        let embs = vec![
            Some(target.clone()),
            Some(same(0.9)),
            Some(same(0.9)),
            Some(same(0.9)),
        ];
        let want = python_reference(&idsv, &embs, 0.5, 1);
        let out = semantic_neighbor_pairs(&idsv, &embs, 0.5, 1);
        assert_eq!(out, want);
        // Cada vecino devuelve a "a" como su único top-1 ⇒ sobreviven los 3 pares.
        assert_eq!(out.len(), 3);
        // La primera emisión desde "a" (idx 0) es con "z": ganó el desempate.
        assert_eq!((out[0].0, out[0].1), (0, 1));
        assert_eq!(idsv[out[0].1].as_str(), "z");
    }

    #[test]
    fn orden_de_emision_coincide_con_loops_anidados_python() {
        // ids NO ordenados por índice: la pasada 2 de Python itera índices y
        // filtra por string id — replicado acá.
        let idsv = vec!["c".to_string(), "a".to_string(), "b".to_string()];
        let embs = vec![
            Some(vec![1.0, 0.0]),
            Some(vec![1.0, 0.0]),
            Some(vec![1.0, 0.0]),
        ];
        let want = python_reference(&idsv, &embs, 0.9, 5);
        let out = semantic_neighbor_pairs(&idsv, &embs, 0.9, 5);
        assert_eq!(out, want);
        // La pasada 2 visita TODOS los (i,j) y emite sólo cuando ids[i]<ids[j]:
        // i=1(a): j=0(c) ✓ luego j=2(b) ✓; después i=2(b): j=0(c) ✓.
        let seq: Vec<(usize, usize)> = out.iter().map(|(i, j, _)| (*i, *j)).collect();
        assert_eq!(seq, vec![(1, 0), (1, 2), (2, 0)]);
    }

    /// Réplica directa del algoritmo Python para test de paridad.
    fn python_reference(
        hybrid_ids: &[String],
        hybrid_emb: &[Option<Vec<f64>>],
        threshold: f64,
        max_edges: usize,
    ) -> Vec<(usize, usize, f64)> {
        fn cos(a: &Option<Vec<f64>>, b: &Option<Vec<f64>>) -> f64 {
            let (Some(x), Some(y)) = (a, b) else {
                return 0.0;
            };
            if x.is_empty() || y.is_empty() {
                return 0.0;
            }
            let dot: f64 = sum_neumaier(x.iter().zip(y).map(|(p, q)| p * q));
            let na = sum_neumaier(x.iter().map(|v| v * v)).sqrt();
            let nb = sum_neumaier(y.iter().map(|v| v * v)).sqrt();
            if na == 0.0 || nb == 0.0 {
                0.0
            } else {
                dot / (na * nb)
            }
        }
        let n = hybrid_ids.len();
        use std::collections::{HashMap as HM, HashSet as HS};
        let mut neighbors: HM<String, Vec<(f64, String)>> = HM::new();
        for i in 0..n {
            for j in (i + 1)..n {
                let score = cos(&hybrid_emb[i], &hybrid_emb[j]);
                if score < threshold {
                    continue;
                }
                neighbors
                    .entry(hybrid_ids[i].clone())
                    .or_default()
                    .push((score, hybrid_ids[j].clone()));
                neighbors
                    .entry(hybrid_ids[j].clone())
                    .or_default()
                    .push((score, hybrid_ids[i].clone()));
            }
        }
        let mut allowed: HS<(String, String)> = HS::new();
        for (node, ns) in &neighbors {
            let mut ranked = ns.clone();
            ranked.sort_by(|a, b| b.0.total_cmp(&a.0).then_with(|| b.1.cmp(&a.1)));
            for (_, other) in ranked.into_iter().take(max_edges) {
                allowed.insert((node.min(&other).clone(), node.max(&other).clone()));
            }
        }
        let mut out = Vec::new();
        for i in 0..n {
            for j in 0..n {
                if hybrid_ids[i] >= hybrid_ids[j] {
                    continue;
                }
                let pair = (hybrid_ids[i].clone(), hybrid_ids[j].clone());
                if !allowed.contains(&pair) {
                    continue;
                }
                let score = cos(&hybrid_emb[i], &hybrid_emb[j]);
                if score < threshold {
                    continue;
                }
                out.push((i, j, score));
            }
        }
        out
    }

    #[test]
    fn paridad_contra_referencia_python_en_dataset_pseudoaleatorio() {
        let mut state: u64 = 42;
        let mut next = move || {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            ((state >> 11) as f64) / ((1u64 << 53) as f64) - 0.5
        };
        let n = 60;
        let dim = 64;
        let idsv: Vec<String> = (0..n).map(|i| format!("mem-{i:038}")).collect();
        let embs: Vec<Option<Vec<f64>>> = (0..n)
            .map(|i| {
                if i % 7 == 0 {
                    None // algunos sin embedding
                } else {
                    Some((0..dim).map(|_| next()).collect())
                }
            })
            .collect();

        for threshold in [0.05, 0.2, 0.82] {
            for max_edges in [1, 2, 5] {
                let got = semantic_neighbor_pairs(&idsv, &embs, threshold, max_edges);
                let want = python_reference(&idsv, &embs, threshold, max_edges);
                assert_eq!(got, want, "threshold={threshold} max={max_edges}");
            }
        }
    }
}
