from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

from cortex.doc_validator import DocValidator
from cortex.enterprise.config import load_enterprise_config
from cortex.enterprise.promotion_models import (
    PromotionCandidate,
    PromotionDecision,
    PromotionIssue,
    PromotionRecord,
    PromotionRecordEvent,
)
from cortex.runtime_context import slugify


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class PromotionPaths:
    project_root: Path
    local_vault: Path
    enterprise_vault: Path
    records_path: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str, bool]:
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw, False
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        data = {}
    body = raw[m.end() :]
    if not isinstance(data, dict):
        data = {}
    return data, body, True


def _upsert_frontmatter(raw: str, updates: dict[str, Any]) -> str:
    fm, body, had = _split_frontmatter(raw)
    fm.update({k: v for k, v in updates.items() if v is not None})
    fm_yaml = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    fm_block = f"---\n{fm_yaml}\n---\n\n"
    body_clean = body.lstrip("\n")
    if had:
        return fm_block + body_clean
    return fm_block + raw.lstrip("\n")


def _normalized_markdown_fingerprint(raw: str) -> str:
    fm, body, _ = _split_frontmatter(raw.replace("\r\n", "\n"))
    _ = fm
    body_norm = body.strip() + "\n"
    return hashlib.sha256(body_norm.encode("utf-8")).hexdigest()


def _doc_type_from_rel_path(rel_path: str) -> str | None:
    first = rel_path.split("/", 1)[0].strip().lower()
    mapping = {
        "specs": "spec",
        "decisions": "decision",
        "runbooks": "runbook",
        "hu": "hu",
        "incidents": "incident",
        "sessions": "session",
    }
    return mapping.get(first)


class PromotionRepository:
    def __init__(self, records_path: Path) -> None:
        self.records_path = records_path
        self.records_path.parent.mkdir(parents=True, exist_ok=True)

    def iter_records(self) -> Iterable[PromotionRecord]:
        if not self.records_path.exists():
            return
        for line in self.records_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                yield PromotionRecord.model_validate(payload)
            except Exception:
                continue

    def load_latest_by_origin_id(self) -> dict[str, PromotionRecord]:
        latest: dict[str, PromotionRecord] = {}
        for rec in self.iter_records():
            latest[rec.origin_id] = rec
        return latest

    def append(self, record: PromotionRecord) -> None:
        self.records_path.parent.mkdir(parents=True, exist_ok=True)
        with self.records_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(record.model_dump_json())
            f.write("\n")


class PromotionRulesEngine:
    def __init__(self, *, allowed_doc_types: set[str]) -> None:
        self.allowed_doc_types = allowed_doc_types

    def is_promotable(self, rel_path: str) -> tuple[bool, str]:
        if rel_path.startswith(".cortex/"):
            return False, "internal cortex metadata"
        doc_type = _doc_type_from_rel_path(rel_path)
        if doc_type is None:
            return False, "unknown doc family (not under a recognized vault folder)"
        if doc_type == "session" and "session" not in self.allowed_doc_types:
            return False, "sessions excluded by default (not enabled in org promotion.allowed_doc_types)"
        if doc_type not in self.allowed_doc_types:
            return False, f"doc_type '{doc_type}' not allowed by org promotion.allowed_doc_types"
        return True, "allowed"


