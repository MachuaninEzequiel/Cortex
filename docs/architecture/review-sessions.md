---
title: Review sessions (Phase 07 Level 3)
status: stable
introduced_in: Phase 07 (Pluggable Middle)
---

# Review sessions

> **Decision:** Opción B — extend the existing `SessionRecord` primitive
> with `CheckpointSource.CI_BOT` and the derived `SessionMode.CI_REVIEW`.
> Two alternatives (A: new `SessionStatus.UNDER_REVIEW`; C: new
> `ReviewRecord` primitive) were considered and rejected — see §2.

## 1. What is a review session

A review session is a `SessionRecord` created by `cortex ci
open-review-session` to hold the audit log of one or more CI runs over
a pull request. It:

* Lives in the same `.cortex/sessions/` directory as developer sessions.
* Uses an explicit `base_commit` (from the PR) as `start_commit` —
  not git HEAD.
* Carries the `head_branch` of the PR as `start_branch`.
* Has a synthetic `session_id` of the shape
  `YYYY-MM-DD_pr-NNN-review` (or `YYYY-MM-DD_<branch>-review` when the
  PR number is unknown).
* Receives `CheckpointSource.CI_BOT` checkpoints from
  `cortex ci report-checkpoint`.
* Closes via `cortex ci close-review-session` into `closed`, `handoff`,
  or `abandoned` — the documenter is **not** invoked.

The session **never becomes active**. The developer's own session
(if any) keeps the active pointer.

## 2. Decision rationale

Three options were evaluated when designing Level 3:

| Option | Cost | Pros | Cons |
|---|---|---|---|
| **A.** New `SessionStatus.UNDER_REVIEW` | Invasive — touches enum, validators, storage, UI. | Explicit state. | Confuses the per-session lifecycle. |
| **B. (chosen)** New `CheckpointSource.CI_BOT` + `SessionMode.CI_REVIEW`. | Minimal — two additive enum entries. | Re-uses every primitive (storage, MCP tools, CLI). | Two sessions can coexist for the same PR (dev + review); mitigated by naming convention. |
| **C.** Separate `ReviewRecord` primitive. | Aislada — no Session impact. | Cleanest model. | Duplicates plumbing (storage, MCP tools, CLI). |

We picked **B** because the review session has the same lifecycle as a
developer session (open → checkpoint → close); the existing primitive
fits like a glove and the only new model bits are two enum values.

## 3. Mode inference

`SessionService.infer_mode` returns `SessionMode.CI_REVIEW` when **every**
checkpoint source is `CI_BOT`. A mix (e.g. a CI run + a manual "close
reason" checkpoint) falls back to `OBSERVED`. This is intentional —
mixed-source sessions are not pure audit logs and shouldn't be filtered
as if they were.

## 4. Linking dev session ↔ review session

Today the link is implicit: the review session's `start_commit` is the
PR base, which (for an in-progress dev session) usually matches
`dev_session.start_commit`. Future iterations might add an explicit
`linked_session_id` field if dashboards demand it; until then the
heuristic is sufficient and additive.

## 5. CLI flow

```bash
SESSION_ID=$(cortex ci open-review-session \
    --pr-number 42 --base-commit "$BASE" --head-branch feature/x --json \
    | jq -r .session_id)

cortex ci validate-pr --base-commit "$BASE" --head-commit "$HEAD" \
    --session "$SESSION_ID" --format json > /tmp/cortex.json

cortex ci report-checkpoint \
    --session-id "$SESSION_ID" --from-validation-result /tmp/cortex.json

cortex ci close-review-session --session-id "$SESSION_ID" --status closed
```

## 6. Storage layout

Review sessions persist in the same `.cortex/sessions/` directory as
developer sessions. `cortex session list` shows them with
`mode=ci-review` once closed.

To find the review sessions for a given PR:

```bash
cortex session list --json \
    | jq '.[] | select(.session_id | test("pr-42-review"))'
```

## 7. Trade-offs accepted

* **Two parallel sessions for a PR.** Mitigated by naming convention and
  by `mode=ci-review` (visible in `cortex session list` / `show`).
* **No documenter for review sessions.** Their role is audit, not
  enrichment. Re-using the documenter would create noise in the
  semantic memory.
* **CI runs may stack.** If the workflow re-runs over the same PR, each
  run can either re-open a new review session or reuse the existing
  one. The template re-opens (so the audit log is per-run); change the
  template if you need run-coalescing.
