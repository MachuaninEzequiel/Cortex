//! Presentadores de contexto enriquecido — réplica de
//! `cortex/context_enricher/presenter.py` (P12A-7).
//!
//! Markdown (PR comments), compact (prompt injection), grouped ×2 (Fase 08)
//! y JSON (CI/CD — ya existente como `EnrichedBundle::to_json`, P7).

use super::models::{EnrichedBundle, EnrichedItem};

fn source_tag(item: &EnrichedItem) -> &'static str {
    if item.source == "episodic" {
        "EPISODIC"
    } else {
        "SEMANTIC"
    }
}

/// Fecha `%Y-%m-%d` desde el ISO canónico del item.
fn date_ymd(item: &EnrichedItem) -> Option<&str> {
    item.date.as_deref().map(|d| &d[..10.min(d.len())])
}

/// `m.replace("_search", "").replace("_query", "")`
fn strategy_label(m: &str) -> String {
    m.replace("_search", "").replace("_query", "")
}

fn strategy_labels(matched_by: &[String]) -> Vec<String> {
    matched_by.iter().map(|m| strategy_label(m)).collect()
}

const EMPTY_MD: &str =
    "🧠 Cortex Context — No related memories found.\n\nThis might be a new area of the codebase.";

pub fn to_markdown(ctx: &EnrichedBundle) -> String {
    if ctx.items.is_empty() {
        return EMPTY_MD.to_string();
    }
    let mut parts: Vec<String> = vec![
        format!(
            "🧠 Cortex Context — Found {} related memories",
            ctx.items.len()
        ),
        format!(
            "({} searches, {} raw hits → {} unique)\n",
            ctx.total_searches,
            ctx.total_raw_hits,
            ctx.items.len()
        ),
    ];
    for (i, item) in ctx.items.iter().enumerate() {
        let emoji = if item.source == "episodic" {
            "📝"
        } else {
            "📖"
        };
        parts.push(format!(
            "{emoji} **{}. {}** [{}]",
            i + 1,
            item.title,
            source_tag(item)
        ));
        let mut meta_parts: Vec<String> = vec![];
        if let Some(d) = date_ymd(item) {
            meta_parts.push(d.to_string());
        }
        if !item.files_mentioned.is_empty() {
            meta_parts.push(item.files_mentioned.join(", "));
        }
        if !item.tags.is_empty() {
            meta_parts.push(
                item.tags
                    .iter()
                    .map(|t| format!("`{t}`"))
                    .collect::<Vec<_>>()
                    .join(", "),
            );
        }
        if !meta_parts.is_empty() {
            parts.push(format!("  {}", meta_parts.join(" • ")));
        }
        let mut excerpt: String = item.content.chars().take(200).collect();
        if item.content.chars().count() > 200 {
            excerpt.push('…');
        }
        parts.push(format!("  > {excerpt}"));
        if !item.matched_by.is_empty() {
            parts.push(format!(
                "  _Matched by: {}_",
                strategy_labels(&item.matched_by).join(", ")
            ));
        }
        parts.push(String::new());
    }
    parts.push("---".into());
    parts.push("_Run `cortex context --expand` for full details._".into());
    parts.join("\n")
}

pub fn to_compact(ctx: &EnrichedBundle) -> String {
    if ctx.items.is_empty() {
        return "🧠 Cortex Context — No related memories found.".to_string();
    }
    let mut parts: Vec<String> = vec![format!(
        "## 🧠 Cortex Context ({} memories found)\n",
        ctx.items.len()
    )];
    for item in &ctx.items {
        parts.push(format!("### {} [{}]", item.title, source_tag(item)));
        parts.push(
            item.content
                .chars()
                .take(300)
                .collect::<String>()
                .replace('\n', " "),
        );
        let mut meta_parts: Vec<String> = vec![];
        if !item.files_mentioned.is_empty() {
            meta_parts.push(format!("Files: {}", item.files_mentioned.join(", ")));
        }
        if let Some(d) = date_ymd(item) {
            meta_parts.push(d.to_string());
        }
        if !item.matched_by.is_empty() {
            meta_parts.push(format!(
                "Matched by: {}",
                strategy_labels(&item.matched_by).join(", ")
            ));
        }
        if !meta_parts.is_empty() {
            parts.push(meta_parts.join(" | "));
        }
        parts.push(String::new());
    }
    parts.join("\n")
}

