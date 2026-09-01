//! Pantalla ACCIONES (rediseño — reemplaza `render_actions_screen` del
//! oráculo rich, doc 05 §3.5): propuestas del ActionEngine nativo con
//! revisión previa (spec §11.5) y ejecución vía el runner del motor.
//!
//! Regla del repo: la TUI ORQUESTA el motor, no duplica lógica. El
//! pipeline es EXACTAMENTE el de `cortex next` (ActionContext → registry →
//! PreferencesStore → Scheduler::propose); la ejecución usa `Runner` con
//! su contrato duro (irreversible ⇒ approved explícito, action_log en
//! cada ejecución, dry-run nativo).

use crate::app::state::{AppState, LoadState, Overlay};
use crate::components::empty_state::EmptyState;
use crate::components::header::AppHeader;
use crate::components::help::render_help;
use crate::components::panel::draw_panel;
use crate::components::status_bar::StatusBar;
use crate::components::truncate_visual;
use crate::keymap::global_hints;
use crate::layout::{layout_mode, render_too_small, LayoutMode};
use crate::theme::{StatusKind, Theme};
use cortex_actions::catalog::build_default_registry;
use cortex_actions::context::ActionContext;
use cortex_actions::scheduler::Scheduler;
use cortex_actions::store::PreferencesStore;
use ratatui::prelude::{Constraint, Layout, Line, Rect, Span, Style};
use ratatui::widgets::Paragraph;
use ratatui::Frame;
use std::path::Path;

/// Presupuesto de render (mismo contrato que las demás pantallas: <50ms).
pub const RENDER_BUDGET_MS: u128 = 50;

/// Vista de una propuesta para la TUI (datos del `next --json` + razones).
#[derive(Clone, Debug, PartialEq)]
pub struct ActionView {
    pub id: String,
    pub title: String,
    pub category: String,
    pub effect: String,
    pub cost: String,
    pub reversible: bool,
    pub auto_ok: bool,
    pub score: f64,
}

/// Snapshot de la pantalla ACCIONES (espejo del snapshot de sesiones:
/// render puro sobre datos inmutables).
#[derive(Clone, Debug, Default, PartialEq)]
pub struct ActionsData {
    pub proposals: Vec<ActionView>,
}

/// Evalúa el motor con el MISMO pipeline que `cortex next` (sin duplicar):
/// sin config → error con el mensaje canónico del comando.
pub fn propose(ctx: &ActionContext, all: bool) -> Result<ActionsData, String> {
    if !ctx.config_existe() {
        return Err(format!(
            "Cortex no está configurado en {} (no encuentro config.yaml) — corré \
             `cortex setup agent` primero.",
            ctx.workspace_root.display()
        ));
    }
    let registry = build_default_registry(ctx);
    let prefs = PreferencesStore::new(&ctx.dot_cortex());
    let scheduler = Scheduler::new(&prefs);
    let propuestas = scheduler.propose(&registry, all);
    let proposals = propuestas
        .iter()
        .filter_map(|p| {
            let a = registry.get(&p.action_id)?;
            Some(ActionView {
                id: a.id.clone(),
                title: a.title.clone(),
                category: a.category.as_str().to_string(),
                effect: a.effect.clone(),
                cost: a.cost.as_str().to_string(),
                reversible: a.reversible,
                auto_ok: a.auto_ok,
                score: p.score,
            })
        })
        .collect();
    Ok(ActionsData { proposals })
}

/// Construye el contexto de acciones desde la raíz (misma firma que next).
pub fn context(project_root: Option<&Path>) -> ActionContext {
    ActionContext::from_project_root(project_root)
}

// ── render puro ────────────────────────────────────────────────────────────

