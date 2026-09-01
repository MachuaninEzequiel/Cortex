//! Puerto de `cortex.autopilot.lifecycle`: tipos request/result de los
//! flujos del servicio. La orquestación real queda tras el motor de sesiones.

use serde::{Deserialize, Serialize};

use crate::policies::AutopilotMode;

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct AutopilotStartRequest {
    pub mode: Option<AutopilotMode>,
}

/// `preflight`: dry-run del pipeline de detección (no muta sesión).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PreflightResult {
    pub task_type: String,
    pub confidence: f64,
    pub reason: String,
    pub suggested_complexity: String,
    /// Modo que aplicaría el servicio según config (informativo).
    pub policy_mode: String,
}

/// Alias de reloj del sistema para el enforcer por defecto.
pub type SystemClockAlias = cortex_enterprise::clock::SystemClock;
