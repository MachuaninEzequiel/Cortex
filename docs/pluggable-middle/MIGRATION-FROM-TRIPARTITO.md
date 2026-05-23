# Migration Guide — Tripartito → Pluggable Middle

> **Audience:** users (or tooling) that were on the original mandatory
> tripartite Cortex flow (`cortex-sync` → `cortex-SDDwork` → `cortex-documenter`)
> and now want to move to the Pluggable Middle architecture.
>
> **TL;DR.** Your existing flow keeps working unchanged — Managed mode
> reproduces it exactly. The new architecture only **adds** options
> (Observed, BYO, interactive documenter). Read on if you want to take
> advantage of them.

---

## 1. The two-line summary

| | Before (tripartito) | After (Pluggable Middle) |
|---|---|---|
| Workflow shape | sync → SDDwork → documenter (mandatory) | sync → *one of three middles* → documenter |
| Inter-agent contract | YAML `AgentHandoff` blocks emitted between subagents | `cortex.session.SessionRecord` + checkpoints |
| Closing the loop | `cortex_save_session` invoked by SDDwork at the end | `cortex finish-session` invoked by the user |

The endpoints (sync and documenter) are unchanged in concept. The middle
is now replaceable.

---

## 2. Concept mapping

| Tripartito concept | Pluggable Middle equivalent | Notes |
|---|---|---|
| Mandatory `cortex-SDDwork` middle | **Managed mode** (one of three) | Reproduces the prior behaviour 1:1. |
| YAML handoff between subagents | `cortex_session_checkpoint(source=...)` | The Session is the contract. |
| `cortex_save_session` (called by SDDwork) | `cortex finish-session` (called by the user) | The user closes the loop now. |
| Spec without verification | Spec **with verification hooks** (mandatory) | Sync must declare ≥ 1 hook. |
| Session note generated from YAML inline | Session note **reconstructed** from spec + diff + checkpoints + hooks | Documenter reads the Session, not a YAML payload. |
| Autopilot was a separate lifecycle | Autopilot is a thin policy layer over Sessions | `cortex autopilot start/checkpoint/finish` still works as alias. |

---

## 3. The three new modes

You choose at `create-spec` time (implicitly, by what you do next):

```
                          cortex create-spec
                              │
                              ▼
              ┌────────── Session opened (active) ─────────┐
              │                  │                          │
              ▼                  ▼                          ▼
       ┌───────────┐      ┌───────────┐               ┌───────────┐
       │  Managed  │      │  Observed │               │   BYO     │
       │ (SDDwork) │      │  (IDE hook)              │  (manual)  │
       └─────┬─────┘      └─────┬─────┘               └─────┬─────┘
             │                  │                            │
             └───────── cortex finish-session ───────────────┘
                              │
                              ▼
                      documenter reconstructs +
                      persists session note
```

| Mode | When to use it | Setup needed |
|---|---|---|
| **Managed** | No own tooling, or you want disciplined Fast/Deep Track. | None — invoke `cortex-SDDwork` skill manually or via your IDE. |
| **Observed** | You have your own skills/agents in Cursor / Claude Code / Pi. | Once: `cortex session hooks install --ide <name>`. |
| **BYO** | Manual work, any other agent, "vibe coding". | None — just edit + commit. |

The mode is **inferred at close time** from the set of checkpoint
sources (`SessionService.infer_mode`):
- 0 checkpoints → BYO.
- All Cortex agent sources (sync / SDDwork / explorer / implementer) → Managed.
- Any IDE hook / user-skill / manual / mix → Observed.

---

## 4. Command mapping

### 4.1 What changed

