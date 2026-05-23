# `_internal/` — historical working notes

> **Read-only archive.** Status after Pluggable Middle Fase 04 is closed.

The files under this directory are the **internal scratchpads** the
agents kept during the Pluggable Middle implementation. They are
preserved for traceability but **no longer active**:

| File | Phase | What it was |
|---|---|---|
| `autopilot-audit.md` | T3.1 | Pre-refactor audit of `cortex/autopilot/` — each file mapped to its destination (DELETE / REWRITE / RELOCATE / etc.) plus 8 open design decisions and a sequential execution plan for T3.2–T3.13. The decisions in §11 of that doc were all applied by the executor; the file is now historical. |

**Do not edit these files.** If you need to plan a new round of work
on the same modules, create a fresh document under
`docs/pluggable-middle/fases/_internal/`. If you want to read what was
shipped, the source-of-truth lives in:

- `docs/pluggable-middle/fases/00–04*.md` — phase plans with Progress Log
  marking what was actually shipped.
- `docs/architecture/session-primitive.md` — technical reference.
- `docs/architecture/pluggable-middle-overview.md` — short overview.
- `docs/pluggable-middle/MIGRATION-FROM-TRIPARTITO.md` — migration guide.
- `CHANGELOG.md` `[Unreleased] — Pluggable Middle` entry.
