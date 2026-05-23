"""cortex.session.models — Pydantic models for the Session primitive.

The Session is the core primitive of the Pluggable Middle architecture. It
tracks the lifecycle of a unit of development from the moment ``cortex-sync``
creates a spec until ``cortex-documenter`` (via ``cortex finish-session``)
persists the session note and closes the record.

See: ``docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`` §5.

Module contents:
    - :class:`SessionStatus`         — lifecycle state enum
    - :class:`SessionMode`           — execution mode enum (inferred at close)
    - :class:`CheckpointSource`      — authoring source for a checkpoint
    - :class:`Checkpoint`            — immutable in-flight enrichment record
    - :class:`VerificationHookResult` — immutable hook execution result
    - :class:`SessionRecord`         — root document persisted as YAML

Conventions:
    - All datetimes are timezone-aware and normalized to UTC at validation.
    - ``session_id`` follows ``YYYY-MM-DD_<slug>``.
    - Commit SHAs are 40-character lowercase hex (full SHA-1).
    - Paths are not constrained to relative or absolute; the service layer
      is responsible for storing them workspace-relative.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SESSION_ID_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-z0-9][a-z0-9-]*$")
COMMIT_SHA_PATTERN = re.compile(r"^[a-f0-9]{40}$")

# Sentinel SHA used for sessions opened in projects without an initialised
# git repository. Forty zeros — passes ``COMMIT_SHA_PATTERN`` (so the model
# stays strict) but never matches a real commit. Consumers that branch on
# git-aware vs. gitless behaviour MUST compare against this constant rather
# than testing arbitrary commit strings. See
# ``cortex.session.service.SessionService.open`` and
# ``cortex.documenter.reconstruction`` for the call sites.
GITLESS_COMMIT_PLACEHOLDER: str = "0" * 40

# Output of a verification hook is truncated to this many bytes (tail kept).
# 10 KB is enough to diagnose typical failures (pytest tracebacks fit) without
# bloating the YAML or memory.
MAX_VERIFICATION_OUTPUT_BYTES = 10_000

_TERMINAL_STATUSES: frozenset[str] = frozenset({"closed", "handoff", "abandoned"})


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SessionStatus(StrEnum):
    """Lifecycle states of a Session.

    Transitions allowed:
        OPEN → CLOSED      (work completed and verified)
        OPEN → HANDOFF     (work partial, blockers documented)
        OPEN → ABANDONED   (work discarded without documentation)
    """

    OPEN = "open"
    CLOSED = "closed"
    HANDOFF = "handoff"
    ABANDONED = "abandoned"


class SessionMode(StrEnum):
    """How the *middle* of the workflow was executed.

    Inferred at close time from the set of checkpoints attached to the
    Session — see :meth:`cortex.session.service.SessionService.infer_mode`.
    """

    UNKNOWN = "unknown"  # default while still OPEN
    MANAGED = "managed"  # checkpoints came from Cortex agents (SDDwork, etc.)
    OBSERVED = "observed"  # checkpoints came from IDE hooks or user skills
    BYO = "byo"  # no checkpoints — pure diff-driven reconstruction
    # Pluggable Middle Phase 07 Level 3 — every checkpoint is a CI_BOT
    # audit entry; the session lives in the vault as a review trail.
    CI_REVIEW = "ci-review"


class CheckpointSource(StrEnum):
    """Authoring source for a Checkpoint.

    The set is closed. Any caller must use one of these values, otherwise the
    MCP / service layer rejects the checkpoint at validation time.
    """

    CORTEX_SYNC = "cortex-sync"
    CORTEX_SDDWORK = "cortex-SDDwork"
    CORTEX_CODE_EXPLORER = "cortex-code-explorer"
    CORTEX_CODE_IMPLEMENTER = "cortex-code-implementer"
    CORTEX_CODE_DESIGNER = "cortex-code-designer"
    USER_SKILL = "user-skill"
    IDE_HOOK = "ide-hook"
    MANUAL = "manual"
    # Pluggable Middle Phase 07 Level 3 — emitted by ``cortex ci`` when
    # a CI workflow attaches its audit trail to the active review
    # session.
    CI_BOT = "ci-bot"


class TaskStatus(StrEnum):
    """Lifecycle states of a :class:`Task` (Pluggable Middle Phase 09.C)."""

    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    DONE = "done"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_utc(value: datetime, field_name: str) -> datetime:
    """Reject naive datetimes; normalize any aware datetime to UTC."""
    if value.tzinfo is None:
        raise ValueError(
            f"{field_name} must be timezone-aware (got naive datetime). "
            "Use datetime.now(timezone.utc) or any aware datetime."
        )
    return value.astimezone(UTC)


def _truncate_output(text: str) -> str:
    """Truncate output to ``MAX_VERIFICATION_OUTPUT_BYTES``, keeping the tail."""
    encoded = text.encode("utf-8")
    if len(encoded) <= MAX_VERIFICATION_OUTPUT_BYTES:
        return text
    tail = encoded[-MAX_VERIFICATION_OUTPUT_BYTES:]
    decoded = tail.decode("utf-8", errors="replace")
    return f"[... truncated, kept last {MAX_VERIFICATION_OUTPUT_BYTES} bytes ...]\n{decoded}"


# ---------------------------------------------------------------------------
# Task (Pluggable Middle Phase 09.C)
# ---------------------------------------------------------------------------

TASK_ID_PATTERN = re.compile(r"^T\d+(\.\d+)*$")


class Task(BaseModel):
    """A granular work item inside a Session.

    Tasks decompose the spec into atomic, individually-trackable units.
    They are **opt-in** (default ``SessionRecord.tasks`` is empty) and
    **descriptive** — they do not replace checkpoints, they accompany
    them. A task may link back to the checkpoint that finished it via
    ``checkpoint_index`` (an index into ``SessionRecord.checkpoints``).

    Naming follows the openspec convention: ``T1``, ``T1.2``, ``T1.2.3``.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1)
    files_in_scope: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    completed_at: datetime | None = None
    checkpoint_index: int | None = Field(default=None, ge=0)
    note: str = ""

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        if not TASK_ID_PATTERN.match(value):
            raise ValueError(
                f"Task id {value!r} does not match required pattern "
                "'T\\d+(\\.\\d+)*' (e.g. T1, T1.2, T1.2.3)"
            )
        return value

    @field_validator("completed_at")
    @classmethod
    def _validate_completed_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _to_utc(value, "completed_at")

    @model_validator(mode="after")
    def _validate_status_invariants(self) -> Task:
        # ``completed_at`` may only be set for terminal statuses; conversely
        # DONE *requires* completed_at to be set so the documenter can build
        # accurate timing summaries.
        if self.status is TaskStatus.DONE and self.completed_at is None:
            raise ValueError(
                "Task in status 'done' requires a non-null completed_at"
            )
        if (
            self.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
            and self.completed_at is not None
        ):
            raise ValueError(
                f"Task in status {self.status.value!r} must not set completed_at"
            )
        return self


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------


