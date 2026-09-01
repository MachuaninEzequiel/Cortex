//! Verificador de paridad P12A-4 — doc_generator + doc_validator + doc_verifier.
//!
//! Uso: p12a4_check <golden_dir>
//!
//! Reproduce los escenarios S01–S14 de bench/parity/p12a4_golden.py sobre los
//! portes cortex_app::{doc_generator,doc_validator,doc_verifier} + el PRService
//! extendido, comparando byte-a-byte contra golden_p12a4.txt.
//!
//! El reloj del generator es fijo (2026-06-01) igual que el monkeypatch del
//! oráculo; el mensaje de YAML inválido se normaliza a {{YAML_ERR}} en ambos
//! lados (depende del parser).

use std::process::exit;

use chrono::{TimeZone, Utc};
use cortex_app::doc_generator::DocGenerator;
use cortex_app::doc_validator::DocValidator;
use cortex_app::doc_verifier::DocVerifier;
use cortex_app::pr::PRContext;

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    exit(1);
}

/// `True`/`False` de Python.
fn py_bool(b: bool) -> &'static str {
    if b {
        "True"
    } else {
        "False"
    }
}

/// repr Python de lista de strings: ['a', 'b'] / [].
fn py_list(items: &[String]) -> String {
    format!(
        "[{}]",
        items
            .iter()
            .map(|s| format!("'{s}'"))
            .collect::<Vec<_>>()
            .join(", ")
    )
}

/// repr Python de un valor YAML escalar/secuencia (para properties).
fn py_repr_yaml(v: &serde_yaml::Value) -> String {
    match v {
        serde_yaml::Value::Null => "None".into(),
        serde_yaml::Value::Bool(b) => py_bool(*b).into(),
        serde_yaml::Value::Number(n) => n.to_string(),
        serde_yaml::Value::String(s) => format!("'{s}'"),
        serde_yaml::Value::Sequence(items) => {
            let inner: Vec<String> = items.iter().map(py_repr_yaml).collect();
            format!("[{}]", inner.join(", "))
        }
        other => format!("{other:?}"),
    }
}

fn fixed_now() -> chrono::DateTime<Utc> {
    Utc.with_ymd_and_hms(2026, 6, 1, 12, 0, 0).unwrap()
}

