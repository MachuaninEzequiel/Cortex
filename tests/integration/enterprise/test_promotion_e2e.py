from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cortex.enterprise.config import build_enterprise_org_config, write_enterprise_config
from cortex.enterprise.knowledge_promotion import KnowledgePromotionService


def _write_md(path: Path, *, title: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\n"
        f'title: "{title}"\n'
        f"tags: [spec]\n"
        f"---\n\n"
        f"{body}\n",
        encoding="utf-8",
        newline="\n",
    )


def test_promotion_pipeline_review_then_promote_is_idempotent(tmp_path: Path) -> None:
    project_root = tmp_path / "acme-api"
    project_root.mkdir(parents=True)

    cfg = build_enterprise_org_config(project_name="Acme Org", profile="small-company")
    cfg.promotion.require_review = True
    cfg.promotion.allowed_doc_types = ["spec"]
    write_enterprise_config(project_root, cfg)

    # Explicit new-layout marker
    (project_root / ".cortex" / "workspace.yaml").write_text(
        yaml.safe_dump({"layout_version": 2, "projects": []}),
        encoding="utf-8",
    )

    # Local + enterprise vaults (new-layout: under .cortex/)
    local_doc = project_root / ".cortex" / "vault" / "specs" / "2026-01-01_auth.md"
    _write_md(local_doc, title="Auth", body="Initial spec body")
    (project_root / ".cortex" / "vault-enterprise").mkdir(parents=True, exist_ok=True)

    service = KnowledgePromotionService.from_project_root(project_root)

    # Discover -> no record yet, candidate exists
    candidates = service.discover_candidates()
    assert len(candidates) == 1
    selector = candidates[0].origin_id

    # Without review, nothing planned
    assert service.plan_promotion() == []

    # Review approve
    record = service.review(selector=selector, approve=True, actor="tester", reason="ok")
    assert record.status == "reviewed"

    # Now promotion is planned
    plan = service.plan_promotion()
    assert len(plan) == 1

    # Apply promotion
    written = service.apply_promotion(candidates=plan, actor="tester")
    assert len(written) == 1
    assert written[0].status == "promoted"

    dest = service.paths.enterprise_vault / plan[0].dest_rel_path
    assert dest.exists()
    text = dest.read_text(encoding="utf-8")
    assert "promotion_origin_id" in text
    assert "promotion_fingerprint" in text
    assert "promotion_promoted_at" in text

    # Re-running should be idempotent (no candidates left)
    assert service.discover_candidates() == []
    assert service.plan_promotion() == []


def test_promotion_requires_re_review_when_content_changes(tmp_path: Path) -> None:
    project_root = tmp_path / "acme-api"
    project_root.mkdir(parents=True)

    cfg = build_enterprise_org_config(project_name="Acme Org", profile="small-company")
    cfg.promotion.require_review = True
    cfg.promotion.allowed_doc_types = ["spec"]
    write_enterprise_config(project_root, cfg)

    # Explicit new-layout marker
    (project_root / ".cortex" / "workspace.yaml").write_text(
        yaml.safe_dump({"layout_version": 2, "projects": []}),
        encoding="utf-8",
    )

    local_doc = project_root / ".cortex" / "vault" / "specs" / "2026-01-01_auth.md"
    _write_md(local_doc, title="Auth", body="Initial spec body")
    (project_root / ".cortex" / "vault-enterprise").mkdir(parents=True, exist_ok=True)

    service = KnowledgePromotionService.from_project_root(project_root)
    selector = service.discover_candidates()[0].origin_id
    service.review(selector=selector, approve=True, actor="tester")
    plan = service.plan_promotion()
    service.apply_promotion(candidates=plan, actor="tester")

    # Change source content
    _write_md(local_doc, title="Auth", body="Changed spec body")

    # Candidate should reappear, but not planned until reviewed again
    candidates = service.discover_candidates()
    assert len(candidates) == 1
    assert service.plan_promotion() == []


