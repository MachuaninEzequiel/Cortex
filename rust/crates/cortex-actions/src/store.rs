//! Puerto de `cortex/action_engine/store.py` (Obra 05 Fase B).
//!
//! - `ActionLog`: registro append-only de ejecuciones en
//!   `.cortex/action_log.jsonl` — insumo del paso APRENDER.
//! - `PreferencesStore`: supresiones y contadores aceptar/saltar/nunca por
//!   id en `.cortex/actions.yaml` — el motor aprende preferencias negativas
//!   y positivas (plan §3.5/§3.6).
//!
//! FORMATO-COMPATIBLE byte-a-byte con los archivos que escribe Python:
//! - action_log.jsonl: una línea JSON por ejecución (claves en orden de
//!   inserción del dict Python), `\n` final por entrada.
//! - actions.yaml: `yaml.safe_dump({"acciones": …}, sort_keys=False,
//!   allow_unicode=True)` — orden de inserción, indentación 2.

use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};

use serde_json::Value;

const LOG_ROTADO: &str = "action_log.1.jsonl";

/// Entrada de log con orden de claves preservado (espejo del dict Python).
#[derive(Debug, Clone, Default)]
pub struct OrderedEntry {
    pub fields: Vec<(String, Value)>,
}

impl OrderedEntry {
    pub fn new() -> Self {
        Self::default()
    }

    /// Inserta o reemplaza manteniendo la posición original (semántica de
    /// asignación de dict de Python).
    pub fn set(&mut self, key: &str, value: Value) {
        if let Some(slot) = self.fields.iter_mut().find(|(k, _)| k == key) {
            slot.1 = value;
        } else {
            self.fields.push((key.to_string(), value));
        }
    }

    pub fn get(&self, key: &str) -> Option<&Value> {
        self.fields.iter().find(|(k, _)| k == key).map(|(_, v)| v)
    }

    /// Serialización idéntica a `json.dumps(entry, ensure_ascii=False)`.
    pub fn to_json_string(&self) -> String {
        let mut out = String::from("{");
        for (i, (k, v)) in self.fields.iter().enumerate() {
            if i > 0 {
                out.push_str(", ");
            }
            out.push_str(&serde_json::Value::String(k.clone()).to_string());
            out.push_str(": ");
            // default=str de Python: valores no serializables se stringifican;
            // acá todo entra ya como Value.
            out.push_str(&v.to_string());
        }
        out.push('}');
        out
    }
}

/// JSONL append-only: {id, ts, trigger, dry_run, ok, message, duration_ms}.
pub struct ActionLog {
    dir: PathBuf,
    path: PathBuf,
    max_bytes: u64,
}

impl ActionLog {
    pub fn new(directory: &Path) -> Self {
        Self::with_max_bytes(directory, 5 * 1024 * 1024)
    }

    pub fn with_max_bytes(directory: &Path, max_bytes: u64) -> Self {
        let dir = directory.to_path_buf();
        let path = dir.join("action_log.jsonl");
        Self {
            dir,
            path,
            max_bytes,
        }
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn append(&self, mut entry: OrderedEntry) -> std::io::Result<()> {
        if entry.get("ts").map(|v| v.is_null()).unwrap_or(true) || entry.get("ts").is_none() {
            entry.set("ts", Value::String(crate::models::ahora_iso()));
        }
        fs::create_dir_all(&self.dir)?;
        self.rotar_si_corresponde()?;
        let mut fh = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)?;
        writeln!(fh, "{}", entry.to_json_string())?;
        Ok(())
    }

    fn rotar_si_corresponde(&self) -> std::io::Result<()> {
        let size = match fs::metadata(&self.path) {
            Ok(m) => m.len(),
            Err(_) => return Ok(()),
        };
        if size < self.max_bytes {
            return Ok(());
        }
        let rotado = self.dir.join(LOG_ROTADO);
        if rotado.exists() {
            fs::remove_file(&rotado)?;
        }
        fs::rename(&self.path, &rotado)?;
        Ok(())
    }

    /// Lee (rotado, actual) en ese orden; líneas corruptas se saltan con
    /// warning (espejo del logger.warning de Python).
    pub fn load(&self) -> Vec<Value> {
        let mut eventos = Vec::new();
        for ruta in [self.dir.join(LOG_ROTADO), self.path.clone()] {
            let text = match fs::read_to_string(&ruta) {
                Ok(t) => t,
                Err(_) => continue,
            };
            for linea in text.lines() {
                if linea.trim().is_empty() {
                    continue;
                }
                match serde_json::from_str::<Value>(linea) {
                    Ok(v) => eventos.push(v),
                    Err(_) => {
                        eprintln!("WARNING: Línea corrupta en {}", ruta.display());
                    }
                }
            }
        }
        eventos
    }
}

