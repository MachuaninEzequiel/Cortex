//! Pantalla DETALLE DE SESIÓN (spec §11.4 adaptada al dominio real): la
//! sesión seleccionada con identidad, checkpoints, verificación y tareas —
//! datos reales del `SessionRecord` nativo. Read-only (el diff preview del
//! oráculo rich espera `compute_diff` nativo, aún no portado — anotado).
//!
//! Scroll vertical con `j/k`; el reducer no conoce el máximo de líneas: el
//! render clampea el offset al rango real (determinista, sin estado extra).

use crate::app::state::{AppState, LoadState};
use crate::components::empty_state::EmptyState;
use crate::components::header::AppHeader;
use crate::components::status_bar::StatusBar;
use crate::components::truncate_visual;
use crate::keymap::global_hints;
use crate::layout::{layout_mode, render_too_small, LayoutMode};
use crate::sessions::rel_time;
use crate::theme::{StatusKind, Theme};
use chrono::{DateTime, Utc};
use cortex_app::session::{SessionRecord, TaskStatus};
use ratatui::prelude::{Constraint, Layout, Line, Span, Style};
use ratatui::widgets::Paragraph;
use ratatui::Frame;

/// Fila de checkpoint para la TUI.
#[derive(Clone, Debug, PartialEq)]
pub struct CheckpointRow {
    pub timestamp: String,
    pub source: String,
    pub verified: usize,
    pub note: String,
}

/// Fila de verificación (hooks del spec).
#[derive(Clone, Debug, PartialEq)]
pub struct VerificationRow {
    pub name: String,
    pub passed: bool,
    pub duration_ms: u64,
}

/// Fila de tarea granular.
#[derive(Clone, Debug, PartialEq)]
pub struct TaskRow {
    pub id: String,
    pub status: String,
    pub description: String,
}

/// Snapshot del detalle (reloj inyectado para tiempos relativos
/// deterministas, spec §16.3).
#[derive(Clone, Debug, PartialEq)]
pub struct SessionDetailData {
    pub session_id: String,
    pub status: String,
    pub mode: String,
    pub spec_path: String,
    pub spec_summary: String,
    pub opened_at: String,
    pub closed_at: Option<String>,
    pub now: DateTime<Utc>,
    pub checkpoints: Vec<CheckpointRow>,
    pub verification: Vec<VerificationRow>,
    pub tasks: Vec<TaskRow>,
    /// Diff del port `compute_diff` (git start..end); vacío sin diff.
    pub diff_preview: String,
    /// Error de git contenido en el estado (el detalle sigue siendo útil).
    pub diff_error: Option<String>,
}

impl SessionDetailData {
    pub fn from_record(r: &SessionRecord) -> Self {
        Self {
            session_id: r.session_id.clone(),
            status: r.status.as_str().to_string(),
            mode: mode_str(r.mode),
            spec_path: r.spec_path.clone(),
            spec_summary: r.spec_summary.clone(),
            opened_at: r.opened_at.clone(),
            closed_at: r.closed_at.clone(),
            now: Utc::now(),
            checkpoints: r
                .checkpoints
                .iter()
                .rev() // newest-first, como el oráculo rich
                .map(|c| CheckpointRow {
                    timestamp: c.timestamp.clone(),
                    source: source_str(c.source),
                    verified: c.verified_claims.len(),
                    note: c.note.clone(),
                })
                .collect(),
            verification: r
                .verification_results
                .iter()
                .map(|v| VerificationRow {
                    name: v.name.clone(),
                    passed: v.passed,
                    duration_ms: v.duration_ms,
                })
                .collect(),
            tasks: r
                .tasks
                .iter()
                .map(|t| TaskRow {
                    id: t.id.clone(),
                    status: task_status_str(t.status),
                    description: t.description.clone(),
                })
                .collect(),
            diff_preview: String::new(),
            diff_error: None,
        }
    }
}

