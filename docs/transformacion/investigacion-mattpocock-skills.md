# Research: Matt Pocock's `skills` repo for AI coding agents

Prepared for a design document. All facts below were fetched live from GitHub API /
raw.githubusercontent / the public site pages on **2026-08-27**. Nothing is fabricated.

---

## 1. Confirmed repo identity

- **URL (confirmed):** `https://github.com/mattpocock/skills` — verified via
  `api.github.com/repos/mattpocock/skills` (HTTP 200).
- **Description (exact):** *"Skills for Real Engineers. Straight from my .agents directory."*
- **Created:** 2026-02-03 · **Default branch:** `main` · **Language:** Shell · **License:** MIT
- **Stars / forks / open issues (from GitHub API at fetch time):** ~**238,498** stars, 20,284 forks, 421 open issues.
  The `aihero.dev/skills` page displayed "GitHub stars 238,494" at the same time (same magnitude).
- **Last push / latest commit:** `pushed_at` 2026-08-24; HEAD `6654f6b` (2026-08-24)
  *"feat: add 'Information access' category to retrospective skill for improved agent insights"*.
  API `updated_at` 2026-08-27.
- **Homepage:** `https://aihero.dev/skills` (HTTP 200) — describes it as
  *"AI Skills for Real Engineers. A practical skill system for engineers who want to use AI without giving up their standards."*
- **Related public listing:** `https://skills.sh/mattpocock/skills` (HTTP 200) — reports **"53 skills, 18.6M total installs"**
  and per-skill install counts (grill-me ≈ 982.8K, grill-with-docs ≈ 837.5K, improve-codebase-architecture ≈ 806.4K, tdd ≈ 779.3K, …).
  Note: it shows a handful of legacy names (`to-prd`, `to-issues`, `writing-great-skills`) that have since been renamed in the repo —
  the aggregated install counts persist across renames.

> No alternative repo was needed: `mattpocock/skills` resolved on the first API call.

---

## 2. What the repo contains

**Format:** one **`SKILL.md`** per skill (Markdown + YAML frontmatter), the open **Agent Skills** standard format
consumed by Claude Code, Codex, Cursor and other harnesses. Each skill folder also carries an **`agents/openai.yaml`**
(Codex UI metadata + invocation policy). Skills are grouped in **bucket folders** under `skills/`.

**Totals (verified locally from a clone):**
- **37 `SKILL.md` files**, of which **25 are "promoted"** (shipped in the Claude Code plugin):
  - `skills/engineering/` → **18**
  - `skills/productivity/` → **7**
  - `skills/misc/` → **4** (kept, not promoted) · `skills/in-progress/` → **8** (public beta) · `skills/deprecated/` → **0** (empty)
- Plugin manifest `.claude-plugin/plugin.json` (version 1.2.3, `package.json` 1.2.3) lists exactly the 25 promoted skills.

**Bucket semantics** (from `CLAUDE.md` / ADRs):
- `engineering/` + `productivity/` = **promoted**: must appear in top-level README **and** plugin `skills` array.
- `misc/` = "kept around but rarely used, not promoted". `in-progress/` = beta, public on purpose, feedback wanted,
  installable only via `npx skills@latest add mattpocock/skills --skill=<name>`. `deprecated/` = retired skills are deleted, not kept.

**Full inventory (25 promoted, grouped by invocation axis):**

*Engineering — User-invoked (9)*: `ask-matt` (router), `grill-with-docs`, `triage`, `improve-codebase-architecture`,
`setup-matt-pocock-skills` (run-once setup), `to-spec`, `to-tickets`, `implement`, `wayfinder`.

*Engineering — Model-invoked (9)*: `prototype`, `diagnosing-bugs`, `research`, `tdd`, `domain-modeling`,
`codebase-design`, `code-review`, `resolving-merge-conflicts`, `wizard`.

*Productivity — User-invoked (5)*: `grill-me`, `handoff`, `teach`, `to-questionnaire`, `wait-what`.

*Productivity — Model-invoked (2)*: `grilling`, `writing-for-agents`.

*misc (4, not promoted)*: `git-guardrails-claude-code`, `migrate-to-shoehorn`, `scaffold-exercises`, `setup-pre-commit`.

*in-progress (8, beta)*: `loop-me`, `writing-beats`, `writing-fragments`, `writing-shape`, `claude-handoff`,
`setup-ts-deep-modules`, `implement-spec`, `retro`.

