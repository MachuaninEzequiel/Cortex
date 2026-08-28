//! Snapshots de render con TestBackend (prompt-logo.md §45 + rediseño F2):
//! Full/Compact/Minimal sin panic, sin escritura fuera del área, variante
//! correcta según breakpoint, determinismo, gate de latencia del Home
//! (<50ms), y los snapshots de tamaño del rediseño (spec §16.3):
//! 160×45 / 100×30 / 80×24 / 68×20 / 40×12 / TooSmall, invariantes
//! 1×1..200×80 y reloj inyectado en los tiempos relativos.

use chrono::{DateTime, Utc};
use cortex_tui::app::{update as reducer, Action, AppState, LoadState};
use cortex_tui::sessions::{rel_time, SessionRow, SessionsScreenData};
use ratatui::backend::TestBackend;
use ratatui::{Terminal, TerminalOptions, Viewport};

fn draw(w: u16, h: u16, f: impl FnOnce(&mut ratatui::Frame<'_>)) -> ratatui::buffer::Buffer {
    let backend = TestBackend::new(w, h);
    let mut terminal = Terminal::with_options(
        backend,
        TerminalOptions {
            viewport: Viewport::Fixed(ratatui::prelude::Rect::new(0, 0, w, h)),
        },
    )
    .unwrap();
    terminal.draw(f).unwrap();
    terminal.backend().buffer().clone()
}

fn symbols(buf: &ratatui::buffer::Buffer) -> String {
    let mut s = String::new();
    for y in 0..buf.area.height {
        for x in 0..buf.area.width {
            s.push_str(buf[(x, y)].symbol());
        }
        s.push('\n');
    }
    s
}

// ── gates P10 (sin cambios en el contrato) ─────────────────────────────────

#[test]
fn splash_full_en_pantalla_grande() {
    let buf = draw(100, 30, |f| {
        cortex_tui::splash::render(f, cortex_tui::env_color_mode())
    });
    assert_eq!(
        cortex_tui::branding_mode(buf.area),
        cortex_tui::BrandingMode::Full
    );
    let s = symbols(&buf);
    // Isotipo presente (half-blocks) y wordmark pixel.
    assert!(s.contains('▀') || s.contains('█'), "falta el isotipo");
    // Aire alrededor (prompt §42): la primera fila es espacio.
    assert!(s.lines().next().unwrap().trim().is_empty());
    assert!(s.lines().last().unwrap().trim().is_empty());
}

#[test]
fn splash_compact_en_pantalla_mediana() {
    let buf = draw(70, 20, |f| {
        cortex_tui::splash::render(f, cortex_tui::env_color_mode())
    });
    assert_eq!(
        cortex_tui::branding_mode(buf.area),
        cortex_tui::BrandingMode::Compact
    );
    assert!(symbols(&buf).contains('▀'));
}

#[test]
fn splash_minimal_en_pantalla_chica() {
    let buf = draw(40, 12, |f| {
        cortex_tui::splash::render(f, cortex_tui::env_color_mode())
    });
    assert_eq!(
        cortex_tui::branding_mode(buf.area),
        cortex_tui::BrandingMode::Minimal
    );
    // No panic y algo dibujado.
    assert!(symbols(&buf).contains('█') || symbols(&buf).contains('▀'));
}

#[test]
fn splash_no_explode_en_area_minima() {
    // 1×1: sin panic, sin escritura fuera (TestBackend clampea).
    let _ = draw(1, 1, |f| {
        cortex_tui::splash::render(f, cortex_tui::env_color_mode())
    });
    let _ = draw(10, 3, |f| {
        cortex_tui::splash::render(f, cortex_tui::env_color_mode())
    });
}

#[test]
fn home_renderiza_estado_demo() {
    let state = cortex_tui::home::demo_state();
    let buf = draw(80, 24, |f| cortex_tui::home::render(f, &state));
    let s = symbols(&buf);
    assert!(s.contains("Cortex"), "falta el título");
    assert!(
        s.contains("sesión") || s.contains("session"),
        "falta fila sesión"
    );
    assert!(s.contains("vault"), "falta fila vault");
    assert!(
        s.contains("q salir") || s.contains("q quit"),
        "faltan hints"
    );
    // Mark del header presente.
    assert!(s.contains('█'), "falta el mark del header");
}

#[test]
fn home_es_determinista() {
    let state = cortex_tui::home::demo_state();
    let a = draw(80, 24, |f| cortex_tui::home::render(f, &state));
    let b = draw(80, 24, |f| cortex_tui::home::render(f, &state));
    assert_eq!(a, b, "el render debe ser determinista");
}

#[test]
fn home_no_pinta_fuera_del_area() {
    // Widget de logo en un área chica dentro de un buffer grande: el resto
    // del buffer queda intacto.
    let mut buf = ratatui::buffer::Buffer::empty(ratatui::prelude::Rect::new(0, 0, 40, 20));
    let area = ratatui::prelude::Rect::new(5, 5, 10, 4);
    ratatui::widgets::Widget::render(
        cortex_tui::CortexLogo::new(cortex_tui::LogoVariant::Mark),
        area,
        &mut buf,
    );
    for y in 0..20 {
        for x in 0..40 {
            let inside = (5..15).contains(&x) && (5..9).contains(&y);
            if !inside {
                assert_eq!(
                    buf[(x, y)].symbol(),
                    " ",
                    "celda fuera del área modificada en ({x},{y})"
                );
            }
        }
    }
}

#[test]
fn home_render_bajo_presupuesto_50ms() {
    // Gate P10: snapshot render + latencia. Promedio de N renders < 50ms
    // (generoso por diseño: el Home es estático).
    let state = cortex_tui::home::demo_state();
    let n = 200;
    let t0 = std::time::Instant::now();
    for _ in 0..n {
        let _ = draw(80, 24, |f| cortex_tui::home::render(f, &state));
    }
    let avg = t0.elapsed() / n;
    assert!(
        avg.as_millis() < cortex_tui::home::RENDER_BUDGET_MS,
        "render promedio {avg:?} ≥ presupuesto {}ms",
        cortex_tui::home::RENDER_BUDGET_MS
    );
}

// ── snapshots del rediseño (spec §16.3) ────────────────────────────────────

const TS_A: &str = "2026-05-16T10:00:00+00:00";
const TS_B: &str = "2026-05-17T10:00:00+00:00";

fn now() -> DateTime<Utc> {
    DateTime::parse_from_rfc3339("2026-05-17T12:00:00+00:00")
        .unwrap()
        .with_timezone(&Utc)
}

fn data(n: usize) -> SessionsScreenData {
    SessionsScreenData {
        rows: (0..n)
            .map(|i| SessionRow {
                session_id: format!("2026-05-{i:02}_sesion"),
                status: if i % 5 == 4 {
                    "closed".into()
                } else {
                    "open".into()
                },
                mode: "managed".into(),
                opened_at: TS_A.into(),
                closed_at: if i % 5 == 4 { Some(TS_B.into()) } else { None },
                checkpoint_count: i % 3,
                spec_summary: format!("Spec de la sesión número {i}"),
            })
            .collect(),
        active_id: Some("2026-05-00_sesion".into()),
        now: now(),
        counts: Default::default(),
    }
}

fn draw_sessions(w: u16, h: u16, n: usize) -> String {
    let mut state = AppState::new("es", (w, h));
    reducer(&mut state, Action::SessionsLoaded(data(n)));
    let buf = draw(w, h, |f| cortex_tui::sessions::render(f, &state));
    symbols(&buf)
}

#[test]
fn sesiones_wide_160x45() {
    assert_eq!(
        cortex_tui::layout::layout_mode(ratatui::prelude::Rect::new(0, 0, 160, 45)),
        cortex_tui::layout::LayoutMode::Wide
    );
    let s = draw_sessions(160, 45, 12);
    assert!(s.contains("CORTEX") || s.contains('█'), "{s}");
    assert!(s.contains('●'), "marca activa ausente");
    assert!(s.contains('○'));
    assert!(
        s.contains("2026-05-11_sesion"),
        "falta id lejano: hay scroll"
    );
    assert!(s.contains("1/12"), "falta posición: {s}");
}

#[test]
fn sesiones_standard_100x30() {
    let s = draw_sessions(100, 30, 12);
    assert!(s.contains('●'));
    assert!(s.contains("2026-05-00_sesion"));
    assert!(s.contains("open"));
    assert!(s.contains("managed"));
}

#[test]
fn sesiones_compact_80x24() {
    let s = draw_sessions(80, 24, 12);
    assert!(s.contains('●'));
    assert!(s.contains("2026-05-00_sesion"));
    assert!(s.contains("sesiones"), "header: {s}");
}

#[test]
fn sesiones_minimo_68x20() {
    let s = draw_sessions(68, 20, 12);
    assert!(
        s.contains("2026-05-00_sesion"),
        "la lista debe verse en compact"
    );
}

#[test]
fn sesiones_minimal_40x12() {
    // Minimal: flujo vertical, sin bordes secundarios, datos visibles.
    let s = draw_sessions(40, 12, 3);
    assert!(
        s.contains("2026-05-00_sesion") || s.contains("sesion"),
        "{s}"
    );
}

#[test]
fn sesiones_too_small_estable() {
    let s = draw_sessions(30, 8, 3);
    assert!(s.contains("Terminal demasiado pequeña"), "{s}");
    assert!(s.contains("q salir"), "{s}");
}

#[test]
fn sesiones_vacias_estado_explicito() {
    let mut state = AppState::new("es", (80, 24));
    reducer(
        &mut state,
        Action::SessionsLoaded(SessionsScreenData {
            rows: vec![],
            active_id: None,
            now: now(),
            counts: Default::default(),
        }),
    );
    let buf = draw(80, 24, |f| cortex_tui::sessions::render(f, &state));
    let s = symbols(&buf);
    assert!(s.contains("(no sessions on disk)"), "{s}");
    assert!(s.contains("Abrí una con:"), "{s}");
}

#[test]
fn sesiones_failed_estado_explicito() {
    let mut state = AppState::new("es", (80, 24));
    reducer(&mut state, Action::SessionsFailed("storage roto".into()));
    let buf = draw(80, 24, |f| cortex_tui::sessions::render(f, &state));
    let s = symbols(&buf);
    assert!(s.contains("No se pudieron cargar"), "{s}");
    assert!(s.contains("storage roto"), "{s}");
    assert!(s.contains('×'), "glifo de error ausente");
}

#[test]
fn sesiones_loading_estado_explicito() {
    let mut state = AppState::new("es", (80, 24));
    state.sessions = LoadState::Loading;
    let buf = draw(80, 24, |f| cortex_tui::sessions::render(f, &state));
    let s = symbols(&buf);
    assert!(s.contains("Cargando sesiones"), "{s}");
}

#[test]
fn ayuda_se_abre_como_overlay() {
    let mut state = AppState::new("es", (80, 24));
    reducer(&mut state, Action::SessionsLoaded(data(2)));
    reducer(&mut state, Action::OpenHelp);
    let buf = draw(80, 24, |f| cortex_tui::sessions::render(f, &state));
    let s = symbols(&buf);
    assert!(s.contains("AYUDA") || s.contains("HELP"), "{s}");
    assert!(s.contains("j/k"), "{s}");
}

#[test]
fn render_determinista_del_mismo_snapshot() {
    let a = draw_sessions(100, 30, 12);
    let b = draw_sessions(100, 30, 12);
    assert_eq!(a, b);
}

#[test]
fn seleccion_mueve_la_barra_y_la_posicion() {
    let mut state = AppState::new("es", (100, 30));
    reducer(&mut state, Action::SessionsLoaded(data(12)));
    reducer(&mut state, Action::MoveDown);
    let buf = draw(100, 30, |f| cortex_tui::sessions::render(f, &state));
    let s = symbols(&buf);
    assert!(s.contains("2/12"), "posición 2/12: {s}");
}

// ── tiempos relativos (reloj inyectado) ────────────────────────────────────

#[test]
fn rel_time_vocabulario_acotado() {
    let now = now();
    assert_eq!(rel_time("2026-05-17T11:59:59+00:00", now, "en"), "just now");
    assert_eq!(rel_time("2026-05-17T11:59:30+00:00", now, "en"), "30s ago");
    let two_h = rel_time("2026-05-17T10:00:00+00:00", now, "en");
    assert!(two_h.starts_with("2h "), "{two_h}");
    let day = rel_time(TS_A, now, "en");
    assert!(day.starts_with("1d "), "{day}");
    // ES: mismo vocabulario, prefijo "hace".
    assert_eq!(rel_time("2026-05-17T11:59:30+00:00", now, "es"), "hace 30s");
}

#[test]
fn rel_time_timestamp_invalido_queda_crudo() {
    assert_eq!(rel_time("no-es-fecha", now(), "en"), "no-es-fecha");
}

// ── invariantes de tamaño (spec §16.4): sin panic en 1×1..200×80 ──────────

#[test]
fn ninguna_pantalla_explota_en_cualquier_tamano() {
    let widths = [
        1u16, 2, 5, 10, 20, 39, 40, 67, 68, 89, 90, 119, 120, 160, 200,
    ];
    let heights = [1u16, 2, 5, 8, 11, 12, 19, 20, 25, 26, 31, 32, 45, 60, 80];
    for w in widths {
        for h in heights {
            let _ = draw_sessions(w, h, 8); // no debe panic
        }
    }
}

#[test]
fn home_y_splash_sin_panic_en_tamano_minimo() {
    let state = cortex_tui::home::demo_state();
    for w in [1u16, 2, 5, 10, 20, 40, 80, 120] {
        for h in [1u16, 2, 5, 12, 20, 30] {
            let _ = draw(w, h, |f| cortex_tui::home::render(f, &state));
            let _ = draw(w, h, |f| {
                cortex_tui::splash::render(f, cortex_tui::ColorMode::Truecolor)
            });
        }
    }
}

/// El `now` del snapshot vive en los datos: un reloj distinto cambia solo
/// los tiempos relativos, nunca la estructura del render.
#[test]
fn reloj_distinto_no_afecta_estructura() {
    use chrono::TimeZone as _;
    let mut d = data(3);
    d.now = Utc.with_ymd_and_hms(2026, 5, 18, 0, 0, 0).unwrap();
    let mut state = AppState::new("es", (100, 30));
    reducer(&mut state, Action::SessionsLoaded(d));
    let buf = draw(100, 30, |f| cortex_tui::sessions::render(f, &state));
    let s = symbols(&buf);
    assert!(s.contains("2026-05-00_sesion"));
    assert!(s.contains('●'));
}
