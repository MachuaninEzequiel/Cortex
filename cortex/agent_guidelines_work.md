# Cortex Work Mode (Deprecated)

`cortex-work` was replaced by `cortex-SDDwork` in Release 2 and then by the
**Pluggable Middle** architecture in Fase 02.

The current flow has three modes:

1. `cortex-sync` — pre-flight, context recovery, spec persistence (with
   verification hooks). Opens the Session.
2. **Middle (one of):**
   - `cortex-SDDwork` (Managed) — emits checkpoints, no YAML.
   - User's own agent / IDE (Observed) — optionally emits checkpoints via
     IDE hooks (Fase 03).
   - Anything (BYO) — no checkpoints; the documenter reconstructs from diff.
3. `cortex finish-session` — closes the Session via the documenter.

See `cortex agent-guidelines` (which renders `cortex/agent_guidelines.md`)
for the authoritative current rules.

External memory tools remain forbidden in all cases.
