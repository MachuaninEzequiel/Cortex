---
title: Pluggable Middle (short overview)
status: stable
audience: new contributors, quick orientation
canonical_design: docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md
---

# Pluggable Middle — short overview

> **3-page orientation** for someone who wants to understand the Cortex
> execution model without reading the full 800-line architecture doc.
> For the canonical design see
> [`docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`](../pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md).
> For migrating from the legacy tripartite flow see
> [`docs/pluggable-middle/MIGRATION-FROM-TRIPARTITO.md`](../pluggable-middle/MIGRATION-FROM-TRIPARTITO.md).

---

## 1. The shape of the system

Cortex frames every unit of work as **three layers**:

```
   cortex-sync       (the Analyst)        — produces the spec
        │
        ▼
   ┌─── Session opens automatically ───┐
   │                                   │
   ▼                                   ▼
   middle                              ← PLUGGABLE
   (1 of 3 modes)
   │
   ▼
   ┌─── cortex finish-session ─────────┐
   │                                   │
   ▼
   cortex-documenter   (the Guardian)  — persists the session note + ADRs
```

**Sync** and **documenter** are the two fixed endpoints. The middle is
**pluggable**: a developer picks one of three modes depending on how
much tooling they have and how much discipline they want.

---

## 2. The three modes

| Mode | Who does the work | When |
|---|---|---|
| 🟢 **Managed** | `cortex-SDDwork` skill + subagents | No own tooling, or you want enforced discipline. |
| 🟡 **Observed** | Your IDE / agent + IDE hooks | You have your own skills (Cursor, Claude Code, Pi). |
| 🔵 **BYO** | Anything (manual, another agent, …) | Maximum freedom; Cortex reconstructs from the diff. |

The mode is **inferred** at close time from the set of *checkpoint
sources* attached to the Session. No checkpoints → BYO; only Cortex
sources → Managed; anything else → Observed.

---

## 3. The Session primitive

`cortex.session.SessionRecord` is the on-disk YAML file that anchors a
unit of work from spec creation to documenter close. Lives at
`.cortex/sessions/<session_id>.yaml`. Fields:

- **Identity**: `session_id`, `spec_path`, `spec_summary`.
- **Snapshot**: `start_commit`, `start_branch`, `opened_at`.
- **Live state**: `status` (`open` / `closed` / `handoff` / `abandoned`),
  `mode` (inferred at close).
- **Enrichment**: `checkpoints` (append-only), `verification_results`.
- **Close-time**: `closed_at`, `end_commit`, `documenter_decision`,
  `session_note_path`, `adrs_created`.

A pointer file `.cortex/sessions/active.txt` names the currently active
session.

Operations: open, append checkpoint, close (terminal status), abandon,
list, switch active.

---

## 4. The full lifecycle, in one diagram

```
USER         SYNC        SESSION       MIDDLE             DOCUMENTER
 │            │             │             │                   │
 │ "do X"     │             │             │                   │
 ├───────────▶│             │             │                   │
 │            │ create-spec │             │                   │
 │            ├────────────▶│ OPEN        │                   │
 │            │             │             │                   │
 │            │             │             │ (Managed: SDDwork │
 │            │             │             │  emits checkpoints│
 │            │             │             │  Observed: IDE   │
 │            │             │             │  hook emits      │
 │            │             │             │  BYO: nothing)   │
 │            │             │◀────────────┤                   │
 │            │             │             │                   │
 │ finish-session                                             │
 ├────────────┼─────────────┼─────────────┼──────────────────▶│
 │            │             │             │                   │ load Session
 │            │             │             │                   │ git diff
 │            │             │             │                   │ run hooks
 │            │             │             │                   │ persist note
 │            │             │             │                   │ ADRs
 │            │             │             │                   │ close Session
 │ ✓ done                                                     │
 │◀───────────┼─────────────┼─────────────┼───────────────────┤
```

---

## 5. The pieces in Python

| Module | Responsibility |
|---|---|
| `cortex.session` | Primitive: `SessionRecord`, `Checkpoint`, storage, git wrapper, `VerificationRunner`. |
| `cortex.session.hooks` | IDE-side trigger installers (Claude Code, Cursor/git, Pi). |
| `cortex.documenter` | Reconstruction algorithm (8 steps) + persister + interactive UI. |
| `cortex.autopilot` | Thin policy + lifecycle wrapper over Sessions. CLI/MCP aliases preserved. |
| `cortex.services.NoteService` | Writes session notes via the canonical template. |
| `cortex.services.SpecService` | Validates and persists specs with verification hooks. |