**Repo-level docs:** `README.md`, `CHANGELOG.md` (changesets workflow), `CLAUDE.md` (repo self-instructions),
`CONTEXT.md` (the repo's *own* shared-language glossary — models its issue-tracker vocabulary),
`.agents/` (ADRs + invocation/install/writing-docs conventions), `.out-of-scope/` (explicit scope refusals),
`.claude-plugin/` (plugin + marketplace manifests), `docs/<bucket>/<skill>.md` (human-facing pages, published at
`https://aihero.dev/skills-<skill-name>`), `scripts/` (link-skills.sh, list-skills.sh).

---

## 3. His workflow (the core ask)

The workflow is not in prose — it is encoded in **`ask-matt/SKILL.md`**, the "router" skill that maps how the skills
chain into flows. Verbatim framing from `ask-matt`: *"A flow is a path through the skills. Most paths run along one
main flow, and two on-ramps merge onto it."*

### The main flow: idea → ship
1. **`/grill-with-docs`** — interview to sharpen the idea. Stateful: leaves a paper trail in `CONTEXT.md` (shared
   language/glossary) and ADRs (decisions). If there's no working directory, use `/grill-me` (stateless). Both run the
   same **`/grilling`** primitive.
2. **Prototype branch** — if a question needs a runnable answer (state/business logic/UI), detour through
   `/handoff` → `/prototype` → `/handoff` back; prototype is throwaway code kept as a **primary source** on a
   `prototype/<name>` branch.
3. **Multi-session branch?**
   - **Yes** → `/to-spec` (synthesize the thread into a spec, **no re-interview**), then `/to-tickets` (split into
     **tracer-bullet vertical slices**, each declaring its **blocking edges**; local tracker = one file per ticket
     under `.scratch/<feature-slug>/issues/<NN>-<slug>.md` numbered blockers-first; real tracker = native blocking links),
     then **`/implement` per ticket, `/clear`ing the context between tickets**. Each ticket is sized to fit one fresh
     context window.
   - **No** → `/implement` right there, same context window.
   Either way, **`/implement`** drives **`/tdd`** internally (one red→green slice at a time), then closes out with
   **`/code-review`** (two-axis: Standards + Spec) **before committing**.

### On-ramps
- **Incoming bugs/requests piling up** → `/triage` (issue state machine: `needs-triage`, `needs-info`,
  `ready-for-agent`, `ready-for-human`, `wontfix`). Only for issues the user **didn't** create.
- **Something broken** → `/diagnosing-bugs` (refuses to theorize until it has a **tight feedback loop** that already
  goes red on the bug; then fix + regression test; hands off to `/improve-codebase-architecture` when the real finding
  is a missing seam).
- **Huge, foggy effort (greenfield / too big for one session)** → `/wayfinder`: charts a **shared map** of
  **decision tickets** (`wayfinder:map`) on the issue tracker, resolves one ticket per session (types: `research`/AFK,
  `prototype`/HITL, `grilling`/HITL, `task`) — aiming to produce **decisions, not deliverables** — then **hands off**
  into the main flow at `/to-spec` when the map clears.

### Context hygiene / phase boundaries (his explicit methodology)
- Keep grilling→spec→tickets in **one unbroken context window**; don't compact/clear until after `/to-tickets`.
- Each `/implement` starts **fresh** from the ticket (self-contained tickets = disposable contexts).
- The limit is the **"smart zone"** (~150k tokens on state-of-the-art models, his term): if a session approaches it before
  `/to-tickets`, `/compact` at the nearest phase boundary.
- At **phase boundaries** he ranks five options: Continue (rule out first — "primary-source cost"), `/clear`,
  `/handoff` (narrow: new harness/directory/colleague/forked side-task), Subagent, `/compact` (the default at the bottom).

### Why these skills exist — his 4 diagnosed failure modes (README, with cited epigraphs)
1. **"The Agent Didn't Do What I Want"** (misalignment) → **grilling sessions** (`/grill-me`, `/grill-with-docs`).
   Quote: *"No-one knows exactly what they want"* — The Pragmatic Programmer.
2. **"The Agent Is Way Too Verbose"** → build a **shared language** (ubiquitous language, DDD): `CONTEXT.md` glossary +
   ADRs = `grill-with-docs`'s second job. Example quote from README: *BEFORE* "There's a problem when a lesson inside a
   section of a course is made 'real'…" vs *AFTER* "There's a problem with the **materialization cascade**".
   He calls this *"the single coolest technique in this repo."*
3. **"The Code Doesn't Work"** → **feedback loops** (static types, browser access, automated tests) → `/tdd`
   (red-green-refactor, vertical slices) and `/diagnosing-bugs`.
4. **"We Built A Ball Of Mud"** → **caring about design** → `/to-spec` (quiz on modules before spec), `/codebase-design`
   (deep modules: John Ousterhout), `/improve-codebase-architecture` (survey, run every few days).

Design philosophy (README, exact): *"Approaches like GSD, BMAD, and Spec-Kit try to help by owning the process. But while
doing so, they take away your control and make bugs in the process hard to resolve. These skills are designed to be
**small, easy to adapt, and composable**. They work with any model."* TDD is central (red-green-refactor; vertical
**tracer-bullet** slices; anti-patterns: implementation-coupled, tautological, horizontal slicing; test **only at
pre-agreed seams**).

