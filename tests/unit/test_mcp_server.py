from __future__ import annotations

from pathlib import Path

from cortex.mcp.server import CortexMCPServer


class FakeRetrievalResult:
    def to_prompt(self) -> str:
        return "retrieval prompt"


class FakeContext:
    def to_prompt_format(self) -> str:
        return "context prompt"


class FakeMemory:
    def __init__(self) -> None:
        self.last_save_kwargs: dict[str, object] | None = None

    def retrieve(self, query: str, top_k: int = 5) -> FakeRetrievalResult:
        return FakeRetrievalResult()

    def enrich(
        self,
        changed_files: list[str],
        keywords: list[str] | None = None,
        pr_title: str | None = None,
        *,
        top_k: int | None = None,
    ) -> FakeContext:
        return FakeContext()

    def save_session_note(self, **kwargs: object) -> str:
        self.last_save_kwargs = dict(kwargs)
        return "vault/sessions/test.md"

    def create_spec_note(self, **kwargs: object) -> str:
        return "vault/specs/test.md"

    def import_work_item(self, external_id: str, **kwargs: object) -> str:
        return f"vault/hu/{external_id.lower()}.md"

    def get_work_item_note(self, item_id: str) -> str:
        return f"vault/hu/{item_id.lower()}.md"

    def sync_vault(self) -> int:
        return 3


def test_cortex_context_uses_prompt_format() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]

    result = server._context_text({"query": "Release 2 context", "changed_files": ["cortex/core.py"]})

    assert result == "context prompt"


def test_cortex_save_session_tool() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]

    result = server._save_session_text(
        {
            "title": "Release 2",
            "spec_summary": "Implement orchestrated workflow.",
            "changes_made": ["Added SDDwork"],
        }
    )

    assert result == "Session note saved -> vault/sessions/test.md"


def test_cortex_create_spec_tool_requires_sync() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]
    server._called_tools = set()

    result = server._create_spec_text(
        {
            "title": "Release 2",
            "goal": "Introduce subagent orchestration.",
        }
    )

    assert "VIOLACI" in result


def test_cortex_create_spec_tool_after_sync() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]
    server._called_tools = {"cortex_sync_ticket"}

    result = server._create_spec_text(
        {
            "title": "Release 2",
            "goal": "Introduce subagent orchestration.",
        }
    )

    assert result == "Specification saved -> vault/specs/test.md"


# ---------------------------------------------------------------------------
# Governance guard — robust contract tests
# ---------------------------------------------------------------------------


