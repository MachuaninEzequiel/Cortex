//! Spec conductual del brain nativo — espejo de los 13 tests de
//! tests/unit/brain/test_brain_v1.py (LA especificación de comportamiento).
//!
//! Las decisiones (routing, tiers, nunca-muta, ayuda en desconocido, banner
//! ≤80) deben coincidir; el renderizado exacto de respuestas de servicios
//! Python difiere por diseño (los servicios se consumen vía CLI).

use std::sync::Mutex;
static ENV_LOCK: Mutex<()> = Mutex::new(());

use cortex_brain::chat::{DeterministicBackend, LlmBackend, BANNER};
use cortex_brain::router::route_intent;
use cortex_brain::tools::{build_tools, dispatch, Tier};

#[test]
fn salud_a_cortex_health() {
    assert_eq!(
        route_intent("¿cómo está cortex?").tool.as_deref(),
        Some("cortex.health")
    );
}

#[test]
fn webgraph_a_serve() {
    assert_eq!(
        route_intent("abrí el grafo").tool.as_deref(),
        Some("webgraph.serve")
    );
}

#[test]
fn busqueda_extrae_query() {
    let intent = route_intent("busca docs sobre autenticación jwt");
    assert_eq!(intent.tool.as_deref(), Some("memory.search"));
    assert!(intent.args["query"].contains("autenticación"));
}

#[test]
fn pregunta_abierta_va_a_related() {
    assert_eq!(
        route_intent("que documentos hablan de la migracion de datos?")
            .tool
            .as_deref(),
        Some("docs.related")
    );
}

#[test]
fn slash_quit() {
    assert_eq!(route_intent("/quit").slash.as_deref(), Some("quit"));
}

#[test]
fn sin_match_devuelve_razon() {
    let intent = route_intent("xyzzy");
    assert!(intent.tool.is_none() && !intent.razon.is_empty());
}

#[test]
fn no_hay_herramientas_mutadoras() {
    let mutadoras = [
        "vault.reindex",
        "session.checkpoint_now",
        "setup.finish_bootstrap",
    ];
    let tools = build_tools();
    for m in mutadoras {
        assert!(!tools.contains_key(m), "el brain NUNCA ejecuta mutaciones");
    }
}

#[test]
fn todas_read_o_safe() {
    for spec in build_tools().values() {
        assert!(matches!(spec.tier, Tier::Read | Tier::SafeAction));
    }
}

#[test]
fn webgraph_es_safe_action() {
    assert_eq!(build_tools()["webgraph.serve"].tier, Tier::SafeAction);
}

#[test]
fn propose_nunca_ejecuta_mutaciones_y_ofrece_comando() {
    let _env = ENV_LOCK.lock().unwrap();
    unsafe { std::env::set_var("CORTEX_BIN", "/bin/echo") };
    // echo "next --json ..." ≠ JSON válido ⇒ falla ruidosa SIN ejecutar nada.
    let out = dispatch("actions.propose", &[]);
    unsafe { std::env::remove_var("CORTEX_BIN") };
    match out {
        Ok(texto) => assert!(texto.contains("propone"), "{texto}"),
        Err(e) => assert!(e.contains("JSON"), "{e}"),
    }
}

#[test]
fn desconocido_ofrece_ayuda() {
    let out = DeterministicBackend
        .generate("xyzzy sin sentido", "")
        .unwrap();
    assert!(out.contains("/help") || out.contains("Comandos"));
}

#[test]
fn banner_renderiza_en_80() {
    for line in BANNER.lines() {
        assert!(line.chars().count() <= 80);
    }
}

#[test]
fn doctor_responde_sin_modelo() {
    let _env = ENV_LOCK.lock().unwrap();
    unsafe { std::env::set_var("CORTEX_BIN", "/bin/echo") };
    let out = DeterministicBackend
        .generate("¿cómo está cortex?", "")
        .unwrap();
    unsafe { std::env::remove_var("CORTEX_BIN") };
    // Delega al CLI doctor: respuesta no vacía del servicio (render propio).
    assert!(!out.trim().is_empty());
}
