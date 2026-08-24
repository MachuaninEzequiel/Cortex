//! Verificador P4-fin: VerificationRunner + quality_gates en Rust vs oráculo.
//!
//! Uso: verification_check <golden_dir>
//! Normaliza duration_ms→{{D}} y run_at→{{TS}} antes de comparar.

use std::path::Path;

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    std::process::exit(1);
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        fail("uso: verification_check <golden_dir>");
    }
    let gdir = Path::new(&args[1]);

    let runner = cortex_app::session::verification::VerificationRunner::new(gdir.to_path_buf());

    // Mismos casos que el oráculo (bench/parity/verification_golden.py).
    let hooks = [
        ("ok", "echo hola-verificacion", 10u64),
        ("falla", "echo detalle-error >&2; exit 3", 10),
        ("solo-stderr", "echo solo-errores >&2", 10),
        ("timeout", "sleep 5", 1),
        ("truncado", "python3 -c \"print('x'*12000, end='')\"", 15),
    ];

    let golden_text =
        std::fs::read_to_string(gdir.join("verification_results.json")).expect("golden v");
    let golden: serde_json::Value = serde_json::from_str(&golden_text).expect("json");

    for (i, (name, command, timeout)) in hooks.iter().enumerate() {
        let hook = cortex_app::session::VerificationHook {
            name: name.to_string(),
            command: command.to_string(),
            required: true,
            success_criteria: "exit code 0".into(),
            timeout_seconds: *timeout,
        };
        let r = runner.run_hook(&hook);
        let gcase = &golden.as_array().unwrap()[i];

        let norm = |v: &serde_json::Value| -> serde_json::Value {
            let mut o = v.clone();
            if let Some(obj) = o.as_object_mut() {
                obj.insert("duration_ms".into(), "{{D}}".into());
                obj.insert("run_at".into(), "{{TS}}".into());
            }
            o
        };
        let got = norm(&serde_json::to_value(&r).unwrap());
        let want = norm(gcase);
        if got != want {
            eprintln!("rust : {got}");
            eprintln!("py   : {want}");
            fail(&format!("verification hook '{name}' difiere"));
        }
        println!(
            "✅ hook '{}' idéntico (exit={} passed={})",
            name, r.exit_code, r.passed
        );
    }

    // ── Quality gates ──
    use cortex_app::session::{quality_gates, Checkpoint, CheckpointSource};
    let ts = "2026-08-24T00:00:00+00:00";
    let cp = |verified: &[&str], artifacts: &[&str], note: &str| {
        let r = Checkpoint {
            timestamp: ts.into(),
            source: CheckpointSource::Manual,
            verified_claims: verified.iter().map(|s| s.to_string()).collect(),
            unverified_claims: vec![],
            artifacts_touched: artifacts.iter().map(|s| s.to_string()).collect(),
            note: note.into(),
        };
        r
    };
    let casos: Vec<(&str, Checkpoint, Vec<&str>)> = vec![
        (
            "accept_ok",
            cp(&["tests pasan correctamente"], &["src/a.py"], ""),
            vec!["src/a.py"],
        ),
        (
            "redelegate_scope",
            cp(&["algo"], &["src/fuera.py"], ""),
            vec!["src/otro.py"],
        ),
        (
            "process_artifact_ok",
            cp(&["diseño listo"], &[".cortex/vault/designs/d.md"], ""),
            vec!["src/b.py"],
        ),
        ("sin_senal", cp(&[], &[], ""), vec![]),
        (
            "placeholder_note",
            cp(&["tests ok"], &["src/a.py"], "pendiente TBD"),
            vec![],
        ),
        (
            "claim_corto",
            cp(&["tests"], &["src/a.py"], ""),
            vec!["src/a.py"],
        ),
    ];

    let gates_text = std::fs::read_to_string(gdir.join("quality_gates.json")).expect("golden q");
    let golden_gates: serde_json::Value = serde_json::from_str(&gates_text).expect("json");

    for (i, (nombre, checkpoint, scope)) in casos.iter().enumerate() {
        let scope_owned: Vec<String> = scope.iter().map(|s| s.to_string()).collect();
        let verdict = quality_gates::review_checkpoint(checkpoint, &scope_owned);
        let got = serde_json::to_value(&verdict).unwrap();
        // El oráculo agrega 'caso' como etiqueta; se excluye de la comparación.
        let mut want = golden_gates.as_array().unwrap()[i].clone();
        if let Some(obj) = want.as_object_mut() {
            obj.remove("caso");
        }
        if got != want {
            eprintln!("rust : {got}\npy   : {want}");
            fail(&format!("quality gate caso '{nombre}' difiere"));
        }
        println!("✅ gate '{}' → {}", nombre, got["action"].as_str().unwrap());
    }

    println!("\nPARIDAD VERIFICATION+GATES COMPLETA");
}
