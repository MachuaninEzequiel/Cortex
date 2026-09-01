//! Comando `cortex next` (Cierre T2) — espejo de cli/next.py sobre el
//! motor nativo cortex-actions (P6). Salida texto/--json byte-parity;
//! `elapsed_ms` es medición propia ⇒ normalizable {{ELAPSED}} en gates.

use std::io::{IsTerminal as _, Write as _};
use std::path::Path;
use std::time::Instant;

use clap::Parser;
use cortex_actions::catalog::build_default_registry;
use cortex_actions::context::ActionContext;
use cortex_actions::metrics::calcular_metricas;
use cortex_actions::scheduler::Scheduler;
use cortex_actions::store::{ActionLog, PreferencesStore};

fn echo(s: &str) {
    let mut out = std::io::stdout();
    let _ = writeln!(out, "{s}");
}

#[derive(Parser, Debug)]
#[command(
    name = "next",
    disable_help_subcommand = true,
    disable_version_flag = true
)]
pub struct NextArgs {
    #[arg(long)]
    pub all: bool,
    #[arg(long)]
    pub json: bool,
    #[arg(long)]
    pub explain_why_not: bool,
    #[arg(long)]
    pub stats: bool,
    /// Abre la pantalla de aprobación de acciones (TUI ratatui).
    #[arg(long)]
    pub tui: bool,
    #[arg(long)]
    pub project_root: Option<String>,
}

