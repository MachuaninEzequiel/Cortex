//! Puerto de `EpisodicMemoryStore._extract_entities` (P12A-1).
//!
//! Extracción estructurada de entidades (funciones, clases, endpoints,
//! errores, config keys, dependencias, variables, constantes) sobre el
//! contenido de una memoria, con los MISMOS patrones regex del Python y el
//! MISMO orden de inserción (el orden visible de los flags `entity_*` en la
//! meta flattenada del export depende de él).
//!
//! Semántica replicada por categoría:
//! - `findall` acumula matches de todos los patrones de la categoría en orden;
//! - tuplas (patrones con >1 grupo) ⇒ primer grupo no-vacío;
//! - dedup preservando primera aparición, descartando vacíos;
//! - cap de 15 valores por categoría.

use std::sync::OnceLock;

/// Un patrón compilado + los grupos a considerar (en orden).
struct Pat {
    re: regex::Regex,
    /// Índices de grupo (base 1) a probar; se toma el primer no-vacío.
    groups: &'static [usize],
}

fn p(pattern: &str, groups: &'static [usize]) -> Pat {
    Pat {
        re: regex::Regex::new(pattern).expect("regex de entidades inválida"),
        groups,
    }
}

fn patterns() -> &'static [(&'static str, Vec<Pat>)] {
    static PATS: OnceLock<Vec<(&'static str, Vec<Pat>)>> = OnceLock::new();
    PATS.get_or_init(|| {
        vec![
            (
                "function",
                vec![
                    p(r"(?:def|function|async\s+function)\s+(\w+)\s*\(", &[1]),
                    p(
                        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(.*\)\s*=>",
                        &[1],
                    ),
                    p(
                        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\*?\s*\([^)]*\)",
                        &[1],
                    ),
                ],
            ),
            (
                "class",
                vec![
                    p(r"class\s+(\w+)", &[1]),
                    // En Python el `{` suelto es literal; acá va escapado
                    // (misma semántica).
                    p(r"(?:const|let|var)\s+(\w+)\s*=\s*class\s*\{", &[1]),
                ],
            ),
            (
                "endpoint",
                vec![
                    p(
                        r#"(?:@app\.(?:route|get|post|put|delete|patch|head|options))\(\s*[\"']([^\"']+)[\"']"#,
                        &[1],
                    ),
                    p(
                        r#"router\.(?:get|post|put|delete|patch|head|options)\(\s*[\"']([^\"']+)[\"']"#,
                        &[1],
                    ),
                    p(
                        r#"(?:app\.)?(?:get|post|put|delete|patch|head|options)\(\s*[\"']([^\"']+)[\"']"#,
                        &[1],
                    ),
                ],
            ),
            (
                "error",
                vec![
                    p(r"(?:Error|Exception|TypeError|ValueError|KeyError):\s*(.+)", &[1]),
                    p(r"throw\s+new\s+(\w+Error)\s*\(", &[1]),
                    p(r"catch\s*\(\s*\w+\s+(\w+Error)", &[1]),
                ],
            ),
            (
                "config_key",
                vec![
                    p(r#"(?:process\.env|os\.environ)\[['\"](\w+)['\"]\]"#, &[1]),
                    p(r#"config\.get\(\s*['\"](\w+)['\"]\s*\)"#, &[1]),
                    p(r"settings\.\s*(\w+)", &[1]),
                ],
            ),
            (
                "dependency",
                vec![
                    p(
                        r#"(?:import\s+.*\s+from\s+|require\s*\()\s*[\"']([^\"']+)[\"']"#,
                        &[1],
                    ),
                    p(r"from\s+([\w./-]+)\s+import", &[1]),
                    p(r"import\s+([\w./-]+)", &[1]),
                ],
            ),
            ("variable", vec![p(r"(?:const|let|var)\s+(\w+)\s*=", &[1])]),
            (
                "constant",
                vec![p(r"(?:const\s+(\w+)\s*=)|(?:#\s*define\s+(\w+))", &[1, 2])],
            ),
        ]
    })
}

/// Extrae entidades ordenadas por categoría (orden de declaración) y dentro
/// de cada una por primera aparición, dedup + vacíos fuera + cap 15.
pub fn extract_entities(content: &str) -> Vec<(String, Vec<String>)> {
    let mut out: Vec<(String, Vec<String>)> = Vec::new();
    for (etype, pats) in patterns() {
        let mut matches: Vec<String> = Vec::new();
        for pat in pats {
            for caps in pat.re.captures_iter(content) {
                let picked = pat
                    .groups
                    .iter()
                    .filter_map(|g| caps.get(*g))
                    .map(|m| m.as_str())
                    .find(|s| !s.is_empty())
                    .unwrap_or("");
                if !picked.is_empty() && !matches.contains(&picked.to_string()) {
                    matches.push(picked.to_string());
                }
            }
        }
        if !matches.is_empty() {
            matches.truncate(15);
            out.push((etype.to_string(), matches));
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extrae_funcion_clase_endpoint_error() {
        // Verificado contra el oráculo: la frase en español con "función" NO
        // matchea (el patrón exige "function"); "def nombre(" sí.
        assert!(extract_entities(
            "Se arregló el bug de login en la función authenticate_user del módulo auth."
        )
        .is_empty());
        let got = extract_entities("def authenticate_user(password): valida el login.");
        assert_eq!(got.len(), 1);
        assert_eq!(got[0].0, "function");
        assert_eq!(got[0].1, vec!["authenticate_user"]);
    }

    #[test]
    fn clase_y_cap_quince() {
        let mut s = String::new();
        for i in 0..20 {
            s.push_str(&format!("class Cosa{i} hace cosas.\n"));
        }
        let got = extract_entities(&s);
        assert_eq!(got[0].0, "class");
        assert_eq!(got[0].1.len(), 15);
        assert_eq!(got[0].1[0], "Cosa0");
    }

    #[test]
    fn tupla_primer_grupo_no_vacio() {
        // `constant`: alternativa 1 (const X =) gana sobre la 2 (#define).
        let got = extract_entities("const MAX_RETRIES = 5");
        assert_eq!(
            got.iter().find(|(t, _)| t == "constant").unwrap().1,
            vec!["MAX_RETRIES"]
        );
    }

    #[test]
    fn sin_entidades_devuelve_vacio() {
        assert!(
            extract_entities("Memoria genérica sin entidades ni archivos adjuntos.").is_empty()
        );
    }

    #[test]
    fn orden_de_categorias_estable() {
        // Verificado contra el oráculo: "importar os" no matchea dependency
        // (patrón exige "import " con espacio).
        let got = extract_entities(
            "class FeedbackStore persiste feedback.jsonl; error ValueError: boom al importar os",
        );
        let tipos: Vec<&str> = got.iter().map(|(t, _)| t.as_str()).collect();
        assert_eq!(tipos, vec!["class", "error"]);
        assert_eq!(got[0].1, vec!["FeedbackStore"]);
        assert_eq!(got[1].1, vec!["boom al importar os"]);
    }
}
