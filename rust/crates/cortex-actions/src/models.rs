//! Puerto de `cortex/action_engine/models.py` (Obra 05 Fase B, §3.2 del plan).
//!
//! Contrato duro replicado:
//! 1. Toda acción delega en su servicio — nunca reimplementa lógica.
//! 2. Las precondiciones se evalúan ANTES de ofrecer la acción.
//! 3. `reversible=false` ⇒ requiere aprobación SIEMPRE (sin modo auto).
//! 4. Toda ejecución se registra en `.cortex/action_log.jsonl`.
//! 5. Dry-run nativo: `run(true)` devuelve el efecto sin escribir.

use std::collections::BTreeMap;
use std::fmt;
use std::sync::Arc;

use chrono::{SecondsFormat, Utc};

/// Categorías del catálogo (Literal de Python).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Categoria {
    Setup,
    Quality,
    Maintenance,
    Knowledge,
    Learning,
}

impl Categoria {
    pub fn as_str(self) -> &'static str {
        match self {
            Categoria::Setup => "setup",
            Categoria::Quality => "quality",
            Categoria::Maintenance => "maintenance",
            Categoria::Knowledge => "knowledge",
            Categoria::Learning => "learning",
        }
    }
}

impl fmt::Display for Categoria {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Costos declarados (Literal de Python).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Costo {
    Instant,
    Seconds,
    Minutes,
}

impl Costo {
    pub fn as_str(self) -> &'static str {
        match self {
            Costo::Instant => "instant",
            Costo::Seconds => "seconds",
            Costo::Minutes => "minutes",
        }
    }
}

impl fmt::Display for Costo {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Trigger de ejecución (Literal de Python).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Trigger {
    OnOpen,
    OnEvent,
    OnSchedule,
}

impl Trigger {
    pub fn as_str(self) -> &'static str {
        match self {
            Trigger::OnOpen => "on-open",
            Trigger::OnEvent => "on-event",
            Trigger::OnSchedule => "on-schedule",
        }
    }
}

/// Tabla estática de impacto por categoría (plan §3.4): setup > calidad >
/// mantenimiento > conocimiento > aprendizaje. Refinada luego por aprendizaje.
pub fn impacto_base(categoria: &str) -> f64 {
    match categoria {
        "setup" => 10.0,
        "quality" => 8.0,
        "maintenance" => 6.0,
        "knowledge" => 4.0,
        "learning" => 3.0,
        _ => 2.0,
    }
}

pub fn costo_penalizacion(costo: &str) -> f64 {
    match costo {
        "instant" => 0.0,
        "seconds" => 1.0,
        "minutes" => 3.0,
        _ => 1.0,
    }
}

/// `ahora_iso()` — `datetime.now(UTC).isoformat(timespec="seconds")`.
pub fn ahora_iso() -> String {
    Utc::now().to_rfc3339_opts(SecondsFormat::Secs, false)
}

/// Resultado de ejecutar una acción (dataclass frozen).
#[derive(Debug, Clone)]
pub struct ActionResult {
    pub ok: bool,
    pub message: String,
    pub details: BTreeMap<String, serde_json::Value>,
}

impl ActionResult {
    pub fn new(ok: bool, message: impl Into<String>) -> Self {
        Self {
            ok,
            message: message.into(),
            details: BTreeMap::new(),
        }
    }

    /// `ActionResult.dry(effect)` — mensaje `[dry-run] …`.
    pub fn dry(effect: impl Into<String>) -> Self {
        Self::new(true, format!("[dry-run] {}", effect.into()))
    }

    /// `ActionResult.fail(message)`.
    pub fn fail(message: impl Into<String>) -> Self {
        Self::new(false, message)
    }

    pub fn with_details(mut self, details: BTreeMap<String, serde_json::Value>) -> Self {
        self.details = details;
        self
    }
}

/// Precondición pura: predicado sin efectos + razón legible si falla.
///
/// `deep_only=true`: el check es costoso y SOLO se evalúa en modo deep
/// (`cortex next --all` / on-schedule). En snapshot on-open se asume cumplido.
pub struct Check {
    pub description: String,
    #[allow(clippy::type_complexity)]
    predicate: Box<dyn Fn() -> bool + Send + Sync + 'static>,
    pub deep_only: bool,
}