| Before | After | Notes |
|---|---|---|
| (implicit, via subagents) | `cortex create-spec ... --verification-hook 'name=t;command=...'` | Spec now requires verification hooks. |
| `cortex save-session ...` (called by SDDwork) | `cortex finish-session [ID] [--interactive]` | User-invoked closure. |
| YAML handoff inline | `cortex session checkpoint --source <s> --note ... --artifact path` | Append to the active Session. |
| `cortex autopilot install --ide X` | `cortex session hooks install --ide X` | Old alias still accepted; new command is canonical. |
| `cortex autopilot cleanup` | (removed) | JSONL events no longer exist. |
| `cortex autopilot report` | `cortex session list` | Covered by the canonical session listing. |

### 4.2 What is new

| Command | Purpose |
|---|---|
| `cortex session current` | id of the active session |
| `cortex session list [--status open\|closed\|...]` | list sessions on disk |
| `cortex session show [ID]` | full detail |
| `cortex session diff [ID]` | `git diff start_commit..HEAD` |
| `cortex session switch <ID>` | promote a different OPEN session to active |
| `cortex session abandon <ID> --reason X` | close as ABANDONED, no note |
| `cortex session checkpoint ...` | append a checkpoint (invoked by IDE hooks) |
| `cortex session hooks list \| install \| uninstall \| status` | manage IDE hooks |
| `cortex finish-session [--interactive]` | close the active session via the documenter |

### 4.3 What stayed (with deprecation warnings)

| Surface | Status | Reason |
|---|---|---|
| `cortex autopilot start/checkpoint/finish/status/doctor` | alias, kept | UX continuity; delegates to Sessions internally. |
| `cortex_autopilot_*` MCP tools | alias, kept | Same — body delegates. |
| `cortex_validate_handoff` MCP tool | deprecated (warning) | Used by Legacy YAML mode of the documenter for single-agent IDEs (Codex). |
| `cortex.handoff.AgentHandoff` Pydantic schema | deprecated (docstring) | Same — Legacy YAML mode. |
| `cortex.services.session_service` import path | deprecated alias | Renamed to `note_service.py`. Old import emits `DeprecationWarning`. |

---

## 5. Workflow examples — side by side

### 5.1 Implementing a small feature with `cortex-SDDwork`

**Before:**

```bash
$ cortex create-spec --title "JWT refresh" --goal "..."
# Switch to cortex-SDDwork profile in the IDE.
# SDDwork orchestrates Fast Track; emits YAML AgentHandoff at the end.
# Documenter consumes the YAML and calls cortex_save_session.
```

**After (Managed mode reproduces this 1:1):**

```bash
$ cortex create-spec --title "JWT refresh" --goal "..." \
    --verification-hook 'name=tests;command=pytest tests/auth/'
# Session opens automatically.
# Switch to cortex-SDDwork (or invoke as Skill).
# SDDwork emits cortex_session_checkpoint(source="cortex-SDDwork") instead
#   of YAML — no behavioural difference visible to the user.
$ cortex finish-session         # user closes the loop
```

### 5.2 Implementing the same feature in Cursor (Observed mode — new)

```bash
$ cortex session hooks install --ide cursor   # once per repo
$ cortex create-spec --title "JWT refresh" --goal "..." \
    --verification-hook 'name=tests;command=pytest tests/auth/'
# Work in Cursor / VSCode / Cline / Roo with your usual skills.
# Each git commit emits a checkpoint automatically (post-commit hook).
$ cortex finish-session --interactive   # review + persist
```

### 5.3 Implementing the same feature manually (BYO mode — new)

```bash
$ cortex create-spec --title "JWT refresh" --goal "..." \
    --verification-hook 'name=tests;command=pytest tests/auth/'
# Edit files manually. No agent, no hook. No checkpoint.
$ git commit -m "JWT refresh"
$ cortex finish-session    # documenter reconstructs from diff + hooks
```

### 5.4 The documenter interactive mode (new in Phase 04)

```bash
$ cortex finish-session --interactive
```

Renders the draft session note, the suggested ADRs (with the 3/3
criteria heuristic), the scope drift, and the verification results.
Hotkeys:

