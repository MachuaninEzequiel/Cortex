//! Puerto de la parte de `cortex/feedback_loop.py` que consume el
//! ContextEnricher: ImplicitFeedbackAnalyzer + boost implícito.

/// Stopwords del analyzer (comunes en inglés + código).
const STOPWORDS: [&str; 49] = [
    // Common English
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "as", "is", "was", "are", "were", "been", "be", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "must", // Common code
    "function", "return", "class", "def", "import", "export", "const", "let", "var", "if", "else",
    "while", "switch", "case",
];

fn extraer_de_lista(list: &[String]) -> Vec<String> {
    list.iter()
        .map(|k| k.to_lowercase())
        .filter(|k| !STOPWORDS.contains(&k.as_str()))
        .collect()
}

/// `\b[a-z][a-z0-9_]{2,}\b` sobre texto lowercased + filtro de stopwords
/// y longitud > 2. El `\b` inicial exige que el carácter anterior no sea
/// palabra (en regex, `[a-z0-9_]` son word-chars ⇒ "_foo"/"4abc" NO matchean).
fn extraer_de_texto(texto: &str) -> Vec<String> {
    let lower = texto.to_lowercase();
    let chars: Vec<char> = lower.chars().collect();
    let es_word = |c: char| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_';
    let mut words: Vec<String> = Vec::new();
    let mut i = 0usize;
    while i < chars.len() {
        // \b inicial: inicio de string o char anterior no-word.
        let boundary_previa = i == 0 || !es_word(chars[i - 1]);
        if boundary_previa && chars[i].is_ascii_lowercase() {
            let start = i;
            let mut j = i + 1;
            while j < chars.len() && es_word(chars[j]) {
                j += 1;
            }
            words.push(chars[start..j].iter().collect());
            i = j;
        } else {
            i += 1;
        }
    }
    words
        .into_iter()
        .filter(|w| w.len() > 2 && !STOPWORDS.contains(&w.as_str()))
        .collect()
}

fn jaccard(a: &[String], b: &[String]) -> f64 {
    if a.is_empty() || b.is_empty() {
        return 0.0;
    }
    let sa: std::collections::HashSet<&String> = a.iter().collect();
    let sb: std::collections::HashSet<&String> = b.iter().collect();
    let inter = sa.intersection(&sb).count();
    let union = sa.union(&sb).count();
    if union == 0 {
        return 0.0;
    }
    inter as f64 / union as f64
}

#[derive(Debug, Clone)]
pub struct ImplicitFeedback {
    pub is_useful: bool,
}

/// Espejo de FeedbackCollector.process_implicit: analiza overlap entre el
/// work_context (keywords/files/entities) y cada item recuperado; un item
/// con usefulness >= 0.3 recibe boost `(1.0 + implicit_boost)`.
pub fn procesar_feedback_implicito(
    keywords: &[String],
    files: &[String],
    entities: &[String],
    items: &[(String, String, String, Vec<String>)], // (id, content, title, files)
    implicit_boost: f64,
    scores_enriched: &mut [f64],
) {
    let work_keywords = extraer_de_lista(keywords);
    let work_files: std::collections::HashSet<&String> = files.iter().collect();
    let work_entities: std::collections::HashSet<&String> = entities.iter().collect();

    for (idx, (_id, content, title, item_files)) in items.iter().enumerate() {
        let memory_keywords = extraer_de_texto(&format!("{content} {title}"));
        let kw_overlap = jaccard(&work_keywords, &memory_keywords);

        let ifiles: std::collections::HashSet<&String> = item_files.iter().collect();
        let file_overlap = overlap_sets(&work_files, &ifiles);
        let entity_overlap = overlap_sets(&work_entities, &std::collections::HashSet::new());

        let usefulness = kw_overlap * 0.4 + file_overlap * 0.4 + entity_overlap * 0.2;
        // ImplicitFeedback.is_useful ⇔ usefulness >= 0.3
        if usefulness >= 0.3 {
            scores_enriched[idx] *= 1.0 + implicit_boost;
        }
    }
}

fn overlap_sets(
    a: &std::collections::HashSet<&String>,
    b: &std::collections::HashSet<&String>,
) -> f64 {
    if a.is_empty() || b.is_empty() {
        return 0.0;
    }
    let inter = a.intersection(b).count();
    let union = a.union(b).count();
    if union == 0 {
        return 0.0;
    }
    inter as f64 / union as f64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stopwords_y_regex_texto() {
        let kws = extraer_de_texto("The function authenticate_user failed with error");
        assert!(kws.contains(&"authenticate_user".to_string()));
        assert!(!kws.contains(&"the".to_string()));
        assert!(!kws.contains(&"with".to_string()));
        // \b exige frontera real: sin ella, "_foo" y "4abc" matchearían mal.
        assert!(extraer_de_texto("_foo bar").contains(&"bar".to_string()));
        assert!(!extraer_de_texto("_foo").contains(&"foo".to_string()));
        assert!(!extraer_de_texto("4abc").contains(&"abc".to_string()));
    }

    #[test]
    fn jaccard_basico() {
        let a = vec!["x".to_string(), "y".to_string()];
        let b = vec!["y".to_string(), "z".to_string()];
        assert!((jaccard(&a, &b) - 1.0 / 3.0).abs() < 1e-12);
        assert_eq!(jaccard(&[], &a), 0.0);
    }

    #[test]
    fn boost_solo_sobre_umbral_03() {
        let items = vec![(
            "m1".to_string(),
            "auth login error".to_string(),
            "[bugfix] auth".to_string(),
            vec![],
        )];
        let kws = vec!["auth".to_string(), "login".to_string(), "error".to_string()];
        let mut scores = [2.0f64];
        procesar_feedback_implicito(&kws, &[], &[], &items, 0.15, &mut scores);
        // kw_overlap=1.0 → usefulness 0.4 ≥ 0.3 ⇒ boost
        assert!((scores[0] - 2.3).abs() < 1e-12);
    }
}