impl fmt::Debug for Check {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Check")
            .field("description", &self.description)
            .field("deep_only", &self.deep_only)
            .finish_non_exhaustive()
    }
}

impl Check {
    pub fn new(
        description: impl Into<String>,
        predicate: impl Fn() -> bool + Send + Sync + 'static,
    ) -> Self {
        Self {
            description: description.into(),
            predicate: Box::new(predicate),
            deep_only: false,
        }
    }

    pub fn deep(
        description: impl Into<String>,
        predicate: impl Fn() -> bool + Send + Sync + 'static,
    ) -> Self {
        Self {
            description: description.into(),
            predicate: Box::new(predicate),
            deep_only: true,
        }
    }

    /// `cumple(deep=…)`: un check roto nunca ofrece la acción (excepción ⇒ false).
    pub fn cumple(&self, deep: bool) -> bool {
        if self.deep_only && !deep {
            return true;
        }
        // Espejo del try/except de Python: un panic del predicado cuenta como
        // check roto (nunca revienta el scheduler).
        std::panic::catch_unwind(std::panic::AssertUnwindSafe(&self.predicate)).unwrap_or(false)
    }
}

/// Acción del catálogo (dataclass frozen con validaciones de contrato).
pub struct Action {
    pub id: String,
    pub title: String,
    pub category: Categoria,
    pub effect: String,
    pub preconditions: Vec<Check>,
    pub reversible: bool,
    pub undo: Option<Arc<dyn Fn() -> ActionResult + Send + Sync>>,
    pub cost: Costo,
    pub auto_ok: bool,
    #[allow(clippy::type_complexity)]
    pub run: Arc<dyn Fn(bool) -> ActionResult + Send + Sync>,
}

impl fmt::Debug for Action {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Action")
            .field("id", &self.id)
            .field("title", &self.title)
            .field("category", &self.category)
            .field("effect", &self.effect)
            .field("reversible", &self.reversible)
            .field("cost", &self.cost)
            .field("auto_ok", &self.auto_ok)
            .finish()
    }
}

impl Action {
    /// Constructor con las validaciones de `__post_init__`.
    ///
    /// Errores (mismos mensajes que Python):
    /// - auto_ok requiere reversible=true y cost=instant (regla dura #3);
    /// - reversible=true exige undo;
    /// - id con formato 'dominio.accion'.
    pub fn new(
        id: impl Into<String>,
        title: impl Into<String>,
        category: Categoria,
        effect: impl Into<String>,
    ) -> Result<Self, String> {
        let id = id.into();
        if !id.contains('.') || id.is_empty() {
            return Err(format!("id inválido: '{id}' — formato 'dominio.accion'"));
        }
        Ok(Self {
            id,
            title: title.into(),
            category,
            effect: effect.into(),
            preconditions: Vec::new(),
            reversible: false,
            undo: None,
            cost: Costo::Seconds,
            auto_ok: false,
            run: Arc::new(|_dry_run| ActionResult::fail("acción sin implementar")),
        })
    }

    pub fn preconditions(mut self, checks: Vec<Check>) -> Self {
        self.preconditions = checks;
        self
    }

    pub fn reversible(mut self, reversible: bool) -> Self {
        self.reversible = reversible;
        self
    }

    pub fn undo(mut self, undo: Arc<dyn Fn() -> ActionResult + Send + Sync>) -> Self {
        self.undo = Some(undo);
        self
    }

    pub fn cost(mut self, cost: Costo) -> Self {
        self.cost = cost;
        self
    }

    pub fn auto_ok(mut self, auto_ok: bool) -> Self {
        self.auto_ok = auto_ok;
        self
    }

    pub fn run_fn(mut self, run: impl Fn(bool) -> ActionResult + Send + Sync + 'static) -> Self {
        self.run = Arc::new(run);
        self
    }

    /// Valida el contrato y devuelve la acción (panic con el mensaje de
    /// error si viola contrato — espejo del ValueError de __post_init__).
    pub fn checked(self) -> Self {
        if let Err(e) = self.validate() {
            panic!("{e}");
        }
        self
    }

