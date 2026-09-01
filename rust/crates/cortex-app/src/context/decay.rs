//! Puerto de `cortex/memory_decay.py` — decaimiento temporal de scores.
//!
//! factor = max(decay_rate^(age_hours - min_age), floor) para memorias no
//! permanentes; 1.0 para permanentes (tipos/etiquetas) o menores a min_age.

use chrono::{DateTime, Utc};

pub const DEFAULT_DECAY_RATE: f64 = 0.995;

/// Tipos con piso (conocimiento permanente).
const PERMANENT_TYPES: [&str; 5] = [
    "adr",
    "architecture",
    "decision",
    "project_intro",
    "vault_doc",
];

/// Etiquetas que indican conocimiento permanente.
const PERMANENT_TAGS: [&str; 8] = [
    "adr",
    "architecture",
    "decision",
    "permanent",
    "onboarding",
    "getting-started",
    "runbook",
    "design",
    // nota: "tech-spec" va aparte abajo porque contiene guión
];

fn es_permanente_type(memory_type: &str) -> bool {
    PERMANENT_TYPES.contains(&memory_type.to_lowercase().as_str())
}

fn es_permanente_tag(tag: &str) -> bool {
    let t = tag.to_lowercase();
    PERMANENT_TAGS.contains(&t.as_str()) || t == "tech-spec"
}

#[derive(Debug, Clone, Copy)]
pub struct DecayConfig {
    pub decay_rate: f64,
    pub half_life_hours: f64,
    pub floor: f64,
    pub min_age_hours: f64,
}

impl DecayConfig {
    /// `__post_init__`: un decay_rate igual al default se deriva del
    /// half_life (bug #9); uno explícito distinto se respeta.
    pub fn new(half_life_hours: f64, floor: f64) -> Self {
        let mut cfg = Self {
            decay_rate: DEFAULT_DECAY_RATE,
            half_life_hours,
            floor,
            min_age_hours: 24.0,
        };
        if cfg.decay_rate == DEFAULT_DECAY_RATE && cfg.half_life_hours > 0.0 {
            cfg.decay_rate = 0.5f64.powf(1.0 / cfg.half_life_hours);
        }
        cfg
    }
}

fn parse_ts(s: &str) -> Option<DateTime<Utc>> {
    if let Ok(dt) = DateTime::parse_from_rfc3339(s) {
        return Some(dt.with_timezone(&Utc));
    }
    for fmt in ["%Y-%m-%dT%H:%M:%S%.f", "%Y-%m-%d %H:%M:%S"] {
        if let Ok(dt) = DateTime::parse_from_str(s, fmt) {
            return Some(dt.with_timezone(&Utc));
        }
    }
    None
}

/// Espejo de MemoryDecay.calculate_decay_factor con `now` inyectable
/// (el enricher Python usa now(); los tests fijan el reloj).
pub fn calculate_decay_factor(
    memory_type: &str,
    tags: &[String],
    timestamp_iso: &str,
    config: &DecayConfig,
    now: DateTime<Utc>,
) -> f64 {
    // should_decay
    let permanente = es_permanente_type(memory_type)
        || tags.iter().any(|t| es_permanente_tag(t))
        || tags.iter().any(|t| t.to_lowercase() == "permanent");
    if permanente {
        return 1.0;
    }

    let Some(ts) = parse_ts(timestamp_iso) else {
        // Timestamp ausente/ilegible en el puerto: tratar como reciente
        // (factor 1.0). El oráculo nunca llega acá con datos canónicos.
        return 1.0;
    };

    let age_hours = (now - ts).num_seconds() as f64 / 3600.0;
    if age_hours < config.min_age_hours {
        return 1.0;
    }

    let hours_since_decay = age_hours - config.min_age_hours;
    let factor = config.decay_rate.powf(hours_since_decay);
    if factor < config.floor {
        config.floor
    } else {
        factor
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::TimeZone;

    fn now_fija() -> DateTime<Utc> {
        Utc.with_ymd_and_hms(2026, 8, 24, 12, 0, 0).unwrap()
    }

    #[test]
    fn permanentes_no_decaen() {
        let cfg = DecayConfig::new(168.0, 0.10);
        assert_eq!(
            calculate_decay_factor(
                "decision",
                &[],
                "2026-01-01T00:00:00+00:00",
                &cfg,
                now_fija()
            ),
            1.0
        );
        assert_eq!(
            calculate_decay_factor(
                "general",
                &["architecture".to_string()],
                "2026-01-01T00:00:00+00:00",
                &cfg,
                now_fija()
            ),
            1.0
        );
    }

    #[test]
    fn recientes_sin_decay_viejos_al_piso() {
        let cfg = DecayConfig::new(168.0, 0.10);
        // <24h ⇒ 1.0
        assert_eq!(
            calculate_decay_factor("bugfix", &[], "2026-08-24T00:00:00+00:00", &cfg, now_fija()),
            1.0
        );
        // años ⇒ floor exacto (determinista para siempre)
        assert_eq!(
            calculate_decay_factor("bugfix", &[], "2026-01-01T00:00:00+00:00", &cfg, now_fija()),
            0.10
        );
    }

    #[test]
    fn decay_rate_derivado_del_half_life() {
        let cfg = DecayConfig::new(168.0, 0.10);
        let esperado = 0.5f64.powf(1.0 / 168.0);
        assert!((cfg.decay_rate - esperado).abs() < 1e-15);
    }
}
