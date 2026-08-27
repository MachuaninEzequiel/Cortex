#!/usr/bin/env python3
"""Gate de paridad P12B-3 (enterprise/review_knowledge).

Genera `golden_enterprise.txt` con segmentos deterministas que el checker
Rust (`examples/enterprise_check.rs`) reproduce byte-a-byte tras normalizar
{{ROOT}}/{{TS}}. Oráculos reales: Pydantic/PyYAML/cortex.enterprise y
run_doctor de cortex.doctor.

Uso:
    python bench/parity/enterprise_golden_p12b.py build --out DIR
    python bench/parity/enterprise_golden_p12b.py verify --out DIR
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT_MARK = "{{ROOT}}"
TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)")

FIXED_TS = "2026-08-25T12:00:00+00:00"
SEGMENT = "=== SEGMENT {name} ==="


# ── helpers ─────────────────────────────────────────────────────────────────


def norm(text: str, root: Path) -> str:
    text = text.replace(str(root.resolve()), ROOT_MARK)
    return TS_RE.sub("{{TS}}", text)


def _patch_clocks() -> None:
    """Fija los relojes de los módulos enterprise al instante determinista."""
    from cortex.enterprise import knowledge_promotion as kp
    from cortex.enterprise import promotion_doctype as pd

    kp._utc_now = lambda: FIXED_TS

    class _DT(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ANN001
            return datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)

    pd.datetime = _DT


def _make_project(base: Path, *, profile: str = "small-company") -> Path:
    """Proyecto legacy mínimo con org.yaml + vaults."""
    root = base / "acme-api"
    root.mkdir(parents=True)
    (root / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\n", encoding="utf-8"
    )
    from cortex.enterprise.config import (
        build_enterprise_org_config,
        write_enterprise_config,
    )

    cfg = build_enterprise_org_config(project_name="Acme Org", profile=profile)
    cfg.promotion.allowed_doc_types = ["spec"]
    write_enterprise_config(root, cfg)
    (root / "vault" / "specs").mkdir(parents=True)
    (root / "vault-enterprise").mkdir()
    return root


def seg_config(out_lines: list[str], workdir: Path) -> None:
    from cortex.enterprise.config import (
        build_enterprise_org_config,
        describe_enterprise_topology,
        load_enterprise_config,
        render_enterprise_config_yaml,
        write_enterprise_config,
    )

    for profile in ("small-company", "multi-project-team", "regulated-organization", "custom"):
        cfg = build_enterprise_org_config(
            project_name="Acme Platform", profile=profile,
            github_actions_enabled=True, branch_isolation_enabled=False,
        )
        out_lines.append(render_enterprise_config_yaml(cfg))
        out_lines.append(describe_enterprise_topology(cfg) + "\n")

    # Round-trip + errores contractuales.
    tmp = workdir / "cfgtmp"
    tmp.mkdir(exist_ok=True)
    cfg = build_enterprise_org_config(project_name="Ácme Platform")
    path = write_enterprise_config(tmp, cfg)
    loaded = load_enterprise_config(tmp, required=True)
    out_lines.append(f"roundtrip={loaded == cfg}\npath={path.name}\nslug={loaded.organization.slug}\n")
    try:
        bad = build_enterprise_org_config(project_name="Bad Org")
        bad.memory.enterprise_semantic_enabled = False
        # Revalidar vía model_validate; el contrato es el TEXTO del validador
        # (sin el wrapper de framework de Pydantic).
        type(bad).model_validate(bad.model_dump())
    except ValueError as exc:
        core = exc.errors()[0]["msg"]
        if core.startswith("Value error, "):
            core = core[len("Value error, "):]
        out_lines.append(f"cross_rule={core}\n")


def seg_governance(out_lines: list[str], workdir: Path) -> None:
    from cortex.enterprise.config import build_enterprise_org_config
    from cortex.enterprise.governance import (
        allowed_classifications_for,
        assert_can_promote,
        classification_visible_to,
        team_can_promote,
        user_team,
    )

    org = build_enterprise_org_config(project_name="Org")
    from cortex.enterprise.models import TeamConfig

    org.teams = [
        TeamConfig(id="first", members=["alice"], can_promote=False, can_review=True),
        TeamConfig(id="second", members=["alice"], can_promote=True, can_review=False),
    ]
    org.policies.confidential_visible_to = ["first"]

    rows = {
        "user_alice": user_team("alice", org),
        "user_unknown": user_team("ghost", org),
        "can_promote_first": team_can_promote("first", org),
        "visible_confidential_first": classification_visible_to("confidential", "first", org),
        "visible_confidential_none": classification_visible_to("confidential", None, org),
        "allowed_first": [c for c in allowed_classifications_for("first", org)],
    }
    out_lines.append(json.dumps(rows, sort_keys=False) + "\n")
    try:
        assert_can_promote("alice", org)
    except PermissionError as exc:
        out_lines.append(f"deny={exc}\n")


def seg_promotion_legacy(out_lines: list[str], workdir: Path) -> None:
    from cortex.enterprise.knowledge_promotion import KnowledgePromotionService

    _patch_clocks()
    root = _make_project(workdir / "promo")
    (root / "vault" / "specs" / "auth.md").write_text(
        "---\ntitle: Auth\ntags: [spec]\n---\n\nInitial spec body\n",
        encoding="utf-8",
    )
    svc = KnowledgePromotionService.from_project_root(root)

    candidates = svc.discover_candidates()
    out_lines.append(json.dumps([
        {
            "origin_id": c.origin_id,
            "doc_type": c.doc_type,
            "local_rel_path": c.local_rel_path,
            "dest_rel_path": c.dest_rel_path,
            "fingerprint": c.fingerprint,
            "status": c.status,
            "issues": [i.model_dump() for i in c.issues],
        }
        for c in candidates
    ], indent=1) + "\n")

    record = svc.review(selector=candidates[0].origin_id, approve=True, actor="tester", reason="ok")
    out_lines.append(record.model_dump_json() + "\n")

    plan = svc.plan_promotion()
    written = svc.apply_promotion(candidates=plan, actor="tester")
    dest = svc.paths.enterprise_vault / plan[0].dest_rel_path
    out_lines.append("PROMOTED_FILE_START\n")
    out_lines.append(dest.read_text(encoding="utf-8"))
    out_lines.append("PROMOTED_FILE_END\n")
    out_lines.append(json.dumps({
        "written": len(written),
        "records": svc.paths.records_path.read_text(encoding="utf-8"),
    }, indent=1) + "\n")
    out_lines.append(f"idempotent_discover={svc.discover_candidates() == []}\n")
    shutil.rmtree(root)


def seg_doctype(out_lines: list[str], workdir: Path) -> None:
    from cortex.enterprise.config import build_enterprise_org_config
    from cortex.enterprise.promotion_doctype import promote_note_doctype_aware

    _patch_clocks()
    root = _make_project(workdir / "doctype")
    org = build_enterprise_org_config(project_name="Acme Org")
    ent = root / "vault-enterprise"

    cases = [
        ("session", "---\ndoc_type: session\ntitle: Sprint\nstatus: active\n---\n\n## Key Decisions\n\nKeep Rust\n\n## Noise\n\nDrop me\n"),
        ("runbook", "---\ndoc_type: runbook\ntitle: Deploy\n---\n\nSteps\n"),
    ]
    for family, raw in cases:
        src = root / "vault" / family / "note.md"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(raw, encoding="utf-8")
        result = promote_note_doctype_aware(
            source_path=src,
            enterprise_vault_root=ent,
            org=org,
            project_id="api",
            actor="tester",
            reason=None,
            dry_run=False,
        )
        body = result.target_path.read_text(encoding="utf-8")
        out_lines.append(
            f"CASE {family}\nmode={result.promotion_mode}\nsummarized={result.summarized}\n"
            f"requires_review={result.requires_review}\nFILE_START\n{body}FILE_END\n"
        )
    shutil.rmtree(root)


def seg_review_queue(out_lines: list[str], workdir: Path) -> None:
    from cortex.cli.review_knowledge import list_pending_drafts

    root = workdir / "queue"
    vault = root / "vault-enterprise"
    (vault / "runbooks").mkdir(parents=True)
    (vault / "specs").mkdir()
    (vault / "specs" / "rejected").mkdir()
    (vault / "runbooks" / "b.md").write_text(
        "---\ndoc_type: runbook\nstatus: draft\ntitle: B\nowner: ana\n---\nB\n", encoding="utf-8"
    )
    (vault / "specs" / "a.md").write_text(
        "---\ndoc_type: spec\nstatus: draft\ntitle: A\nowner: bob\n---\nB\n", encoding="utf-8"
    )
    (vault / "specs" / "pub.md").write_text(
        "---\nstatus: published\n---\nB\n", encoding="utf-8"
    )
    (vault / "specs" / "rejected" / "skip.md").write_text(
        "---\nstatus: draft\n---\nB\n", encoding="utf-8"
    )
    pending = list_pending_drafts(vault)
    out_lines.append(json.dumps(pending, indent=1, default=str) + "\n")
    shutil.rmtree(root)


def seg_retention(out_lines: list[str], workdir: Path) -> None:
    from cortex.enterprise.config import build_enterprise_org_config
    from cortex.enterprise.maintenance import archive_violations, scan_retention_violations

    now = datetime(2026, 8, 25, tzinfo=UTC)
    root = workdir / "retention"
    (root / "_archived").mkdir(parents=True)
    (root / "archived.md").write_text("---\ndoc_type: hu\ncreated_at: '2025-01-01T00:00:00+00:00'\n---\nB\n", encoding="utf-8")
    (root / "zero.md").write_text("---\ndoc_type: changelog\ncreated_at: '2020-01-01'\n---\nB\n", encoding="utf-8")
    (root / "no-type.md").write_text("---\ntitle: X\n---\nB\n", encoding="utf-8")
    (root / "overdue.md").write_text("---\ndoc_type: hu\ncreated_at: '2024-06-01T00:00:00+00:00'\n---\nB\n", encoding="utf-8")

    org = build_enterprise_org_config(project_name="Org")
    hits = scan_retention_violations(root, org=org, now=now)
    out_lines.append(json.dumps([
        {
            "path": h.path.relative_to(root).as_posix(),
            "doc_type": h.doc_type,
            "retention_days": h.retention_days,
            "days_overdue": h.days_overdue,
        }
        for h in hits
    ], indent=1) + "\n")
    moved = archive_violations(hits, root, dry_run=True)
    out_lines.append(json.dumps([m.relative_to(root).as_posix() for m in moved]) + "\n")
    shutil.rmtree(root)


def seg_retrieval(out_lines: list[str], workdir: Path) -> None:
    from cortex.enterprise.config import build_enterprise_org_config
    from cortex.enterprise import sources as src_mod
    from cortex.enterprise.retrieval_service import EnterpriseRetrievalService
    from cortex.models import EpisodicHit, MemoryEntry, SemanticDocument

    cfg = build_enterprise_org_config(project_name="Acme", profile="multi-project-team")
    service = EnterpriseRetrievalService(
        enterprise_config=cfg,
        local_project_id="acme-project",
        project_root=Path.cwd(),
        local_vault_path="vault",
        local_episodic_dir=".memory/chroma",
        local_collection_name="cortex_episodic",
        embedding_model="all-MiniLM-L6-v2",
        embedding_backend="onnx",
    )

    def fake_vault(self, query, top_k, use_embeddings=True):
        out = []
        for source in self.sources:
            doc = SemanticDocument(
                path=f"{source.scope.value}/same.md" if hasattr(source.scope, "value") else f"{source.scope}/same.md",
                title="Same", content="x", score=0.9,
                origin_scope=str(source.scope),
                origin_project_id=source.project_id,
                origin_vault=source.path,
                origin_persist_dir="",
            )
            out.append(doc)
        return out

    def fake_episodic(self, query, top_k, use_embeddings=True):
        return []

    orig_vault, orig_episodic = src_mod.MultiVaultReader.search, src_mod.MultiEpisodicReader.search
    src_mod.MultiVaultReader.search = fake_vault
    src_mod.MultiEpisodicReader.search = fake_episodic
    try:
        result = service.search(query="q", scope="all", top_k=10)
    finally:
        src_mod.MultiVaultReader.search = orig_vault
        src_mod.MultiEpisodicReader.search = orig_episodic

    out_lines.append(json.dumps({
        "unified": [
            {"source": h.source, "score": round(h.score, 12),
             "scope": h.metadata.get("scope"), "project": h.metadata.get("project_id")}
            for h in result.unified_hits
        ],
        "breakdown": result.source_breakdown,
    }, indent=1) + "\n")
    _ = workdir


def seg_reporting(out_lines: list[str], workdir: Path) -> None:
    """Reporting con doctor REAL de Python convertido a snapshot neutral."""
    from cortex.doctor import DoctorCheck, DoctorReport, run_doctor
    from cortex.enterprise.reporting import EnterpriseReportingService

    root = _make_project(workdir / "report")
    doctor = run_doctor(root, scope="enterprise")
    snapshot = DoctorReport(
        project_root=doctor.project_root,
        checks=[
            DoctorCheck(name=c.name, ok=c.ok, severity=c.severity, detail=c.detail)
            for c in doctor.checks
        ],
    )

    service = EnterpriseReportingService.from_project_root(root)
    report = service.build_memory_report(scope="all")

    payload = {
        "project_root": ROOT_MARK,
        "enterprise_enabled": report.enterprise_enabled,
        "sources": [
            {
                "scope": s.scope,
                "markdown_files": s.markdown_files,
                "validation_errors": s.validation_errors,
                "validation_warnings": s.validation_warnings,
                "notes": s.notes,
            }
            for s in report.sources
        ],
        "promotion": {
            "enabled": report.promotion.enabled,
            "require_review": report.promotion.require_review,
            "candidates_discovered": report.promotion.candidates_discovered,
        },
        "doctor": {
            "has_failures": snapshot.has_failures,
            "check_names": [c.name for c in snapshot.checks],
        },
    }
    out_lines.append(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    shutil.rmtree(root)


SEGMENTS = [
    ("config", seg_config),
    ("governance", seg_governance),
    ("promotion_legacy", seg_promotion_legacy),
    ("doctype", seg_doctype),
    ("review_queue", seg_review_queue),
    ("retention", seg_retention),
    ("retrieval", seg_retrieval),
    ("reporting", seg_reporting),
]


def build(out_dir: Path) -> int:
    workdir = out_dir / ".work"
    shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for name, fn in SEGMENTS:
        lines.append(SEGMENT.format(name=name) + "\n")
        buf: list[str] = []
        fn(buf, workdir)
        joined = "".join(buf)
        joined = norm(joined, workdir.parent.parent.parent.parent)
        lines.append(joined)
        lines[-1] = joined.rstrip("\n") + "\n"
    golden = out_dir / "golden_enterprise.txt"
    golden.write_text("".join(lines), encoding="utf-8")
    shutil.rmtree(workdir, ignore_errors=True)
    print(f"[OK] golden generado: {golden}")
    return 0


def verify(out_dir: Path) -> int:
    golden = out_dir / "golden_enterprise.txt"
    backup = out_dir / "golden_backup.txt"
    if not golden.exists():
        print("[FAIL] no existe el golden; corré build primero")
        return 1
    expected = golden.read_text(encoding="utf-8")
    rc = build(out_dir)
    _ = rc
    actual = out_dir / "golden_enterprise.txt"
    if actual.read_text(encoding="utf-8") == expected:
        if not backup.exists():
            backup.write_text(expected, encoding="utf-8")
        print("[PASS] golden_enterprise.txt determinista")
        return 0
    print("[FAIL] golden difiere entre build y verify")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "verify"])
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    out_dir = Path(ns.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    return build(out_dir) if ns.cmd == "build" else verify(out_dir)


if __name__ == "__main__":
    sys.exit(main())