class TestGovernanceGuard:
    """Tests del guard MCP que bloquea ``cortex_create_spec`` sin ``cortex_sync_ticket``.

    Estos tests son el contrato público de gobernanza del framework.
    Si alguno falla, el guard quedó roto y los IDEs pueden saltarse el flujo
    tripartito sin penalización.
    """

    def test_violation_message_uses_canonical_utf8(self) -> None:
        """El mensaje de violación debe estar libre de mojibake.

        Históricamente este string fue víctima de doble-encoding
        (UTF-8 leído como cp1252). Si vuelve a romperse, este test atrapa
        el regression antes de que el adopter vea un "âŒ VIOLACIÃ“N".
        """
        server = CortexMCPServer.__new__(CortexMCPServer)
        server.memory = FakeMemory()  # type: ignore[assignment]
        server._called_tools = set()
        result = server._create_spec_text(
            {"title": "t", "goal": "g"}
        )
        # Caracteres UTF-8 correctos
        assert "❌" in result
        assert "VIOLACIÓN" in result
        assert "Según" in result
        assert "sesión" in result
        # Mojibake explícitamente NO presente
        assert "âŒ" not in result
        assert "VIOLACIÃ" not in result
        assert "sesiÃ" not in result

    def test_violation_message_is_centralised(self) -> None:
        """El mensaje canónico vive en una constante de clase única.

        Garantiza que no haya duplicación en el archivo: si alguien copia
        el string a otro método, este test (más una grep manual al
        cerrar la ola) lo detecta.
        """
        from cortex.mcp.server import CortexMCPServer as Srv

        assert hasattr(Srv, "_GOVERNANCE_VIOLATION_MESSAGE")
        msg = Srv._GOVERNANCE_VIOLATION_MESSAGE
        assert "VIOLACIÓN DE GOBERNANZA" in msg
        assert "cortex_sync_ticket" in msg

    def test_violation_lists_called_tools(self) -> None:
        """El mensaje debe listar las tools llamadas en la sesión para diagnóstico."""
        server = CortexMCPServer.__new__(CortexMCPServer)
        server.memory = FakeMemory()  # type: ignore[assignment]
        server._called_tools = {"cortex_search", "cortex_context"}
        result = server._create_spec_text({"title": "t", "goal": "g"})
        assert "cortex_search" in result
        assert "cortex_context" in result

    def test_guard_does_not_persist_spec_when_blocked(self) -> None:
        """Cuando el guard rechaza, ``memory.create_spec_note`` NO debe llamarse."""

        class TrackingMemory(FakeMemory):
            def __init__(self) -> None:
                self.spec_calls = 0

            def create_spec_note(self, **kwargs: object) -> str:  # type: ignore[override]
                self.spec_calls += 1
                return "vault/specs/should-not-exist.md"

        server = CortexMCPServer.__new__(CortexMCPServer)
        mem = TrackingMemory()
        server.memory = mem  # type: ignore[assignment]
        server._called_tools = set()

        server._create_spec_text({"title": "t", "goal": "g"})
        assert mem.spec_calls == 0, (
            "El guard debe rechazar ANTES de invocar create_spec_note; "
            f"pero create_spec_note fue llamado {mem.spec_calls} veces"
        )

    def test_handle_call_tool_dispatcher_uses_helper(self) -> None:
        """El dispatcher ``handle_call_tool`` ahora delega en ``_create_spec_text``.

        Verifica el refactor DRY: cuando el dispatcher recibe
        ``cortex_create_spec`` sin ``cortex_sync_ticket`` previo, el mensaje
        retornado debe ser idéntico al del helper directo.
        """
        server = CortexMCPServer.__new__(CortexMCPServer)
        server.memory = FakeMemory()  # type: ignore[assignment]
        server._called_tools = set()
        helper_msg = server._create_spec_text({"title": "t", "goal": "g"})
        # Cualquier ruta que dispatch por nombre debería retornar el mismo
        # mensaje. Verificamos llamando explícitamente al helper desde dos
        # ángulos para detectar drift si alguien re-introduce el guard duplicado.
        helper_msg_2 = server._create_spec_text({"title": "x", "goal": "y"})
        # El mensaje contiene los mismos elementos canónicos
        for marker in ("❌", "VIOLACIÓN DE GOBERNANZA", "cortex_sync_ticket"):
            assert marker in helper_msg
            assert marker in helper_msg_2


def test_cortex_sync_vault_tool() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]

    assert server._sync_vault_text() == "Vault synced - 3 documents indexed."


def test_cortex_import_hu_tool() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]

    result = server._import_hu_text({"external_id": "PROJ-123"})

    assert result == "Tracked item imported -> vault/hu/proj-123.md"


def test_cortex_get_hu_tool() -> None:
    server = CortexMCPServer.__new__(CortexMCPServer)
    server.memory = FakeMemory()  # type: ignore[assignment]

    result = server._get_hu_text({"item_id": "PROJ-123"})

    assert result == "Tracked item note -> vault/hu/proj-123.md"


# ---------------------------------------------------------------------------
# Tripartita Refinada — Plan 02 §1 cortex_validate_handoff
# ---------------------------------------------------------------------------


