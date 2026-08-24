//! Verificador P5c: kwargs de create() + render de la nota (minijinja).
//!
//! Uso: persister_check <golden_dir> <templates_dir>

use std::path::{Path, PathBuf};

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    std::process::exit(1);
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        fail("uso: persister_check <golden_dir> <templates_dir>");
    }
    let gdir = Path::new(&args[1]);
    let tdir = Path::new(&args[2]);

    let yml = std::fs::read_to_string(gdir.join("session.yaml")).expect("session.yaml");
    let record: cortex_app::session::SessionRecord =
        serde_yaml::from_str(&yml).expect("session.yaml inválido");
    record.validate().expect("session no valida");

    let spec_copy = gdir.join("spec_copy.md");
    let mut spec = cortex_app::documenter::spec_loader::load_spec(&spec_copy);
    spec.path = PathBuf::from(format!(
        "{{{{ROOT}}}}/specs/{}",
        spec_copy.file_name().unwrap().to_string_lossy()
    ));

    let out = cortex_app::documenter::reconstruct_gitless(&record, &spec, vec![])
        .unwrap_or_else(|e| fail(&format!("reconstruct: {e}")));
    let (create_args, _warnings) = cortex_app::documenter::persister::build_create_args(&out);

    // ── Kwargs (sort_keys como el oráculo) ──
    let got_value = serde_json::to_value(&create_args).expect("serialize");
    // Re-serializar con sort_keys: BTreeMap ordena; usamos Value→sorted.
    let sorted = sort_json(got_value.clone());
    let got_sorted = serde_json::to_string_pretty(&sorted).unwrap() + "\n";

    let golden_args_text = std::fs::read_to_string(gdir.join("create_args.json")).unwrap();
    if got_sorted != golden_args_text {
        eprintln!("--- rust(sorted) ---\n{got_sorted}\n--- golden ---\n{golden_args_text}");
        fail("create_args difiere");
    }
    println!(
        "✅ create_args idénticos ({} campos)",
        count_leaves(&sorted)
    );

    // ── Render de la nota vía minijinja ──
    let template_src = std::fs::read_to_string(tdir.join("session.md.j2")).expect("template");
    let mut env = minijinja::Environment::new();
    // Misma configuración que templates_engine.py.
    env.set_trim_blocks(true);
    env.set_lstrip_blocks(true);
    env.set_keep_trailing_newline(true);
    env.add_template("session.md.j2", &template_src)
        .expect("template parsea");
    let ctx = minijinja::Value::from_serialize(&got_value);
    let body = env
        .get_template("session.md.j2")
        .expect("tpl")
        .render(ctx)
        .expect("render");

    let golden_body = std::fs::read_to_string(gdir.join("note_body.md")).expect("body");
    if body == golden_body {
        println!("✅ note_body byte-a-byte idéntico (jinja2 ↔ minijinja)");
    } else {
        // Diagnóstico: primera línea que difiere.
        for (i, (a, b)) in body.lines().zip(golden_body.lines()).enumerate() {
            if a != b {
                fail(&format!(
                    "body difiere en línea {}: rust={a:?} py={b:?}",
                    i + 1
                ));
            }
        }
        fail(&format!(
            "body difiere en longitud: rust={} py={}",
            body.lines().count(),
            golden_body.lines().count()
        ));
    }

    println!("\nPARIDAD PERSISTER COMPLETA");
}

fn sort_json(v: serde_json::Value) -> serde_json::Value {
    match v {
        serde_json::Value::Object(m) => {
            let mut keys: Vec<&String> = m.keys().collect();
            keys.sort();
            let mut out = serde_json::Map::new();
            for k in keys {
                out.insert(k.clone(), sort_json(m[k].clone()));
            }
            serde_json::Value::Object(out)
        }
        serde_json::Value::Array(a) => {
            serde_json::Value::Array(a.into_iter().map(sort_json).collect())
        }
        other => other,
    }
}

fn count_leaves(v: &serde_json::Value) -> usize {
    match v {
        serde_json::Value::Object(m) => m.len(),
        serde_json::Value::Array(_) => v.as_array().map(|a| a.len()).unwrap_or(0),
        _ => 1,
    }
}