/// Grupos por doc_type (label upper, OTHER al final implícito), ordenados por
/// max enriched_score desc; orden estable para empates (first-appearance).
pub fn to_markdown_grouped(ctx: &EnrichedBundle) -> String {
    if ctx.items.is_empty() {
        return "🧠 Cortex Context — No related memories found.".to_string();
    }
    let ordered = group_sorted(ctx, GroupCase::Upper);
    let mut parts: Vec<String> = vec![format!(
        "# Cortex Context ({} items, {} chars)\n",
        ctx.items.len(),
        ctx.total_chars
    )];
    for (label, items) in ordered {
        parts.push(format!("\n## {label} ({} items)", items.len()));
        for item in items {
            parts.push(format!("\n### {}", item.title));
            let mut meta = vec![format!("score: {:.3}", item.enriched_score)];
            if !item.matched_by.is_empty() {
                meta.push(format!("matched_by: {}", item.matched_by.join(", ")));
            }
            if let Some(s) = &item.matched_section_title {
                meta.push(format!("section: {s}"));
            }
            if item.vault_scope != "local" && !item.vault_scope.is_empty() {
                meta.push(format!("scope: {}", item.vault_scope));
            }
            parts.push(meta.join(" | "));
            let content_len = item.content.chars().count();
            let mut excerpt: String = item.content.chars().take(200).collect();
            if content_len > 200 {
                excerpt.push('…');
            }
            parts.push(format!("> {excerpt}"));
        }
    }
    parts.join("\n")
}

pub fn to_compact_grouped(ctx: &EnrichedBundle) -> String {
    if ctx.items.is_empty() {
        return "🧠 Cortex Context — No related memories found.".to_string();
    }
    let ordered = group_sorted(ctx, GroupCase::Lower);
    let mut parts: Vec<String> = vec![format!("## Cortex Context ({} items)\n", ctx.items.len())];
    for (label, items) in ordered {
        parts.push(format!("[{}]", label.to_uppercase()));
        for item in items {
            let section = match &item.matched_section_title {
                Some(s) if !s.is_empty() => format!(" §{s}"),
                _ => String::new(),
            };
            parts.push(format!(
                "- {}{} (score={:.2})",
                item.title, section, item.enriched_score
            ));
            parts.push(format!(
                "  {}",
                item.content
                    .chars()
                    .take(200)
                    .collect::<String>()
                    .replace('\n', " ")
            ));
        }
        parts.push(String::new());
    }
    parts.join("\n")
}

enum GroupCase {
    Upper,
    Lower,
}

/// defaultdict + sort por max(enriched_score) desc, estable.
fn group_sorted<'a>(
    ctx: &'a EnrichedBundle,
    case: GroupCase,
) -> Vec<(String, Vec<&'a EnrichedItem>)> {
    let mut groups: Vec<(String, Vec<&'a EnrichedItem>)> = vec![];
    for item in &ctx.items {
        let raw = item.doc_type.clone().unwrap_or_else(|| match case {
            GroupCase::Upper => "OTHER".to_string(),
            GroupCase::Lower => "other".to_string(),
        });
        let label = match case {
            GroupCase::Upper => raw.to_uppercase(),
            GroupCase::Lower => raw.to_lowercase(),
        };
        match groups.iter_mut().find(|(l, _)| *l == label) {
            Some((_, v)) => v.push(item),
            None => groups.push((label, vec![item])),
        }
    }
    // sorted(..., key=max score, reverse=True) — estable en Python.
    groups.sort_by(|a, b| {
        let ma =
            a.1.iter()
                .map(|i| i.enriched_score)
                .fold(f64::NEG_INFINITY, f64::max);
        let mb =
            b.1.iter()
                .map(|i| i.enriched_score)
                .fold(f64::NEG_INFINITY, f64::max);
        mb.partial_cmp(&ma).unwrap_or(std::cmp::Ordering::Equal)
    });
    groups
}

#[cfg(test)]
mod tests {
    use super::*;

    fn item(id: &str, content: &str) -> EnrichedItem {
        EnrichedItem {
            source: "episodic",
            source_id: id.into(),
            title: id.into(),
            content: content.into(),
            score: 0.5,
            enriched_score: 0.6,
            matched_by: vec!["topic_search".into()],
            files_mentioned: vec![],
            date: Some("2026-05-01T10:30:00+00:00".into()),
            tags: vec![],
            doc_type: None,
            status: None,
            vault_scope: "local".into(),
            origin_project_id: None,
            matched_chunk_id: None,
            matched_section_title: None,
        }
    }

    fn ctx(items: Vec<EnrichedItem>) -> EnrichedBundle {
        let n = items.len();
        EnrichedBundle {
            work: Default::default(),
            items,
            total_searches: 1,
            total_raw_hits: n,
            total_chars: 10,
            within_budget_override: None,
        }
    }

    #[test]
    fn markdown_vacio() {
        assert!(presenter_markdown_empty());
    }

    fn presenter_markdown_empty() -> bool {
        to_markdown(&ctx(vec![])).starts_with("🧠 Cortex Context — No related")
    }

    #[test]
    fn excerpt_trunca_con_elipsis() {
        let largo = "a".repeat(250);
        let md = to_markdown(&ctx(vec![item("n", &largo)]));
        assert!(md.contains('…'));
    }

    #[test]
    fn agrupado_orden_por_score_desc() {
        let mut alto = item("alto", "c");
        alto.enriched_score = 0.9;
        alto.doc_type = Some("adr".into());
        let bajo = item("bajo", "c");
        let md = to_compact_grouped(&ctx(vec![bajo, alto]));
        let pos_alto = md.find("[ADR]").unwrap();
        let pos_other = md.find("[OTHER]").unwrap();
        assert!(pos_alto < pos_other);
    }
}
