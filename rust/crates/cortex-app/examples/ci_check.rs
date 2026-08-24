//! Verificador de paridad P11-ci — plugin CI nativo vs oráculo Python.
//!
//! Uso: ci_check <fixtures_dir> <golden_dir>
//!
//! Reconstruye la secuencia completa del oráculo (`bench/parity/
//! ci_golden_p11.py`) sobre las nativas session (P4 + service P11),
//! documenter (P5) y verification: valida 10 escenarios de `validate-pr`
//! en los tres formatos y el flujo Level-3 de review-sessions, normaliza
//! igual ({{ROOT}}, {{MS}}, {{DUR}}, {{DATE}}) y compara byte-a-byte contra
//! el golden commiteado.

use std::path::{Path, PathBuf};

use cortex_app::ci::markdown_formatter::render_pr_comment;
use cortex_app::ci::result::{ValidationInput, ValidationResult};
use cortex_app::ci::{
    close_review_session, open_review_session, read_diff_from_args, report_ci_checkpoint,
    validate_pull_request,
};
use cortex_app::session::service::SessionService;
use cortex_app::session::verification::VerificationRunner;
use cortex_app::session::{SessionStatus, SessionStorage};

fn fail(msg: &str) -> ! {
    eprintln!("❌ {msg}");
    std::process::exit(1);
}

// ── utilidades ──────────────────────────────────────────────────────────────

/// Copia recursiva (el fixture es chico; sin dependencias extra).
fn copy_dir(src: &Path, dst: &Path) {
    std::fs::create_dir_all(dst).unwrap();
    for entry in std::fs::read_dir(src).unwrap() {
        let e = entry.unwrap();
        let ty = e.file_type().unwrap();
        let to = dst.join(e.file_name());
        if ty.is_dir() {
            copy_dir(&e.path(), &to);
        } else {
            std::fs::copy(e.path(), &to).unwrap();
        }
    }
}

/// Emisión JSON compacta estilo `json.dumps` default (", " / ": ").
fn pj_compact_kv(pairs: &[(&str, String)]) -> String {
    let body: Vec<String> = pairs.iter().map(|(k, v)| format!("{k:?}: {v}")).collect();
    format!("{{{}}}", body.join(", "))
}

struct Ctx {
    work: PathBuf, // copia mutante del fixture
    head2: String,
    ids: std::collections::HashMap<&'static str, String>,
    bloques: Vec<String>,
}

impl Ctx {
    fn sessions_dir(&self) -> PathBuf {
        self.work.join(".cortex").join("sessions")
    }
    fn service(&self) -> SessionService {
        SessionService::new(SessionStorage::new(self.sessions_dir()), &self.work)
    }

    fn diff_file(&self, name: &str, content: &str) -> PathBuf {
        let p = self.work.join(name);
        std::fs::write(&p, content).unwrap();
        p
    }

    /// Espejo del comando `cortex validate-pr --format …`.
    fn validate_pr(
        &mut self,
        titulo: &str,
        diff: Option<&Path>,
        base_commit: Option<&str>,
        head_branch: Option<&str>,
        session: Option<&str>,
        fmt: &str,
    ) -> i32 {
        let repo_root = self.work.clone();
        let diff_text = match read_diff_from_args(diff, base_commit, None, &repo_root) {
            Ok(t) => t,
            Err(e) => {
                eprintln!("✗ {e}");
                return 3;
            }
        };
        let payload = ValidationInput {
            diff_text,
            repo_root: repo_root.clone(),
            base_commit: base_commit.map(str::to_string),
            head_commit: None,
            base_branch: None,
            head_branch: head_branch.map(str::to_string),
            pr_number: None,
            pr_author: None,
            explicit_session_id: session.map(str::to_string),
        };
        let result = validate_pull_request(
            &payload,
            self.service(),
            VerificationRunner::new(repo_root.clone()),
        );
        // json y pr-comment se emiten vía typer.echo ⇒ un \n extra al final;
        // el formato text usa sólo console.print (cada línea ya trae su \n).
        let salida = match fmt {
            "json" => {
                let mut s = result.to_json_string();
                s.push('\n');
                s
            }
            "pr-comment" => {
                let mut s = render_pr_comment(&result, "<!-- cortex-pr-summary -->");
                s.push('\n');
                s
            }
            _ => format_texto(&result),
        };
        self.bloques
            .push(format!("### {titulo} · rc={}\n{salida}", result.exit_code));
        result.exit_code
    }

