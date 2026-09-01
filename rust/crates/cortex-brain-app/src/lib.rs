//! cortex-brain-app — shell Tauri de Cortex Brain (Obra 20, G-A1+).
//!
//! Estado: scaffolding + IPC esqueleto (G-A2) + scan de proyectos
//! (G-A3). La app abre una ventana Tauri con un "Hello, Cortex Brain"
//! del lado de React (apps/brain-ui/).
//!
//! Próximos gates:
//! - G-A4: integración con `cortex_brain` (lib) para chat in-process.
//! - G-A7: UI completa (sidebar con los proyectos de `projects.rs`).
//!
//! Spec: docs/transformacion/20-CORTEX-BRAIN-APP.md

#![allow(unsafe_code)] // std::env::set_var en tests con HOME_LOCK (serialización de test).

pub mod ipc;
pub mod projects;

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

/// Command Tauri: lista los proyectos desde el cache (rápido, no
/// recorre el árbol; elimina entradas stale). G-A7 lo invoca desde la
/// sidebar. Async para no bloquear el main thread de Tauri.
#[tauri::command]
async fn list_projects() -> Vec<projects::ProjectEntry> {
    projects::list_projects()
}

/// Command Tauri: scan completo de la raíz + reescritura del cache.
/// Operación cara (segundos en un home grande): async para no
/// bloquear el main thread de Tauri.
#[tauri::command]
async fn refresh_projects() -> Vec<projects::ProjectEntry> {
    projects::refresh_projects()
}

/// Construye la app Tauri.
///
/// G-A2: al setup, intenta bindear el server IPC. Si ya hay una
/// instancia escuchando, conecta como cliente y **continúa como GUI**
/// (no mata la instancia existente, no es nuestro trabajo decidir eso).
/// El server mismo vive en un thread dedicado, fuera del ciclo de
/// Tauri: acepta conexiones y por cada query loggea en stderr. El
/// loop de motor real (que responde al cliente) llega en G-A4; el
/// streaming de chunks reales en G-A6.
///
/// G-A3: registra los commands `list_projects` / `refresh_projects`
/// (sidebar de proyectos; el frontend los consume en G-A7).
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    use std::io::BufReader;

    match ipc::try_bind() {
        Ok(server) => {
            // Spawn del loop de accept en un thread dedicado. El handle
            // se descarta; el thread muere con el proceso.
            let _ = std::thread::Builder::new()
                .name("cortex-brain-ipc".into())
                .spawn(move || {
                    while let Ok(conn) = server.accept() {
                        let (raw_read, _write) = match conn.into_split() {
                            Ok(parts) => parts,
                            Err(e) => {
                                eprintln!("ipc: split falló: {e}");
                                continue;
                            }
                        };
                        // Por cada conexión entrante, leemos queries
                        // hasta EOF y las loggeamos. G-A4 las enruta al
                        // motor y responde por el `_write`. G-A6 lo hace
                        // en chunks streaming.
                        let _ = std::thread::spawn(move || {
                            let mut reader = BufReader::new(raw_read);
                            while let Ok(Some(req)) =
                                ipc::read_json_line::<ipc::QueryRequest, _>(&mut reader)
                            {
                                eprintln!(
                                    "ipc: query recibida: project={} text={:?} request_id={}",
                                    req.project, req.text, req.request_id
                                );
                            }
                        });
                    }
                });
        }
        Err(ipc::BindError::AlreadyBound(_)) => {
            // Hay otra instancia. Lo registramos; el comportamiento de
            // "forward to running instance" como cliente es responsabilidad
            // del flag --query (main.rs). Acá sólo dejamos el aviso.
            eprintln!(
                "cortex-brain: otra instancia ya está corriendo. Las queries por \
                 --query se mandan a esa instancia; esta GUI corre en paralelo."
            );
        }
        Err(ipc::BindError::NotSupported) => {
            eprintln!("cortex-brain: IPC no soportado en este OS (G-A2: sólo Unix)");
        }
        Err(e) => {
            eprintln!("cortex-brain: error al bindear IPC: {e}");
        }
    }

    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![list_projects, refresh_projects])
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
