//! Gate P12B-8 — replay nativo de `golden_cli.txt`.
//!
//! Reproduce los casos del gate invocando el binario `cortex-cli` con las
//! mismas recetas de fixture y normaliza {{ROOT}}/{{TS}}/{{FP}} idéntico al
//! oráculo Python (`cli_golden_p12b.py`); luego compara cada segmento.
//!
//! Uso (tras el build del golden):
//!     .venv/bin/python bench/parity/archive/cli_golden_p12b.py build
//!     cargo run -p cortex-cli --example cli_check -- ../../bench/parity/archive/.p12b-cli
//!
//! Los textos self-golden (--help, errores clap, tutor slug) viven en
//! `tests/cli_self_golden.rs`; acá se valida la paridad funcional.

use std::path::{Path, PathBuf};
use std::process::Command;

use tempfile::TempDir;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let golden_dir = args
        .get(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("../../bench/parity/archive/.p12b-cli"));
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let bin = manifest.join("../../target/debug/cortex-cli");
    let py_bin = manifest.join("../../../.venv/bin/cortex");

    let python_bin = manifest.join("../../../.venv/bin/python");
    let golden_path = golden_dir.join("golden_cli.txt");
    if !golden_path.exists() {
        eprintln!(
            "[FAIL] golden ausente: {} (corré primero cli_golden_p12b.py build)",
            golden_path.display()
        );
        std::process::exit(1);
    }
    let golden = std::fs::read_to_string(&golden_path).unwrap();

    // Segmentos: "### nombre [PASS] ...\n<contenido hasta próximo ###>"
    let mut segments = std::collections::HashMap::new();
    let mut current: Option<(String, Vec<String>)> = None;
    for line in golden.lines() {
        if let Some(rest) = line.strip_prefix("### ") {
            if let Some((name, buf)) = current.take() {
                segments.insert(name, buf);
            }
            let name = rest.split(' ').next().unwrap_or("").to_string();
            current = Some((name, Vec::new()));
        } else if let Some((_, buf)) = current.as_mut() {
            buf.push(line.to_string());
        }
    }
    if let Some((name, buf)) = current.take() {
        segments.insert(name, buf);
    }
    if segments.is_empty() {
        eprintln!("[FAIL] golden sin segmentos");
        std::process::exit(1);
    }

    let work = TempDir::new().unwrap();
    let mut failures: Vec<String> = Vec::new();
    let total = segments.len();
    // El orden de all_cases() está congelado en el oráculo; el replay usa los
    // nombres de segmento como fuente de verdad.
    for name in [
        "s01_hint_l0",
        "s02_hint_l1",
        "s03_hint_l7",
        "s05_doctor_empty",
        "s06_doctor_all_org",
        "s07_doctor_strict",
        "s08_orgconfig_text",
        "s09_orgconfig_json",
        "s10_orgconfig_missing_required",
        "s11_promote_dryrun_empty",
        "s12_promote_dryrun_json_reviewed",
        "s13_promote_dryrun_text_reviewed",
        "s14_rk_pending",
        "s15_rk_pending_json",
        "s16_rk_approve",
        "s17_rk_reject_move",
        "s18_rk_escape",
        "s19_mr_local_text",
        "s20_mr_all_json",
        "s21_mr_invalid_scope",
        "s22_wg_export_empty",
        "s23_wg_no_config",
        "s24_pf_security_json",
        "s25_pf_noop_tie",
        "s25b_agent_guidelines",
        "s26_install_skills_fresh",
        "s27_unknown_command",
        "s28_unknown_help_flag",
        "s29_rollback_doctor",
        "s30_rollback_unknown",
    ] {
        let expected = match segments.get(name) {
            Some(seg) => format!("{}\n", seg.join("\n")),
            None => {
                failures.push(format!("{name}: ausente en golden"));
                continue;
            }
        };
        match replay_case(name, &bin, &py_bin, &python_bin, work.path(), &expected) {
            Ok(()) => println!("  [ok] {name}"),
            Err(err) => {
                println!("  [FAIL] {name}: {err}");
                failures.push(name.to_string());
            }
        }
    }

    if failures.is_empty() {
        println!("[PASS] cli_check byte-parity vs golden_cli.txt ({total} casos)");
        println!("✅ PARIDAD P12B-8");
    } else {
        eprintln!(
            "[FAIL] {}/{} casos divergentes: {}",
            failures.len(),
            total,
            failures.join(", ")
        );
        std::process::exit(1);
    }
}

