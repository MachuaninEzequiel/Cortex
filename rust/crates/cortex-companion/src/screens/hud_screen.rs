//! HUD v1 (doc 17): columna de marca en celdas + diálogos. Sin placa, sin
//! cajas de navegación, sin inyectar al agente.

use std::time::Instant;

use ratatui::layout::{Constraint, Layout, Position, Rect};
use ratatui::prelude::{Color, Frame, Line, Span, Style};
use ratatui::widgets::{Block, Paragraph};

use crate::app::AppAction;
use crate::engine::ActionProposal;
use crate::hud_brand;
use crate::screens::home::{AppRenderInfo, HomeData};
use crate::widgets::{to_color, Button};

use cortex_branding::Rgb;

const TEXT: Rgb = Rgb(0xE4, 0xED, 0xE7);
const MUTED: Rgb = Rgb(0x8A, 0x9E, 0x93);
const MINT: Rgb = Rgb(0x8F, 0xDC, 0xB0);
const MINT_SOFT: Rgb = Rgb(0xAE, 0xE8, 0xC6);
const MINT_PALE: Rgb = Rgb(0xC8, 0xF0, 0xDC);
const BORDER: Rgb = Rgb(0x2A, 0x4A, 0x3A);
const ACCENT: Rgb = Rgb(0x3D, 0x6B, 0x54);
const BG: Rgb = Rgb(0x0C, 0x14, 0x10);

/// Acciones que el HUD puede mostrar y Aprobar (higiene, no ciclo de sesión).
pub fn is_hygiene(id: &str) -> bool {
    matches!(
        id,
        "vault.validate_docs"
            | "vault.reindex"
            | "learn.topic"
            | "memory.prune"
            | "knowledge.promote"
    )
}

pub fn pick_hygiene<'a>(
    actions: &'a [ActionProposal],
    skipped: Option<&str>,
) -> Option<&'a ActionProposal> {
    actions
        .iter()
        .find(|a| is_hygiene(&a.id) && skipped != Some(a.id.as_str()))
}

pub const PROMPT_NO_SESSION: &str = "no hay sesión activa. abrí el trabajo con las skills de Cortex (grill / to-spec / sesión). no pidas que el humano corra la CLI.";

pub const PROMPT_NO_PHASE: &str = "checkpoint de lo que acabás de hacer: evidencia, artifacts tocados, nota de una línea. dirigido a vos, no un comando para el humano.";

pub const PROMPT_NEXT_SPEC: &str = "el requisito ya está grillado. escribí una spec con Goal medible, Non-goals, Acceptance criteria SI/NO, files_in_scope y verification hooks. persistila con cortex_write_doc (doc_type spec). no le pidas al humano `cortex spec` ni `cortex session`.";

pub const PROMPT_NEXT_PLAN: &str = "la spec está. ticketizá en vertical slices: What, Blocked by, Verification, Done when. persistí `.scratch/<feature>/issues/NN-slug.md`. no le pidas al humano `cortex session`.";

pub const PROMPT_NEXT_IMPLEMENT: &str = "tomá el siguiente ticket desbloqueado e implementalo respetando files_in_scope de la spec; evidencia real en verified_claims (>10 chars); no salgas del alcance.";

pub const PROMPT_NEXT_REVIEW: &str = "revisá en dos ejes (Standards y Spec) con hallazgos file:line. veredicto approve / request-changes / block. no le pidas al humano `cortex review` ni `cortex session`.";

pub const PROMPT_NEXT_CLOSE: &str = "el trabajo está en review. cerrá la sesión con las skills/MCP de Cortex (documenter COMPOSED, tool cortex_finish_session). no le pidas al humano `cortex session` ni `cortex finish`.";

pub const PROMPT_PHASE_CLOSE: &str = "la sesión ya está en close. no empujes más fase. si falta evidencia, documentala; no le pidas al humano un comando Cortex.";

