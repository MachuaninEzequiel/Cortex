//! Verificador de paridad P6 — cortex-actions vs oráculo Python (`cortex next`).
//!
//! Uso: actions_check <fixtures_dir> <golden_dir>
//!
//! Para cada escenario recalcula —con la MISMA semántica del CLI Python— las
//! cuatro salidas gateadas (next_stats.json, next_json.json,
//! next_why_not.json, next_texto.txt), aplica la misma normalización
//! ({{ROOT}}, {{MS}}) y compara byte-a-byte contra los goldens capturados
//! por bench/parity/actions_golden_p6.py.
//!
//! La serialización es manual (emitter propio con orden de claves de
//! inserción) porque `next` en Python emite dicts ordenados por inserción y
//! serde_json sin preserve_order usaría BTreeMap.

use std::path::Path;

use cortex_actions::catalog::build_default_registry;
use cortex_actions::context::ActionContext;
use cortex_actions::metrics::calcular_metricas;
use cortex_actions::models::{redondear, Action};
use cortex_actions::scheduler::Scheduler;
use cortex_actions::store::{ActionLog, PreferencesStore};

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    std::process::exit(1);
}

// ── mini-JSON con orden de inserción + repr de floats de Python ───────────

#[derive(Clone)]
enum Pj {
    Obj(Vec<(String, Pj)>),
    Arr(Vec<Pj>),
    Str(String),
    /// Valor crudo ya formateado (p.ej. `{{MS}}`, sin comillas).
    Raw(String),
    F64(f64),
    U64(u64),
    Bool(bool),
}

/// Espejo del repr de float de CPython (shortest round-trip, ".0" forzado).
fn py_float(x: f64) -> String {
    let s = format!("{x}");
    if s.contains('.') || s.contains('e') || s.contains('E') {
        s
    } else {
        format!("{s}.0")
    }
}

fn escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

fn emit(v: &Pj, indent: usize, out: &mut String) {
    let pad = "  ".repeat(indent);
    let pad_inner = "  ".repeat(indent + 1);
    match v {
        Pj::Obj(fields) => {
            if fields.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push('{');
            for (i, (k, val)) in fields.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push('\n');
                out.push_str(&pad_inner);
                out.push_str(&escape(k));
                out.push_str(": ");
                emit(val, indent + 1, out);
            }
            out.push('\n');
            out.push_str(&pad);
            out.push('}');
        }
        Pj::Arr(items) => {
            if items.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push('[');
            for (i, item) in items.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                out.push('\n');
                out.push_str(&pad_inner);
                emit(item, indent + 1, out);
            }
            out.push('\n');
            out.push_str(&pad);
            out.push(']');
        }
        Pj::Str(s) => out.push_str(&escape(s)),
        Pj::Raw(s) => out.push_str(s),
        Pj::F64(x) => out.push_str(&py_float(*x)),
        Pj::U64(n) => out.push_str(&n.to_string()),
        Pj::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
    }
}

fn dumps(v: &Pj) -> String {
    let mut s = String::new();
    emit(v, 0, &mut s);
    s
}

// ── cálculo espejo del CLI `next` ─────────────────────────────────────────

const DEFINICION: &str = "pct_motor alto + volumen estable = el motor toma las decisiones rutinarias (target dueño: abrir el menú <1 vez/día activo)";

struct SalidaNext {
    /// None solo cuando falta config (rc=1): los tres JSON gateados llevan el
    /// mensaje de error en stderr y stdout queda vacío.
    stats: Option<String>,
    next_json: String,
    why_not_json: String,
    texto: String,
}

