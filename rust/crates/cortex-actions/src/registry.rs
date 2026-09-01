//! Puerto de `cortex/action_engine/registry.py` — catálogo de acciones
//! registradas por id (sin duplicados). El orden de inserción es observable
//! (desempate estable del scheduler ⇒ debe replicarse con Vec).

use crate::models::Action;

pub struct Registry {
    acciones: Vec<Action>,
}

impl Default for Registry {
    fn default() -> Self {
        Self::new()
    }
}

impl Registry {
    pub fn new() -> Self {
        Self {
            acciones: Vec::new(),
        }
    }

    /// Registra una acción; duplicado ⇒ error (mismo mensaje que Python).
    pub fn register(&mut self, action: Action) -> Result<(), String> {
        if self.contains(&action.id) {
            return Err(format!("acción duplicada: {}", action.id));
        }
        self.acciones.push(action);
        Ok(())
    }

    pub fn get(&self, action_id: &str) -> Option<&Action> {
        self.acciones.iter().find(|a| a.id == action_id)
    }

    pub fn get_mut(&mut self, action_id: &str) -> Option<&mut Action> {
        self.acciones.iter_mut().find(|a| a.id == action_id)
    }

    pub fn all(&self) -> &[Action] {
        &self.acciones
    }

    pub fn len(&self) -> usize {
        self.acciones.len()
    }

    pub fn is_empty(&self) -> bool {
        self.acciones.is_empty()
    }

    pub fn contains(&self, action_id: &str) -> bool {
        self.get(action_id).is_some()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{ActionResult, Categoria};

    fn accion(id: &str) -> Action {
        Action::new(id, "t", Categoria::Maintenance, "e")
            .unwrap()
            .reversible(true)
            .undo(std::sync::Arc::new(|| ActionResult::new(true, "ok")))
    }

    #[test]
    fn duplicados_rechazados() {
        let mut r = Registry::new();
        r.register(accion("test.a")).unwrap();
        assert_eq!(
            r.register(accion("test.a")).unwrap_err(),
            "acción duplicada: test.a"
        );
    }

    #[test]
    fn orden_de_insercion_preservado() {
        let mut r = Registry::new();
        for id in ["b.x", "a.y", "c.z"] {
            r.register(accion(id)).unwrap();
        }
        let ids: Vec<&str> = r.all().iter().map(|a| a.id.as_str()).collect();
        assert_eq!(ids, vec!["b.x", "a.y", "c.z"]);
        assert!(r.contains("a.y"));
        assert_eq!(r.len(), 3);
    }
}
