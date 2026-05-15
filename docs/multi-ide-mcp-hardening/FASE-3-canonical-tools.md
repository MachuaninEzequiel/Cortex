# FASE 3 — Vocabulario canonico de tools

**Semaforo:** Amarillo.
**Pre-requisitos:** Fase 0 cerrada (en particular seccion 2 del `INVENTARIO.md`).
**Bloquea:** Fase 4.

---

## Objetivo

Crear la unica fuente de verdad para la traduccion entre el **vocabulario canonico de Cortex** (los nombres que usan los prompts en `.cortex/subagents/*.md`) y los **nombres reales de cada IDE soportado** (`Read` en Claude Code, `read_file` en opencode, etc.).

Coherencia con principio rector #1 ("Cortex se comporta igual en todos los IDEs"): los prompts canonicos referencian los tools por nombre canonico. El adapter del IDE traduce esos nombres al formato que el IDE entiende, sin tocar el cuerpo del prompt.

---

## Tasks

### Task 3.1 — Crear `cortex/ide/canonical_tools.py`

**Archivo nuevo:** `cortex/ide/canonical_tools.py`.

**Contenido:**

```python
"""
Vocabulario canonico de tools de Cortex.

Los prompts en .cortex/subagents/*.md y .cortex/skills/*.md referencian
tools por su NOMBRE CANONICO. Cada adapter de IDE traduce estos nombres
al formato que el IDE entiende.

NUNCA reescribir el cuerpo de un prompt. La traduccion solo aplica al
frontmatter `tools:` que el adapter inyecta en la copia especifica del IDE.
"""

from typing import Literal

CanonicalTool = Literal[
    # Filesystem operations
    "read_file",
    "write_file",
    "edit_file",
    "glob",
    "grep",
    # Shell
    "execute_command",
    # Cortex MCP tools (mismo nombre canonico, varia el prefijo MCP por IDE)
    "cortex_save_session",
    "cortex_search",
    "cortex_search_vector",
    "cortex_context",
    "cortex_verify_session_claims",
    "cortex_validate_handoff",
    "cortex_ping",
    # ... (completar segun INVENTARIO.md seccion 2)
]

IDEName = Literal["claude_code", "opencode", "cursor", "codex", "pi", "vscode", "windsurf", "zed", "antigravity", "claude_desktop", "hermes"]

# Mapping: tool canonico -> nombre real por IDE
# Si un IDE no soporta un tool, valor None (el adapter lo omite del frontmatter).
TOOL_NAME_BY_IDE: dict[CanonicalTool, dict[IDEName, str | None]] = {
    "read_file": {
        "claude_code": "Read",
        "opencode": "read_file",
        "cursor": "read_file",
        # ... completar todos los IDEs
    },
    "write_file": {
        "claude_code": "Write",
        "opencode": "write_file",
        # ...
    },
    # ... resto
    "cortex_save_session": {
        "claude_code": "mcp__cortex__cortex_save_session",
        "opencode": "cortex_save_session",
        # ...
    },
    # ... resto MCP tools
}


def translate(canonical: CanonicalTool, ide: IDEName) -> str | None:
    """Devuelve el nombre que <ide> entiende para el tool canonico.
    None si el IDE no soporta el tool (el adapter lo omite)."""
    return TOOL_NAME_BY_IDE[canonical][ide]


def translate_list(canonical_tools: list[CanonicalTool], ide: IDEName) -> list[str]:
    """Traduce una lista de tools canonicos a la lista del IDE,
    omitiendo los None (no soportados)."""
    out = []
    for t in canonical_tools:
        name = translate(t, ide)
        if name is not None:
            out.append(name)
    return out
```

### Task 3.2 — Validar la matriz contra `INVENTARIO.md`

Para cada IDE listado en la seccion 2 del inventario, completar las celdas. Si una celda no se puede completar (porque el IDE no soporta el tool, o porque el nombre real es desconocido), documentarlo explicitamente — NO dejar `None` sin justificacion.

### Task 3.3 — Tests del mapping

**Archivo nuevo:** `tests/unit/ide/test_canonical_tools.py`.

**Tests:**
- `test_all_canonical_tools_have_mapping_for_all_ides`: itera `CanonicalTool` x `IDEName`, falla si una celda no esta declarada (incluso si es `None` explicito).
- `test_translate_returns_correct_name`: parametrizado, ej. `translate("read_file", "claude_code") == "Read"`.
- `test_translate_list_filters_unsupported`: si un IDE devuelve `None` para un tool, no aparece en la lista resultante.
- `test_no_orphan_ides`: cada IDE en `IDEName` aparece como columna completa en `TOOL_NAME_BY_IDE`.

### Task 3.4 — Documentacion del contrato

**Archivo:** `docs/architecture/canonical-tools.md` (nuevo).

**Contenido:**
- Por que existe el vocabulario canonico (anti-patron del prompt reescrito por IDE).
- Como agregar un tool nuevo (procedimiento paso a paso).
- Como agregar un IDE nuevo (procedimiento paso a paso).
- Politica de "soportado / no soportado": cuando declarar `None` y como documentarlo.

---

## Archivos involucrados

- Nuevos:
  - `cortex/ide/canonical_tools.py`
  - `tests/unit/ide/test_canonical_tools.py`
  - `docs/architecture/canonical-tools.md`
- Modificados: ninguno (los adapters se modifican en Fase 4).

---

## Criterios de aceptacion

- [ ] `cortex/ide/canonical_tools.py` cubre TODOS los tools listados en `INVENTARIO.md` seccion 2.
- [ ] `cortex/ide/canonical_tools.py` cubre TODOS los IDEs en `cortex/ide/adapters/`.
- [ ] El test `test_all_canonical_tools_have_mapping_for_all_ides` pasa sin excepciones.
- [ ] La documentacion explica como extender la matriz cuando se agrega un IDE o un tool.

---

## Gate de cero deuda tecnica

- [ ] CERO `None` en la matriz sin justificacion documentada.
- [ ] CERO tools canonicos declarados pero sin uso en ningun prompt canonico actual (la matriz no se infla con tools "para el futuro").
- [ ] CERO IDEs declarados pero sin adapter en `cortex/ide/adapters/`.
- [ ] Tests cubren la totalidad de la matriz, no solo casos felices.
- [ ] El contrato esta documentado de forma que un colaborador externo puede agregar IDE/tool sin preguntar.

---

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| El nombre real de un tool en algun IDE cambio entre versiones | Documentar la version del IDE contra la que se valido. Smoke test en Fase 7 incluye verificacion en runtime. |
| La matriz se desactualiza si alguien agrega un adapter sin agregar las columnas | Test `test_no_orphan_ides` previene merge de adapters sin sus columnas. CI gate. |
| Un IDE soporta un tool con nombre completamente distinto (no solo casing) | El mapping es libre — soporta cualquier nombre. Lo unico que se mantiene constante es el nombre canonico del lado de Cortex. |

---

## Estimacion

1 sesion. Es mecanico; el bottleneck es validar contra `INVENTARIO.md`.

---

## Handoff a Fase 4

```yaml
agent: fase-3-canonical-tools
status: completed
artifacts_produced:
  - cortex/ide/canonical_tools.py
  - tests/unit/ide/test_canonical_tools.py
  - docs/architecture/canonical-tools.md
verified_claims:
  - "Matriz cubre todos los tools de INVENTARIO.md y todos los IDEs en cortex/ide/adapters/"
  - "Tests previenen drift entre IDEs/adapters/matriz"
context_for_next:
  - "Fase 4 puede importar translate() y translate_list() para reescribir los adapters"
```
