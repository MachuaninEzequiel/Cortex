---
title: Session primitive
status: stable
introduced_in: Phase 00 (Pluggable Middle architecture)
---

# Session primitive

> **Phase 01 (Pluggable Middle) update:** the documenter now reads a
> Session and reconstructs the work via ``cortex finish-session``. The
> sections below describe the primitive itself; for the reconstruction
> algorithm see ``docs/pluggable-middle/fases/01-DOCUMENTER-RECONSTRUCTION.md``.

## Managed mode: checkpoints flow (Phase 02)

```
$ cortex create-spec ...
→ vault/specs/2026-05-16_*.md, Session opened (active)

# Managed: SDDwork orchestrates, emitting checkpoints

(SDDwork)    cortex_session_checkpoint(source="cortex-SDDwork", ...)
  ↓ delegates (Deep Track)
(explorer)   cortex_session_checkpoint(source="cortex-code-explorer", ...)
(implementer) cortex_session_checkpoint(source="cortex-code-implementer", ...)
(SDDwork)    cortex_session_checkpoint(source="cortex-SDDwork", ...)   # wrap-up

# user runs

$ cortex finish-session
→ documenter reads ALL checkpoints + diff + hooks
→ session note includes:
   * "Key Decisions" populated from checkpoint `note` fields
   * "Verified State" populated from `verified_claims`
   * "Unverified Claims" populated from `unverified_claims`
   * "Blockers" populated from failed verification hooks
→ mode inferred as MANAGED (because all sources are Cortex agents)
→ ADR candidates surfaced from checkpoint notes (3/3 criteria heuristic)
```

No YAML AgentHandoff inline. The Session itself is the inter-agent contract.

---

## BYO mode lifecycle (Phase 01)

```
$ cortex create-spec --title "..." --goal "..." --file src/x.py \
    --verification-hook 'name=tests;command=pytest tests/x/'
→ writes vault/specs/2026-05-16_*.md, opens Session

# user edits files with any tool / agent, commits

$ cortex finish-session
→ reconstructs:
    - git diff start_commit..HEAD
    - runs verification_hooks
    - cross-checks scope, surfaces drift / unimplemented
    - builds AgentHandoff synthetically (no inline YAML required)
→ persists vault/sessions/<id>.md
→ closes Session as CLOSED (or HANDOFF if hooks fail / scope incomplete)
```

---


The **Session** is the core primitive of the Pluggable Middle architecture.
It tracks the lifecycle of a single unit of development — from the moment
`cortex-sync` creates a spec until `cortex finish-session` (Phase 01)
persists the session note.

> **Source of truth:** `docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md` §5.
> This document is the technical reference for the module produced in
> Phase 00. Use it as the entry point for callers and contributors.

---

## 1. Why a Session

The original Cortex flow forced one monolithic protocol on every adopter:
`sync → SDDwork → documenter`. The Pluggable Middle architecture removes
that constraint by making the middle replaceable (Managed / Observed /
BYO). To keep the framework opinionated *and* flexible, we need a small
piece of shared state that:

- Anchors the spec, start commit, and start branch at the time work begins.
- Accumulates checkpoints from any middle (or none).
- Records the close-time decision (closed / handoff / abandoned).

That piece of state is the Session. Without it, the documenter (Phase 01)
could not reconstruct what happened between spec creation and finish.

---

## 2. On-disk layout

```
.cortex/sessions/
    active.txt                # one line: id of the active session (or empty)
    2026-05-16_auth-jwt.yaml  # one file per Session
    2026-05-15_login.yaml
```

`active.txt` is the only mutable global state. Each session YAML is
written atomically (`*.tmp` + `os.replace`) so a crashed write never
leaves a half-written file behind.

A representative on-disk Session:

