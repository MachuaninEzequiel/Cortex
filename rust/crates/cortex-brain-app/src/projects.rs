//! Scan recursivo de proyectos Cortex + cache (Obra 20, G-A3).
//!
//! Detecta proyectos Cortex en la máquina para la sidebar de la app:
//! un directorio es proyecto Cortex si contiene `config.yaml` y un
//! directorio `.cortex/` (heurística del doc 20 §4.1).
//!
//! Decisiones cerradas con el dueño (2026-08-31, G-A3):
//! 1. **Raíz del scan:** sólo `$HOME` en v1 (fallback `USERPROFILE`
//!    porque Windows es target oficial). Roots extra configurables
//!    quedan para la settings GUI (G-A7).
//! 2. **`config.yaml` corrupto:** NO se ignora: se lista con
//!    `valid_config: false`. Más honesto que esconderlo; la UI podrá
//!    marcarlo.
//! 3. **Sesión activa:** se lee la convención de archivos del storage
//!    de sesiones (`cortex_app::session::SessionStorage`):
//!    `.cortex/sessions/active.txt` no vacío + el `<id>.yaml`
//!    referenciado existe. NO se depende de `cortex-app` porque arrastra
//!    `cortex-embed`+ONNX (`ort-sys` baja onnxruntime en build.rs) al
//!    build del app sólo para leer un puntero. Puntero stale ⇒ false
//!    (misma semántica que `SessionService::get_active`).
//! 4. **"Abierto en este instante":** v1 basta con `.git/HEAD` legible
//!    (branch != vacío). Los lock files en `~/.config/cortex/locks/`
//!    quedan deferidos (doc 20 §4.1).
//!
//! Cache: `~/.cache/cortex/brain-projects.json` con `{path, mtime,
//! sha256_config}` por entrada. `list_projects` valida el cache contra
//! el filesystem (path existe, mtime y sha del config) y NO recorre el
//! árbol; `refresh_projects` hace el scan completo y reescribe el cache.
//!
//! Spec: docs/transformacion/20-CORTEX-BRAIN-APP.md §4.1 y
//! docs/transformacion/21-CORTEX-BRAIN-APP-ESTADO.md §11.

use std::path::{Path, PathBuf};

/// Directorios que el scan NUNCA entra (doc 20 §4.1: la lista es la
/// misma que un `.gitignore` estándar de dev).
const SKIP_DIRS: &[&str] = &[
    ".git",
    "node_modules",
    "target",
    ".venv",
    "__pycache__",
    ".cargo",
    "dist",
    "build",
    ".next",
    ".gradle",
    "vendor",
    "Library",
    ".cache",
];

/// Límite de profundidad del scan (niveles por debajo de la raíz).
const MAX_DEPTH: usize = 8;

/// Versión del formato del archivo de cache. Si cambia, el cache se
/// descarta y se re-escanea.
const CACHE_VERSION: u32 = 1;

/// Proyecto Cortex detectado. Serializado snake_case para que el
/// frontend TS (G-A7) tenga el espejo 1:1.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct ProjectEntry {
    /// Path absoluto del proyecto.
    pub path: String,
    /// Rama actual (`ref: refs/heads/<x>` de `.git/HEAD`); vacía si no
    /// hay git o es detached HEAD.
    pub branch: String,
    /// Hay sesión Cortex activa (ver [`has_active_session`]).
    pub has_session: bool,
    /// `config.yaml` parsea como mapping YAML. Los corruptos se listan
    /// con `false` (decisión del dueño: no se esconden).
    pub valid_config: bool,
    /// Último (re)escaneo de la entrada, epoch segundos.
    pub last_scan: u64,
}

/// Entrada de cache: la [`ProjectEntry`] más el fingerprint del
/// `config.yaml` para invalidación barata.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
struct CachedProject {
    #[serde(flatten)]
    entry: ProjectEntry,
    /// mtime del `config.yaml` al momento del scan, epoch segundos.
    mtime_secs: u64,
    /// sha256 del contenido del `config.yaml` (cinta extra por si el
    /// mtime no refleja un cambio de contenido).
    sha256_config: String,
}

/// Formato on-disk del cache.
#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct CacheFile {
    version: u32,
    entries: Vec<CachedProject>,
}

// ── Raíces y rutas ────────────────────────────────────────────────────────

