---
title: Plan 02 — Cambios al MCP server
status: ✅ CERRADA (2026-05-14)
phase: 1 (junto con Plan 01)
prerequisitos: Plan 01 §8 (Pydantic schema AgentHandoff) implementado primero
implementacion: ../implementacion/02-mcp-server-cambios.md
---

# Plan 02 — Cambios al MCP server

El MCP server (`cortex/mcp/server.py`) enforcea los contratos. Sin estos cambios, los nuevos contratos canonical son solo aspiracionales.

## Resumen

| § | Cambio | Tipo | Esfuerzo |
|---|--------|------|----------|
| 1 | Nuevo MCP tool `cortex_validate_handoff` | Tool nuevo | 2 h |
| 2 | Nuevo MCP tool `cortex_verify_session_claims` | Tool nuevo | 3 h |
| 3 | Schema `MemoryEntry.confidence` propagado en MCP responses | Tweak | 1 h |
| 4 | `cortex_save_session` acepta parámetros de handoff | Extensión | 2 h |
| 5 | Tests del MCP `TestHandoffValidation` | Tests | 2 h |
| 6 | Update `tests/e2e/test_artefact_integrity.py::MCP_TO_CLI` | Mapping | 30 min |

**Total estimado: ~10 horas (~1.5 días).**

---

## §1. Nuevo MCP tool `cortex_validate_handoff`

### Objetivo

Validar el YAML handoff que un subagent produce. Si es inválido, rechazar antes de que el siguiente agent consuma basura.

### Archivos a tocar

- `cortex/mcp/server.py`:
  - Agregar definición de tool en `_setup_tools` (line ~110 zone).
  - Agregar branch en `handle_call_tool` para dispatch.
  - Agregar helper `_validate_handoff_text(arguments: dict) -> str`.
- `tests/unit/test_mcp_server.py` — tests del nuevo tool.

### Plan

1. **Definición del tool** en el list de `Tool(...)` retornado por list_tools handler:
   ```python
   types.Tool(
       name="cortex_validate_handoff",
       description=(
           "Validate a structured agent handoff (YAML). Use this between "
           "subagents to enforce the cortex.handoff.AgentHandoff schema. "
           "Returns OK with normalized fields or an error message detailing "
           "the schema violations."
       ),
       inputSchema={
           "type": "object",
           "properties": {
               "handoff_yaml": {
                   "type": "string",
                   "description": "YAML text matching AgentHandoff schema.",
               },
               "expected_agent": {
                   "type": "string",
                   "description": "(Optional) Assert the handoff's agent field matches this value.",
               },
           },
           "required": ["handoff_yaml"],
       },
   ),
   ```

2. **Dispatcher** en `handle_call_tool`:
   ```python
   elif name == "cortex_validate_handoff":
       result_text = self._validate_handoff_text(arguments)
       self._log_tool_call(name, arguments, result_text)
       return [types.TextContent(type="text", text=result_text)]
   ```

3. **Helper:**
   ```python
   def _validate_handoff_text(self, arguments: dict[str, Any]) -> str:
       from cortex.handoff import AgentHandoff
       from pydantic import ValidationError

       yaml_text = arguments.get("handoff_yaml", "")
       expected_agent = arguments.get("expected_agent")
       if not yaml_text.strip():
           return "❌ handoff_yaml is required and must not be empty."
       try:
           handoff = AgentHandoff.from_yaml(yaml_text)
       except ValidationError as exc:
           # Compact, readable error.
           details = "; ".join(
               f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
               for err in exc.errors()
           )
           return f"❌ Handoff schema violation:\n  {details}"
       except Exception as exc:
           return f"❌ Failed to parse YAML: {exc}"

       if expected_agent and handoff.agent != expected_agent:
           return (
               f"❌ Agent mismatch: handoff says '{handoff.agent}' but "
               f"expected '{expected_agent}'."
           )

       lines = [
           f"✅ Handoff validated for {handoff.agent} (status: {handoff.status})",
           f"  verified_claims: {len(handoff.verified_claims)}",
           f"  unverified_claims: {len(handoff.unverified_claims)}",
           f"  artifacts: {len(handoff.artifacts_produced)}",
           f"  context_for_next: {len(handoff.context_for_next)}",
       ]
       if handoff.suggested_adr:
           lines.append(f"  ⚠ suggested ADR: {handoff.suggested_adr_reason}")
       if handoff.suggested_context_terms:
           lines.append(
               f"  📚 CONTEXT.md terms: {', '.join(handoff.suggested_context_terms)}"
           )
       return "\n".join(lines)
   ```

