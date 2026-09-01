//! Renderizado modular y funciones de vista (spec §2 / §4 / §5).
//!
//! Todas las vistas son funciones puras que reciben `&AppState` y `&Theme`,
//! garantizando testeabilidad con `TestBackend` sin efectos colaterales.

use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::prelude::{Frame, Line, Modifier, Span, Style};
use ratatui::widgets::{Block, BorderType, Clear, List, ListItem, Paragraph, Wrap};

use crate::app::{AppState, LoadState, Overlay, Screen};
use crate::theme::Theme;

/// Función principal de dibujo de la TUI.
pub fn draw(frame: &mut Frame<'_>, state: &AppState, theme: &Theme) {
    let area = frame.area();
    if area.width < 20 || area.height < 6 {
        let warn = Paragraph::new("Terminal demasiado pequeña")
            .style(Style::default().fg(theme.error));
        frame.render_widget(warn, area);
        return;
    }

    // Geometría compartida con el hit-test del mouse (`crate::hit`).
    let chunks = crate::hit::root_chunks(area);
    let chunks = &*chunks;

    draw_header(frame, chunks[0], state, theme);

    match state.screen {
        Screen::Home => draw_home(frame, chunks[1], state, theme),
        Screen::Sessions => draw_sessions(frame, chunks[1], state, theme),
        Screen::SessionDetail => draw_session_detail(frame, chunks[1], state, theme),
        Screen::Actions => draw_actions(frame, chunks[1], state, theme),
        Screen::Search => draw_search(frame, chunks[1], state, theme),
    }

    draw_status_bar(frame, chunks[2], state, theme);

    if state.overlay != Overlay::None {
        draw_overlay(frame, area, state, theme);
    }
}

/// Header superior compacto y elegante con información de contexto.
pub fn draw_header(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme) {
    let project = match &state.home {
        LoadState::Ready(h) => h.proyecto.as_str(),
        _ => "Cortex",
    };
    let branch = match &state.home {
        LoadState::Ready(h) => h.rama.as_deref().unwrap_or("main"),
        _ => "main",
    };
    let active_session = match &state.home {
        LoadState::Ready(h) => h.sesion_line.as_deref().unwrap_or("sin sesión"),
        _ => "-",
    };

    let title_spans = vec![
        Span::styled("◈ CORTEX ", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)),
        Span::styled("· ", Style::default().fg(theme.muted)),
        Span::styled(format!("⌗ {project} "), Style::default().fg(theme.text)),
        Span::styled(format!("⎇ {branch} "), Style::default().fg(theme.text_muted)),
        Span::styled("· ", Style::default().fg(theme.muted)),
        Span::styled(format!("● {active_session} "), Style::default().fg(theme.success)),
    ];

    let block = Block::bordered()
        .border_type(BorderType::Rounded)
        .border_style(theme.border(false))
        .style(Style::default().bg(theme.bg));

    let paragraph = Paragraph::new(Line::from(title_spans))
        .block(block);

    frame.render_widget(paragraph, area);
}

