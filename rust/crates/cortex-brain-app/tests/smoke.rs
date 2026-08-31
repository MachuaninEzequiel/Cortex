//! Smoke test del crate. La verificación real (ventana abre) es manual;
//! este test garantiza que el binario al menos parsea argv sin panic.

use cortex_brain_app::Role;

#[test]
fn argv_vacio_resuelve_app() {
    let argv: Vec<String> = vec![];
    assert_eq!(Role::from_argv(&argv), Role::App);
}

#[test]
fn argv_con_query_resuelve_query_client() {
    let argv: Vec<String> = vec![
        "cortex-brain".into(),
        "--query".into(),
        "¿cómo está la sesión?".into(),
        "--project".into(),
        "/tmp".into(),
    ];
    assert_eq!(Role::from_argv(&argv), Role::QueryClient);
}
