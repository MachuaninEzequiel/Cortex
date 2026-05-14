"""cortex.autopilot.service — Core business API for Autopilot.

All peripheral layers (CLI, MCP, hooks) delegate to this service.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from cortex.workspace.layout import WorkspaceLayout
from cortex.autopilot.config import load_autopilot_config
from cortex.autopilot.context import fetch_context
from cortex.autopilot.context_budget import profile_for_task_type
from cortex.autopilot.delegation import DelegationEngine, ReviewVerdict
from cortex.autopilot.detectors.base import resolve_detectors
from cortex.autopilot.detectors.ambiguous import AmbiguousRequestDetector
from cortex.autopilot.detectors.default import (
    CodeChangeDetector,
    DocsOnlyDetector,
    LargeRefactorDetector,
    NoopDetector,
    QuestionOnlyDetector,
    SecuritySensitiveDetector,
)
from cortex.autopilot.errors import SessionNotFoundError
from cortex.autopilot.lifecycle import (
    CheckpointRequest,
    CheckpointResult,
    FinishRequest,
    FinishResult,
    PreflightRequest,
    PreflightResult,
    StartRequest,
    StartResult,
    StatusResult,
)
from cortex.autopilot.models import (
    AutopilotBudgetSnapshot,
    AutopilotCheckpoint,
    AutopilotEvent,
    AutopilotSessionState,
    DelegationResult,
    DetectionRequest,
    PolicyDecision,
    SessionDraft,
)
from cortex.autopilot.policies.auto_checkpoint import AutoCheckpointPolicy
from cortex.autopilot.policies.base import evaluate_policies, most_restrictive
from cortex.autopilot.policies.default import (
    BudgetPolicy,
    DocumentationRequiredPolicy,
    HumanApprovalPolicy,
    SpecRequiredPolicy,
)
from cortex.autopilot.state_store import StateStore
from cortex.autopilot.session_builder import SessionBuilder
from cortex.autopilot.session_writer import (
    IndexingSessionWriter,
    SessionWriter,
    VaultSessionWriter,
)


logger = __import__("logging").getLogger(__name__)


def _build_default_session_writer(layout: WorkspaceLayout) -> SessionWriter:
    """Build the production-grade session writer for a discovered layout.

    Returns an :class:`IndexingSessionWriter` whenever ``AgentMemory`` can
    be initialised from the workspace config — making indexing mandatory
    on every Autopilot persist.

    Falls back to :class:`VaultSessionWriter` (persistence only) when the
    workspace is not fully set up (no config.yaml, etc.). The fallback is
    visible via ``cortex autopilot doctor`` so degraded setups never go
    unnoticed.
    """
    base = VaultSessionWriter(layout.vault_path)
    try:
        from cortex.core import AgentMemory

        memory = AgentMemory(config_path=str(layout.config_path))
    except Exception as exc:
        logger.warning(
            "Autopilot indexing disabled (AgentMemory unavailable): %s. "
            "Session notes will be persisted to disk but NOT indexed into "
            "semantic / episodic memory. Run `cortex setup agent` to enable "
            "full indexing.",
            exc,
        )
        return base
    return IndexingSessionWriter(
        inner=base,
        vault_path=layout.vault_path,
        semantic=memory.semantic,
        episodic=memory.episodic,
        context_metadata=memory._runtime_metadata,
    )


# Default detector / policy instances used when none are explicitly injected.
_DEFAULT_DETECTORS = [
    AmbiguousRequestDetector(),
    QuestionOnlyDetector(),
    DocsOnlyDetector(),
    SecuritySensitiveDetector(),
    LargeRefactorDetector(),
    CodeChangeDetector(),
    NoopDetector(),
]

_DEFAULT_POLICIES = [
    BudgetPolicy(),
    SpecRequiredPolicy(),
    AutoCheckpointPolicy(),
    DocumentationRequiredPolicy(),
    HumanApprovalPolicy(),
]


class AutopilotService:
    """Central business service for the Autopilot lifecycle.

    Parameters
    ----------
    state_store:
        Persistent state store.
    detectors:
        List of detector instances.  Defaults to the built-in set.
    policies:
        List of policy instances.  Defaults to the built-in set.
    """

    def __init__(
        self,
        state_store: StateStore,
        detectors: list[object] | None = None,
        policies: list[object] | None = None,
        session_builder: SessionBuilder | None = None,
        session_writer: SessionWriter | None = None,
    ) -> None:
        self._store = state_store
        self._detectors = detectors if detectors is not None else list(_DEFAULT_DETECTORS)
        self._policies = policies if policies is not None else list(_DEFAULT_POLICIES)
        self._builder = session_builder if session_builder is not None else SessionBuilder()
        self._writer = session_writer

    # ------------------------------------------------------------------
    # Class-method factory
    # ------------------------------------------------------------------
    @classmethod
    def from_project_root(cls, project_root: Path) -> "AutopilotService":
        """Create a service instance for *project_root* using ``WorkspaceLayout``.

        The default factory wires an :class:`IndexingSessionWriter` so that
        every successful ``finish --auto`` not only persists the session
        note to disk but also indexes it into the semantic and episodic
        memory stores — making the new note immediately retrievable via
        ``cortex search``.

        If the workspace is not fully configured (no ``config.yaml``,
        missing dependencies), the factory falls back to a persist-only
        :class:`VaultSessionWriter` and logs a warning. ``cortex autopilot
        doctor`` surfaces this degraded mode so it never goes unnoticed.
        """
        layout = WorkspaceLayout.discover(project_root)
        store = StateStore(layout.workspace_root)
        writer = _build_default_session_writer(layout)
        return cls(state_store=store, session_writer=writer)

    # ------------------------------------------------------------------
    # start
    # ------------------------------------------------------------------
    def start(self, request: StartRequest) -> StartResult:
        """Create a new session and persist it."""
        state = self._store.create_session(
            project_root=request.project_root,
            workspace_root=request.workspace_root,
            mode=request.mode,
            user_request=request.user_request,
            title_hint=request.title_hint,
        )

        self._store.append_event(
            AutopilotEvent(
                session_id=state.session_id,
                event_type="start",
                source="cli",
                payload={
                    "mode": request.mode,
                    "user_request": request.user_request,
                },
            )
        )

        return StartResult(session_id=state.session_id, state=state)

    # ------------------------------------------------------------------
    # preflight
    # ------------------------------------------------------------------
    def preflight(self, request: PreflightRequest) -> PreflightResult:
        """Detect task type, evaluate policies, and update state."""
        state = self._store.require_state(request.session_id)

        # Update request info if provided
        if request.user_request is not None:
            state.user_request = request.user_request
        if request.changed_files:
            state.changed_files = list(request.changed_files)

        detection = resolve_detectors(
            self._detectors,  # type: ignore[arg-type]
            DetectionRequest(
                user_request=state.user_request,
                changed_files=state.changed_files,
                git_diff_stat=request.git_diff_stat,
                session_state=state,
            ),
        )

        state.detected_task_type = detection.task_type
        state.complexity = detection.suggested_complexity
        # Seed budget snapshot with detection metadata
        state.budget.deep_track_reason = (
            detection.reason if detection.suggested_complexity == "deep" else None
        )
        state.updated_at = datetime.now()

        # Evaluate policies
        policy_decisions = evaluate_policies(
            self._policies,  # type: ignore[arg-type]
            state,
        )
        worst = most_restrictive(policy_decisions)
        can_proceed = worst.allowed if worst else True

        # Degrade mode if a policy demands it
        if worst and worst.action == "degrade" and worst.degrade_to:
            state.mode = worst.degrade_to  # type: ignore[assignment]

        state.status = "preflight_done"
        self._store.save_state(state)
        self._store.append_event(
            AutopilotEvent(
                session_id=state.session_id,
                event_type="preflight",
                source="cli",
                payload={
                    "detection": detection.model_dump(mode="json"),
                    "can_proceed": can_proceed,
                    "worst_policy": worst.model_dump(mode="json") if worst else None,
                },
            )
        )

        return PreflightResult(
            detection=detection,
            policy_decisions=policy_decisions,
            can_proceed=can_proceed,
            state=state,
        )

    # ------------------------------------------------------------------
    # checkpoint
    # ------------------------------------------------------------------
    def checkpoint(self, request: CheckpointRequest) -> CheckpointResult:
        """Record a checkpoint with observed state."""
        state = self._store.require_state(request.session_id)

        ck = AutopilotCheckpoint(
            timestamp=datetime.now(),
            summary=request.summary,
            files_at_checkpoint=list(request.files_at_checkpoint),
            verified=request.verified,
        )
        state.checkpoints.append(ck)
        state.status = "implementation_seen"
        state.updated_at = datetime.now()
        self._store.save_state(state)

        self._store.append_event(
            AutopilotEvent(
                session_id=state.session_id,
                event_type="checkpoint",
                source="cli",
                payload={
                    "summary": request.summary,
                    "verified": request.verified,
                },
            )
        )

        return CheckpointResult(state=state)

    # ------------------------------------------------------------------
    # finish
    # ------------------------------------------------------------------
    def finish(self, request: FinishRequest) -> FinishResult:
        """Attempt to close the session, generating a draft if needed."""
        state = self._store.require_state(request.session_id)

        # Guard against duplicate session notes
        if state.session_note_path:
            state.status = "documented"
            state.updated_at = datetime.now()
            self._store.save_state(state)
            self._store.append_event(
                AutopilotEvent(
                    session_id=state.session_id,
                    event_type="finish",
                    source="cli",
                    payload={
                        "auto": request.auto,
                        "saved": False,
                        "reason": "Session note already exists",
                    },
                )
            )
            return FinishResult(
                state=state,
                draft=None,
                saved=False,
            )

        # Evaluate policies before finishing
        policy_decisions = evaluate_policies(
            self._policies,  # type: ignore[arg-type]
            state,
        )
        worst = most_restrictive(policy_decisions)

        draft: SessionDraft | None = None
        saved = False

        if request.auto and (worst is None or worst.action != "block"):
            draft = self._builder.build(state)
            persisted_path = self._persist_draft(state, draft)
            if persisted_path is not None:
                state.session_note_path = str(persisted_path)
                state.status = "documented"
                saved = True
            else:
                # Writer not configured or write failed — the draft exists
                # in memory but not on disk. Mark the session finished, not
                # documented, so the contract "documented ⇒ file on disk"
                # is never violated.
                state.status = "finished"
        elif worst and worst.action == "block":
            # Blocked — generate an auto-draft anyway but do not mark documented
            draft = self._builder.build(state)
            state.warnings.append(worst.reason)
            state.status = "finished"
        else:
            state.status = "finished"

        state.updated_at = datetime.now()
        self._store.save_state(state)

        self._store.append_event(
            AutopilotEvent(
                session_id=state.session_id,
                event_type="finish",
                source="cli",
                payload={
                    "auto": request.auto,
                    "saved": saved,
                    "session_note_path": state.session_note_path if saved else None,
                    "blocked_by": worst.reason if worst and worst.action == "block" else None,
                },
            )
        )

        return FinishResult(state=state, draft=draft, saved=saved)

    # ------------------------------------------------------------------
    # finish helpers
    # ------------------------------------------------------------------
    def _persist_draft(
        self,
        state: AutopilotSessionState,
        draft: SessionDraft,
    ) -> Path | None:
        """Persist *draft* via the configured ``SessionWriter``.

        Returns the path written, or ``None`` when no writer is configured
        or the write failed. On failure, a warning is appended to the
        session state so operators can diagnose the issue from telemetry.
        """
        if self._writer is None:
            state.warnings.append(
                "AutopilotService has no session_writer; "
                "draft was generated but not persisted to disk."
            )
            return None
        try:
            return self._writer.write(state, draft)
        except Exception as exc:  # pragma: no cover - defensive
            state.warnings.append(f"Session note persistence failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------
    def status(self, session_id: str | None = None) -> StatusResult:
        """Return the current status of a session (or latest if no ID given)."""
        if session_id:
            state = self._store.load_state(session_id)
            if state is None:
                return StatusResult(active=False)
            events = self._store.load_events(session_id)
            return StatusResult(active=True, state=state, event_count=len(events))

        sessions = self._store.list_sessions()
        if not sessions:
            return StatusResult(active=False)

        # Return the most recently updated session
        latest = max(
            sessions,
            key=lambda sid: (
                self._store.load_state(sid) or AutopilotSessionState(
                    project_root="", workspace_root="", updated_at=datetime.min
                )
            ).updated_at,
        )
        state = self._store.load_state(latest)
        if state is None:
            return StatusResult(active=False)
        events = self._store.load_events(latest)
        return StatusResult(active=True, state=state, event_count=len(events))

    # ------------------------------------------------------------------
    # context
    # ------------------------------------------------------------------
    def build_context(
        self, session_id: str, *, memory: object | None = None
    ) -> tuple[str, AutopilotBudgetSnapshot]:
        """Fetch enriched context for *session_id* respecting the budget profile.

        Returns ``(prompt_text, budget_snapshot)`` and persists the updated
        state with the new budget snapshot.
        """
        state = self._store.require_state(session_id)
        result = fetch_context(state, memory=memory)
        state.budget = result.budget
        state.updated_at = datetime.now()
        self._store.save_state(state)
        self._store.append_event(
            AutopilotEvent(
                session_id=state.session_id,
                event_type="context",
                source="cli",
                payload={
                    "profile": result.profile_name,
                    "chars": result.budget.chars_injected,
                    "items": result.budget.items_retrieved,
                },
            )
        )
        return result.prompt_text, result.budget

    # ------------------------------------------------------------------
    # delegation / two-stage review
    # ------------------------------------------------------------------
    def review_delegation(
        self,
        session_id: str,
        result: DelegationResult,
    ) -> ReviewVerdict:
        """Run two-stage review on a ``DelegationResult``.

        Persist the review outcome as an event and, if accepted, record a
        checkpoint automatically.
        """
        state = self._store.require_state(session_id)
        engine = DelegationEngine()
        verdict = engine.review(result, state)

        event_payload: dict = {
            "task_id": result.task_id,
            "status": result.status,
            "accepted": verdict.accepted,
            "stage_1_passed": verdict.stage_1_passed,
            "stage_2_passed": verdict.stage_2_passed,
            "reason": verdict.reason,
            "action": verdict.action,
        }

        if not verdict.accepted:
            state.warnings.append(
                f"Delegation {result.task_id} rejected: {verdict.reason}"
            )
            self._store.save_state(state)

        self._store.append_event(
            AutopilotEvent(
                session_id=state.session_id,
                event_type="delegation_review",
                source="cli",
                payload=event_payload,
            )
        )

        if verdict.accepted:
            ck = AutopilotCheckpoint(
                timestamp=datetime.now(),
                summary=f"Delegation accepted: {result.task_id}",
                files_at_checkpoint=list(result.files_changed),
                verified=result.tests_passed or False,
            )
            state.checkpoints.append(ck)
            state.updated_at = datetime.now()
            self._store.save_state(state)

        return verdict
