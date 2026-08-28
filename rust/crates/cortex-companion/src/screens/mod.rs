//! Pantallas del Companion (G-B2b+): cada una renderiza sobre datos puros
//! y devuelve `AppRenderInfo` con los botones del frame (para el hit-test
//! del siguiente). El binario inyecta los backends; los render no tocan I/O.

pub mod actions_screen;
pub mod brain_screen;
pub mod home;
pub mod menu_screen;
pub mod search_screen;
pub mod sessions_screen;

pub use actions_screen::{actions_areas, render_actions, ActionsAreas, ActionsRenderInfo};
pub use brain_screen::{
    brain_areas, brain_rows, render_brain, BrainAreas, BrainRenderInfo, BrainRow,
};
pub use home::{render_home, AppRenderInfo as HomeRenderInfo, BrandAssets, HomeAreas, HomeData};
pub use menu_screen::{menu_areas, render_menu, AppRenderInfo as MenuRenderInfo, MenuAreas};
pub use modal::render_modal;
pub use search_screen::{render_search, search_areas, SearchAreas, SearchData, SearchRenderInfo};
pub use sessions_screen::{render_sessions, sessions_areas, SessionsAreas, SessionsRenderInfo};

/// Modal de aprobación como SUPERFICIE de la máquina de estados (B6): se
/// renderiza encima de la pantalla actual cuando `AppState::pending` está
/// setiado. Muestra SIEMPRE el efecto exacto (spec 14 §5) y los botones
/// [Aprobar]/[Denegar] cuyas rects comparten geometría con `hit_test`.
mod modal {
    use ratatui::layout::Rect;
    use ratatui::prelude::Color;
    use ratatui::style::{Modifier, Style};
    use ratatui::text::{Line, Span};
    use ratatui::widgets::{Block, Borders, Paragraph};
    use ratatui::Frame;

    use crate::app::{MODAL_APROBAR_RECT, MODAL_DENEGAR_RECT, MODAL_RECT};
    use crate::approval::ApprovalRequest;

    pub fn render_modal(f: &mut Frame<'_>, req: &ApprovalRequest) {
        let title = Span::styled(req.title.clone(), Style::default().fg(Color::Yellow));
        let effect = effect_content(&req.effect);
        f.render_widget(
            Paragraph::new(vec![Line::from(effect)])
                .block(Block::default().borders(Borders::ALL).title(title)),
            MODAL_RECT,
        );
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                "[ Aprobar ]",
                Style::default()
                    .fg(Color::Green)
                    .add_modifier(Modifier::BOLD),
            ))),
            MODAL_APROBAR_RECT,
        );
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                "[ Denegar ]",
                Style::default().fg(Color::Red),
            ))),
            MODAL_DENEGAR_RECT,
        );
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                "clic decide · Esc/deny · el efecto exacto se audita",
                Style::default().fg(Color::DarkGray),
            ))),
            Rect::new(
                MODAL_RECT.x + 2,
                MODAL_RECT.y + 5,
                MODAL_RECT.width.saturating_sub(4),
                1,
            ),
        );
    }

    /// Recorta el efecto a la caja del modal (largo variable, sin break).
    fn effect_content(effect: &str) -> Span<'static> {
        let max = (MODAL_RECT.width.saturating_sub(4)) as usize;
        let content: String = effect.chars().collect();
        if content.chars().count() > max {
            let cut: String = content.chars().take(max.saturating_sub(1)).collect();
            Span::styled(format!("{cut}…"), Style::default().fg(Color::White))
        } else {
            Span::styled(content, Style::default().fg(Color::White))
        }
    }
}