pub fn compose_agent_prompt(session: Option<&crate::engine::SessionSummary>) -> String {
    let Some(s) = session else {
        return PROMPT_NO_SESSION.to_string();
    };
    match s.phase.as_deref() {
        Some("grill") => PROMPT_NEXT_SPEC.to_string(),
        Some("spec") => PROMPT_NEXT_PLAN.to_string(),
        Some("plan") => PROMPT_NEXT_IMPLEMENT.to_string(),
        Some("implement") => PROMPT_NEXT_REVIEW.to_string(),
        Some("review") => PROMPT_NEXT_CLOSE.to_string(),
        Some("close") => PROMPT_PHASE_CLOSE.to_string(),
        Some(_) | None => PROMPT_NO_PHASE.to_string(),
    }
}

pub fn hud_prompt(data: &HomeData) -> String {
    if !data.prompt.is_empty() {
        return data.prompt.clone();
    }
    compose_agent_prompt(data.session.as_ref())
}

#[derive(Debug, Clone)]
pub struct HudAreas {
    pub brand: Rect,
    pub mark: Rect,
    pub word: Rect,
    pub dialogs: Rect,
    pub copy_btn: Rect,
    pub approve_btn: Option<Rect>,
    pub skip_btn: Option<Rect>,
    pub ask: Rect,
    pub hovered_mouse: Option<(u16, u16)>,
}

pub fn hud_areas(area: Rect) -> HudAreas {
    let brand_w = if area.width < 90 { 22 } else { 28 }.min(area.width);
    let [brand, dialogs] =
        Layout::horizontal([Constraint::Length(brand_w), Constraint::Min(20)]).areas(area);

    // GRID: MARK (1,0,26,9) / WORD (1,9,26,3) — inset 1 col, sin placa.
    let inset = 1u16.min(brand.width.saturating_sub(1));
    let mark_h = brand.height.saturating_sub(3).max(1);
    let mark = Rect::new(
        brand.x + inset,
        brand.y,
        brand
            .width
            .saturating_sub(inset)
            .min(hud_brand::MARK_W as u16),
        mark_h,
    );
    let word = Rect::new(
        brand.x + inset,
        brand.y.saturating_add(mark_h),
        brand
            .width
            .saturating_sub(inset)
            .min(hud_brand::WORD_W as u16),
        3.min(brand.height.saturating_sub(mark_h)),
    );

    let copy_w = 16u16.min(dialogs.width.saturating_sub(2));
    let copy_btn = Rect::new(
        dialogs.x + dialogs.width.saturating_sub(copy_w + 1),
        dialogs.y + 3,
        copy_w,
        2,
    );
    let btn_w = 15u16.min(dialogs.width / 3);
    let approve_btn = if dialogs.height > 7 {
        Some(Rect::new(
            dialogs.x + dialogs.width.saturating_sub(btn_w * 2 + 3),
            dialogs.y + 7,
            btn_w,
            1,
        ))
    } else {
        None
    };
    let skip_btn = if dialogs.height > 7 {
        Some(Rect::new(
            dialogs.x + dialogs.width.saturating_sub(btn_w + 1),
            dialogs.y + 7,
            btn_w,
            1,
        ))
    } else {
        None
    };
    // GRID ASK (0, 9, …, 2) en pane de 12 filas; si es más bajo, pegado al piso.
    let ask_y = if dialogs.height >= 12 {
        dialogs.y.saturating_add(9)
    } else {
        dialogs.y + dialogs.height.saturating_sub(2)
    };
    let ask = Rect::new(
        dialogs.x,
        ask_y,
        dialogs.width,
        2.min(
            dialogs
                .height
                .saturating_sub(ask_y.saturating_sub(dialogs.y)),
        ),
    );

    HudAreas {
        brand,
        mark,
        word,
        dialogs,
        copy_btn,
        approve_btn,
        skip_btn,
        ask,
        hovered_mouse: None,
    }
}