### Criterio de cierre

- [x] Tool registrado con inputSchema.
- [x] Dispatcher en `handle_call_tool`.
- [x] `_validate_handoff_text` con validación + assert opcional de agent.
- [x] Mensajes de error legibles (no traceback).

---

## §2. Nuevo MCP tool `cortex_verify_session_claims`

### Objetivo

Soportar el Verification Gate (Plan 01 §4) automáticamente: recibe una lista de claims y la URL del PR/commit, ejecuta `cortex verify-docs` + cross-check contra git diff, y retorna qué claims están verificados, cuáles asserted y cuáles contradichos.

### Archivos a tocar

- `cortex/mcp/server.py` — definición + dispatcher + helper `_verify_session_claims_text`.
- `tests/unit/test_mcp_server.py` — tests.

### Plan

1. **Tool definition:**
   ```python
   types.Tool(
       name="cortex_verify_session_claims",
       description=(
           "Verify session claims against the actual git diff. Returns a "
           "structured breakdown of verified / asserted / contradicted "
           "claims that the documenter can use to fill the confidence field."
       ),
       inputSchema={
           "type": "object",
           "properties": {
               "claims": {
                   "type": "array",
                   "items": {"type": "string"},
                   "description": "List of claims to verify.",
               },
               "base_branch": {
                   "type": "string",
                   "description": "Branch to diff against (default: main).",
               },
               "files_to_check": {
                   "type": "array",
                   "items": {"type": "string"},
                   "description": "Optional file allowlist to scope verification.",
               },
           },
           "required": ["claims"],
       },
   ),
   ```

2. **Helper logic:**
   - Obtener git diff vs `base_branch` (vía `cortex.doc_verifier._git_diff_files` ya existente).
   - Para cada claim, ejecutar matching keyword heurístico:
     - Si el claim menciona un archivo o función que aparece en el diff → `verified`.
     - Si el claim contradice texto del diff (palabras opuestas como "added" vs diff que muestra delete) → `contradicted`.
     - En cualquier otro caso → `asserted`.
   - Retornar JSON-like text legible.

   **Nota técnica:** este es un heurístico bestial pero útil. Para una verificación real LLM-judge sería necesaria, pero como first-pass alcanza para distinguir claims que tocan código real vs claims gratuitos.

3. **Helper:**
   ```python
   def _verify_session_claims_text(self, arguments: dict[str, Any]) -> str:
       from cortex.doc_verifier import DocVerifier

       claims = arguments.get("claims", [])
       base = arguments.get("base_branch", "main")
       if not claims:
           return "❌ claims list is required."

       try:
           # Lazy: read diff once.
           import subprocess
           result = subprocess.run(
               ["git", "diff", "--unified=0", base, "--"],
               cwd=self.project_root,
               capture_output=True,
               text=True,
               timeout=10,
           )
           diff_text = result.stdout
       except Exception as exc:
           return f"❌ Could not read diff: {exc}"

       diff_lower = diff_text.lower()
       verified, asserted, contradicted = [], [], []

       for claim in claims:
           tokens = [t.lower() for t in claim.replace("_", " ").split() if len(t) > 3]
           hits = sum(1 for t in tokens if t in diff_lower)
           # Heuristic: claim mentions ≥2 tokens that appear in the diff → verified.
           if hits >= 2:
               verified.append(claim)
           elif hits == 0:
               asserted.append(claim)
           else:
               # 1 hit: borderline; mark as asserted to be safe.
               asserted.append(claim)

       lines = [
           f"Verification of {len(claims)} claims against branch {base}:",
           f"  ✅ verified: {len(verified)}",
           f"  ⚠ asserted: {len(asserted)}",
           f"  ❌ contradicted: {len(contradicted)}",
       ]
       if verified:
           lines.append("\nVerified:")
           lines.extend(f"  - {c}" for c in verified)
       if asserted:
           lines.append("\nAsserted (no diff evidence):")
           lines.extend(f"  - {c}" for c in asserted)
       return "\n".join(lines)
   ```