---

## 4. Connection to Superpowers / plan-driven development / TDD

- **No direct reference to `obra/superpowers` (or "obra") anywhere in the repo** — verified by grep across all
  tracked files: **zero matches**.
- **TDD is first-class** (`skills/engineering/tdd`), and the whole flow is **plan-driven**: grill → spec → tickets →
  implement → review, with the "write a spec/plan before code" discipline a through-line.
- The *closest methodological relatives* are named-in-counterpoint: **GSD, BMAD, Spec-Kit** (rejected because they
  "own the process" and make process bugs hard to fix). Other named influences (quoted in README): *The Pragmatic
  Programmer* (Hunt & Thomas), *Domain-Driven Design* (Eric Evans), *Extreme Programming Explained* (Kent Beck),
  *A Philosophy of Software Design* (Ousterhout), plus Feathers' **seam** concept in `codebase-design`.
- If the user was thinking of a Superpowers connection, it is **conceptual, not cited**: same "skills as small
  composable Markdown+frontmatter units that agents invoke before acting" ethos as obra/superpowers, and the same
  grilling/requirements-clarification and test-first instincts — but the repo never names Superpowers. One caveat to
  hold onto: these two ecosystems are independent and use different CLI/tooling (Claude Code plugin + `skills.sh` here).

---

## 5. Notable design decisions & patterns (source-grounded)

**SKILL.md frontmatter / internal structure**
- Frontmatter: `name`, `description`, and for user-invoked skills `disable-model-invocation: true`.
  (e.g. `grill-me`'s whole body is literally: `Call the Skill tool with "grilling"` — a thin orchestrator that delegates
  to the model-invoked `grilling` primitive.)
- **Description convention carries the invocation tax:** user-invoked descriptions are **human-facing** one-liners
  (strip trigger lists); model-invoked descriptions are **model-facing** with rich trigger phrasing
  (`"Use when the user wants…, mentions…, asks for…"`) so auto-invocation fires. Test he gives: *could the model usefully
  reach for this autonomously?* (`.agents/invocation.md`).

**Invocation model (the defining axis)** — `.agents/invocation.md`
- **User-invoked** = orchestrators, reachable only by the human typing `/name`; `disable-model-invocation: true`
  (Claude Code) + `policy.allow_implicit_invocation: false` in `agents/openai.yaml` (Codex). A user-invoked skill can
  **never** call another user-invoked skill; it may call model-invoked ones.
