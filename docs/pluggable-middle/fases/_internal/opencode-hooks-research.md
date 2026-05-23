# Opencode hooks — research note (Phase 05 / T5.1)

> **Type:** historical scratchpad. Documents what was known about
> opencode's hook surface at implementation time.
> **Date:** 2026-05-17
> **Owner of the change:** `cortex/session/hooks/adapters/opencode.py`

## 1. Sources consulted

* `cortex/autopilot/adapters/opencode.py` (pre-Phase 03; recovered from
  the deleted file in git HEAD). The original Autopilot adapter wrote a
  markdown block into `.opencode/hooks.md` using
  ``<!-- AUTOPILOT-OPENCODE -->`` sentinel markers. The hook content
  itself was a placeholder: *"Emit Cortex Autopilot bootstrap on session
  start."* — the inverse direction of what the Pluggable Middle wants
  (Cortex → IDE bootstrap), so the new adapter cannot reuse that body.
* Adjacent bundled adapters (`claude_code.py`, `cursor.py`, `pi.py`)
  for the three install/uninstall patterns Cortex already supports.
* The Pluggable Middle architecture §10.5 (Phase 03 §3.3) — the new
  hook contract is *invocation of `cortex session checkpoint
  --source ide-hook`*, not bootstrap emission.

## 2. Format chosen

`.opencode/hooks.md` (project-scoped) with sentinel markers and a fenced
``sh`` block that holds the invocation. Rationale:

* The original Autopilot adapter already targeted that path; users that
  followed Cortex's pre-Phase 03 instructions still have the directory
  layout.
* opencode's contemporary hooks mechanism (markdown + fenced shell
  invocations) is the closest analogue to what the cursor adapter does
  for `.git/hooks/post-commit`.
* Markdown is text — re-uses the cursor adapter's idempotent
  install/uninstall logic verbatim, just swapping the file location
  and adding an ``<!-- ... -->`` marker syntax.

## 3. Hook command shape

Identical to the cursor adapter:

```sh
cortex session checkpoint --source ide-hook \
    --note "edit via opencode" >/dev/null 2>&1 || true
```

The ``|| true`` guard ensures a Cortex failure (binary missing, no
active session, etc.) cannot interrupt the IDE.

## 4. Open questions left for the future

* If opencode introduces a native JSON / TOML hook descriptor, the
  markdown adapter should be deprecated. Track via the same
  ``cortex doctor`` check that lists installed adapters.
* User-scoped install (`~/.opencode/hooks.md`) is **not** supported in
  Phase 05; if users ask we can revisit with a `--scope user|project`
  flag.

## 5. Implementation notes

* Sentinel markers chosen so they survive markdown rendering and are
  unique enough to grep-and-strip on uninstall:
  * `<!-- >>> cortex-session-hook (managed by 'cortex session hooks') >>> -->`
  * `<!-- <<< cortex-session-hook <<< -->`
* Tests follow the cursor-adapter test pattern (10+ scenarios) because
  the file format is text.
