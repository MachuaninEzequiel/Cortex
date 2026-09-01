//! Preview visual de los modos de Herdr sin terminal: renderiza cada modo a
//! un `TestBackend` y vuelca el buffer con los ESTILOS REALES de cada celda
//! (fg/bg/símbolo) en un formato JSON compacto que el script de conversión a
//! PNG consume. Uso:
//!
//!   cargo run -p cortex-companion --example preview_ansi -- <float|sidecar|copilot|home> \
//!     > /tmp/preview.json
//!
//! Es una herramienta de desarrollo (verificación de estética), no shipped.

use cortex_companion::engine::{ActionProposal, DoctorSummary, SessionSummary, StatsSummary};
use cortex_companion::screens::copilot_screen::{copilot_areas, render_copilot};
use cortex_companion::screens::home::{home_areas, render_home, BrandAssets, HomeData};
use cortex_companion::screens::hud_screen::{hud_areas, render_hud};
use ratatui::backend::TestBackend;
use ratatui::layout::Rect;
use ratatui::prelude::Color;
use ratatui::Terminal;

fn sample_data() -> HomeData {
    HomeData {
        project: "cortex-demo".into(),
        branch: Some("feature/transformacion-2026-08".into()),
        session: Some(SessionSummary {
            id: "2026-08-17_demo".into(),
            status: "open".into(),
            mode: "managed".into(),
            opened_at: "hace 2 min".into(),
            phase: Some("implement".into()),
        }),
        top_action: Some(ActionProposal {
            id: "suggest_next_phase".into(),
            title: "sugerir siguiente fase".into(),
            score: 1.5,
            cost: "instant".into(),
            reversible: true,
            effect: "sugiere la siguiente fase".into(),
        }),
        doctor: Some(DoctorSummary {
            ok: true,
            checks: vec![("vault".into(), "ok".into()), ("mcp".into(), "ok".into())],
        }),
        stats: Some(StatsSummary {
            episodic: 12,
            semantic: 34,
            vault_path: ".cortex/vault".into(),
        }),
        hygiene: Some(ActionProposal {
            id: "vault.reindex".into(),
            title: "reindexar vault".into(),
            score: 2.0,
            cost: "instant".into(),
            reversible: true,
            effect: "reindexa la memoria semántica".into(),
        }),
        agent_label: "pi idle".into(),
        ask: "¿qué sigue?".into(),
        prompt: String::new(),
        error: None,
        liquid: Default::default(),
    }
}

fn dump(term: Terminal<TestBackend>) {
    let buf = term.backend().buffer().clone();
    let w = buf.area.width as usize;
    let h = buf.area.height as usize;
    let cells: Vec<serde_json::Value> = buf
        .content
        .iter()
        .map(|cell| {
            let sym = if cell.symbol().is_empty() { " " } else { cell.symbol() };
            let rgb = |c: Color| match c {
                Color::Rgb(r, g, b) => serde_json::json!([r, g, b]),
                _ => serde_json::Value::Null,
            };
            serde_json::json!({"s": sym, "fg": rgb(cell.fg), "bg": rgb(cell.bg)})
        })
        .collect();
    let doc = serde_json::json!({"w": w, "h": h, "cells": cells});
    println!("{}", serde_json::to_string(&doc).unwrap());
}

fn main() {
    let mode = std::env::args().nth(1).unwrap_or_else(|| "home".into());
    let data = sample_data();
    let (w, h) = match mode.as_str() {
        "float" => (90, 12),
        "sidecar" => (44, 40),
        "copilot" => (70, 24),
        _ => (80, 24),
    };
    let mut term = Terminal::new(TestBackend::new(w, h)).expect("test terminal");
    term.draw(|f| {
        let area = f.area();
        match mode.as_str() {
            "float" | "sidecar" => {
                let mut areas = hud_areas(area);
                areas.hovered_mouse = None;
                let _ = render_hud(f, area, &data, &mut areas);
            }
            "copilot" => {
                let mut areas = copilot_areas(area);
                areas.hovered_mouse = None;
                let agent: Option<cortex_companion::herdr::HerdrAgentInfo> = None;
                let _ = render_copilot(f, area, &data, &agent, &mut areas);
            }
            _ => {
                let mut areas = home_areas(Rect::new(0, 0, w, h));
                areas.hovered_mouse = None;
                let _ = render_home(f, area, &data, &BrandAssets::load(), &mut areas);
            }
        }
    })
    .expect("draw");
    dump(term);
}