pub fn hud_hit_test(
    areas: &HudAreas,
    x: u16,
    y: u16,
    hygiene_id: Option<&str>,
) -> Option<AppAction> {
    let p = Position::new(x, y);
    if areas.copy_btn.contains(p) {
        return Some(AppAction::CopyPrompt);
    }
    if let Some(r) = areas.approve_btn {
        if r.contains(p) {
            if let Some(id) = hygiene_id {
                return Some(AppAction::ApproveProposal { id: id.to_string() });
            }
        }
    }
    if let Some(r) = areas.skip_btn {
        if r.contains(p) {
            return Some(AppAction::HudSkip);
        }
    }
    None
}

fn hovered(areas: &HudAreas, id: &str) -> bool {
    let Some((x, y)) = areas.hovered_mouse else {
        return false;
    };
    let p = Position::new(x, y);
    match id {
        "copy" => areas.copy_btn.contains(p),
        "approve" => areas.approve_btn.is_some_and(|r| r.contains(p)),
        "skip" => areas.skip_btn.is_some_and(|r| r.contains(p)),
        _ => false,
    }
}

fn label(_rect: Rect, text: &str, color: Color, hover: bool) -> Paragraph<'_> {
    let style = if hover {
        Style::default()
            .fg(to_color(MINT_PALE))
            .add_modifier(ratatui::style::Modifier::BOLD)
    } else {
        Style::default().fg(color)
    };
    Paragraph::new(Line::from(Span::styled(text.to_string(), style)))
}

