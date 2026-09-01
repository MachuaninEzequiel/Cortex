//! Puerto de `cortex/context_enricher/co_occurrence.py` — grafo de
//! co-ocurrencia naive (conteo) y tipado (relaciones semánticas).

use std::collections::HashMap;

// ── naive co-occurrence ────────────────────────────────────────────────────

/// `{file_a: {file_b: count}}` a partir de entradas episódicas
/// (`files` por entrada; entradas con <2 archivos no aportan).
pub fn build_co_occurrence(entries_files: &[Vec<String>]) -> HashMap<String, HashMap<String, i64>> {
    let mut co: HashMap<String, HashMap<String, i64>> = HashMap::new();
    for files in entries_files {
        if files.len() < 2 {
            continue;
        }
        for f1 in files {
            let inner = co.entry(f1.clone()).or_default();
            for f2 in files {
                if f1 != f2 {
                    *inner.entry(f2.clone()).or_insert(0) += 1;
                }
            }
        }
    }
    co
}

/// Espejo de ContextEnricher._co_occurrence_score — normalizado [0,1].
pub fn co_occurrence_score(
    current_files: &[String],
    memory_files: &[String],
    co: &HashMap<String, HashMap<String, i64>>,
) -> f64 {
    if current_files.is_empty() || memory_files.is_empty() || co.is_empty() {
        return 0.0;
    }
    let mut total = 0.0f64;
    for f1 in current_files {
        for f2 in memory_files {
            if let Some(n) = co.get(f1).and_then(|m| m.get(f2)) {
                total += *n as f64;
            }
        }
    }
    let max_possible = (current_files.len() * memory_files.len()) as f64;
    if max_possible > 0.0 {
        total / max_possible
    } else {
        0.0
    }
}

// ── typed graph ────────────────────────────────────────────────────────────

pub const RELATIONSHIP_WEIGHTS: [(&str, f64); 6] = [
    ("imported_by", 1.0),
    ("tested_by", 0.9),
    ("implements", 0.8),
    ("uses", 0.7),
    ("references", 0.5),
    ("configures", 0.6),
];

fn weight_of(rel: &str) -> f64 {
    RELATIONSHIP_WEIGHTS
        .iter()
        .find(|(k, _)| *k == rel)
        .map(|(_, w)| *w)
        .unwrap_or(0.5)
}

/// `_infer_relationship` sobre los STEMS lowercased de los paths.
fn infer_relationship(file_a: &str, file_b: &str) -> &'static str {
    let stem = |p: &str| {
        // Path.stem de Python: quita SÓLO el último sufijo.
        let name = p.rsplit(['/', '\\']).next().unwrap_or(p);
        match name.rfind('.') {
            Some(idx) if idx > 0 => name[..idx].to_lowercase(),
            _ => name.to_lowercase(),
        }
    };
    let name_a = stem(file_a);
    let name_b = stem(file_b);

    // Test file → source file (nota: el chequeo es "test" in stem).
    if name_a.contains("test") {
        return "tested_by";
    }
    if name_b.contains("test") {
        return "tested_by";
    }
    if name_a.contains("config") {
        return "configures";
    }
    if name_b.contains("config") {
        return "configures";
    }
    if name_a.contains("model") || name_a.contains("db") {
        return "imported_by";
    }
    if name_a.contains("service") || name_a.contains("util") {
        return "uses";
    }
    "references"
}

#[derive(Debug, Clone)]
struct Relationship {
    relation_type: &'static str,
    strength: f64,
    count: i64,
}

#[derive(Default)]
pub struct TypedCooccurrenceGraph {
    relationships: Vec<Relationship>,
    outgoing: HashMap<String, HashMap<String, Vec<usize>>>,
    incoming: HashMap<String, HashMap<String, Vec<usize>>>,
}

impl TypedCooccurrenceGraph {
    /// `build_from_memories`: nodos + relaciones entre archivos que
    /// co-ocurren en una memoria (pares i<j en orden del vec).
    pub fn build_from_memories(entries_files: &[Vec<String>]) -> Self {
        let mut g = Self::default();
        for files in entries_files {
            if files.len() < 2 {
                continue;
            }
            for i in 0..files.len() {
                for j in (i + 1)..files.len() {
                    let (f1, f2) = (&files[i], &files[j]);
                    let rel_type = infer_relationship(f1, f2);
                    g.add_relationship(f1, f2, rel_type);
                }
            }
        }
        g
    }

