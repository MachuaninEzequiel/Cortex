//! G-B1 — paridad por construcción: el engine in-proceso produce las MISMAS
//! salidas JSON que el binario CLI sobre el mismo fixture.
//!
//! Uso: `cargo build -p cortex-cli` primero (el binario CLI se ubica en
//! target/debug; se puede sobreescribir con la env `CORTEX_BIN`).

use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

use cortex_companion::engine::{Backend, InProcessBackend};

/// Fixture commiteado del repo (mismo que usan los gates de doctor).
const FIXTURE_REL: &str = "../../../bench/parity/archive/.p12b-doctor/.work/ap_e2e/acme-api";

fn cli_bin() -> PathBuf {
    if let Ok(p) = std::env::var("CORTEX_BIN") {
        return PathBuf::from(p);
    }
    let default = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../target/debug/cortex-cli");
    assert!(
        default.is_file(),
        "compilá primero el CLI: `cargo build -p cortex-cli` (buscado en {})",
        default.display()
    );
    default
}

fn copy_dir(src: &Path, dst: &Path) -> std::io::Result<()> {
    std::fs::create_dir_all(dst)?;
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        let target = dst.join(entry.file_name());
        if entry.file_type()?.is_dir() {
            copy_dir(&entry.path(), &target)?;
        } else {
            std::fs::copy(entry.path(), &target)?;
        }
    }
    Ok(())
}

/// Copia hermética del fixture (única por corrida) + una nota más en el
/// vault para que la búsqueda "auth" tenga resultados semánticos.
fn fixture_project() -> PathBuf {
    let src = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(FIXTURE_REL);
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("reloj pre-epoch")
        .as_nanos();
    let dst = std::env::temp_dir().join(format!(
        "cortex-companion-parity-{}-{nanos}",
        std::process::id()
    ));
    copy_dir(&src, &dst).expect("copiar fixture ap_e2e");
    std::fs::create_dir_all(dst.join("vault/architecture")).unwrap();
    std::fs::write(
        dst.join("vault/architecture/auth.md"),
        "---\ntitle: Auth\n---\n\n# Authentication\n\nFlujo OAuth y emisión de tokens JWT firmados por el servicio de auth.\n",
    )
    .unwrap();
    dst
}

/// Normaliza `"elapsed_ms": <digits>` (variable real) para comparar byte a
/// byte el payload de `next` (patrón {{ELAPSED}} de los gates).
fn strip_elapsed_ms(s: &str) -> String {
    let marker = "\"elapsed_ms\"";
    let bytes = s.as_bytes();
    let mut out = String::new();
    let mut idx = 0;
    while let Some(rel) = s[idx..].find(marker) {
        let start = idx + rel;
        out.push_str(&s[idx..start]);
        let rest = &s[start..];
        let colon = start + rest.find(':').expect("colon tras elapsed_ms");
        let mut end = colon + 1;
        while end < bytes.len() && bytes[end].is_ascii_whitespace() {
            end += 1;
        }
        while end < bytes.len() && bytes[end].is_ascii_digit() {
            end += 1;
        }
        out.push_str(&s[start..=colon]);
        out.push_str(" 0");
        idx = end;
    }
    out.push_str(&s[idx..]);
    out
}

#[test]
fn session_list_json_equals_cli() {
    let fixture = fixture_project();
    let be = InProcessBackend::open(&fixture).expect("abrir backend");

    let engine = be.session_list_json().expect("session list json engine");
    let cli = Command::new(cli_bin())
        .args([
            "session",
            "list",
            "--json",
            "--project-root",
            fixture.to_str().unwrap(),
        ])
        .output()
        .expect("correr CLI");
    assert!(
        cli.status.success(),
        "CLI rc={:?}: {}",
        cli.status.code(),
        String::from_utf8_lossy(&cli.stderr)
    );
    let cli_out = String::from_utf8(cli.stdout).unwrap().trim().to_string();

    assert_eq!(
        engine, cli_out,
        "session list --json debe ser byte-idéntico"
    );
    assert!(
        cli_out.contains("2026-05-16_demo"),
        "el fixture debe listar su sesión"
    );
    let _ = std::fs::remove_dir_all(fixture);
}

