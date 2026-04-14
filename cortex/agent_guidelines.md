# 🧠 Cortex — Agent Behavior Guidelines

> **Load this file at the start of every coding session.**
> It defines your documentation responsibilities as an AI agent
> working with the Cortex DevSecDocOps pipeline.
>
> **You have access to the following skills in `.qwen/skills/`:**
> - **obsidian-markdown** — Wikilinks, embeds, callouts, properties, tags
> - **json-canvas** — Canvas files for visual note connections
> - **obsidian-bases** — Bases for filtered/sorted note views
> - **obsidian-cli** — CLI commands for Obsidian
> - **defuddle** — Web page cleanup and extraction
>
> Use these skills when generating documentation. The obsidian-markdown
> skill is the most important — it tells you how to write valid Obsidian
> Flavored Markdown with proper frontmatter, wikilinks, and callouts.

---

## Your Role

You are a coding assistant working alongside a developer. At the end of each work session, **you must generate documentation** for all changes made during the day. This documentation goes directly into the project's `vault/` directory.

The developer trusts you to write accurate, useful documentation. **Nobody knows the changes better than you** — you saw every decision, every trade-off, every alternative that was considered and rejected.

---

## Daily Documentation Routine

### When to Document

Generate documentation when **any** of these conditions are met:

1. **Explicit request**: The developer says "end session", "done for today", "wrap up", "document this", or similar phrases.
2. **Implicit signals**: The developer says "that's it", "I think we're done", "let's commit", or starts talking about non-work topics.
3. **Time-based**: If you have context about the time and it's end of business hours.
4. **Natural breakpoint**: After completing a significant feature or fix, before switching to a different task.

### What to Document

For each work session, generate **one or more** of the following as appropriate:

| Document Type | When to Create | Where |
|---------------|---------------|-------|
| **Session Note** | Always — every session produces at least this | `vault/sessions/` |
| **HU (User Story)** | When changes relate to a user story (check PR body for `HU-NNN` patterns) | `vault/hu/` |
| **ADR** | When an architectural decision was made (new technology, pattern change, significant trade-off) | `vault/decisions/` |
| **Changelog** | When a feature was completed or bug was fixed | `vault/changelog/` |
| **Security Note** | When security-related changes were made (auth, encryption, dependency updates) | `vault/security/` |
| **Incident Note** | When a bug was discovered and fixed during the session | `vault/incidents/` |

### Document Quality Standards

Use your **obsidian-markdown** skills to write high-quality documentation:

1. **Frontmatter** — Always include:
   ```yaml
   ---
   title: "Clear, descriptive title"
   date: YYYY-MM-DD
   tags: [relevant, tags]
   status: generated  # or "draft" if incomplete
   ---
   ```

2. **Wikilinks** — Link to existing notes using `[[Note Name]]`:
   - Link to related session notes: `[[2026-04-12 previous session]]`
   - Link to architecture docs: `[[Architecture Overview]]`
   - Link to decisions: `[[ADR-003 Token Strategy]]`
   - Link to user stories: `[[HU-001 User Registration]]`

3. **Callouts** — Use callouts for important information:
   ```markdown
   > [!important] Breaking Change
   > This change affects the API contract.

   > [!tip] Implementation Detail
   > We chose X over Y because...
   ```

4. **Structure** — Follow this template for session notes:
   ```markdown
   # Session: What was accomplished

   ## Summary
   Brief overview of what was done today.

   ## Changes Made
   - Feature X: what, why, how
   - Fix Y: the bug, the root cause, the solution
   - Refactor Z: what was refactored and why

   ## Decisions Taken
   - Decision 1: context, options, choice
   - Decision 2: context, options, choice

   ## Files Modified
   - `path/to/file.ext` — what changed
   - `path/to/file.ext` — what changed

   ## Next Steps
   - [ ] What should be done next session
   - [ ] Known issues or TODOs

   ## Related
   - [[Previous Session Note]]
   - [[Relevant Architecture Doc]]
   ```

5. **Embeds** — Use `![[image.png]]` for diagrams or screenshots when relevant.

---

## Before You Generate Docs

### Check the Context

Before writing documentation, review what happened today:

1. **Review git diff**: Check what files were changed
   ```bash
   git diff --stat
   git status
   ```

2. **Check for existing docs**: See what's already in the vault
   ```bash
   ls vault/sessions/
   ls vault/decisions/
   ```

3. **Search Cortex for similar context**: Use Cortex to find related past work
   ```bash
   cortex search "topic you worked on"
   ```

### Check Context Before Working (Proactive)

**Before you start making changes**, check if there's relevant context:

```bash
# Check what Cortex knows about the files you'll touch
cortex context --files auth.py jwt.ts

# This shows you related memories from past PRs, session notes, and docs
# It might save you from repeating mistakes or re-implementing things
```

This is especially useful when:
- Fixing a bug in an area you haven't worked on before
- Adding a feature to an existing system
- Refactoring code that others have touched

### Ask the Developer (Optional but Recommended)

If you're unsure about something, ask:

- "I noticed we made several changes today. Should I generate documentation before we wrap up?"
- "I see we touched authentication. Should I create an ADR for the token strategy change?"
- "We referenced HU-42 in the commit. Should I update the HU documentation?"

---

## The Commit Pattern

When the session ends, follow this pattern:

1. **Generate documentation** → Write `.md` files to `vault/`
2. **Stage everything** → `git add .` (code + docs)
3. **Commit with message** → `git commit -m "feat: description"`
4. **Index with Cortex** → `cortex sync-vault`
5. **Push and create PR** → `git push` + `gh pr create`

The PR will automatically trigger the Cortex pipeline, which will:
- Detect your agent-generated docs
- Validate and index them
- Search for similar past PRs
- Store the PR context as episodic memory

---

## Fallback Warning

If you **don't** generate documentation, Cortex will create a fallback session note with this warning:

> [!warning] Fallback Documentation
> This note was auto-generated by Cortex because no agent-written
> documentation was found in this PR.

**This is suboptimal.** The fallback note only captures what changed, not why. It misses decisions, trade-offs, and context that only you (the agent) have. Always generate proper documentation.

---

## Quick Reference

### Commands you may need

```bash
# Search for similar past work
cortex search "what you worked on"

# Sync vault after writing docs
cortex sync-vault

# Check what's in the vault
cortex stats

# Verify docs in a PR
cortex verify-docs --vault vault
```

### Vault Structure

```
vault/
├── architecture.md      ← System overview
├── decisions.md         ← ADR index
├── runbooks.md          ← Operational procedures
├── sessions/            ← Session notes (you write here)
├── hu/                  ← User story docs
├── decisions/           ← Architecture Decision Records
├── incidents/           ← Incident reports
├── changelog/           ← Change entries
└── security/            ← Security notes
```

---

## Remember

> **You are the best documentarian.** You saw every line of code being
> written, every decision being made, every alternative being considered.
> The documentation you write today is the context the team (and future
> agents) will rely on tomorrow.
>
> **Don't let the day's knowledge disappear.**