pub fn render_hud(
    f: &mut Frame<'_>,
    area: Rect,
    data: &HomeData,
    areas: &mut HudAreas,
) -> AppRenderInfo {
    let t0 = Instant::now();
    f.render_widget(
        Block::default().style(Style::default().bg(to_color(BG)).fg(to_color(TEXT))),
        area,
    );

    hud_brand::blit_mark(f.buffer_mut(), areas.mark);
    if areas.word.width >= 10 && areas.word.height >= 2 {
        hud_brand::blit_word(f.buffer_mut(), areas.word);
    }
    if areas.brand.width >= 24 {
        let x = areas.brand.x + areas.brand.width.saturating_sub(1);
        for y in areas.brand.y..areas.brand.y.saturating_add(areas.brand.height) {
            if let Some(cell) = f.buffer_mut().cell_mut((x, y)) {
                cell.set_symbol("│");
                cell.set_fg(to_color(BORDER));
                cell.set_bg(to_color(BG));
            }
        }
    }

    let dx = areas.dialogs;
    let project = data
        .project
        .rsplit(['/', '\\'])
        .next()
        .unwrap_or(data.project.as_str());
    let agent = if data.agent_label.is_empty() {
        "—"
    } else {
        data.agent_label.as_str()
    };
    f.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("COMPANION", Style::default().fg(to_color(MUTED))),
            Span::raw("  "),
            Span::styled(agent.to_string(), Style::default().fg(to_color(MUTED))),
        ])),
        Rect::new(dx.x + 1, dx.y, dx.width.saturating_sub(2), 1),
    );

    let sess = data
        .session
        .as_ref()
        .map(|s| {
            if let Some(ref ph) = s.phase {
                format!("{} [{}]  ·  fase {}", s.id, s.status, ph)
            } else {
                format!("{} [{}]", s.id, s.status)
            }
        })
        .unwrap_or_else(|| "sin sesión".into());
    let branch = data.branch.clone().unwrap_or_default();
    let meta = format!("{project}  ·  {branch}  ·  {sess}");
    f.render_widget(
        Paragraph::new(Line::from(Span::styled(
            meta,
            Style::default().fg(to_color(TEXT)),
        ))),
        Rect::new(
            dx.x + 1,
            dx.y.saturating_add(1),
            dx.width.saturating_sub(2),
            1,
        ),
    );
    f.render_widget(
        Paragraph::new(Line::from(Span::styled(
            "─".repeat(dx.width as usize),
            Style::default().fg(to_color(BORDER)),
        ))),
        Rect::new(dx.x, dx.y.saturating_add(2), dx.width, 1),
    );

    let prompt = hud_prompt(data);
    let prompt_h = 3u16.min(dx.height.saturating_sub(6)).max(1);
    f.render_widget(
        Paragraph::new(vec![
            Line::from(Span::styled(
                "PROMPT PARA EL AGENTE",
                Style::default().fg(to_color(MUTED)),
            )),
            Line::from(Span::styled(
                prompt.clone(),
                Style::default().fg(to_color(TEXT)),
            )),
        ]),
        Rect::new(
            dx.x + 1,
            dx.y.saturating_add(3),
            dx.width.saturating_sub(areas.copy_btn.width + 3),
            prompt_h,
        ),
    );
    f.render_widget(
        label(
            areas.copy_btn,
            "[ Copiar ]",
            to_color(MINT_PALE),
            hovered(areas, "copy"),
        ),
        areas.copy_btn,
    );

    let mut buttons = vec![Button {
        id: "hud-copy",
        rect: areas.copy_btn,
        label: "[ Copiar ]".into(),
        enabled: true,
    }];

    let hygiene = data.hygiene.as_ref();
    if dx.height > 7 {
        f.render_widget(
            Paragraph::new(Line::from(Span::styled(
                "─".repeat(dx.width as usize),
                Style::default().fg(to_color(BORDER)),
            ))),
            Rect::new(dx.x, dx.y.saturating_add(6), dx.width, 1),
        );
        let title = hygiene
            .map(|a| a.title.as_str())
            .unwrap_or("sin higiene pendiente");
        let score = hygiene
            .map(|a| format!("score {:.1}", a.score))
            .unwrap_or_default();
        f.render_widget(
            Paragraph::new(Line::from(vec![
                Span::styled("HIGIENE  ", Style::default().fg(to_color(MUTED))),
                Span::styled(title.to_string(), Style::default().fg(to_color(MINT_SOFT))),
                Span::raw("  "),
                Span::styled(score, Style::default().fg(to_color(MUTED))),
            ])),
            Rect::new(
                dx.x + 1,
                dx.y.saturating_add(7),
                dx.width.saturating_sub(34).max(10),
                1,
            ),
        );
        if let Some(r) = areas.approve_btn {
            let en = hygiene.is_some();
            f.render_widget(
                label(
                    r,
                    "[ Aprobar ]",
                    to_color(if en { ACCENT } else { MUTED }),
                    hovered(areas, "approve") && en,
                ),
                r,
            );
            buttons.push(Button {
                id: "hud-approve",
                rect: r,
                label: "[ Aprobar ]".into(),
                enabled: en,
            });
        }
        if let Some(r) = areas.skip_btn {
            f.render_widget(
                label(r, "[ Saltar ]", to_color(MUTED), hovered(areas, "skip")),
                r,
            );
            buttons.push(Button {
                id: "hud-skip",
                rect: r,
                label: "[ Saltar ]".into(),
                enabled: hygiene.is_some(),
            });
        }
    }

    f.render_widget(
        Paragraph::new(Line::from(Span::styled(
            "─".repeat(dx.width as usize),
            Style::default().fg(to_color(BORDER)),
        ))),
        Rect::new(dx.x, areas.ask.y.saturating_sub(1), dx.width, 1),
    );
    let ask_txt = if data.ask.is_empty() {
        "›  preguntale a Cortex".to_string()
    } else {
        format!("›  {}", data.ask)
    };
    f.render_widget(
        Paragraph::new(Line::from(Span::styled(
            ask_txt,
            Style::default().fg(to_color(MINT)),
        ))),
        areas.ask,
    );

    AppRenderInfo {
        buttons,
        spent_ms: t0.elapsed().as_secs_f32() * 1000.0,
    }
}
