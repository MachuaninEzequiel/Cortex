//! Pantalla SESIONES en ratatui (rediseño F2 — spec del agente externo
//! adaptada al repo).
//!
//! Contrato de DATOS (intacto, Gate CIERRE T6): la pantalla muestra
//! exactamente la misma información que `cortex session list --json`
//! (`_record_summary`): session_id, status, mode, opened_at, closed_at,
//! checkpoint_count y spec_summary — orden newest-first, con marca de
//! sesión activa. La serialización `SessionRow::to_json` no cambió.
//!
//! Lo NUEVO (diseño, spec §7/§9/§11): tema semántico (`Theme`), glifos de
//! estado (●/○/✓/!/×), tiempos relativos deterministas (reloj inyectado en
//! el snapshot), conteos por status en el header, estados explícitos
//! Loading / Failed / Empty / Ready, navegación j/k con posición. El loop
//! interactivo vive en `app::runtime` (el CLI solo arranca).

use crate::app::state::{AppState, LoadState, Overlay};
use crate::components::empty_state::EmptyState;
use crate::components::header::AppHeader;
use crate::components::list::SelectableList;
use crate::components::status_bar::StatusBar;
use crate::components::truncate_visual;
use crate::keymap::global_hints;
use crate::layout::{layout_mode, render_too_small, LayoutMode};
use crate::theme::{StatusKind, Theme};
use chrono::{DateTime, Utc};
use cortex_app::session::service::SessionService;
use cortex_app::session::SessionRecord;
use ratatui::prelude::{Constraint, Layout, Line, Rect, Span, Style};
use ratatui::Frame;

/// Presupuesto de render (mismo contrato que el Home: <50ms).
pub const RENDER_BUDGET_MS: u128 = 50;

/// Fila espejo exacto de `_record_summary` (cli/session.py) — el dict que
/// emite `session list --json`. NO MODIFICAR (paridad-como-contrato).
#[derive(Clone, Debug, PartialEq)]
pub struct SessionRow {
    pub session_id: String,
    pub status: String,
    pub mode: String,
    pub opened_at: String,
    pub closed_at: Option<String>,
    pub checkpoint_count: usize,
    pub spec_summary: String,
}

impl SessionRow {
    /// `_record_summary(record)`.
    pub fn from_record(r: &SessionRecord) -> Self {
        Self {
            session_id: r.session_id.clone(),
            status: r.status.as_str().to_string(),
            mode: mode_value(r.mode).to_string(),
            opened_at: r.opened_at.clone(),
            closed_at: r.closed_at.clone(),
            checkpoint_count: r.checkpoints.len(),
            spec_summary: r.spec_summary.clone(),
        }
    }

    /// Serialización idéntica a `json.dumps([...], ensure_ascii=False)` del
    /// comando `session list --json` (orden de claves = orden del dict).
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "session_id": self.session_id,
            "status": self.status,
            "mode": self.mode,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "checkpoint_count": self.checkpoint_count,
            "spec_summary": self.spec_summary,
        })
    }
}

fn mode_value(mode: cortex_app::session::SessionMode) -> &'static str {
    match mode {
        cortex_app::session::SessionMode::Unknown => "unknown",
        cortex_app::session::SessionMode::Managed => "managed",
        cortex_app::session::SessionMode::Observed => "observed",
        cortex_app::session::SessionMode::Byo => "byo",
        cortex_app::session::SessionMode::CiReview => "ci-review",
    }
}

/// Conteos por status (header de la pantalla).
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct SessionCounts {
    pub open: usize,
    pub closed: usize,
    pub handoff: usize,
    pub abandoned: usize,
}

impl SessionCounts {
    fn from_records(records: &[SessionRecord]) -> Self {
        let mut c = Self::default();
        for r in records {
            match r.status {
                cortex_app::session::SessionStatus::Open => c.open += 1,
                cortex_app::session::SessionStatus::Closed => c.closed += 1,
                cortex_app::session::SessionStatus::Handoff => c.handoff += 1,
                cortex_app::session::SessionStatus::Abandoned => c.abandoned += 1,
            }
        }
        c
    }
}