```yaml
session_id: 2026-05-16_auth-jwt
spec_path: vault/specs/2026-05-16_auth-jwt.md
spec_summary: Implementar refresh tokens JWT
start_commit: abc123def4567890...
start_branch: feature/auth-jwt
opened_at: 2026-05-16T10:00:00+00:00
status: open
mode: unknown
checkpoints:
  - timestamp: 2026-05-16T10:15:00+00:00
    source: cortex-SDDwork
    verified_claims: ["wrote auth.py"]
    unverified_claims: []
    artifacts_touched: ["src/auth.py"]
    note: "fast track"
verification_results: []
closed_at: null
end_commit: null
documenter_decision: null
session_note_path: null
adrs_created: []
```

---

## 3. Lifecycle

```
                  cortex create-spec
                   (auto session_open)
                          |
                          v
                    +-----------+
              +---->|   OPEN    |
              |     +-----+-----+
              |           |
              | +---------+----------+
              | |         |          |
              | v         v          v
        checkpoint   finish      abandon
              |   complete/handoff   |
              |         |            |
              |         v            v
              |    +---------+  +-----------+
              |    | CLOSED  |  | ABANDONED |
              |    | HANDOFF |  +-----------+
              |    +---------+
              |
              +--- accepts more checkpoints while OPEN
```

Once a Session leaves OPEN, the record becomes read-only. Re-opening is
not supported by design — the documenter creates a new Session for any
follow-up work.

---

## 4. Mode inference

When a Session closes, the mode is inferred from the set of checkpoint
sources:

| Checkpoints present                                                  | Inferred mode |
|----------------------------------------------------------------------|---------------|
| None                                                                 | `byo`         |
| Only Cortex sources (`cortex-sync`, `cortex-SDDwork`, explorer, implementer) | `managed`     |
| Anything else (IDE hooks, user skills, manual annotations)           | `observed`    |

This is a pure function — see `SessionService.infer_mode`.

---

## 5. Public API surface

### CLI

| Command                                          | Purpose                                           |
|---|---|
| `cortex session current`                         | Print the id of the active Session.               |
| `cortex session list [--status STATUS] [--json]` | List sessions on disk, newest first.              |
| `cortex session show [SESSION_ID] [--json] [--watch]` | Full detail; pass `--watch` to open the live TUI focused on this session (Phase 06). |
| `cortex session watch [SESSION_ID] [--refresh N]` | **Live TUI** (Phase 06): refresh every `N` seconds (default 1.5). Active session panel, checkpoints, diff preview, verification status and recent-sessions sidebar. Ctrl+C to exit. |
| `cortex session diff [SESSION_ID]`               | `git diff start_commit..(end_commit|HEAD)`        |
| `cortex session switch <SESSION_ID>`             | Promote a different OPEN session to active.       |
| `cortex session abandon <SESSION_ID> --reason X` | Close as `abandoned`, recording the reason as a manual checkpoint. |

All commands accept `--project-root <path>` and skip the heavy
`AgentMemory` façade — Session management only needs git and the
on-disk YAMLs.

### MCP tools

| Tool name                    | Purpose                                          |
|---|---|
| `cortex_session_open`         | Open a Session (normally invoked transparently from `cortex_create_spec`). |
| `cortex_session_checkpoint`   | Append a checkpoint to an OPEN Session.          |
| `cortex_session_close`        | Close a Session into a terminal status.          |
| `cortex_session_status`       | Return a full SessionRecord (active by default). |
| `cortex_session_list`         | List summarized records (optionally filtered by status). |

Every tool input is schema-validated. Invalid `source` or `status`
values are rejected with an actionable message that lists the allowed
values.

### Python (façade)

```python
from cortex import AgentMemory

memory = AgentMemory()

# Open is implicit on create_spec; equivalent direct call:
session = memory.open_session(
    spec_id="2026-05-16_demo",
    spec_path="vault/specs/2026-05-16_demo.md",
    spec_summary="demo",
)

# Enrich during work
memory.checkpoint_session(
    session.session_id,
    source="cortex-SDDwork",
    verified_claims=["wrote auth.py"],
    note="fast track",
)

# Close at the end (this is what Phase 01's `cortex finish-session`
# will trigger from the documenter)
memory.close_session(
    session.session_id,
    status="closed",
    documenter_decision="closed",
)
```

