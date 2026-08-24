//! Puerto de `cortex/action_engine/learning.py` — paso APRENDER v0
//! (plan §3.6). Bucle mínimo: cada decisión (accept/skip/never) se persiste
//! en `.cortex/actions.yaml` y ajusta el score futuro vía
//! `PreferencesStore::penalizacion_skips`.

use std::path::Path;

use crate::store::PreferencesStore;

pub struct Learner {
    preferences: PreferencesStore,
}

impl Learner {
    pub fn new(directory: &Path) -> Self {
        Self {
            preferences: PreferencesStore::new(directory),
        }
    }

    pub fn from_store(preferences: PreferencesStore) -> Self {
        Self { preferences }
    }

    /// accept | skip | never — persiste y ajusta prioridad futura.
    pub fn registrar_decision(&self, action_id: &str, eleccion: &str) -> Result<(), String> {
        self.preferences.registrar(action_id, eleccion)
    }

    pub fn suprimida(&self, action_id: &str) -> bool {
        self.preferences.nunca_mas(action_id)
    }

    pub fn multiplicador(&self, action_id: &str) -> f64 {
        self.preferences.penalizacion_skips(action_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bucle_minimo_aprender() {
        let dir = std::env::temp_dir().join(format!(
            "cortex-actions-learn-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        let learner = Learner::new(&dir);
        assert!(!learner.suprimida("a.b"));
        assert!((learner.multiplicador("a.b") - 1.0).abs() < 1e-12);
        learner.registrar_decision("a.b", "skip").unwrap();
        assert!((learner.multiplicador("a.b") - 0.85).abs() < 1e-12);
        learner.registrar_decision("a.b", "never").unwrap();
        assert!(learner.suprimida("a.b"));
        std::fs::remove_dir_all(dir).ok();
    }
}
