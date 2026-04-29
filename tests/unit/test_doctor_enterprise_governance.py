from __future__ import annotations

from pathlib import Path

from cortex.doctor import run_doctor
from cortex.enterprise.config import build_enterprise_org_config, write_enterprise_config


def _check_map(report) -> dict[str, object]:
    return {c.name: c for c in report.checks}


def test_doctor_enterprise_reports_promotion_checks_when_enabled(tmp_path: Path) -> None:
    # Minimal project structure
    (tmp_path / "config.yaml").write_text("semantic:\n  vault_path: vault\n", encoding="utf-8")
    (tmp_path / "vault").mkdir(parents=True, exist_ok=True)

    cfg = build_enterprise_org_config(project_name="Acme Org", profile="small-company")
    cfg.promotion.enabled = True
    cfg.promotion.allowed_doc_types = ["spec"]
    write_enterprise_config(tmp_path, cfg)

    (tmp_path / "vault-enterprise").mkdir(parents=True, exist_ok=True)
    (tmp_path / "vault-enterprise" / "runbooks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "vault-enterprise" / "runbooks" / "hello.md").write_text(
        "---\n"
        'title: "Hello"\n'
        "tags: [runbook]\n"
        "---\n\n"
        "Body\n",
        encoding="utf-8",
    )

    report = run_doctor(tmp_path, scope="enterprise")
    checks = _check_map(report)

    assert "enterprise_vault_validation_errors" in checks
    assert "enterprise_promotion_allowed_doc_types" in checks
    assert "enterprise_promotion_dir" in checks
    assert "enterprise_promotion_records_presence" in checks


def test_doctor_enterprise_fails_when_allowed_doc_types_empty(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text("semantic:\n  vault_path: vault\n", encoding="utf-8")
    (tmp_path / "vault").mkdir(parents=True, exist_ok=True)

    cfg = build_enterprise_org_config(project_name="Acme Org", profile="small-company")
    cfg.promotion.enabled = True
    cfg.promotion.allowed_doc_types = []
    write_enterprise_config(tmp_path, cfg)

    (tmp_path / "vault-enterprise").mkdir(parents=True, exist_ok=True)

    report = run_doctor(tmp_path, scope="enterprise")
    checks = _check_map(report)
    assert checks["enterprise_promotion_allowed_doc_types"].ok is False