---

## 6. Invariants enforced by the model

These are checked by Pydantic at construction time and by `SessionStorage`
when re-validating on read:

- `session_id` matches `^\d{4}-\d{2}-\d{2}_[a-z0-9][a-z0-9-]*$`.
- `start_commit` and `end_commit` (when set) are 40-char lowercase hex.
- All datetimes are timezone-aware and normalized to UTC.
- An OPEN session has all close-time fields (`closed_at`, `end_commit`,
  `documenter_decision`) set to `None`.
- A terminal session (CLOSED / HANDOFF / ABANDONED) has all those
  fields populated.
- `Checkpoint` and `VerificationHookResult` are immutable (`frozen=True`).

Violations of any of these become a `pydantic.ValidationError` at
construction time, and the storage layer wraps load failures as
`SessionStorageCorrupted` for the explicit `load()` path — `list_all()`
logs and skips so that one corrupted file doesn't break the rest.

---

## 7. `cortex doctor` integration

`cortex doctor` includes a `[sessions]` section that validates:

1. The `.cortex/sessions/` directory exists and is writable.
2. The active pointer (if set) references an existing session.
3. All YAML files on disk parse successfully (warnings for the ones that
   don't).
4. Invariants hold for every parsed record.
5. At most one OPEN session is the active one; extra OPENs trigger a
   `sessions_multiple_open` warning suggesting a `switch` or `close`.

Run it with:

```bash
cortex doctor                 # default scope
cortex doctor --scope all     # includes enterprise checks
```

---

## 8. IDE hooks (Phase 03 — Observed mode)

Phase 03 added `cortex.session.hooks`, a generic installer for IDE-side
triggers that emit checkpoints automatically. Each adapter installs a
small artifact in the project root (or user config) that, on an IDE
event, invokes ``cortex session checkpoint --source ide-hook ...``.

| Adapter | Target file | Event |
|---|---|---|
| `claude-code` | `.claude/settings.json` (`hooks.PostToolUse`) | After every Edit / Write / MultiEdit tool use |
| `cursor`      | `.git/hooks/post-commit`                       | After every git commit (also covers VSCode / Cline / Roo) |
| `opencode`    | `.opencode/hooks.md` (markdown block, Phase 05) | After every significant edit in opencode |
| `pi`          | `justfile` (`cortex-checkpoint` recipe)        | Invoked from Pi flows via `just cortex-checkpoint` |

CLI surface:

```bash
cortex session hooks list                  # tabular status of every adapter
cortex session hooks install --ide cursor
cortex session hooks status --ide cursor
cortex session hooks uninstall --ide cursor
```

Implementation contract:

* Each adapter implements `cortex.session.hooks.HookAdapter` (Protocol with
  `is_supported() / install() / uninstall() / status()`).
* Installs are **idempotent** — running `install` twice is a no-op.
* Hooks never abort the IDE operation: shell hooks use `|| true`, the
  Claude Code JSON entry routes through `>/dev/null 2>&1 || true`.
* Each install/uninstall is delimited by sentinel markers, so the user
  can have their own hook content in the same file without conflict.

When a hook fires the Session picks up a checkpoint with
``source=ide-hook``. At ``finish-session`` time the documenter infers
`mode = OBSERVED` from those checkpoints (see §4).

`cortex doctor` reports policy config + which IDE adapters are installed
under the current project, plus a count of ide-hook checkpoints in the
active session (to confirm the hooks are firing).

---

## 9. Quality gates (Phase 08)

Phase 08 restored five quality mechanisms that the Phase 03 Autopilot
fusion removed without porting forward. None of them change the data
model; they wire missing checks back into the existing pipeline:

| Mechanism | Owner | Behaviour |
|---|---|---|
| **Transactional indexing rollback** | `cortex.services.note_service.NoteService.create` | If semantic or episodic indexing fails after the session note is on disk, the file is `unlink`-ed and the exception propagates. Preserves the invariant *"file on disk ⇒ file indexed"*. |
| **Two-stage subagent review** | `cortex.session.quality_gates.review_checkpoint` (pure) + MCP tool `cortex_review_checkpoint` | Run by SDDwork after each subagent checkpoint in Deep Track. Stage 1: spec compliance (artifacts ⊆ scope, progress reported). Stage 2: quality (no `TBD`/`FIXME`/`???` in note, non-trivial test/build claims). Action: `accept` / `redelegate` / `warn`. |
| **Documenter self-review** | `DocumenterPersister._self_review_draft` | Scans the about-to-persist draft for placeholders, file-mention inconsistencies, and hollow success claims. Informational only — never blocks; surfaces warnings via the `auto-draft` tag and a `[self-review]` prefix in `next_steps`. |
| **Budget profile wiring** | `cortex.context_enricher.budget_resolver.resolve_budget_profile` | `cortex_context` accepts a `task_type` argument and sizes `top_k` accordingly. Question-only / noop → 0 hits; docs-only / ambiguous → 3; fast-code → 5; deep-code / security → 8. Unknown values fall back to fast-code. |
| **Conditional session template** | `cortex/documentation/templates/session.md.j2` | Single Jinja2 template with `{% if task_type == "..." %}` blocks: `question-only` / `docs-only` omit *Changes Made* and *Files Touched*; `security` renders a dedicated *Security Review* section with decorated claims; everything else keeps the full layout. |

Each gate is independently testable; none is reachable from Codex's
legacy single-agent flow.

---

## 10. SDD refinement (Phase 09)

Phase 09 closes three openspec-style workflow gaps the audit identified.
All additive; no breaking changes to the primitive.

### 10.1 Proposal step (09.A)

`cortex create-spec --proposal-mode required` makes the spec creation
reject the call unless the caller passes `--proposal-confirmed`. The
``cortex-sync`` skill prompt now emits a 2–3 line proposal *before* it
commits to the detailed spec, with explicit accept/edit/cancel
handling. Modes: ``optional`` (default — proposal emitted but spec
proceeds), ``required`` (gates), ``skip`` (legacy).

### 10.2 Design step (09.B)

* New subagent ``cortex-code-designer`` lives between explorer and
  implementer in Deep Track.
* New doc type ``design`` with ``vault/designs/<session_id>.md``
  (architecture decision + data model changes + API contracts + test
  plan + risks).
* MCP tool ``write_design_note_canonical`` persists the design doc.
* Implementer reads the design and follows it (no inline arch
  decisions).
* Skip exception: ``task_type == "docs-only"`` allows a 1-line minimal
  design.

### 10.3 Tasks granular (09.C)

* ``Task`` model + ``SessionRecord.tasks`` field (opt-in via
  ``cortex create-spec --with-tasks``).
* CLI subapp ``cortex session task list | done | in-progress | skip |
  block``.
* MCP tools ``cortex_session_task_list`` and ``cortex_session_task_update``
  (the latter creates the task on the fly when ``description`` is
  supplied — that's how SDDwork emits a decomposition in one pass).
* Naming convention: ``T<n>`` and ``T<n>.<n>`` dot-notation (e.g. `T1`,
  `T1.2`, `T2.1`). Enforced by the Pydantic model.
* Documenter reports `tasks: X/Y done (Z skipped)` in the summary line
  and the session note grows a dedicated ``## Tasks`` block when any
  task exists.

---

## 11. What's next (Phase 04+)

The primitive itself and the three execution modes (Managed, Observed,
BYO) are complete:

- Phase 00 — Session primitive (this document).
- Phase 01 — Documenter reconstruction (`cortex finish-session`).
- Phase 02 — Managed mode unified on top of checkpoints.
- Phase 03 — Autopilot fusion + Observed mode hooks (§8 above).
- Phase 04 — Interactive documenter UX (`--interactive`), final
  polish, legacy YAML removal evaluation.
- **Phase 08** — Managed quality gates restored (§9 above).
- **Phase 09** — SDD refinement (§10 above).

See `docs/pluggable-middle/fases/` for the per-phase task plans.
