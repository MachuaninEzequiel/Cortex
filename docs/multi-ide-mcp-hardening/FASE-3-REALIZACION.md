# FASE 3 — REALIZACION

**Fecha de ejecucion:** 2026-05-15
**Output formal:** `cortex/ide/canonical_tools.py` + tests + doc.
**Estado:** Completada. 49 tests nuevos pasando, 134 preexistentes sin regresion (183 totales). Linter `ruff` verde.

---

## 1. Tasks ejecutadas

| Task | Descripcion | Archivo principal |
|---|---|---|
| 3.1 | Crear `cortex/ide/canonical_tools.py` con vocabulario + matriz + API | `cortex/ide/canonical_tools.py` (227 lineas) |
| 3.2 | Tests del mapping (cobertura, traducciones, errores) | `tests/unit/ide/test_canonical_tools.py` (49 tests) |
| 3.3 | Documentacion del contrato + REALIZACION | `docs/architecture/canonical-tools.md` + este archivo |

---

## 2. Decisiones tomadas durante la realizacion

### 2.1 Solo 2 IDEs en la matriz (claude_code y opencode)

El plan original sugeria una matriz NxM con todos los IDEs como columnas. Tras Fase 0 (decisiones firmadas del creador), el alcance se redujo:

- **claude_code**: validado, columna explicita.
- **opencode**: validado, columna explicita.
- **codex**: no aplica — `AGENTS.md` es markdown plano sin frontmatter `tools:`. NO se incluye.
- **pi**: bundle estatico no-tocar — adapter no inyecta frontmatter via canonical_tools.
- **community/experimental** (vscode, cursor, claude_desktop, windsurf, antigravity, hermes, zed): no validados — fuera de la matriz.

**Tradeoff aceptado:** la matriz queda corta (2 IDEs) pero PRECISA. Cuando se valide un IDE community en plan futuro, se agrega una columna nueva.

### 2.2 `ValidatedIDE` Literal estricto + error explicito

En lugar de aceptar cualquier string como `ide` parameter, declaro `ValidatedIDE = Literal["claude_code", "opencode"]`. Cuando el caller pasa un IDE no validado:

```python
translate("read_file", "codex")
# raises UnvalidatedIDEError(
#   "IDE 'codex' is not validated against official docs in this plan. "
#   "Validated IDEs: ['claude_code', 'opencode']. See "
#   "docs/multi-ide-mcp-hardening/MATRIZ-NATIVA-IDES.md section 4."
# )
```

**Razon:** previene drift silencioso. Si alguien intenta extender el modulo sin firmar el IDE, el codigo falla con guidance accionable hacia la doc del plan.

### 2.3 `None` como valor explicito para "tool acepted, no en frontmatter"

Para opencode + tools MCP, el valor es `None`. Significa: "opencode soporta este tool pero NO se declara en el campo `tools:` del agent profile" (se descubre dinamicamente al conectarse al MCP server).

Esto es distinto de `UnvalidatedIDEError` (IDE no soportado) y de `UnknownCanonicalToolError` (tool no existe). Tres senales semanticas distintas, cada una con su tipo de exception o valor de retorno:

| Caso | Comportamiento |
|---|---|
| Tool acepted, declarable en frontmatter | Devuelve `str` con nombre nativo |
| Tool acepted, descubierto dinamicamente | Devuelve `None` |
| Tool no existe en vocabulario | Lanza `UnknownCanonicalToolError` |
| IDE no validado | Lanza `UnvalidatedIDEError` |

### 2.4 `translate_list` filtra `None` automaticamente

Para conveniencia del adapter consumidor: si un subagent declara tools `[read_file, write_file, cortex_save_session]` y se traduce a opencode, el output debe ser `["read", "write"]` (no `["read", "write", None]`).

El filtrado se hace dentro de `translate_list` en lugar de en cada caller. Tests `test_translate_list_filters_none_for_opencode_mcp` validan el comportamiento.

### 2.5 Test `test_no_orphan_ide_in_matrix` como red de seguridad

Si un developer agrega `cursor` a `_TOOL_NAME_BY_IDE` sin agregarla a `Literal[ValidatedIDE]`, el test falla:

```
AssertionError: Tool 'read_file' tiene IDEs en la matriz que no estan en ValidatedIDE Literal: {'cursor'}
```

**Razon:** evita la situacion donde la matriz crece silenciosamente con IDEs no validados, pasando la verificacion del Literal pero violando el contrato del plan.

### 2.6 Vocabulario incluye `cortex_delegate_task` (deprecado)

Aunque Fase 5 lo eliminara, el vocabulario actual lo incluye porque la skill canonica `cortex-SDDwork.md` aun lo referencia. Cuando Fase 5 elimine la mencion del template en `cortex_workspace.py`, se quita tambien del `Literal`.

**Tradeoff:** mantener un tool deprecado evita que el adapter de claude_code falle al traducir. El test correspondiente (`test_translate_mcp_tool_for_opencode_returns_none`) lista los 9 MCP tools incluyendo el delegate, asi cuando Fase 5 elimine la referencia, todos los tests fallan limpiamente y obligan a actualizar.