    /// Validaciones de contrato de `__post_init__`.
    pub fn validate(&self) -> Result<(), String> {
        if self.auto_ok && !(self.reversible && self.cost == Costo::Instant) {
            return Err(format!(
                "{}: auto_ok requiere reversible=True y cost='instant' (regla dura #3 del contrato)",
                self.id
            ));
        }
        if self.reversible && self.undo.is_none() {
            return Err(format!(
                "{}: reversible=True exige undo (contrato)",
                self.id
            ));
        }
        Ok(())
    }
}

/// Una acción que el scheduler ofrece tras evaluar precondiciones.
#[derive(Debug, Clone)]
pub struct ProposedAction {
    pub action_id: String,
    pub score: f64,
    /// Por qué se propone: `["impacto {categoria}"] + extra_reasons`.
    pub reasons: Vec<String>,
}

/// Decisión del usuario/aprendizaje sobre una acción propuesta.
#[derive(Debug, Clone)]
pub struct Decision {
    pub action_id: String,
    /// "accept" | "skip" | "never"
    pub eleccion: String,
    pub ts: String,
}

impl Decision {
    pub fn new(action_id: impl Into<String>, eleccion: impl Into<String>) -> Self {
        Self {
            action_id: action_id.into(),
            eleccion: eleccion.into(),
            ts: ahora_iso(),
        }
    }
}

/// Redondeo compatible con `round(x, n)` de Python (half-to-even decimal).
/// Sobre valores sin empate decimal exacto coincide cualquier redondeo
/// correcto; acá se delega en el formateo shortest-correct de Rust.
pub fn redondear(x: f64, decimales: usize) -> f64 {
    let s = format!("{x:.decimales$}");
    s.parse().unwrap_or(x)
}

#[cfg(test)]
mod tests {
    use super::*;

    // Espejo de TestContrato (tests/unit/action_engine/test_core.py).
    #[test]
    fn auto_ok_exige_reversible_e_instant() {
        let a = Action::new(
            "test.accion",
            "Acción de prueba",
            Categoria::Maintenance,
            "e",
        )
        .unwrap()
        .reversible(false)
        .auto_ok(true)
        .validate();
        assert!(a.unwrap_err().contains("auto_ok"));

        let b = Action::new(
            "test.accion",
            "Acción de prueba",
            Categoria::Maintenance,
            "e",
        )
        .unwrap()
        .reversible(true)
        .cost(Costo::Minutes)
        .auto_ok(true)
        .validate();
        assert!(b.unwrap_err().contains("auto_ok"));
    }

    #[test]
    fn reversible_exige_undo() {
        let a = Action::new("test.accion", "t", Categoria::Maintenance, "e")
            .unwrap()
            .reversible(true)
            .validate();
        assert!(a.unwrap_err().contains("undo"));
    }

    #[test]
    fn id_formato_dominio_accion() {
        let err = Action::new("sinpunto", "t", Categoria::Maintenance, "e").unwrap_err();
        assert!(err.contains("id inválido"));
    }

    #[test]
    fn check_roto_nunca_revienta() {
        let c = Check::new("roto", || panic!("boom"));
        assert!(!c.cumple(false));
        let ok = Check::new("ok", || true);
        assert!(ok.cumple(false));
    }

    #[test]
    fn deep_only_se_omite_en_snapshot() {
        let c = Check::deep("caro", || false);
        assert!(c.cumple(false)); // snapshot on-open: asumido cumplido
        assert!(!c.cumple(true)); // deep: se evalúa de verdad
    }

    #[test]
    fn dry_y_fail_mensajes() {
        assert_eq!(ActionResult::dry("efecto").message, "[dry-run] efecto");
        assert!(!ActionResult::fail("mal").ok);
        assert!(ahora_iso().len() >= 19);
    }

    #[test]
    fn redondeo_compatible_python() {
        assert_eq!(redondear(4.25, 3), 4.25);
        assert_eq!(redondear(66.666666, 1), 66.7);
        assert_eq!(redondear(8.0, 3), 8.0);
    }
}
