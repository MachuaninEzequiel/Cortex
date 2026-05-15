"""Tests para cortex.ide.canonical_tools (Fase 3 del plan multi-IDE)."""
from __future__ import annotations

from typing import get_args

import pytest

from cortex.ide import canonical_tools as ct
from cortex.ide.canonical_tools import (
    CanonicalTool,
    UnknownCanonicalToolError,
    UnvalidatedIDEError,
    ValidatedIDE,
    get_canonical_tools,
    get_validated_ides,
    translate,
    translate_list,
)

# ---------------------------------------------------------------------------
# Cobertura de la matriz
# ---------------------------------------------------------------------------


def test_every_canonical_tool_has_entry_in_matrix():
    """Todo tool en CanonicalTool debe estar en la matriz interna."""
    canonical_set = set(get_args(CanonicalTool))
    matrix_set = set(ct._TOOL_NAME_BY_IDE.keys())
    missing = canonical_set - matrix_set
    extra = matrix_set - canonical_set
    assert not missing, f"Tools en CanonicalTool sin entry en matriz: {missing}"
    assert not extra, f"Entries en matriz sin declaracion en CanonicalTool: {extra}"


def test_every_validated_ide_has_entry_for_every_tool():
    """Para cada IDE validado, cada tool canonico debe tener una traduccion declarada (incluso si es None)."""
    validated = get_args(ValidatedIDE)
    for canonical in get_args(CanonicalTool):
        by_ide = ct._TOOL_NAME_BY_IDE[canonical]
        for ide in validated:
            assert ide in by_ide, (
                f"Falta entry para IDE '{ide}' en tool canonico '{canonical}'. "
                "Cada IDE validado debe tener traduccion explicita (str o None)."
            )


def test_no_orphan_ide_in_matrix():
    """La matriz NO debe tener IDEs que no esten en ValidatedIDE.

    Esto previene drift: si alguien agrega 'cursor' a la matriz sin agregarla
    a ValidatedIDE, el test falla y obliga a actualizar el Literal.
    """
    validated_set = set(get_args(ValidatedIDE))
    for canonical, by_ide in ct._TOOL_NAME_BY_IDE.items():
        orphans = set(by_ide.keys()) - validated_set
        assert not orphans, (
            f"Tool '{canonical}' tiene IDEs en la matriz que no estan en "
            f"ValidatedIDE Literal: {orphans}"
        )


# ---------------------------------------------------------------------------
# translate()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("canonical,ide,expected", [
    ("read_file", "claude_code", "Read"),
    ("read_file", "opencode", "read"),
    ("write_file", "claude_code", "Write"),
    ("write_file", "opencode", "write"),
    ("edit_file", "claude_code", "Edit"),
    ("edit_file", "opencode", "edit"),
    ("execute_command", "claude_code", "Bash"),
    ("execute_command", "opencode", "bash"),
])
def test_translate_filesystem_tools(canonical, ide, expected):
    """Filesystem tools devuelven el nombre nativo del IDE."""
    assert translate(canonical, ide) == expected


_MCP_TOOLS_PARAMETRIZED = [
    "cortex_search",
    "cortex_context",
    "cortex_save_session",
    "cortex_validate_handoff",
    "cortex_verify_session_claims",
    "cortex_sync_ticket",
    "cortex_create_spec",
    "cortex_ping",
    # cortex_delegate_task ELIMINADO en Fase 5 del plan multi-IDE.
]


@pytest.mark.parametrize("canonical", _MCP_TOOLS_PARAMETRIZED)
def test_translate_mcp_tool_for_claude_code_has_prefix(canonical):
    """En claude_code, todo tool MCP debe tener prefijo mcp__cortex__."""
    result = translate(canonical, "claude_code")
    assert result is not None
    assert result.startswith("mcp__cortex__"), (
        f"Tool MCP {canonical} en claude_code debe llevar prefijo mcp__cortex__. Got: {result}"
    )
    assert result == f"mcp__cortex__{canonical}"


@pytest.mark.parametrize("canonical", _MCP_TOOLS_PARAMETRIZED)
def test_translate_mcp_tool_for_opencode_returns_none(canonical):
    """En opencode, todo tool MCP devuelve None (descubrimiento dinamico)."""
    assert translate(canonical, "opencode") is None


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------


def test_translate_raises_on_unknown_canonical():
    """Tool canonico no existente debe lanzar UnknownCanonicalToolError."""
    with pytest.raises(UnknownCanonicalToolError) as exc_info:
        translate("does_not_exist_tool", "claude_code")
    msg = str(exc_info.value)
    assert "does_not_exist_tool" in msg
    assert "canonical vocabulary" in msg.lower()