/// Preferencias por acción en YAML (sin compile-doctest):
///
/// ```text
/// acciones:
///   vault.reindex:
///     never: false
///     skips: 2
///     accepts: 7
/// ```
///
/// Reglas v0 (aprendizaje): `never` suprime la acción para siempre; cada
/// `skip` resta score; los `accepts` lo devuelven.
pub struct PreferencesStore {
    dir: PathBuf,
    path: PathBuf,
}

#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct PrefsEntrada {
    pub never: bool,
    pub skips: i64,
    pub accepts: i64,
}

impl PreferencesStore {
    pub fn new(directory: &Path) -> Self {
        let dir = directory.to_path_buf();
        let path = dir.join("actions.yaml");
        Self { dir, path }
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Carga preservando el orden de inserción del archivo (sort_keys=False
    /// de Python). YAML roto ⇒ se ignora con warning (nunca tumba el motor).
    fn load(&self) -> Vec<(String, PrefsEntrada)> {
        let text = match fs::read_to_string(&self.path) {
            Ok(t) => t,
            Err(_) => return Vec::new(),
        };
        let doc: Result<serde_yaml::Mapping, _> = serde_yaml::from_str(&text);
        let doc = match doc {
            Ok(d) => d,
            Err(_) => {
                eprintln!("WARNING: actions.yaml ilegible; se ignora");
                return Vec::new();
            }
        };
        let Some(acciones) = doc.get("acciones") else {
            return Vec::new();
        };
        let Some(acciones) = acciones.as_mapping() else {
            return Vec::new();
        };
        let mut out = Vec::new();
        for (k, v) in acciones {
            let Some(id) = k.as_str() else { continue };
            let empty = serde_yaml::Mapping::new();
            let entrada = v.as_mapping().unwrap_or(&empty);
            let get_i = |key: &str| -> i64 {
                entrada
                    .get(serde_yaml::Value::String(key.to_string()))
                    .and_then(|x| x.as_i64())
                    .unwrap_or(0)
            };
            out.push((
                id.to_string(),
                PrefsEntrada {
                    never: entrada
                        .get(serde_yaml::Value::String("never".to_string()))
                        .and_then(|x| x.as_bool())
                        .unwrap_or(false),
                    skips: get_i("skips"),
                    accepts: get_i("accepts"),
                },
            ));
        }
        out
    }

    fn guardar(&self, acciones: &[(String, PrefsEntrada)]) -> std::io::Result<()> {
        fs::create_dir_all(&self.dir)?;
        // Espejo de yaml.safe_dump({"acciones": …}, sort_keys=False,
        // allow_unicode=True): mapping anidado indentado a 2 espacios.
        let mut out = String::new();
        if acciones.is_empty() {
            out.push_str("acciones: {}\n");
        } else {
            out.push_str("acciones:\n");
            for (id, e) in acciones {
                out.push_str(&format!("  {id}:\n"));
                out.push_str(&format!("    never: {}\n", e.never));
                out.push_str(&format!("    skips: {}\n", e.skips));
                out.push_str(&format!("    accepts: {}\n", e.accepts));
            }
        }
        fs::write(&self.path, out)?;
        Ok(())
    }

    fn entrada_de<'a>(
        acciones: &'a [(String, PrefsEntrada)],
        action_id: &str,
    ) -> Option<&'a PrefsEntrada> {
        acciones
            .iter()
            .find(|(k, _)| k == action_id)
            .map(|(_, v)| v)
    }

    /// Registra 'accept' | 'skip' | 'never' para una acción.
    ///
    /// Un accept compensa hasta dos skips (v0 simple).
    pub fn registrar(&self, action_id: &str, eleccion: &str) -> Result<(), String> {
        let mut acciones = self.load();
        let base = Self::entrada_de(&acciones, action_id)
            .copied()
            .unwrap_or_default();
        let mut entrada = base;
        match eleccion {
            "never" => entrada.never = true,
            "skip" => entrada.skips += 1,
            "accept" => {
                entrada.accepts += 1;
                // un accept compensa hasta dos skips (v0 simple)
                if entrada.skips >= 2 {
                    entrada.skips -= 2;
                } else {
                    entrada.skips = 0;
                }
            }
            other => return Err(format!("elección inválida: '{other}'")),
        }
        if let Some(slot) = acciones.iter_mut().find(|(k, _)| k == action_id) {
            slot.1 = entrada;
        } else {
            acciones.push((action_id.to_string(), entrada));
        }
        self.guardar(&acciones).map_err(|e| e.to_string())
    }

    pub fn nunca_mas(&self, action_id: &str) -> bool {
        self.load()
            .iter()
            .find(|(k, _)| k == action_id)
            .map(|(_, e)| e.never)
            .unwrap_or(false)
    }

