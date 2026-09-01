//! cortex-brain-app — shell Tauri de Cortex Brain (Obra 20, G-A1+).
//!
//! Estado: scaffolding + IPC esqueleto (G-A2) + scan de proyectos
//! (G-A3) + chat in-process con el motor (G-A4). La app abre una
//! ventana Tauri con un "Hello, Cortex Brain" del lado de React
//! (apps/brain-ui/).
//!
//! Próximos gates:
//! - G-A5: integración Liquid real (feature `llama` + GGUF).
//! - G-A7: UI completa (sidebar con los proyectos de `projects.rs`,
//!   chat con el engine de `chat.rs`).
//!
//! Spec: docs/transformacion/20-CORTEX-BRAIN-APP.md

#![allow(unsafe_code)] // std::env::set_var en tests con HOME_LOCK (serialización de test).

use tauri::Manager;

pub mod chat;
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

/// Command Tauri: un turno de chat in-process con el motor (G-A4).
/// Usa el SharedEngine de la app (mismo estado que el server IPC),
/// resuelto via AppHandle: los commands async de Tauri exigen futures
/// Send + 'static y `State<'_, T>` prestado no lo cumple (doc de
/// Tauri 2: en async, resolver el estado adentro con `app.state`).
/// G-A7 lo invoca desde la UI por proyecto.
#[tauri::command]
async fn chat_turn(
    app: tauri::AppHandle,
    project: String,
    text: String,
) -> Result<chat::ChatTurn, String> {
    let engine = app.state::<chat::SharedEngine>();
    engine.respond(&project, &text)
}

/// Payload del evento `chat-chunk` emitido durante el streaming en vivo.
#[derive(Debug, Clone, serde::Serialize)]
pub struct ChatChunkPayload {
    pub request_id: String,
    pub chunk: String,
}

/// Command Tauri: turno de chat streaming (G-A7). Emite eventos
/// `chat-chunk` en vivo a medida que el motor genera piezas, y
/// devuelve el `ChatTurn` autoritativo final (con el texto procesado
/// y las tools) al terminar.
#[tauri::command]
async fn chat_turn_stream(
    app: tauri::AppHandle,
    project: String,
    text: String,
    request_id: String,
) -> Result<chat::ChatTurn, String> {
    use tauri::Emitter;
    let engine = app.state::<chat::SharedEngine>();
    let req_id = request_id.clone();
    let app_handle = app.clone();
    engine.respond_streaming(&project, &text, &mut move |piece: &str| {
        let payload = ChatChunkPayload {
            request_id: req_id.clone(),
            chunk: piece.to_string(),
        };
        let _ = app_handle.emit("chat-chunk", &payload);
    })
}

/// Command Tauri: devuelve los proyectos con backend actualmente
/// cargado en RAM (status bar live widget).
#[tauri::command]
async fn loaded_projects(app: tauri::AppHandle) -> Vec<String> {
    let engine = app.state::<chat::SharedEngine>();
    engine.loaded_projects()
}

/// Command Tauri: descarga backends inactivos (>90s) para liberar RAM.
/// Invocado periódicamente por el ticker de la UI.
#[tauri::command]
async fn reap_idle(app: tauri::AppHandle) {
    let engine = app.state::<chat::SharedEngine>();
    engine.reap_idle();
}

/// Command Tauri: lista de modelos GGUF detectados / elegibles.
#[tauri::command]
async fn list_models() -> Vec<chat::ModelEntry> {
    chat::list_available_models()
}

/// Payload del evento `download-progress` emitido durante la descarga de un modelo.
#[derive(Debug, Clone, serde::Serialize)]
pub struct DownloadProgressPayload {
    pub bytes_done: u64,
    pub bytes_total: Option<u64>,
    pub percentage: Option<f32>,
    pub status: String,
    pub error: Option<String>,
}

