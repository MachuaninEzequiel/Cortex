//! Filtros estructurales post-retrieval — réplica de
//! `cortex/context_enricher/filters.py` (P12A-7).
//!
//! El motor de retrieval es content-driven; estos filtros remueven ítems que
//! el caller sabe irrelevantes POR METADATOS. Todos los campos son
//! opcionales: con `filters=None` o un `EnrichmentFilters` vacío,
//! `apply_filters` es no-op.

use chrono::{DateTime, Utc};

use super::models::EnrichedItem;

/// Filtros AND-compuestos aplicados después del retrieval y antes del budget.
#[derive(Debug, Clone)]
pub struct EnrichmentFilters {
    pub doc_types: Option<Vec<String>>,
    pub exclude_doc_types: Vec<String>,
    pub statuses_allowed: Option<Vec<String>>,
    pub statuses_excluded: Vec<String>,
    /// AND
    pub tags_required: Vec<String>,
    pub tags_excluded: Vec<String>,
    /// OR
    pub tags_any_of: Vec<String>,
    /// "local" | "enterprise" | "all"
    pub vault_scope: String,
    pub max_age_days: Option<i64>,
    pub project_ids: Option<Vec<String>>,
    pub strict: bool,
}

impl Default for EnrichmentFilters {
    fn default() -> Self {
        Self {
            doc_types: None,
            exclude_doc_types: vec![],
            statuses_allowed: None,
            statuses_excluded: vec![],
            tags_required: vec![],
            tags_excluded: vec![],
            tags_any_of: vec![],
            vault_scope: "all".into(),
            max_age_days: None,
            project_ids: None,
            strict: false,
        }
    }
}

impl EnrichmentFilters {
    /// `True` cuando cada campo está en su default.
    pub fn is_empty(&self) -> bool {
        self.doc_types.is_none()
            && self.exclude_doc_types.is_empty()
            && self.statuses_allowed.is_none()
            && self.statuses_excluded.is_empty()
            && self.tags_required.is_empty()
            && self.tags_excluded.is_empty()
            && self.tags_any_of.is_empty()
            && self.vault_scope == "all"
            && self.max_age_days.is_none()
            && self.project_ids.is_none()
            && !self.strict
    }
}

/// Réplica de `datetime.now(UTC)` interno de Python.
pub fn apply_filters(
    items: &[EnrichedItem],
    filters: Option<&EnrichmentFilters>,
) -> Vec<EnrichedItem> {
    apply_filters_at(items, filters, Utc::now())
}

/// Variante con reloj inyectable (los gates la usan para determinismo).
pub fn apply_filters_at(
    items: &[EnrichedItem],
    filters: Option<&EnrichmentFilters>,
    now: DateTime<Utc>,
) -> Vec<EnrichedItem> {
    let Some(f) = filters else {
        return items.to_vec();
    };
    if f.is_empty() {
        return items.to_vec();
    }
    items
        .iter()
        .filter(|item| passes(item, f, now))
        .cloned()
        .collect()
}

fn passes(item: &EnrichedItem, f: &EnrichmentFilters, now: DateTime<Utc>) -> bool {
    // doc_types
    if let Some(doc_types) = &f.doc_types {
        match &item.doc_type {
            None => {
                if f.strict {
                    return false;
                }
            }
            Some(dt) => {
                if !doc_types.contains(dt) {
                    return false;
                }
            }
        }
    }

    if !f.exclude_doc_types.is_empty()
        && item
            .doc_type
            .as_ref()
            .is_some_and(|dt| f.exclude_doc_types.contains(dt))
    {
        return false;
    }

    // status
    if let Some(allowed) = &f.statuses_allowed {
        match &item.status {
            None => return false,
            Some(s) if !allowed.contains(s) => return false,
            _ => {}
        }
    }
    if let Some(s) = &item.status {
        if f.statuses_excluded.contains(s) {
            return false;
        }
    }

    // tags
    let item_tags: std::collections::HashSet<&str> = item.tags.iter().map(String::as_str).collect();
    if !f.tags_required.is_empty()
        && !f
            .tags_required
            .iter()
            .all(|t| item_tags.contains(t.as_str()))
    {
        return false;
    }
    if !f.tags_excluded.is_empty()
        && item_tags
            .intersection(&f.tags_excluded.iter().map(String::as_str).collect())
            .next()
            .is_some()
    {
        return false;
    }
    if !f.tags_any_of.is_empty()
        && item_tags
            .intersection(&f.tags_any_of.iter().map(String::as_str).collect())
            .next()
            .is_none()
    {
        return false;
    }

    // scope
    if f.vault_scope != "all" && item.vault_scope != f.vault_scope {
        // Python: getattr(item, "vault_scope", "local") or "local" — el modelo
        // siempre trae el campo (default "local").
        return false;
    }

    // age
    if let Some(days) = f.max_age_days {
        if days > 0 {
            if let Some(date_str) = &item.date {
                if let Some(item_instant) = parse_iso_naive_or_aware(date_str) {
                    // Python compara instantes: cutoff = now - days vs
                    // item_date (naive ⇒ UTC). Ambos lados en naive-UTC.
                    let cutoff = now.naive_utc() - chrono::Duration::days(days);
                    if item_instant < cutoff {
                        return false;
                    }
                }
            }
        }
    }

    // project
    if let Some(project_ids) = &f.project_ids {
        match &item.origin_project_id {
            Some(p) if project_ids.contains(p) => {}
            _ => return false,
        }
    }

    true
}

