//! Preview de las tres variantes + wordmark (dev: `cargo run -p
//! cortex-branding --example preview`). Colorea según entorno; respeta
//! NO_COLOR.

use cortex_branding::ansi::{self, ColorMode};
use cortex_branding::logo::LogoVariant;
use cortex_branding::wordmark::wordmark;

fn main() {
    let mode = ansi::env_color_mode();
    println!("modo de color: {mode:?}\n");
    for variant in [LogoVariant::Full, LogoVariant::Compact, LogoVariant::Mark] {
        let map = variant.pixel_map();
        println!(
            "── {} ({}×{} px → {} cols × {} filas) ──",
            variant.label(),
            map.w(),
            map.h(),
            map.w(),
            map.h().div_ceil(2)
        );
        if mode == ColorMode::Plain {
            println!("{}", ansi::render_plain(map));
        } else {
            println!("{}", ansi::render_ansi(map, mode));
        }
        println!();
    }
    println!("── wordmark (35×7 px) ──");
    let wm = wordmark();
    if mode == ColorMode::Plain {
        println!("{}", ansi::render_plain(wm));
    } else {
        println!("{}", ansi::render_ansi(wm, mode));
    }
}