#[test]
fn stats_then_search_same_instance_matches_cli() {
    // Regresión G-B1 fix round 1: el singleton de memoria quedaba
    // mode-locked por el primer accesor. stats() abre el slot SIN
    // embeddings (flujo Home); search() posterior sobre la MISMA instancia
    // debe abrir su propio slot CON embeddings y ser byte-idéntico al CLI
    // (que siempre busca con embeddings).
    let fixture = fixture_project();
    let be = InProcessBackend::open(&fixture).expect("abrir backend");

    // stats() primero — camino de Home; abre el slot sin embeddings.
    let stats = be.stats().expect("stats");
    assert!(
        stats.semantic > 0,
        "el vault del fixture debe tener docs semánticas"
    );

    // search() después, sobre la MISMA instancia — camino de Search.
    let engine = be.search_json("auth", 5).expect("search json engine");
    let cli = Command::new(cli_bin())
        .current_dir(&fixture)
        .args(["search", "auth", "--json", "--top-k", "5"])
        .output()
        .expect("correr CLI");
    assert!(
        cli.status.success(),
        "CLI rc={:?}: {}",
        cli.status.code(),
        String::from_utf8_lossy(&cli.stderr)
    );
    let cli_out = String::from_utf8(cli.stdout).unwrap().trim().to_string();

    assert_eq!(
        engine, cli_out,
        "search tras stats (misma instancia) debe ser byte-idéntico al CLI — \
         el slot sin embeddings no debe contaminar la búsqueda"
    );
    assert!(
        engine.contains("semantic") || engine.contains("unified_hits"),
        "shape esperado de RetrievalResult"
    );
    let _ = std::fs::remove_dir_all(fixture);
}

#[test]
fn search_json_equals_cli() {
    let fixture = fixture_project();
    let be = InProcessBackend::open(&fixture).expect("abrir backend");

    let engine = be.search_json("auth", 5).expect("search json engine");

    // `cortex search` NO acepta --project-root ⇒ cwd apuntando al fixture.
    let cli = Command::new(cli_bin())
        .current_dir(&fixture)
        .args(["search", "auth", "--json", "--top-k", "5"])
        .output()
        .expect("correr CLI");
    assert!(
        cli.status.success(),
        "CLI rc={:?}: {}",
        cli.status.code(),
        String::from_utf8_lossy(&cli.stderr)
    );
    let cli_out = String::from_utf8(cli.stdout).unwrap().trim().to_string();

    assert_eq!(engine, cli_out, "search --json debe ser byte-idéntico");
    assert!(
        cli_out.contains("unified_hits"),
        "shape esperado de RetrievalResult"
    );
    let _ = std::fs::remove_dir_all(fixture);
}

#[test]
fn next_json_equals_cli_normalized_elapsed() {
    let fixture = fixture_project();
    let be = InProcessBackend::open(&fixture).expect("abrir backend");

    let engine = strip_elapsed_ms(&be.next_actions_json().expect("next json engine"));
    let cli = Command::new(cli_bin())
        .args([
            "next",
            "--json",
            "--project-root",
            fixture.to_str().unwrap(),
        ])
        .output()
        .expect("correr CLI");
    assert!(
        cli.status.success(),
        "CLI rc={:?}: {}",
        cli.status.code(),
        String::from_utf8_lossy(&cli.stderr)
    );
    let cli_out = strip_elapsed_ms(String::from_utf8(cli.stdout).unwrap().trim());

    assert_eq!(
        engine, cli_out,
        "next --json debe ser byte-idéntico (elapsed_ms normalizado)"
    );
    assert!(
        cli_out.contains("\"acciones\""),
        "shape esperado de next --json"
    );
    let _ = std::fs::remove_dir_all(fixture);
}

#[test]
fn session_current_none_without_active_session() {
    let fixture = fixture_project();
    // Sin puntero activo: `get_active` → None.
    let _ = std::fs::remove_file(fixture.join(".cortex/sessions/active.txt"));
    let be = InProcessBackend::open(&fixture).expect("abrir backend");

    let current = be.session_current().expect("session current sin error");
    assert!(
        current.is_none(),
        "sin active.txt no debe haber sesión activa"
    );

    // Sanidad: los structs del trait funcionan (lectura por defecto).
    let list = be.session_list().expect("session list");
    assert_eq!(list.len(), 1, "el fixture tiene 1 sesión");
    assert_eq!(list[0].id, "2026-05-16_demo");
    assert_eq!(list[0].status, "open");
    let _ = std::fs::remove_dir_all(fixture);
}
