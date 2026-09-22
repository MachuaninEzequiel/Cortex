# cortex/session/proposal.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/proposal.py` (183 líneas).
- **Módulo Python:** `cortex.session.proposal`.
- **Docstring del módulo:** cortex.session.proposal — Interactive proposal primitive (Phase 09.A+).
- **Clases definidas:**
  - `Alternative` (BaseModel)
    - One option presented to the user inside a :class:`Proposal`.
    - Métodos internos: `_validate_id`
  - `Proposal` (BaseModel)
    - A structured proposal awaiting user confirmation.
    - Métodos internos: `_strip_empty_risks`, `_validate_recommendation`
- **Funciones de módulo:**
  - `format_proposal_card(proposal)` — Render *proposal* as a Markdown card suitable for an MCP tool result.
- **Constantes / símbolos de módulo:** `ALTERNATIVE_ID_PATTERN`, `__all__`

## Para qué sirve

cortex.session.proposal — Interactive proposal primitive (Phase 09.A+).

Models the artifact emitted by ``cortex-sync`` (and any future skill that
needs explicit user confirmation) when ``proposal_mode`` is ``optional``
or ``required``. The proposal is rendered as a Markdown "card" that the
MCP client surfaces to the user as a structured tool result, **forcing**
visual emphasis that a plain assistant message cannot guarantee.

Why this exists
---------------
Phase 09.A originally instructed the agent to emit the proposal as a
plain Markdown message and pause its turn. In practice that was fragile:
the LLM may forget to stop, the IDE may collapse the message under the
last MCP indicator, and there is no server-side audit trail.

By forcing the agent to call ``cortex_emit_proposal``, the proposal:
    * Is rendered consistently across IDEs (the tool result IS the card).
    * Is logged in ``mcp_calls_<timestamp>.log`` for audit.
    * Anchors the timestamp used to enforce the
      ``required`` → ``cortex_create_spec`` gate (see
      :class:`cortex.mcp.server.CortexMCPServer._create_spec_text`).

Model contract
--------------
- Exactly one alternative is the *recommendation*; the rest carry a
  ``rejected_reason`` explaining why they were not chosen.
- Alternative ids are short tokens (``A``, ``B``, ``C``…) so the user
  can reference them in plain language.
- ``risks`` is optional but encouraged — it surfaces the assumptions the
  user is implicitly accepting by saying ``ok``.

This module is **pure**: it does not touch the filesystem, MCP server, or
any session storage. Persistence (if ever needed) lives elsewhere; see
``docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`` §12.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `re`, `__future__`, `pydantic`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 183.
Docstrings de símbolos públicos:
- `format_proposal_card`: Render *proposal* as a Markdown card suitable for an MCP tool result.

---
Fuente: código de `cortex/session/proposal.py` (AST + grafo de imports internos). No se usó documentación previa.