/// Parseo ISO tolerante (con o sin offset); devuelve el naive equivalente.
/// Los offsets no-UTC se normalizan a UTC para comparar instantes como hace
/// Python con datetimes aware.
fn parse_iso_naive_or_aware(s: &str) -> Option<chrono::NaiveDateTime> {
    let trimmed = s.trim();
    if let Ok(dt) = chrono::DateTime::parse_from_rfc3339(trimmed) {
        return Some(dt.with_timezone(&Utc).naive_utc());
    }
    for fmt in ["%Y-%m-%dT%H:%M:%S%.f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"] {
        if fmt == "%Y-%m-%d" {
            if let Ok(d) = chrono::NaiveDate::parse_from_str(trimmed, fmt) {
                return d.and_hms_opt(0, 0, 0);
            }
        } else if let Ok(ndt) = chrono::NaiveDateTime::parse_from_str(trimmed, fmt) {
            // Naive ⇒ Python le pega UTC (replace tzinfo=UTC).
            return Some(ndt);
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixed() -> chrono::DateTime<Utc> {
        chrono::TimeZone::with_ymd_and_hms(&Utc, 2026, 6, 1, 12, 0, 0).unwrap()
    }

    #[test]
    fn default_es_vacío() {
        let f = EnrichmentFilters::default();
        assert!(f.is_empty());
        assert!(f.vault_scope == "all");
    }

    #[test]
    fn doc_types_strict_y_tolerante() {
        let items = vec![
            EnrichedItem {
                source_id: "a".into(),
                doc_type: Some("adr".into()),
                ..test_item()
            },
            EnrichedItem {
                source_id: "b".into(),
                doc_type: None,
                ..test_item()
            },
        ];
        let f = EnrichmentFilters {
            doc_types: Some(vec!["adr".into()]),
            ..Default::default()
        };
        let out = apply_filters_at(&items, Some(&f), fixed());
        assert_eq!(out.len(), 2); // no-strict mantiene None
        let f = EnrichmentFilters {
            doc_types: Some(vec!["adr".into()]),
            strict: true,
            ..Default::default()
        };
        let out = apply_filters_at(&items, Some(&f), fixed());
        assert_eq!(ids(&out), vec!["a"]);
    }

    #[test]
    fn tags_and_or_exclude() {
        let items = vec![
            EnrichedItem {
                source_id: "x".into(),
                tags: vec!["rust".into(), "core".into()],
                ..test_item()
            },
            EnrichedItem {
                source_id: "y".into(),
                tags: vec!["rust".into()],
                ..test_item()
            },
        ];
        let req = EnrichmentFilters {
            tags_required: vec!["rust".into(), "core".into()],
            ..Default::default()
        };
        assert_eq!(
            ids(&apply_filters_at(&items, Some(&req), fixed())),
            vec!["x"]
        );
        let excl = EnrichmentFilters {
            tags_excluded: vec!["rust".into()],
            ..Default::default()
        };
        assert!(apply_filters_at(&items, Some(&excl), fixed()).is_empty());
        let any = EnrichmentFilters {
            tags_any_of: vec!["python".into(), "core".into()],
            ..Default::default()
        };
        assert_eq!(
            ids(&apply_filters_at(&items, Some(&any), fixed())),
            vec!["x"]
        );
    }

    #[test]
    fn max_age_ventana() {
        use chrono::TimeZone;
        let now = Utc.with_ymd_and_hms(2026, 6, 1, 12, 0, 0).unwrap();
        let items = vec![
            EnrichedItem {
                source_id: "old".into(),
                date: Some("2020-01-01T00:00:00+00:00".into()),
                ..test_item()
            },
            EnrichedItem {
                source_id: "new".into(),
                date: Some("2026-05-01T00:00:00+00:00".into()),
                ..test_item()
            },
            EnrichedItem {
                source_id: "nodate".into(),
                ..test_item()
            },
        ];
        let f = EnrichmentFilters {
            max_age_days: Some(365),
            ..Default::default()
        };
        let out = apply_filters_at(&items, Some(&f), now);
        assert_eq!(ids(&out), vec!["new", "nodate"]);
    }

    fn ids(items: &[EnrichedItem]) -> Vec<String> {
        items.iter().map(|i| i.source_id.clone()).collect()
    }

    fn test_item() -> EnrichedItem {
        EnrichedItem {
            source: "episodic",
            source_id: String::new(),
            title: "t".into(),
            content: "c".into(),
            score: 0.5,
            enriched_score: 0.6,
            matched_by: vec![],
            files_mentioned: vec![],
            date: None,
            tags: vec![],
            doc_type: None,
            status: None,
            vault_scope: "local".into(),
            origin_project_id: None,
            matched_chunk_id: None,
            matched_section_title: None,
        }
    }
}
