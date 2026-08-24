//! i18n del brain — chrome ES/EN (espejo de cortex/action_engine/i18n.py).
//!
//! Los tests que tocan el idioma GLOBAL se serializan con un lock y siempre
//! restauran Es (default) para no contaminar otros tests del binario.

use std::sync::Mutex;

use cortex_brain::chat::{procesar_respuesta_modelo, LlmBackend, ScriptedBackend};
use cortex_brain::i18n::{self, Lang};
use cortex_brain::tools::build_tools;

fn lang_lock() -> std::sync::MutexGuard<'static, ()> {
    static LOCK: Mutex<()> = Mutex::new(());
    LOCK.lock().unwrap_or_else(|e| e.into_inner())
}

#[test]
fn ayuda_es_por_default() {
    let _g = lang_lock();
    i18n::fijar(Lang::Es);
    let h = cortex_brain::chat::help_text();
    assert!(h.contains("Comandos:"), "{h}");
    assert!(h.contains("El brain NUNCA ejecuta mutaciones"));
    assert!(h.contains("vault.stats"), "catálogo presente");
    i18n::fijar(Lang::Es);
}

#[test]
fn ayuda_en_traducida() {
    let _g = lang_lock();
    i18n::fijar(Lang::En);
    let h = cortex_brain::chat::help_text();
    assert!(h.contains("Commands:"), "{h}");
    assert!(h.contains("The brain NEVER runs mutations"));
    // El catálogo es invariante: nombres de tools no se traducen.
    assert!(h.contains("memory.search"), "{h}");
    i18n::fijar(Lang::Es);
}

#[test]
fn protocolo_tool_mensajes_en_ingles() {
    let _g = lang_lock();
    i18n::fijar(Lang::En);
    unsafe { std::env::set_var("CORTEX_BIN", "/bin/echo") };
    let mut backend = ScriptedBackend::new("script", ["TOOL: memory.search secreto"]);
    let raw = backend.generate("q", "").unwrap();
    let out = procesar_respuesta_modelo(&raw, &build_tools(), &mut |_, _| false);
    unsafe { std::env::remove_var("CORTEX_BIN") };
    assert!(out.contains("(not executed)"), "{out}");
    assert!(!out.contains("(no ejecutado)"), "{out}");

    let mut backend = ScriptedBackend::new("script", ["TOOL: vault.reindex todo"]);
    let raw = backend.generate("q", "").unwrap();
    let out = procesar_respuesta_modelo(&raw, &build_tools(), &mut |_, _| true);
    assert!(out.contains("unknown tool: vault.reindex"), "{out}");
    i18n::fijar(Lang::Es);
}

#[test]
fn detectar_respeta_convencion_python() {
    // Sin archivos ni env → es (DEFAULT_LANG de Python).
    let fantasma = std::path::Path::new("/no/existe/config.yaml");
    assert_eq!(i18n::detectar(None, fantasma, fantasma), Lang::Es);

    // Layout nuevo (.cortex/config.yaml) gana sobre legacy.
    let dir = std::env::temp_dir().join(format!("brain-i18n-layout-{}", std::process::id()));
    let nueva = dir.join(".cortex");
    std::fs::create_dir_all(&nueva).unwrap();
    std::fs::write(dir.join("config.yaml"), "ui:\n  language: es\n").unwrap();
    std::fs::write(nueva.join("config.yaml"), "ui:\n  language: en\n").unwrap();
    assert_eq!(
        i18n::detectar(None, &nueva.join("config.yaml"), &dir.join("config.yaml")),
        Lang::En
    );
    std::fs::remove_dir_all(&dir).ok();
}