#[allow(clippy::too_many_arguments)]
fn replay_case(
    name: &str,
    bin: &Path,
    py_bin: &Path,
    python_bin: &Path,
    work: &Path,
    expected: &str,
) -> Result<(), String> {
    // Recetas espejo de run_case() del oráculo.
    let spec: CaseSpec = match name {
        "s01_hint_l0" => CaseSpec::hint("l0"),
        "s02_hint_l1" => CaseSpec::hint("l1"),
        "s03_hint_l7" => CaseSpec::hint("l7"),
        "s05_doctor_empty" => CaseSpec::simple("l7", &["doctor"]),
        "s06_doctor_all_org" => CaseSpec::simple("l7", &["doctor", "--scope", "all"]),
        "s07_doctor_strict" => CaseSpec::simple("l7", &["doctor", "--strict"]),
        "s08_orgconfig_text" => CaseSpec::simple("l7", &["org-config"]),
        "s09_orgconfig_json" => CaseSpec::simple("l7", &["org-config", "--json"]),
        "s10_orgconfig_missing_required" => CaseSpec::simple("l0", &["org-config", "--required"]),
        "s11_promote_dryrun_empty" => CaseSpec::simple("l7", &["promote-knowledge"]),
        "s12_promote_dryrun_json_reviewed" => {
            CaseSpec::promo("l7", &["promote-knowledge", "--json"])
        }
        "s13_promote_dryrun_text_reviewed" => CaseSpec::promo("l7", &["promote-knowledge"]),
        "s14_rk_pending" => CaseSpec::review(&["review-knowledge", "pending"]),
        "s15_rk_pending_json" => CaseSpec::review(&["review-knowledge", "pending", "--json"]),
        "s16_rk_approve" => CaseSpec::review(&[
            "review-knowledge",
            "approve",
            "specs/draft1.md",
            "--reviewer",
            "tester",
        ]),
        "s17_rk_reject_move" => CaseSpec::review(&[
            "review-knowledge",
            "reject",
            "specs/draft2.md",
            "--reason",
            "no sirve",
        ]),
        "s18_rk_escape" => CaseSpec::review(&["review-knowledge", "approve", "../escape.md"]),
        "s19_mr_local_text" => CaseSpec::simple("l7", &["memory-report", "--scope", "local"]),
        "s20_mr_all_json" => CaseSpec::mr_json(),
        "s21_mr_invalid_scope" => CaseSpec::simple("l7", &["memory-report", "--scope", "bogus"]),
        "s22_wg_export_empty" => CaseSpec::wg_export("l1"),
        "s23_wg_no_config" => CaseSpec::simple("l0", &["webgraph", "export"]),
        "s24_pf_security_json" => CaseSpec::simple(
            "l1",
            &[
                "autopilot",
                "preflight",
                "--request",
                "implementar autenticación completa con JWT y refresh tokens",
                "--json",
            ],
        ),
        "s25_pf_noop_tie" => CaseSpec::simple(
            "l1",
            &["autopilot", "preflight", "--request", "qué hora es"],
        ),
        "s25b_agent_guidelines" => CaseSpec::simple("l0", &["agent-guidelines"]),
        "s26_install_skills_fresh" => {
            CaseSpec::simple("l0", &["install-skills", "--dest", "skills-out"])
        }
        "s27_unknown_command" => CaseSpec::simple("l0", &["frobnicate", "--x", "1"]),
        "s28_unknown_help_flag" => CaseSpec::simple("l0", &["--frobnicate"]),
        "s29_rollback_doctor" => CaseSpec::passthrough(
            "l1",
            &["doctor", "--project-root", "."],
            &["doctor", "--project-root", "."],
        ),
        "s30_rollback_unknown" => CaseSpec::passthrough("l0", &["frobnicate"], &["frobnicate"]),
        other => return Err(format!("caso sin receta: {other}")),
    };

    // Fixture espejo del oráculo (mismo basename "fix"); SIEMPRE limpio para
    // evitar fuga de estado entre casos (el gate también arranca fresco).
    let root = work.join("fix");
    if root.exists() {
        std::fs::remove_dir_all(&root).unwrap();
    }
    std::fs::create_dir_all(&root).unwrap();
    match spec.fixture {
        "l7" | "l7r" => build_l7(&root),
        "l1" => {
            std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
        }
        _ => {}
    }
    if matches!(spec.fixture, "review") {
        build_review(&root);
    }
    if spec.promo {
        seed_reviewed_candidate(&root, python_bin);
    }

    let mut cmd = Command::new(bin);
    cmd.args(spec.rs_args)
        .current_dir(&root)
        .env("CORTEX_BIN", py_bin)
        .env("USER", "tester")
        .env("LOGNAME", "tester")
        .env("LNAME", "tester")
        .env("USERNAME", "tester");
    if spec.passthrough {
        cmd.env("CORTEX_PY", "1");
    }
    let out = cmd.output().map_err(|e| e.to_string())?;

    let stdout = String::from_utf8_lossy(&out.stdout);
    let stderr = String::from_utf8_lossy(&out.stderr);

    if spec.data_only {
        // El golden trae SOLO el stdout normalizado (sin rc ni stderr);
        // el stdout nativo ya termina en \n como la salida del oráculo.
        return compare(
            name,
            expected,
            &normalize(&stdout, &root, spec.normalize_fp),
        );
    }

    let mut blob = normalize(&stdout, &root, spec.normalize_fp);
    if !stderr.is_empty() {
        blob.push_str("---STDERR---\n");
        blob.push_str(&normalize(&stderr, &root, spec.normalize_fp));
    }
    blob.push_str(&format!("rc={}\n", out.status.code().unwrap_or(-1)));

    // Archivo generado por webgraph export.
    if spec.snapshot {
        let snap = root.join(".cortex/webgraph/cache/snapshot-hybrid.json");
        let body = std::fs::read_to_string(&snap).map_err(|e| format!("snapshot ausente: {e}"))?;
        blob.push_str("---SNAPSHOT---\n");
        // Igual que el oráculo: primero {{FP}}, luego {{ROOT}}/{{TS}}.
        blob.push_str(&normalize(&normalize_fp(&body), &root, spec.normalize_fp));
        blob.push('\n');
    }

    compare(name, expected, &blob)
}

