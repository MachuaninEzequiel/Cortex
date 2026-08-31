//! IPC esqueleto (Obra 20, G-A2).
//!
//! Transporte: Unix socket (Linux/macOS) o named pipe (Windows, stub en
//! esta etapa). Protocolo: JSON-lines (NDJSON) — un mensaje JSON por
//! línea terminada en `\n`.
//!
//! Single-instance: el server intenta bindear el socket. Si ya existe
//! y otro proceso está escuchando, retorna [`BindError::AlreadyBound`].
//!
//! **Hoy el server hace echo**: por cada query entrante, responde con
//! el mismo texto recibido (envuelto en el envelope del doc 20 §3.4).
//! La lógica de motor llega en G-A4; el streaming de chunks reales en
//! G-A6.
//!
//! Spec: docs/transformacion/20-CORTEX-BRAIN-APP.md §3.4.

use std::io::{BufRead, Write};
use std::path::PathBuf;

/// Mensaje del cliente al server. Hoy un solo tipo (`query`); el
/// streaming y los `done`/`chunk`/`error` se agregan en G-A6.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct QueryRequest {
    #[serde(rename = "type")]
    pub kind: String, // siempre "query" en G-A2
    pub project: String,
    pub text: String,
    pub request_id: String,
}

/// Mensaje del server al cliente. Hoy es un solo mensaje `echo` por
/// query. G-A6 introduce `chunk` + `done` + `error`.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct QueryResponse {
    #[serde(rename = "type")]
    pub kind: String, // "echo" en G-A2; "chunk"/"done"/"error" en G-A6
    pub text: String,
    pub request_id: String,
}

/// Path default del socket. Cross-platform; en Windows retorna None
/// (named pipe se implementa en G-A2.1).
pub fn socket_path() -> Option<PathBuf> {
    socket_path_impl()
}

#[cfg(unix)]
fn socket_path_impl() -> Option<PathBuf> {
    // Linux: $XDG_RUNTIME_DIR (per-user, no root, se borra al logout).
    // macOS: $TMPDIR (per-user, /var/folders/...).
    // Fallback: /tmp/cortex-brain-<uid>.sock en Linux, $TMPDIR/cortex-brain.sock en macOS.
    #[cfg(target_os = "linux")]
    {
        if let Some(dir) = std::env::var_os("XDG_RUNTIME_DIR") {
            return Some(PathBuf::from(dir).join("cortex-brain.sock"));
        }
        let uid = unsafe { libc::getuid() };
        Some(PathBuf::from(format!("/tmp/cortex-brain-{uid}.sock")))
    }
    #[cfg(target_os = "macos")]
    {
        if let Some(dir) = std::env::var_os("TMPDIR") {
            return Some(PathBuf::from(dir).join("cortex-brain.sock"));
        }
        Some(PathBuf::from("/tmp/cortex-brain.sock"))
    }
    #[cfg(not(any(target_os = "linux", target_os = "macos")))]
    {
        None
    }
}

#[cfg(windows)]
fn socket_path_impl() -> Option<PathBuf> {
    // G-A2.1: named pipe `\\.\pipe\cortex-brain`.
    None
}

#[derive(Debug)]
pub enum BindError {
    /// Ya hay una instancia escuchando en el socket.
    AlreadyBound(PathBuf),
    /// No se pudo crear el socket (permisos, fs, etc).
    Io {
        path: PathBuf,
        source: std::io::Error,
    },
    /// Windows: named pipe no implementado en G-A2.
    NotSupported,
}

impl std::fmt::Display for BindError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            BindError::AlreadyBound(p) => write!(
                f,
                "ya hay una instancia de cortex-brain escuchando en {}",
                p.display()
            ),
            BindError::Io { path, source } => {
                write!(f, "error de io al bindear {}: {source}", path.display())
            }
            BindError::NotSupported => {
                f.write_str("IPC no soportado en este OS (G-A2: sólo Unix; Windows en G-A2.1)")
            }
        }
    }
}