- **Model-invoked** = the reusable discipline; model- or user-reachable; default (omit the flag/policy block).
- **Cross-skill dependencies must be explicit tool calls**, not prose: *"Call the Skill tool with `grilling`"* — no
  leading `/` (harness-neutral), and *"Call the Skill tool twice, for `grilling` and `domain-modeling`"* when two are
  needed (one skill per call). Backed by changesets `skill-tool-invocation-terminology.md` and
  `user-invoked-skill-invocation.md` (PR #878/#453 bugfixes: naming a skill in prose doesn't reliably load it; and
  user-invoked skills can't be reached via the Skill tool at all — phrase those as "tell the human to run `/setup-...`").

**Setup & dependencies**
- `/setup-matt-pocock-skills` seeds per-repo config **once** (`.agents/adr/0001`): issue tracker (GitHub default;
  GitLab; local markdown under `.scratch/`; or "other" freeform), triage label vocabulary, and domain-doc layout
  (single-context `CONTEXT.md`+`docs/adr/` vs multi-context `CONTEXT-MAP.md` for monorepos). Writes
  `docs/agents/{issue-tracker,domain,triage-labels}.md` + an `## Agent skills` block in `CLAUDE.md` (never both
  CLAUDE.md and AGENTS.md).
- **Hard- vs soft-dependency** skills (ADR-0001): `to-tickets`, `to-spec`, `triage` = hard (must tell user to run
  setup); `tdd`, `diagnosing-bugs`, `improve-codebase-architecture` = soft (reference glossary/ADRs in prose only).

**Distribution (ADR-0002, `install-block.md`)**
- Two exclusive routes: **Claude Code plugin** (`claude plugins install mattpocock-skills`, in the *official* Claude
  marketplace since 2026-08-05, auto-update) = managed read-only bundle; **skills.sh** (`npx skills@latest add
  mattpocock/skills`) = copies editable files, works for Codex/other agents. "Pick one: installing both leaves you with
  every skill twice."
- **Native Codex plugin deferred** because Codex's manifest accepts only a single path + drops symlinks on install, so it
  can't express this repo's curated bucket subset — documented reasoning with tested-and-rejected alternatives.

**Other notable conventions**
- **`AGENTS.md` is a symlink to `CLAUDE.md`** (so Codex reads the same repo instructions).
- **Buckets + strict sync rules:** promoted buckets must appear in README + plugin; non-promoted must not.
- **"No em-dashes anywhere in this repo's prose"** (CLAUDE.md rule, enforced via changesets `remove-em-dashes-repo-wide.md`,
  `grilling-remove-em-dashes.md`) — a notable, fanatical anti-em-dash convention.
- **Shared language as a first-class artifact:** `CONTEXT.md` glossary (ubiquitous language), ADRs for decisions;
  `domain-modeling` = the active build/sharpen discipline; `wait-what` = reactive re-explainer using `CONTEXT.md` vocabulary.
- **Code review = two parallel axes** (Standards incl. a fixed **Fowler code-smell baseline**; Spec), run as **parallel
  sub-agents** so contexts don't pollute each other; reports shown separately, deliberately not merged/reranked.
- **Diagnosing-bugs = 6 gated phases** (Feedback loop → Reproduce+minimise → 3–5 ranked falsifiable hypotheses →
  Instrument → Fix+regression test → Cleanup), with a **Redact** section (secrets → `<REDACTED>`) and *"No red-capable
  command, no Phase 2."*
- **`writing-for-agents`** is the meta-skill defining how SKILL.md/AGENTS.md are written; docs pages use a fixed four-/
  five-section template (*What it does · When to reach for it · Common questions · It's working if · Where it fits*).
- **`.out-of-scope/` directory** documents deliberate refusals with reasons and linked issues: mainstream issue
  trackers only; **no hard cap on grilling questions** (issue #44 "Codex just asked me 200 questions"); no verify mode
  for `setup-matt-pocock-skills` (issue #106).
- Repo itself dogfoods: uses `CONTEXT.md` + glossary, ADRs, changesets/changelog, its own `ask-matt` routing.

---

## 6. Remaining unknowns / caveats

1. **Star count timing:** ~238.5k is the API value at fetch time (banner page showed 238,494 the same day — consistent;
   this looks like an unusually viral repo, but I report what the API returned).
2. **Name drift on skills.sh:** published install counts reference legacy skill names (`to-prd`, `to-issues`,
   `writing-great-skills`) superseded in the repo by `to-spec`, `to-tickets`, `writing-for-agents`; the exact mapping
   of which rename produced which is not documented per skill in the repo (CHANGELOG.md was not fully mined for the full
   rename history, only the head was read).
3. The `aihero.dev` marketing pages and newsletter claims (e.g. "learn how I actually engineer") were not exhaustively
   scraped; only the `/skills` and `skills.sh` pages were fetched.
4. `permissionless.md`, the total-typescript shop or `course-video-manager` (his CONTEXT.md example) were not part of
   this repo deep-dive; if the design doc needs his *in-repo* `CONTEXT.md` example content, fetch
   `mattpocock/course-video-manager/CONTEXT.md`.
5. **No Superpowers/obra reference exists** — if the design doc expected one, treat that as a confirmed negative finding.

---

### Fetch log (all HTTP 200 unless noted)
- `api.github.com/repos/mattpocock/skills` — 200 (metadata, stars)
- `api.github.com/users/mattpocock/repos?per_page=100&sort=updated` — 200 (repo discovery)
- `api.github.com/repos/mattpocock/skills/git/trees/main?recursive=1` — 200 (full file tree, 257 entries)
- `raw.githubusercontent.com/mattpocock/skills/main/README.md` — 200
- `https://github.com/mattpocock/skills` (git clone, depth 1, HEAD 6654f6b) — success
- `https://aihero.dev/skills` — 200 · `https://skills.sh/mattpocock/skills` — 200