fn compare(_name: &str, expected: &str, got: &str) -> Result<(), String> {
    if expected == got {
        return Ok(());
    }
    let exp_tail: Vec<&str> = expected.lines().rev().take(6).collect();
    let got_tail: Vec<&str> = got.lines().rev().take(6).collect();
    Err(format!(
        "difiere (tail esperado {:?} vs obtenido {:?})",
        exp_tail, got_tail
    ))
}

struct CaseSpec {
    fixture: &'static str,
    rs_args: Vec<String>,
    promo: bool,
    passthrough: bool,
    snapshot: bool,
    normalize_fp: bool,
    /// El golden contiene solo stdout (memory-report --json normalizado).
    data_only: bool,
}

impl CaseSpec {
    fn hint(kind: &'static str) -> Self {
        Self {
            fixture: kind,
            rs_args: vec!["hint".into()],
            promo: false,
            passthrough: false,
            snapshot: false,
            normalize_fp: false,
            data_only: false,
        }
    }
    fn simple(kind: &'static str, args: &[&str]) -> Self {
        Self {
            fixture: kind,
            rs_args: args.iter().map(|s| s.to_string()).collect(),
            promo: false,
            passthrough: false,
            snapshot: false,
            normalize_fp: false,
            data_only: false,
        }
    }
    fn promo(kind: &'static str, args: &[&str]) -> Self {
        let mut s = Self::simple(kind, args);
        s.promo = true;
        s
    }
    fn review(args: &[&str]) -> Self {
        let mut s = Self::simple("review", args);
        s.fixture = "review";
        s
    }
    fn wg_export(kind: &'static str) -> Self {
        let mut s = Self::simple(kind, &["webgraph", "export", "--no-cache"]);
        s.snapshot = true;
        s.normalize_fp = true;
        s
    }
    fn mr_json() -> Self {
        let mut s = Self::simple("l7", &["memory-report", "--scope", "all", "--json"]);
        s.data_only = true;
        s
    }
    fn passthrough(kind: &'static str, py_args: &[&str], rs_args: &[&str]) -> Self {
        let mut s = Self::simple(kind, rs_args);
        let _ = py_args;
        s.passthrough = true;
        s
    }
}

// ── fixtures ────────────────────────────────────────────────────────────────

fn build_l7(root: &Path) {
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    std::fs::create_dir_all(root.join("vault/specs")).unwrap();
    std::fs::create_dir_all(root.join("vault/sessions")).unwrap();
    for i in 0..3 {
        std::fs::write(
            root.join(format!("vault/specs/s{i}.md")),
            format!("# s{i}\n"),
        )
        .unwrap();
    }
    for i in 0..2 {
        std::fs::write(
            root.join(format!("vault/sessions/x{i}.md")),
            format!("# x{i}\n"),
        )
        .unwrap();
    }
    std::fs::create_dir_all(root.join(".github/workflows")).unwrap();
    std::fs::write(root.join(".mcp.json"), "{}\n").unwrap();
    std::fs::create_dir_all(root.join(".cortex")).unwrap();
    std::fs::write(
        root.join(".cortex/org.yaml"),
        "schema_version: 1\norganization:\n  name: Acme Org\nmemory:\n  enterprise_semantic_enabled: true\npromotion:\n  enabled: true\n",
    )
    .unwrap();
    std::fs::create_dir_all(root.join("vault-enterprise")).unwrap();
}

