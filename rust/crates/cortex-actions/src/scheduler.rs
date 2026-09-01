//! Puerto de `cortex/action_engine/scheduler.py` (Obra 05 Fase B, plan §3.4).
//!
//! Evalúa precondiciones + preferencias, calcula score
//! (impacto × frescura − costo) y devuelve máximo `max_visible` propuestas.

use std::collections::HashMap;

use crate::models::{costo_penalizacion, impacto_base, redondear, Action, ProposedAction};
use crate::registry::Registry;
use crate::signals::multiplicador_categoria;
use crate::signals::MemorySignals;
use crate::store::PreferencesStore;

pub const MAX_VISIBLE_DEFAULT: usize = 5;

/// Evalúa el registry y propone acciones priorizadas.
pub struct Scheduler<'a> {
    pub preferences: &'a PreferencesStore,
    pub max_visible: usize,
    /// frescura: cuántas ejecuciones recientes de la misma acción bajan su
    /// prioridad. v0: fijo.
    pub frescura: f64,
    pub extra_reasons: HashMap<String, Vec<String>>,
    /// Señales de feedback real (Fase E): dominio negativo sube quality/
    /// maintenance; positivo sube learning/knowledge. Tope ±25%.
    pub senales: Option<MemorySignals>,
}

impl<'a> Scheduler<'a> {
    pub fn new(preferences: &'a PreferencesStore) -> Self {
        Self {
            preferences,
            max_visible: MAX_VISIBLE_DEFAULT,
            frescura: 1.0,
            extra_reasons: HashMap::new(),
            senales: None,
        }
    }

    pub fn max_visible(mut self, max_visible: usize) -> Self {
        self.max_visible = max_visible;
        self
    }

    pub fn with_senales(mut self, senales: MemorySignals) -> Self {
        self.senales = Some(senales);
        self
    }

    pub fn with_extra_reasons(mut self, extra: HashMap<String, Vec<String>>) -> Self {
        self.extra_reasons = extra;
        self
    }

    fn score(&self, action: &Action) -> f64 {
        let impacto = impacto_base(action.category.as_str());
        let penalizacion_costo = costo_penalizacion(action.cost.as_str());
        let multiplicador_aprendido = self.preferences.penalizacion_skips(&action.id);
        let base = (impacto * self.frescura - penalizacion_costo) * multiplicador_aprendido;
        base * multiplicador_categoria(action.category.as_str(), self.senales.as_ref())
    }

    fn fallidas(action: &Action, deep: bool) -> Vec<String> {
        action
            .preconditions
            .iter()
            .filter(|c| !c.cumple(deep))
            .map(|c| c.description.clone())
            .collect()
    }

    /// Acciones ofrecibles ahora mismo.
    ///
    /// `deep=false` (on-open): snapshot barato — los checks marcados
    /// `deep_only` se omiten. `deep=true` (--all/on-schedule): escaneo
    /// completo incluyendo los costosos.
    pub fn propose(&self, registry: &Registry, deep: bool) -> Vec<ProposedAction> {
        let mut propuestas: Vec<ProposedAction> = Vec::new();
        for action in registry.all() {
            if self.preferences.nunca_mas(&action.id) {
                continue;
            }
            if !Self::fallidas(action, deep).is_empty() {
                continue;
            }
            let mut razones = vec![format!("impacto {}", action.category)];
            if let Some(extra) = self.extra_reasons.get(&action.id) {
                razones.extend(extra.iter().cloned());
            }
            propuestas.push(ProposedAction {
                action_id: action.id.clone(),
                score: redondear(self.score(action), 3),
                reasons: razones,
            });
        }
        // Python: sort(reverse=True) es estable ⇒ a igual score gana el orden
        // de inserción del registry. Rust sort_by también es estable.
        propuestas.sort_by(|a, b| b.score.total_cmp(&a.score));
        propuestas.truncate(self.max_visible);
        propuestas
    }

