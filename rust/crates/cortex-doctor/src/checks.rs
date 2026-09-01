//! Tipos de salida del doctor — espejo de `DoctorCheck`/`DoctorReport`.

use std::path::PathBuf;

use serde::{Deserialize, Serialize};

pub type DoctorSeverity = &'static str;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DoctorCheck {
    pub name: String,
    pub ok: bool,
    pub severity: String,
    pub detail: String,
}

impl DoctorCheck {
    pub fn new(
        name: impl Into<String>,
        ok: bool,
        severity: impl Into<String>,
        detail: impl Into<String>,
    ) -> Self {
        Self {
            name: name.into(),
            ok,
            severity: severity.into(),
            detail: detail.into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DoctorReport {
    pub project_root: PathBuf,
    pub checks: Vec<DoctorCheck>,
}

impl DoctorReport {
    /// `has_failures`: algún check !ok con severity "fail".
    pub fn has_failures(&self) -> bool {
        self.checks.iter().any(|c| !c.ok && c.severity == "fail")
    }

    /// `has_warnings`: algún check !ok con severity "warn".
    pub fn has_warnings(&self) -> bool {
        self.checks.iter().any(|c| !c.ok && c.severity == "warn")
    }
}