/// Snapshot inmutable de la pantalla (patrón heredado): el renderer es
/// función pura del snapshot, nunca toca storage. `now` es el reloj
/// CAPTURADO al construir el snapshot: los tiempos relativos son
/// deterministas entre renders del mismo snapshot (spec §16.3: reloj
/// inyectable/fijo).
#[derive(Clone, Debug, Default, PartialEq)]
pub struct SessionsScreenData {
    /// Newest-first (mismo sort que `list_command`).
    pub rows: Vec<SessionRow>,
    /// session_id activo (None ⇒ sin marca).
    pub active_id: Option<String>,
    /// Reloj del snapshot (Utc::now() en producción).
    pub now: DateTime<Utc>,
    /// Conteos por status para el header.
    pub counts: SessionCounts,
}

impl SessionsScreenData {
    /// Construcción desde el storage nativo con la semántica de
    /// `list_command`: filtra opcionalmente por status, ordena
    /// newest-first por `opened_at` y resuelve el activo.
    pub fn from_service(
        service: &SessionService,
        status_filter: Option<cortex_app::session::SessionStatus>,
    ) -> Result<Self, String> {
        let mut records = service.list(status_filter)?;
        let counts = SessionCounts::from_records(&records);
        records.sort_by(|a, b| b.opened_at.cmp(&a.opened_at));
        let rows = records.iter().map(SessionRow::from_record).collect();
        Ok(Self {
            active_id: service.get_active().map(|r| r.session_id),
            rows,
            now: Utc::now(),
            counts,
        })
    }
}

// ── tiempo relativo (port del oráculo `_format_relative`, bilingüe) ───────

/// "just now" · "12m ago" · "2h 14m ago" · "1d 4h ago" — vocabulario
/// acotado para que la columna nunca se ensanche.
pub fn rel_time(ts: &str, now: DateTime<Utc>, lang: &'static str) -> String {
    let Ok(dt) = DateTime::parse_from_rfc3339(ts) else {
        return ts.to_string();
    };
    let dt = dt.with_timezone(&Utc);
    let secs = (now - dt).num_seconds().max(0);
    let ago = |s: String| {
        if lang == "en" {
            format!("{s} ago")
        } else {
            format!("hace {s}")
        }
    };
    if secs < 5 {
        return if lang == "en" {
            "just now".into()
        } else {
            "justo ahora".into()
        };
    }
    if secs < 60 {
        return ago(format!("{secs}s"));
    }
    let (minutes, sec) = (secs / 60, secs % 60);
    if minutes < 60 {
        return ago(format!("{minutes}m {sec}s"));
    }
    let (hours, mm) = (minutes / 60, minutes % 60);
    if hours < 24 {
        return if mm > 0 {
            ago(format!("{hours}h {mm}m"))
        } else {
            ago(format!("{hours}h"))
        };
    }
    let (days, hh) = (hours / 24, hours % 24);
    if hh > 0 {
        ago(format!("{days}d {hh}h"))
    } else {
        ago(format!("{days}d"))
    }
}

// ── render puro ────────────────────────────────────────────────────────────

/// Opciones de render (selección/idioma/tema): el render sigue siendo
/// función pura `(state, opts) → frame`.
pub struct RenderOpts<'a> {
    pub selection: usize,
    pub offset: usize,
    pub theme: &'a Theme,
    pub lang: &'static str,
}