def test_review_rejects_documents_with_validation_errors(tmp_path: Path) -> None:
    project_root = tmp_path / "acme-api"
    project_root.mkdir(parents=True)

    cfg = build_enterprise_org_config(project_name="Acme Org", profile="small-company")
    cfg.promotion.require_review = True
    cfg.promotion.allowed_doc_types = ["spec"]
    write_enterprise_config(project_root, cfg)

    # Explicit new-layout marker
    (project_root / ".cortex" / "workspace.yaml").write_text(
        yaml.safe_dump({"layout_version": 2, "projects": []}),
        encoding="utf-8",
    )
    (project_root / ".cortex" / "vault-enterprise").mkdir(parents=True, exist_ok=True)

    # Invalid YAML frontmatter (parsing error -> severity=error)
    bad_doc = project_root / ".cortex" / "vault" / "specs" / "bad.md"
    bad_doc.parent.mkdir(parents=True, exist_ok=True)
    bad_doc.write_text("---\n: bad yaml\n---\n\nBody\n", encoding="utf-8", newline="\n")

    service = KnowledgePromotionService.from_project_root(project_root)
    selector = service.discover_candidates()[0].origin_id

    with pytest.raises(ValueError):
        service.review(selector=selector, approve=True, actor="tester")


def test_promotion_new_layout_paths_are_consistent(tmp_path: Path) -> None:
    """Explicit new-layout: assert that service paths resolve under .cortex/."""
    project_root = tmp_path / "acme-api"
    project_root.mkdir(parents=True)

    cfg = build_enterprise_org_config(project_name="Acme Org", profile="small-company")
    cfg.promotion.require_review = True
    cfg.promotion.allowed_doc_types = ["spec"]
    write_enterprise_config(project_root, cfg)

    (project_root / ".cortex" / "workspace.yaml").write_text(
        yaml.safe_dump({"layout_version": 2, "projects": []}),
        encoding="utf-8",
    )

    local_doc = project_root / ".cortex" / "vault" / "specs" / "auth.md"
    _write_md(local_doc, title="Auth", body="Body")
    (project_root / ".cortex" / "vault-enterprise").mkdir(parents=True, exist_ok=True)

    service = KnowledgePromotionService.from_project_root(project_root)

    assert service.paths.local_vault == project_root / ".cortex" / "vault"
    assert service.paths.enterprise_vault == project_root / ".cortex" / "vault-enterprise"
    assert service.paths.records_path == (
        project_root / ".cortex" / "vault-enterprise" / "promotion" / "records.jsonl"
    )

    candidates = service.discover_candidates()
    assert len(candidates) == 1
    record = service.review(selector=candidates[0].origin_id, approve=True, actor="tester")
    assert record.status == "reviewed"
    plan = service.plan_promotion()
    assert len(plan) == 1
    written = service.apply_promotion(candidates=plan, actor="tester")
    assert len(written) == 1


def test_promotion_legacy_layout_paths_are_consistent(tmp_path: Path) -> None:
    """Explicit legacy layout: assert that service paths resolve at repo root."""
    project_root = tmp_path / "acme-api"
    project_root.mkdir(parents=True)

    # Legacy markers: config.yaml at root
    (project_root / "config.yaml").write_text("episodic:\n  persist_dir: .memory\n", encoding="utf-8")

    cfg = build_enterprise_org_config(project_name="Acme Org", profile="small-company")
    cfg.promotion.require_review = True
    cfg.promotion.allowed_doc_types = ["spec"]
    write_enterprise_config(project_root, cfg)

    local_doc = project_root / "vault" / "specs" / "auth.md"
    _write_md(local_doc, title="Auth", body="Body")
    (project_root / "vault-enterprise").mkdir(parents=True, exist_ok=True)

    service = KnowledgePromotionService.from_project_root(project_root)

    assert service.paths.local_vault == project_root / "vault"
    assert service.paths.enterprise_vault == project_root / "vault-enterprise"
    assert service.paths.records_path == (
        project_root / "vault-enterprise" / ".cortex" / "promotion" / "records.jsonl"
    )

    candidates = service.discover_candidates()
    assert len(candidates) == 1
    record = service.review(selector=candidates[0].origin_id, approve=True, actor="tester")
    assert record.status == "reviewed"
    plan = service.plan_promotion()
    assert len(plan) == 1
    written = service.apply_promotion(candidates=plan, actor="tester")
    assert len(written) == 1