---

## 3. Cumplimiento del gate de cero deuda tecnica de Fase 3

| Item del gate | Estado |
|---|---|
| `cortex/ide/canonical_tools.py` cubre todos los tools que aparecen en prompts canonicos | OK — 13 tools (filesystem 3, shell 1, MCP 9). Test `test_get_canonical_tools_includes_all_subagent_tools` valida. |
| Cubre todos los IDEs validados (decision firmada: solo claude_code + opencode) | OK — `Literal[ValidatedIDE]` + tests `test_every_validated_ide_has_entry_for_every_tool`. |
| Tests cubren la matriz exhaustivamente | OK — 49 tests, cobertura completa de matriz, traducciones parametrizadas, errores. |
| Documentacion accionable | OK — `docs/architecture/canonical-tools.md` con: contrato, vocabulario, procedimiento para agregar tool/IDE, anti-patterns. |
| Linter `ruff` verde | OK. |
| CERO `TODO`/`FIXME`/`HACK` agregados | OK — verificado con grep. |
| CERO IDEs en la matriz que no esten en `ValidatedIDE` | OK — test `test_no_orphan_ide_in_matrix` lo previene. |
| CERO tools en `Literal[CanonicalTool]` que no esten en `_TOOL_NAME_BY_IDE` | OK — test `test_every_canonical_tool_has_entry_in_matrix`. |

---

## 4. Acoplamiento con fases anteriores

- **Fase 0**: este modulo materializa las decisiones 1-4 firmadas. Codex/pi/community quedan fuera segun lo decidido.
- **Fase 1**: independiente. canonical_tools no toca el MCP server.
- **Fase 2**: incluye `cortex_ping` (introducido en Fase 2) en el vocabulario.

## 5. Items para handoff a Fase 4

Fase 4 (adapters SSoT) es la consumidora directa de este modulo. Cambios concretos esperados:

### claude_code adapter

```python
# En cortex/ide/adapters/claude_code.py inject_profiles, al escribir
# .claude/agents/<name>.md, agregar el frontmatter `tools:` traducido:

from cortex.ide.canonical_tools import translate_list
from cortex.ide.prompts import split_markdown_frontmatter

# Leer el frontmatter del archivo canonico
canonical_md = get_subagent_prompt(project_root, agent_name)
canonical_frontmatter, body = split_markdown_frontmatter(canonical_md)

# Parsear `tools:` del canonical_frontmatter (formato: "tools: a, b, c")
canonical_tools_list = parse_tools_field(canonical_frontmatter)

# Traducir y escribir en el frontmatter del archivo inyectado
translated_tools = translate_list(canonical_tools_list, "claude_code")
# Inyectar como: tools: Read, Write, mcp__cortex__cortex_save_session, ...
```

### opencode adapter

```python
# El agent profile JSON ya NO declara MCP tools (se descubren dinamicamente).
# El campo `tools` solo lleva los nativos lowercase:

from cortex.ide.canonical_tools import translate_list

native_tools = translate_list(canonical_tools_list, "opencode")
# native_tools: ["read", "write", ...] (sin MCP — fueron filtrados como None)

# El profile JSON queda:
"tools": {
    "read": True,
    "write": True,
    # ... segun lo declarado
    # NO incluir cortex_save_session, etc. — se descubren via MCP discovery
}
```

### codex y pi: NO usan este modulo

Confirmado por las decisiones firmadas. codex genera AGENTS.md plano; pi es bundle estatico.

---

## 6. Handoff formal

```yaml
agent: fase-3-canonical-tools
status: completed
artifacts_produced:
  - cortex/ide/canonical_tools.py (227 lineas)
  - tests/unit/ide/__init__.py
  - tests/unit/ide/test_canonical_tools.py (49 tests)
  - docs/architecture/canonical-tools.md
  - docs/multi-ide-mcp-hardening/FASE-3-REALIZACION.md (este documento)
verified_claims:
  - "49 tests nuevos pasando"
  - "134 tests preexistentes sin regresion (183 totales)"
  - "Linter ruff verde"
  - "Vocabulario cubre todos los tools mencionados en .cortex/subagents/*.md y .cortex/skills/*.md"
  - "Decisiones firmadas del creador respetadas: solo claude_code + opencode validados"
  - "Errores claros para IDEs no validados (UnvalidatedIDEError) y tools desconocidos (UnknownCanonicalToolError)"
unverified_claims: []
contradicted_claims: []
context_for_next:
  - "Fase 4 puede consumir translate / translate_list / get_validated_ides"
  - "Fase 4 debe parsear el frontmatter `tools:` de los archivos canonicos
    (o leer la lista desde los renders de cortex_workspace.py) y aplicar la traduccion"
  - "Fase 5 (eliminacion delegate) debe quitar 'cortex_delegate_task' del Literal y de la matriz; el test test_translate_mcp_tool_for_opencode_returns_none fallara limpiamente y avisa"
suggested_adr: false
```