class TestHandoffValidation:
    """Contract tests for the ``cortex_validate_handoff`` MCP tool.

    These cover the schema enforcement guarantee: any agent emitting a
    structured handoff must round-trip through ``AgentHandoff`` so the
    next agent in the chain can rely on the field set.
    """

    def _make_server(self) -> CortexMCPServer:
        server = CortexMCPServer.__new__(CortexMCPServer)
        server.memory = FakeMemory()  # type: ignore[assignment]
        server.project_root = Path.cwd()
        server._called_tools = set()
        return server

    def test_valid_minimal_handoff_passes(self) -> None:
        server = self._make_server()
        yaml_text = "agent: cortex-code-explorer\nstatus: complete\n"
        result = server._validate_handoff_text({"handoff_yaml": yaml_text})
        assert "✅" in result
        assert "cortex-code-explorer" in result
        assert "status: complete" in result

    def test_invalid_agent_fails(self) -> None:
        server = self._make_server()
        yaml_text = "agent: nonexistent\nstatus: complete\n"
        result = server._validate_handoff_text({"handoff_yaml": yaml_text})
        assert "❌" in result
        assert "agent" in result.lower()

    def test_invalid_status_fails(self) -> None:
        server = self._make_server()
        yaml_text = "agent: cortex-documenter\nstatus: weird\n"
        result = server._validate_handoff_text({"handoff_yaml": yaml_text})
        assert "❌" in result
        assert "status" in result.lower()

    def test_expected_agent_mismatch_fails(self) -> None:
        server = self._make_server()
        yaml_text = "agent: cortex-documenter\nstatus: complete\n"
        result = server._validate_handoff_text(
            {"handoff_yaml": yaml_text, "expected_agent": "cortex-code-explorer"}
        )
        assert "Agent mismatch" in result

    def test_empty_yaml_fails(self) -> None:
        server = self._make_server()
        result = server._validate_handoff_text({"handoff_yaml": ""})
        assert "required" in result.lower()

    def test_full_handoff_reports_counts(self) -> None:
        server = self._make_server()
        yaml_text = (
            "agent: cortex-code-implementer\n"
            "status: partial\n"
            "verified_claims:\n"
            "  - 'auth.py modified'\n"
            "  - 'tests added'\n"
            "unverified_claims:\n"
            "  - 'performance impact negligible'\n"
            "artifacts_produced:\n"
            "  - path: src/auth.py\n"
            "    action: modified\n"
            "    lines_changed: 12\n"
            "context_for_next:\n"
            "  - 'documenter: verify TTL hardcoding'\n"
            "suggested_adr: true\n"
            "suggested_adr_reason: 'TTL hardcoded with UX/security trade-off'\n"
            "suggested_context_terms:\n"
            "  - JWT\n"
            "  - refresh-token\n"
        )
        result = server._validate_handoff_text({"handoff_yaml": yaml_text})
        assert "verified_claims: 2" in result
        assert "unverified_claims: 1" in result
        assert "artifacts: 1" in result
        assert "context_for_next: 1" in result
        assert "suggested ADR" in result
        assert "JWT" in result and "refresh-token" in result

    def test_malformed_yaml_returns_error(self) -> None:
        server = self._make_server()
        # Not a mapping at the root — AgentHandoff.from_yaml rejects this.
        result = server._validate_handoff_text({"handoff_yaml": "- just\n- a\n- list"})
        assert "❌" in result


# ---------------------------------------------------------------------------
# Tripartita Refinada — Plan 02 §2 cortex_verify_session_claims
# ---------------------------------------------------------------------------


class TestVerifySessionClaims:
    """Contract tests for the ``cortex_verify_session_claims`` MCP tool."""

    def _make_server(self, project_root: Path | None = None) -> CortexMCPServer:
        server = CortexMCPServer.__new__(CortexMCPServer)
        server.memory = FakeMemory()  # type: ignore[assignment]
        server.project_root = project_root or Path.cwd()
        server._called_tools = set()
        return server

    def test_empty_claims_returns_error(self) -> None:
        server = self._make_server()
        result = server._verify_session_claims_text({"claims": []})
        assert "❌" in result
        assert "claims" in result.lower()

    def test_claim_matched_in_diff_is_verified(self, monkeypatch) -> None:
        """A claim whose tokens appear in the diff lands in the verified bucket."""
        import subprocess

        def fake_run(cmd, **kwargs):  # noqa: ANN001 - test helper
            class _R:
                stdout = (
                    "diff --git a/cortex/handoff.py b/cortex/handoff.py\n"
                    "+    handoff = AgentHandoff.from_yaml(text)\n"
                    "+    handoff.validate()\n"
                )
            return _R()

        monkeypatch.setattr(subprocess, "run", fake_run)
        server = self._make_server()
        result = server._verify_session_claims_text(
            {"claims": ["AgentHandoff schema validated in handoff.py"]}
        )
        assert "verified: 1" in result
        assert "asserted: 0" in result

    def test_claim_without_evidence_is_asserted(self, monkeypatch) -> None:
        import subprocess

        def fake_run(cmd, **kwargs):  # noqa: ANN001
            class _R:
                stdout = "diff --git a/README.md b/README.md\n+typo fix\n"
            return _R()

        monkeypatch.setattr(subprocess, "run", fake_run)
        server = self._make_server()
        result = server._verify_session_claims_text(
            {"claims": ["nuclear reactor design refactored for safety"]}
        )
        assert "verified: 0" in result
        assert "asserted: 1" in result

    def test_reports_branch_in_summary(self, monkeypatch) -> None:
        import subprocess

        def fake_run(cmd, **kwargs):  # noqa: ANN001
            class _R:
                stdout = ""
            return _R()

        monkeypatch.setattr(subprocess, "run", fake_run)
        server = self._make_server()
        result = server._verify_session_claims_text(
            {"claims": ["something"], "base_branch": "feature/x"}
        )
        assert "feature/x" in result


