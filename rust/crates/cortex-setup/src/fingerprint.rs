//! SHA-256 hex idéntico a `cortex.documentation.common.compute_fingerprint`.

use sha2::{Digest, Sha256};

/// SHA-256 hex digest lowercase de 64 caracteres del contenido UTF-8.
pub fn compute_fingerprint(content: &str) -> String {
    let digest = Sha256::digest(content.as_bytes());
    let mut hex = String::with_capacity(64);
    for b in digest {
        hex.push_str(&format!("{b:02x}"));
    }
    hex
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_vector() {
        assert_eq!(
            compute_fingerprint(""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
        assert_eq!(compute_fingerprint("hola").len(), 64);
    }
}
