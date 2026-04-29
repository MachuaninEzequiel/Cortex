from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from cortex.doctor import DoctorCheck, DoctorReport, run_doctor
from cortex.enterprise.config import discover_enterprise_config_path, load_enterprise_config
from cortex.enterprise.knowledge_promotion import KnowledgePromotionService

ReportingScope = Literal["local", "enterprise", "all"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PromotionEventSummary(BaseModel):
    origin_id: str
    status: str
    actor: str | None = None
    updated_at: str | None = None


class PromotionReport(BaseModel):
    enabled: bool = False
    require_review: bool = True
    records_path: str | None = None
    candidates_discovered: int = 0
    candidates_ready_to_promote: int = 0
    latest_events: list[PromotionEventSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MemorySourceReport(BaseModel):
    scope: ReportingScope
    vault_path: str | None = None
    markdown_files: int = 0
    validation_errors: int = 0
    validation_warnings: int = 0
    notes: list[str] = Field(default_factory=list)


class MemoryReportPayload(BaseModel):
    generated_at: str = Field(default_factory=_utc_now)
    project_root: str
    enterprise_enabled: bool = False
    sources: list[MemorySourceReport] = Field(default_factory=list)
    promotion: PromotionReport = Field(default_factory=PromotionReport)
    doctor: dict[str, Any] = Field(default_factory=dict)


class EnterpriseReportingService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    @staticmethod
    def from_project_root(project_root: Path) -> "EnterpriseReportingService":
        return EnterpriseReportingService(project_root)

    def build_memory_report(self, *, scope: ReportingScope = "all") -> MemoryReportPayload:
        # Always compute doctor once; we will slice it into the report.
        doctor_scope = "enterprise" if scope in {"enterprise", "all"} else "project"
        doctor = run_doctor(self.project_root, scope=doctor_scope)  # type: ignore[arg-type]

        payload = MemoryReportPayload(
            project_root=str(self.project_root),
            enterprise_enabled=discover_enterprise_config_path(self.project_root) is not None,
            doctor=_doctor_to_payload(doctor),
        )

        if scope in {"local", "all"}:
            payload.sources.append(self._local_source(doctor))

        if scope in {"enterprise", "all"}:
            enterprise = self._enterprise_source(doctor)
            if enterprise is not None:
                payload.sources.append(enterprise)

        # Promotion is enterprise-only, but we still expose a stable shape.
        if scope in {"enterprise", "all"}:
            payload.promotion = self._promotion_report()

        return payload

    def _local_source(self, doctor: DoctorReport) -> MemorySourceReport:
        vault_path = (self.project_root / "vault").resolve()
        md_count = _count_markdown_files(vault_path) if vault_path.exists() else 0
        errors = _extract_check_count(doctor.checks, "vault_validation_errors")
        warnings = _extract_check_count(doctor.checks, "vault_validation_warnings")
        notes: list[str] = []
        if not vault_path.exists():
            notes.append("vault/ directory missing")
        return MemorySourceReport(
            scope="local",
            vault_path=str(vault_path),
            markdown_files=md_count,
            validation_errors=errors,
            validation_warnings=warnings,
            notes=notes,
        )

    def _enterprise_source(self, doctor: DoctorReport) -> MemorySourceReport | None:
        cfg_path = discover_enterprise_config_path(self.project_root)
        if cfg_path is None:
            return None
        cfg = load_enterprise_config(self.project_root, required=True, path=cfg_path)
        assert cfg is not None
        enterprise_vault = cfg.resolve_enterprise_vault_path(self.project_root)
        md_count = _count_markdown_files(enterprise_vault) if enterprise_vault and enterprise_vault.exists() else 0
        errors = _extract_check_count(doctor.checks, "enterprise_vault_validation_errors")
        warnings = _extract_check_count(doctor.checks, "enterprise_vault_validation_warnings")
        notes: list[str] = []
        if enterprise_vault is None:
            notes.append("enterprise vault disabled (memory.enterprise_semantic_enabled=false)")
        elif not enterprise_vault.exists():
            notes.append("enterprise vault directory missing")
        return MemorySourceReport(
            scope="enterprise",
            vault_path=str(enterprise_vault) if enterprise_vault is not None else None,
            markdown_files=md_count,
            validation_errors=errors,
            validation_warnings=warnings,
            notes=notes,
        )

    def _promotion_report(self) -> PromotionReport:
        cfg_path = discover_enterprise_config_path(self.project_root)
        if cfg_path is None:
            return PromotionReport(enabled=False, warnings=["enterprise config missing (.cortex/org.yaml)"])
        cfg = load_enterprise_config(self.project_root, required=True, path=cfg_path)
        assert cfg is not None
        if not cfg.promotion.enabled:
            return PromotionReport(enabled=False, require_review=cfg.promotion.require_review)

        try:
            service = KnowledgePromotionService.from_project_root(self.project_root)
        except Exception as exc:
            return PromotionReport(
                enabled=True,
                require_review=cfg.promotion.require_review,
                warnings=[f"promotion reporting unavailable: {exc}"],
            )

        candidates = service.discover_candidates()
        ready = service.plan_promotion()
        latest = service.repo.load_latest_by_origin_id()
        latest_events = _summarize_latest_events(latest, limit=10)
        return PromotionReport(
            enabled=True,
            require_review=service.require_review,
            records_path=str(service.paths.records_path),
            candidates_discovered=len(candidates),
            candidates_ready_to_promote=len(ready),
            latest_events=latest_events,
        )


def _doctor_to_payload(report: DoctorReport) -> dict[str, Any]:
    return {
        "project_root": str(report.project_root),
        "checks": [
            {
                "name": c.name,
                "ok": c.ok,
                "severity": c.severity,
                "detail": c.detail,
            }
            for c in report.checks
        ],
        "has_failures": report.has_failures,
        "has_warnings": report.has_warnings,
    }


def _extract_check_count(checks: list[DoctorCheck], name: str) -> int:
    for c in checks:
        if c.name != name:
            continue
        # doctor detail is like: "<n> error(s) across ..." for these checks
        parts = str(c.detail).strip().split(" ", 1)
        if parts and parts[0].isdigit():
            return int(parts[0])
        return 0 if c.ok else 1
    return 0


def _count_markdown_files(root: Path | None) -> int:
    if root is None or not root.exists():
        return 0
    return sum(1 for _ in root.rglob("*.md"))


def _summarize_latest_events(latest_by_origin: dict[str, Any], *, limit: int) -> list[PromotionEventSummary]:
    # latest_by_origin contains PromotionRecord objects; we avoid importing models here.
    items: list[PromotionEventSummary] = []
    for origin_id, rec in latest_by_origin.items():
        status = getattr(rec, "status", "unknown")
        actor = None
        updated_at = None
        events = getattr(rec, "events", []) or []
        if events:
            last = events[-1]
            actor = getattr(last, "actor", None)
            updated_at = getattr(last, "at", None)
        items.append(PromotionEventSummary(origin_id=str(origin_id), status=str(status), actor=actor, updated_at=updated_at))
    # Sort by updated_at when present, else by origin_id.
    items.sort(key=lambda e: (e.updated_at or "", e.origin_id), reverse=True)
    return items[:limit]