/// Raíz del scan en v1: `$HOME` (fallback `USERPROFILE` para Windows,
/// target oficial). Decisión del dueño: sin roots extra por ahora.
#[must_use]
pub fn scan_root() -> Option<PathBuf> {
    std::env::var_os("HOME")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("USERPROFILE").map(PathBuf::from))
}

/// Path del cache de proyectos: `~/.cache/cortex/brain-projects.json`
/// (misma convención `~/.cache/cortex/` que `cortex_brain::paths`).
#[must_use]
pub fn cache_path() -> PathBuf {
    let home = std::env::var_os("HOME")
        .or_else(|| std::env::var_os("USERPROFILE"))
        .unwrap_or_default();
    PathBuf::from(home)
        .join(".cache")
        .join("cortex")
        .join("brain-projects.json")
}

// ── Scan ──────────────────────────────────────────────────────────────────

/// Scan recursivo desde `root`, con límite de profundidad
/// [`MAX_DEPTH`] y skip de [`SKIP_DIRS`]. Resultado ordenado por path
/// (determinismo para la UI y para `--projects-list`).
#[must_use]
pub fn scan(root: &Path) -> Vec<ProjectEntry> {
    let mut out = Vec::new();
    scan_dir(root, 0, &mut out);
    out.sort_by(|a, b| a.path.cmp(&b.path));
    out
}

fn scan_dir(dir: &Path, depth: usize, out: &mut Vec<ProjectEntry>) {
    if depth > MAX_DEPTH {
        return;
    }
    // Heurística "es un proyecto Cortex": config.yaml + .cortex/.
    let config = dir.join("config.yaml");
    if config.is_file() && dir.join(".cortex").is_dir() {
        out.push(build_entry(dir));
    }
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let Ok(ft) = entry.file_type() else {
            continue;
        };
        if !ft.is_dir() {
            continue;
        }
        let name = entry.file_name();
        if SKIP_DIRS.contains(&name.to_string_lossy().as_ref()) {
            continue;
        }
        scan_dir(&entry.path(), depth + 1, out);
    }
}

/// Construye la entrada para un directorio que ya pasó la heurística.
fn build_entry(dir: &Path) -> ProjectEntry {
    ProjectEntry {
        path: dir.to_string_lossy().into_owned(),
        branch: branch_of(dir).unwrap_or_default(),
        has_session: has_active_session(dir),
        valid_config: config_is_valid(&dir.join("config.yaml")),
        last_scan: now_secs(),
    }
}

/// `config.yaml` es válido si parsea como mapping YAML. Un YAML
/// sintácticamente válido que no sea mapping (ej. un escalar) NO
/// cuenta como config válido.
fn config_is_valid(config: &Path) -> bool {
    let Ok(text) = std::fs::read_to_string(config) else {
        return false;
    };
    matches!(
        serde_yaml::from_str::<serde_yaml::Value>(&text),
        Ok(serde_yaml::Value::Mapping(_))
    )
}

/// Rama actual del proyecto desde `.git/HEAD` (doc 20 §4.1: para v1
/// basta con HEAD legible). Detached HEAD o sin git ⇒ `None`.
fn branch_of(dir: &Path) -> Option<String> {
    let head = std::fs::read_to_string(dir.join(".git").join("HEAD")).ok()?;
    let head = head.trim();
    head.strip_prefix("ref: refs/heads/").map(str::to_owned)
}

/// ¿Hay sesión Cortex activa? Lee la convención de archivos del
/// storage de sesiones (`cortex_app::session::SessionStorage`,
/// `from_workspace`): `<proyecto>/.cortex/sessions/active.txt` con el
/// id, y la sesión vive en `<id>.yaml` al lado. Un puntero stale
/// (apunta a un yaml que no existe) degrada a `false`, igual que
/// `SessionService::get_active`.
fn has_active_session(dir: &Path) -> bool {
    let sessions = dir.join(".cortex").join("sessions");
    let Ok(pointer) = std::fs::read_to_string(sessions.join("active.txt")) else {
        return false;
    };
    let id = pointer.trim();
    if id.is_empty() {
        return false;
    }
    sessions.join(format!("{id}.yaml")).is_file()
}

// ── Cache ─────────────────────────────────────────────────────────────────

