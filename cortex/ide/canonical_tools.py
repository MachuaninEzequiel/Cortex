"""
cortex.ide.canonical_tools
--------------------------
Vocabulario canonico de tools de Cortex y matriz de traduccion por IDE.

Los prompts canonicos (renders en ``cortex/setup/cortex_workspace.py`` que
producen ``.cortex/subagents/*.md`` y ``.cortex/skills/*.md``) referencian
tools por su NOMBRE CANONICO de Cortex (ej. ``read_file``, ``cortex_save_session``).

Cada adapter de IDE traduce esos nombres al formato que el IDE entiende
cuando inyecta el frontmatter ``tools:`` del archivo especifico del IDE.

Coherencia con principio rector #1 ("Cortex se comporta igual en todos los IDEs"):
NUNCA se reescribe el cuerpo del prompt. La traduccion solo aplica al
frontmatter ``tools:`` que el adapter inyecta.

Decisiones del creador (firmadas 2026-05-15, `MATRIZ-NATIVA-IDES.md` seccion 4):

- **claude_code**: usa nombres PascalCase nativos (``Read``, ``Write``) +
  prefijo ``mcp__cortex__`` para tools MCP.
- **opencode**: usa nombres lowercase nativos (``read``, ``write``) +
  los tools MCP se descubren dinamicamente (no se declaran en frontmatter).
- **codex**: NO usa frontmatter ``tools:`` — AGENTS.md es markdown plano.
  Este modulo NO traduce para codex (no aplica).
- **pi**: NO se toca el adapter (bundle estatico con contribuciones de
  comunidad). No usa MCP. Este modulo NO traduce para pi.
- **community/experimental** (vscode, cursor, claude_desktop, windsurf,
  antigravity, hermes, zed): NO validados contra docs oficiales 2026 en
  este plan. Quedan fuera de la matriz hasta plan futuro.

Si un adapter community necesita escribir archivos en formato compatible con
claude_code (ej. vscode escribe a ``.claude/agents/``), puede usar
``translate(canonical, "claude_code")`` directamente.
"""
from __future__ import annotations

from typing import Literal, get_args

# ---------------------------------------------------------------------------
# Vocabulario canonico
# ---------------------------------------------------------------------------

CanonicalTool = Literal[
    # Filesystem operations
    "read_file",
    "write_file",
    "edit_file",
    # Shell
    "execute_command",
    # Cortex MCP tools
    "cortex_search",
    "cortex_context",
    "cortex_save_session",
    "cortex_validate_handoff",
    "cortex_verify_session_claims",
    "cortex_sync_ticket",
    "cortex_create_spec",
    "cortex_ping",
    # NOTA: ``cortex_delegate_task`` fue eliminado en Fase 5 del plan
    # multi-IDE & MCP hardening (2026-05-15). La delegacion a subagents
    # es responsabilidad nativa del IDE, no del MCP server.
]


# IDEs cuyas traducciones estan VALIDADAS contra documentacion oficial 2026
# y soportan un frontmatter ``tools:`` que el adapter inyecta.
#
# Otros IDEs (codex, pi, vscode, cursor, claude_desktop, windsurf, antigravity,
# hermes, zed) NO estan en este Literal — el llamador recibe un type error si
# intenta usarlos, lo cual es intencional segun las decisiones firmadas
# (`MATRIZ-NATIVA-IDES.md` seccion 4).
ValidatedIDE = Literal["claude_code", "opencode"]


# ---------------------------------------------------------------------------
# Matriz de traduccion canonical -> IDE-native
# ---------------------------------------------------------------------------
#
# Valor ``None`` significa "este IDE NO acepta este tool en su frontmatter
# `tools:`". El adapter debe OMITIRLO del frontmatter inyectado.
#
# Para opencode, los tools MCP devuelven None: opencode descubre los tools
# MCP dinamicamente al conectarse al server; declararlos en frontmatter es
# error (ver `MATRIZ-NATIVA-IDES.md` seccion 1.2).

