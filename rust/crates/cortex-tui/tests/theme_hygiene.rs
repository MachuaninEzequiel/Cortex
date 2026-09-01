//! Higiene del tema (spec §7.2): ningún `Color::Rgb(...)` fuera de
//! `theme.rs` y `renderer.rs`. La paleta de marca vive en
//! `cortex-branding`; acá se exige que las pantallas/componentes usen
//! `Theme` o los widgets, nunca colores crudos.
//!
//! El test escanea las fuentes del crate (src/), excluyendo theme.rs y
//! renderer.rs (los dos lugares habilitados). Falla con el archivo y la
//! línea del infractor.

use std::path::Path;

fn walk_rs(dir: &Path, out: &mut Vec<std::path::PathBuf>) {
    for entry in std::fs::read_dir(dir).unwrap() {
        let p = entry.unwrap().path();
        if p.is_dir() {
            walk_rs(&p, out);
        } else if p.extension().is_some_and(|e| e == "rs") {
            out.push(p);
        }
    }
}

#[test]
fn no_hay_color_rgb_fuera_de_theme_y_renderer() {
    let manifest = Path::new(env!("CARGO_MANIFEST_DIR"));
    let src = manifest.join("src");
    let mut files = Vec::new();
    walk_rs(&src, &mut files);

    let mut offenders: Vec<(String, usize)> = Vec::new();
    for f in files {
        let name = f.file_name().unwrap().to_string_lossy().to_string();
        if name == "theme.rs" || name == "renderer.rs" {
            continue;
        }
        let text = std::fs::read_to_string(&f).unwrap();
        for (i, line) in text.lines().enumerate() {
            // Permite: "Color::Rgb" fuera de un literal constructivo solo en
            // comentarios/doc. Busca el constructor real.
            let trimmed = line.trim_start();
            if trimmed.contains("Color::Rgb(") && !trimmed.starts_with("//") {
                offenders.push((f.display().to_string(), i + 1));
            }
        }
    }
    assert!(
        offenders.is_empty(),
        "Color::Rgb fuera de theme.rs/renderer.rs (spec §7.2): {offenders:?}"
    );
}

#[test]
fn theme_expone_tokens_semanticos() {
    use cortex_branding::ansi::ColorMode;
    let t = cortex_tui::Theme::new(ColorMode::Truecolor);
    // Los tokens semánticos están resueltos (no Reset) en truecolor.
    assert_ne!(t.text_primary, ratatui::prelude::Color::Reset);
    assert_ne!(t.border_idle, ratatui::prelude::Color::Reset);
    // En Plain todo es Reset (jerarquía por símbolos, no por color).
    let p = cortex_tui::Theme::new(ColorMode::Plain);
    assert_eq!(p.text_primary, ratatui::prelude::Color::Reset);
    assert_eq!(p.selection_bg, ratatui::prelude::Color::Reset);
}