/// Lista proyectos desde el cache, SIN recorrer el árbol. Valida cada
/// entrada contra el filesystem:
/// - path inexistente ⇒ se elimina del cache (y se reescribe el file).
/// - mtime o sha256 del `config.yaml` cambiaron ⇒ se re-deriva la
///   entrada (branch, sesión, validez) in-place.
///
/// Es la misma función que usa el command Tauri `list_projects` y el
/// flag `--projects-list`.
#[must_use]
pub fn list_projects() -> Vec<ProjectEntry> {
    let Some(mut cache) = load_cache() else {
        return Vec::new();
    };
    let mut kept: Vec<CachedProject> = Vec::with_capacity(cache.entries.len());
    let mut dirty = false;
    for mut cached in cache.entries.drain(..) {
        let dir = PathBuf::from(&cached.entry.path);
        let config = dir.join("config.yaml");
        if !dir.is_dir() || !config.is_file() {
            // Proyecto borrado de la máquina ⇒ fuera del cache.
            dirty = true;
            continue;
        }
        let mtime = config_mtime_secs(&config).unwrap_or(0);
        let sha = sha256_file(&config).unwrap_or_default();
        if mtime != cached.mtime_secs || sha != cached.sha256_config {
            // El config cambió ⇒ re-derivar la entrada completa.
            cached.entry = build_entry(&dir);
            cached.mtime_secs = mtime;
            cached.sha256_config = sha;
            dirty = true;
        }
        kept.push(cached);
    }
    if dirty {
        cache.entries = kept.clone();
        save_cache(&cache);
    }
    kept.into_iter().map(|c| c.entry).collect()
}

/// Scan completo de la raíz + reescritura del cache. Es la operación
/// cara; la dispara `refresh_projects` (command Tauri, click
/// "Refrescar") o `--projects-list` cuando el cache todavía no existe.
#[must_use]
pub fn refresh_projects() -> Vec<ProjectEntry> {
    let entries = match scan_root() {
        Some(root) => scan(&root),
        None => Vec::new(),
    };
    let cached: Vec<CachedProject> = entries
        .iter()
        .map(|entry| {
            let config = Path::new(&entry.path).join("config.yaml");
            CachedProject {
                entry: entry.clone(),
                mtime_secs: config_mtime_secs(&config).unwrap_or(0),
                sha256_config: sha256_file(&config).unwrap_or_default(),
            }
        })
        .collect();
    save_cache(&CacheFile {
        version: CACHE_VERSION,
        entries: cached,
    });
    entries
}

fn load_cache() -> Option<CacheFile> {
    let text = std::fs::read_to_string(cache_path()).ok()?;
    let file: CacheFile = serde_json::from_str(&text).ok()?;
    (file.version == CACHE_VERSION).then_some(file)
}

fn save_cache(file: &CacheFile) {
    if let Some(parent) = cache_path().parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if let Ok(json) = serde_json::to_string_pretty(file) {
        let _ = std::fs::write(cache_path(), json);
    }
}

// ── Helpers de fingerprint ────────────────────────────────────────────────

fn config_mtime_secs(config: &Path) -> Option<u64> {
    let modified = std::fs::metadata(config).ok()?.modified().ok()?;
    modified
        .duration_since(std::time::UNIX_EPOCH)
        .ok()
        .map(|d| d.as_secs())
}