    /// Para cada acción NO propuesta: qué precondiciones fallaron.
    pub fn explain_why_not(&self, registry: &Registry, deep: bool) -> Vec<(String, Vec<String>)> {
        let mut detalle = Vec::new();
        for action in registry.all() {
            if self.preferences.nunca_mas(&action.id) {
                detalle.push((
                    action.id.clone(),
                    vec!["suprimida por preferencia ('nunca más')".to_string()],
                ));
                continue;
            }
            let fallidas = Self::fallidas(action, deep);
            if !fallidas.is_empty() {
                detalle.push((action.id.clone(), fallidas));
            }
        }
        detalle
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{ActionResult, Categoria, Check, Costo};
    use std::sync::Arc;

    struct Tmp(PathBuf);
    impl Drop for Tmp {
        fn drop(&mut self) {
            std::fs::remove_dir_all(&self.0).ok();
        }
    }

    use std::path::PathBuf;

    fn tmpdir(tag: &str) -> Tmp {
        let d = std::env::temp_dir().join(format!(
            "cortex-actions-sched-{tag}-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        std::fs::create_dir_all(&d).unwrap();
        Tmp(d)
    }

    fn accion_ok(id: &str) -> Action {
        Action::new(
            id,
            "Acción de prueba",
            Categoria::Maintenance,
            "no cambia nada real",
        )
        .unwrap()
        .reversible(true)
        .undo(Arc::new(|| ActionResult::new(true, "deshecho")))
        .cost(Costo::Instant)
        .auto_ok(true)
        .run_fn(|dry_run| {
            if dry_run {
                ActionResult::new(true, "[dry-run] simulado")
            } else {
                ActionResult::new(true, "hecho")
            }
        })
    }

    #[test]
    fn precondicion_falla_no_ofrece() {
        let g = tmpdir("p1");
        let prefs = PreferencesStore::new(&g.0);
        let mut registry = Registry::new();
        registry
            .register(accion_ok("test.accion").preconditions(vec![Check::new("nunca", || false)]))
            .unwrap();
        let sched = Scheduler::new(&prefs);

        assert!(sched.propose(&registry, false).is_empty());
        let detalle = sched.explain_why_not(&registry, false);
        assert_eq!(detalle[0].1[0], "nunca");
    }

    #[test]
    fn nunca_mas_suprime() {
        let g = tmpdir("p2");
        let prefs = PreferencesStore::new(&g.0);
        let mut registry = Registry::new();
        registry.register(accion_ok("test.accion")).unwrap();
        let sched = Scheduler::new(&prefs);

        assert_eq!(sched.propose(&registry, false).len(), 1);
        prefs.registrar("test.accion", "never").unwrap();
        assert!(sched.propose(&registry, false).is_empty());
        let detalle = sched.explain_why_not(&registry, false);
        assert!(detalle[0].1[0].contains("preferencia"));
    }

    #[test]
    fn skips_bajan_score_y_accepts_compensan() {
        let g = tmpdir("p3");
        let prefs = PreferencesStore::new(&g.0);
        let mut registry = Registry::new();
        registry.register(accion_ok("test.accion")).unwrap();

        let base = Scheduler::new(&prefs).propose(&registry, false)[0].score;

        prefs.registrar("test.accion", "skip").unwrap();
        let tras_skip = Scheduler::new(&prefs).propose(&registry, false)[0].score;
        assert!(tras_skip < base);

        prefs.registrar("test.accion", "accept").unwrap();
        prefs.registrar("test.accion", "accept").unwrap();
        let tras_accepts = Scheduler::new(&prefs).propose(&registry, false)[0].score;
        assert_eq!(tras_accepts, base);
    }

    #[test]
    fn max_visible() {
        let g = tmpdir("p4");
        let prefs = PreferencesStore::new(&g.0);
        let mut registry = Registry::new();
        for i in 0..8 {
            registry.register(accion_ok(&format!("test.a{i}"))).unwrap();
        }
        let sched = Scheduler::new(&prefs).max_visible(5);
        assert_eq!(sched.propose(&registry, false).len(), 5);
    }

    #[test]
    fn orden_estable_por_score() {
        let g = tmpdir("p5");
        let prefs = PreferencesStore::new(&g.0);
        let mut registry = Registry::new();
        // misma categoría/costo → mismo score ⇒ orden = inserción (estable)
        registry.register(accion_ok("b.segundo")).unwrap();
        registry.register(accion_ok("a.primero")).unwrap();
        let sched = Scheduler::new(&prefs);
        let props = sched.propose(&registry, false);
        let ids: Vec<&str> = props.iter().map(|p| p.action_id.as_str()).collect();
        assert_eq!(ids, vec!["b.segundo", "a.primero"]);
    }
}