fn source_str(s: cortex_app::session::CheckpointSource) -> String {
    match s {
        cortex_app::session::CheckpointSource::CortexSync => "cortex-sync",
        cortex_app::session::CheckpointSource::CortexSddwork => "cortex-SDDwork",
        cortex_app::session::CheckpointSource::CortexCodeExplorer => "cortex-code-explorer",
        cortex_app::session::CheckpointSource::CortexCodeImplementer => "cortex-code-implementer",
        cortex_app::session::CheckpointSource::CortexCodeDesigner => "cortex-code-designer",
        cortex_app::session::CheckpointSource::UserSkill => "user-skill",
        cortex_app::session::CheckpointSource::IdeHook => "ide-hook",
        cortex_app::session::CheckpointSource::Manual => "manual",
        cortex_app::session::CheckpointSource::CiBot => "ci-bot",
    }
    .to_string()
}

fn mode_str(m: cortex_app::session::SessionMode) -> String {
    match m {
        cortex_app::session::SessionMode::Unknown => "unknown",
        cortex_app::session::SessionMode::Managed => "managed",
        cortex_app::session::SessionMode::Observed => "observed",
        cortex_app::session::SessionMode::Byo => "byo",
        cortex_app::session::SessionMode::CiReview => "ci-review",
        cortex_app::session::SessionMode::Composed => "composed",
    }
    .to_string()
}

fn task_status_str(s: TaskStatus) -> String {
    match s {
        TaskStatus::Pending => "pending",
        TaskStatus::InProgress => "in-progress",
        TaskStatus::Done => "done",
        TaskStatus::Skipped => "skipped",
        TaskStatus::Blocked => "blocked",
    }
    .to_string()
}

/// Render puro del detalle sobre el `AppState` compartido.
pub fn render(f: &mut Frame<'_>, state: &AppState) {
    let area = f.area();
    if layout_mode(area) == LayoutMode::TooSmall {
        render_too_small(f, state.lang);
        return;
    }
    let theme = Theme::new(crate::env_color_mode());

    let [header_area, body_area, status_area] = Layout::vertical([
        Constraint::Length(1),
        Constraint::Min(4),
        Constraint::Length(1),
    ])
    .areas(area);

    let right: Vec<(StatusKind, String)> = match &state.detail {
        LoadState::Ready(d) => vec![(detail_status_kind(&d.status), d.status.clone())],
        _ => vec![],
    };
    f.render_widget(
        AppHeader {
            title: if state.lang == "en" {
                "session detail"
            } else {
                "detalle de sesión"
            },
            right: &right,
            lang: state.lang,
            mode: state.mode,
        },
        header_area,
    );

    match &state.detail {
        LoadState::Loading | LoadState::Idle => {
            f.render_widget(
                EmptyState {
                    kind: StatusKind::Pending,
                    title: if state.lang == "en" {
                        "Loading session…"
                    } else {
                        "Cargando sesión…"
                    },
                    body: &[],
                    hint: Some(if state.lang == "en" {
                        "q quit"
                    } else {
                        "q salir"
                    }),
                    theme: &theme,
                },
                body_area,
            );
        }
        LoadState::Failed(err) => {
            let short = truncate_visual(err, 70);
            let body = vec![short.as_str()];
            f.render_widget(
                EmptyState {
                    kind: StatusKind::Error,
                    title: if state.lang == "en" {
                        "Could not load the session"
                    } else {
                        "No se pudo cargar la sesión"
                    },
                    body: &body,
                    hint: Some(if state.lang == "en" {
                        "b back · q quit"
                    } else {
                        "b volver · q salir"
                    }),
                    theme: &theme,
                },
                body_area,
            );
        }
        LoadState::Ready(d) => {
            let lines = build_lines(d, state.lang, &theme);
            let viewport = body_area.height.saturating_sub(1) as usize;
            let scroll = state
                .detail_scroll
                .min(lines.len().saturating_sub(viewport));
            let window: Vec<Line<'static>> =
                lines.iter().skip(scroll).take(viewport).cloned().collect();
            f.render_widget(Paragraph::new(window).block(theme.top_rule()), body_area);
        }
    }

    // Status bar: volver, scroll, salir + posición.
    let position = match &state.detail {
        LoadState::Ready(d) => {
            let total = build_lines(d, state.lang, &theme).len();
            let viewport = body_area.height.saturating_sub(1) as usize;
            if total > viewport {
                Some((state.detail_scroll + 1, total - viewport + 1))
            } else {
                None
            }
        }
        _ => None,
    };
    let mut hints = global_hints(state.lang);
    hints.insert(0, ("b", if state.lang == "en" { "back" } else { "volver" }));
    hints.insert(
        1,
        (
            "j/k",
            if state.lang == "en" {
                "scroll"
            } else {
                "desplazar"
            },
        ),
    );
    let message = state.notifications.first();
    f.render_widget(
        StatusBar {
            hints: &hints,
            position,
            message,
            theme: &theme,
        },
        status_area,
    );

    if state.overlay == crate::app::state::Overlay::Help {
        crate::components::help::render_help(f, area, &theme, state.lang);
    }
}