class KnowledgePromotionService:
    def __init__(self, paths: PromotionPaths, *, org_slug: str, require_review: bool) -> None:
        self.paths = paths
        self.org_slug = org_slug
        self.require_review = require_review
        self.repo = PromotionRepository(paths.records_path)
        self.validator = DocValidator(vault_path=paths.local_vault)

    @staticmethod
    def from_project_root(project_root: Path) -> "KnowledgePromotionService":
        config = load_enterprise_config(project_root, required=True)
        if config is None:
            raise FileNotFoundError("Enterprise config (.cortex/org.yaml) is required for promotion.")
        enterprise_vault = config.resolve_enterprise_vault_path(project_root)
        if enterprise_vault is None:
            raise ValueError("Enterprise vault is disabled (memory.enterprise_semantic_enabled=false).")
        local_vault = (project_root / "vault").resolve()
        org_slug = config.organization.slug or slugify(config.organization.name, fallback="organization")
        records_path = (enterprise_vault / ".cortex" / "promotion" / "records.jsonl").resolve()
        paths = PromotionPaths(
            project_root=project_root.resolve(),
            local_vault=local_vault,
            enterprise_vault=enterprise_vault.resolve(),
            records_path=records_path,
        )
        return KnowledgePromotionService(paths, org_slug=org_slug, require_review=config.promotion.require_review)

    def _project_slug(self) -> str:
        return slugify(self.paths.project_root.name, fallback="project")

    def _origin_id(self, local_rel_path: str) -> str:
        return f"{self._project_slug()}:{local_rel_path}"

    def _dest_rel_path(self, local_rel_path: str) -> str:
        parts = local_rel_path.split("/", 1)
        family = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        if rest:
            return f"{family}/{self._project_slug()}/{rest}"
        return f"{family}/{self._project_slug()}/{Path(local_rel_path).name}"

    def discover_candidates(self) -> list[PromotionCandidate]:
        config = load_enterprise_config(self.paths.project_root, required=True)
        assert config is not None
        rules = PromotionRulesEngine(allowed_doc_types=set(config.promotion.allowed_doc_types))
        latest = self.repo.load_latest_by_origin_id()

        if not self.paths.local_vault.exists():
            return []

        candidates: list[PromotionCandidate] = []
        for md_path in sorted(self.paths.local_vault.rglob("*.md")):
            rel = str(md_path.relative_to(self.paths.local_vault)).replace("\\", "/")
            ok, _reason = rules.is_promotable(rel)
            if not ok:
                continue

            raw = md_path.read_text(encoding="utf-8")
            fingerprint = _normalized_markdown_fingerprint(raw)
            origin_id = self._origin_id(rel)
            dest_rel = self._dest_rel_path(rel)
            doc_type = _doc_type_from_rel_path(rel) or "unknown"

            issues: list[PromotionIssue] = []
            vr = self.validator.validate_file(md_path)
            for issue in vr.issues:
                issues.append(
                    PromotionIssue(
                        file=issue.file,
                        field=issue.field,
                        message=issue.message,
                        severity=issue.severity,  # type: ignore[arg-type]
                    )
                )

            status = "candidate"
            existing = latest.get(origin_id)
            if existing and existing.status == "promoted" and existing.fingerprint == fingerprint:
                continue
            if existing and existing.fingerprint != fingerprint:
                status = "candidate"

            candidates.append(
                PromotionCandidate(
                    origin_id=origin_id,
                    doc_type=doc_type,
                    local_rel_path=rel,
                    local_abs_path=str(md_path),
                    dest_rel_path=dest_rel,
                    fingerprint=fingerprint,
                    status=status,
                    issues=issues,
                    metadata={"discovered_at": _utc_now()},
                )
            )
        return candidates

    def review(self, *, selector: str, approve: bool, actor: str, reason: str | None = None) -> PromotionRecord:
        candidates = self.discover_candidates()
        match = None
        for c in candidates:
            if c.origin_id == selector or c.local_rel_path == selector:
                match = c
                break
        if match is None:
            raise ValueError(f"No candidate found for selector: {selector}")

        if any(i.severity == "error" for i in match.issues):
            raise ValueError("Cannot review a document with validation errors.")

        decision = PromotionDecision(
            decision="approve" if approve else "reject",
            actor=actor,
            reason=reason,
        )
        status = "reviewed" if approve else "rejected"
        event = PromotionRecordEvent(
            event=status, actor=actor, payload={"reason": reason} if reason else {}
        )
        record = PromotionRecord(
            origin_id=match.origin_id,
            local_rel_path=match.local_rel_path,
            doc_type=match.doc_type,
            dest_rel_path=match.dest_rel_path,
            fingerprint=match.fingerprint,
            status=status,  # type: ignore[arg-type]
            decision=decision,
            events=[PromotionRecordEvent(event="candidate", payload={"fingerprint": match.fingerprint}), event],
        )
        self.repo.append(record)
        return record

    def plan_promotion(self) -> list[PromotionCandidate]:
        candidates = self.discover_candidates()
        latest = self.repo.load_latest_by_origin_id()
        promotable: list[PromotionCandidate] = []

        for c in candidates:
            rec = latest.get(c.origin_id)
            if self.require_review:
                if rec is None or rec.status != "reviewed" or rec.fingerprint != c.fingerprint:
                    continue
            if any(i.severity == "error" for i in c.issues):
                continue
            promotable.append(c)

        return promotable

    def apply_promotion(self, *, candidates: list[PromotionCandidate], actor: str) -> list[PromotionRecord]:
        latest = self.repo.load_latest_by_origin_id()
        written: list[PromotionRecord] = []

        for c in candidates:
            existing = latest.get(c.origin_id)
            if existing and existing.status == "promoted" and existing.fingerprint == c.fingerprint:
                continue

            src = self.paths.local_vault / c.local_rel_path
            dest = self.paths.enterprise_vault / c.dest_rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)

            raw = src.read_text(encoding="utf-8")
            promoted_raw = _upsert_frontmatter(
                raw,
                {
                    "promotion_status": "promoted",
                    "promotion_origin_id": c.origin_id,
                    "promotion_origin_path": c.local_rel_path,
                    "promotion_origin_project": self._project_slug(),
                    "promotion_fingerprint": c.fingerprint,
                    "promotion_promoted_at": _utc_now(),
                },
            )
            dest.write_text(promoted_raw, encoding="utf-8", newline="\n")

            ev_candidate = PromotionRecordEvent(event="candidate", payload={"fingerprint": c.fingerprint})
            ev_promoted = PromotionRecordEvent(event="promoted", actor=actor)
            record = PromotionRecord(
                origin_id=c.origin_id,
                local_rel_path=c.local_rel_path,
                doc_type=c.doc_type,
                dest_rel_path=c.dest_rel_path,
                fingerprint=c.fingerprint,
                status="promoted",
                decision=existing.decision if existing else None,
                events=[ev_candidate, ev_promoted],
            )
            self.repo.append(record)
            written.append(record)

        return written