The MCP server (`cortex/mcp/server.py`) exposes 6 canonical session
tools: `cortex_session_{open, checkpoint, close, status, list}` +
`cortex_finish_session`.

The CLI exposes them under `cortex session ...` and `cortex
finish-session` (with `--interactive` for the Phase 04 prompt UX).

---

## 6. Verification hooks — the new spec contract

Every spec must declare at least one `verification_hook`: an executable
command that **proves** the work is done. Examples:

```yaml
verification_hooks:
  - name: tests
    command: pytest tests/auth/
  - name: types
    command: mypy src/auth.py
  - name: lint
    command: ruff check src/auth.py
    required: false  # failures recorded but don't force HANDOFF
```

The documenter runs them at finish-session time. Failing required hooks
force the session to close as `HANDOFF` (work incomplete) instead of
`CLOSED`.

For research/docs-only tasks the hook can be a presence check:
`test -f docs/research-output.md`.

---

## 7. IDE hooks (Observed mode)

Install once per repo:

```bash
cortex session hooks install --ide claude-code   # .claude/settings.json
cortex session hooks install --ide cursor        # .git/hooks/post-commit
cortex session hooks install --ide pi            # justfile recipes
cortex session hooks list                        # what's installed
```

Each hook calls `cortex session checkpoint --source ide-hook ...`. All
guarded with `|| true` (or equivalent) so a Cortex failure never aborts
the IDE operation.

---

## 8. Documenter modes

- **`auto`** (default) — runs the full pipeline silently.
  `cortex finish-session` uses this unless overridden.
- **`interactive`** — `cortex finish-session --interactive` renders the
  draft + ADRs + scope drift in a `rich` UI and asks for confirmation
  ([A]pprove / [E]dit / [H]andoff / [C]ancel). Set
  `documenter.default_mode: interactive` in `.cortex/config.yaml` to
  make it the default per project.

---

## 9. Diagnostics & quality gates

`cortex doctor` (without arguments) reports the whole stack:

- `[sessions]` — directory writable, active pointer valid, all YAMLs parse.
- `[autopilot]` — policy resolved, mode active, IDE hooks installed.
- `[pluggable_middle]` — documenter modules import, interactive mode
  constructible, verification runner ready, MCP tools registered.

Run it after `cortex setup agent` to confirm a healthy install.

**Phase 08 — Managed quality gates** add five inline checks that the
pipeline runs automatically (no opt-in needed):

1. Transactional indexing rollback in `NoteService.create` so no
   session note can be on disk without being indexed.
2. Two-stage checkpoint review via the new `cortex_review_checkpoint`
   MCP tool — SDDwork runs it after each subagent in Deep Track.
3. Documenter self-review of the draft (placeholders / file mentions /
   evidence). Informational: surfaces an `auto-draft` tag instead of
   blocking the close.
4. Task-aware retrieval budget in `cortex_context` (pass `task_type`
   and `top_k` sizes itself; default falls back to fast-code).
5. Conditional `session.md.j2` template that omits noise on
   `question-only` / `docs-only` and adds a security-review section on
   `task_type == "security"`.

See `docs/architecture/session-primitive.md` §9 for the wiring details.

**Phase 06 — Sessions TUI** ships a live observability view of the
Session primitive:

```bash
cortex session watch                # active session, refresh every 1.5s
cortex session watch <ID> --refresh 3
cortex session show <ID> --watch    # alias of the above
```

The TUI renders header + active session panel + recent checkpoints +
truncated diff preview + recent-sessions sidebar in a `rich.Layout`.
The renderer is a pure function (`SessionTuiState → rich.Layout`) so
it is unit-tested against `Console(file=StringIO(), force_terminal=True,
height=60)` without a real terminal. Ctrl+C exits cleanly; non-TTY
invocations refuse to start (use `cortex session show` instead).

---

## 10. Where the design lives

| | File |
|---|---|
| Full design (one-pager not enough) | `docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md` |
| Phase plans (00 to 04, executable) | `docs/pluggable-middle/fases/*.md` |
| Session module reference | `docs/architecture/session-primitive.md` |
| Migration from tripartite | `docs/pluggable-middle/MIGRATION-FROM-TRIPARTITO.md` |
| This short overview | `docs/architecture/pluggable-middle-overview.md` |
| User-facing CHANGELOG entry | `CHANGELOG.md` → `[Unreleased] — Pluggable Middle` |