_TOOL_NAME_BY_IDE: dict[str, dict[str, str | None]] = {
    # ---------------- Filesystem ----------------
    "read_file": {
        "claude_code": "Read",
        "opencode": "read",
    },
    "write_file": {
        "claude_code": "Write",
        "opencode": "write",
    },
    "edit_file": {
        "claude_code": "Edit",
        "opencode": "edit",
    },
    # ---------------- Shell ----------------
    "execute_command": {
        "claude_code": "Bash",
        "opencode": "bash",
    },
    # ---------------- Cortex MCP ----------------
    # claude_code: el harness prefija ``mcp__<server>__`` cuando el frontmatter
    # restringe tools. Sin restriccion, el agente hereda todas; con restriccion,
    # debe listarlas explicitamente con el prefijo.
    #
    # opencode: None — los MCP tools se descubren dinamicamente y el adapter
    # NO debe declararlos en el campo ``tools:`` del agent profile (eso solo
    # acepta nombres nativos lowercase).
    "cortex_search": {
        "claude_code": "mcp__cortex__cortex_search",
        "opencode": None,
    },
    "cortex_context": {
        "claude_code": "mcp__cortex__cortex_context",
        "opencode": None,
    },
    "cortex_save_session": {
        "claude_code": "mcp__cortex__cortex_save_session",
        "opencode": None,
    },
    "cortex_validate_handoff": {
        "claude_code": "mcp__cortex__cortex_validate_handoff",
        "opencode": None,
    },
    "cortex_verify_session_claims": {
        "claude_code": "mcp__cortex__cortex_verify_session_claims",
        "opencode": None,
    },
    "cortex_sync_ticket": {
        "claude_code": "mcp__cortex__cortex_sync_ticket",
        "opencode": None,
    },
    "cortex_create_spec": {
        "claude_code": "mcp__cortex__cortex_create_spec",
        "opencode": None,
    },
    "cortex_ping": {
        "claude_code": "mcp__cortex__cortex_ping",
        "opencode": None,
    },
}


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------


class UnknownCanonicalToolError(KeyError):
    """Raised cuando se pide traducir un tool canonico que no existe."""


class UnvalidatedIDEError(KeyError):
    """Raised cuando se pide traducir para un IDE no validado en este plan.

    Los IDEs no validados (codex, pi, vscode, cursor, claude_desktop, etc.)
    NO tienen una traduccion certificada contra docs oficiales. El adapter
    correspondiente debe manejar sus tools sin pasar por este modulo.
    """


def translate(canonical: CanonicalTool, ide: str) -> str | None:
    """Traducir un tool canonico al nombre que el IDE espera.

    Args:
        canonical: nombre canonico de Cortex (ej. "read_file").
        ide:       identificador del IDE (ej. "claude_code", "opencode").

    Returns:
        - ``str`` con el nombre nativo del IDE.
        - ``None`` si el IDE acepta el tool pero NO lo declara en frontmatter
          (caso clasico: MCP tools en opencode, que se descubren dinamicamente).

    Raises:
        UnknownCanonicalToolError: si ``canonical`` no es uno de los tools
            declarados en ``CanonicalTool``.
        UnvalidatedIDEError: si ``ide`` no esta en ``ValidatedIDE``. El plan
            multi-IDE 2026 solo certifica ``claude_code`` y ``opencode``.
    """
    if canonical not in _TOOL_NAME_BY_IDE:
        raise UnknownCanonicalToolError(
            f"Canonical tool '{canonical}' is not in the canonical vocabulary. "
            f"Known tools: {sorted(_TOOL_NAME_BY_IDE.keys())}"
        )
    by_ide = _TOOL_NAME_BY_IDE[canonical]
    if ide not in by_ide:
        validated = get_validated_ides()
        raise UnvalidatedIDEError(
            f"IDE '{ide}' is not validated against official docs in this plan. "
            f"Validated IDEs: {validated}. See "
            f"docs/multi-ide-mcp-hardening/MATRIZ-NATIVA-IDES.md section 4."
        )
    return by_ide[ide]


def translate_list(canonical_tools: list[CanonicalTool], ide: str) -> list[str]:
    """Traducir una lista de tools canonicos al formato del IDE.

    Omite los tools cuya traduccion es ``None`` (no se declaran en frontmatter
    para ese IDE).

    Args:
        canonical_tools: lista de nombres canonicos.
        ide:             identificador del IDE.

    Returns:
        Lista de nombres nativos del IDE, ya filtrada (sin ``None``).

    Raises:
        UnknownCanonicalToolError: si algun tool de la lista no es canonico.
        UnvalidatedIDEError: si el IDE no esta validado.
    """
    out: list[str] = []
    for canonical in canonical_tools:
        translated = translate(canonical, ide)
        if translated is not None:
            out.append(translated)
    return out


def get_validated_ides() -> list[str]:
    """Devuelve la lista de IDEs validados contra docs oficiales 2026.

    Estos son los IDEs cuyo adapter inyecta un frontmatter ``tools:`` traducible
    y cuyas traducciones fueron verificadas contra documentacion oficial:

    - ``claude_code`` (Claude Code, ``.claude/agents/<name>.md``)
    - ``opencode`` (sst opencode, ``~/.config/opencode/agents/<name>.md``)
    """
    return list(get_args(ValidatedIDE))


def get_canonical_tools() -> list[str]:
    """Devuelve la lista completa de tools canonicos."""
    return list(get_args(CanonicalTool))