/// Pantalla principal Home / Dashboard.
pub fn draw_home(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme) {
    // Geometría compartida con el hit-test (`crate::hit`): si el área es menor
    // de lo que pide el wordmark (p. ej. sidecar angosto), se omite la bandera
    // y se da todo el alto al contenido, en vez de partir el logo.
    let bands = crate::hit::home_bands(area);
    if bands.banner.height > 0 {
        draw_3d_wordmark(frame.buffer_mut(), bands.banner, theme);
    }
    let cols = crate::hit::home_cols_outer(area);

    // Columna Izquierda: Estado del Proyecto y Memoria
    let (vault_info, actions_info, doctor_ok) = match &state.home {
        LoadState::Ready(h) => (
            format!("{} notas", h.vault_notas),
            format!("{} pendientes", h.acciones_pendientes),
            h.doctor_items.iter().all(|(_, s)| s == "ok"),
        ),
        _ => ("-".into(), "-".into(), true),
    };

    let status_glyph = if doctor_ok { "✓" } else { "!" };
    let status_color = if doctor_ok { theme.success } else { theme.warning };

    // Atajos rápidos: botones clickeables (misma geometría que `hit`).
    let mut atajos_spans =
        vec![Span::styled(crate::hit::HOME_ATAJOS_PREFIX, Style::default().fg(theme.text_muted))];
    for (i, (cell, s)) in crate::hit::home_shortcut_cells(area).iter().enumerate() {
        if i > 0 {
            atajos_spans.push(Span::styled(
                crate::hit::HOME_SHORTCUT_SEP,
                Style::default().fg(theme.muted),
            ));
        }
        let style = if crate::hit::hovered(state, *cell) {
            Style::default().fg(theme.bg).bg(theme.accent).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.accent)
        };
        atajos_spans.push(Span::styled(crate::hit::home_shortcut_text(s), style));
    }

    let left_text = vec![
        Line::from(vec![
            Span::styled("Salud de gobernanza: ", Style::default().fg(theme.text_muted)),
            Span::styled(format!("{status_glyph} OK"), Style::default().fg(status_color).add_modifier(Modifier::BOLD)),
        ]),
        Line::from(""),
        Line::from(vec![
            Span::styled("Vault de conocimiento: ", Style::default().fg(theme.text_muted)),
            Span::styled(vault_info, Style::default().fg(theme.text)),
        ]),
        Line::from(vec![
            Span::styled("Acciones del Action Engine: ", Style::default().fg(theme.text_muted)),
            Span::styled(actions_info, Style::default().fg(theme.accent_soft)),
        ]),
        Line::from(""),
        Line::from(atajos_spans),
    ];

    let left_block = Block::bordered()
        .border_type(BorderType::Rounded)
        .border_style(theme.border(true))
        .title(" ▦ Estado del Workspace ")
        .title_style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));

    frame.render_widget(Paragraph::new(left_text).block(left_block), cols.0);

    // Columna Derecha: Pipeline & SDDwork Agents
    draw_sddwork(frame, cols.1, state, theme);
}

/// Panel de SDDwork y Agentes de Cortex (spec §2: designer, explorer, implementer, security-auditor, test-verifier, documenter).
pub fn draw_sddwork(frame: &mut Frame<'_>, area: Rect, _state: &AppState, theme: &Theme) {
    let agents = [
        ("Designer", "✓ Spec & Goals validados", theme.success),
        ("Explorer", "● Mapeo de codebase activo", theme.accent),
        ("Implementer", "● Vertical slices en curso", theme.accent),
        ("Security Auditor", "○ En espera de commit", theme.muted),
        ("Test Verifier", "○ En espera de gate", theme.muted),
        ("Documenter", "○ En espera de cierre", theme.muted),
    ];

    let mut lines = Vec::new();
    for (name, status, color) in agents {
        lines.push(Line::from(vec![
            Span::styled(format!("{:<18}", name), Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
            Span::styled(status, Style::default().fg(color)),
        ]));
    }

    let block = Block::bordered()
        .border_type(BorderType::Rounded)
        .border_style(theme.border(false))
        .title(" ⌬ Agentes SDDwork ")
        .title_style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));

    frame.render_widget(Paragraph::new(lines).block(block), area);
}

/// Pantalla de Sesiones.
pub fn draw_sessions(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme) {
    let block = Block::bordered()
        .border_type(BorderType::Rounded)
        .border_style(theme.border(true))
        .title(" ❐ Sesiones de Trabajo ")
        .title_style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));

    match &state.sessions {
        LoadState::Ready(data) => {
            let items: Vec<ListItem> = data
                .rows
                .iter()
                .enumerate()
                .map(|(i, r)| {
                    let is_selected = i == state.selection;
                    let style = if is_selected {
                        Style::default()
                            .fg(theme.accent)
                            .bg(theme.selection_bg)
                            .add_modifier(Modifier::BOLD)
                    } else {
                        Style::default().fg(theme.text)
                    };
                    let prefix = if is_selected { "▶ " } else { "  " };
                    let status_badge = format!("[{}]", r.status);
                    ListItem::new(format!("{prefix}{:<16} {:<12} {}", r.session_id, status_badge, r.opened_at)).style(style)
                })
                .collect();

            let list = List::new(items).block(block);
            frame.render_widget(list, area);
        }
        LoadState::Loading => {
            let p = Paragraph::new("Cargando sesiones...")
                .style(Style::default().fg(theme.muted))
                .block(block);
            frame.render_widget(p, area);
        }
        LoadState::Failed(e) => {
            let p = Paragraph::new(format!("Error: {e}"))
                .style(Style::default().fg(theme.error))
                .block(block);
            frame.render_widget(p, area);
        }
        LoadState::Idle => {
            let p = Paragraph::new("Sin sesiones").block(block);
            frame.render_widget(p, area);
        }
    }
}

