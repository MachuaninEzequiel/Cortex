//! Gate CIERRE T6 — pantalla sesiones ratatui.
//!
//! Contrato: (a) los DATOS mostrados son idénticos a lo que emite
//! `cortex session list --json` (`_record_summary` + orden newest-first +
//! marca de activa), verificado contra la serialización JSON de las mismas
//! filas; (b) snapshot render bajo presupuesto <50ms; (c) determinismo y
//! estado vacío. Fuente canónica: SessionService nativo sobre fixtures
//! reales en tmp.

use cortex_app::session::service::SessionService;
use cortex_app::session::{CheckpointSource, SessionStorage};
use cortex_tui::sessions::{SessionRow, SessionsScreenData, RENDER_BUDGET_MS};
use ratatui::backend::TestBackend;
use ratatui::{Terminal, TerminalOptions, Viewport};

fn draw(w: u16, h: u16, data: &SessionsScreenData) -> String {
    let backend = TestBackend::new(w, h);
    let mut terminal = Terminal::with_options(
        backend,
        TerminalOptions {
            viewport: Viewport::Fixed(ratatui::prelude::Rect::new(0, 0, w, h)),
        },
    )
    .unwrap();
    terminal
        .draw(|f| cortex_tui::sessions::render(f, data))
        .unwrap();
    let buf = terminal.backend().buffer();
    let mut s = String::new();
    for y in 0..buf.area.height {
        for x in 0..buf.area.width {
            s.push_str(buf[(x, y)].symbol());
        }
        s.push('\n');
    }
    s
}

fn fixture_root(tag: &str) -> (tempfile::TempDir, SessionService) {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().join(tag);
    std::fs::create_dir_all(&root).unwrap();
    let storage = SessionStorage::new(root.join(".cortex").join("sessions"));
    (tmp, SessionService::new(storage, &root))
}

const TS_A: &str = "2026-05-16T10:00:00+00:00";
const TS_B: &str = "2026-05-17T10:00:00+00:00";

/// Dos sesiones reales con timestamps fijados por YAML directo (determinista).
fn seed_two_sessions(svc: &SessionService) {
    svc.open(
        "2026-05-16_demo",
        "vault/specs/2026-05-16_demo.md",
        "Primera demo",
    )
    .unwrap();
    svc.open(
        "2026-05-17_segunda",
        "vault/specs/2026-05-17_segunda.md",
        "Segunda demo",
    )
    .unwrap();
}

#[test]
fn datos_mostrados_iguales_a_session_list_json() {
    let (_tmp, svc) = fixture_root("parity");
    seed_two_sessions(&svc);

    // Fijar timestamps deterministas editando el YAML del storage nativo.
    for (id, ts) in [("2026-05-16_demo", TS_A), ("2026-05-17_segunda", TS_B)] {
        let p = _tmp
            .path()
            .join("parity/.cortex/sessions")
            .join(format!("{id}.yaml"));
        let text = std::fs::read_to_string(&p).unwrap();
        let idx = text.find("opened_at:").unwrap() + "opened_at:".len();
        let end = text[idx..].find('\n').map(|e| idx + e).unwrap();
        std::fs::write(&p, format!("{} {}{}", &text[..idx], ts, &text[end..])).unwrap();
    }

    // Un checkpoint real en la primera para checkpoint_count=1.
    svc.checkpoint(
        "2026-05-16_demo",
        CheckpointSource::Manual,
        vec!["claim".into()],
        vec![],
        vec![],
        "nota",
        None,
    )
    .unwrap();

    let data = SessionsScreenData::from_service(&svc, None).unwrap();

    // Orden newest-first como list_command.
    assert_eq!(data.rows[0].session_id, "2026-05-17_segunda");
    assert_eq!(data.rows[1].session_id, "2026-05-16_demo");

    // La serialización de cada fila == payload exacto de `list --json`.
    let json_rows: Vec<serde_json::Value> = data.rows.iter().map(SessionRow::to_json).collect();
    let r0 = &json_rows[0];
    assert_eq!(r0["session_id"], "2026-05-17_segunda");
    assert_eq!(r0["status"], "open");
    // OPEN ⇒ mode "unknown": infer_mode recién al cerrar (como el oráculo).
    assert_eq!(r0["mode"], "unknown");
    assert_eq!(r0["opened_at"], TS_B);
    assert_eq!(r0["closed_at"], serde_json::Value::Null);
    assert_eq!(r0["checkpoint_count"], 0);
    assert_eq!(r0["spec_summary"], "Segunda demo");
    let r1 = &json_rows[1];
    assert_eq!(r1["checkpoint_count"], 1);
    assert_eq!(r1["spec_summary"], "Primera demo");

    // TODO valor del --json aparece en el render.
    let s = draw(100, 20, &data);
    for row in &data.rows {
        assert!(s.contains(&row.session_id), "falta id {}", row.session_id);
        assert!(s.contains(&row.status), "falta status");
        assert!(s.contains(&row.mode), "falta mode");
        assert!(
            s.contains(row.checkpoint_count.to_string().as_str()),
            "faltan checkpoints"
        );
        assert!(
            s.contains(&truncate_summary(&row.spec_summary)),
            "falta summary"
        );
    }
    // Marca de activa sobre la sesión activa (la última abierta).
    assert!(s.contains('*'), "falta marca activa");
}

