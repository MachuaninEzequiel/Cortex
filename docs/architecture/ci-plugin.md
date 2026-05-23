---
title: CI plugin
status: stable
introduced_in: Phase 07 (Pluggable Middle)
---

# Cortex CI plugin

> **Phase 07 deliverable.** Provider-agnostic CLI that validates a pull
> request against the matching Cortex `SessionRecord` + spec, optionally
> renders a sticky PR comment, and (Level 3) attaches an audit trail to
> a CI-owned review session.

## Levels

| Level | Surface | Status |
|---|---|---|
| 1 — validation gate | `cortex ci validate-pr` + `templates/ci/*.yml` | shipped |
| 2 — PR comment       | `--format pr-comment` + sticky comment step | shipped |
| 3 — review sessions  | `open-review-session`, `report-checkpoint`, `close-review-session` + `CheckpointSource.CI_BOT` + `SessionMode.CI_REVIEW` | shipped |

The three levels are independent — you can adopt them gradually.

---

## Level 1 — validation gate

```bash
cortex ci validate-pr \
    [--diff <file>]                      \
    [--base-commit <sha>]                \
    [--head-commit <sha>]                \
    [--base-branch <name>]               \
    [--head-branch <name>]               \
    [--pr-number <int>]                  \
    [--pr-author <user>]                 \
    [--session <id>]                     \
    [--format json|text|pr-comment]      \
    [--project-root <path>]
```

The validator runs four checks:

1. **Session matching** (priority order: `--session` → base_commit →
   head_branch → none). `none` → exit 2.
2. **Scope** (re-uses `cortex.documenter.reconstruction._scope_cross_check`).
   Out-of-scope files become *warnings*; in-scope files not implemented
   become *blockers*.
3. **Verification hooks** declared in the spec. Required failures block;
   non-required failures warn.
4. **Lifecycle** — a HANDOFF session warns; an ABANDONED session blocks.

### Exit codes

| Code | Meaning |
|---:|---|
| 0 | pass |
| 1 | pass with warnings (non-blocking) |
| 2 | blocked (required hook failed, no session match, etc.) |
| 3 | error (git failure, missing diff file, …) |

### Output formats

| Format | Use case |
|---|---|
| `json` (default) | machine consumers (downstream gates, dashboards) |
| `text` | local debugging |
| `pr-comment` | Markdown body for `gh pr comment` (Level 2) |

The JSON shape is stable; see `cortex.ci.result.ValidationResult.to_json_dict`.

---

## Level 2 — sticky PR comment

`--format pr-comment` renders the Markdown body delimited by the
sentinel marker:

```
<!-- cortex-pr-summary -->
```

The provider-side step (see `templates/ci/github-actions-cortex-validate.yml`)
uses `gh pr comment --edit-last` so re-runs of the workflow update the
same comment instead of stacking new ones.

---

## Level 3 — review sessions

Each PR run can open a CI-owned `SessionRecord` that records:

* The base commit + source branch.
* One or more `CheckpointSource.CI_BOT` checkpoints (one per validate
  run; can be split across stages).
* A terminal status (closed / handoff / abandoned) and a derived
  `SessionMode.CI_REVIEW` when every checkpoint came from CI.

```bash
SESSION_ID=$(cortex ci open-review-session \
    --pr-number 42 --base-commit $BASE --head-branch feature/x --json \
    | jq -r .session_id)

cortex ci validate-pr --base-commit $BASE --head-commit $HEAD \
    --session "$SESSION_ID" --format json > /tmp/cortex.json

cortex ci report-checkpoint \
    --session-id "$SESSION_ID" \
    --from-validation-result /tmp/cortex.json

cortex ci close-review-session --session-id "$SESSION_ID" --status closed
```

Review sessions persist alongside developer sessions in
`.cortex/sessions/`. They never invoke the documenter — their role is
audit trail only.

See [`review-sessions.md`](review-sessions.md) for the architectural
decision rationale (Opción B was chosen).

---

## Provider templates

| File | Provider |
|---|---|
| `templates/ci/github-actions-cortex-validate.yml` | GitHub Actions (L1+L2) |
| `templates/ci/gitlab-ci-cortex-validate.yml`     | GitLab CI (L1+L2)      |
| `templates/ci/README.md`                          | adoption + tips        |
