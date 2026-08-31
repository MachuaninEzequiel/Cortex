//! cortex-brain-app — shell Tauri de Cortex Brain (Obra 20, G-A1).
//!
//! Estado: scaffolding mínimo. La app abre una ventana Tauri con un
//! "Hello, Cortex Brain" del lado de React (apps/brain-ui/).
//!
//! Próximos gates:
//! - G-A2: IPC server (JSON-lines por socket).
//! - G-A3: scan recursivo de proyectos.
//! - G-A4: integración con `cortex_brain` (lib) para chat in-process.
//!
//! Spec: docs/transformacion/20-CORTEX-BRAIN-APP.md

#![forbid(unsafe_code)]

/// Roles del binario unificado `cortex-brain` (decisión del dueño,
/// doc 20 §12.1 opción C). En G-A1 sólo se implementa `App`; los
/// flags `--query` y `--projects-list` se cablean en G-A2/G-A3.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Role {
    /// Default: levanta la GUI Tauri.
    App,
    /// Cliente IPC: manda una query al server y sale. (G-A9.)
    QueryClient,
    /// Lista proyectos detectados y sale. (G-A3.)
    ProjectsList,
}

impl Role {
    /// Decide el rol a partir de los argumentos del proceso.
    ///
    /// - `--query <text>` ⇒ `QueryClient` (el resto se ignora).
    /// - `--projects-list` ⇒ `ProjectsList`.
    /// - cualquier otra cosa (incluido "sin args") ⇒ `App`.
    pub fn from_argv(argv: &[String]) -> Self {
        if argv.iter().any(|a| a == "--query") {
            Role::QueryClient
        } else if argv.iter().any(|a| a == "--projects-list") {
            Role::ProjectsList
        } else {
            Role::App
        }
    }
}

/// Construye la app Tauri.
///
/// En G-A1 sólo se llama desde el entrypoint GUI; en gates siguientes
/// se le agregan los commands (Tauri commands invocados desde React).
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|_app| Ok(()))
        .run(tauri::generate_context!())
        .expect("error al iniciar Cortex Brain");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sin_args_es_app() {
        let argv: Vec<String> = vec![];
        assert_eq!(Role::from_argv(&argv), Role::App);
    }

    #[test]
    fn flag_query_es_query_client() {
        let argv: Vec<String> = vec!["cortex-brain".into(), "--query".into()];
        assert_eq!(Role::from_argv(&argv), Role::QueryClient);
    }

    #[test]
    fn flag_projects_list_es_projects_list() {
        let argv: Vec<String> = vec!["cortex-brain".into(), "--projects-list".into()];
        assert_eq!(Role::from_argv(&argv), Role::ProjectsList);
    }

    #[test]
    fn app_tiene_prioridad_si_no_hay_flags_relevantes() {
        let argv: Vec<String> = vec![
            "cortex-brain".into(),
            "--project-root".into(),
            "/tmp".into(),
        ];
        assert_eq!(Role::from_argv(&argv), Role::App);
    }
}
