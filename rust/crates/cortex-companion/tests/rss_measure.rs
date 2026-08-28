//! Medición de RSS del flujo compuesto Home→Search (G-B1 nota: re-muestrear
//! en B4). Diagnóstico MANUAL: `cargo test -p cortex-companion --test rss_measure -- --ignored --nocapture`.
//! NO es un gate (el binario de release es la cifra operativa); detecta
//! fugas y documenta el objetivo ~15-25 MB. Medición adicional del binario
//! real en PTY: ver reporte B4.

use cortex_companion::engine::{Backend, InProcessBackend};

/// Fixture del repo para paridad (misma que usa tests/parity_cli.rs).
fn fixture() -> Option<std::path::PathBuf> {
    let src = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../../bench/parity/archive/.p12b-doctor/.work/ap_e2e/acme-api");
    src.exists().then_some(src)
}

/// Copia hermética mínima del fixture (como tests/parity_cli.rs) para no
/// tocar el fixture commiteado del bench.
fn copy_dir(src: &std::path::Path, dst: &std::path::Path) {
    for entry in std::fs::read_dir(src).expect("leer fixture") {
        let entry = entry.expect("entry");
        let target = dst.join(entry.file_name());
        if entry.file_type().expect("ftype").is_dir() {
            std::fs::create_dir_all(&target).expect("mkdir dst");
            copy_dir(&entry.path(), &target);
        } else {
            std::fs::copy(entry.path(), target).expect("copy file");
        }
    }
}

fn vm_rss_kb() -> Option<String> {
    let status = std::fs::read_to_string("/proc/self/status").ok()?;
    status
        .lines()
        .find(|l| l.starts_with("VmRSS:"))
        .map(|l| l.trim().to_string())
}

#[test]
#[ignore = "diagnóstico manual (documentada en el gate B4)"]
fn composite_flow_rss_print() {
    let src = fixture().expect("fixture de paridad presente en el worktree");
    let dst = std::env::temp_dir().join(format!("cortex-companion-rss-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dst);
    std::fs::create_dir_all(&dst).expect("mkdir rss fixture");
    copy_dir(&src, &dst);

    let be = InProcessBackend::open(&dst).expect("backend abre fixture");
    // Flujo compuesto: stats (slot sin embeddings) + search (slot con
    // embeddings) sobre la MISMA instancia, como lo hace el Home real.
    let _ = be.stats().expect("stats ok");
    let _ = be.search("auth", 5).expect("search ok");
    let _ = be.doctor().expect("doctor ok");
    let _ = be.next_actions().expect("next ok");

    // Muestreo en tight-loop para capturar el pico tras el warm-up.
    let mut peak_kb: Option<String> = None;
    for _ in 0..40 {
        peak_kb = vm_rss_kb();
        std::thread::sleep(std::time::Duration::from_millis(5));
    }
    let peak = peak_kb.unwrap_or_else(|| "<desconocido>".to_string());
    // NOTA operativa (ver reporte B4): el binario de TEST en debug linkea
    // todo onnx/tokenizers ⇒ RSS inflado por código estático; la cifra real
    // del binario en PTY (sin modelo ONNX instalado) fue ~4.3 MB. Con el
    // modelo instalado (~/.cache/cortex/models), `stats()` carga ONNX por
    // legado de NativeMemory → buscar desacople en B7.
    println!("VmRSS pico (test debug, flujo compuesto): {peak}");
    let _ = std::fs::remove_dir_all(&dst);
    // Bound anti-fuga únicamente (1 GB): si se supera, hay un leak real.
    let kb: u64 = peak
        .split_whitespace()
        .nth(1)
        .and_then(|v| v.parse().ok())
        .unwrap_or(0);
    assert!(
        kb < 1024 * 1024,
        "RSS compuesto {}kB superó el bound anti-fuga 1GB",
        kb
    );
}