impl std::error::Error for BindError {}

#[derive(Debug)]
pub enum ConnectError {
    NotSupported,
    NoServer(PathBuf),
    Io {
        path: PathBuf,
        source: std::io::Error,
    },
}

impl std::fmt::Display for ConnectError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ConnectError::NotSupported => {
                f.write_str("IPC no soportado en este OS (G-A2: sólo Unix; Windows en G-A2.1)")
            }
            ConnectError::NoServer(p) => write!(
                f,
                "no hay cortex-brain escuchando en {} (¿arrancaste la GUI?)",
                p.display()
            ),
            ConnectError::Io { path, source } => {
                write!(f, "error de io al conectar a {}: {source}", path.display())
            }
        }
    }
}

impl std::error::Error for ConnectError {}

// ── Unix implementation ───────────────────────────────────────────────────

#[cfg(unix)]
mod imp {
    use super::*;
    use std::os::unix::net::{UnixListener, UnixStream};

    /// Server: intenta crear y bindear el socket. Si el path ya existe
    /// y hay algo escuchando, retorna `BindError::AlreadyBound`.
    pub fn try_bind() -> Result<IpcServer, BindError> {
        let path = socket_path().ok_or(BindError::NotSupported)?;

        // Si existe el path, intentamos conectar primero. Si funciona,
        // hay otro server. Si no funciona, lo borramos y reintentamos.
        if path.exists() {
            match UnixStream::connect(&path) {
                Ok(_) => return Err(BindError::AlreadyBound(path)),
                Err(_) => {
                    // Stale socket: lo borramos.
                    let _ = std::fs::remove_file(&path);
                }
            }
        }

        // Asegurar directorio padre (en Linux el dir es XDG_RUNTIME_DIR
        // que puede no existir si el usuario nunca abrió una sesión
        // gráfica; en macOS $TMPDIR siempre existe).
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }

        let listener = UnixListener::bind(&path).map_err(|source| BindError::Io {
            path: path.clone(),
            source,
        })?;
        // Permisos: sólo el dueño puede escribir (0600). Importante en
        // Linux donde el path puede estar en /tmp.
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600));
        }

        Ok(IpcServer { listener, path })
    }

    /// Cliente: conecta al socket. Si nadie escucha, retorna
    /// `ConnectError::NoServer`.
    pub fn try_connect() -> Result<IpcClient, ConnectError> {
        let path = socket_path().ok_or(ConnectError::NotSupported)?;
        let stream = UnixStream::connect(&path).map_err(|e| {
            if e.kind() == std::io::ErrorKind::NotFound
                || e.kind() == std::io::ErrorKind::ConnectionRefused
            {
                ConnectError::NoServer(path.clone())
            } else {
                ConnectError::Io {
                    path: path.clone(),
                    source: e,
                }
            }
        })?;
        Ok(IpcClient { stream })
    }

    #[derive(Debug)]
    pub struct IpcServer {
        pub(crate) listener: UnixListener,
        pub(crate) path: PathBuf,
    }

    impl IpcServer {
        pub fn path(&self) -> &std::path::Path {
            &self.path
        }

        /// Acepta una conexión entrante. Bloquea.
        pub fn accept(&self) -> std::io::Result<IpcConnection> {
            let (stream, _addr) = self.listener.accept()?;
            Ok(IpcConnection { stream })
        }
    }

    impl Drop for IpcServer {
        fn drop(&mut self) {
            // Limpieza del socket file al apagar el server.
            let _ = std::fs::remove_file(&self.path);
        }
    }

    #[derive(Debug)]
    pub struct IpcClient {
        pub(crate) stream: UnixStream,
    }

    impl IpcClient {
        pub fn into_connection(self) -> IpcConnection {
            IpcConnection {
                stream: self.stream,
            }
        }
    }

    pub struct IpcConnection {
        pub(crate) stream: UnixStream,
    }

    impl IpcConnection {
        pub fn into_split(self) -> std::io::Result<(ReadHalf, WriteHalf)> {
            let read = self.stream.try_clone()?;
            let write = self.stream;
            Ok((ReadHalf { stream: read }, WriteHalf { stream: write }))
        }
    }

    impl std::io::Read for IpcConnection {
        fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
            std::io::Read::read(&mut self.stream, buf)
        }
    }

    impl std::io::Write for IpcConnection {
        fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
            std::io::Write::write(&mut self.stream, buf)
        }
        fn flush(&mut self) -> std::io::Result<()> {
            std::io::Write::flush(&mut self.stream)
        }
    }

    pub struct ReadHalf {
        pub(crate) stream: UnixStream,
    }

    impl std::io::Read for ReadHalf {
        fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
            std::io::Read::read(&mut self.stream, buf)
        }
    }

    pub struct WriteHalf {
        pub(crate) stream: UnixStream,
    }

    impl std::io::Write for WriteHalf {
        fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
            std::io::Write::write(&mut self.stream, buf)
        }
        fn flush(&mut self) -> std::io::Result<()> {
            std::io::Write::flush(&mut self.stream)
        }
    }
}