fn calcular_salida(fixture: &Path) -> SalidaNext {
    let ctx = ActionContext::from_project_root(Some(fixture));
    if !ctx.config_existe() {
        // Espejo del typer.echo(..., err=True) + Exit(1).
        let msg = format!(
            "Cortex no está configurado en {} (no encuentro config.yaml) — corré `cortex setup agent` primero.\n",
            ctx.workspace_root.display()
        );
        return SalidaNext {
            stats: None,
            next_json: msg.clone(),
            why_not_json: msg.clone(),
            texto: msg,
        };
    }

    // ── next --stats: métricas puras sobre action_log.jsonl (early-return). ──
    let metricas = calcular_metricas(&ActionLog::new(&ctx.dot_cortex()));
    let stats = dumps(&Pj::Obj(vec![
        (
            "total_ejecuciones".into(),
            Pj::U64(metricas.total_ejecuciones as u64),
        ),
        ("via_auto".into(), Pj::U64(metricas.via_auto as u64)),
        ("via_usuario".into(), Pj::U64(metricas.via_usuario as u64)),
        ("pct_motor".into(), Pj::F64(metricas.pct_motor)),
        (
            "dias_con_interaccion".into(),
            Pj::U64(metricas.dias_con_interaccion.len() as u64),
        ),
        (
            "por_accion".into(),
            Pj::Obj(
                metricas
                    .acciones_por_id
                    .iter()
                    .map(|(k, n)| (k.clone(), Pj::U64(*n as u64)))
                    .collect(),
            ),
        ),
        ("definicion".into(), Pj::Str(DEFINICION.into())),
    ]));

    // ── propuestas compartidas por --json / --explain-why-not / texto ──
    let prefs = PreferencesStore::new(&ctx.dot_cortex());
    let registry = build_default_registry(&ctx);
    let scheduler = Scheduler::new(&prefs);
    let propuestas = scheduler.propose(&registry, false);
    let why_not = scheduler.explain_why_not(&registry, false);

    let by_id = |id: &str| -> &Action {
        registry
            .all()
            .iter()
            .find(|a| a.id == id)
            .unwrap_or_else(|| fail(&format!("acción propuesta ausente en catálogo: {id}")))
    };

    let items: Vec<Pj> = propuestas
        .iter()
        .map(|p| {
            let a = by_id(&p.action_id);
            Pj::Obj(vec![
                ("id".into(), Pj::Str(a.id.clone())),
                ("title".into(), Pj::Str(a.title.clone())),
                ("category".into(), Pj::Str(a.category.as_str().into())),
                ("effect".into(), Pj::Str(a.effect.clone())),
                ("cost".into(), Pj::Str(a.cost.as_str().into())),
                ("reversible".into(), Pj::Bool(a.reversible)),
                ("auto_ok".into(), Pj::Bool(a.auto_ok)),
                // El score ya viene redondeado a 3 decimales por propose().
                ("score".into(), Pj::F64(redondear(p.score, 3))),
            ])
        })
        .collect();

    let mut payload = vec![
        ("elapsed_ms".to_string(), Pj::Raw("{{MS}}".to_string())),
        ("acciones".to_string(), Pj::Arr(items.clone())),
    ];
    let next_json = dumps(&Pj::Obj(payload.clone()));

    payload.push((
        "why_not".to_string(),
        Pj::Obj(
            why_not
                .iter()
                .map(|(id, razones)| {
                    (
                        id.clone(),
                        Pj::Arr(razones.iter().map(|r| Pj::Str(r.clone())).collect()),
                    )
                })
                .collect(),
        ),
    ));
    let why_not_json = dumps(&Pj::Obj(payload));

    // ── salida texto plano ──
    let mut texto = String::new();
    if propuestas.is_empty() {
        texto.push_str("✅ Nada pendiente — tu workspace está al día.\n");
    } else {
        texto.push_str(&format!(
            "🧠 Cortex · {} acción(es) sugeridas:\n\n",
            propuestas.len()
        ));
        for (i, p) in propuestas.iter().enumerate() {
            let a = by_id(&p.action_id);
            let auto = if a.auto_ok { " [auto-ok]" } else { "" };
            texto.push_str(&format!(" [{}] {}\n", i + 1, a.title));
            texto.push_str(&format!(
                "     id: {} · costo: {}{} · score: {}\n",
                a.id,
                a.cost.as_str(),
                auto,
                py_float(redondear(p.score, 3))
            ));
            texto.push_str(&format!("     efecto: {}\n\n", a.effect));
        }
    }
    texto.push_str(
        "\n[dim]{{MS}}ms · ejecutá `cortex next --json` para salida machine-readable[/dim]\n",
    );

    SalidaNext {
        stats: Some(stats),
        next_json,
        why_not_json,
        texto,
    }
}

fn asegurar_nl(s: &str) -> String {
    let t = s.strip_suffix('\n').unwrap_or(s);
    format!("{t}\n")
}

fn comparar(nombre: &str, obtenido: &str, esperado_path: &Path, fallas: &mut usize) {
    let Ok(esperado) = std::fs::read_to_string(esperado_path) else {
        fail(&format!("falta golden {}", esperado_path.display()));
    };
    if obtenido == esperado {
        println!("[PASS] {nombre}");
    } else {
        println!("[FAIL] {nombre} difiere ({})", esperado_path.display());
        println!("--- esperado ---\n{esperado}\n--- obtenido ---\n{obtenido}");
        *fallas += 1;
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        fail("uso: actions_check <fixtures_dir> <golden_dir>");
    }
    // Canonicalizar ANTES del chdir de los escenarios (checkpoint_now lee git
    // con cwd=fixture, igual que el oráculo).
    let fixtures = std::fs::canonicalize(&args[1]).expect("fixtures_dir");
    let golden_dir = std::fs::canonicalize(&args[2]).expect("golden_dir");

    let escenarios = ["base", "preferencias", "git-dirty", "sin-config"];
    let archivos = [
        "next_stats.json",
        "next_json.json",
        "next_why_not.json",
        "next_texto.txt",
    ];

    let mut fallas = 0usize;
    for escenario in escenarios {
        let fixture = fixtures.join(escenario);
        // El oráculo corre el CLI con cwd=fixture (checkpoint_now lee git ahí).
        std::env::set_current_dir(&fixture).expect("chdir fixture");
        let ruta_fixture = fixture.to_string_lossy().to_string();
        let salida = calcular_salida(&fixture);

        let norm = |t: String| t.replace(ruta_fixture.as_str(), "{{ROOT}}");

        let stats_val = salida
            .stats
            .clone()
            .unwrap_or_else(|| salida.next_json.clone());
        let valores: [String; 4] = [
            norm(stats_val),
            norm(salida.next_json.clone()),
            norm(salida.why_not_json.clone()),
            norm(salida.texto.clone()),
        ];
        for (fname, obtenido) in archivos.iter().zip(valores.iter()) {
            comparar(
                &format!("{escenario}/{fname}"),
                &asegurar_nl(obtenido),
                &golden_dir.join(escenario).join(fname),
                &mut fallas,
            );
        }
    }

    if fallas == 0 {
        println!("\nPARIDAD P6 COMPLETA ✅ (catálogo/scheduler/stats byte-a-byte)");
    } else {
        fail(&format!("{fallas} diferencias de paridad"));
    }
}