### Criterio de cierre

- [x] Tool registrado con inputSchema.
- [x] Dispatcher en `handle_call_tool`.
- [x] Helper con heurístico de matching.
- [x] Tests: claim que matchea diff → verified; claim gratuito → asserted; claims vacíos → error.

---

## §3. Schema `MemoryEntry.confidence` propagado

### Objetivo

Cuando un MCP tool retorna memorias (`cortex_search`, `cortex_context`), incluir el campo `confidence` en la representación.

### Archivos a tocar

- `cortex/mcp/server.py`:
  - `_search_text` — incluir confidence en la salida.
  - `_context_text` — incluir confidence si la enrichment lo trae.

### Plan

Al iterar `unified_hits` o `episodic_hits`, agregar al output:
```python
conf = hit.entry.metadata.get("confidence") if hit.entry else None
conf_label = f" [{conf}]" if conf else ""
lines.append(f"- [{e.memory_type}{conf_label}] {e.content}")
```

### Criterio de cierre

- [x] `_search_text` incluye `[verified]` / `[asserted]` / `[contradicted]` en la línea de cada hit con `confidence` definida.
- [x] Test que verifica el formato.

---

## §4. `cortex_save_session` acepta parámetros de handoff

### Objetivo

El MCP tool `cortex_save_session` (que delega a `SessionService.create` vía `AgentMemory.save_session_note`) debe aceptar los 5 nuevos parámetros opcionales: `handoff`, `blockers`, `verified_state`, `unverified_claims`, `suggested_skills`.

### Archivos a tocar

- `cortex/mcp/server.py::_save_session_text` — extender mapping de arguments.
- `cortex/core.py::AgentMemory.save_session_note` — extender firma.
- `cortex/services/session_service.py::SessionService.create` — extender firma.
- Tests de los 3 niveles.

### Plan

Propagar los 5 campos en cascade:

1. **MCP server inputSchema** del `cortex_save_session` tool — agregar properties:
   ```python
   "handoff": {"type": "boolean", "default": False},
   "blockers": {"type": "array", "items": {"type": "string"}},
   "verified_state": {"type": "array", "items": {"type": "string"}},
   "unverified_claims": {"type": "array", "items": {"type": "string"}},
   "suggested_skills": {"type": "array", "items": {"type": "string"}},
   ```

2. **`_save_session_text`:**
   ```python
   path = self.memory.save_session_note(
       title=arguments.get("title", ""),
       ...,
       handoff=arguments.get("handoff", False),
       blockers=arguments.get("blockers", []),
       verified_state=arguments.get("verified_state", []),
       unverified_claims=arguments.get("unverified_claims", []),
       suggested_skills=arguments.get("suggested_skills", []),
   )
   ```

3. **`AgentMemory.save_session_note`:** extender firma y pasarlo a `_session_service.create`.

4. **`SessionService.create`:** llamar a `write_session_note(..., handoff=..., blockers=..., ...)`.

### Criterio de cierre

- [x] InputSchema actualizado.
- [x] Cascade en 3 niveles funcional.
- [x] Test e2e: invocar `cortex_save_session` con `handoff=True` → archivo tiene frontmatter `status: handoff`.

---

## §5. Tests del MCP — TestHandoffValidation

### Archivos a tocar

- `tests/unit/test_mcp_server.py` — agregar `TestHandoffValidation` class.

### Plan