    /// Score multiplier v0: -15% por skip consecutivo (mínimo 0.4).
    pub fn penalizacion_skips(&self, action_id: &str) -> f64 {
        let skips = self
            .load()
            .iter()
            .find(|(k, _)| k == action_id)
            .map(|(_, e)| e.skips)
            .unwrap_or(0);
        let m = 1.0 - 0.15 * skips as f64;
        if m < 0.4 {
            0.4
        } else {
            m
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::ahora_iso;

    fn tmpdir(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!(
            "cortex-actions-test-{tag}-{}-{}",
            std::process::id(),
            chrono::Utc::now().timestamp_nanos_opt().unwrap_or_default()
        ));
        fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn action_log_append_y_load_ordenado() {
        let dir = tmpdir("log");
        let log = ActionLog::new(&dir);
        let mut e1 = OrderedEntry::new();
        e1.set("id", Value::String("a.ok".into()));
        e1.set("ts", Value::String(ahora_iso()));
        e1.set("dry_run", Value::Bool(false));
        e1.set("via", Value::String("auto".into()));
        log.append(e1).unwrap();

        let entradas = log.load();
        assert_eq!(entradas.len(), 1);
        assert_eq!(entradas[0]["id"], "a.ok");

        // orden de claves del archivo = orden de inserción (compat Python)
        let linea = fs::read_to_string(log.path()).unwrap();
        assert!(linea.starts_with("{\"id\": \"a.ok\", \"ts\": \""));
        assert!(linea.ends_with("\"via\": \"auto\"}\n"));
        fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn preferences_skip_baja_accept_compensa_never_suprime() {
        let dir = tmpdir("prefs");
        let prefs = PreferencesStore::new(&dir);

        prefs.registrar("vault.reindex", "skip").unwrap();
        assert!((prefs.penalizacion_skips("vault.reindex") - 0.85).abs() < 1e-12);
        prefs.registrar("vault.reindex", "accept").unwrap();
        assert!((prefs.penalizacion_skips("vault.reindex") - 1.0).abs() < 1e-12);

        for _ in 0..5 {
            prefs.registrar("vault.reindex", "skip").unwrap();
        }
        assert!((prefs.penalizacion_skips("vault.reindex") - 0.4).abs() < 1e-12);

        prefs.registrar("otra.x", "never").unwrap();
        assert!(prefs.nunca_mas("otra.x"));
        assert!(!prefs.nunca_mas("vault.reindex"));

        assert_eq!(
            prefs.registrar("x.y", "invalida").unwrap_err(),
            "elección inválida: 'invalida'"
        );
        fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn yaml_formato_compatible_python() {
        let dir = tmpdir("yamlfmt");
        let prefs = PreferencesStore::new(&dir);
        prefs.registrar("vault.reindex", "skip").unwrap();
        prefs.registrar("otra.x", "never").unwrap();
        prefs.registrar("vault.reindex", "skip").unwrap();
        prefs.registrar("vault.reindex", "skip").unwrap();
        prefs.registrar("vault.reindex", "accept").unwrap();
        prefs.registrar("vault.reindex", "accept").unwrap();
        prefs.registrar("vault.reindex", "accept").unwrap();
        let contenido = fs::read_to_string(prefs.path()).unwrap();
        let esperado = "acciones:\n\
                        vault.reindex:\n\
                        \x20   never: false\n\
                        \x20   skips: 2\n\
                        \x20   accepts: 7\n"
            .replacen("acciones:\nvault", "acciones:\n  vault", 1)
            .replace("vault.reindex:", "  vault.reindex:")
            .replace("otra.x:", "  otra.x:");
        // Comparamos contra el texto canónico esperado directamente:
        let canon = "acciones:\n  vault.reindex:\n    never: false\n    skips: 0\n    accepts: 3\n  otra.x:\n    never: true\n    skips: 0\n    accepts: 0\n";
        assert_eq!(contenido, canon);
        drop(esperado);
        fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn yaml_roto_se_ignora() {
        let dir = tmpdir("roto");
        fs::write(dir.join("actions.yaml"), "::: [esto no es yaml\n\t- x").unwrap();
        let prefs = PreferencesStore::new(&dir);
        assert!(!prefs.nunca_mas("cualquiera"));
        assert!((prefs.penalizacion_skips("cualquiera") - 1.0).abs() < 1e-12);
        fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn rotacion_de_log() {
        let dir = tmpdir("rot");
        let log = ActionLog::with_max_bytes(&dir, 10);
        let mut e = OrderedEntry::new();
        e.set("id", Value::String("a.b".into()));
        e.set("ts", Value::String(ahora_iso()));
        log.append(e.clone()).unwrap();
        log.append(e).unwrap(); // supera max_bytes=10 → rota
        assert!(dir.join(LOG_ROTADO).exists());
        assert_eq!(log.load().len(), 2); // lee ambos archivos
        fs::remove_dir_all(dir).ok();
    }
}