class Checkpoint(BaseModel):
    """A single enrichment record appended to a Session during work.

    Checkpoints are *immutable* (``frozen=True``). They form an append-only
    log of agent or hook activity within an OPEN Session.

    Attributes:
        timestamp:         When the checkpoint was emitted (UTC).
        source:            Who emitted it.
        verified_claims:   Facts the source verified (read files, ran tests).
        unverified_claims: Statements the source assumes but did not prove.
        artifacts_touched: Paths the source touched (read, created, modified).
        note:              Free-form context for the next phase (≤ 1 line).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    timestamp: datetime
    source: CheckpointSource
    verified_claims: list[str] = Field(default_factory=list)
    unverified_claims: list[str] = Field(default_factory=list)
    artifacts_touched: list[str] = Field(default_factory=list)
    note: str = ""

    @field_validator("timestamp")
    @classmethod
    def _validate_timestamp(cls, value: datetime) -> datetime:
        return _to_utc(value, "timestamp")


# ---------------------------------------------------------------------------
# VerificationHookResult
# ---------------------------------------------------------------------------


class VerificationHook(BaseModel):
    """One verification hook declared in a spec.

    Verification hooks are commands the spec author declares to *objectively
    prove* that the work for a spec is done. They are executed by
    :class:`cortex.session.verification.VerificationRunner` after the user
    runs ``cortex finish-session``.

    Attributes:
        name:             Short human-readable label (must be non-empty
                          and unique within a spec).
        command:          Shell command to execute, run with ``shell=True``
                          in the repo root.
        required:         When True (default), a failure marks the session
                          as ``handoff`` instead of ``closed``. Failures of
                          non-required hooks are recorded but don't block.
        success_criteria: Documentation string. Not evaluated; success is
                          determined by exit code 0 from the command.
        timeout_seconds:  Wall-clock limit. Reaching it cancels the hook
                          with ``passed=False`` and ``exit_code=-1``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    command: str = Field(min_length=1)
    required: bool = True
    success_criteria: str = "exit code 0"
    timeout_seconds: int = Field(default=300, ge=1, le=1800)


