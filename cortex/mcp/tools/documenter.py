"""Handlers MCP del dominio spec/proposal/documenter (mixín de CortexMCPServer).

Extraído del monolito server.py (deuda V1, Obra 01 fase P3). Los métodos
conservan su firma y semántica ``self.`` exactas; el contrato observable
está congelado por tests/unit/mcp/test_golden_contract.py.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def _serialize_reconstruction(out: Any) -> dict[str, Any]:
    """Serialize a :class:`ReconstructionOutput` to JSON-safe dict.

    Used by ``cortex_documenter_briefing``. Kept at module scope so it
    can be unit-tested without spinning up the full server. Paths are
    rendered as POSIX strings; ``LoadedSpec`` is reduced to the fields
    the skill needs for editorial decisions.
    """
    # ``VerificationHookResult`` (frozen, extra="forbid") doesn't carry the
    # ``required`` flag — that lives on the spec's ``VerificationHook``. We
    # derive it by name lookup so the briefing payload stays self-contained.
    # Default ``True`` on miss is conservative: an unmatched result is treated
    # as required so a failure isn't silently downgraded.
    _hook_required_by_name = {h.name: h.required for h in out.spec.verification_hooks}
    return {
        "session_id": out.session_id,
        "spec": {
            "path": out.spec.path.as_posix(),
            "title": out.spec.title,
            "goal": out.spec.goal,
            "files_in_scope": [p.as_posix() for p in out.spec.files_in_scope],
            "constraints": list(out.spec.constraints),
            "acceptance_criteria": list(out.spec.acceptance_criteria),
            "verification_hooks": [
                {
                    "name": h.name,
                    "command": h.command,
                    "required": h.required,
                    "success_criteria": h.success_criteria,
                    "timeout_seconds": h.timeout_seconds,
                }
                for h in out.spec.verification_hooks
            ],
        },
        "diff_text": out.diff_text,
        "diff_entries": [
            {"action": e.action, "path": e.path.as_posix()} for e in out.diff_entries
        ],
        "files_touched": [p.as_posix() for p in out.files_touched],
        "files_verified_by_git": [p.as_posix() for p in out.files_verified_by_git],
        "files_declared_only": [p.as_posix() for p in out.files_declared_only],
        "in_scope_files": [p.as_posix() for p in out.in_scope_files],
        "out_of_scope_files": [p.as_posix() for p in out.out_of_scope_files],
        "unimplemented_files": [p.as_posix() for p in out.unimplemented_files],
        "verification_results": [
            {
                "name": r.name,
                "command": r.command,
                "passed": r.passed,
                "exit_code": r.exit_code,
                "output": r.output,
                "duration_ms": r.duration_ms,
                "run_at": r.run_at.isoformat(),
                "required": _hook_required_by_name.get(r.name, True),
            }
            for r in out.verification_results
        ],
        "contradictions": [
            {
                "prior_record": c.prior_record,
                "current_claim": c.current_claim,
                "evidence": c.evidence,
                "severity": c.severity,
            }
            for c in out.contradictions
        ],
        "suggested_status": out.suggested_status.value,
        "suggested_adrs": [
            {
                "title": a.title,
                "rationale": a.rationale,
                "source_checkpoint_index": a.source_checkpoint_index,
                "evidence": a.evidence,
                "confidence": a.confidence,
            }
            for a in out.suggested_adrs
        ],
        "raw_checkpoints": [
            {
                "timestamp": cp.timestamp.isoformat(),
                "source": cp.source.value,
                "verified_claims": list(cp.verified_claims),
                "unverified_claims": list(cp.unverified_claims),
                "artifacts_touched": list(cp.artifacts_touched),
                "note": cp.note,
            }
            for cp in out.raw_checkpoints
        ],
        "end_commit": out.end_commit,
        "gitless": out.gitless,
    }

class DocumenterToolsMixin:
    """Mixín: handlers MCP de spec/proposal/documenter."""

    _GOVERNANCE_VIOLATION_MESSAGE = (
        "❌ **VIOLACIÓN DE GOBERNANZA**: cortex_create_spec fue llamado sin "
        "ejecutar primero cortex_sync_ticket.\n\n"
        "Según las reglas de Cortex v2.0, cortex-sync DEBE llamar a "
        "cortex_sync_ticket como PRIMER paso para inyectar contexto histórico "
        "vía ONNX/hybrid retrieval antes de crear cualquier spec.\n\n"
        "Por favor, corrige el flujo:\n"
        "1. Llama a cortex_sync_ticket con el pedido del usuario\n"
        "2. Luego llama a cortex_create_spec"
    )

    def _create_spec_text(self, arguments: dict[str, Any]) -> str:
        called_tools: set[str] = getattr(self, "_called_tools", set())
        if "cortex_sync_ticket" not in called_tools:
            logger.error(
                "GOVERNANCE_VIOLATION: cortex_create_spec called without "
                "cortex_sync_ticket. Tools called: %s",
                called_tools,
            )
            return (
                f"{self._GOVERNANCE_VIOLATION_MESSAGE}\n\n"
                f"Herramientas llamadas en esta sesión: "
                f"{', '.join(sorted(called_tools))}"
            )

        proposal_mode = str(arguments.get("proposal_mode", "optional"))
        proposal_confirmed = bool(arguments.get("proposal_confirmed", False))

        if proposal_mode == "required" and proposal_confirmed:
            gap_error = self._validate_proposal_gap()
            if gap_error is not None:
                logger.error("PROPOSAL_GAP_VIOLATION: %s", gap_error)
                return f"❌ {gap_error}"

        from cortex.documentation.errors import DuplicateDocumentError

        try:
            result = self.memory.create_spec_note(
                title=arguments.get("title", ""),
                goal=arguments.get("goal", ""),
                requirements=arguments.get("requirements", []),
                files_in_scope=arguments.get("files_in_scope", []),
                constraints=arguments.get("constraints", []),
                acceptance_criteria=arguments.get("acceptance_criteria", []),
                tags=arguments.get("tags", []),
                verification_hooks=arguments.get("verification_hooks", []),
                sync_vault=not arguments.get("no_sync", False),
                proposal_mode=proposal_mode,
                proposal_confirmed=proposal_confirmed,
            )
        except ValueError as exc:
            return f"❌ {exc}"
        except DuplicateDocumentError as exc:
            # Expected branch: a spec already exists at the target path with
            # *different* content. Idempotent same-content retries don't reach
            # this — they succeed silently in ``writers._write_note``. Return
            # an actionable message without polluting ``_error_history`` /
            # marking the server as degraded; this is user-recoverable, not a
            # server fault. See
            # ``docs/incidents/2026-05-22_appfutbol-mcp-duplicate-loop/``.
            return (
                f"ℹ️  Spec ya existe con contenido distinto.\n\n{exc}\n\n"
                f"Opciones:\n"
                f"  • Cambiá el título para generar un slug distinto.\n"
                f"  • O abrí sesión sobre la spec existente con cortex_session_open."
            )
        # Tolerate test doubles that still return a bare Path (see
        # ``tests/unit/test_mcp_server.py``). Real callers always return
        # ``SpecCreationResult``.
        if hasattr(result, "path"):
            path = result.path
            session = result.session
        else:
            path = result
            session = None
        message = f"Specification saved -> {path}"
        if session is not None and session.is_gitless:
            message += (
                "\n\n⚠️  No git repository detected. Session opened in degraded mode:\n"
                "   • cortex finish-session will skip git diff reconstruction\n"
                "   • documenter will rely exclusively on checkpoints\n"
                "   • To enable full session capabilities later, run:\n"
                "       git init && git add -A && git commit -m \"initial\""
            )
        return message

    def _validate_proposal_gap(self) -> str | None:
        """Return an error string if the proposal/spec gap is invalid.

        Enforces Phase 09.A+ ``required`` mode: a follow-up
        ``cortex_create_spec`` with ``proposal_confirmed=True`` must come
        from a different conversational turn than the originating
        ``cortex_emit_proposal``. The gap heuristic catches an LLM that
        chains both calls in the same response without a real user reply.

        Returns:
            ``None`` if the gap is fine; otherwise a human-readable error.
        """
        emitted_at = self._last_proposal_emitted_at
        if emitted_at is None:
            return (
                "proposal_mode='required' requires a prior cortex_emit_proposal "
                "call. Emit the proposal first, end your turn, and only after "
                "the user replies should you call cortex_create_spec with "
                "proposal_confirmed=True."
            )
        delta = (datetime.now() - emitted_at).total_seconds()
        if delta < self._PROPOSAL_MIN_GAP_SECONDS:
            return (
                f"proposal emitted {delta:.2f}s ago — too recent to count as "
                f"user-confirmed. The user has not had time to respond yet. "
                f"End your turn after cortex_emit_proposal and wait for an "
                f"explicit reply before calling cortex_create_spec. "
                f"(minimum gap: {self._PROPOSAL_MIN_GAP_SECONDS}s)"
            )
        return None

    def _emit_proposal_text(self, arguments: dict[str, Any]) -> str:
        """Render a structured proposal card and record its timestamp.

        Validates the payload against :class:`cortex.session.proposal.Proposal`,
        which guarantees recommendation/alternative consistency. Stamps
        ``_last_proposal_emitted_at`` so a subsequent
        ``cortex_create_spec`` with ``proposal_mode='required'`` can verify
        a user turn has elapsed.
        """
        from pydantic import ValidationError

        from cortex.session.proposal import Proposal, format_proposal_card

        payload = {
            "summary": arguments.get("summary", ""),
            "alternatives": arguments.get("alternatives", []),
            "recommendation_id": arguments.get("recommendation_id", ""),
            "risks": list(arguments.get("risks", []) or []),
        }
        try:
            proposal = Proposal.model_validate(payload)
        except ValidationError as exc:
            return f"❌ cortex_emit_proposal payload invalid: {exc}"

        self._last_proposal_emitted_at = datetime.now()
        card = format_proposal_card(proposal)
        return card

    def _self_review_note_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_self_review_note`` (Phase 09.A+ / May 2026).

        Pure inspection. Surfaces placeholder tokens and hollow success
        claims so the skill can revise its draft before persisting.
        Never blocks — the skill chooses what to do with the warnings.
        """
        body = str(arguments.get("body", ""))
        hooks_passed = bool(arguments.get("verification_hooks_passed", False))

        warnings: list[str] = []
        body_lower = body.lower()
        for token in self._PLACEHOLDER_TOKENS:
            if token in body_lower:
                warnings.append(f"Placeholder token detected: {token!r}")

        if not hooks_passed:
            for pattern in self._SUCCESS_CLAIM_PATTERNS:
                if pattern in body_lower:
                    warnings.append(
                        f"Hollow claim {pattern!r} — no verification hook "
                        "actually passed; either remove the claim or run "
                        "the test/build that proves it."
                    )

        return json.dumps(
            {"warnings": warnings, "passed": not warnings}, ensure_ascii=False
        )

    _VALID_FINISH_INTENTS: tuple[str, ...] = ("auto", "handoff", "abandon")

    def _finish_session_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_finish_session`` (Phase 01 / T1.7).

        The Phase 04 ``--interactive`` mode of the documenter (``cortex
        finish-session --interactive``) is **CLI only**; an MCP request
        runs the auto pipeline because the protocol is non-interactive
        by design (text in, text out — no terminal to prompt against).
        Pass ``interactive: true`` to receive a clear error directing
        the caller to the CLI.
        """
        if arguments.get("interactive"):
            return (
                "❌ The interactive documenter mode is CLI-only. Run "
                "`cortex finish-session --interactive` instead, or omit "
                "`interactive` from this tool call."
            )
        from cortex.documenter import (
            DocumenterPersister,
            FinishOverrides,
            ReconstructionInput,
            Reconstructor,
        )
        from cortex.session import SessionStatus
        from cortex.session.verification import VerificationRunner

        raw_id = arguments.get("session_id")
        intent = str(arguments.get("intent") or "auto").strip()
        reason = str(arguments.get("reason") or "").strip()

        if intent not in self._VALID_FINISH_INTENTS:
            return (
                f"❌ Invalid intent {intent!r}. Must be one of: "
                f"{', '.join(self._VALID_FINISH_INTENTS)}"
            )
        if intent != "auto" and not reason:
            return f"❌ 'reason' is required when intent is {intent!r}."

        # Resolve session id: explicit arg or active.
        if raw_id is None or not str(raw_id).strip():
            active = self.memory.get_active_session()
            if active is None:
                return "❌ No active session. Pass session_id explicitly."
            session_id = active.session_id
        else:
            session_id = str(raw_id).strip()

        record = self.memory.get_session(session_id)
        if record.status is not SessionStatus.OPEN:
            return (
                f"❌ Session {session_id!r} is already in status "
                f"{record.status.value!r}; nothing to finish."
            )

        reconstructor = Reconstructor(
            session_service=self.memory._session_service,
            verification_runner=VerificationRunner(repo_root=self.memory.repo_root),
            repo_root=self.memory.repo_root,
        )
        out = reconstructor.reconstruct(ReconstructionInput(session_id=session_id))

        forced_status: SessionStatus | None = None
        if intent == "abandon":
            forced_status = SessionStatus.ABANDONED
        elif intent == "handoff":
            forced_status = SessionStatus.HANDOFF

        persister = DocumenterPersister(
            note_service=self.memory._note_service,
            session_service=self.memory._session_service,
            vault_path=self.memory._vault_path_resolved,
        )
        result = persister.finalize(
            out,
            overrides=FinishOverrides(forced_status=forced_status),
        )

        payload = {
            "session_id": result.session_id,
            "final_status": result.final_status.value,
            "session_note_path": (
                str(result.session_note_path) if result.session_note_path else None
            ),
            "adrs_created": [str(p) for p in result.adrs_created],
            "summary_text": result.summary,
            "already_closed": result.already_closed,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _documenter_briefing_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_documenter_briefing`` (Phase 09.A+ / May 2026).

        Read-only reconstruction. Mirrors :meth:`_finish_session_text`
        up to the moment of persistence, then returns the full
        :class:`ReconstructionOutput` serialized as JSON instead of
        running the persister and closing the session.

        Consumed by the ``/cortex-documenter`` skill to obtain the
        context (spec, diff, checkpoints, hooks, scope drift, ADR
        candidates) it needs to write a session note with editorial
        criterion. The skill calls ``cortex_close_session`` after it
        has written the notes via the ``write_*_note_canonical`` tools.
        """
        from cortex.documenter import ReconstructionInput, Reconstructor
        from cortex.session.verification import VerificationRunner

        raw_id = arguments.get("session_id")
        if raw_id is None or not str(raw_id).strip():
            active = self.memory.get_active_session()
            if active is None:
                return "❌ No active session. Pass session_id explicitly."
            session_id = active.session_id
        else:
            session_id = str(raw_id).strip()

        run_hooks = bool(arguments.get("run_hooks", False))

        reconstructor = Reconstructor(
            session_service=self.memory._session_service,
            verification_runner=VerificationRunner(repo_root=self.memory.repo_root),
            repo_root=self.memory.repo_root,
        )
        out = reconstructor.reconstruct(
            ReconstructionInput(session_id=session_id, run_hooks=run_hooks)
        )
        return json.dumps(_serialize_reconstruction(out), ensure_ascii=False)