    fn open_review_session(
        &mut self,
        tag: &'static str,
        titulo: &str,
        pr_number: Option<i64>,
        base_commit: &str,
        head_branch: &str,
        json_out: bool,
    ) -> i32 {
        let today = chrono::Utc::now().format("%Y-%m-%d");
        let suffix = match pr_number {
            Some(n) => format!("pr-{n}-review"),
            None => format!("{}-review", head_branch.replace('/', "-").to_lowercase()),
        };
        let spec_id = format!("{today}_{suffix}");
        let record = open_review_session(
            &self.service(),
            &spec_id,
            base_commit,
            head_branch,
            pr_number,
            None,
        )
        .unwrap_or_else(|e| fail(&e));
        self.ids.insert(tag, record.session_id.clone());
        let salida = if json_out {
            pj_compact_kv(&[
                ("session_id", format!("{:?}", record.session_id)),
                ("status", format!("{:?}", record.status.as_str())),
            ])
        } else {
            record.session_id.clone()
        };
        self.bloques
            .push(format!("### {titulo} · rc=0\n{salida}\n"));
        0
    }

    #[allow(clippy::too_many_arguments)]
    fn report_checkpoint(
        &mut self,
        tag: &str,
        titulo: &str,
        from_validation: Option<&str>,
        manual_claims: &[&str],
        manual_artifacts: &[&str],
        note: &str,
        json_out: bool,
    ) -> i32 {
        let payload = from_validation.map(|p| {
            serde_json::from_str::<serde_json::Value>(
                &std::fs::read_to_string(self.work.join(p)).unwrap_or_default(),
            )
            .unwrap_or(serde_json::Value::Null)
        });
        let claims: Vec<String> = manual_claims.iter().map(|s| s.to_string()).collect();
        let artifacts: Vec<String> = manual_artifacts.iter().map(|s| s.to_string()).collect();
        match report_ci_checkpoint(
            &self.service(),
            &self.ids[tag],
            if payload.is_none() || payload.as_ref() == Some(&serde_json::Value::Null) {
                None
            } else {
                payload.as_ref()
            },
            &claims,
            &artifacts,
            note,
        ) {
            Ok(record) => {
                let salida = if json_out {
                    pj_compact_kv(&[
                        ("session_id", format!("{:?}", record.session_id)),
                        ("checkpoint_count", format!("{}", record.checkpoints.len())),
                    ])
                } else {
                    format!("checkpoint emitted; total={}", record.checkpoints.len())
                };
                self.bloques
                    .push(format!("### {titulo} · rc=0\n{salida}\n"));
                0
            }
            Err(_) => {
                // Error de carga del archivo de validación ⇒ exit 3 con
                // mensaje a stderr (no entra al golden).
                eprintln!("✗ could not load --from-validation-result");
                self.bloques.push(format!("### {titulo} · rc=3\n"));
                3
            }
        }
    }

    fn close_review_session_cmd(
        &mut self,
        tag: &str,
        titulo: &str,
        status: SessionStatus,
        reason: &str,
        json_out: bool,
    ) -> i32 {
        match close_review_session(&self.service(), &self.ids[tag], status, reason) {
            Ok(record) => {
                let salida = if json_out {
                    pj_compact_kv(&[
                        ("session_id", format!("{:?}", record.session_id)),
                        ("status", format!("{:?}", record.status.as_str())),
                        ("mode", format!("{:?}", mode_str(record.mode))),
                    ])
                } else {
                    format!(
                        "{} → {} (mode={})",
                        record.session_id,
                        record.status.as_str(),
                        mode_str(record.mode)
                    )
                };
                self.bloques
                    .push(format!("### {titulo} · rc=0\n{salida}\n"));
                0
            }
            Err(e) => {
                eprintln!("✗ {e}");
                3
            }
        }
    }
}