// ── Windows stub ──────────────────────────────────────────────────────────

#[cfg(windows)]
mod imp {
    use super::*;

    pub fn try_bind() -> Result<IpcServer, BindError> {
        Err(BindError::NotSupported)
    }

    pub fn try_connect() -> Result<IpcClient, ConnectError> {
        Err(ConnectError::NotSupported)
    }

    #[derive(Debug)]
    pub struct IpcServer;

    impl IpcServer {
        pub fn path(&self) -> &std::path::Path {
            std::path::Path::new("")
        }
        pub fn accept(&self) -> std::io::Result<IpcConnection> {
            Err(std::io::Error::new(
                std::io::ErrorKind::Unsupported,
                "IPC no soportado en Windows (G-A2.1)",
            ))
        }
    }

    #[derive(Debug)]
    pub struct IpcClient;

    impl IpcClient {
        pub fn into_connection(self) -> IpcConnection {
            IpcConnection
        }
    }

    pub struct IpcConnection;

    impl IpcConnection {
        pub fn into_split(self) -> std::io::Result<(ReadHalf, WriteHalf)> {
            Err(std::io::Error::new(
                std::io::ErrorKind::Unsupported,
                "IPC no soportado en Windows (G-A2.1)",
            ))
        }
    }

    impl std::io::Read for IpcConnection {
        fn read(&mut self, _buf: &mut [u8]) -> std::io::Result<usize> {
            Err(std::io::Error::new(
                std::io::ErrorKind::Unsupported,
                "IPC no soportado en Windows (G-A2.1)",
            ))
        }
    }

    impl std::io::Write for IpcConnection {
        fn write(&mut self, _buf: &[u8]) -> std::io::Result<usize> {
            Err(std::io::Error::new(
                std::io::ErrorKind::Unsupported,
                "IPC no soportado en Windows (G-A2.1)",
            ))
        }
        fn flush(&mut self) -> std::io::Result<()> {
            Ok(())
        }
    }

    pub struct ReadHalf;
    pub struct WriteHalf;

    impl std::io::Read for ReadHalf {
        fn read(&mut self, _buf: &mut [u8]) -> std::io::Result<usize> {
            Ok(0)
        }
    }
    impl std::io::Write for WriteHalf {
        fn write(&mut self, _buf: &[u8]) -> std::io::Result<usize> {
            Ok(0)
        }
        fn flush(&mut self) -> std::io::Result<()> {
            Ok(())
        }
    }
}

pub use imp::*;

// ── Public API (wrappers cross-platform) ────────────────────────────────

