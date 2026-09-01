//! Puerto de `cortex/action_engine/signals.py` (Obra 05 Fase E).
//!
//! La marca [y]=útil de la búsqueda TUI (y cualquier feedback explícito
//! persistido) alimenta la prioridad: dominio negativo ⇒ suben calidad/
//! mantenimiento (retrieval malo = problemas de índice/docs); dominio
//! positivo ⇒ suben aprendizaje/conocimiento. Ventana por defecto: 14 días.

use std::fs;
use std::path::Path;

use chrono::{DateTime, Duration, Utc};

pub const VENTANA_DIAS_DEFAULT: i64 = 14;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MemorySignals {
    pub positivos: i64,
    pub negativos: i64,
}

impl MemorySignals {
    pub fn new(positivos: i64, negativos: i64) -> Self {
        Self {
            positivos,
            negativos,
        }
    }

    /// "positivo" | "negativo" | "neutro".
    pub fn dominio(&self) -> &'static str {
        if self.positivos > self.negativos {
            "positivo"
        } else if self.negativos > self.positivos {
            "negativo"
        } else {
            "neutro"
        }
    }
}

/// Parseo tolerante de timestamps ISO-8601 (espejo de `datetime.fromisoformat`
/// para los formatos que escribe Cortex). None ⇒ evento se CUENTA igual
/// (solo se descarta cuando el ts parsea y es anterior al corte).
fn parse_ts(value: &serde_json::Value) -> Option<DateTime<Utc>> {
    let s = value.as_str()?;
    if let Ok(dt) = DateTime::parse_from_rfc3339(s) {
        return Some(dt.with_timezone(&Utc));
    }
    // Naive (sin offset): Python compararía naive<aware y reventaría; los
    // archivos de Cortex siempre escriben offsets. Acá se interpreta UTC.
    for fmt in ["%Y-%m-%dT%H:%M:%S%.f", "%Y-%m-%d %H:%M:%S"] {
        if let Ok(dt) = DateTime::parse_from_str(s, fmt) {
            return Some(dt.with_timezone(&Utc));
        }
    }
    None
}

/// Lee feedback.jsonl (+rotado) filtrando a la ventana temporal.
pub fn leer_senales(dot_cortex: &Path, dias: i64) -> MemorySignals {
    let ruta = dot_cortex.join("feedback.jsonl");
    let rotado = dot_cortex.join("feedback.1.jsonl");
    let corte = Utc::now() - Duration::days(dias);

    let mut positivos = 0i64;
    let mut negativos = 0i64;
    for archivo in [rotado, ruta] {
        let text = match fs::read_to_string(&archivo) {
            Ok(t) => t,
            Err(_) => continue,
        };
        for linea in text.lines() {
            if linea.trim().is_empty() {
                continue;
            }
            let Ok(evento) = serde_json::from_str::<serde_json::Value>(linea) else {
                continue;
            };
            let ts = parse_ts(evento.get("ts").unwrap_or(&serde_json::Value::Null));
            if let Some(ts) = ts {
                if ts < corte {
                    continue;
                }
            }
            let tipo = evento
                .get("feedback_type")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            match tipo {
                "positive" | "useful" => positivos += 1,
                "negative" | "not_useful" => negativos += 1,
                _ => {}
            }
        }
    }
    MemorySignals {
        positivos,
        negativos,
    }
}

