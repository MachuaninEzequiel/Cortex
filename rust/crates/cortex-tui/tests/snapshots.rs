//! Snapshots de render con TestBackend (prompt-logo.md §45): Full/Compact/
//! Minimal sin panic, sin escritura fuera del área, variante correcta según
//! breakpoint, determinismo y gate de latencia del Home (<50ms).

use cortex_tui::{branding_mode, home, BrandingMode};
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

#[test]
fn splash_full_en_pantalla_grande() {
    let buf = draw(100, 30, |f| {
        cortex_tui::splash::render(f, cortex_tui::env_color_mode())
    });
    assert_eq!(branding_mode(buf.area), BrandingMode::Full);
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
    assert_eq!(branding_mode(buf.area), BrandingMode::Compact);
    assert!(symbols(&buf).contains('▀'));
}

#[test]
fn splash_minimal_en_pantalla_chica() {
    let buf = draw(40, 12, |f| {
        cortex_tui::splash::render(f, cortex_tui::env_color_mode())
    });
    assert_eq!(branding_mode(buf.area), BrandingMode::Minimal);
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
    let state = home::demo_state();
    let buf = draw(80, 24, |f| home::render(f, &state));
    let s = symbols(&buf);
    assert!(s.contains("Cortex"), "falta el título");
    assert!(
        s.contains("sesión") || s.contains("session"),
        "falta fila sesión"
    );
    assert!(s.contains("vault"), "falta fila vault");
    assert!(
        s.contains("q=salir") || s.contains("q=quit"),
        "faltan hints"
    );
    // Mark del header presente.
    assert!(s.contains('█'), "falta el mark del header");
}

#[test]
fn home_es_determinista() {
    let state = home::demo_state();
    let a = draw(80, 24, |f| home::render(f, &state));
    let b = draw(80, 24, |f| home::render(f, &state));
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
    let state = home::demo_state();
    let n = 200;
    let t0 = std::time::Instant::now();
    for _ in 0..n {
        let _ = draw(80, 24, |f| home::render(f, &state));
    }
    let avg = t0.elapsed() / n;
    assert!(
        avg.as_millis() < home::RENDER_BUDGET_MS,
        "render promedio {avg:?} ≥ presupuesto {}ms",
        home::RENDER_BUDGET_MS
    );
}
