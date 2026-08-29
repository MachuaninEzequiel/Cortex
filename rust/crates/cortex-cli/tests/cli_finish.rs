#[test]
fn finish_help_existe() {
    let bin = env!("CARGO_BIN_EXE_cortex-cli");
    let out = std::process::Command::new(bin)
        .args(["finish", "--help"])
        .output()
        .expect("cortex finish --help");
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("finish") || stdout.contains("Cierra la sesión"));
}

#[test]
fn finish_cierra_sesion_fixture() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path();
    let ses_dir = root.join(".cortex").join("sessions");
    std::fs::create_dir_all(&ses_dir).unwrap();
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    let storage = cortex_app::session::SessionStorage::new(ses_dir);
    let rec = cortex_app::session::SessionRecord {
        session_id: "2026-08-29_testfinish".into(),
        status: cortex_app::session::SessionStatus::Open,
        opened_at: "2026-08-29T00:00:00+00:00".into(),
        ..Default::default()
    };
    storage.save(&rec).unwrap();
    storage
        .set_active_session_id(Some("2026-08-29_testfinish"))
        .unwrap();

    let res = cortex_cli::commands::finish_cmd::finish_session(
        Some(root),
        Some("2026-08-29_testfinish"),
        "auto",
    );
    assert!(res.is_ok(), "finish_session failed: {res:?}");

    let read_back = storage.load("2026-08-29_testfinish").unwrap();
    assert!(read_back.status.is_terminal());
}