- `[A]` — approve everything as-is.
- `[E]` — review title (inline), body (in `$EDITOR`), ADRs (one by one).
- `[H]` — close as HANDOFF, capture a reason.
- `[C]` — cancel; the session stays OPEN.

Set `documenter.default_mode: interactive` in `.cortex/config.yaml` if
you want this as your default.

---

## 6. Code-level changes for downstream tooling

If your tooling imported anything from the autopilot module, here is the
1:1 mapping after Phase 04 cleanup:

| Old import | New import |
|---|---|
| `cortex.autopilot.models.AutopilotSessionState` | `cortex.session.models.SessionRecord` |
| `cortex.autopilot.models.AutopilotCheckpoint` | `cortex.session.models.Checkpoint` |
| `cortex.autopilot.models.SessionDraft` | (removed; the documenter writes session notes via `cortex.services.NoteService`) |
| `cortex.autopilot.session_writer.IndexingSessionWriter` | (removed in Phase 03; transactional rollback ported to `cortex.services.note_service.NoteService.create` in Phase 08 / T8.1) |
| `cortex.autopilot.state_store.StateStore` | `cortex.session.storage.SessionStorage` |
| `cortex.autopilot.policies.base.AutopilotPolicy` | `cortex.autopilot.policies.AutopilotPolicy` (consolidated module) |
| `cortex.autopilot.adapters.cursor.CursorAutopilotAdapter` | `cortex.session.hooks.adapters.cursor.CursorGitHookAdapter` (different Protocol — see §7) |
| `cortex.services.session_service.SessionService` (the note service) | `cortex.services.note_service.NoteService` |
| `cortex.autopilot.delegation.DelegationEngine` | (removed in Phase 03; spirit ported to `cortex.session.quality_gates.review_checkpoint` — pure function exposed as MCP tool `cortex_review_checkpoint` in Phase 08 / T8.2) |
| `cortex.autopilot.context_budget.BUDGET_PROFILES` | `cortex.context_enricher.budget_resolver.resolve_budget_profile` (Phase 08 / T8.4) |

### What's new in Phase 08 (Managed quality gates)

| Symbol | Where | Notes |
|---|---|---|
| `cortex_review_checkpoint` (MCP tool) | `cortex.mcp.server` | Two-stage review (spec compliance + quality) over any checkpoint of an OPEN session. Used by SDDwork in Deep Track. |
| `cortex.session.quality_gates.review_checkpoint` | new pure module | Same logic without the MCP wrapper — testable / reusable. |
| `cortex.context_enricher.budget_resolver.resolve_budget_profile` | new pure module | Maps `task_type` → `(top_k, max_chars)`. `cortex_context` accepts `task_type` and resizes retrieval. |
| `NoteService.create(task_type=...)` | `cortex.services.note_service` | Drives the conditional `session.md.j2` (omit noise on `question-only`/`docs-only`, add Security Review on `security`). |
| Tag `auto-draft` | session note frontmatter | Attached by the documenter's self-review when placeholders / unreferenced files / hollow success claims are detected. |

### What's new in Phase 09 (SDD refinement: proposal + design + tasks)