fn ctx_full() -> PRContext {
    PRContext {
        pr_number: 42,
        title: "Fix login bug".into(),
        body: "Cuerpo del PR con detalles.".into(),
        author: "dev1".into(),
        source_branch: "fix/login".into(),
        target_branch: "main".into(),
        commit_sha: "abc123def4567890".into(),
        files_changed: (0..25).map(|i| format!("f{i}.py")).collect(),
        diff_summary: " f0.py | 1 +\n 1 file changed".into(),
        labels: vec![
            "rag".into(),
            "backend".into(),
            "ci".into(),
            "x".into(),
            "y".into(),
            "z".into(),
        ],
        lint_result: Some("pass".into()),
        audit_result: Some("pass".into()),
        test_result: Some("pass".into()),
        ..Default::default()
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        fail("uso: p12a4_check <golden_dir>");
    }
    let gdir = std::fs::canonicalize(&args[1]).expect("golden_dir");

    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let work = std::env::temp_dir().join(format!("p12a4_work_{nanos}"));
    std::fs::create_dir_all(&work).expect("work");

    // Fixture vaultfix idéntico a construir_vault() del oráculo.
    let vaultfix = work.join("vaultfix");
    std::fs::create_dir_all(&vaultfix).expect("vaultfix");
    std::fs::write(
        vaultfix.join("ok.md"),
        "---\ntitle: Nota OK\ndate: '2026-05-01'\ntags: [a, b]\n---\nVéase [[otra]] y [[con display]] [[ancla#sec]] [[bloque^x]].\n![[embed-ok]] ![[ok2]]\n",
    )
    .unwrap();
    std::fs::write(
        vaultfix.join("embed-ok.md"),
        "---\ntitle: E\n---\ncontenido\n",
    )
    .unwrap();
    std::fs::write(vaultfix.join("ok2.md"), "---\ntitle: E2\n---\nx\n").unwrap();
    std::fs::write(
        vaultfix.join("broken.md"),
        "---\ntitle: Rota\n---\n![[no-existe]] y [[link-normal]]\n",
    )
    .unwrap();
    std::fs::write(vaultfix.join("nofm.md"), "solo texto\n").unwrap();
    std::fs::write(
        vaultfix.join("badyaml.md"),
        "---\ntitle: [unclosed\n---\ncuerpo\n",
    )
    .unwrap();
    std::fs::write(
        vaultfix.join("partial.md"),
        "---\ntags: [solo-tags]\n---\nx\n",
    )
    .unwrap();

    let mut bloques: Vec<String> = Vec::new();

    macro_rules! emitir {
        ($titulo:expr, $body:expr) => {{
            let resultado: Result<String, String> = ($body)();
            bloques.push(match resultado {
                Ok(salida) => format!("### {}\nrc=0\n{salida}", $titulo),
                Err(e) => format!("### {}\nrc=1\nException: {}", $titulo, e),
            });
        }};
    }

    let gen = DocGenerator::new(work.join("vault_out"));

    // S01 session completa
    emitir!("S01 session completa", || -> Result<String, String> {
        let doc = gen.generate_session(&ctx_full(), fixed_now());
        assert_eq!(
            doc.filename, "2026-06-01_fix-login-bug.md",
            "{}",
            doc.filename
        );
        Ok(format!("filename={}\n---\n{}", doc.filename, doc.content))
    });

    // S02 session vacía
    emitir!("S02 session vacía", || -> Result<String, String> {
        let ctx = PRContext {
            title: "T".into(),
            author: "a".into(),
            source_branch: "b".into(),
            commit_sha: "c".into(),
            ..Default::default()
        };
        let doc = gen.generate_session(&ctx, fixed_now());
        Ok(format!("filename={}\n---\n{}", doc.filename, doc.content))
    });

    // S03 safe_filename edges
    emitir!("S03 safe_filename edges", || -> Result<String, String> {
        Ok([
            gen.safe_filename("Fix login bug! @#$%", "2026-06-01"),
            gen.safe_filename("***", "2026-06-01"),
            gen.safe_filename("A B", "2026-06-01"),
        ]
        .join("\n"))
    });

    // S04 generate_all skip_types
    emitir!(
        "S04 generate_all skip_types",
        || -> Result<String, String> {
            let docs_all = gen.generate_all(&ctx_full(), fixed_now(), &[]);
            let docs_skip = gen.generate_all(&ctx_full(), fixed_now(), &["session"]);
            let tipos: Vec<String> = docs_all
                .iter()
                .map(|d| d.doc_type.value().to_string())
                .collect();
            let skip_tipos: Vec<String> = docs_skip
                .iter()
                .map(|d| d.doc_type.value().to_string())
                .collect();
            let filenames: Vec<String> = docs_all.iter().map(|d| d.filename.clone()).collect();
            Ok(format!(
                "all={}\nskip={}\nfilenames={}",
                py_list(&tipos),
                py_list(&skip_tipos),
                py_list(&filenames)
            ))
        }
    );

    // S05 write_docs archivos
    emitir!("S05 write_docs archivos", || -> Result<String, String> {
        let docs = gen.generate_all(&ctx_full(), fixed_now(), &[]);
        let written = gen.write_docs(&docs)?;
        let rels: Vec<String> = written
            .iter()
            .map(|p| p.strip_prefix(&work).unwrap().to_string_lossy().to_string())
            .collect();
        let no_vacios = written
            .iter()
            .all(|p| !std::fs::read_to_string(p).unwrap().trim().is_empty());
        Ok(format!(
            "rels={}\nno_vacios={}",
            py_list(&rels),
            py_bool(no_vacios)
        ))
    });

    let val = DocValidator::new(&vaultfix);

    fn issues_breve(result: &cortex_app::doc_validator::DocValidationResult) -> String {
        result
            .issues
            .iter()
            .map(|i| format!("{}|{}|{}", i.severity.value(), i.field, i.message))
            .collect::<Vec<_>>()
            .join("; ")
    }

    // S06 validate inexistente
    emitir!("S06 validate inexistente", || -> Result<String, String> {
        let r = val.validate_file(&vaultfix.join("fantasma.md"));
        Ok(format!(
            "is_valid={}\n{}",
            py_bool(r.is_valid),
            issues_breve(&r)
        ))
    });

    // S07 sin frontmatter
    emitir!("S07 sin frontmatter", || -> Result<String, String> {
        let r = val.validate_file(&vaultfix.join("nofm.md"));
        Ok(format!(
            "is_valid={}\n{}",
            py_bool(r.is_valid),
            issues_breve(&r)
        ))
    });

    // S08 nota válida
    emitir!("S08 nota válida", || -> Result<String, String> {
        let r = val.validate_file(&vaultfix.join("ok.md"));
        let claves: Vec<String> = r.properties.keys().cloned().collect();
        let title = r
            .properties
            .get("title")
            .map(|v| match v {
                serde_yaml::Value::String(s) => s.clone(),
                other => py_repr_yaml(other),
            })
            .unwrap_or_else(|| "None".into());
        let tags = r
            .properties
            .get("tags")
            .map(py_repr_yaml)
            .unwrap_or_else(|| "None".into());
        let mut wikilinks = r.wikilinks.clone();
        wikilinks.sort();
        let mut embeds = r.embeds.clone();
        embeds.sort();
        Ok(format!(
            "is_valid={}\nprops_keys={}\ntitle={title}\ntags={tags}\nwikilinks={}\nembeds={}\nerrors={} warnings={}",
            py_bool(r.is_valid),
            py_list(&claves),
            py_list(&wikilinks),
            py_list(&embeds),
            r.errors().len(),
            r.warnings().len()
        ))
    });

    // S09 embed roto
    emitir!("S09 embed roto", || -> Result<String, String> {
        let r = val.validate_file(&vaultfix.join("broken.md"));
        let mut wikilinks = r.wikilinks.clone();
        wikilinks.sort();
        let mut embeds = r.embeds.clone();
        embeds.sort();
        Ok(format!(
            "is_valid={}\nwikilinks={}\nembeds={}\n{}",
            py_bool(r.is_valid),
            py_list(&wikilinks),
            py_list(&embeds),
            issues_breve(&r)
        ))
    });

    // S10 yaml inválido
    emitir!("S10 yaml inválido", || -> Result<String, String> {
        let r = val.validate_file(&vaultfix.join("badyaml.md"));
        let breve = r
            .issues
            .iter()
            .map(|i| {
                let msg = if i.message.starts_with("Invalid YAML") {
                    "{{YAML_ERR}}"
                } else {
                    &i.message
                };
                format!("{}|{}|{}", i.severity.value(), i.field, msg)
            })
            .collect::<Vec<_>>()
            .join("; ");
        Ok(format!("is_valid={}\n{}", py_bool(r.is_valid), breve))
    });

    // S11 fm parcial
    emitir!("S11 fm parcial", || -> Result<String, String> {
        let r = val.validate_file(&vaultfix.join("partial.md"));
        Ok(format!(
            "is_valid={}\n{}",
            py_bool(r.is_valid),
            issues_breve(&r)
        ))
    });

    // S12 verifier from_list
    emitir!("S12 verifier from_list", || -> Result<String, String> {
        let ver = DocVerifier::with_root(&vaultfix, Some(work.clone()));
        let files: Vec<String> = vec![
            "vaultfix/nuevo.md".into(),
            "vaultfix/editado.md".into(),
            "vaultfix/borrado.md".into(),
            "vaultfix/nota.txt".into(),
            "fuera/f.md".into(),
            "vaultfix/".into(),
        ];
        let r = ver.verify_from_list(&files);
        Ok(r.to_json())
    });

    // S13 verifier git nonrepo
    emitir!("S13 verifier git nonrepo", || -> Result<String, String> {
        let previo = std::env::current_dir().unwrap();
        std::env::set_current_dir(&work).unwrap();
        let ver = DocVerifier::with_root(&vaultfix, Some(work.clone()));
        let r = ver.verify_from_diff("main", None);
        std::env::set_current_dir(previo).ok();
        Ok(r.to_json())
    });

    // S14 verifier vault fuera
    emitir!("S14 verifier vault fuera", || -> Result<String, String> {
        // vault RELATIVO no bajo root ⇒ strip_prefix falla ⇒ error.
        let ver = DocVerifier::with_root("elsewhere/vault", Some(work.clone()));
        let r = ver.verify_from_list(&["x.md".to_string()]);
        Ok(r.to_json())
    });

    // Normalización idéntica al oráculo.
    let crudo = bloques.join("");
    let ruta = work.to_string_lossy().to_string();
    let mut normalizado = crudo.replace(ruta.as_str(), "{{ROOT}}");
    if !normalizado.ends_with('\n') {
        normalizado.push('\n');
    }

    let esperado = std::fs::read_to_string(gdir.join("golden_p12a4.txt"))
        .unwrap_or_else(|e| fail(&format!("falta golden: {e}")));
    if normalizado == esperado {
        println!("[PASS] golden_p12a4.txt");
        println!("\nPARIDAD P12A-4 COMPLETA ✅ (doc_generator + validator + verifier)");
    } else {
        println!("[FAIL] golden_p12a4.txt difiere");
        let mut n = 0usize;
        for (l1, l2) in esperado.lines().zip(normalizado.lines()) {
            if l1 != l2 {
                println!("  py:   {l1}\n  rust: {l2}");
                n += 1;
                if n > 20 {
                    break;
                }
            }
        }
        fail("diferencias de paridad");
    }
    std::fs::remove_dir_all(&work).ok();
}