fn build_review(root: &Path) {
    std::fs::write(root.join("config.yaml"), "semantic:\n  vault_path: vault\n").unwrap();
    std::fs::create_dir_all(root.join("vault")).unwrap();
    let specs = root.join("vault-enterprise/specs");
    std::fs::create_dir_all(&specs).unwrap();
    std::fs::write(
        specs.join("draft1.md"),
        "---\ntitle: Draft One\ndoc_type: spec\nowner: alice\nstatus: draft\n---\n\nBody one\n",
    )
    .unwrap();
    std::fs::write(
        specs.join("draft2.md"),
        "---\ntitle: Draft Two\ndoc_type: runbook\nstatus: draft\n---\n\nBody two\n",
    )
    .unwrap();
}

/// Semilla del candidato revisado usando el BINARIO PY (misma semilla que el
/// oráculo: KnowledgePromotionService real).
fn seed_reviewed_candidate(root: &Path, py_bin: &Path) {
    // La revisión usa el servicio real de Python (mismo oráculo que el gate).
    // La ruta del proyecto viaja por argv para no pelear con quoting.
    let script = concat!(
        "import sys\n",
        "from pathlib import Path\n",
        "from cortex.enterprise.knowledge_promotion import KnowledgePromotionService\n",
        "svc = KnowledgePromotionService.from_project_root(Path(sys.argv[1]))\n",
        "cands = svc.discover_candidates()\n",
        "assert cands, 'sin candidatos'\n",
        "svc.review(selector=cands[0].origin_id, approve=True, actor='tester', reason='ok')\n",
    );
    let out = Command::new(py_bin)
        .arg("-c")
        .arg(script)
        .arg(root)
        .output()
        .expect("python para semilla");
    if !out.status.success() {
        panic!(
            "semilla de candidato falló: {}",
            String::from_utf8_lossy(&out.stderr)
        );
    }
}

// ── normalización (idéntica al oráculo) ─────────────────────────────────────

fn normalize(text: &str, root: &Path, fp: bool) -> String {
    let mut out = text.replace(root.to_str().unwrap(), "{{ROOT}}");
    if fp {
        out = normalize_fp(&out);
    }
    out = replace_ts(&out);
    out
}

fn normalize_fp(body: &str) -> String {
    // "fingerprint": "<64 hex>" → {{FP}}
    let mut out = String::with_capacity(body.len());
    let bytes = body.as_bytes();
    let pat = b"\"fingerprint\": \"";
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i..].starts_with(pat) {
            let start = i + pat.len();
            let hex_end = (start..bytes.len().min(start + 65))
                .find(|&j| !(bytes[j] as char).is_ascii_hexdigit());
            if let Some(end) = hex_end {
                if end - start == 64 && bytes[end] == b'"' {
                    out.push_str("\"fingerprint\": \"{{FP}}\"");
                    i = end + 1;
                    continue;
                }
            }
        }
        let ch_len = utf8_len(bytes[i]);
        out.push_str(&body[i..i + ch_len]);
        i += ch_len;
    }
    out
}

fn replace_ts(s: &str) -> String {
    let bytes = s.as_bytes();
    let mut out = String::with_capacity(s.len());
    let mut i = 0;
    while i < s.len() {
        // ISO: YYYY-MM-DDTHH:MM(:SS(.fff)?)?(Z|+00:00)
        if i + 10 <= s.len()
            && bytes[i] == b'2'
            && bytes[i + 4] == b'-'
            && bytes[i + 7] == b'-'
            && bytes[i + 10] == b'T'
            && s[i..].len() > 10
        {
            // buscar fin del timestamp razonable
            let rest = &s[i..];
            let end = rest
                .find(|c: char| {
                    !(c.is_ascii_digit() || matches!(c, '-' | ':' | 'T' | '.' | '+' | 'Z'))
                })
                .map(|j| i + j)
                .unwrap_or(s.len());
            let cand = &s[i..end];
            let looks_ts = cand.len() >= 16
                && cand.as_bytes()[13] == b':'
                && (cand.ends_with("+00:00") || cand.ends_with('Z') || cand.contains(':'));
            if looks_ts {
                out.push_str("{{TS}}");
                i = end;
                continue;
            }
        }
        let ch_len = utf8_len(bytes[i]);
        out.push_str(&s[i..i + ch_len]);
        i += ch_len;
    }
    out
}

fn utf8_len(b: u8) -> usize {
    if b < 0x80 {
        1
    } else if b >> 5 == 0b110 {
        2
    } else if b >> 4 == 0b1110 {
        3
    } else {
        4
    }
}