/// Pantalla de Detalle de Sesión.
pub fn draw_session_detail(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme) {
    let block = Block::bordered()
        .border_type(BorderType::Rounded)
        .border_style(theme.border(true))
        .title(" ◉ Detalle de Sesión ")
        .title_style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));

    match &state.detail {
        LoadState::Ready(d) => {
            let mut lines = vec![
                Line::from(vec![
                    Span::styled("ID: ", Style::default().fg(theme.text_muted)),
                    Span::styled(&d.session_id, Style::default().fg(theme.text).add_modifier(Modifier::BOLD)),
                ]),
                Line::from(vec![
                    Span::styled("Estado: ", Style::default().fg(theme.text_muted)),
                    Span::styled(&d.status, Style::default().fg(theme.success)),
                ]),
                Line::from(vec![
                    Span::styled("Checkpoints: ", Style::default().fg(theme.text_muted)),
                    Span::styled(format!("{}", d.checkpoints.len()), Style::default().fg(theme.accent_soft)),
                ]),
                Line::from(""),
                Line::from(Span::styled("Checkpoints:", Style::default().fg(theme.accent).add_modifier(Modifier::BOLD))),
            ];

            for (i, cp) in d.checkpoints.iter().enumerate() {
                lines.push(Line::from(vec![
                    Span::styled(format!("  {}. ", i + 1), Style::default().fg(theme.muted)),
                    Span::styled(format!("{} — {}", cp.timestamp, cp.note), Style::default().fg(theme.text)),
                ]));
            }

            frame.render_widget(Paragraph::new(lines).block(block).wrap(Wrap { trim: true }), area);
        }
        _ => {
            frame.render_widget(Paragraph::new("Selecciona una sesión").block(block), area);
        }
    }
}

/// Pantalla de Acciones y Propuestas del Engine.
pub fn draw_actions(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme) {
    let block = Block::bordered()
        .border_type(BorderType::Rounded)
        .border_style(theme.border(true))
        .title(" ↯ Propuestas del Action Engine ")
        .title_style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));

    match &state.actions {
        LoadState::Ready(data) => {
            let items: Vec<ListItem> = data
                .proposals
                .iter()
                .enumerate()
                .map(|(i, a)| {
                    let is_selected = i == state.selection;
                    let style = if is_selected {
                        Style::default()
                            .fg(theme.accent)
                            .bg(theme.selection_bg)
                            .add_modifier(Modifier::BOLD)
                    } else {
                        Style::default().fg(theme.text)
                    };
                    let prefix = if is_selected { "▶ " } else { "  " };
                    let rev = if a.reversible { "✓ reversible" } else { "⚠ permanente" };
                    ListItem::new(format!("{prefix}{:<24} {:<14} score: {:.2} — {}", a.id, rev, a.score, a.title)).style(style)
                })
                .collect();

            let list = List::new(items).block(block);
            frame.render_widget(list, area);
        }
        _ => {
            frame.render_widget(Paragraph::new("Sin acciones pendientes").block(block), area);
        }
    }
}