fn truncate_summary(s: &str) -> String {
    if s.chars().count() <= 40 {
        s.to_string()
    } else {
        s.chars().take(40).collect()
    }
}

#[test]
fn filtro_por_status_y_activo_nulo() {
    let (_tmp, svc) = fixture_root("filter");
    seed_two_sessions(&svc);
    svc.close(
        "2026-05-17_segunda",
        cortex_app::session::SessionStatus::Closed,
        cortex_app::session::SessionStatus::Closed,
        None,
        vec![],
    )
    .unwrap();

    let open =
        SessionsScreenData::from_service(&svc, Some(cortex_app::session::SessionStatus::Open))
            .unwrap();
    assert_eq!(open.rows.len(), 1);
    assert_eq!(open.rows[0].status, "open");

    let all = SessionsScreenData::from_service(&svc, None).unwrap();
    assert_eq!(all.rows.len(), 2);
    // La cerrada muestra closed_at no nulo en su JSON y mode inferido
    // (sin checkpoints ⇒ byo, como `session list --json`).
    let closed_row = all
        .rows
        .iter()
        .find(|r| r.session_id == "2026-05-17_segunda")
        .unwrap();
    assert!(closed_row.closed_at.is_some());
    let j = closed_row.to_json();
    assert_eq!(j["status"], "closed");
    assert_eq!(j["mode"], "byo");
}

#[test]
fn pantalla_vacia_mensaje_contratual() {
    let (_tmp, svc) = fixture_root("empty");
    let data = SessionsScreenData::from_service(&svc, None).unwrap();
    let s = draw(60, 10, &data);
    assert!(s.contains("(no sessions on disk)"), "mensaje vacío ausente");
}

#[test]
fn render_determinista() {
    let (_tmp, svc) = fixture_root("det");
    seed_two_sessions(&svc);
    let data = SessionsScreenData::from_service(&svc, None).unwrap();
    let a = draw(90, 18, &data);
    let b = draw(90, 18, &data);
    assert_eq!(a, b);
}

#[test]
fn render_bajo_presupuesto_50ms() {
    let (_tmp, svc) = fixture_root("latency");
    seed_two_sessions(&svc);
    let data = SessionsScreenData::from_service(&svc, None).unwrap();
    let n = 200;
    let t0 = std::time::Instant::now();
    for _ in 0..n {
        let _ = draw(100, 20, &data);
    }
    let avg = t0.elapsed() / n;
    assert!(
        avg.as_millis() < RENDER_BUDGET_MS,
        "render promedio {avg:?} ≥ presupuesto {RENDER_BUDGET_MS}ms"
    );
}