/// Render puro `state → frame` con los estados explícitos del rediseño.
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

    // Header: título + conteos por status a la derecha.
    let mut right: Vec<(StatusKind, String)> = Vec::new();
    let datos = match &state.sessions {
        LoadState::Ready(d) => Some(d),
        _ => None,
    };
    if let Some(d) = datos {
        let shown: Vec<(StatusKind, String)> = vec![
            (StatusKind::Active, format!("{} open", d.counts.open)),
            (StatusKind::Pending, format!("{} closed", d.counts.closed)),
            (StatusKind::Warning, format!("{} handoff", d.counts.handoff)),
            (
                StatusKind::Error,
                format!("{} abandoned", d.counts.abandoned),
            ),
        ];
        right = shown
            .into_iter()
            .filter(|(_, t)| !t.starts_with("0 "))
            .collect();
    }
    let title = if state.lang == "en" {
        "sessions"
    } else {
        "sesiones"
    };
    f.render_widget(
        AppHeader {
            title,
            right: &right,
            lang: state.lang,
            mode: state.mode,
        },
        header_area,
    );

    // Cuerpo: estados explícitos (spec §11.7).
    match &state.sessions {
        LoadState::Loading => {
            f.render_widget(
                EmptyState {
                    kind: StatusKind::Pending,
                    title: if state.lang == "en" {
                        "Loading sessions…"
                    } else {
                        "Cargando sesiones…"
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
            let short = truncate_visual(err, 60);
            let body = vec![short.as_str()];
            f.render_widget(
                EmptyState {
                    kind: StatusKind::Error,
                    title: if state.lang == "en" {
                        "Could not load sessions"
                    } else {
                        "No se pudieron cargar las sesiones"
                    },
                    body: &body,
                    hint: Some(if state.lang == "en" {
                        "retrying automatically · q quit"
                    } else {
                        "se reintenta automáticamente · q salir"
                    }),
                    theme: &theme,
                },
                body_area,
            );
        }
        LoadState::Ready(data) if data.rows.is_empty() => {
            // Mensaje CONTRACTUAL del gate T6 (no traducir).
            f.render_widget(
                EmptyState {
                    kind: StatusKind::Pending,
                    title: "(no sessions on disk)",
                    body: &[if state.lang == "en" {
                        "Open one with: cortex start"
                    } else {
                        "Abrí una con: cortex start"
                    }],
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
        LoadState::Ready(data) => {
            render_sessions_list(f, body_area, data, state, &theme);
        }
        LoadState::Idle => {}
    }

    // Status bar: hints prioritarios + posición + mensaje.
    let position = match &state.sessions {
        LoadState::Ready(d) if !d.rows.is_empty() => Some((state.selection + 1, d.rows.len())),
        _ => None,
    };
    let message = state.notifications.first();
    f.render_widget(
        StatusBar {
            hints: &global_hints(state.lang),
            position,
            message,
            theme: &theme,
        },
        status_area,
    );

    // Overlay de ayuda (spec §12: derivada del mapa, no texto hardcodeado).
    if state.overlay == Overlay::Help {
        crate::components::help::render_help(f, area, &theme, state.lang);
    }
}

fn render_sessions_list(
    f: &mut Frame<'_>,
    area: Rect,
    data: &SessionsScreenData,
    state: &AppState,
    theme: &Theme,
) {
    let opts = RenderOpts {
        selection: state.selection,
        offset: state.offset,
        theme,
        lang: state.lang,
    };
    let items = build_rows(data, &opts);
    f.render_widget(
        SelectableList {
            items: &items,
            selected: state.selection,
            offset: state.offset,
            theme,
        },
        area,
    );
}

fn build_rows(data: &SessionsScreenData, opts: &RenderOpts) -> Vec<Vec<Line<'static>>> {
    data.rows
        .iter()
        .enumerate()
        .map(|(i, row)| {
            let is_active = data.active_id.as_deref() == Some(row.session_id.as_str());
            let is_sel = i == opts.selection;
            // Fila seleccionada: estilo de selección completo (spec: el azul
            // identifica selección/actividad; la barra ▌ la pinta el list).
            let base = if is_sel {
                opts.theme.selected()
            } else {
                opts.theme.body()
            };
            let marker = if is_active { "●" } else { "○" };
            let marker_style: Style = if is_active {
                opts.theme.status_color(StatusKind::Active).into()
            } else {
                opts.theme.muted()
            };
            let status_color = opts.theme.status_color(status_kind(&row.status));
            let spans = vec![
                Span::styled(marker, marker_style),
                Span::styled(
                    format!(" {:<24}", truncate_visual(&row.session_id, 24)),
                    base,
                ),
                Span::styled(
                    format!(" {:<9}", truncate_visual(&row.status, 9)),
                    Style::default().fg(status_color),
                ),
                Span::styled(
                    format!(" {:<8}", truncate_visual(&row.mode, 8)),
                    opts.theme.muted(),
                ),
                Span::styled(format!(" {:>5}", row.checkpoint_count), base),
                Span::styled(
                    format!(" {:<11}", rel_time(&row.opened_at, data.now, opts.lang)),
                    opts.theme.muted(),
                ),
                Span::styled(
                    format!("  {}", truncate_visual(&row.spec_summary, 40)),
                    base,
                ),
            ];
            vec![Line::from(spans)]
        })
        .collect()
}

/// Color semántico por status (spec §7.1: verde/ámbar/rojo solo semántica;
/// la actividad es azul de marca).
fn status_kind(status: &str) -> StatusKind {
    match status {
        "open" => StatusKind::Active,
        "handoff" => StatusKind::Warning,
        "abandoned" => StatusKind::Error,
        _ => StatusKind::Pending, // closed
    }
}
