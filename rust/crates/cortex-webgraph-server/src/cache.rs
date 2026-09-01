//! Porteo de `cortex/webgraph/cache.py` — caché persistente de snapshots.
//!
//! El fingerprint replica byte-a-byte el hashlib de Python:
//! json.dumps(config_payload, sort_keys=True) [separadores DEFAULT de
//! Python] + hash_tree(vault) + hash_tree(episodic) + count + token.
//! hash_tree recorre archivos ordenados por PARTES de ruta (comparación
//! Path de Python, no por string completo) con mtime_ns y size.

#![forbid(unsafe_code)]

use std::path::{Path, PathBuf};

use sha2::Digest;

use cortex_workspace::WorkspaceLayout;

pub struct WebGraphCache {
    pub project_root: PathBuf,
    pub cache_dir: PathBuf,
}

fn file_parts_relative(root: &Path, path: &Path) -> Option<Vec<String>> {
    path.strip_prefix(root).ok().map(|rel| {
        rel.iter()
            .map(|c| c.to_string_lossy().to_string())
            .collect()
    })
}

impl WebGraphCache {
    pub fn new(project_root: &Path, layout: Option<&WorkspaceLayout>) -> Self {
        let default_layout;
        let layout: &WorkspaceLayout = match layout {
            Some(l) => l,
            None => {
                default_layout = WorkspaceLayout::discover(project_root);
                &default_layout
            }
        };
        let cache_dir = layout.webgraph_cache_dir();
        let _ = std::fs::create_dir_all(&cache_dir);
        Self {
            project_root: project_root.to_path_buf(),
            cache_dir,
        }
    }

    pub fn snapshot_path(&self, mode: &str, scope: Option<&str>) -> PathBuf {
        match scope {
            None | Some("all") => self.cache_dir.join(format!("snapshot-{mode}.json")),
            Some(s) => self.cache_dir.join(format!("snapshot-{mode}-{s}.json")),
        }
    }

    fn meta_path(&self) -> PathBuf {
        self.cache_dir.join("meta.json")
    }

    fn meta_key(mode: &str, scope: Option<&str>) -> String {
        match scope {
            None | Some("all") => mode.to_string(),
            Some(s) => format!("{mode}:{s}"),
        }
    }

    /// load_snapshot: None si no existe o el fingerprint difiere.
    /// Formato interno (serde_json pretty); el contrato conductual es que
    /// la respuesta cacheada == respuesta fresca.
    pub fn load_snapshot(
        &self,
        mode: &str,
        fingerprint: &str,
        scope: Option<&str>,
    ) -> Option<crate::contracts::WebGraphSnapshot> {
        let path = self.snapshot_path(mode, scope);
        let meta_path = self.meta_path();
        if !path.exists() || !meta_path.exists() {
            return None;
        }
        let meta: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(&meta_path).ok()?).ok()?;
        let expected = meta.get(Self::meta_key(mode, scope))?.as_str()?;
        if expected != fingerprint {
            return None;
        }
        let snap: Option<crate::contracts::WebGraphSnapshot> =
            serde_json::from_str(&std::fs::read_to_string(&path).ok()?).ok();
        snap
    }

    pub fn store_snapshot(
        &self,
        mode: &str,
        snapshot: &crate::contracts::WebGraphSnapshot,
        scope: Option<&str>,
    ) -> PathBuf {
        let path = self.snapshot_path(mode, scope);
        let _ = std::fs::create_dir_all(path.parent().unwrap_or(Path::new(".")));
        let _ = std::fs::write(
            &path,
            serde_json::to_string_pretty(snapshot).unwrap_or_default(),
        );
        let meta_path = self.meta_path();
        let mut meta: serde_json::Value = meta_path
            .exists()
            .then(|| {
                serde_json::from_str(&std::fs::read_to_string(&meta_path).unwrap_or_default()).ok()
            })
            .flatten()
            .unwrap_or(serde_json::json!({}));
        if !meta.is_object() {
            meta = serde_json::json!({});
        }
        meta[Self::meta_key(mode, scope)] = serde_json::Value::String(snapshot.fingerprint.clone());
        let _ = std::fs::write(
            &meta_path,
            serde_json::to_string_pretty(&meta).unwrap_or_default(),
        );
        path
    }

    pub fn compute_fingerprint(
        &self,
        vault_path: &Path,
        episodic_path: &Path,
        episodic_count: usize,
        episodic_cache_token: i64,
        config_payload: &serde_json::Value,
    ) -> String {
        let mut hasher = sha2::Sha256::new();
        hasher.update(
            crate::pyjson::dumps(config_payload, crate::pyjson::Mode::PythonDefault, true)
                .as_bytes(),
        );
        Self::hash_tree(&mut hasher, vault_path);
        Self::hash_tree(&mut hasher, episodic_path);
        hasher.update(episodic_count.to_string().as_bytes());
        hasher.update(episodic_cache_token.to_string().as_bytes());
        let digest = hasher.finalize();
        let hex: String = digest.iter().map(|b| format!("{b:02x}")).collect();
        hex
    }

    fn hash_tree<D: Digest>(hasher: &mut D, root: &Path) {
        if !root.exists() {
            hasher.update(format!("missing:{}", root.display()).as_bytes());
            return;
        }
        let mut files: Vec<(Vec<String>, PathBuf)> = Vec::new();
        collect_files(root, root, &mut files);
        // sorted() de Python sobre Paths compara por PARTES.
        files.sort_by(|a, b| a.0.cmp(&b.0));
        for (parts, path) in &files {
            hasher.update(parts.join("/").as_bytes());
            if let Ok(meta) = std::fs::metadata(path) {
                let mtime_ns = meta
                    .modified()
                    .ok()
                    .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                    .map(|d| d.as_nanos())
                    .unwrap_or(0);
                hasher.update(mtime_ns.to_string().as_bytes());
                hasher.update(meta.len().to_string().as_bytes());
            }
        }
    }
}

fn collect_files(root: &Path, dir: &Path, out: &mut Vec<(Vec<String>, PathBuf)>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let p = entry.path();
        if p.is_dir() {
            collect_files(root, &p, out);
        } else if p.is_file() {
            if let Some(parts) = file_parts_relative(root, &p) {
                out.push((parts, p));
            }
        }
    }
}