fn detail_status_kind(status: &str) -> StatusKind {
    match status {
        "open" => StatusKind::Active,
        "handoff" => StatusKind::Warning,
        "abandoned" => StatusKind::Error,
        _ => StatusKind::Pending,
    }
}

/// Todas las líneas del detalle (el render hace la ventana de scroll).
fn build_lines(d: &SessionDetailData, lang: &'static str, theme: &Theme) -> Vec<Line<'static>> {
    let mut out: Vec<Line<'static>> = Vec::new();

    // Identidad.
    out.push(Line::from(vec![
        Span::styled(truncate_visual(&d.session_id, 48), theme.title()),
        Span::styled(
            format!("  ·  {}", d.status),
            Style::default().fg(theme.status_color(detail_status_kind(&d.status))),
        ),
    ]));
    out.push(Line::from(vec![Span::styled(
        format!("spec   {}", truncate_visual(&d.spec_path, 60)),
        theme.muted(),
    )]));
    out.push(Line::from(vec![Span::styled(
        format!(
            "mode   {} · summary: {}",
            d.mode,
            truncate_visual(&d.spec_summary, 52)
        ),
        theme.body(),
    )]));
    let opened = rel_time(&d.opened_at, d.now, lang);
    let closed = d
        .closed_at
        .as_deref()
        .map(|c| rel_time(c, d.now, lang))
        .unwrap_or_else(|| "-".to_string());
    out.push(Line::from(vec![Span::styled(
        if lang == "en" {
            format!("opened {opened} · closed {closed}")
        } else {
            format!("abierta {opened} · cerrada {closed}")
        },
        theme.muted(),
    )]));
    out.push(Line::from(""));

    // Checkpoints (newest-first).
    let cp_title = format!("checkpoints ({})", d.checkpoints.len());
    out.push(Line::styled(cp_title, theme.subtitle()));
    if d.checkpoints.is_empty() {
        out.push(Line::styled(
            if lang == "en" {
                "(no checkpoints yet — the session advances with cortex checkpoint)"
            } else {
                "(sin checkpoints aún — la sesión avanza con cortex checkpoint)"
            },
            theme.muted(),
        ));
    } else {
        for cp in &d.checkpoints {
            let kind = if cp.verified > 0 {
                StatusKind::Success
            } else {
                StatusKind::Pending
            };
            out.push(Line::from(vec![
                Span::styled(
                    format!(
                        "{} {}  ",
                        kind.glyph(),
                        rel_time(&cp.timestamp, d.now, lang)
                    ),
                    Style::default().fg(theme.status_color(kind)),
                ),
                Span::styled(
                    format!("{:<22}", truncate_visual(&cp.source, 22)),
                    theme.muted(),
                ),
                Span::styled(truncate_visual(&cp.note, 44), theme.body()),
            ]));
        }
    }
    out.push(Line::from(""));

    // Verificación.
    let v_title = if lang == "en" {
        format!("verification ({})", d.verification.len())
    } else {
        format!("verificación ({})", d.verification.len())
    };
    out.push(Line::styled(v_title, theme.subtitle()));
    if d.verification.is_empty() {
        out.push(Line::styled(
            if lang == "en" {
                "(verification not yet run)"
            } else {
                "(verificación aún no corrida)"
            },
            theme.muted(),
        ));
    } else {
        for v in &d.verification {
            let kind = if v.passed {
                StatusKind::Success
            } else {
                StatusKind::Error
            };
            let dur = format_duration(v.duration_ms, lang);
            out.push(Line::from(vec![
                Span::styled(
                    format!("{} {} ", kind.glyph(), v.name),
                    Style::default().fg(theme.status_color(kind)),
                ),
                Span::styled(format!("({dur})"), theme.muted()),
            ]));
        }
    }
    out.push(Line::from(""));

    // Tareas granulares.
    let t_title = if lang == "en" {
        format!("tasks ({})", d.tasks.len())
    } else {
        format!("tareas ({})", d.tasks.len())
    };
    out.push(Line::styled(t_title, theme.subtitle()));
    if d.tasks.is_empty() {
        out.push(Line::styled(
            if lang == "en" {
                "(no granular tasks)"
            } else {
                "(sin tareas granulares)"
            },
            theme.muted(),
        ));
    } else {
        for t in &d.tasks {
            let kind = task_kind(&t.status);
            out.push(Line::from(vec![
                Span::styled(
                    format!("{} ", kind.glyph()),
                    Style::default().fg(theme.status_color(kind)),
                ),
                Span::styled(format!("{:<10}", t.id), theme.muted()),
                Span::styled(truncate_visual(&t.description, 44), theme.body()),
            ]));
        }
    }
    out.push(Line::from(""));

    // Diff (port nativo del oráculo rich `_render_diff_panel`: primeras 8
    // líneas con color +/-/@@ y footer de líneas truncadas).
    out.push(Line::styled("diff", theme.subtitle()));
    if let Some(e) = &d.diff_error {
        out.push(Line::styled(
            format!(
                "({})",
                if lang == "en" {
                    format!("diff unavailable: {e}")
                } else {
                    format!("diff no disponible: {e}")
                }
            ),
            theme.muted(),
        ));
    } else if d.diff_preview.is_empty() {
        out.push(Line::styled(
            if lang == "en" {
                "(no diff — start_commit equals end_ref)"
            } else {
                "(sin diff — start_commit equivale a end_ref)"
            },
            theme.muted(),
        ));
    } else {
        let raw: Vec<&str> = d.diff_preview.lines().collect();
        let visible = raw.iter().take(8);
        for line in visible {
            let style = if line.starts_with("+++") || line.starts_with("---") {
                theme.shortcut_label()
            } else if line.starts_with('+') {
                Style::default().fg(theme.success)
            } else if line.starts_with('-') {
                Style::default().fg(theme.error)
            } else if line.starts_with("@@") {
                theme.shortcut_key()
            } else {
                theme.muted()
            };
            out.push(Line::styled(truncate_visual(line, 76), style));
        }
        let extra = raw.len().saturating_sub(8);
        if extra > 0 {
            out.push(Line::styled(
                format!(
                    "({} {})",
                    extra,
                    if lang == "en" {
                        "more lines"
                    } else {
                        "líneas más"
                    }
                ),
                theme.muted(),
            ));
        }
    }
    out
}

fn task_kind(status: &str) -> StatusKind {
    match status {
        "done" => StatusKind::Success,
        "in-progress" => StatusKind::Active,
        "blocked" => StatusKind::Warning,
        "skipped" => StatusKind::Pending,
        _ => StatusKind::Pending,
    }
}

/// `824ms` / `5.2s` / `2m 4s` (mismo vocabulario que el oráculo rich).
fn format_duration(ms: u64, lang: &'static str) -> String {
    let _ = lang;
    if ms < 1000 {
        format!("{ms}ms")
    } else {
        let secs = ms as f64 / 1000.0;
        if secs < 60.0 {
            format!("{secs:.1}s")
        } else {
            let m = secs as u64 / 60;
            let r = secs as u64 % 60;
            format!("{m}m {r}s")
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::theme::Theme;
    use cortex_branding::ansi::ColorMode;

    fn data() -> SessionDetailData {
        SessionDetailData {
            session_id: "2026-05-17_demo".into(),
            status: "open".into(),
            mode: "managed".into(),
            spec_path: "vault/specs/2026-05-17_demo.md".into(),
            spec_summary: "Implementar el flujo de sesiones end-to-end.".into(),
            opened_at: "2026-05-17T10:00:00+00:00".into(),
            closed_at: None,
            now: DateTime::parse_from_rfc3339("2026-05-17T12:00:00+00:00")
                .unwrap()
                .with_timezone(&Utc),
            checkpoints: vec![CheckpointRow {
                timestamp: "2026-05-17T11:00:00+00:00".into(),
                source: "manual".into(),
                verified: 1,
                note: "checkpoint inicial".into(),
            }],
            verification: vec![],
            tasks: vec![TaskRow {
                id: "T1".into(),
                status: "pending".into(),
                description: "primer tarea".into(),
            }],
            diff_preview: "+linea nueva\n- linea vieja".into(),
            diff_error: None,
        }
    }

    #[test]
    fn build_lines_cubre_secciones() {
        let theme = Theme::new(ColorMode::Plain);
        let lines = build_lines(&data(), "es", &theme);
        let text: String = lines
            .iter()
            .map(|l| {
                l.spans
                    .iter()
                    .map(|s| s.content.as_ref())
                    .collect::<String>()
            })
            .collect::<Vec<_>>()
            .join("\n");
        assert!(text.contains("2026-05-17_demo"));
        assert!(text.contains("checkpoints (1)"));
        assert!(text.contains("verificación (0)"));
        assert!(text.contains("tareas (1)"));
        assert!(text.contains("T1"));
        // Sección diff: preview con estilo de símbolos y footer.
        assert!(text.contains("diff"));
        assert!(text.contains("+linea nueva"));
        assert!(text.contains("- linea vieja"));
    }

    #[test]
    fn diff_error_se_muestra_sin_romper_el_detalle() {
        let mut d = data();
        d.diff_preview = String::new();
        d.diff_error = Some("repo sin git".into());
        let theme = Theme::new(ColorMode::Plain);
        let lines = build_lines(&d, "es", &theme);
        let text: String = lines
            .iter()
            .map(|l| {
                l.spans
                    .iter()
                    .map(|s| s.content.as_ref())
                    .collect::<String>()
            })
            .collect::<Vec<_>>()
            .join("\n");
        assert!(text.contains("diff no disponible: repo sin git"), "{text}");
    }

    #[test]
    fn diff_largo_se_trunca_con_footer() {
        let mut d = data();
        d.diff_preview = (0..20)
            .map(|i| format!("+línea {i}"))
            .collect::<Vec<_>>()
            .join("\n");
        let theme = Theme::new(ColorMode::Plain);
        let lines = build_lines(&d, "es", &theme);
        let text: String = lines
            .iter()
            .map(|l| {
                l.spans
                    .iter()
                    .map(|s| s.content.as_ref())
                    .collect::<String>()
            })
            .collect::<Vec<_>>()
            .join("\n");
        assert!(text.contains("12 líneas más"), "{text}");
        assert!(text.contains("+línea 0"));
        assert!(!text.contains("+línea 15"));
    }

    #[test]
    fn duracion_formateada() {
        assert_eq!(format_duration(824, "es"), "824ms");
        assert_eq!(format_duration(5200, "es"), "5.2s");
        assert_eq!(format_duration(124_000, "es"), "2m 4s");
    }
}