/// Multiplicador suave (tope ±25%) según dominio del feedback.
pub fn multiplicador_categoria(categoria: &str, senales: Option<&MemorySignals>) -> f64 {
    let Some(s) = senales else { return 1.0 };
    if s.dominio() == "neutro" {
        return 1.0;
    }
    let delta = (s.positivos - s.negativos).abs();
    // 0.05 no es exacto en binario pero AMBOS lados hacen 1.0 + 0.05 * delta
    // con la misma aritmética f64 ⇒ mismos bits.
    let factor = (1.0 + 0.05 * delta as f64).min(1.25);
    if s.dominio() == "negativo" {
        if categoria == "quality" || categoria == "maintenance" {
            factor
        } else {
            1.0
        }
    } else if categoria == "learning" || categoria == "knowledge" {
        factor
    } else {
        1.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::ActionResult;
    use chrono::Timelike;
    use std::path::PathBuf;

    struct Tmp(PathBuf);
    impl Drop for Tmp {
        fn drop(&mut self) {
            std::fs::remove_dir_all(&self.0).ok();
        }
    }

    fn tmpdir(tag: &str) -> Tmp {
        let d = std::env::temp_dir().join(format!(
            "cortex-actions-sig-{tag}-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        std::fs::create_dir_all(&d).unwrap();
        Tmp(d)
    }

    /// Espejo de _escribir_feedback(test_fase_e.py): eventos relativos a hoy.
    fn escribir_feedback(dir: &Path, eventos: &[(i64, &str)]) {
        let ahora = Utc::now();
        let lineas: Vec<String> = eventos
            .iter()
            .map(|(dias_atras, tipo)| {
                let ts = (ahora - Duration::days(*dias_atras))
                    .with_nanosecond(0)
                    .unwrap()
                    .to_rfc3339_opts(chrono::format::SecondsFormat::Secs, false);
                serde_json::json!({"ts": ts, "feedback_type": tipo, "memory_id": "x"}).to_string()
            })
            .collect();
        std::fs::write(
            dir.join("feedback.jsonl"),
            format!("{}\n", lineas.join("\n")),
        )
        .unwrap();
    }

    #[test]
    fn lee_ventana_y_descarta_fuera_de_ella() {
        let g = tmpdir("v1");
        escribir_feedback(&g.0, &[(1, "positive"), (2, "positive"), (30, "negative")]);
        let senales = leer_senales(&g.0, 14);
        assert_eq!(senales.positivos, 2);
        assert_eq!(senales.negativos, 0);
    }

    #[test]
    fn dominio_negativo_y_positivo() {
        let g = tmpdir("v2");
        escribir_feedback(&g.0, &[(1, "negative"), (1, "negative")]);
        assert_eq!(
            leer_senales(&g.0, VENTANA_DIAS_DEFAULT).dominio(),
            "negativo"
        );

        let g2 = tmpdir("v3");
        escribir_feedback(&g2.0, &[(1, "useful"), (2, "positive")]);
        assert_eq!(
            leer_senales(&g2.0, VENTANA_DIAS_DEFAULT).dominio(),
            "positivo"
        );
    }

    #[test]
    fn multiplicadores_por_dominio() {
        let g = tmpdir("m1");
        escribir_feedback(&g.0, &[(0, "negative"), (1, "negative"), (2, "negative")]);
        let senales = leer_senales(&g.0, VENTANA_DIAS_DEFAULT);
        assert!(multiplicador_categoria("quality", Some(&senales)) > 1.0);
        assert!(multiplicador_categoria("maintenance", Some(&senales)) > 1.0);
        assert_eq!(multiplicador_categoria("learning", Some(&senales)), 1.0);

        let g2 = tmpdir("m2");
        escribir_feedback(&g2.0, &[(0, "positive"), (1, "positive")]);
        let senales = leer_senales(&g2.0, VENTANA_DIAS_DEFAULT);
        assert!(multiplicador_categoria("learning", Some(&senales)) > 1.0);
        assert!(multiplicador_categoria("knowledge", Some(&senales)) > 1.0);
        assert_eq!(multiplicador_categoria("quality", Some(&senales)), 1.0);
    }

    #[test]
    fn tope_25_porciento() {
        let g = tmpdir("m3");
        let eventos: Vec<(i64, &str)> = (0..50).map(|i| (i % 20, "negative")).collect();
        escribir_feedback(&g.0, &eventos);
        let senales = leer_senales(&g.0, VENTANA_DIAS_DEFAULT);
        let m = multiplicador_categoria("quality", Some(&senales));
        assert!((m - 1.25).abs() < 1e-12, "{m}");
    }

    #[test]
    fn neutro_es_neutro() {
        let g = tmpdir("m4");
        escribir_feedback(&g.0, &[(1, "positive"), (2, "negative")]);
        let senales = leer_senales(&g.0, VENTANA_DIAS_DEFAULT);
        assert_eq!(multiplicador_categoria("quality", Some(&senales)), 1.0);
    }

    #[test]
    fn scheduler_con_senales_espejo_fase_e() {
        use crate::models::{Action, Categoria, Costo};
        use crate::registry::Registry;
        use crate::scheduler::Scheduler;
        use crate::store::PreferencesStore;

        let g = tmpdir("sc");
        let prefs = PreferencesStore::new(&g.0);
        let mut registry = Registry::new();
        registry
            .register(
                Action::new("qual.y", "t", Categoria::Quality, "e")
                    .unwrap()
                    .reversible(true)
                    .undo(std::sync::Arc::new(|| ActionResult::new(true, "")))
                    .cost(Costo::Instant),
            )
            .unwrap();

        let sin = Scheduler::new(&prefs).propose(&registry, false)[0].score;
        let con = Scheduler::new(&prefs)
            .with_senales(MemorySignals::new(0, 10))
            .propose(&registry, false)[0]
            .score;
        assert!((con - sin * 1.25).abs() < 1e-9);

        let mut registry2 = Registry::new();
        registry2
            .register(
                Action::new("learn.x", "t", Categoria::Learning, "e")
                    .unwrap()
                    .reversible(true)
                    .undo(std::sync::Arc::new(|| ActionResult::new(true, ""))),
            )
            .unwrap();
        let sin = Scheduler::new(&prefs).propose(&registry2, false)[0].score;
        let con = Scheduler::new(&prefs)
            .with_senales(MemorySignals::new(0, 10))
            .propose(&registry2, false)[0]
            .score;
        assert_eq!(con, sin);
    }
}
