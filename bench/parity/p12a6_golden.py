#!/usr/bin/env python3
"""Golden P12A-6 — cortex.documentation.migration.

Construye un reporte determinista de los escenarios S01–S12 (dry-run, apply,
idempotencia, force, inferencia por ruta, unclassifiable + report, legacy
preserve/drop, backups+exclusiones, mapeos de status, validate_vault,
títulos/derivaciones y resolución de fechas) y lo compara byte-a-byte contra
el checker Rust `p12a6_check`.

Normalizaciones pactadas:
- {{ROOT}}     ruta absoluta de la bóveda temporal
- {{TS}}       valores de timestamps en YAML (dependen del reloj/mtime)
- {{STAMP}}    nombre del backup tar.gz
- {{SCHEMA_ERR}} volcado de errores pydantic (no es contrato)
- {{YAML_ERR}} mensaje de parser YAML (PyYAML vs serde_yaml)

Los valores deterministas de fechas se emiten además en líneas `clave=valor`
(fuera del alcance de la normalización) para fijarlos exactamente.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import yaml  # noqa: E402

from cortex.documentation.migration import (  # noqa: E402
    format_report,
    migrate_vault,
    validate_vault,
)

FIXED = "2026-06-01T12:00:00+00:00"


def write_note(folder: Path, name: str, fm: dict | None = None, body: str = "body") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.md"
    fm_dict = fm or {"title": name, "tags": ["legacy"], "status": "accepted", "date": "2026-04-01"}
    path.write_text("---\n" + yaml.safe_dump(fm_dict, sort_keys=False) + "---\n\n" + body, encoding="utf-8")
    return path


def fm_of(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])


def dump_fm(fm: dict) -> str:
    return yaml.safe_dump(fm, sort_keys=False)


def normalize(text: str, root: str) -> str:
    s = text.replace(root, "{{ROOT}}")
    s = re.sub(
        r"(created_at|updated_at|opened_at|last_verified_at|synced_at|closed_at|release_date): '[^']*'",
        r"\1: '{{TS}}'",
        s,
    )
    s = re.sub(r"vault-\d{4}-\d{2}-\d{2}T\d{6}Z\.tar\.gz", "vault-{{STAMP}}.tar.gz", s)
    s = re.sub(r"mtime_(created|updated)=.*", r"mtime_\1={{TS}}", s)
    if not s.endswith("\n"):
        s += "\n"
    return s


def sanitize_error(err: str) -> str:
    """Colapsa errores de volcado pydantic/parser (no contrato) a marcadores."""
    if err.startswith("Frontmatter validation failed"):
        return "{{SCHEMA_ERR}}"
    if err.startswith("Invalid YAML"):
        return "{{YAML_ERR}}"
    return err


def dump_payload(p: dict) -> str:
    clone = dict(p)
    clone["issues"] = [
        {"path": i["path"], "error": sanitize_error(i["error"])} for i in p["issues"]
    ]
    return json.dumps(clone)


def build_report(root: Path) -> str:
    blocks: list[str] = []
    fixed = __import__("datetime").datetime.fromisoformat(FIXED)

    def emit(name: str, fn) -> None:
        try:
            blocks.append(f"### {name}\nrc=0\n{fn()}")
        except Exception as exc:  # noqa: BLE001
            blocks.append(f"### {name}\nrc=1\nException: {type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------
    def s01() -> str:
        vault = root / "s01"
        src = write_note(vault / "decisions", "ADR-007-foo",
                         {"title": "ADR-007", "tags": ["legacy"], "status": "accepted",
                          "date": "2026-04-01", "author": "alice"},
                         body="ver [[b]] y [[a]] y [[b]]")
        before = src.read_text(encoding="utf-8")
        result = migrate_vault(vault, apply=False, create_backup_archive=False, now=fixed)
        d = result.migrated[0]
        lines = [
            f"applied={result.applied}",
            f"migrated={len(result.migrated)}",
            f"doc_type={d.doc_type.value}",
            f"reason={d.reason}",
            f"file_unchanged={src.read_text(encoding='utf-8') == before}",
            "---",
            dump_fm(d.new_fm),
            f"adr_number={d.new_fm['adr_number']}",
            f"links={d.new_fm['links']}",
            f"fingerprint_len={len(d.new_fm['fingerprint'])}",
            f"vault_scope={d.new_fm['vault_scope']}",
            "created=" + d.new_fm["created_at"],
        ]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    def s02() -> str:
        vault = root / "s02"
        src = write_note(vault / "decisions", "ADR-009-canonical",
                         {"title": "ADR-009", "status": "proposed", "date": "2026-05-05"})
        result = migrate_vault(vault, apply=True, create_backup_archive=False, now=fixed)
        return "\n".join([
            f"applied={result.applied}",
            f"migrated={len(result.migrated)}",
            f"backup={result.backup_path}",
            "---",
            src.read_text(encoding="utf-8"),
        ])

    # ------------------------------------------------------------------
    def s03() -> str:
        vault = root / "s03"
        src = write_note(vault / "decisions", "ADR-001-x")
        migrate_vault(vault, apply=True, create_backup_archive=False, now=fixed)
        after_first = src.read_text(encoding="utf-8")
        result2 = migrate_vault(vault, apply=True, create_backup_archive=False, now=fixed)
        skip_reasons = [d.reason for d in result2.already_migrated]
        return "\n".join([
            f"migrated={len(result2.migrated)}",
            f"already={len(result2.already_migrated)}",
            f"skip_reason={skip_reasons[0]}",
            f"idempotent={src.read_text(encoding='utf-8') == after_first}",
        ])

    # ------------------------------------------------------------------
    def s04() -> str:
        vault = root / "s04"
        write_note(vault / "decisions", "ADR-011-force")
        migrate_vault(vault, apply=True, create_backup_archive=False, now=fixed)
        result2 = migrate_vault(vault, apply=True, force=True, create_backup_archive=False, now=fixed)
        return f"remigrated={len(result2.migrated)}"

    # ------------------------------------------------------------------
    INFERENCE = [
        ("sessions", "2026-04-14_abc123_foo", None),
        ("runbooks", "RB-deploy", None),
        ("hu", "PROJ-1", {"external_id": "PROJ-1", "source": "linear"}),
        ("glossary", "api-gateway", None),
        ("changelog", "v1.0.0", None),
        ("incidents", "INC-003-db", None),
        ("postmortems", "PM-003-db", None),
        ("architecture", "overview", None),
        ("handoffs", "H1", None),
        ("decisions", "DEC-20260401-cache", None),
        ("decisions", "ADR-002-y", None),
        ("designs", "design-alpha", None),
    ]

    def s05() -> str:
        vault = root / "s05"
        out = []
        for i, (folder, name, extra) in enumerate(INFERENCE):
            fm = {"title": name}
            if extra:
                fm.update(extra)
            write_note(vault / folder, name, fm)
            res = migrate_vault(vault, apply=True, create_backup_archive=False, now=fixed)
            d = [x for x in res.migrated if x.path.stem == name][0]
            nfm = d.new_fm
            extras = {k: v for k, v in nfm.items()
                      if k in {"adr_number", "incident_number", "session_id", "term",
                               "version", "parent_session_id", "external_id", "source",
                               "kind", "runbook_kind", "estimated_duration_minutes",
                               "reversible_within_days", "related_adrs", "severity"}}
            out.append(f"{folder}/{name}: doc_type={d.doc_type.value} extras={extras}")
        return "\n".join(out)

    # ------------------------------------------------------------------
    def s06() -> str:
        vault = root / "s06"
        write_note(vault / "random", "unknown")
        result = migrate_vault(vault, apply=False, create_backup_archive=False, now=fixed)
        reason = result.unclassifiable[0].reason
        return "\n".join([
            f"unclassifiable={len(result.unclassifiable)}",
            f"reason={reason}",
            "---",
            format_report(result),
        ])

    # ------------------------------------------------------------------
    def s07() -> str:
        vault = root / "s07"
        src = write_note(vault / "decisions", "ADR-020-legacy",
                         {"title": "ADR-020", "status": "accepted", "date": "2026-04-01",
                          "author": "alice", "priority": "high", "custom_field": "x"})
        migrate_vault(vault, apply=True, preserve_legacy=True, create_backup_archive=False, now=fixed)
        keys_keep = list(fm_of(src).keys())
        src2 = write_note(vault / "decisions", "ADR-021-nolegacy",
                          {"title": "ADR-021", "status": "accepted", "date": "2026-04-01",
                           "author": "bob"})
        migrate_vault(vault, apply=True, preserve_legacy=False, create_backup_archive=False, now=fixed)
        keys_drop = list(fm_of(src2).keys())
        return "\n".join([f"keys_keep={keys_keep}", f"keys_drop={keys_drop}"])

    # ------------------------------------------------------------------
    def s08() -> str:
        vault = root / "s08"
        write_note(vault / "decisions", "ADR-030-bk")
        # Backup viejo + _archived deben excluirse del escaneo.
        old_bk = vault / ".cortex" / "backups"
        old_bk.mkdir(parents=True, exist_ok=True)
        (old_bk / "old.md").write_text("viejo", encoding="utf-8")
        write_note(vault / "_archived" / "decisions", "old-note", body="archivado")
        result = migrate_vault(vault, apply=True, now=fixed)
        result_nb = migrate_vault(vault, apply=True, force=True,
                                  create_backup_archive=False, now=fixed)
        return "\n".join([
            f"total_scanned={result.total_scanned}",
            f"backup_exists={result.backup_path is not None and result.backup_path.exists()}",
            f"suffix={result.backup_path.suffix}",
            f"name={result.backup_path.name}",
            f"no_backup={result_nb.backup_path is None}",
        ])

    # ------------------------------------------------------------------
    def s09() -> str:
        vault = root / "s09"
        a = write_note(vault / "sessions", "2026-04-14_deadbe_cool",
                       {"title": "S", "date": "2026-04-14", "status": "generated"})
        b = write_note(vault / "hu", "PROJ-9",
                       {"external_id": "PROJ-9", "source": "linear", "kind": "story",
                        "status": "imported"})
        c = write_note(vault / "decisions", "DEC-1-weird",
                       {"title": "D", "status": "weird status"})
        d = write_note(vault / "decisions", "ADR-040-s", {"title": "A", "status": "proposed"})
        migrate_vault(vault, apply=True, create_backup_archive=False, now=fixed)
        return "\n".join([
            f"session_status={fm_of(a)['status']}",
            f"hu_status={fm_of(b)['status']}",
            f"decision_status={fm_of(c)['status']}",
            f"adr_status={fm_of(d)['status']}",
        ])

    # ------------------------------------------------------------------
    def s10() -> str:
        vault = root / "s10"
        write_note(vault / "decisions", "ADR-050-ok")
        write_note(vault / "decisions", "ADR-051-ok")
        migrate_vault(vault, apply=True, create_backup_archive=False, now=fixed)
        p_migrated = validate_vault(vault)

        v2 = root / "s10b"
        write_note(v2 / "decisions", "ADR-060-raw")  # sin migrar: sin doc_type
        p_raw = validate_vault(v2)

        p_missing = validate_vault(root / "missing")

        v3 = root / "s10c"
        write_note(v3 / "random", "n1", {"doc_type": 123})
        write_note(v3 / "random", "n2", {"doc_type": "nonsense"})
        write_note(v3 / "random", "n3", {"doc_type": "adr", "vault_scope": "cloud"})
        write_note(v3 / "decisions", "n4", {"doc_type": "design"})  # faltan session_id/spec_path
        # YAML malformado escrito en crudo (PyYAML y serde_yaml difieren ⇒ {{YAML_ERR}}).
        bad = v3 / "random" / "n5.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("---\na: [unclosed\n---\n\ncuerpo\n", encoding="utf-8")
        p_mixed = validate_vault(v3)

        payloads = [p_migrated, p_raw, p_missing, p_mixed]
        return "||".join(dump_payload(p) for p in payloads)

    # ------------------------------------------------------------------
    def s11() -> str:
        vault = root / "s11"
        a = write_note(vault / "decisions", "my_cool_note", {"title": "", "status": "active"})
        b = write_note(vault / "sessions", "session-no-id", {"title": "SN"})
        c = write_note(vault / "sessions", "zzz", {"title": "Z"})
        g = write_note(vault / "glossary", "multi-word-term", {"status": "draft"})
        h = write_note(vault / "hu", "ext-fallback", {"source": "linear"})
        ch = write_note(vault / "changelog", "2.0.0", {"status": "unreleased"})
        migrate_vault(vault, apply=True, create_backup_archive=False, now=fixed)
        fa, fb, fc, fg, fh, fch = (fm_of(x) for x in (a, b, c, g, h, ch))
        return "\n".join([
            f"title_empty_fallback={fa['title']}",
            f"sid_slug={fb['session_id']}",
            f"sid_short={fc['session_id']}",
            f"term={fg['term']}",
            f"ext_id={fh['external_id']}",
            f"version={fch['version']}",
        ])

    # ------------------------------------------------------------------
    def s12() -> str:
        vault = root / "s12"
        a = write_note(vault / "decisions", "ADR-070-tz",
                       {"title": "TZ", "status": "accepted",
                        "created_at": "2026-03-01T10:30:00+02:00",
                        "updated_at": "2026-02-01T00:00:00Z"})
        b = write_note(vault / "decisions", "ADR-071-dateonly",
                       {"title": "DO", "status": "accepted", "date": "2026-04-01"})
        c = write_note(vault / "decisions", "ADR-072-mtime", {"title": "MT", "status": "draft"})
        migrate_vault(vault, apply=True, create_backup_archive=False, now=fixed)
        fa, fb, fc = fm_of(a), fm_of(b), fm_of(c)
        return "\n".join([
            "created_aware=" + fa["created_at"],
            "updated_clamped=" + fa["updated_at"],
            "date_only=" + fb["created_at"],
            "mtime_created=" + fc["created_at"],
            "mtime_updated=" + fc["updated_at"],
        ])

    for name, fn in [
        ("S01 dry-run", s01),
        ("S02 apply", s02),
        ("S03 idempotencia", s03),
        ("S04 force", s04),
        ("S05 inferencia", s05),
        ("S06 unclassifiable+report", s06),
        ("S07 legacy preserve/drop", s07),
        ("S08 backups+exclusiones", s08),
        ("S09 status mapping", s09),
        ("S10 validate_vault", s10),
        ("S11 títulos/derives", s11),
        ("S12 datetimes", s12),
    ]:
        emit(name, fn)

    text = "\n".join(blocks)
    return normalize(text, str(root))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    golden = out_dir / "golden_p12a6.txt"

    tmp = Path(tempfile.mkdtemp(prefix="p12a6_oracle_"))
    try:
        first = build_report(tmp)
        second = build_report(tmp)
        if first != second:
            print("❌ ORÁCULO NO DETERMINISTA")
            for a, b in zip(first.splitlines(), second.splitlines()):
                if a != b:
                    print(f"  1ª: {a}\n  2ª: {b}")
            return 1
        print("✅ ORÁCULO DETERMINISTA")
        if args.command == "build":
            golden.write_text(first, encoding="utf-8")
            print(f"[OK] escrito {golden}")
            return 0
        expected = golden.read_text(encoding="utf-8")
        if first == expected:
            print("[PASS] golden_p12a6.txt")
            return 0
        print("[FAIL]")
        import difflib

        for line in difflib.unified_diff(
            expected.splitlines(), first.splitlines(), "py-guardado", "py-rerun", lineterm=""
        ):
            print(line)
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
