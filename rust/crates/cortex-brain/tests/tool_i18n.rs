//! i18n de las salidas de tools del brain (dispatch/propose/run_cli).
//!
//! Las tools son la capa que renderiza respuestas al usuario; con
//! `ui.language: en` deben salir en inglés. Los tests tocan el idioma global
//! bajo lock y restauran Es al final.

use std::sync::Mutex;

use cortex_brain::i18n::{self, Lang};
use cortex_brain::tools::dispatch;

fn lang_lock() -> std::sync::MutexGuard<'static, ()> {
    static LOCK: Mutex<()> = Mutex::new(());
    LOCK.lock().unwrap_or_else(|e| e.into_inner())
}

#[test]
fn falta_query_en_ingles() {
    let _g = lang_lock();
    i18n::fijar(Lang::En);
    let err = dispatch("memory.search", &[]).unwrap_err();
    assert_eq!(err, "missing <query>");
    i18n::fijar(Lang::Es);
    let err = dispatch("memory.search", &[]).unwrap_err();
    assert_eq!(err, "falta <query>");
}

#[test]
fn related_pide_precision_en_ambos_idiomas() {
    let _g = lang_lock();

    i18n::fijar(Lang::En);
    let out = dispatch("docs.related", &[]).unwrap();
    assert!(out.contains("precision"), "{out}");
    assert!(out.contains("docs.related <topic>"), "{out}");

    i18n::fijar(Lang::Es);
    let out = dispatch("docs.related", &[]).unwrap();
    assert!(out.contains("precisión"), "{out}");
    assert!(out.contains("docs.related <tema>"), "{out}");
}

#[test]
fn vault_stats_cuenta_en_idioma_vigente() {
    let _g = lang_lock();
    // cwd del test = crate root; vault/ no existe ahí ⇒ 0 notas.
    i18n::fijar(Lang::En);
    let out = dispatch("vault.stats", &[]).unwrap();
    assert!(out.starts_with("Vault: "), "{out}");
    assert!(out.ends_with(" .md notes"), "{out}");

    i18n::fijar(Lang::Es);
    let out = dispatch("vault.stats", &[]).unwrap();
    assert!(out.ends_with(" notas .md"), "{out}");
}

#[test]
fn propose_en_no_menciona_comandos_espanoles() {
    unsafe {
        std::env::set_var("CORTEX_BIN", "/bin/echo");
    }
    let _g = lang_lock();
    i18n::fijar(Lang::En);
    let out = dispatch("actions.propose", &[]);
    unsafe { std::env::remove_var("CORTEX_BIN") };
    match out {
        Ok(texto) => {
            assert!(
                texto.contains("suggested actions") || texto.contains("Nothing pending"),
                "{texto}"
            );
            assert!(!texto.contains("ejecutalas VOS"), "{texto}");
        }
        Err(e) => assert!(e.contains("JSON") || e.contains("invalid JSON"), "{e}"),
    }
    i18n::fijar(Lang::Es);
}
