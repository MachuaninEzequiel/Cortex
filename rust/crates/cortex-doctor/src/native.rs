//! Adapter `NativeDoctorBackend`: cierra el seam enterprise→doctor dejado en
//! P12B-3. Implementa `cortex_enterprise::reporting::DoctorBackend`
//! convirtiendo el reporte nativo a las vistas neutrales.

use std::path::{Path, PathBuf};

use crate::checks::DoctorCheck;
use crate::doctor::run_doctor;
use cortex_enterprise::error::EnterpriseError;
use cortex_enterprise::reporting::DoctorScope;

/// Resolve() no estricto de Python: canonicaliza el ancestro existente más
/// profundo y normaliza `.`/`..` del resto (mismo algoritmo que
/// cortex-enterprise::review_knowledge).
pub(crate) fn python_resolve(path: &Path) -> PathBuf {
    let abs = if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir().unwrap_or_default().join(path)
    };
    let comps: Vec<std::path::Component> = abs.components().collect();
    let mut idx = comps.len();
    while idx > 0 {
        let candidate: PathBuf = comps[..idx].iter().collect();
        if candidate.exists() {
            break;
        }
        idx -= 1;
    }
    let base: PathBuf = comps[..idx].iter().collect();
    let mut out = std::fs::canonicalize(&base).unwrap_or(base);
    for comp in &comps[idx..] {
        match comp {
            std::path::Component::CurDir => {}
            std::path::Component::ParentDir => {
                out.pop();
            }
            other => out.push(other.as_os_str()),
        }
    }
    out
}
use cortex_enterprise::reporting::{DoctorBackend, DoctorCheckView, DoctorReportView};

pub struct NativeDoctorBackend;

impl NativeDoctorBackend {
    pub fn new() -> Self {
        Self
    }
}

impl Default for NativeDoctorBackend {
    fn default() -> Self {
        Self::new()
    }
}

impl DoctorBackend for NativeDoctorBackend {
    fn run(
        &self,
        project_root: &Path,
        scope: DoctorScope,
    ) -> Result<DoctorReportView, EnterpriseError> {
        let scope = match scope {
            DoctorScope::Project => crate::doctor::DoctorScope::Project,
            DoctorScope::Enterprise => crate::doctor::DoctorScope::Enterprise,
        };
        let report = run_doctor(project_root, scope)?;
        let has_failures = report.has_failures();
        let has_warnings = report.has_warnings();
        Ok(DoctorReportView {
            project_root: report.project_root,
            has_failures,
            has_warnings,
            checks: report
                .checks
                .into_iter()
                .map(
                    |DoctorCheck {
                         name,
                         ok,
                         severity,
                         detail,
                     }| {
                        DoctorCheckView {
                            name,
                            ok,
                            severity,
                            detail,
                        }
                    },
                )
                .collect(),
        })
    }
}