def test_translate_raises_on_unvalidated_ide():
    """IDE no validado debe lanzar UnvalidatedIDEError con guidance."""
    with pytest.raises(UnvalidatedIDEError) as exc_info:
        translate("read_file", "codex")
    msg = str(exc_info.value)
    assert "codex" in msg
    assert "validated" in msg.lower()
    assert "MATRIZ-NATIVA-IDES.md" in msg, "Debe referenciar la doc del plan"


@pytest.mark.parametrize("ide", ["pi", "cursor", "vscode", "claude_desktop", "windsurf", "antigravity", "hermes", "zed"])
def test_translate_rejects_all_unvalidated_ides(ide):
    """Todos los IDEs no listados en ValidatedIDE son rechazados."""
    with pytest.raises(UnvalidatedIDEError):
        translate("read_file", ide)


# ---------------------------------------------------------------------------
# translate_list()
# ---------------------------------------------------------------------------


def test_translate_list_filesystem_only():
    """Lista de filesystem tools devuelve todos traducidos."""
    tools: list[CanonicalTool] = ["read_file", "write_file", "edit_file"]
    assert translate_list(tools, "claude_code") == ["Read", "Write", "Edit"]
    assert translate_list(tools, "opencode") == ["read", "write", "edit"]


def test_translate_list_filters_none_for_opencode_mcp():
    """Lista mixta filtra los None (MCP tools en opencode no aparecen)."""
    tools: list[CanonicalTool] = [
        "read_file",
        "write_file",
        "cortex_save_session",
        "cortex_verify_session_claims",
    ]
    result = translate_list(tools, "opencode")
    # Solo los filesystem aparecen; los MCP fueron filtrados (None).
    assert result == ["read", "write"]


def test_translate_list_keeps_all_for_claude_code():
    """En claude_code, todos los tools aparecen (ninguno es None)."""
    tools: list[CanonicalTool] = [
        "read_file",
        "write_file",
        "cortex_save_session",
        "cortex_verify_session_claims",
    ]
    result = translate_list(tools, "claude_code")
    assert result == [
        "Read",
        "Write",
        "mcp__cortex__cortex_save_session",
        "mcp__cortex__cortex_verify_session_claims",
    ]


def test_translate_list_empty_input():
    """Lista vacia devuelve lista vacia."""
    assert translate_list([], "claude_code") == []
    assert translate_list([], "opencode") == []


def test_translate_list_propagates_unknown_tool_error():
    """translate_list propaga UnknownCanonicalToolError si algun item es invalido."""
    with pytest.raises(UnknownCanonicalToolError):
        translate_list(["read_file", "this_is_not_a_tool"], "claude_code")


def test_translate_list_propagates_unvalidated_ide_error():
    """translate_list propaga UnvalidatedIDEError si el IDE no es valido."""
    with pytest.raises(UnvalidatedIDEError):
        translate_list(["read_file"], "codex")


# ---------------------------------------------------------------------------
# Helpers de introspeccion
# ---------------------------------------------------------------------------


def test_get_validated_ides_returns_exactly_two():
    """Las decisiones del creador limitan a claude_code + opencode."""
    validated = get_validated_ides()
    assert validated == ["claude_code", "opencode"]


def test_get_canonical_tools_includes_all_subagent_tools():
    """Vocabulario debe cubrir los tools que los prompts canonicos referencian."""
    tools = get_canonical_tools()
    # Tools que aparecen en .cortex/subagents/*.md frontmatter:
    required = {
        "read_file",
        "write_file",
        "edit_file",
        "execute_command",
        "cortex_search",
        "cortex_context",
        "cortex_save_session",
        "cortex_validate_handoff",
        "cortex_verify_session_claims",
    }
    missing = required - set(tools)
    assert not missing, f"Vocabulario incompleto. Falta: {missing}"


def test_get_canonical_tools_includes_skill_tools():
    """Tools mencionados en skills canonicas (cortex-sync, cortex-SDDwork)."""
    tools = get_canonical_tools()
    skill_required = {
        "cortex_sync_ticket",
        "cortex_create_spec",
    }
    missing = skill_required - set(tools)
    assert not missing, f"Vocabulario sin tools de skills. Falta: {missing}"


def test_get_canonical_tools_includes_phase_2_ping():
    """cortex_ping (introducido en Fase 2) debe estar en el vocabulario."""
    assert "cortex_ping" in get_canonical_tools()


def test_cortex_delegate_task_removed_in_phase5():
    """Regression guard: cortex_delegate_task fue eliminado en Fase 5
    del plan multi-IDE & MCP hardening (2026-05-15). NO debe volver al
    vocabulario sin un nuevo plan que lo justifique."""
    assert "cortex_delegate_task" not in get_canonical_tools()
    # Tampoco en la matriz interna.
    from cortex.ide import canonical_tools as ct
    assert "cortex_delegate_task" not in ct._TOOL_NAME_BY_IDE
