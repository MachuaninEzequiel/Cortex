//! Pantalla SESIONES en ratatui — reemplazo de la TUI rich vieja
//! (`cortex/cli/session_tui.py`, decisión doc 09 §3.8; Cierre Obra 07 T6).
//!
//! Contrato de DATOS: la pantalla muestra exactamente la misma información
//! que `cortex session list --json` (`_record_summary`): session_id,
//! status, mode, opened_at, closed_at, checkpoint_count y spec_summary —
//! orden newest-first, con marca de sesión activa. Paridad de datos, no de
//! estética rich.
//!
//! La fuente canónica es el SessionService nativo
//! (`cortex-app::session`) — los mismos records que alimenta al CLI.

use cortex_app::session::SessionRecord;
use ratatui::prelude::{Constraint, Layout};
use ratatui::widgets::{Block, Borders, Paragraph};
use ratatui::Frame;

/// Presupuesto de render (mismo contrato que el Home: <50ms).
pub const RENDER_BUDGET_MS: u128 = 50;

/// Fila espejo exacto de `_record_summary` (cli/session.py) — el dict que
/// emite `session list --json`.
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
        cortex_app::session::SessionMode::Composed => "composed",
        cortex_app::session::SessionMode::CiReview => "ci-review",
    }
}

/// Snapshot inmutable de la pantalla (patrón `SessionTuiState`: el renderer
/// es función pura del snapshot, nunca toca storage).
#[derive(Clone, Debug, Default)]
pub struct SessionsScreenData {
    /// Newest-first (mismo sort que `list_command`).
    pub rows: Vec<SessionRow>,
    /// session_id activo (None ⇒ sin marca).
    pub active_id: Option<String>,
}

impl SessionsScreenData {
    /// Construcción desde el storage nativo con la semántica de
    /// `list_command`: filtra opcionalmente por status, ordena
    /// newest-first por `opened_at` y resuelve el activo.
    pub fn from_service(
        service: &cortex_app::session::service::SessionService,
        status_filter: Option<cortex_app::session::SessionStatus>,
    ) -> Result<Self, String> {
        let mut records = service.list(status_filter)?;
        records.sort_by(|a, b| b.opened_at.cmp(&a.opened_at));
        let rows = records.iter().map(SessionRow::from_record).collect();
        Ok(Self {
            active_id: service.get_active().map(|r| r.session_id),
            rows,
        })
    }
}

/// Render puro `state → frame`. Read-only, sin input (contrato v1 de la
/// TUI rich heredado).
pub fn render(f: &mut Frame<'_>, data: &SessionsScreenData) {
    let chunks = Layout::vertical([Constraint::Length(1), Constraint::Min(1)]).split(f.area());

    let title = format!("cortex · sesiones · {} en disco", data.rows.len());
    f.render_widget(Paragraph::new(title), chunks[0]);

    if data.rows.is_empty() {
        f.render_widget(Paragraph::new("(no sessions on disk)"), chunks[1]);
        return;
    }

    // Tabla liviana: marca | ID | STATUS | MODE | CKPTS | summary.
    let mut lines: Vec<ratatui::prelude::Line<'static>> = Vec::new();
    lines.push(ratatui::prelude::Line::from(format!(
        "{:<1} {:<24} {:<9} {:<8} {:>5}  {}",
        "", "ID", "STATUS", "MODE", "CKPT", "SPEC SUMMARY"
    )));
    for row in &data.rows {
        let marker = if data.active_id.as_deref() == Some(row.session_id.as_str()) {
            "*"
        } else {
            ""
        };
        lines.push(ratatui::prelude::Line::from(format!(
            "{:<1} {:<24} {:<9} {:<8} {:>5}  {}",
            marker,
            row.session_id,
            row.status,
            row.mode,
            row.checkpoint_count,
            truncate(&row.spec_summary, 40),
        )));
    }
    f.render_widget(
        Paragraph::new(lines).block(Block::new().borders(Borders::TOP)),
        chunks[1],
    );
}

fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max {
        s.to_string()
    } else {
        s.chars().take(max).collect()
    }
}