class VerificationHookResult(BaseModel):
    """Captured outcome of executing one verification hook from the spec.

    Verification hooks are commands the spec declares to *objectively prove*
    that the work is done (tests, type-checks, lint, file presence, etc.).
    The runner (see Phase 01: ``cortex/session/verification.py``) builds one
    of these per executed hook.

    Output is truncated to :data:`MAX_VERIFICATION_OUTPUT_BYTES`, keeping the
    tail (most informative for failure analysis).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    command: str
    passed: bool
    exit_code: int
    output: str
    duration_ms: int = Field(ge=0)
    run_at: datetime

    @field_validator("output")
    @classmethod
    def _validate_output_size(cls, value: str) -> str:
        return _truncate_output(value)

    @field_validator("run_at")
    @classmethod
    def _validate_run_at(cls, value: datetime) -> datetime:
        return _to_utc(value, "run_at")


# ---------------------------------------------------------------------------
# SessionRecord — the root document
# ---------------------------------------------------------------------------


class SessionRecord(BaseModel):
    """The complete record of a development Session.

    Persists as YAML to ``.cortex/sessions/<session_id>.yaml``. Opened
    automatically by ``cortex_create_spec`` (Phase 00) and closed by
    ``cortex finish-session`` (Phase 01).

    Invariants enforced at validation:
        * ``session_id`` matches ``YYYY-MM-DD_<slug>``.
        * ``start_commit`` (and ``end_commit`` when set) is a 40-char hex SHA.
        * If ``status == OPEN`` then ``closed_at``, ``end_commit`` and
          ``documenter_decision`` MUST all be ``None``.
        * If ``status`` is terminal (CLOSED / HANDOFF / ABANDONED) then those
          three fields MUST all be non-None.

    Mutation pattern:
        ``SessionRecord`` is mutable through validated assignment
        (``validate_assignment=True``). The service layer mutates the record
        (e.g. appending to ``checkpoints``, updating ``status``) and persists
        the new state via ``SessionStorage.save``. Inner records
        (:class:`Checkpoint`, :class:`VerificationHookResult`) are frozen.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # ── Identity ────────────────────────────────────────────────────
    session_id: str
    spec_path: Path
    spec_summary: str = ""

    # ── Repo snapshot at open time ─────────────────────────────────
    start_commit: str
    start_branch: str
    opened_at: datetime

    # ── Live state ─────────────────────────────────────────────────
    status: SessionStatus = SessionStatus.OPEN
    mode: SessionMode = SessionMode.UNKNOWN

    # ── Enrichment (appended during OPEN) ──────────────────────────
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    verification_results: list[VerificationHookResult] = Field(default_factory=list)
    # Pluggable Middle Phase 09.C: optional task decomposition. Opt-in
    # via ``cortex create-spec --with-tasks``. Empty list means the
    # legacy non-granular workflow.
    tasks: list[Task] = Field(default_factory=list)

    # ── Close-time fields (None while OPEN) ────────────────────────
    closed_at: datetime | None = None
    end_commit: str | None = None
    documenter_decision: SessionStatus | None = None
    session_note_path: Path | None = None
    adrs_created: list[Path] = Field(default_factory=list)

    # ── Field validators ──────────────────────────────────────────

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, value: str) -> str:
        if not SESSION_ID_PATTERN.match(value):
            raise ValueError(
                f"session_id {value!r} does not match required pattern "
                "'YYYY-MM-DD_<slug>' (slug: lowercase a-z0-9 and hyphens, "
                "must start with a-z0-9)"
            )
        return value

    @field_validator("start_commit")
    @classmethod
    def _validate_start_commit(cls, value: str) -> str:
        if not COMMIT_SHA_PATTERN.match(value):
            raise ValueError(
                f"start_commit must be a 40-character lowercase hex SHA, got {value!r}"
            )
        return value

    @field_validator("end_commit")
    @classmethod
    def _validate_end_commit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not COMMIT_SHA_PATTERN.match(value):
            raise ValueError(f"end_commit must be a 40-character lowercase hex SHA, got {value!r}")
        return value

    @field_validator("opened_at")
    @classmethod
    def _validate_opened_at(cls, value: datetime) -> datetime:
        return _to_utc(value, "opened_at")

    @field_validator("closed_at")
    @classmethod
    def _validate_closed_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _to_utc(value, "closed_at")

    # ── Model-level invariants ────────────────────────────────────

    @model_validator(mode="after")
    def _validate_status_invariants(self) -> SessionRecord:
        is_terminal = self.status.value in _TERMINAL_STATUSES
        terminal_fields = {
            "closed_at": self.closed_at,
            "end_commit": self.end_commit,
            "documenter_decision": self.documenter_decision,
        }
        if is_terminal:
            missing = sorted(k for k, v in terminal_fields.items() if v is None)
            if missing:
                raise ValueError(
                    f"Session in status {self.status.value!r} requires non-null "
                    f"fields: {', '.join(missing)}"
                )
        else:
            populated = sorted(k for k, v in terminal_fields.items() if v is not None)
            if populated:
                raise ValueError(
                    f"Session in status {self.status.value!r} must not set "
                    f"close-time fields: {', '.join(populated)}"
                )
        return self

    @property
    def is_gitless(self) -> bool:
        """Whether this session was opened without a usable git repository.

        Inferred from ``start_commit == GITLESS_COMMIT_PLACEHOLDER``. The
        sentinel is set by :meth:`SessionService.open` when
        :func:`cortex.session.git.is_git_repo` returns ``False`` for the
        workspace. Documenter, doctor and the close path read this flag
        to skip git operations and produce a degraded session note.
        """
        return self.start_commit == GITLESS_COMMIT_PLACEHOLDER
