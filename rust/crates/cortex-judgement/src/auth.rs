//! Resolución de la API key: env primero, luego llavero del OS.
//! Nunca se escribe en YAML / org.yaml / git.

const SERVICE: &str = "cortex.typesafe";

/// Env gana. Si está vacía, se consulta el llavero (error ⇒ None, fail-open).
pub fn resolve_api_key(env_name: &str) -> Option<String> {
    if let Ok(v) = std::env::var(env_name) {
        let t = v.trim();
        if !t.is_empty() {
            return Some(t.to_string());
        }
    }
    keyring_get(env_name)
}

pub fn key_configured(env_name: &str) -> bool {
    resolve_api_key(env_name).is_some()
}

pub fn store_api_key(env_name: &str, key: &str) -> Result<(), String> {
    let trimmed = key.trim();
    if trimmed.is_empty() {
        delete_api_key(env_name);
        return Ok(());
    }
    keyring_set(env_name, trimmed)
}

pub fn delete_api_key(env_name: &str) {
    if let Ok(entry) = keyring::Entry::new(SERVICE, env_name) {
        let _ = entry.delete_credential();
    }
}

fn keyring_get(env_name: &str) -> Option<String> {
    let entry = keyring::Entry::new(SERVICE, env_name).ok()?;
    match entry.get_password() {
        Ok(p) if !p.trim().is_empty() => Some(p),
        _ => None,
    }
}

fn keyring_set(env_name: &str, value: &str) -> Result<(), String> {
    let entry = keyring::Entry::new(SERVICE, env_name).map_err(|e| format!("llavero: {e}"))?;
    entry
        .set_password(value)
        .map_err(|e| format!("no se pudo guardar la key en el llavero del OS: {e}"))
}