/// Render puro de la pantalla ACCIONES sobre el `AppState` compartido.
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

    let right: Vec<(StatusKind, String)> = match &state.actions {
        LoadState::Ready(d) if !d.proposals.is_empty() => {
            vec![(
                StatusKind::Active,
                format!(
                    "{} {}",
                    d.proposals.len(),
                    if state.lang == "en" {
                        "suggested"
                    } else {
                        "sugeridas"
                    }
                ),
            )]
        }
        _ => vec![],
    };
    f.render_widget(
        AppHeader {
            title: if state.lang == "en" {
                "actions"
            } else {
                "acciones"
            },
            right: &right,
            lang: state.lang,
            mode: state.mode,
        },
        header_area,
    );

    match &state.actions {
        LoadState::Loading => {
            f.render_widget(
                EmptyState {
                    kind: StatusKind::Pending,
                    title: if state.lang == "en" {
                        "Evaluating actions…"
                    } else {
                        "Evaluando acciones…"
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
                        "Could not evaluate actions"
                    } else {
                        "No se pudieron evaluar las acciones"
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
        LoadState::Ready(d) if d.proposals.is_empty() => {
            f.render_widget(
                EmptyState {
                    kind: StatusKind::Success,
                    title: if state.lang == "en" {
                        "Nothing pending — your workspace is up to date"
                    } else {
                        "Nada pendiente — tu workspace está al día"
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
        LoadState::Ready(d) => render_proposals(f, body_area, d, state, &theme),
        LoadState::Idle => {}
    }

    let position = match &state.actions {
        LoadState::Ready(d) if !d.proposals.is_empty() => {
            Some((state.selection + 1, d.proposals.len()))
        }
        _ => None,
    };
    // Spinner vivo mientras una acción está ejecutándose (spec §6.1: toda
    // operación larga transmite actividad; el frame depende del tick del
    // estado ⇒ determinista en snapshots).
    let spinner_msg = match state.actions_front() {
        Some(idx) => {
            let frame = crate::app::runtime::SPINNER
                [state.tick as usize % crate::app::runtime::SPINNER.len()];
            let title = match &state.actions {
                LoadState::Ready(d) => d
                    .proposals
                    .get(idx)
                    .map(|p| p.title.clone())
                    .unwrap_or_default(),
                _ => String::new(),
            };
            Some(crate::app::state::Notification {
                text: format!(
                    "{frame} {}",
                    if state.lang == "en" {
                        format!("executing: {title}…")
                    } else {
                        format!("ejecutando: {title}…")
                    }
                ),
                kind: StatusKind::Pending,
                expires_at_tick: 0,
            })
        }
        None => None,
    };
    let message = spinner_msg.as_ref().or(state.notifications.first());
    f.render_widget(
        StatusBar {
            hints: &actions_hints(state.lang),
            position,
            message,
            theme: &theme,
        },
        status_area,
    );

    if state.overlay == Overlay::Help {
        render_help(f, area, &theme, state.lang);
    }
    if let Overlay::Confirm { index, armed } = state.overlay {
        render_confirm(f, area, index, armed, state, &theme);
    }
    if let Overlay::ConfirmBatch { count, armed } = state.overlay {
        render_confirm_batch(f, area, count, armed, state, &theme);
    }
}

/// Revisión del lote auto-ok (doc 05 §3.5): se ejecutan N acciones
/// reversibles e instantáneas con UN Enter (el contrato del motor no
/// permite auto_ok irreversible).
fn render_confirm_batch(
    f: &mut Frame<'_>,
    area: Rect,
    count: usize,
    _armed: bool,
    state: &AppState,
    theme: &Theme,
) {
    let mw = (area.width * 7 / 10).clamp(48, 72);
    let mh = 12u16;
    let mx = area.x + (area.width - mw) / 2;
    let my = area.y + (area.height - mh) / 2;
    let m_area = Rect::new(mx, my, mw, mh);
    let inner = draw_panel(
        m_area,
        if state.lang == "en" {
            "RUN AUTO-OK BATCH"
        } else {
            "EJECUTAR LOTE AUTO-OK"
        },
        true,
        theme,
        f.buffer_mut(),
    );
    let title = if state.lang == "en" {
        format!("{count} suggested actions marked auto-ok")
    } else {
        format!("{count} acciones sugeridas marcadas auto-ok")
    };
    let mut lines: Vec<Line<'static>> = vec![Line::from(vec![Span::styled(title, theme.title())])];
    lines.push(Line::from(""));
    lines.push(Line::from(vec![Span::styled(
        if state.lang == "en" {
            "All of them are reversible and instant (engine contract)."
        } else {
            "Todas son reversibles e instantáneas (contrato del motor)."
        },
        theme.body(),
    )]));
    lines.push(Line::from(""));
    lines.push(Line::from(vec![
        Span::styled(
            if state.lang == "en" {
                "Enter apply"
            } else {
                "Enter aplicar"
            },
            theme.shortcut_key(),
        ),
        Span::styled(" · ", theme.muted()),
        Span::styled(
            if state.lang == "en" {
                "Esc back"
            } else {
                "Esc volver"
            },
            theme.shortcut_key(),
        ),
    ]));
    f.render_widget(Paragraph::new(lines), inner);
}

fn actions_hints(lang: &'static str) -> Vec<(&'static str, &'static str)> {
    let mut h = global_hints(lang);
    h.insert(
        0,
        ("Enter", if lang == "en" { "review" } else { "revisar" }),
    );
    h
}

fn render_proposals(
    f: &mut Frame<'_>,
    area: Rect,
    data: &ActionsData,
    state: &AppState,
    theme: &Theme,
) {
    let inner = draw_panel(
        area,
        &format!(
            "cortex · {} {}",
            data.proposals.len(),
            if state.lang == "en" {
                "suggested"
            } else {
                "sugeridas"
            }
        ),
        true,
        theme,
        f.buffer_mut(),
    );
    let mut items: Vec<Vec<Line<'static>>> = Vec::new();
    for (i, p) in data.proposals.iter().enumerate() {
        let is_sel = i == state.selection;
        let base = if is_sel {
            theme.selected()
        } else {
            theme.body()
        };
        let mut l1 = vec![
            Span::styled(format!("[{}] ", i + 1), theme.shortcut_key()),
            Span::styled(p.title.clone(), base),
        ];
        if p.auto_ok {
            l1.push(Span::styled("  [auto-ok]", theme.accent_soft));
        }
        items.push(vec![
            Line::from(l1),
            Line::from(vec![
                Span::styled(
                    format!(
                        "  {} · {} · {}",
                        p.id,
                        p.cost,
                        if p.reversible {
                            "reversible"
                        } else {
                            "irreversible"
                        }
                    ),
                    theme.muted(),
                ),
                Span::styled(format!(" · score {}", p.score), theme.muted()),
                Span::styled(
                    format!("  {}", truncate_visual(&p.effect, 52)),
                    theme.subtitle(),
                ),
            ]),
        ]);
    }
    let list = crate::components::list::SelectableList {
        items: &items,
        selected: state.selection,
        offset: state.offset,
        theme,
    };
    f.render_widget(list, inner);
}

/// Revisión previa (spec §11.5): intención, consecuencias, advertencia de
/// irreversibilidad, acción primaria inequívoca y opción segura por defecto.
fn render_confirm(
    f: &mut Frame<'_>,
    area: Rect,
    index: usize,
    armed: bool,
    state: &AppState,
    theme: &Theme,
) {
    let Some(p) = (match &state.actions {
        LoadState::Ready(d) => d.proposals.get(index),
        _ => None,
    }) else {
        return;
    };
    // Modal centrado, ancho acotado al 70% (spec §13: focus trap, nunca
    // compite con el contenido operativo).
    let critical = !p.reversible;
    // Modal centrado, ancho acotado (spec §13): nunca compite con el
    // contenido operativo.
    let mw = (area.width * 7 / 10).clamp(48, 72);
    let mh = (area.height * 3 / 5).clamp(10, 18);
    let mx = area.x + (area.width - mw) / 2;
    let my = area.y + (area.height - mh) / 2;
    let m_area = Rect::new(mx, my, mw, mh);
    let inner = draw_panel(
        m_area,
        if armed {
            if state.lang == "en" {
                "CONFIRM EXECUTION"
            } else {
                "CONFIRMAR EJECUCIÓN"
            }
        } else if state.lang == "en" {
            "RUN ACTION"
        } else {
            "EJECUTAR ACCIÓN"
        },
        true,
        theme,
        f.buffer_mut(),
    );
    let mut lines: Vec<Line<'static>> = vec![Line::from(vec![Span::styled(
        p.title.clone(),
        theme.title(),
    )])];
    lines.push(Line::from(vec![
        Span::styled(format!("{} · costo: {} · ", p.id, p.cost), theme.muted()),
        Span::styled(
            if p.reversible {
                "reversible"
            } else {
                "irreversible"
            },
            if critical {
                Style::default().fg(theme.warning)
            } else {
                theme.muted()
            },
        ),
    ]));
    lines.push(Line::from(""));
    lines.push(Line::from(vec![
        Span::styled(
            if state.lang == "en" {
                "Effect: "
            } else {
                "Efecto: "
            },
            theme.shortcut_key(),
        ),
        Span::styled(p.effect.clone(), theme.body()),
    ]));
    if critical {
        lines.push(Line::from(""));
        lines.push(Line::from(vec![Span::styled(
            format!(
                "! {}",
                if state.lang == "en" {
                    "This action is IRREVERSIBLE — it cannot be undone."
                } else {
                    "Esta acción es IRREVERSIBLE — no se puede deshacer."
                }
            ),
            Style::default()
                .fg(theme.warning)
                .add_modifier(ratatui::prelude::Modifier::BOLD),
        )]));
    }
    if armed {
        lines.push(Line::from(""));
        lines.push(Line::from(Span::styled(
            if state.lang == "en" {
                "Enter again to confirm definitively."
            } else {
                "Enter de nuevo para confirmar definitivamente."
            },
            theme.warning,
        )));
    }
    lines.push(Line::from(""));
    lines.push(Line::from(vec![
        Span::styled(
            if state.lang == "en" {
                "Enter apply"
            } else {
                "Enter aplicar"
            },
            theme.shortcut_key(),
        ),
        Span::styled(if critical { " (×2) · " } else { " · " }, theme.muted()),
        Span::styled(
            if state.lang == "en" {
                "Esc back"
            } else {
                "Esc volver"
            },
            theme.shortcut_key(),
        ),
    ]));
    f.render_widget(Paragraph::new(lines), inner);
}
