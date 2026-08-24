//! Protocolo TOOL del brain — backend falso scriptado (CI sin modelo).
//!
//! Cubre el contrato de 6a5479f (auto-despacho con confirmación) pero
//! testeable en librería: extracción de "TOOL: <nombre> <args>", separación
//! de la respuesta, gate de confirmación inyectable y despacho real vía CLI.
//! `ScriptedBackend` es el backend falso que CI usa para ejercitar el loop
//! completo sin GGUF.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use cortex_brain::chat::{
    confirma, extraer_tool, procesar_respuesta_modelo, LlmBackend, ScriptedBackend,
};
use cortex_brain::tools::build_tools;

// ── Extracción ──────────────────────────────────────────────────────────────

#[test]
fn extrae_tool_simple_sin_args() {
    assert_eq!(
        extraer_tool("TOOL: vault.stats"),
        Some(("vault.stats".into(), String::new()))
    );
}

#[test]
fn extrae_tool_con_args() {
    assert_eq!(
        extraer_tool("TOOL: memory.search autenticación jwt"),
        Some(("memory.search".into(), "autenticación jwt".into()))
    );
}

#[test]
fn extrae_primera_linea_tool_si_hay_varias() {
    let out = "pensando...\nTOOL: vault.stats\ny además\nTOOL: cortex.health";
    assert_eq!(
        extraer_tool(out),
        Some(("vault.stats".into(), String::new()))
    );
}

#[test]
fn sin_linea_tool_devuelve_none() {
    assert_eq!(extraer_tool("respuesta normal sin herramientas"), None);
}

#[test]
fn tool_con_espacios_interiores_se_normaliza() {
    assert_eq!(
        extraer_tool("TOOL:   memory.search     query  con  espacios "),
        Some(("memory.search".into(), "query con espacios".into()))
    );
}

// ── Confirmación (decisión pura) ────────────────────────────────────────────

#[test]
fn confirmacion_acepta_variantes_si() {
    for s in ["s", "S", "si", "SI", "Si", "sí", "SÍ"] {
        assert!(confirma(s), "{s} debe aprobar");
    }
}

#[test]
fn confirmacion_rechaza_default_negativo() {
    for s in ["", " ", "n", "N", "no", "NO", "y", "yes", "quizá"] {
        assert!(!confirma(s), "{s} debe rechazar");
    }
}

// ── Loop end-to-end con backend falso scriptado ─────────────────────────────

#[test]
fn scripted_backend_entrega_respuestas_en_orden_y_luego_falla() {
    let mut b = ScriptedBackend::new("script", ["uno", "dos"]);
    assert_eq!(b.name(), "script");
    assert_eq!(b.generate("q1", "").unwrap(), "uno");
    assert_eq!(b.generate("q2", "").unwrap(), "dos");
    assert!(
        b.generate("q3", "").is_err(),
        "script agotado = error ruidoso"
    );
}

#[test]
fn flujo_completo_sugiere_confirma_y_despacha() {
    let _env = env_lock();
    unsafe { std::env::set_var("CORTEX_BIN", "/bin/echo") };
    let mut backend = ScriptedBackend::new("script", ["TOOL: memory.search hola mundo"]);
    let raw = backend.generate("busca hola mundo", "").unwrap();

    let llamado = Arc::new(AtomicBool::new(false));
    let llamado2 = llamado.clone();
    let out = procesar_respuesta_modelo(&raw, &build_tools(), &mut move |t, a| {
        assert_eq!(t, "memory.search");
        assert_eq!(a, "hola mundo");
        llamado2.store(true, Ordering::SeqCst);
        true // usuario aprueba
    });
    unsafe { std::env::remove_var("CORTEX_BIN") };

    assert!(llamado.load(Ordering::SeqCst), "confirmación consultada");
    // /bin/echo imprime sus argumentos ⇒ prueba de que DESPACHÓ de verdad:
    // memory.search se traduce al CLI `cortex search <q>`.
    assert!(out.contains("search hola mundo"), "salida: {out}");
    assert!(!out.contains("(no ejecutado)"));
}

#[test]
fn flujo_completo_rechaza_y_no_despacha() {
    let _env = env_lock();
    unsafe { std::env::set_var("CORTEX_BIN", "/bin/echo") };
    let mut backend = ScriptedBackend::new("script", ["TOOL: memory.search secreto"]);
    let raw = backend.generate("q", "").unwrap();

    let out = procesar_respuesta_modelo(&raw, &build_tools(), &mut |_, _| false);
    unsafe { std::env::remove_var("CORTEX_BIN") };

    assert!(out.contains("(no ejecutado)"), "salida: {out}");
    assert!(!out.contains("secreto\nsecreto"), "el echo no debe correr");
    // La línea TOOL nunca se muestra cruda al usuario.
    assert!(!out.contains("TOOL:"));
}

// TDD: esta prueba exige que una tool FUERA del catálogo (ej. mutación
// vault.reindex) jamás llegue al despacho aunque "el usuario" apruebe.
#[test]
fn flujo_tool_inexistente_nunca_despacha() {
    let _env = env_lock();
    unsafe { std::env::set_var("CORTEX_BIN", "/bin/echo") };
    let mut backend = ScriptedBackend::new("script", ["TOOL: vault.reindex todo"]);
    let raw = backend.generate("q", "").unwrap();

    let out = procesar_respuesta_modelo(&raw, &build_tools(), &mut |_, _| true);
    unsafe { std::env::remove_var("CORTEX_BIN") };

    assert!(out.contains("inexistente"), "salida: {out}");
    assert!(!out.contains("vault.reindex todo"), "jamás despacha");
}

#[test]
fn respuesta_con_texto_y_tool_muestra_texto_sin_la_linea_tool() {
    let mut backend = ScriptedBackend::new(
        "script",
        ["Te conviene ver las acciones.\nTOOL: actions.propose"],
    );
    let raw = backend.generate("q", "").unwrap();
    let out = procesar_respuesta_modelo(&raw, &build_tools(), &mut |_, _| false);
    assert!(out.contains("Te conviene ver las acciones."));
    assert!(!out.contains("TOOL:"));
}

// ── helpers ─────────────────────────────────────────────────────────────────

fn env_lock() -> std::sync::MutexGuard<'static, ()> {
    use std::sync::Mutex;
    static LOCK: Mutex<()> = Mutex::new(());
    LOCK.lock().unwrap_or_else(|e| e.into_inner())
}
