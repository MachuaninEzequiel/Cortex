//! `cortex tutor` y `cortex hint` — puertos de cli/main.py sobre
//! cortex-tutor (P12B-7).
//!
//! - `hint`: paridad byte-a-byte real vs Python pipado (rich Panel width=80,
//!   ver `rich_panel`).
//! - `tutor <slug>`: imprime el recurso embebido del crate (captura rich sin
//!   ANSI a ~98 col, divergencia cosmética documentada en P12B-7 ⇒ caso
//!   self-golden en el gate, no paridad live).
//! - `tutor` sin args: loop interactivo fiel a `TutorEngine.run`
//!   (EOF ⇒ línea en blanco y salida rc=0).

use std::io::{BufRead, Write};

use clap::Parser;

use crate::rich_panel;

#[derive(Parser, Debug)]
#[command(
    name = "tutor",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct TutorArgs {
    /// Tópico directo (ej: 'pipeline', 'vault', 'commands'). Sin argumento abre el menú.
    #[arg(value_name = "TOPIC")]
    pub topic: Option<String>,
}

/// Parsea tokens y ejecuta. Siempre retorna true (subárbol nuestro).
pub fn run(tokens: &[String]) -> bool {
    let args =
        TutorArgs::parse_from(std::iter::once("tutor".to_string()).chain(tokens.iter().cloned()));
    std::process::exit(match args.topic.as_deref() {
        Some(slug) => show_topic(slug),
        None => run_menu(),
    });
}

/// `engine.show_topic_by_slug(topic)` + error contractual si no existe.
fn show_topic(slug: &str) -> i32 {
    match cortex_tutor::engine::show_topic_by_slug(slug) {
        Some(body) => {
            print_ensuring_final_newline(&body);
            0
        }
        None => {
            let slugs: Vec<String> = cortex_tutor::topics::get_all_topics()
                .into_iter()
                .map(|t| t.slug.to_string())
                .collect();
            eprintln!(
                "Tópico '{slug}' no encontrado. Disponibles: {}",
                slugs.join(", ")
            );
            1
        }
    }
}

/// `TutorEngine.run()` con stdin heredado; EOF corta el loop.
fn run_menu() -> i32 {
    let topics = cortex_tutor::topics::get_all_topics();
    if topics.is_empty() {
        println!("No hay tópicos registrados.");
        return 0;
    }
    let menu = cortex_tutor::engine::render_menu();
    let stdin = std::io::stdin();
    let mut lines = stdin.lock().lines();

    loop {
        // _render_menu: blank + panel + blank (console.clear() es no-op pipado).
        println!();
        print!("{menu}");
        println!();
        let _ = std::io::stdout().flush();

        print!("  Elegí un tema (1-{}) o 'q' para salir: ", topics.len());
        let _ = std::io::stdout().flush();

        let choice = match lines.next() {
            Some(Ok(line)) => line,
            Some(Err(_)) | None => {
                println!();
                return 0;
            }
        };
        let choice = choice.trim().to_lowercase();

        if matches!(choice.as_str(), "q" | "quit" | "exit" | "salir") {
            println!("\n  ¡Hasta la próxima!\n");
            return 0;
        }

        if let Ok(digits) = choice.parse::<usize>() {
            let idx = digits.wrapping_sub(1);
            if idx < topics.len() {
                print_ensuring_final_newline(topics[idx].body);
                render_footer();
                match lines.next() {
                    Some(Ok(_)) => continue,
                    Some(Err(_)) | None => return 0,
                }
            }
        }

        if let Some(body) = cortex_tutor::engine::show_topic_by_slug(&choice) {
            print_ensuring_final_newline(&body);
            render_footer();
            match lines.next() {
                Some(Ok(_)) => continue,
                Some(Err(_)) | None => return 0,
            }
        }

        println!(
            "  '{choice}' no es válido. Usá un número (1-{}) o 'q'.",
            topics.len()
        );
        print!("  [Enter para continuar]");
        let _ = std::io::stdout().flush();
        match lines.next() {
            Some(Ok(_)) => continue,
            Some(Err(_)) | None => return 0,
        }
    }
}

fn render_footer() {
    println!();
    println!("  ← Enter = volver al menú  |  q = salir");
}

fn print_ensuring_final_newline(body: &str) {
    if body.ends_with('\n') {
        print!("{body}");
    } else {
        println!("{body}");
    }
    let _ = std::io::stdout().flush();
}

/// `cortex hint` — panel rich replicado, paridad byte-a-byte.
pub fn run_hint() -> bool {
    let cwd = std::env::current_dir().unwrap_or_default();
    let state = cortex_tutor::hint::ProjectState::detect(&cwd);
    let hint = cortex_tutor::hint::get_hint(&state);

    let content = format!("{}\n\n  $ {}", hint.body, hint.command);
    let title = format!("{} {}", hint.icon, hint.title);
    // tip.render(): c.print() / c.print(Panel(...)) / c.print()
    println!();
    print!("{}", rich_panel::render(&title, &content));
    println!();
    true
}
