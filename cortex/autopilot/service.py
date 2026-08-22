"""cortex.autopilot.service — AutopilotService over the Session primitive.

Phase 03 refactor: ``AutopilotService`` is now a thin orchestrator that
wires together:

    * :class:`cortex.session.service.SessionService` for lifecycle ops
      (the SessionRecord is the canonical state),
    * :class:`cortex.autopilot.policies.PolicyEnforcer` for warnings and
      blocks at lifecycle hooks,
    * :mod:`cortex.autopilot.detectors` for the dry-run *preflight*,
    * :mod:`cortex.documenter` when ``finish(auto=True)`` needs to close
      the session via the canonical documenter pipeline.

The service does **not** open sessions — that is the job of
``cortex_create_spec``. ``start`` adopts whatever session is currently
active and surfaces open-time policy warnings.

Public API kept for backwards-compatibility:
    :meth:`start`        — adopt the active session under the configured policy.
    :meth:`preflight`    — dry-run the detector pipeline.
    :meth:`checkpoint`   — append a checkpoint and surface policy warnings.
    :meth:`finish`       — close the active session (auto=True → documenter).
    :meth:`status`       — describe the active or named session.
    :classmethod:`from_project_root` — wire dependencies from a project root.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from cortex.autopilot.config import load_autopilot_config
from cortex.autopilot.detectors.ambiguous import AmbiguousRequestDetector
from cortex.autopilot.detectors.base import resolve_detectors
from cortex.autopilot.detectors.default import (
    CodeChangeDetector,
    DocsOnlyDetector,
    LargeRefactorDetector,
    NoopDetector,
    QuestionOnlyDetector,
    SecuritySensitiveDetector,
)
from cortex.autopilot.errors import AutopilotError, NoActiveSessionError
from cortex.autopilot.lifecycle import (
    AutopilotCheckpointRequest,
    AutopilotCheckpointResult,
    AutopilotFinishRequest,
    AutopilotFinishResult,
    AutopilotPreflightRequest,
    AutopilotPreflightResult,
    AutopilotStartRequest,
    AutopilotStartResult,
    AutopilotStatusResult,
)
from cortex.autopilot.models import DetectionRequest
from cortex.autopilot.policies import (
    AutopilotMode,
    AutopilotPolicy,
    EnforcementResult,
    EnforcementSeverity,
    PolicyEnforcer,
)
from cortex.session.errors import SessionNotFound
from cortex.session.models import (
    CheckpointSource,
    SessionRecord,
    SessionStatus,
)
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage
from cortex.workspace.layout import WorkspaceLayout

logger = logging.getLogger(__name__)


# Default detector set; the user can inject a custom list via the constructor.
def _default_detectors() -> list[Any]:
    return [
        AmbiguousRequestDetector(),
        QuestionOnlyDetector(),
        DocsOnlyDetector(),
        SecuritySensitiveDetector(),
        LargeRefactorDetector(),
        CodeChangeDetector(),
        NoopDetector(),
    ]


# Factory signature for the heavyweight AgentMemory dependency. Lazy so
# the simple flows (status, checkpoint, observe-mode finish) never pay
# the AgentMemory startup cost.
MemoryFactory = Callable[[], Any]


class AutopilotService:
    """Apply an :class:`AutopilotPolicy` over a canonical session lifecycle.

    Dependencies are injectable so tests can supply a temporary
    :class:`SessionService` and skip the documenter integration entirely
    by passing ``memory_factory=None`` and calling ``finish(auto=False)``.
    """

    def __init__(
        self,
        session_service: SessionService,
        policy: AutopilotPolicy,
        repo_root: Path,
        *,
        memory_factory: MemoryFactory | None = None,
        detectors: Sequence[Any] | None = None,
    ) -> None:
        self._sessions = session_service
        self._policy = policy
        self._enforcer = PolicyEnforcer(policy)
        self._repo_root = Path(repo_root)
        self._memory_factory = memory_factory
        self._detectors = list(detectors) if detectors is not None else _default_detectors()

    # ── Construction ─────────────────────────────────────────────

    @classmethod
    def from_project_root(
        cls,
        project_root: Path,
        *,
        policy: AutopilotPolicy | None = None,
    ) -> AutopilotService:
        """Wire a service with workspace-discovered defaults.

        - ``SessionService`` is built over the discovered ``WorkspaceLayout``.
        - ``policy`` defaults to ``AutopilotPolicy.from_config(autopilot.yaml)``.
        - ``memory_factory`` lazily instantiates ``AgentMemory`` on first
          ``finish(auto=True)`` call. If memory cannot be built (no
          ``config.yaml``, missing deps), the call surfaces the exception.
        """
        layout = WorkspaceLayout.discover(project_root)
        storage = SessionStorage(layout.sessions_dir)
        session_service = SessionService(storage, layout.repo_root)
        cfg = load_autopilot_config(layout)
        resolved_policy = policy or AutopilotPolicy.from_config(cfg)

        def _memory_factory() -> Any:
            from cortex.core import AgentMemory

            return AgentMemory(config_path=str(layout.config_path))

        return cls(
            session_service=session_service,
            policy=resolved_policy,
            repo_root=layout.repo_root,
            memory_factory=_memory_factory,
        )

    # ── Properties ───────────────────────────────────────────────

    @property
    def policy(self) -> AutopilotPolicy:
        return self._policy

    @property
    def session_service(self) -> SessionService:
        return self._sessions

    # ── start ────────────────────────────────────────────────────

    def start(self, request: AutopilotStartRequest) -> AutopilotStartResult:
        """Adopt the active session under the (optionally overridden) mode.

        Raises :class:`NoActiveSessionError` when no session is active —
        the user must run ``cortex create-spec`` first.
        """
        active = self._require_active()

        if request.mode is not None and request.mode is not self._policy.mode:
            self._policy = _policy_with_mode(self._policy, request.mode)
            self._enforcer = PolicyEnforcer(self._policy)

        results = self._enforcer.on_session_open(active)
        return AutopilotStartResult(
            session=active,
            policy=self._policy,
            warnings=_warnings(results),
        )

    # ── preflight (dry-run of detectors, no mutation) ────────────

    def preflight(self, request: AutopilotPreflightRequest) -> AutopilotPreflightResult:
        """Run the detector pipeline against the request without touching state.

        Useful as a sanity check before the user dives into a heavy task
        ("the spec looks ambiguous — clarify before starting?").
        """
        detection = resolve_detectors(
            self._detectors,
            DetectionRequest(
                user_request=request.user_request,
                changed_files=list(request.changed_files),
                git_diff_stat=request.git_diff_stat,
            ),
        )
        return AutopilotPreflightResult(detection=detection)

    # ── checkpoint ───────────────────────────────────────────────

    def checkpoint(self, request: AutopilotCheckpointRequest) -> AutopilotCheckpointResult:
        """Append a checkpoint to the active session and surface warnings."""
        active = self._require_active()
        try:
            source = CheckpointSource(request.source)
        except ValueError as exc:
            valid = ", ".join(s.value for s in CheckpointSource)
            raise AutopilotError(
                f"unknown checkpoint source {request.source!r}; valid: {valid}"
            ) from exc

        record = self._sessions.checkpoint(
            active.session_id,
            source=source,
            verified_claims=request.verified_claims,
            unverified_claims=request.unverified_claims,
            artifacts_touched=request.artifacts_touched,
            note=request.note,
        )
        new_checkpoint = record.checkpoints[-1]
        results = self._enforcer.on_checkpoint(
            record,
            new_checkpoint,
            files_in_scope=request.files_in_scope,
        )
        return AutopilotCheckpointResult(
            session=record,
            checkpoint=new_checkpoint,
            warnings=_warnings(results),
        )

    # ── finish ───────────────────────────────────────────────────

    def finish(self, request: AutopilotFinishRequest) -> AutopilotFinishResult:
        """Close the session, optionally via the documenter pipeline.

        ``auto=True`` delegates to the canonical
        ``DocumenterPersister.finalize`` (reconstructs context, runs
        verification hooks, writes session note + ADRs, closes).

        ``auto=False`` closes the record without documenting — used by
        the ``observe`` mode when the user plans to run
        ``cortex finish-session`` later.

        Returns a result with ``blocked=True`` and the policy reason when
        :meth:`PolicyEnforcer.on_pre_close` emits a BLOCK.
        """
        session = self._resolve_target_session(request.session_id)
        if session.status is not SessionStatus.OPEN:
            return AutopilotFinishResult(
                session=session,
                documented=False,
                summary=f"session already in status {session.status.value}; no-op",
            )

        pre = self._enforcer.on_pre_close(session)
        blocks = [r for r in pre if r.severity is EnforcementSeverity.BLOCK]
        if blocks:
            return AutopilotFinishResult(
                session=session,
                blocked=True,
                blocked_reason=blocks[0].reason,
                warnings=_warnings(pre),
            )

        if request.auto:
            return self._finish_auto(session, request, warnings=_warnings(pre))
        return self._finish_manual(session, request, warnings=_warnings(pre))

    # ── status ───────────────────────────────────────────────────

    def status(self, session_id: str | None = None) -> AutopilotStatusResult:
        """Describe the session.

        With ``session_id=None`` returns the active session; otherwise
        looks up by id. Returns ``active=False`` when neither resolves.
        """
        if session_id is None:
            session = self._sessions.get_active()
        else:
            try:
                session = self._sessions.get(session_id)
            except SessionNotFound:
                session = None

        if session is None:
            return AutopilotStatusResult(active=False, policy=self._policy)

        inferred = self._sessions.infer_mode(session.checkpoints)
        return AutopilotStatusResult(
            active=True,
            session=session,
            policy=self._policy,
            checkpoint_count=len(session.checkpoints),
            inferred_mode=inferred.value,
        )

    # ── Internals ────────────────────────────────────────────────

    def _require_active(self) -> SessionRecord:
        active = self._sessions.get_active()
        if active is None:
            raise NoActiveSessionError(
                "No active session. Run `cortex create-spec` first to open one."
            )
        return active

    def _resolve_target_session(self, session_id: str | None) -> SessionRecord:
        if session_id is None:
            return self._require_active()
        try:
            return self._sessions.get(session_id)
        except SessionNotFound as exc:
            raise AutopilotError(f"session {session_id!r} not found") from exc

    def _finish_manual(
        self,
        session: SessionRecord,
        request: AutopilotFinishRequest,
        *,
        warnings: list[str],
    ) -> AutopilotFinishResult:
        """Close the record without invoking the documenter."""
        status = _intent_to_status(request.intent)
        updated = self._sessions.close(
            session.session_id,
            status=status,
            documenter_decision=status,
        )
        return AutopilotFinishResult(
            session=updated,
            documented=False,
            summary=f"closed without documenting ({status.value})",
            warnings=warnings,
        )

    def _finish_auto(
        self,
        session: SessionRecord,
        request: AutopilotFinishRequest,
        *,
        warnings: list[str],
    ) -> AutopilotFinishResult:
        """Invoke the canonical documenter to close + persist + index."""
        if self._memory_factory is None:
            raise AutopilotError(
                "finish(auto=True) requires a memory_factory to invoke the documenter; "
                "either inject one or use finish(auto=False)."
            )
        from cortex.documenter import (
            DocumenterPersister,
            FinishOverrides,
            ReconstructionInput,
            Reconstructor,
        )
        from cortex.session.verification import VerificationRunner

        memory = self._memory_factory()
        reconstructor = Reconstructor(
            session_service=self._sessions,
            verification_runner=VerificationRunner(repo_root=self._repo_root),
            repo_root=self._repo_root,
        )
        out = reconstructor.reconstruct(ReconstructionInput(session_id=session.session_id))

        forced = _intent_to_forced_status(request.intent)
        persister = DocumenterPersister(
            note_service=memory._note_service,
            session_service=self._sessions,
            vault_path=memory._vault_path_resolved,
        )
        result = persister.finalize(
            out,
            overrides=FinishOverrides(forced_status=forced),
        )

        # Reload the session to capture the now-closed state.
        refreshed = self._sessions.get(session.session_id)
        return AutopilotFinishResult(
            session=refreshed,
            documented=not result.already_closed,
            session_note_path=str(result.session_note_path) if result.session_note_path else None,
            adrs_created=[str(p) for p in result.adrs_created],
            summary=result.summary,
            warnings=warnings,
        )


# ── Module helpers ───────────────────────────────────────────────


def _warnings(results: list[EnforcementResult]) -> list[str]:
    return [r.reason for r in results if r.severity is EnforcementSeverity.WARN]


def _policy_with_mode(policy: AutopilotPolicy, mode: AutopilotMode) -> AutopilotPolicy:
    """Return a copy of ``policy`` with the mode replaced.

    Higher modes flip the warning flags on; lowering to OBSERVE turns
    them off so the new mode is fully consistent.
    """
    is_observe = mode is AutopilotMode.OBSERVE
    return AutopilotPolicy(
        mode=mode,
        budget_profile=policy.budget_profile,
        pre_commit_verification=mode is AutopilotMode.AUTOPILOT,
        out_of_scope_warning=not is_observe,
        warn_on_security_summary=not is_observe,
        auto_checkpoint_threshold_files=policy.auto_checkpoint_threshold_files,
        auto_checkpoint_threshold_minutes=policy.auto_checkpoint_threshold_minutes,
    )


def _intent_to_status(intent: str) -> SessionStatus:
    """Translate a finish ``intent`` to a :class:`SessionStatus`."""
    normalized = intent.strip().lower()
    if normalized in {"handoff"}:
        return SessionStatus.HANDOFF
    if normalized in {"abandoned", "abandon"}:
        return SessionStatus.ABANDONED
    return SessionStatus.CLOSED


def _intent_to_forced_status(intent: str) -> SessionStatus | None:
    """Translate a finish ``intent`` to a forced status override.

    ``"closed"`` means *no override* — let the documenter pick CLOSED or
    HANDOFF based on the reconstruction.
    """
    normalized = intent.strip().lower()
    if normalized in {"handoff"}:
        return SessionStatus.HANDOFF
    if normalized in {"abandoned", "abandon"}:
        return SessionStatus.ABANDONED
    return None


__all__ = ["AutopilotService"]