/// Command Tauri: descarga el modelo oficial (o custom URL) vía HttpSource
/// en un thread dedicado emitiendo eventos `download-progress` (G-A8).
#[tauri::command]
async fn download_model(app: tauri::AppHandle, url: Option<String>) -> Result<String, String> {
    use cortex_brain::download::{DownloadProgress, HttpSource, ModelSource};
    use cortex_brain::paths;
    use tauri::Emitter;

    let app_handle = app.clone();
    let source = match url {
        Some(custom_url) => {
            let sha = format!("{custom_url}.sha256");
            HttpSource::with_url(custom_url, sha)
        }
        None => HttpSource::new(),
    };

    let dest = paths::default_model_path();

    tauri::async_runtime::spawn_blocking(move || {
        let res = source.fetch(
            &dest,
            Some(&mut |p: DownloadProgress| {
                let percentage = p.bytes_total.map(|tot| {
                    if tot > 0 {
                        ((p.bytes_done as f64 / tot as f64) * 100.0) as f32
                    } else {
                        0.0
                    }
                });
                let payload = DownloadProgressPayload {
                    bytes_done: p.bytes_done,
                    bytes_total: p.bytes_total,
                    percentage,
                    status: "downloading".into(),
                    error: None,
                };
                let _ = app_handle.emit("download-progress", &payload);
            }),
        );

        match res {
            Ok(r) => {
                let payload = DownloadProgressPayload {
                    bytes_done: r.bytes,
                    bytes_total: Some(r.bytes),
                    percentage: Some(100.0),
                    status: "done".into(),
                    error: None,
                };
                let _ = app_handle.emit("download-progress", &payload);
                Ok(r.path.to_string_lossy().into_owned())
            }
            Err(e) => {
                let err_str = e.to_string();
                let payload = DownloadProgressPayload {
                    bytes_done: 0,
                    bytes_total: None,
                    percentage: None,
                    status: "error".into(),
                    error: Some(err_str.clone()),
                };
                let _ = app_handle.emit("download-progress", &payload);
                Err(err_str)
            }
        }
    })
    .await
    .map_err(|e| format!("falló el task de descarga: {e}"))?
}