    fn add_relationship(&mut self, from_file: &str, to_file: &str, relation_type: &'static str) {
        if from_file == to_file {
            return; // skip self-references
        }
        let base_strength = weight_of(relation_type);
        let strength = (base_strength * (1.0 / 3.0)).min(1.0); // count=1 ⇒ count/3
        let idx = self.relationships.len();
        let _ = (from_file, to_file); // sólo claves de adyacencia
        self.relationships.push(Relationship {
            relation_type,
            strength,
            count: 1,
        });
        self.outgoing
            .entry(from_file.to_string())
            .or_default()
            .entry(to_file.to_string())
            .or_default()
            .push(idx);
        self.incoming
            .entry(to_file.to_string())
            .or_default()
            .entry(from_file.to_string())
            .or_default()
            .push(idx);
    }

    /// La relación más fuerte entre dos archivos (ambas direcciones).
    /// `max(all_rels, key=strength)` de Python: primer máximo gana con
    /// comparación estricta — replicado recorriendo outgoing+incoming.
    fn strongest(&self, file_a: &str, file_b: &str) -> Option<&Relationship> {
        let mut best: Option<&Relationship> = None;
        if let Some(m) = self.outgoing.get(file_a) {
            if let Some(idxs) = m.get(file_b) {
                for &i in idxs {
                    let r = &self.relationships[i];
                    if best.map(|b| r.strength > b.strength).unwrap_or(true) {
                        best = Some(r);
                    }
                }
            }
        }
        if let Some(m) = self.incoming.get(file_a) {
            if let Some(idxs) = m.get(file_b) {
                for &i in idxs {
                    let r = &self.relationships[i];
                    if best.map(|b| r.strength > b.strength).unwrap_or(true) {
                        best = Some(r);
                    }
                }
            }
        }
        best
    }

    /// `calculate_relationship_score(current, memory)` normalizado [0,1].
    pub fn calculate_relationship_score(
        &self,
        current_files: &[String],
        memory_files: &[String],
    ) -> f64 {
        if current_files.is_empty() || memory_files.is_empty() {
            return 0.0;
        }
        let mut total_score = 0.0f64;
        let mut max_possible = 0.0f64;
        for f1 in current_files {
            for f2 in memory_files {
                if let Some(rel) = self.strongest(f1, f2) {
                    let type_weight = weight_of(rel.relation_type);
                    let score = type_weight * rel.strength * ((rel.count as f64 / 3.0).min(1.0));
                    total_score += score;
                }
                max_possible += 1.0;
            }
        }
        if max_possible > 0.0 {
            total_score / max_possible
        } else {
            0.0
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sv(v: &[&str]) -> Vec<String> {
        v.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn co_ocurrencia_naive_conteo() {
        let entries = vec![sv(&["a.py", "b.py", "c.py"]), sv(&["a.py", "b.py"])];
        let co = build_co_occurrence(&entries);
        assert_eq!(co["a.py"]["b.py"], 2);
        assert_eq!(co["a.py"]["c.py"], 1);
        assert!(!co.contains_key("c.py__x"));

        let score = co_occurrence_score(&sv(&["a.py"]), &sv(&["b.py"]), &co);
        assert!((score - 2.0).abs() < 1e-12);
    }

    #[test]
    fn inferencia_de_relaciones() {
        assert_eq!(infer_relationship("test_auth.py", "auth.py"), "tested_by");
        assert_eq!(infer_relationship("app.py", "test_x.rs"), "tested_by");
        assert_eq!(infer_relationship("config.yaml", "main.rs"), "configures");
        assert_eq!(infer_relationship("models.py", "x.py"), "imported_by");
        assert_eq!(infer_relationship("util.go", "x.go"), "uses");
        assert_eq!(infer_relationship("a.md", "b.md"), "references");
    }

    #[test]
    fn typed_graph_score() {
        let entries = vec![sv(&["a.py", "b.py"])];
        let g = TypedCooccurrenceGraph::build_from_memories(&entries);
        // references: 0.5 * strength(0.5*1/3) * min(1/3,1) = 0.083333…
        let s = g.calculate_relationship_score(&sv(&["a.py"]), &sv(&["b.py"]));
        assert!((s - (0.5 * (0.5 / 3.0) * (1.0 / 3.0))).abs() < 1e-12);
    }
}