/// Pantalla de Búsqueda Híbrida.
pub fn draw_search(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(3), Constraint::Min(4)])
        .split(area);

    // Input de búsqueda
    let input_block = Block::bordered()
        .border_type(BorderType::Rounded)
        .border_style(theme.border(true))
        .title(" ⌕ Buscar en Memoria (BM25 + Semántica RRF) ")
        .title_style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));

    let query_display = format!("> {}█", state.search_query);
    let input_p = Paragraph::new(query_display)
        .style(Style::default().fg(theme.text))
        .block(input_block);

    frame.render_widget(input_p, chunks[0]);

    // Resultados
    let results_block = Block::bordered()
        .border_type(BorderType::Rounded)
        .border_style(theme.border(false))
        .title(" Resultados ");

    match &state.search {
        LoadState::Ready(data) => {
            let items: Vec<ListItem> = data
                .hits
                .iter()
                .enumerate()
                .map(|(i, h)| {
                    let is_selected = i == state.selection;
                    let style = if is_selected {
                        Style::default()
                            .fg(theme.accent)
                            .bg(theme.selection_bg)
                            .add_modifier(Modifier::BOLD)
                    } else {
                        Style::default().fg(theme.text)
                    };
                    let source_badge = format!("[{}]", h.source);
                    ListItem::new(format!("{:<12} {:<30} score: {:.3}\n     {}", source_badge, h.title, h.score, h.path)).style(style)
                })
                .collect();

            let list = List::new(items).block(results_block);
            frame.render_widget(list, chunks[1]);
        }
        _ => {
            frame.render_widget(Paragraph::new("Escribe una consulta y presiona Enter").block(results_block), chunks[1]);
        }
    }
}

/// Barra de estado inferior con atajos siempre visibles — cada par
/// `[tecla] etiqueta` es un botón clickeable (geometría en `crate::hit`).
pub fn draw_status_bar(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme) {
    let mut hints: Vec<Span> = Vec::new();
    for (cell, h) in crate::hit::status_cells(area) {
        let key_style = if crate::hit::hovered(state, cell) && h.action.is_some() {
            Style::default().fg(theme.bg).bg(theme.accent).add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(theme.accent).add_modifier(Modifier::BOLD)
        };
        hints.push(Span::raw(" "));
        hints.push(Span::styled(h.key, key_style));
        hints.push(Span::raw(" "));
        hints.push(Span::styled(format!("{}  ", h.label), Style::default().fg(theme.text_muted)));
    }

    let bar = Paragraph::new(Line::from(hints))
        .style(Style::default().bg(theme.mantle));

    frame.render_widget(bar, area);
}

/// Overlays y Modales (Help, Confirmaciones).
pub fn draw_overlay(frame: &mut Frame<'_>, area: Rect, state: &AppState, theme: &Theme) {
    match state.overlay {
        Overlay::Help => {
            let popup_area = centered_rect(60, 60, area);
            frame.render_widget(Clear, popup_area);

            let block = Block::bordered()
                .border_type(BorderType::Rounded)
                .border_style(theme.border(true))
                .title(" ※ Ayuda y Keymap Vim ")
                .title_style(Style::default().fg(theme.accent).add_modifier(Modifier::BOLD));

            let lines = vec![
                Line::from(Span::styled("Navegación General:", Style::default().fg(theme.accent_soft).add_modifier(Modifier::BOLD))),
                Line::from("  j / Down   - Bajar en la lista"),
                Line::from("  k / Up     - Subir en la lista"),
                Line::from("  g / Home   - Ir al inicio"),
                Line::from("  G / End    - Ir al final"),
                Line::from("  Enter      - Seleccionar / Activar"),
                Line::from("  Esc / b    - Volver / Cerrar modal"),
                Line::from(""),
                Line::from(Span::styled("Atajos de Pantalla:", Style::default().fg(theme.accent_soft).add_modifier(Modifier::BOLD))),
                Line::from("  s          - Pantalla de Sesiones"),
                Line::from("  a          - Pantalla de Acciones (o auto-ok dentro de acciones)"),
                Line::from("  /          - Búsqueda en memoria"),
                Line::from("  c          - Copiar selección (OSC 52)"),
                Line::from("  q / Ctrl+C - Salir"),
            ];

            frame.render_widget(Paragraph::new(lines).block(block), popup_area);
        }
        Overlay::Confirm { index: _, armed } => {
            let popup_area = centered_rect(50, 25, area);
            frame.render_widget(Clear, popup_area);

            let block = Block::bordered()
                .border_type(BorderType::Double) // Doble borde para alerta crítica (spec §4)
                .border_style(Style::default().fg(theme.warning).add_modifier(Modifier::BOLD))
                .title(" ⚠ Confirmar Ejecución ")
                .title_style(Style::default().fg(theme.warning).add_modifier(Modifier::BOLD));

            let msg = if armed {
                "Presiona ENTER una vez más para ejecutar la acción irreversible."
            } else {
                "¿Deseas ejecutar esta acción? Presiona ENTER para confirmar, ESC para cancelar."
            };

            frame.render_widget(Paragraph::new(msg).block(block).wrap(Wrap { trim: true }), popup_area);
        }
        Overlay::ConfirmBatch { count, armed } => {
            let popup_area = centered_rect(50, 25, area);
            frame.render_widget(Clear, popup_area);

            let block = Block::bordered()
                .border_type(BorderType::Double)
                .border_style(Style::default().fg(theme.warning).add_modifier(Modifier::BOLD))
                .title(" ⚠ Confirmar Lote Auto-OK ")
                .title_style(Style::default().fg(theme.warning).add_modifier(Modifier::BOLD));

            let msg = if armed {
                format!("Confirmando lote de {count} acciones. ENTER para proceder.")
            } else {
                format!("¿Ejecutar lote de {count} acciones auto-ok? ENTER para armar, ESC para cancelar.")
            };

            frame.render_widget(Paragraph::new(msg).block(block).wrap(Wrap { trim: true }), popup_area);
        }
        Overlay::None => {}
    }
}