/// Intenta ser server. Si el socket ya existe y hay alguien escuchando,
/// retorna `BindError::AlreadyBound`. En Windows retorna `NotSupported`.
pub fn try_bind() -> Result<IpcServer, BindError> {
    imp::try_bind()
}

/// Intenta conectar al server. Si nadie escucha, retorna
/// `ConnectError::NoServer`. En Windows retorna `NotSupported`.
pub fn try_connect() -> Result<IpcClient, ConnectError> {
    imp::try_connect()
}

// ── Helpers JSON-lines ────────────────────────────────────────────────────

/// Lee una línea terminada en `\n` y la deserializa a `T`.
/// Devuelve `Ok(None)` si el peer cerró la conexión (EOF limpio).
pub fn read_json_line<T: serde::de::DeserializeOwned, R: BufRead>(
    reader: &mut R,
) -> Result<Option<T>, std::io::Error> {
    let mut line = String::new();
    let n = reader.read_line(&mut line)?;
    if n == 0 {
        return Ok(None);
    }
    let trimmed = line.trim_end_matches('\n').trim_end_matches('\r');
    serde_json::from_str(trimmed).map_err(|e| {
        std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            format!("json inválido: {e}"),
        )
    })
}

/// Serializa `value` a JSON + `\n` y la escribe.
pub fn write_json_line<T: serde::Serialize, W: Write>(
    writer: &mut W,
    value: &T,
) -> Result<(), std::io::Error> {
    let mut s = serde_json::to_string(value)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, format!("json: {e}")))?;
    s.push('\n');
    writer.write_all(s.as_bytes())?;
    writer.flush()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    // ── read/write json line (puros, no tocan FS) ────────────────────────

    #[test]
    fn write_y_read_round_trip() {
        let req = QueryRequest {
            kind: "query".into(),
            project: "/tmp/proj".into(),
            text: "hola".into(),
            request_id: "r1".into(),
        };
        let mut buf = Vec::new();
        write_json_line(&mut buf, &req).unwrap();
        let s = String::from_utf8(buf.clone()).unwrap();
        assert!(s.ends_with('\n'), "debe terminar en \\n");
        assert!(s.contains("\"type\":\"query\""));
        assert!(s.contains("\"request_id\":\"r1\""));

        let mut cursor = Cursor::new(buf);
        let parsed: QueryRequest = read_json_line(&mut cursor).unwrap().unwrap();
        assert_eq!(parsed.text, "hola");
        assert_eq!(parsed.request_id, "r1");
    }

    #[test]
    fn read_eof_retorna_none() {
        let mut cursor = Cursor::new(Vec::<u8>::new());
        let out: Option<QueryRequest> = read_json_line(&mut cursor).unwrap();
        assert!(out.is_none());
    }

    #[test]
    fn read_json_invalido_es_error_explicito() {
        let mut cursor = Cursor::new(b"esto no es json\n".to_vec());
        let err = read_json_line::<QueryRequest, _>(&mut cursor).unwrap_err();
        assert_eq!(err.kind(), std::io::ErrorKind::InvalidData);
        assert!(format!("{err}").contains("json"));
    }

    // ── socket_path (puro, no toca FS) ───────────────────────────────────

    #[cfg(unix)]
    #[test]
    fn socket_path_unix_no_es_vacio() {
        let p = socket_path().expect("debe retornar path en Unix");
        assert!(p.to_str().unwrap().contains("cortex-brain"));
    }

    #[cfg(windows)]
    #[test]
    fn socket_path_windows_es_none_en_g_a2() {
        assert!(socket_path().is_none());
    }

    // ── bind / connect (integración, tocan FS en tempdir) ────────────────

    #[cfg(unix)]
    #[test]
    fn bind_y_accept_y_echo_round_trip() {
        use crate::ipc;
        use std::io::BufReader;
        use std::os::unix::fs::PermissionsExt;
        use std::sync::{Arc, Barrier};

        let _home_lock = HOME_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let tmp = std::env::temp_dir().join(format!("cortex-brain-ipc-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        std::fs::create_dir_all(&tmp).unwrap();
        let xdg = tmp.join("runtime");
        std::fs::create_dir_all(&xdg).unwrap();
        unsafe {
            std::env::set_var("XDG_RUNTIME_DIR", &xdg);
        }

        let server = ipc::try_bind().expect("bind");
        let path = server.path().to_path_buf();
        let _ = std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600));

        let b1 = Arc::new(Barrier::new(2));
        let b2 = b1.clone();

        let server_thread = std::thread::spawn(move || {
            let conn = server.accept().unwrap();
            b1.wait();
            let (read, mut write) = conn.into_split().unwrap();
            let mut br = BufReader::new(read);
            let req: QueryRequest = read_json_line(&mut br).unwrap().expect("mensaje entrante");
            let resp = QueryResponse {
                kind: "echo".into(),
                text: req.text.clone(),
                request_id: req.request_id.clone(),
            };
            write_json_line(&mut write, &resp).unwrap();
        });

        let client = ipc::try_connect().expect("connect");
        let conn = client.into_connection();
        let (read, mut write) = conn.into_split().unwrap();
        b2.wait();
        let req = QueryRequest {
            kind: "query".into(),
            project: "/tmp/p".into(),
            text: "ping".into(),
            request_id: "r42".into(),
        };
        write_json_line(&mut write, &req).unwrap();
        let mut br = BufReader::new(read);
        let resp: QueryResponse = read_json_line(&mut br).unwrap().expect("respuesta");
        assert_eq!(resp.text, "ping");
        assert_eq!(resp.request_id, "r42");
        assert_eq!(resp.kind, "echo");

        server_thread.join().unwrap();
        unsafe {
            std::env::set_var("XDG_RUNTIME_DIR", &xdg);
        }
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[cfg(unix)]
    #[test]
    fn connect_sin_server_retorna_no_server() {
        let _home_lock = HOME_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let tmp =
            std::env::temp_dir().join(format!("cortex-brain-ipc-empty-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        std::fs::create_dir_all(&tmp).unwrap();
        let xdg = tmp.join("runtime");
        std::fs::create_dir_all(&xdg).unwrap();
        unsafe {
            std::env::set_var("XDG_RUNTIME_DIR", &xdg);
        }

        match imp::try_connect() {
            Err(ConnectError::NoServer(_)) => {}
            other => panic!("esperaba NoServer, recibí: {other:?}"),
        }

        unsafe {
            std::env::remove_var("XDG_RUNTIME_DIR");
        }
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[cfg(unix)]
    #[test]
    fn stale_socket_se_reemplaza() {
        // Si el path existe pero no hay nadie escuchando, el bind lo
        // borra y arranca limpio.
        let _home_lock = HOME_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let tmp =
            std::env::temp_dir().join(format!("cortex-brain-ipc-stale-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        std::fs::create_dir_all(&tmp).unwrap();
        let xdg = tmp.join("runtime");
        std::fs::create_dir_all(&xdg).unwrap();
        unsafe {
            std::env::set_var("XDG_RUNTIME_DIR", &xdg);
        }

        // Crear archivo stale.
        let path = socket_path().unwrap();
        std::fs::write(&path, b"stale").unwrap();
        assert!(path.exists());

        let server = imp::try_bind().expect("bind limpia stale");
        assert!(path.exists());
        drop(server);
        assert!(!path.exists());

        unsafe {
            std::env::remove_var("XDG_RUNTIME_DIR");
        }
        let _ = std::fs::remove_dir_all(&tmp);
    }

    // Lock para tests que tocan XDG_RUNTIME_DIR (no es thread-safe con
    // tests paralelos que también setean env). Usamos `lock().unwrap_or_else(|e| e.into_inner())`
    // para recuperarnos de PoisonError cuando un test paralelo hace panic.
    static HOME_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());
}