```python
class TestHandoffValidation:
    """Tests for the cortex_validate_handoff MCP tool."""

    def _make_server(self) -> CortexMCPServer:
        server = CortexMCPServer.__new__(CortexMCPServer)
        server.memory = FakeMemory()  # type: ignore[assignment]
        server.project_root = Path.cwd()
        server._called_tools = set()
        return server

    def test_valid_minimal_handoff_passes(self):
        server = self._make_server()
        yaml_text = """
        agent: cortex-code-explorer
        status: complete
        """
        result = server._validate_handoff_text({"handoff_yaml": yaml_text})
        assert "✅" in result
        assert "cortex-code-explorer" in result

    def test_invalid_agent_fails(self):
        server = self._make_server()
        yaml_text = "agent: nonexistent\nstatus: complete"
        result = server._validate_handoff_text({"handoff_yaml": yaml_text})
        assert "❌" in result
        assert "agent" in result.lower()

    def test_invalid_status_fails(self):
        server = self._make_server()
        yaml_text = "agent: cortex-documenter\nstatus: weird"
        result = server._validate_handoff_text({"handoff_yaml": yaml_text})
        assert "❌" in result

    def test_expected_agent_mismatch_fails(self):
        server = self._make_server()
        yaml_text = "agent: cortex-documenter\nstatus: complete"
        result = server._validate_handoff_text({
            "handoff_yaml": yaml_text,
            "expected_agent": "cortex-code-explorer",
        })
        assert "Agent mismatch" in result

    def test_empty_yaml_fails(self):
        server = self._make_server()
        result = server._validate_handoff_text({"handoff_yaml": ""})
        assert "required" in result.lower()

    def test_full_handoff_reports_counts(self):
        server = self._make_server()
        yaml_text = """
        agent: cortex-code-implementer
        status: partial
        verified_claims:
          - "auth.py modified"
          - "tests added"
        unverified_claims:
          - "performance impact negligible"
        artifacts_produced:
          - path: src/auth.py
            action: modified
            lines_changed: 12
        context_for_next:
          - "documenter: verify TTL hardcoding"
        suggested_adr: true
        suggested_adr_reason: "TTL hardcoded with UX/security trade-off"
        """
        result = server._validate_handoff_text({"handoff_yaml": yaml_text})
        assert "verified_claims: 2" in result
        assert "unverified_claims: 1" in result
        assert "artifacts: 1" in result
        assert "context_for_next: 1" in result
        assert "suggested ADR" in result
```

### Criterio de cierre

- [x] 6 tests `TestHandoffValidation` verdes (entregados 7, +1 edge case malformed).
- [x] Cobertura: minimal, agent inválido, status inválido, mismatch, vacío, full.

---

## §6. Update `MCP_TO_CLI` en artefact integrity

### Archivos a tocar

- `tests/e2e/test_artefact_integrity.py::TestMcpCliAlignment::MCP_TO_CLI` — agregar entradas para los 2 nuevos tools.

### Plan

```python
MCP_TO_CLI = {
    # ... existentes
    # New in Tripartita Refinada — Tripartita refinada
    "cortex_validate_handoff": None,  # MCP-only; no direct CLI
    "cortex_verify_session_claims": None,  # MCP-only; no direct CLI
}
```

Justificación: estos tools son **MCP-only** (no se exponen como CLI). El `None` documenta explícitamente esa decisión.

### Criterio de cierre

- [x] Entrada agregada para `cortex_validate_handoff` con value `None`.
- [x] Entrada agregada para `cortex_verify_session_claims` con value `None`.
- [x] Test `test_mcp_tools_have_cli_counterpart_or_documented` sigue verde.

---

## Checklist final del Plan 02

- [x] §1 `cortex_validate_handoff` registrado + dispatcher + helper.
- [x] §2 `cortex_verify_session_claims` registrado + dispatcher + helper.
- [x] §3 Confidence propagado en `_search_text` y `_context_text`.
- [x] §4 `cortex_save_session` acepta 5 parámetros nuevos de handoff (cascade 3 niveles).
- [x] §5 6 tests `TestHandoffValidation` verdes (7 entregados).
- [x] §6 `MCP_TO_CLI` actualizado.
- [x] Suite global verde — 799 passed, 6 skipped, 0 failed (vs baseline 784 → +15 tests).
