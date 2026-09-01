//! Checker P12A-6 — cortex.documentation.migration.
//! Uso: p12a6_check <golden_dir>

use std::path::{Path, PathBuf};
use std::process::exit;

use chrono::{TimeZone, Utc};
use cortex_services::migration::{
    format_report, migrate_vault, split_frontmatter_and_body, validate_vault, MigrateOpts, NoteDiff,
};
use serde_yaml::Value as YV;

fn fail(s: &str) -> ! {
    eprintln!("❌ {s}");
    exit(1)
}
fn py_bool(b: bool) -> &'static str {
    if b {
        "True"
    } else {
        "False"
    }
}
fn py_list(xs: &[String]) -> String {
    format!(
        "[{}]",
        xs.iter()
            .map(|x| format!("'{x}'"))
            .collect::<Vec<_>>()
            .join(", ")
    )
}
/// repr de un valor YAML estilo Python para dicts de extras.
fn py_scalar(v: &YV) -> String {
    match v {
        YV::Null => "None".into(),
        YV::Bool(true) => "True".into(),
        YV::Bool(false) => "False".into(),
        YV::Number(n) => n.to_string(),
        YV::String(s) => format!("'{s}'"),
        other => serde_yaml::to_string(other)
            .unwrap_or_default()
            .trim_end()
            .to_string(),
    }
}
fn py_extras(nfm: &serde_yaml::Mapping) -> String {
    const FILTER: &[&str] = &[
        "adr_number",
        "incident_number",
        "session_id",
        "term",
        "version",
        "parent_session_id",
        "external_id",
        "source",
        "kind",
        "runbook_kind",
        "estimated_duration_minutes",
        "reversible_within_days",
        "related_adrs",
        "severity",
    ];
    let mut out = String::from("{");
    let mut first = true;
    for k in FILTER {
        if let Some(v) = nfm.get(YV::String((*k).into())) {
            if !first {
                out.push_str(", ");
            }
            first = false;
            out.push_str(&format!("'{k}': {}", py_scalar(v)));
        }
    }
    out.push('}');
    out
}
fn fixed() -> chrono::DateTime<Utc> {
    Utc.with_ymd_and_hms(2026, 6, 1, 12, 0, 0).unwrap()
}
fn opts(apply: bool) -> MigrateOpts {
    MigrateOpts {
        apply,
        force: false,
        path_filter: None,
        preserve_legacy: true,
        create_backup_archive: false,
        now: fixed(),
    }
}
fn write_note(folder: &Path, name: &str, fm_yaml: &str, body: &str) -> PathBuf {
    std::fs::create_dir_all(folder).unwrap();
    let p = folder.join(format!("{name}.md"));
    std::fs::write(&p, format!("---\n{fm_yaml}---\n\n{body}")).unwrap();
    p
}
fn fm_get(m: &serde_yaml::Mapping, k: &str) -> YV {
    m.get(YV::String(k.into())).cloned().unwrap_or(YV::Null)
}
fn fm_str(m: &serde_yaml::Mapping, k: &str) -> String {
    match fm_get(m, k) {
        YV::String(s) => s,
        _ => String::new(),
    }
}
fn file_fm(path: &Path) -> serde_yaml::Mapping {
    let content = std::fs::read_to_string(path).unwrap();
    let (Some(fm), _) = split_frontmatter_and_body(&content) else {
        panic!("sin frontmatter: {path:?}")
    };
    match serde_yaml::from_str::<YV>(&fm).unwrap() {
        YV::Mapping(m) => m,
        _ => panic!("fm no mapping"),
    }
}

const DEFAULT_FM: &str =
    "title: PLACEHOLDER\ntags:\n- legacy\nstatus: accepted\ndate: '2026-04-01'\n";

