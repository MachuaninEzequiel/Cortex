//! Puerto de `cortex/action_engine/metrics.py` (Obra 05 Fase E, plan §3.6).
//!
//! - `pct_motor` = ejecuciones decididas por el motor (auto-ok, via=auto)
//!   sobre el total de ejecuciones reales (no dry-run).
//! - Target declarado por el dueño: abrir el menú de acciones <1 vez por día
//!   de trabajo activo ⇒ proxy medible hoy: pct_motor alto con volumen
//!   estable de ejecuciones y dias_con_interaccion bajo.

use std::collections::BTreeSet;

use crate::store::ActionLog;

#[derive(Debug, Clone)]
pub struct MetricasMotor {
    pub total_ejecuciones: usize,
    pub via_auto: usize,
    pub via_usuario: usize,
    pub dry_runs: usize,
    pub pct_motor: f64,
    /// Ordenado por conteo descendente; a igual conteo gana la primera
    /// aparición en el log (sort estable de Python).
    pub acciones_por_id: Vec<(String, usize)>,
    pub dias_con_interaccion: Vec<String>,
}

/// Espejo exacto de `calcular_metricas`.
pub fn calcular_metricas(log: &ActionLog) -> MetricasMotor {
    let mut total = 0usize;
    let mut auto = 0usize;
    let mut usuario = 0usize;
    let mut dry = 0usize;
    // Vec preserva orden de primera aparición (dict Python); BTreeSet para días.
    let mut por_id: Vec<(String, usize)> = Vec::new();
    let mut dias: BTreeSet<String> = BTreeSet::new();

    for entry in log.load() {
        let es_dry = entry
            .get("dry_run")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
        if es_dry {
            dry += 1;
            continue;
        }
        total += 1;
        if entry.get("via").and_then(|v| v.as_str()) == Some("auto") {
            auto += 1;
        } else {
            usuario += 1;
        }
        let accion_id = entry
            .get("id")
            .and_then(|v| v.as_str())
            .unwrap_or("?")
            .to_string();
        match por_id.iter_mut().find(|(k, _)| *k == accion_id) {
            Some((_, n)) => *n += 1,
            None => por_id.push((accion_id, 1)),
        }
        // str(entry.get("ts", ""))[:10] — si hay algo no vacío, entra al set.
        let ts_full = entry
            .get("ts")
            .map(|v| match v {
                serde_json::Value::String(s) => s.clone(),
                other => other.to_string(),
            })
            .unwrap_or_default();
        let ts: String = ts_full.chars().take(10).collect();
        if !ts.is_empty() {
            dias.insert(ts);
        }
    }

    // round(auto / total * 100, 1) si total>0, si no 0.0.
    let pct = if total > 0 {
        crate::models::redondear(auto as f64 / total as f64 * 100.0, 1)
    } else {
        0.0
    };

    // dict(sorted(por_id.items(), key=lambda kv: -kv[1])) — estable ⇒ orden de
    // primera aparición para iguales conteos.
    let mut acciones_por_id = por_id;
    acciones_por_id.sort_by_key(|(_, n)| std::cmp::Reverse(*n));

    MetricasMotor {
        total_ejecuciones: total,
        via_auto: auto,
        via_usuario: usuario,
        dry_runs: dry,
        pct_motor: pct,
        acciones_por_id,
        dias_con_interaccion: dias.into_iter().collect(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::store::OrderedEntry;
    use serde_json::json;
    use std::path::PathBuf;

    struct Tmp(PathBuf);
    impl Drop for Tmp {
        fn drop(&mut self) {
            std::fs::remove_dir_all(&self.0).ok();
        }
    }

    fn tmpdir(tag: &str) -> Tmp {
        let d = std::env::temp_dir().join(format!(
            "cortex-actions-met-{tag}-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        std::fs::create_dir_all(&d).unwrap();
        Tmp(d)
    }

    /// Espejo de TestMetricasMotor.test_calculo_pct_motor.
    #[test]
    fn calculo_pct_motor() {
        let g = tmpdir("pct");
        let log = ActionLog::new(&g.0);
        let casos = [
            ("a.ok", false, "auto"),
            ("b.ok", false, "auto"),
            ("c.x", false, "user"),
            ("d.dry", true, "auto"),
        ];
        for (id, dry, via) in casos {
            let mut e = OrderedEntry::new();
            e.set("id", json!(id));
            e.set("ts", json!("2026-08-24T10:00:00+00:00"));
            e.set("dry_run", json!(dry));
            e.set("via", json!(via));
            log.append(e).unwrap();
        }
        let m = calcular_metricas(&log);
        assert_eq!(m.total_ejecuciones, 3); // dry-runs no cuentan
        assert_eq!(m.via_auto, 2);
        assert_eq!(m.via_usuario, 1);
        assert!((m.pct_motor - 66.7).abs() < 1e-9);
        assert!(!m.dias_con_interaccion.is_empty());
    }

    #[test]
    fn vacio() {
        let g = tmpdir("empty");
        let m = calcular_metricas(&ActionLog::new(&g.0));
        assert_eq!(m.total_ejecuciones, 0);
        assert_eq!(m.pct_motor, 0.0);
    }

    #[test]
    fn por_accion_orden_estable_por_conteo() {
        let g = tmpdir("orden");
        let log = ActionLog::new(&g.0);
        for (id, via) in [
            ("x.a", "user"),
            ("y.b", "user"),
            ("x.a", "user"),
            ("z.c", "user"),
            ("x.a", "user"),
            ("y.b", "user"),
        ] {
            let mut e = OrderedEntry::new();
            e.set("id", json!(id));
            e.set("ts", json!("2026-08-24T10:00:00+00:00"));
            e.set("dry_run", json!(false));
            e.set("via", json!(via));
            log.append(e).unwrap();
        }
        let m = calcular_metricas(&log);
        let ids: Vec<(&str, usize)> = m
            .acciones_por_id
            .iter()
            .map(|(k, v)| (k.as_str(), *v))
            .collect();
        assert_eq!(ids, vec![("x.a", 3), ("y.b", 2), ("z.c", 1)]);
    }
}
