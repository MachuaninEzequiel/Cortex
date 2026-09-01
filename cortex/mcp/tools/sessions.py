"""Handlers MCP del dominio sesiones/checkpoints/tasks (mixín de CortexMCPServer).

Extraído del monolito server.py (deuda V1, Obra 01 fase P3). Los métodos
conservan su firma y semántica ``self.`` exactas; el contrato observable
está congelado por tests/unit/mcp/test_golden_contract.py.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cortex.mcp.schemas import _CHECKPOINT_SOURCE_VALUES

logger = logging.getLogger(__name__)


class SessionToolsMixin:
    """Mixín: handlers MCP de sesiones/checkpoints/tasks."""

    def _save_session_text(self, arguments: dict[str, Any]) -> str:
        path = self.memory.save_session_note(
            title=arguments.get("title", ""),
            spec_summary=arguments.get("spec_summary", ""),
            changes_made=arguments.get("changes_made", []),
            files_touched=arguments.get("files_touched", []),
            key_decisions=arguments.get("key_decisions", []),
            next_steps=arguments.get("next_steps", []),
            tags=arguments.get("tags", []),
            sync_vault=not arguments.get("no_sync", False),
            handoff=bool(arguments.get("handoff", False)),
            blockers=list(arguments.get("blockers", []) or []),
            verified_state=list(arguments.get("verified_state", []) or []),
            unverified_claims=list(arguments.get("unverified_claims", []) or []),
            suggested_skills=list(arguments.get("suggested_skills", []) or []),
        )
        return f"Session note saved -> {path}"

    # ------------------------------------------------------------------
    # Pluggable Middle — Session primitive (Fase 00 / T0.7)
    # ------------------------------------------------------------------

    _VALID_CHECKPOINT_SOURCES: tuple[str, ...] = _CHECKPOINT_SOURCE_VALUES
    _VALID_CLOSE_STATUSES: tuple[str, ...] = ("closed", "handoff", "abandoned")

    def _session_open_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_open``."""
        spec_id = str(arguments.get("spec_id", "")).strip()
        spec_path = str(arguments.get("spec_path", "")).strip()
        if not spec_id or not spec_path:
            return "❌ spec_id and spec_path are required for cortex_session_open."

        record = self.memory.open_session(
            spec_id=spec_id,
            spec_path=spec_path,
            spec_summary=str(arguments.get("spec_summary", "")),
        )
        payload = {
            "session_id": record.session_id,
            "opened_at": record.opened_at.isoformat(),
            "start_commit": record.start_commit,
            "start_branch": record.start_branch,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _session_checkpoint_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_checkpoint``."""
        session_id = str(arguments.get("session_id", "")).strip()
        source = str(arguments.get("source", "")).strip()
        if not session_id or not source:
            return "❌ session_id and source are required for cortex_session_checkpoint."
        if source not in self._VALID_CHECKPOINT_SOURCES:
            return (
                f"❌ Invalid source {source!r}. Must be one of: "
                f"{', '.join(self._VALID_CHECKPOINT_SOURCES)}"
            )

        record = self.memory.checkpoint_session(
            session_id,
            source=source,
            verified_claims=list(arguments.get("verified_claims", []) or []),
            unverified_claims=list(arguments.get("unverified_claims", []) or []),
            artifacts_touched=list(arguments.get("artifacts_touched", []) or []),
            note=str(arguments.get("note", "")),
        )
        last = record.checkpoints[-1] if record.checkpoints else None
        payload = {
            "session_id": record.session_id,
            "checkpoint_count": len(record.checkpoints),
            "last_checkpoint_at": last.timestamp.isoformat() if last else None,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _session_close_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_close``."""
        session_id = str(arguments.get("session_id", "")).strip()
        status = str(arguments.get("status", "")).strip()
        documenter_decision = str(arguments.get("documenter_decision", "")).strip()
        if not session_id or not status or not documenter_decision:
            return (
                "❌ session_id, status and documenter_decision are required "
                "for cortex_session_close."
            )
        if status not in self._VALID_CLOSE_STATUSES:
            return (
                f"❌ Invalid status {status!r}. Must be one of: "
                f"{', '.join(self._VALID_CLOSE_STATUSES)}"
            )
        if documenter_decision not in self._VALID_CLOSE_STATUSES:
            return (
                f"❌ Invalid documenter_decision {documenter_decision!r}. "
                f"Must be one of: {', '.join(self._VALID_CLOSE_STATUSES)}"
            )

        session_note_path = arguments.get("session_note_path")
        adrs = list(arguments.get("adrs_created", []) or [])
        record = self.memory.close_session(
            session_id,
            status=status,
            documenter_decision=documenter_decision,
            session_note_path=session_note_path,
            adrs_created=adrs,
        )
        payload = {
            "session_id": record.session_id,
            "closed_at": record.closed_at.isoformat() if record.closed_at else None,
            "end_commit": record.end_commit,
            "mode_inferred": record.mode.value,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _session_status_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_status``."""
        raw_id = arguments.get("session_id")
        if raw_id is None or not str(raw_id).strip():
            record = self.memory.get_active_session()
            if record is None:
                return "❌ No active session. Pass session_id or open one first."
        else:
            record = self.memory.get_session(str(raw_id).strip())
        return json.dumps(record.model_dump(mode="json"), ensure_ascii=False)

    def _session_task_list_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_task_list`` (Phase 09.C)."""
        from cortex.session import TaskStatus

        raw_id = arguments.get("session_id")
        if raw_id is None or not str(raw_id).strip():
            record = self.memory.get_active_session()
            if record is None:
                return "❌ No active session. Pass session_id or open one first."
            session_id = record.session_id
        else:
            session_id = str(raw_id).strip()

        raw_status = arguments.get("status")
        filter_status: TaskStatus | None = None
        if raw_status not in (None, ""):
            try:
                filter_status = TaskStatus(str(raw_status))
            except ValueError:
                return (
                    f"❌ Invalid status {raw_status!r}. Must be one of: "
                    f"{', '.join(s.value for s in TaskStatus)}"
                )

        tasks = self.memory.list_session_tasks(session_id, status=filter_status)
        return json.dumps(
            [t.model_dump(mode="json") for t in tasks],
            ensure_ascii=False,
        )

    def _session_task_update_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_task_update`` (Phase 09.C).

        Doubles as ``create-or-update``: if the task id does not exist
        yet and ``description`` is supplied, a fresh task is appended.
        """
        from cortex.session import Task, TaskStatus

        raw_id = arguments.get("session_id")
        if raw_id is None or not str(raw_id).strip():
            record = self.memory.get_active_session()
            if record is None:
                return "❌ No active session. Pass session_id or open one first."
            session_id = record.session_id
        else:
            session_id = str(raw_id).strip()

        task_id = str(arguments.get("task_id", "")).strip()
        raw_status = str(arguments.get("status", "")).strip()
        if not task_id or not raw_status:
            return "❌ task_id and status are required."
        try:
            new_status = TaskStatus(raw_status)
        except ValueError:
            return (
                f"❌ Invalid status {raw_status!r}. Must be one of: "
                f"{', '.join(s.value for s in TaskStatus)}"
            )

        note = str(arguments.get("note", ""))
        ckp_idx = arguments.get("checkpoint_index")
        checkpoint_index: int | None
        if ckp_idx is None or ckp_idx == "":
            checkpoint_index = None
        else:
            try:
                checkpoint_index = int(ckp_idx)
            except (TypeError, ValueError):
                return "❌ checkpoint_index must be an integer."

        # Auto-create the task if it doesn't exist yet and description was passed.
        existing = self.memory.list_session_tasks(session_id)
        if not any(t.id == task_id for t in existing):
            description = str(arguments.get("description", "")).strip()
            if not description:
                return (
                    f"❌ Task {task_id!r} does not exist; pass `description` "
                    "to create it on the fly."
                )
            files = list(arguments.get("files_in_scope", []) or [])
            try:
                self.memory.add_session_task(
                    session_id,
                    Task(
                        id=task_id,
                        description=description,
                        files_in_scope=files,
                        status=TaskStatus.PENDING,
                    ),
                )
            except (ValueError, Exception) as exc:  # noqa: BLE001
                return f"❌ {exc}"

        try:
            self.memory.update_session_task(
                session_id,
                task_id,
                new_status,
                note=note,
                checkpoint_index=checkpoint_index,
            )
        except (ValueError, Exception) as exc:  # noqa: BLE001
            return f"❌ {exc}"
        return json.dumps(
            {"session_id": session_id, "task_id": task_id, "status": new_status.value},
            ensure_ascii=False,
        )

    _PLACEHOLDER_TOKENS: frozenset[str] = frozenset(
        {"tbd", "todo", "fixme", "xxx", "???", "fill me", "[pendiente]"}
    )
    _SUCCESS_CLAIM_PATTERNS: frozenset[str] = frozenset(
        {
            "tests pass",
            "test passed",
            "tests passed",
            "build exitoso",
            "build successful",
            "linter clean",
            "lint passed",
            "checks pass",
            "ci passed",
        }
    )

    def _session_review_checkpoint_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_review_checkpoint`` (Phase 08 / T8.2).

        Runs :func:`cortex.session.quality_gates.review_checkpoint` over
        the resolved checkpoint of the resolved session and returns the
        verdict as JSON. Pure inspection — never mutates the session.
        """
        from cortex.documenter.spec_loader import load_spec
        from cortex.session.quality_gates import review_checkpoint

        raw_id = arguments.get("session_id")
        if raw_id is None or not str(raw_id).strip():
            record = self.memory.get_active_session()
            if record is None:
                return "❌ No active session. Pass session_id or open one first."
        else:
            record = self.memory.get_session(str(raw_id).strip())

        if not record.checkpoints:
            return "❌ Session has no checkpoints to review."

        try:
            idx = int(arguments.get("checkpoint_index", -1))
        except (TypeError, ValueError):
            return "❌ checkpoint_index must be an integer."
        try:
            checkpoint = record.checkpoints[idx]
        except IndexError:
            return (
                f"❌ checkpoint_index {idx} out of range "
                f"(session has {len(record.checkpoints)} checkpoint(s))."
            )

        spec_path = record.spec_path
        if not spec_path.is_absolute():
            spec_path = (self.project_root / spec_path).resolve()
        spec = load_spec(spec_path)

        verdict = review_checkpoint(checkpoint, spec)
        payload = {
            "accepted": verdict.accepted,
            "stage_1_passed": verdict.stage_1_passed,
            "stage_2_passed": verdict.stage_2_passed,
            "reason": verdict.reason,
            "action": verdict.action,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _close_session_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_close_session`` (Phase 09.A+ / May 2026).

        Close an OPEN session into a terminal state declared by the
        skill, recording the optional note path + any ADR paths the
        skill created. Does **not** invoke the reconstructor; the
        skill already has all the context (it called
        ``cortex_documenter_briefing`` first).
        """
        from cortex.session import SessionStatus

        raw_id = arguments.get("session_id")
        raw_status = arguments.get("status")
        note_path_arg = arguments.get("session_note_path")
        adrs_arg = arguments.get("adrs_created", []) or []

        if raw_status is None or not str(raw_status).strip():
            return "❌ 'status' is required (one of: closed, handoff, abandoned)."
        try:
            status = SessionStatus(str(raw_status).strip())
        except ValueError:
            return (
                f"❌ Invalid status {raw_status!r}. Must be one of: "
                "closed, handoff, abandoned."
            )
        if status not in {
            SessionStatus.CLOSED,
            SessionStatus.HANDOFF,
            SessionStatus.ABANDONED,
        }:
            return (
                f"❌ Status {status.value!r} is not terminal — cortex_close_session "
                "only accepts closed / handoff / abandoned."
            )

        if raw_id is None or not str(raw_id).strip():
            active = self.memory.get_active_session()
            if active is None:
                return "❌ No active session. Pass session_id explicitly."
            session_id = active.session_id
        else:
            session_id = str(raw_id).strip()

        from pathlib import Path

        note_path = Path(str(note_path_arg)) if note_path_arg else None
        adrs = [Path(str(p)) for p in adrs_arg if str(p).strip()]

        try:
            record = self.memory._session_service.close(
                session_id,
                status=status,
                documenter_decision=status,
                session_note_path=note_path,
                adrs_created=adrs,
            )
        except Exception as exc:
            return f"❌ Failed to close session {session_id!r}: {exc}"

        payload = {
            "session_id": record.session_id,
            "final_status": record.status.value,
            "mode": record.mode.value,
            "closed_at": record.closed_at.isoformat() if record.closed_at else None,
            "end_commit": record.end_commit,
            "session_note_path": (
                str(record.session_note_path) if record.session_note_path else None
            ),
            "adrs_created": [str(p) for p in record.adrs_created],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _session_list_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_list``."""
        raw_status = arguments.get("status")
        status = str(raw_status).strip() if raw_status else None
        records = self.memory.list_sessions(status)
        payload = [
            {
                "session_id": r.session_id,
                "status": r.status.value,
                "mode": r.mode.value,
                "opened_at": r.opened_at.isoformat(),
                "closed_at": r.closed_at.isoformat() if r.closed_at else None,
                "checkpoint_count": len(r.checkpoints),
                "spec_summary": r.spec_summary,
            }
            for r in records
        ]
        return json.dumps(payload, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Tripartita Refinada — Handoff & Verification helpers (Plan 02)
    # ------------------------------------------------------------------

    def _validate_handoff_text(self, arguments: dict[str, Any]) -> str:
        """Validate a YAML handoff against the AgentHandoff schema.

        Deprecated since Pluggable Middle Phase 02: the canonical contract
        between Cortex agents is now ``cortex_session_checkpoint``. This
        tool remains available for the documenter's Legacy YAML mode
        (single-agent IDEs like Codex that cannot emit checkpoints
        inline). It will be removed in Phase 04 if no Legacy YAML
        consumer remains.
        """
        from pydantic import ValidationError

        from cortex.handoff import AgentHandoff

        logger.warning(
            "cortex_validate_handoff is deprecated since Phase 02 (Pluggable "
            "Middle). Use cortex_session_checkpoint for inter-agent state. "
            "This tool stays available only for the documenter's Legacy "
            "YAML mode."
        )
        yaml_text = str(arguments.get("handoff_yaml", "") or "")
        expected_agent = arguments.get("expected_agent")
        if not yaml_text.strip():
            return "❌ handoff_yaml is required and must not be empty."
        try:
            handoff = AgentHandoff.from_yaml(yaml_text)
        except ValidationError as exc:
            details = "; ".join(
                f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
            )
            return f"❌ Handoff schema violation:\n  {details}"
        except Exception as exc:
            return f"❌ Failed to parse YAML: {exc}"

        if expected_agent and handoff.agent != expected_agent:
            return (
                f"❌ Agent mismatch: handoff says '{handoff.agent}' but "
                f"expected '{expected_agent}'."
            )

        lines = [
            f"✅ Handoff validated for {handoff.agent} (status: {handoff.status})",
            f"  verified_claims: {len(handoff.verified_claims)}",
            f"  unverified_claims: {len(handoff.unverified_claims)}",
            f"  artifacts: {len(handoff.artifacts_produced)}",
            f"  context_for_next: {len(handoff.context_for_next)}",
        ]
        if handoff.suggested_adr:
            reason = handoff.suggested_adr_reason or "(no reason given)"
            lines.append(f"  ⚠ suggested ADR: {reason}")
        if handoff.suggested_context_terms:
            lines.append(f"  📚 CONTEXT.md terms: {', '.join(handoff.suggested_context_terms)}")
        return "\n".join(lines)

    def _verify_session_claims_text(self, arguments: dict[str, Any]) -> str:
        """Cross-check claims against the current git diff (heuristic)."""
        from cortex.mcp._subprocess import git_branch_exists, safe_run

        claims = [str(c).strip() for c in (arguments.get("claims") or []) if str(c).strip()]
        base = str(arguments.get("base_branch") or "main")
        if not claims:
            return "❌ claims list is required and must not be empty."

        # Pre-validacion barata: si la rama base no existe, fallar rapido (~100ms)
        # en lugar de esperar el timeout completo del diff. Esto evita el caso
        # donde el adopter pasa "main" pero su repo usa "master" — sin esto, el
        # handler queda bloqueado 10s antes de devolver un error.
        if not git_branch_exists(base, cwd=self.project_root, timeout=2.0):
            return (
                f"❌ Base branch '{base}' does not exist in this repo. "
                f"Pass a valid branch via `base_branch` argument."
            )

        diff_result = safe_run(
            ["git", "diff", "--unified=0", base, "--"],
            cwd=self.project_root,
            timeout=10.0,
        )
        if not diff_result.ok:
            return f"❌ git diff against '{base}' failed: {diff_result.error}"
        diff_text = diff_result.stdout

        diff_lower = diff_text.lower()
        verified: list[str] = []
        asserted: list[str] = []
        contradicted: list[str] = []  # reserved for future negation heuristic

        for claim in claims:
            tokens = [
                t.lower() for t in claim.replace("_", " ").replace("/", " ").split() if len(t) > 3
            ]
            hits = sum(1 for t in tokens if t in diff_lower)
            if hits >= 2:
                verified.append(claim)
            else:
                asserted.append(claim)

        lines = [
            f"Verification of {len(claims)} claims against branch {base}:",
            f"  ✅ verified: {len(verified)}",
            f"  ⚠ asserted: {len(asserted)}",
            f"  ❌ contradicted: {len(contradicted)}",
        ]
        if verified:
            lines.append("\nVerified:")
            lines.extend(f"  - {c}" for c in verified)
        if asserted:
            lines.append("\nAsserted (no diff evidence):")
            lines.extend(f"  - {c}" for c in asserted)
        return "\n".join(lines)