fn mode_str(m: cortex_app::session::SessionMode) -> &'static str {
    use cortex_app::session::SessionMode as M;
    match m {
        M::Unknown => "unknown",
        M::Managed => "managed",
        M::Observed => "observed",
        M::Byo => "byo",
        M::CiReview => "ci-review",
    }
}

/// Espejo del bloque `text` de `_emit` del CLI Python.
///
/// Rich Console (no-tty) imprime sin markup ni ANSI; las líneas largas del
/// fixture no superan el ancho default de wrap (80 columnas).
fn format_texto(r: &ValidationResult) -> String {
    let mut out = String::new();
    out.push_str(&format!("{}\n", r.summary_text));
    if let Some(s) = &r.matched_session {
        out.push_str(&format!("  session: {}\n", s.session_id));
    }
    out.push_str(&format!("  status:  {}\n", r.status.as_str()));
    for w in &r.warnings {
        out.push_str(&format!("  warn: {w}\n"));
    }
    for b in &r.blockers {
        out.push_str(&format!("  block: {b}\n"));
    }
    out
}

const DIFF_IN_SCOPE: &str = "--- a/src/x.py\n+++ b/src/x.py\n@@ -1 +1,2 @@\n x\n+new\n";
const DIFF_OUT_SCOPE: &str = concat!(
    "--- a/src/x.py\n+++ b/src/x.py\n@@ -1 +1,2 @@\n x\n+new\n",
    "--- a/src/unexpected.py\n+++ b/src/unexpected.py\n@@\n"
);
const DIFF_OTHER: &str = "--- a/src/other.py\n+++ b/src/other.py\n@@\n";

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        fail("uso: ci_check <fixtures_dir> <golden_dir>");
    }
    let fixtures = std::fs::canonicalize(&args[1]).expect("fixtures_dir");
    let golden_dir = std::fs::canonicalize(&args[2]).expect("golden_dir");

    // Copia mutante del fixture pristine (el flujo review-session escribe).
    let tmpbase = std::env::temp_dir().join(format!(
        "cortex-ci-check-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    copy_dir(&fixtures, &tmpbase);
    let work = std::fs::canonicalize(tmpbase.join("proyecto")).expect("proyecto");

    let head2 = {
        let mf = work.join(".cortex").join("p11_manifest.json");
        let v: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(&mf).unwrap()).unwrap();
        v["head2"].as_str().unwrap().to_string()
    };

    let mut ctx = Ctx {
        work: work.clone(),
        head2,
        ids: Default::default(),
        bloques: Vec::new(),
    };

    // JSON crudo de S06 para --from-validation-result (igual que el oráculo:
    // se genera ANTES de la secuencia y su bloque no entra al golden).
    let d_in0 = ctx.diff_file("in.diff", DIFF_IN_SCOPE);
    {
        let payload = ValidationInput {
            diff_text: std::fs::read_to_string(&d_in0).unwrap(),
            repo_root: work.clone(),
            explicit_session_id: Some("2026-05-13_optfail".into()),
            ..Default::default()
        };
        let result = validate_pull_request(
            &payload,
            ctx.service(),
            VerificationRunner::new(work.clone()),
        );
        assert_eq!(result.exit_code, 1, "escenario semilla debía warn");
        std::fs::write(
            work.join("validation_optfail.json"),
            result.to_json_string(),
        )
        .unwrap();
    }

    let d_in = d_in0;
    let d_out = ctx.diff_file("out.diff", DIFF_OUT_SCOPE);
    let d_other = ctx.diff_file("other.diff", DIFF_OTHER);

    ctx.validate_pr(
        "S01 validate-pr explicit pass (json)",
        Some(&d_in),
        None,
        None,
        Some("2026-05-14_demo"),
        "json",
    );
    ctx.validate_pr(
        "S02 validate-pr no-match blocked (json)",
        Some(&d_in),
        None,
        None,
        None,
        "json",
    );
    ctx.validate_pr(
        "S03 validate-pr out-of-scope warn (json)",
        Some(&d_out),
        None,
        None,
        Some("2026-05-14_demo"),
        "json",
    );
    ctx.validate_pr(
        "S04 validate-pr unimplemented blocked (json)",
        Some(&d_other),
        None,
        None,
        Some("2026-05-14_demo"),
        "json",
    );
    ctx.validate_pr(
        "S05 validate-pr required-hook-fail blocked (json)",
        Some(&d_in),
        None,
        None,
        Some("2026-05-12_hookfail"),
        "json",
    );
    ctx.validate_pr(
        "S06 validate-pr optional-hook-fail warn (json)",
        Some(&d_in),
        None,
        None,
        Some("2026-05-13_optfail"),
        "json",
    );
    ctx.validate_pr(
        "S07 validate-pr handoff warn (json)",
        Some(&d_in),
        None,
        None,
        Some("2026-05-11_handoff"),
        "json",
    );
    ctx.validate_pr(
        "S08 validate-pr abandoned blocked (json)",
        Some(&d_in),
        None,
        None,
        Some("2026-05-10_abandoned"),
        "json",
    );
    ctx.validate_pr(
        "S09 validate-pr by_branch pass (json)",
        Some(&d_in),
        None,
        Some("feature/x"),
        None,
        "json",
    );
    let h2 = ctx.head2.clone();
    ctx.validate_pr(
        "S10 validate-pr by_commit->abandoned blocked (json)",
        Some(&d_in),
        Some(&h2),
        None,
        None,
        "json",
    );
    ctx.validate_pr(
        "S11 validate-pr out-of-scope warn (text)",
        Some(&d_out),
        None,
        None,
        Some("2026-05-14_demo"),
        "text",
    );
    ctx.validate_pr(
        "S12 validate-pr pass (pr-comment)",
        Some(&d_in),
        None,
        None,
        Some("2026-05-14_demo"),
        "pr-comment",
    );
    ctx.validate_pr(
        "S13 validate-pr no-match (pr-comment)",
        Some(&d_in),
        None,
        None,
        None,
        "pr-comment",
    );

    ctx.open_review_session(
        "rs1",
        "S14 open-review-session pr42 (json)",
        Some(42),
        &"a".repeat(40),
        "feature/ci",
        true,
    );
    ctx.report_checkpoint(
        "rs1",
        "S15 report-checkpoint manual (json)",
        None,
        &["manual claim"],
        &["src/x.py"],
        "initial review",
        true,
    );
    ctx.report_checkpoint(
        "rs1",
        "S16 report-checkpoint from-validation (json)",
        Some("validation_optfail.json"),
        &[],
        &[],
        "",
        true,
    );
    ctx.close_review_session_cmd(
        "rs1",
        "S17 close-review-session closed (json)",
        SessionStatus::Closed,
        "",
        true,
    );
    ctx.open_review_session(
        "rs2",
        "S18 open-review-session branch (texto)",
        None,
        &"b".repeat(40),
        "feature/ci",
        false,
    );
    ctx.report_checkpoint(
        "rs2",
        "S19 report-checkpoint from-validation (texto)",
        Some("validation_optfail.json"),
        &[],
        &[],
        "",
        false,
    );
    ctx.close_review_session_cmd(
        "rs2",
        "S20 close-review-session handoff reason (texto)",
        SessionStatus::Handoff,
        "hooks failed",
        false,
    );
    ctx.open_review_session(
        "rs3",
        "S21 open-review-session pr7 (json)",
        Some(7),
        &"c".repeat(40),
        "feature/cr",
        true,
    );
    ctx.report_checkpoint(
        "rs3",
        "S22 report-checkpoint from-validation (json)",
        Some("validation_optfail.json"),
        &[],
        &[],
        "",
        true,
    );
    ctx.close_review_session_cmd(
        "rs3",
        "S23 close-review-session closed ci-review (json)",
        SessionStatus::Closed,
        "",
        true,
    );

    // ── normalización idéntica al oráculo ──
    let raw = ctx.bloques.concat();
    let work_prefix = format!("{}", work.display());
    let mut texto = raw.replace(&work_prefix, "{{ROOT}}");
    // "duration_ms": N → "{{MS}}" (el oráculo cita el placeholder)
    let mut search_from = 0;
    while let Some(rel) = texto[search_from..].find("\"duration_ms\": ") {
        let pos = search_from + rel;
        let start = pos + "\"duration_ms\": ".len();
        let digits: String = texto[start..]
            .chars()
            .take_while(|c| c.is_ascii_digit())
            .collect();
        if digits.is_empty() {
            search_from = start;
            continue;
        }
        texto.replace_range(start..start + digits.len(), "\"{{MS}}\"");
        search_from = start + 8;
    }
    // (X.Xs, → ({{DUR}}s,
    {
        let re_dur = |t: &str| -> Option<(usize, usize)> {
            let b = t.as_bytes();
            let mut i = 0;
            while i + 6 < b.len() {
                if b[i] == b'('
                    && b[i + 1].is_ascii_digit()
                    && b[i + 2] == b'.'
                    && b[i + 3].is_ascii_digit()
                    && b[i + 4] == b's'
                    && b[i + 5] == b','
                {
                    return Some((i + 1, i + 4));
                }
                i += 1;
            }
            None
        };
        while let Some((a, z)) = re_dur(&texto) {
            texto.replace_range(a..z, "{{DUR}}");
        }
    }
    // YYYY-MM-DD_(…-review) → {{DATE}}_
    {
        let bytes = texto.as_bytes();
        let mut cuts: Vec<(usize, usize)> = Vec::new();
        let mut i = 0;
        while i + 10 < bytes.len() {
            let fecha_ok = bytes[i..i + 4].iter().all(|c| c.is_ascii_digit())
                && bytes[i + 4] == b'-'
                && bytes[i + 5..i + 7].iter().all(|c| c.is_ascii_digit())
                && bytes[i + 7] == b'-'
                && bytes[i + 8..i + 10].iter().all(|c| c.is_ascii_digit())
                && bytes[i + 10] == b'_';
            if fecha_ok {
                // mirar si sigue <slug>-review como palabra
                let rest = &texto[i + 11..];
                let slug_end = rest
                    .find(|c: char| !(c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-'))
                    .unwrap_or(rest.len());
                let slug = &rest[..slug_end];
                if slug.ends_with("-review") && !slug.starts_with('-') {
                    cuts.push((i, i + 10));
                    i += 11 + slug.len();
                    continue;
                }
            }
            i += 1;
        }
        for (a, z) in cuts.into_iter().rev() {
            texto.replace_range(a..z, "{{DATE}}");
        }
    }

    let golden_path = golden_dir.join("golden_ci.txt");
    let esperado = std::fs::read_to_string(&golden_path)
        .unwrap_or_else(|e| fail(&format!("falta golden {}: {e}", golden_path.display())));

    if texto == esperado {
        println!("\nPARIDAD P11-CI COMPLETA ✅ (comandos `cortex ci` idénticos al oráculo)");
    } else {
        let esperado_l: Vec<&str> = esperado.lines().collect();
        let obtenido_l: Vec<&str> = texto.lines().collect();
        let mut diffs = 0;
        for (n, (e, o)) in esperado_l.iter().zip(obtenido_l.iter()).enumerate() {
            if e != o {
                println!("línea {}:\n  esp: {e:?}\n  obt: {o:?}", n + 1);
                diffs += 1;
                if diffs > 12 {
                    break;
                }
            }
        }
        if esperado_l.len() != obtenido_l.len() {
            println!(
                "largo distinto: esperado {} vs obtenido {}",
                esperado_l.len(),
                obtenido_l.len()
            );
        }
        fail("diferencias de paridad");
    }

    let _ = std::fs::remove_dir_all(&tmpbase);
}