/// Procesa UNA conexión IPC: lee un request, lo enruta al engine y
/// responde. Con G-A6 el backend streaming emite piezas: cada una sale
/// por el socket como `chunk` EN VIVO, después va el `done`/`error`
/// final y se cierra (un request por conexión; los chunks viajan por
/// la MISMA conexión). El `done.text` es el texto procesado
/// autoritativo (con la salida de las tools ya integrada).
fn handle_connection(conn: ipc::IpcConnection, engine: &chat::BrainEngine) {
    use std::io::BufReader;
    let (raw_read, mut write) = match conn.into_split() {
        Ok(parts) => parts,
        Err(e) => {
            eprintln!("ipc: split falló: {e}");
            return;
        }
    };
    let mut reader = BufReader::new(raw_read);
    let req = match ipc::read_json_line::<ipc::QueryRequest, _>(&mut reader) {
        Ok(Some(req)) => req,
        Ok(None) => return,
        Err(e) => {
            eprintln!("ipc: request inválido: {e}");
            return;
        }
    };
    let request_id = req.request_id.clone();
    let result = engine.respond_streaming(&req.project, &req.text, &mut |piece: &str| {
        let chunk = ipc::QueryResponse {
            kind: "chunk".into(),
            text: piece.to_string(),
            request_id: request_id.clone(),
            tool_calls: None,
        };
        if let Err(e) = ipc::write_json_line(&mut write, &chunk) {
            eprintln!("ipc: no pude mandar chunk: {e}");
        }
    });
    let response = match result {
        Ok(turn) => ipc::QueryResponse {
            kind: "done".into(),
            text: turn.text,
            request_id: req.request_id.clone(),
            tool_calls: (!turn.tool_calls.is_empty()).then_some(turn.tool_calls),
        },
        Err(e) => ipc::QueryResponse {
            kind: "error".into(),
            text: e,
            request_id: req.request_id.clone(),
            tool_calls: None,
        },
    };
    if let Err(e) = ipc::write_json_line(&mut write, &response) {
        eprintln!("ipc: no pude responder: {e}");
    }
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
/// G-A4: registra `chat_turn` + el server IPC enruta las queries al
/// engine de chat.
/// G-A7: registra `chat_turn_stream`, `loaded_projects`, `reap_idle`,
/// `list_models` para la UI completa.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Un engine compartido: el server IPC y el command `chat_turn`
    // (estado Tauri) operan sobre el MISMO estado conversacional por
    // proyecto. Los turnos están serializados por el lock interno del
    // engine (chdir + i18n).
    let engine: chat::SharedEngine = std::sync::Arc::new(chat::BrainEngine::new());
    let engine_para_estado = std::sync::Arc::clone(&engine);

    match ipc::try_bind() {
        Ok(server) => {
            // Spawn del loop de accept en un thread dedicado. El handle
            // se descarta; el thread muere con el proceso.
            let _ = std::thread::Builder::new()
                .name("cortex-brain-ipc".into())
                .spawn(move || {
                    while let Ok(conn) = server.accept() {
                        let engine = std::sync::Arc::clone(&engine);
                        // Cada conexión entrante se procesa en su propio
                        // thread: un request, una respuesta, cierre. El
                        // streaming real (chunks) llega en G-A6.
                        let _ = std::thread::spawn(move || {
                            handle_connection(conn, &engine);
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
        .invoke_handler(tauri::generate_handler![
            list_projects,
            refresh_projects,
            chat_turn,
            chat_turn_stream,
            loaded_projects,
            reap_idle,
            list_models,
            download_model
        ])
        .setup(move |app| {
            app.manage(std::sync::Arc::clone(&engine_para_estado));
            Ok(())
        })
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

    // ── Server e2e (G-A4): bind + request + respuesta del engine ─────

    #[cfg(unix)]
    #[test]
    fn server_responde_query_e2e() {
        use crate::ipc;
        use std::io::BufReader;

        // Comparte el lock con los tests de ipc: todos tocan
        // XDG_RUNTIME_DIR (env de proceso).
        let _env_lock = ipc::tests::ENV_LOCK
            .lock()
            .unwrap_or_else(|e| e.into_inner());

        let tmp = std::env::temp_dir().join(format!("cortex-brain-e2e-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        let xdg = tmp.join("runtime");
        std::fs::create_dir_all(&xdg).unwrap();
        unsafe {
            std::env::set_var("XDG_RUNTIME_DIR", &xdg);
        }

        // Proyecto fixture: existe (para el chdir del engine) pero sin
        // config.yaml (i18n cae al default). El engine le inyecta un
        // ScriptedBackend: el e2e NO depende del CLI cortex.
        let project = tmp.join("proj");
        std::fs::create_dir_all(&project).unwrap();
        let engine = chat::BrainEngine::new();
        engine.insert_backend(
            &project.to_string_lossy(),
            Box::new(cortex_brain::chat::ScriptedBackend::new(
                "e2e",
                ["eco desde el motor"],
            )),
        );

        let server = ipc::try_bind().expect("bind");
        let server_thread = std::thread::spawn(move || {
            let conn = server.accept().unwrap();
            handle_connection(conn, &engine);
            // handle_connection responde y cierra (un request por
            // conexión); al dropear el server acá se limpia el socket.
        });

        let client = ipc::try_connect().expect("connect");
        let conn = client.into_connection();
        let (read, mut write) = conn.into_split().unwrap();
        let req = ipc::QueryRequest {
            kind: "query".into(),
            project: project.to_string_lossy().into_owned(),
            text: "hola motor".into(),
            request_id: "r-e2e-1".into(),
        };
        ipc::write_json_line(&mut write, &req).unwrap();
        drop(write); // EOF del cliente: el server ya respondió igual

        let mut br = BufReader::new(read);
        // G-A6: SIEMPRE llega al menos un chunk antes del done (el
        // default del trait emite el texto completo como una pieza).
        let mut chunks: Vec<String> = Vec::new();
        let resp = loop {
            let msg: ipc::QueryResponse = ipc::read_json_line(&mut br).unwrap().expect("mensaje");
            match msg.kind.as_str() {
                "chunk" => chunks.push(msg.text),
                "done" => break msg,
                other => panic!("mensaje inesperado: {other}"),
            }
        };
        assert_eq!(chunks, vec!["eco desde el motor"], "batch ⇒ 1 pieza");
        assert_eq!(resp.kind, "done");
        assert_eq!(resp.request_id, "r-e2e-1");
        assert_eq!(resp.text.trim(), "eco desde el motor");
        assert!(
            resp.tool_calls.is_none(),
            "script sin TOOL ⇒ sin tool_calls"
        );

        server_thread.join().unwrap();
        unsafe {
            std::env::remove_var("XDG_RUNTIME_DIR");
        }
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[cfg(unix)]
    #[test]
    fn server_streaming_chunks_antes_del_done() {
        use crate::ipc;
        use std::io::BufReader;

        let _env_lock = ipc::tests::ENV_LOCK
            .lock()
            .unwrap_or_else(|e| e.into_inner());

        let tmp = std::env::temp_dir().join(format!("cortex-brain-e2e-s-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        let xdg = tmp.join("runtime");
        std::fs::create_dir_all(&xdg).unwrap();
        unsafe {
            std::env::set_var("XDG_RUNTIME_DIR", &xdg);
        }

        let project = tmp.join("proj");
        std::fs::create_dir_all(&project).unwrap();
        let engine = chat::BrainEngine::new();
        engine.insert_backend(
            &project.to_string_lossy(),
            Box::new(chat::tests::PiezasBackend {
                piezas: vec!["La ".into(), "sesión ".into(), "está activa".into()],
            }),
        );

        let server = ipc::try_bind().expect("bind");
        let server_thread = std::thread::spawn(move || {
            let conn = server.accept().unwrap();
            handle_connection(conn, &engine);
        });

        let client = ipc::try_connect().expect("connect");
        let conn = client.into_connection();
        let (read, mut write) = conn.into_split().unwrap();
        let req = ipc::QueryRequest {
            kind: "query".into(),
            project: project.to_string_lossy().into_owned(),
            text: "estado".into(),
            request_id: "r-s1".into(),
        };
        ipc::write_json_line(&mut write, &req).unwrap();
        drop(write);

        let mut br = BufReader::new(read);
        let mut chunks: Vec<String> = Vec::new();
        let done = loop {
            let msg: ipc::QueryResponse = ipc::read_json_line(&mut br).unwrap().expect("mensaje");
            match msg.kind.as_str() {
                "chunk" => chunks.push(msg.text),
                "done" => break msg,
                other => panic!("mensaje inesperado: {other}"),
            }
        };

        // El criterio de pase del gate: la respuesta aparece
        // INCREMENTALMENTE (3 chunks ANTES del done), no de golpe.
        assert_eq!(chunks, vec!["La ", "sesión ", "está activa"]);
        assert_eq!(done.request_id, "r-s1");
        assert_eq!(done.text.trim(), "La sesión está activa");
        assert!(done.tool_calls.is_none());

        server_thread.join().unwrap();
        unsafe {
            std::env::remove_var("XDG_RUNTIME_DIR");
        }
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn download_progress_payload_serializa() {
        let p = DownloadProgressPayload {
            bytes_done: 1024,
            bytes_total: Some(2048),
            percentage: Some(50.0),
            status: "downloading".into(),
            error: None,
        };
        let json = serde_json::to_string(&p).expect("serialize");
        assert!(json.contains("\"bytes_done\":1024"));
        assert!(json.contains("\"percentage\":50.0"));
        assert!(json.contains("\"status\":\"downloading\""));
    }
}