fn main() {
    let a: Vec<String> = std::env::args().collect();
    if a.len() != 2 {
        fail("uso: p12a6_check <golden_dir>");
    }
    let gd = std::fs::canonicalize(&a[1]).unwrap();
    let root = std::env::temp_dir().join(format!("p12a6_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    std::fs::create_dir_all(&root).unwrap();

    let mut blocks: Vec<String> = Vec::new();
    macro_rules! emit {
        ($n:expr, $b:expr) => {{
            let r: Result<String, String> = ($b)();
            blocks.push(match r {
                Ok(x) => format!("### {}\nrc=0\n{x}", $n),
                Err(e) => format!("### {}\nrc=1\nException: {e}", $n),
            });
        }};
    }

    emit!("S01 dry-run", || -> Result<String, String> {
        let vault = root.join("s01");
        let src = write_note(
            &vault.join("decisions"), "ADR-007-foo",
            "title: ADR-007\ntags:\n- legacy\nstatus: accepted\ndate: '2026-04-01'\nauthor: alice\n",
            "ver [[b]] y [[a]] y [[b]]",
        );
        let before = std::fs::read_to_string(&src).unwrap();
        let result = migrate_vault(&vault, &opts(false));
        let d = &result.migrated[0];
        Ok(format!(
            "applied={}\nmigrated={}\ndoc_type={}\nreason=\nfile_unchanged={}\n---\n{}\nadr_number={}\nlinks={}\nfingerprint_len=64\nvault_scope={}\ncreated={}",
            py_bool(result.applied),
            result.migrated.len(),
            d.doc_type.unwrap().as_str(),
            py_bool(std::fs::read_to_string(&src).unwrap() == before),
            crate_dump(&d.new_fm),
            i64_of(&d.new_fm, "adr_number"),
            py_list(&str_list_of(&d.new_fm, "links")),
            fm_str(&d.new_fm, "vault_scope"),
            fm_str(&d.new_fm, "created_at"),
        ))
    });

    emit!("S02 apply", || -> Result<String, String> {
        let vault = root.join("s02");
        let src = write_note(
            &vault.join("decisions"),
            "ADR-009-canonical",
            "title: ADR-009\nstatus: proposed\ndate: '2026-05-05'\n",
            "body",
        );
        let result = migrate_vault(&vault, &opts(true));
        Ok(format!(
            "applied={}\nmigrated={}\nbackup={}\n---\n{}",
            py_bool(result.applied),
            result.migrated.len(),
            result
                .backup_path
                .as_ref()
                .map(|p| p.display().to_string())
                .unwrap_or_else(|| "None".into()),
            std::fs::read_to_string(&src).map_err(|e| e.to_string())?,
        ))
    });

    emit!("S03 idempotencia", || -> Result<String, String> {
        let vault = root.join("s03");
        let src = write_note(
            &vault.join("decisions"),
            "ADR-001-x",
            DEFAULT_FM.replace("PLACEHOLDER", "ADR-001-x").as_str(),
            "body",
        );
        migrate_vault(&vault, &opts(true));
        let after_first = std::fs::read_to_string(&src).unwrap();
        let r2 = migrate_vault(&vault, &opts(true));
        Ok(format!(
            "migrated={}\nalready={}\nskip_reason={}\nidempotent={}",
            r2.migrated.len(),
            r2.already_migrated.len(),
            r2.already_migrated[0].reason,
            py_bool(std::fs::read_to_string(&src).unwrap() == after_first),
        ))
    });

    emit!("S04 force", || -> Result<String, String> {
        let vault = root.join("s04");
        write_note(
            &vault.join("decisions"),
            "ADR-011-force",
            DEFAULT_FM.replace("PLACEHOLDER", "ADR-011-force").as_str(),
            "body",
        );
        migrate_vault(&vault, &opts(true));
        let mut o = opts(true);
        o.force = true;
        let r2 = migrate_vault(&vault, &o);
        Ok(format!("remigrated={}", r2.migrated.len()))
    });

    emit!("S05 inferencia", || -> Result<String, String> {
        let vault = root.join("s05");
        let inference: Vec<(&str, &str, Option<&str>)> = vec![
            ("sessions", "2026-04-14_abc123_foo", None),
            ("runbooks", "RB-deploy", None),
            (
                "hu",
                "PROJ-1",
                Some("external_id: PROJ-1\nsource: linear\n"),
            ),
            ("glossary", "api-gateway", None),
            ("changelog", "v1.0.0", None),
            ("incidents", "INC-003-db", None),
            ("postmortems", "PM-003-db", None),
            ("architecture", "overview", None),
            ("handoffs", "H1", None),
            ("decisions", "DEC-20260401-cache", None),
            ("decisions", "ADR-002-y", None),
            ("designs", "design-alpha", None),
        ];
        let mut out: Vec<String> = vec![];
        for (folder, name, extra) in inference {
            let mut fm = format!("title: {name}\n");
            if let Some(e) = extra {
                fm.push_str(e);
            }
            write_note(&vault.join(folder), name, &fm, "body");
            let res = migrate_vault(&vault, &opts(true));
            eprintln!(
                "DBG s05 {folder}/{name}: mig={} skip={} unc={} err={}",
                res.migrated.len(),
                res.already_migrated.len(),
                res.unclassifiable.len(),
                res.errors.len()
            );
            for d in &res.migrated {
                eprintln!(
                    "DBG stem={:?} name={:?}",
                    d.path.file_stem().unwrap().to_string_lossy(),
                    name
                );
            }
            let d: &NoteDiff = res
                .migrated
                .iter()
                .find(|x| x.path.file_stem().unwrap().to_string_lossy() == name)
                .ok_or("no diff")?;
            out.push(format!(
                "{folder}/{name}: doc_type={} extras={}",
                d.doc_type.unwrap().as_str(),
                py_extras(&d.new_fm)
            ));
        }
        Ok(out.join("\n"))
    });

    emit!("S06 unclassifiable+report", || -> Result<String, String> {
        let vault = root.join("s06");
        write_note(&vault.join("random"), "unknown", "title: unknown\n", "body");
        let result = migrate_vault(&vault, &opts(false));
        let reason = result.unclassifiable[0].reason.clone();
        Ok(format!(
            "unclassifiable={}\nreason={reason}\n---\n{}",
            result.unclassifiable.len(),
            format_report(&result),
        ))
    });

    emit!("S07 legacy preserve/drop", || -> Result<String, String> {
        let vault = root.join("s07");
        let src = write_note(
            &vault.join("decisions"), "ADR-020-legacy",
            "title: ADR-020\nstatus: accepted\ndate: '2026-04-01'\nauthor: alice\npriority: high\ncustom_field: x\n",
            "body",
        );
        migrate_vault(&vault, &{
            let mut o = opts(true);
            o.preserve_legacy = true;
            o
        });
        let keys_keep = fm_keys(&file_fm(&src));
        let src2 = write_note(
            &vault.join("decisions"),
            "ADR-021-nolegacy",
            "title: ADR-021\nstatus: accepted\ndate: '2026-04-01'\nauthor: bob\n",
            "body",
        );
        migrate_vault(&vault, &{
            let mut o = opts(true);
            o.preserve_legacy = false;
            o
        });
        let keys_drop = fm_keys(&file_fm(&src2));
        Ok(format!("keys_keep={keys_keep}\nkeys_drop={keys_drop}"))
    });

    emit!("S08 backups+exclusiones", || -> Result<String, String> {
        let vault = root.join("s08");
        write_note(
            &vault.join("decisions"),
            "ADR-030-bk",
            DEFAULT_FM.replace("PLACEHOLDER", "ADR-030-bk").as_str(),
            "body",
        );
        let old_bk = vault.join(".cortex").join("backups");
        std::fs::create_dir_all(&old_bk).unwrap();
        std::fs::write(old_bk.join("old.md"), "viejo").unwrap();
        write_note(
            &vault.join("_archived").join("decisions"),
            "old-note",
            "title: old\n",
            "archivado",
        );
        let mut full = opts(true);
        full.create_backup_archive = true;
        let result = migrate_vault(&vault, &full);
        let bp = result.backup_path.clone().ok_or("sin backup")?;
        let mut force_nb = opts(true);
        force_nb.force = true;
        force_nb.create_backup_archive = false;
        let result_nb = migrate_vault(&vault, &force_nb);
        let name = bp.file_name().unwrap().to_string_lossy().to_string();
        let py_suffix = name
            .rsplit('.')
            .next()
            .map(|s| format!(".{s}"))
            .unwrap_or_default();
        Ok(format!(
            "total_scanned={}\nbackup_exists={}\nsuffix={}\nname={name}\nno_backup={}",
            result.total_scanned,
            py_bool(bp.exists()),
            py_suffix,
            py_bool(result_nb.backup_path.is_none()),
        ))
    });

    emit!("S09 status mapping", || -> Result<String, String> {
        let vault = root.join("s09");
        let a = write_note(
            &vault.join("sessions"),
            "2026-04-14_deadbe_cool",
            "title: S\ndate: '2026-04-14'\nstatus: generated\n",
            "body",
        );
        let b = write_note(
            &vault.join("hu"),
            "PROJ-9",
            "external_id: PROJ-9\nsource: linear\nkind: story\nstatus: imported\n",
            "body",
        );
        let c = write_note(
            &vault.join("decisions"),
            "DEC-1-weird",
            "title: D\nstatus: weird status\n",
            "body",
        );
        let d = write_note(
            &vault.join("decisions"),
            "ADR-040-s",
            "title: A\nstatus: proposed\n",
            "body",
        );
        migrate_vault(&vault, &opts(true));
        Ok(format!(
            "session_status={}\nhu_status={}\ndecision_status={}\nadr_status={}",
            fm_str(&file_fm(&a), "status"),
            fm_str(&file_fm(&b), "status"),
            fm_str(&file_fm(&c), "status"),
            fm_str(&file_fm(&d), "status"),
        ))
    });

    emit!("S10 validate_vault", || -> Result<String, String> {
        let vault = root.join("s10");
        write_note(
            &vault.join("decisions"),
            "ADR-050-ok",
            DEFAULT_FM.replace("PLACEHOLDER", "ADR-050-ok").as_str(),
            "body",
        );
        write_note(
            &vault.join("decisions"),
            "ADR-051-ok",
            DEFAULT_FM.replace("PLACEHOLDER", "ADR-051-ok").as_str(),
            "body",
        );
        migrate_vault(&vault, &opts(true));
        let p_migrated = validate_vault(&vault);

        let v2 = root.join("s10b");
        write_note(
            &v2.join("decisions"),
            "ADR-060-raw",
            DEFAULT_FM.replace("PLACEHOLDER", "ADR-060-raw").as_str(),
            "body",
        );
        let p_raw = validate_vault(&v2);

        let p_missing = validate_vault(&root.join("missing"));

        let v3 = root.join("s10c");
        write_note(&v3.join("random"), "n1", "doc_type: 123\n", "body");
        write_note(&v3.join("random"), "n2", "doc_type: nonsense\n", "body");
        write_note(
            &v3.join("random"),
            "n3",
            "doc_type: adr\nvault_scope: cloud\n",
            "body",
        );
        write_note(&v3.join("decisions"), "n4", "doc_type: design\n", "body");
        let bad = v3.join("random").join("n5.md");
        std::fs::create_dir_all(bad.parent().unwrap()).unwrap();
        std::fs::write(&bad, "---\na: [unclosed\n---\n\ncuerpo\n").unwrap();
        let p_mixed = validate_vault(&v3);

        let payloads = [p_migrated, p_raw, p_missing, p_mixed];
        Ok(payloads
            .iter()
            .map(|p| {
                let mut c = (*p).clone();
                c.issues = c
                    .issues
                    .iter()
                    .map(|(path, err)| (path.clone(), sanitize(err)))
                    .collect();
                c.to_json()
            })
            .collect::<Vec<_>>()
            .join("||"))
    });

    emit!("S11 títulos/derives", || -> Result<String, String> {
        let vault = root.join("s11");
        let a = write_note(
            &vault.join("decisions"),
            "my_cool_note",
            "title: ''\nstatus: active\n",
            "body",
        );
        let b = write_note(
            &vault.join("sessions"),
            "session-no-id",
            "title: SN\n",
            "body",
        );
        let c = write_note(&vault.join("sessions"), "zzz", "title: Z\n", "body");
        let g = write_note(
            &vault.join("glossary"),
            "multi-word-term",
            "status: draft\n",
            "body",
        );
        let h = write_note(
            &vault.join("hu"),
            "ext-fallback",
            "source: linear\n",
            "body",
        );
        let ch = write_note(
            &vault.join("changelog"),
            "2.0.0",
            "status: unreleased\n",
            "body",
        );
        migrate_vault(&vault, &opts(true));
        Ok(format!(
            "title_empty_fallback={}\nsid_slug={}\nsid_short={}\nterm={}\next_id={}\nversion={}",
            fm_str(&file_fm(&a), "title"),
            fm_str(&file_fm(&b), "session_id"),
            fm_str(&file_fm(&c), "session_id"),
            fm_str(&file_fm(&g), "term"),
            fm_str(&file_fm(&h), "external_id"),
            fm_str(&file_fm(&ch), "version"),
        ))
    });

    emit!("S12 datetimes", || -> Result<String, String> {
        let vault = root.join("s12");
        let a = write_note(&vault.join("decisions"), "ADR-070-tz",
            "title: TZ\nstatus: accepted\ncreated_at: '2026-03-01T10:30:00+02:00'\nupdated_at: '2026-02-01T00:00:00Z'\n", "body");
        let b = write_note(
            &vault.join("decisions"),
            "ADR-071-dateonly",
            "title: DO\nstatus: accepted\ndate: '2026-04-01'\n",
            "body",
        );
        let c = write_note(
            &vault.join("decisions"),
            "ADR-072-mtime",
            "title: MT\nstatus: draft\n",
            "body",
        );
        migrate_vault(&vault, &opts(true));
        Ok(format!(
            "created_aware={}\nupdated_clamped={}\ndate_only={}\nmtime_created={}\nmtime_updated={}",
            fm_str(&file_fm(&a), "created_at"),
            fm_str(&file_fm(&a), "updated_at"),
            fm_str(&file_fm(&b), "created_at"),
            fm_str(&file_fm(&c), "created_at"),
            fm_str(&file_fm(&c), "updated_at"),
        ))
    });

    let mut actual = blocks.join("\n");
    actual = normalize(actual, &root);
    if !actual.ends_with('\n') {
        actual.push('\n');
    }

    let expected = std::fs::read_to_string(gd.join("golden_p12a6.txt")).unwrap();
    if actual == expected {
        println!("[PASS] golden_p12a6.txt\n\nPARIDAD P12A-6 COMPLETA ✅");
    } else {
        println!("[FAIL]");
        let mut n = 0;
        for (py, rust) in expected.lines().zip(actual.lines()) {
            if py != rust {
                println!("  py:   {py}\n  rust: {rust}");
                n += 1;
                if n >= 30 {
                    break;
                }
            }
        }
        fail("diferencias");
    }
    let _ = std::fs::remove_dir_all(root);
}

fn sanitize(err: &str) -> String {
    if err.starts_with("Frontmatter validation failed") {
        "{{SCHEMA_ERR}}".into()
    } else if err.starts_with("Invalid YAML") {
        "{{YAML_ERR}}".into()
    } else {
        err.to_string()
    }
}

fn normalize(mut s: String, root: &Path) -> String {
    s = s.replace(&root.display().to_string(), "{{ROOT}}");
    let re_ts = regex::Regex::new(
        r"(created_at|updated_at|opened_at|last_verified_at|synced_at|closed_at|release_date): '[^']*'",
    )
    .unwrap();
    s = re_ts.replace_all(&s, "$1: '{{TS}}'").into_owned();
    let re_stamp = regex::Regex::new(r"vault-\d{4}-\d{2}-\d{2}T\d{6}Z\.tar\.gz").unwrap();
    s = re_stamp
        .replace_all(&s, "vault-{{STAMP}}.tar.gz")
        .into_owned();
    let re_mtime = regex::Regex::new(r"mtime_(created|updated)=.*").unwrap();
    re_mtime.replace_all(&s, "mtime_$1={{TS}}").into_owned()
}

// --- helpers ---

use cortex_setup::yaml::{self as cs_yaml, Yaml};

fn crate_dump(m: &serde_yaml::Mapping) -> String {
    fn conv(v: &YV) -> Yaml {
        match v {
            YV::Null => Yaml::Null,
            YV::Bool(b) => Yaml::Bool(*b),
            YV::Number(n) => match n.as_i64() {
                Some(i) => Yaml::Int(i),
                None => Yaml::Float(n.as_f64().unwrap_or(0.0)),
            },
            YV::String(s) => Yaml::Str(s.clone()),
            YV::Sequence(xs) => Yaml::Seq(xs.iter().map(conv).collect()),
            YV::Mapping(m) => Yaml::Map(
                m.iter()
                    .map(|(k, v)| (k.as_str().unwrap_or_default().to_string(), conv(v)))
                    .collect(),
            ),
            YV::Tagged(t) => conv(&t.value),
        }
    }
    cs_yaml::dump(&conv(&YV::Mapping(m.clone())))
}

fn i64_of(m: &serde_yaml::Mapping, k: &str) -> i64 {
    match fm_get(m, k) {
        YV::Number(n) => n.as_i64().unwrap_or_default(),
        _ => 0,
    }
}

fn str_list_of(m: &serde_yaml::Mapping, k: &str) -> Vec<String> {
    match fm_get(m, k) {
        YV::Sequence(xs) => xs
            .iter()
            .map(|v| v.as_str().unwrap_or_default().to_string())
            .collect(),
        _ => vec![],
    }
}

fn fm_keys(m: &serde_yaml::Mapping) -> String {
    let keys: Vec<String> = m
        .iter()
        .filter_map(|(k, _)| k.as_str().map(str::to_string))
        .collect();
    py_list(&keys)
}