| Symbol | Where | Notes |
|---|---|---|
| `--proposal-mode`, `--proposal-confirmed` | `cortex create-spec` (CLI + MCP `cortex_create_spec`) | Phase 09.A gate. Values: `optional` (default), `required` (rejects without confirmation), `skip`. |
| `cortex-code-designer` subagent | `.cortex/subagents/` + `cortex-pi/.pi/agents/` | Phase 09.B. Writes `vault/designs/<session_id>.md` between explorer and implementer in Deep Track. |
| `DocType.DESIGN`, `DesignDocData`, `DesignFrontmatter` | `cortex.documentation.{doc_type,data,schemas}` | New canonical doc type. Local-only (not promotable). |
| `write_design_note` / `write_design_note_canonical` | `cortex.documentation.writers` | Canonical writer + MCP-callable alias. |
| `write_design_note_canonical` (MCP tool) | `cortex.mcp.server` | Persists the design doc; returns `{"path": ...}`. |
| `CheckpointSource.CORTEX_CODE_DESIGNER` | `cortex.session.models` | New enum value for designer-emitted checkpoints. |
| `Task`, `TaskStatus`, `SessionRecord.tasks` | `cortex.session.models` | Phase 09.C. Granular task decomposition. Default `[]` keeps legacy sessions compatible. |
| `cortex session task ...` CLI subapp | `cortex.cli.session` | `list / done / in-progress / skip / block`. |
| `cortex_session_task_list`, `cortex_session_task_update` (MCP tools) | `cortex.mcp.server` | The update tool doubles as create-or-update when `description` is supplied. |
| `--with-tasks` | `cortex create-spec` | Adds the `tasks-required` tag the SDDwork skill reads to emit a task decomposition. |
| Session note summary line | `cortex.documenter.persistence` | Adds `tasks: X/Y done` when tasks exist. |

For Python callers using the `AgentMemory` façade (`from cortex import
AgentMemory`), nothing changed — `open_session`, `checkpoint_session`,
`close_session`, `get_active_session`, `list_sessions`, `get_session`
keep their signatures.

---

## 7. IDE adapter contract change

The legacy `AutopilotHookAdapter` Protocol (single `install/uninstall/
emit_session_start` per IDE, emitting bootstrap JSON to the IDE) is
replaced by the Phase 03 `HookAdapter` Protocol (single
`install/uninstall/status/is_supported` per IDE, where the hook
**emits checkpoints back into Cortex**). The direction flipped:

```
Before:  cortex → JSON payload → IDE bootstrap
After:   IDE event → "cortex session checkpoint" → SessionRecord
```

If you had a custom adapter for an unsupported IDE, port it to the new
Protocol (~60 LOC) and place it under
`cortex/session/hooks/adapters/<your-ide>.py`. See `claude_code.py`,
`cursor.py`, `pi.py` for reference implementations.

---

## 8. Frequently asked questions

**Q: Do I need to migrate existing session notes?**
No. The persisted notes in `vault/sessions/` keep the same format. Only
the **runtime contract** between agents changed.

**Q: Is the old `cortex autopilot ...` CLI gone?**
No. `start / checkpoint / finish / status / doctor` are preserved as
aliases that delegate to the new `AutopilotService` (which itself wraps
`SessionService` + `PolicyEnforcer`). `cleanup`, `report`, `install`,
`uninstall` are removed (`cleanup` and `report` are now no-ops because
JSONL events no longer exist; `install`/`uninstall` moved to
`cortex session hooks ...`).

**Q: Does the documenter still accept YAML handoffs?**
Yes — Legacy YAML mode is **deprecated** (warning) but functional. It
covers single-agent IDEs (Codex) that cannot emit checkpoints inline.
A future major release will remove it once Codex (or equivalent)
supports `cortex_session_checkpoint` natively.

**Q: How do I tell which mode my session ended in?**
`cortex session show <ID>` reports `mode: byo | managed | observed`.
The mode is inferred at close time from the checkpoint sources.

**Q: Can I have multiple OPEN sessions at once?**
Yes. `cortex session list` shows them, `cortex session switch <ID>`
promotes one to active. `cortex doctor` warns if multiple OPEN sessions
exist alongside a stale active pointer.

---

## 9. Where to read next

- `docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md` — full
  design with diagrams and decisions.
- `docs/architecture/session-primitive.md` — technical reference for
  the Session module (§8 covers IDE hooks).
- `docs/architecture/pluggable-middle-overview.md` — short overview
  (3 pages) for new contributors.
- `docs/pluggable-middle/fases/` — per-phase implementation plans
  (00-04). Useful only if you're maintaining the framework itself.