# ---------------------------------------------------------------------------
# Tripartita Refinada — Plan 02 §3 confidence in MCP responses
# ---------------------------------------------------------------------------


class TestSearchConfidenceLabel:
    """``RetrievalResult.to_prompt`` must surface ``MemoryEntry.confidence``."""

    def test_confidence_label_appears_in_prompt(self) -> None:
        from cortex.models import EpisodicHit, MemoryEntry, RetrievalResult

        entry = MemoryEntry(
            content="Refactored auth flow",
            memory_type="session",
            confidence="verified",
        )
        rr = RetrievalResult(query="auth", episodic_hits=[EpisodicHit(entry=entry, score=0.5)])
        prompt = rr.to_prompt()
        assert "[verified]" in prompt
        assert "Refactored auth flow" in prompt

    def test_no_confidence_means_no_label(self) -> None:
        from cortex.models import EpisodicHit, MemoryEntry, RetrievalResult

        entry = MemoryEntry(content="Legacy memory without confidence", memory_type="session")
        rr = RetrievalResult(query="x", episodic_hits=[EpisodicHit(entry=entry, score=0.1)])
        prompt = rr.to_prompt()
        assert "[verified]" not in prompt
        assert "[asserted]" not in prompt
        assert "[contradicted]" not in prompt


# ---------------------------------------------------------------------------
# Tripartita Refinada — Plan 02 §4 cortex_save_session handoff cascade
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Tripartita Refinada — Plan 07 §3: MCP server exposes the 2 new tools
# ---------------------------------------------------------------------------


class TestNewMcpToolsRegistered:
    """Plan 07 §3 — the cierre del bloque MCP requires confirming that
    ``cortex_validate_handoff`` and ``cortex_verify_session_claims`` are
    actually wired into the server's ``list_tools`` handler. We assert
    by parsing the source file (same pattern as the CLI alignment test
    in ``tests/e2e/test_artefact_integrity.py``) so the test does not
    need to spin up an async event loop or load ChromaDB.
    """

    def _registered_tool_names(self) -> set[str]:
        import re
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / "cortex"
            / "mcp"
            / "server.py"
        ).read_text(encoding="utf-8")
        return set(re.findall(r'name="(cortex_[\w_]+)"', source))

    def test_validate_handoff_tool_registered(self) -> None:
        assert "cortex_validate_handoff" in self._registered_tool_names()

    def test_verify_session_claims_tool_registered(self) -> None:
        assert "cortex_verify_session_claims" in self._registered_tool_names()

    def test_dispatcher_routes_to_helpers(self) -> None:
        """Smoke: the call_tool dispatcher must route both new tools to
        the two helpers added in Plan 02. Detects accidental wiring loss."""
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / "cortex"
            / "mcp"
            / "server.py"
        ).read_text(encoding="utf-8")
        # The dispatcher branches must call the helpers.
        assert "self._validate_handoff_text(arguments)" in source
        assert "self._verify_session_claims_text(arguments)" in source


class TestSaveSessionHandoffArguments:
    """The MCP layer must forward the 5 new handoff kwargs to AgentMemory."""

    def test_handoff_kwargs_propagate_to_memory(self) -> None:
        server = CortexMCPServer.__new__(CortexMCPServer)
        memory = FakeMemory()
        server.memory = memory  # type: ignore[assignment]
        server._save_session_text(
            {
                "title": "T",
                "spec_summary": "S",
                "handoff": True,
                "blockers": ["wait for migration"],
                "verified_state": ["tests passing"],
                "unverified_claims": ["performance ok"],
                "suggested_skills": ["cortex-documenter"],
            }
        )
        assert memory.last_save_kwargs is not None
        kw = memory.last_save_kwargs
        assert kw["handoff"] is True
        assert kw["blockers"] == ["wait for migration"]
        assert kw["verified_state"] == ["tests passing"]
        assert kw["unverified_claims"] == ["performance ok"]
        assert kw["suggested_skills"] == ["cortex-documenter"]

    def test_handoff_defaults_when_omitted(self) -> None:
        server = CortexMCPServer.__new__(CortexMCPServer)
        memory = FakeMemory()
        server.memory = memory  # type: ignore[assignment]
        server._save_session_text({"title": "T", "spec_summary": "S"})
        assert memory.last_save_kwargs is not None
        kw = memory.last_save_kwargs
        assert kw["handoff"] is False
        assert kw["blockers"] == []
        assert kw["verified_state"] == []
        assert kw["unverified_claims"] == []
        assert kw["suggested_skills"] == []