/// Función auxiliar para centrar rectángulos de popups/modales.
fn centered_rect(percent_x: u16, percent_y: u16, r: Rect) -> Rect {
    let popup_layout = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(r);

    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(popup_layout[1])[1]
}

/// Renderiza el wordmark 3D voxel "CORTEX" con caras frontales, iluminadas y sombras 3D inferiores.
pub fn draw_3d_wordmark(buf: &mut ratatui::buffer::Buffer, area: Rect, theme: &Theme) {
    let wm = cortex_branding::wordmark::wordmark();
    let (mw, mh) = (wm.w() as u16, wm.h() as u16);
    let rows = (mh as usize).div_ceil(2); // 4 filas con half-blocks
    if area.width < mw || area.height < rows as u16 {
        return;
    }
    let ox = area.x + (area.width.saturating_sub(mw)) / 2;
    let oy = area.y;

    for y in 0..rows.min(area.height as usize) {
        let py_top = y * 2;
        let py_bottom = py_top + 1;
        for x in 0..(mw as usize).min(area.width as usize) {
            let k_top = wm.get(x, py_top);
            let k_bottom = if py_bottom < mh as usize {
                wm.get(x, py_bottom)
            } else {
                cortex_branding::pixels::PixelKind::Transparent
            };

            let c_top = match k_top {
                cortex_branding::pixels::PixelKind::Highlight => Some(theme.wordmark_highlight),
                cortex_branding::pixels::PixelKind::Mark | cortex_branding::pixels::PixelKind::Cross => Some(theme.wordmark_face),
                cortex_branding::pixels::PixelKind::Layer => Some(theme.wordmark_shadow),
                cortex_branding::pixels::PixelKind::Shadow => Some(theme.wordmark_deep),
                _ => None,
            };
            let c_bottom = match k_bottom {
                cortex_branding::pixels::PixelKind::Highlight => Some(theme.wordmark_highlight),
                cortex_branding::pixels::PixelKind::Mark | cortex_branding::pixels::PixelKind::Cross => Some(theme.wordmark_face),
                cortex_branding::pixels::PixelKind::Layer => Some(theme.wordmark_shadow),
                cortex_branding::pixels::PixelKind::Shadow => Some(theme.wordmark_deep),
                _ => None,
            };

            let cell = buf.cell_mut((ox + x as u16, oy + y as u16));
            let Some(cell) = cell else { continue };

            match (c_top, c_bottom) {
                (Some(top), Some(bot)) => {
                    cell.set_symbol("▀");
                    cell.set_fg(top);
                    cell.set_bg(bot);
                }
                (Some(top), None) => {
                    cell.set_symbol("▀");
                    cell.set_fg(top);
                }
                (None, Some(bot)) => {
                    cell.set_symbol("▄");
                    cell.set_fg(bot);
                }
                (None, None) => {}
            }
        }
    }
}