pub fn run(argv: &[String]) -> bool {
    let args = match NextArgs::try_parse_from(
        std::iter::once("next".to_string()).chain(argv.iter().cloned()),
    ) {
        Ok(a) => a,
        Err(e) => {
            eprint!("{e}");
            return true;
        }
    };

    let t0 = Instant::now();

    // --tui: pantalla de aprobación ratatui (el motor se evalúa adentro,
    // con el MISMO pipeline que este comando — la TUI orquesta, no duplica).
    if args.tui {
        let root = args.project_root.as_deref().map(Path::new);
        let req = cortex_tui::app::UiRequest {
            screen: cortex_tui::app::Screen::Actions,
            project_root: root,
            status_filter: None,
            service: None,
            search: Some(std::sync::Arc::new(
                crate::memory_cmds::CliSearchAdapter::new(crate::paths::resolve_project_root(
                    args.project_root.as_deref(),
                )),
            )),
        };
        if !std::io::stdout().is_terminal() {
            return match cortex_tui::app::snapshot(req, 100, 40) {
                Ok(t) => {
                    println!("{t}");
                    eprintln!("next: terminal no interactivo — snapshot emitido; usá un terminal real para el modo en vivo.");
                    true
                }
                Err(e) => {
                    eprintln!("next: {e}");
                    true
                }
            };
        }
        return match cortex_tui::app::run(req) {
            Ok(()) => true,
            Err(e) => {
                eprintln!("next: {e}");
                true
            }
        };
    }

    let ctx = ActionContext::from_project_root(args.project_root.as_deref().map(Path::new));
    if !ctx.config_existe() {
        echo(&format!(
            "Cortex no está configurado en {} (no encuentro config.yaml) — corré \
             `cortex setup agent` primero.",
            ctx.workspace_root.display()
        ));
        return true;
    }

    // --stats: métricas del motor (Fase E).
    if args.stats {
        let metricas = calcular_metricas(&ActionLog::new(&ctx.dot_cortex()));
        use crate::pyjson::{Num, PyVal};
        let v = PyVal::obj(vec![
            (
                "total_ejecuciones",
                PyVal::Num(Num::Int(metricas.total_ejecuciones as i64)),
            ),
            ("via_auto", PyVal::Num(Num::Int(metricas.via_auto as i64))),
            (
                "via_usuario",
                PyVal::Num(Num::Int(metricas.via_usuario as i64)),
            ),
            ("pct_motor", PyVal::Num(Num::Float(metricas.pct_motor))),
            (
                "dias_con_interaccion",
                PyVal::Num(Num::Int(metricas.dias_con_interaccion.len() as i64)),
            ),
            (
                "por_accion",
                crate::pyjson::PyVal::Obj(
                    metricas
                        .acciones_por_id
                        .iter()
                        .map(|(k, n)| (k.clone(), PyVal::Num(Num::Int(*n as i64))))
                        .collect(),
                ),
            ),
            (
                "definicion",
                crate::pyjson::PyVal::s(
                    "pct_motor alto + volumen estable = el motor toma las decisiones \
                     rutinarias (target dueño: abrir el menú <1 vez/día activo)",
                ),
            ),
        ]);
        echo(&crate::pyjson::pydantic_dumps_indent2(&v));
        return true;
    }

    let registry = build_default_registry(&ctx);
    let prefs = PreferencesStore::new(&ctx.dot_cortex());
    let scheduler = Scheduler::new(&prefs);

    let propuestas = scheduler.propose(&registry, args.all);
    let elapsed_ms = t0.elapsed().as_millis() as i64;

    if args.json {
        use crate::pyjson::{Num, PyVal};
        let mut payload: Vec<(String, PyVal)> =
            vec![("elapsed_ms".into(), PyVal::Num(Num::Int(elapsed_ms)))];
        let acciones: Vec<PyVal> = propuestas
            .iter()
            .filter_map(|p| {
                let a = registry.get(&p.action_id)?;
                Some(PyVal::obj(vec![
                    ("id", PyVal::s(a.id.clone())),
                    ("title", PyVal::s(a.title.clone())),
                    ("category", PyVal::s(a.category.as_str())),
                    ("effect", PyVal::s(a.effect.clone())),
                    ("cost", PyVal::s(a.cost.as_str())),
                    ("reversible", PyVal::Bool(a.reversible)),
                    ("auto_ok", PyVal::Bool(a.auto_ok)),
                    ("score", PyVal::Num(Num::Float(p.score))),
                ]))
            })
            .collect();
        payload.push(("acciones".into(), PyVal::Arr(acciones)));
        if args.explain_why_not {
            let why = scheduler.explain_why_not(&registry, args.all);
            payload.push((
                "why_not".into(),
                PyVal::Obj(
                    why.into_iter()
                        .map(|(aid, razones)| {
                            (
                                aid,
                                PyVal::Arr(razones.iter().map(|r| PyVal::s(r.clone())).collect()),
                            )
                        })
                        .collect(),
                ),
            ));
        }
        echo(&crate::pyjson::pydantic_dumps_indent2(&PyVal::Obj(payload)));
        return true;
    }

    if propuestas.is_empty() {
        echo("\u{2705} Nada pendiente \u{2014} tu workspace est\u{e1} al d\u{ed}a.");
        if args.explain_why_not {
            for (aid, razones) in scheduler.explain_why_not(&registry, args.all) {
                echo(&format!("  \u{b7} {aid}: {}", razones.join("; ")));
            }
        }
        return true;
    }

    echo(&format!(
        "\u{1f9e0} Cortex \u{b7} {} acci\u{f3}n(es) sugeridas:\n",
        propuestas.len()
    ));
    for (i, p) in propuestas.iter().enumerate() {
        let Some(a) = registry.get(&p.action_id) else {
            continue;
        };
        let auto = if a.auto_ok { " [auto-ok]" } else { "" };
        echo(&format!(" [{}] {}", i + 1, a.title));
        echo(&format!(
            "     id: {} \u{b7} costo: {}{} \u{b7} score: {}",
            a.id,
            a.cost,
            auto,
            crate::pyjson::format_float(p.score),
        ));
        echo(&format!("     efecto: {}\n", a.effect));
    }

    if args.explain_why_not {
        echo("\u{2014} No propuestas \u{2014}");
        for (aid, razones) in scheduler.explain_why_not(&registry, args.all) {
            echo(&format!("  \u{b7} {aid}: {}", razones.join("; ")));
        }
    }

    echo(&format!(
        "\n[dim]{}ms \u{b7} ejecut\u{e1} `cortex next --json` para salida machine-readable[/dim]",
        elapsed_ms
    ));
    true
}