fn sha256_file(path: &Path) -> Option<String> {
    use sha2::Digest;
    let mut file = std::fs::File::open(path).ok()?;
    let mut hasher = sha2::Sha256::new();
    let mut buf = [0u8; 8192];
    loop {
        let n = std::io::Read::read(&mut file, &mut buf).ok()?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Some(format!("{:x}", hasher.finalize()))
}

fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

// ── Tests ─────────────────────────────────────────────────────────────────
//
// Los tests que tocan $HOME (cache y scan_root) se serializan con
// PROJECTS_LOCK: los tests del mismo binario corren en paralelo y
// set_var no es thread-safe. Mismo patrón que HOME_LOCK en ipc.rs.
// `unwrap_or_else(|e| e.into_inner())` recupera de PoisonError cuando
// un test paralelo paniquea.

#[cfg(test)]
mod tests {
    use super::*;

    static PROJECTS_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());

    const VALID_CONFIG: &str = "proyecto: fixture\nversion: 1\n";
    const BROKEN_CONFIG: &str = "[[[ esto no parsea";

    /// Fixture raíz aislada (por pid, se limpia al final).
    fn tmp_root(tag: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "cortex-brain-projects-{tag}-{}",
            std::process::id()
        ));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    /// Crea un proyecto fixture con las piezas opcionales indicadas.
    fn make_project(
        root: &Path,
        rel: &str,
        config: Option<&str>,
        with_cortex: bool,
        branch: Option<&str>,
        active_session: Option<&str>,
    ) -> PathBuf {
        let dir = root.join(rel);
        std::fs::create_dir_all(&dir).unwrap();
        if let Some(cfg) = config {
            std::fs::write(dir.join("config.yaml"), cfg).unwrap();
        }
        if with_cortex {
            std::fs::create_dir_all(dir.join(".cortex")).unwrap();
            if let Some(sid) = active_session {
                let sessions = dir.join(".cortex").join("sessions");
                std::fs::create_dir_all(&sessions).unwrap();
                std::fs::write(sessions.join("active.txt"), format!("{sid}\n")).unwrap();
                std::fs::write(sessions.join(format!("{sid}.yaml")), "id: x\n").unwrap();
            }
        }
        if let Some(b) = branch {
            std::fs::create_dir_all(dir.join(".git")).unwrap();
            std::fs::write(
                dir.join(".git").join("HEAD"),
                format!("ref: refs/heads/{b}\n"),
            )
            .unwrap();
        }
        dir
    }

    fn path_str(p: &Path) -> String {
        p.to_string_lossy().into_owned()
    }

    #[test]
    fn scan_encuentra_validos_reporta_corrupto_y_skippea() {
        let root = tmp_root("scan");
        // 3 proyectos válidos (uno anidado, como en un home real).
        let p1 = make_project(&root, "acme-api", Some(VALID_CONFIG), true, None, None);
        let p2 = make_project(&root, "code/webgraph", Some(VALID_CONFIG), true, None, None);
        let p3 = make_project(&root, "work/cortex", Some(VALID_CONFIG), true, None, None);
        // config.yaml corrupto PERO con .cortex/ ⇒ se lista con valid_config=false.
        let p4 = make_project(&root, "roto", Some(BROKEN_CONFIG), true, None, None);
        // config.yaml válido sin .cortex/ ⇒ NO es proyecto.
        make_project(&root, "no-cortex", Some(VALID_CONFIG), false, None, None);
        // Proyecto anidado dentro de node_modules ⇒ skip, no se encuentra.
        make_project(
            &root,
            "acme-api/node_modules/escondido",
            Some(VALID_CONFIG),
            true,
            None,
            None,
        );

        let found = scan(&root);
        let paths: Vec<&str> = found.iter().map(|e| e.path.as_str()).collect();

        // Orden lexicográfico por path: acme-api < code/webgraph < roto < work/cortex.
        assert_eq!(
            paths,
            vec![path_str(&p1), path_str(&p2), path_str(&p4), path_str(&p3)],
            "debe encontrar los 3 válidos + el corrupto, ordenados, y skippear node_modules"
        );
        assert!(
            !found[2].valid_config,
            "el corrupto se lista con valid_config=false"
        );
        assert!(found[0].valid_config && found[1].valid_config && found[3].valid_config);
        std::fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn branch_y_sesion_se_detectan() {
        let root = tmp_root("branch-session");
        let con_todo = make_project(
            &root,
            "con-git",
            Some(VALID_CONFIG),
            true,
            Some("feature/x"),
            Some("SES-42"),
        );
        let sin_git = make_project(&root, "sin-git", Some(VALID_CONFIG), true, None, None);
        // Puntero stale: active.txt apunta a un yaml que no existe ⇒ false.
        let stale = make_project(&root, "stale", Some(VALID_CONFIG), true, None, None);
        let sessions = stale.join(".cortex").join("sessions");
        std::fs::create_dir_all(&sessions).unwrap();
        std::fs::write(sessions.join("active.txt"), "SES-99\n").unwrap();

        let found = scan(&root);
        let by_path = |p: &Path| found.iter().find(|e| e.path == path_str(p)).unwrap();

        let e = by_path(&con_todo);
        assert_eq!(e.branch, "feature/x");
        assert!(e.has_session, "sesión activa con pointer + yaml ⇒ true");
        let e = by_path(&sin_git);
        assert_eq!(e.branch, "", "sin git ⇒ branch vacío");
        assert!(!e.has_session);
        let e = by_path(&stale);
        assert!(!e.has_session, "puntero stale degrada a false");
        std::fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn yaml_no_mapping_no_es_config_valido() {
        let root = tmp_root("yaml");
        let escalar = make_project(&root, "escalar", Some("solo un string\n"), true, None, None);
        make_project(&root, "mapping", Some(VALID_CONFIG), true, None, None);

        let found = scan(&root);
        let e = found.iter().find(|e| e.path == path_str(&escalar)).unwrap();
        assert!(
            !e.valid_config,
            "YAML escalar parsea pero no es mapping ⇒ inválido"
        );
        assert!(found.iter().filter(|e| e.valid_config).count() == 1);
        std::fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn profundidad_limite_8() {
        let root = tmp_root("depth");
        // Cadena d1/.../d8: proyecto al fondo de la cadena (profundidad 8) ⇒ found.
        // Cadena d1/.../d8 bajo la raíz. El proyecto VIVE en d8
        // (profundidad 8 ⇒ dentro del límite).
        let mut deep = root.clone();
        for i in 1..=8 {
            deep = deep.join(format!("d{i}"));
        }
        std::fs::create_dir_all(&deep).unwrap();
        std::fs::write(deep.join("config.yaml"), VALID_CONFIG).unwrap();
        std::fs::create_dir_all(deep.join(".cortex")).unwrap();
        // Y otro a profundidad 9 (d8/d9) ⇒ fuera del límite.
        let too_deep = deep.join("d9");
        std::fs::create_dir_all(&too_deep).unwrap();
        std::fs::write(too_deep.join("config.yaml"), VALID_CONFIG).unwrap();
        std::fs::create_dir_all(too_deep.join(".cortex")).unwrap();

        let found = scan(&root);
        assert!(
            found.iter().any(|e| e.path == path_str(&deep)),
            "profundidad 8 ⇒ found"
        );
        assert!(
            !found.iter().any(|e| e.path == path_str(&too_deep)),
            "profundidad 9 ⇒ fuera del límite"
        );
        std::fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn cache_list_no_recurre_y_stale_se_elimina() {
        let _g = PROJECTS_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let home = tmp_root("cache");
        let a = make_project(&home, "proj-a", Some(VALID_CONFIG), true, None, None);
        let b = make_project(&home, "proj-b", Some(VALID_CONFIG), true, None, None);

        unsafe { std::env::set_var("HOME", &home) };
        unsafe { std::env::set_var("USERPROFILE", &home) };

        // refresh llena el cache con a y b.
        let fresh = refresh_projects();
        assert_eq!(fresh.len(), 2);
        assert!(cache_path().is_file());

        // Proyecto nuevo DESPUÉS del cache: list_projects NO lo ve
        // (prueba que leyó cache en vez de recorrer el árbol).
        let c = make_project(&home, "proj-c", Some(VALID_CONFIG), true, None, None);
        let listed = list_projects();
        assert_eq!(listed.len(), 2, "list_projects lee cache, no escanea");
        assert!(listed.iter().all(|e| e.path != path_str(&c)));

        // Proyecto borrado: list_projects lo elimina y REESCRIBE el cache.
        std::fs::remove_dir_all(&b).unwrap();
        let listed = list_projects();
        assert_eq!(listed.len(), 1);
        assert_eq!(listed[0].path, path_str(&a));

        let cache_text = std::fs::read_to_string(cache_path()).unwrap();
        assert!(
            !cache_text.contains("proj-b"),
            "stale eliminado del archivo de cache"
        );
        assert!(cache_text.contains("proj-a"));

        unsafe { std::env::remove_var("HOME") };
        unsafe { std::env::remove_var("USERPROFILE") };
        let _ = std::fs::remove_dir_all(&home);
    }

    #[test]
    fn scan_root_y_cache_honran_home() {
        let _g = PROJECTS_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let home = tmp_root("home");
        make_project(&home, "mi-proj", Some(VALID_CONFIG), true, None, None);

        unsafe { std::env::set_var("HOME", &home) };
        unsafe { std::env::set_var("USERPROFILE", &home) };

        assert_eq!(scan_root(), Some(home.clone()));
        assert_eq!(
            cache_path(),
            home.join(".cache")
                .join("cortex")
                .join("brain-projects.json")
        );

        let entries = refresh_projects();
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].path, path_str(&home.join("mi-proj")));

        // list_projects desde el cache recién escrito (sin escanear de nuevo).
        let listed = list_projects();
        assert_eq!(listed.len(), 1);
        assert_eq!(listed[0].path, entries[0].path);
        assert_eq!(listed[0].last_scan, entries[0].last_scan);

        unsafe { std::env::remove_var("HOME") };
        unsafe { std::env::remove_var("USERPROFILE") };
        let _ = std::fs::remove_dir_all(&home);
    }
}
