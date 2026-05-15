# Canonical Tools — vocabulario y matriz de traduccion

**Estado:** Vigente desde Fase 3 del plan `docs/multi-ide-mcp-hardening/` (2026-05-15).
**Aplica a:** `cortex/ide/canonical_tools.py` + adapters en `cortex/ide/adapters/*.py` (consumidores).

---

## 1. Por que existe este modulo

Los prompts canonicos de Cortex (renders en `cortex/setup/cortex_workspace.py` que producen `.cortex/subagents/*.md` y `.cortex/skills/*.md`) referencian tools por su NOMBRE CANONICO de Cortex.

Ejemplo del frontmatter de `cortex-documenter.md`:

```yaml
tools: read_file, write_file, cortex_save_session, cortex_verify_session_claims, cortex_validate_handoff, cortex_search
```

Cada IDE espera nombres distintos para esos mismos tools:

| Canonical | Claude Code | opencode |
|---|---|---|
| `read_file` | `Read` | `read` |
| `write_file` | `Write` | `write` |
| `cortex_save_session` | `mcp__cortex__cortex_save_session` | (no se declara — descubierto) |

Sin un punto unico de verdad, cada adapter de IDE tendria que reimplementar la traduccion. Y peor: si la traduccion es incorrecta, el subagent inyectado en el IDE viola la restriccion declarada por su prompt canonico (puede invocar tools que no debia).

`canonical_tools.py` es ese punto unico.

---

## 2. Decisiones del creador (firmadas 2026-05-15)

Las traducciones que este modulo soporta estan limitadas a IDEs validados contra documentacion oficial 2026:

- **claude_code** — validado contra https://code.claude.com/docs/en/sub-agents
- **opencode** — validado contra https://opencode.ai/docs/agents/

Los siguientes IDEs NO estan en la matriz, por decision arquitectural firmada:

- **codex**: AGENTS.md es markdown plano sin frontmatter `tools:`. NO aplica traduccion.
- **pi**: bundle estatico con contribuciones de comunidad — no se toca el adapter.
- **community/experimental** (vscode, cursor, claude_desktop, windsurf, antigravity, hermes, zed): NO validados contra docs oficiales en este plan. Quedan fuera hasta plan futuro.

Si un adapter community necesita escribir archivos en formato compatible con un IDE validado (ej. vscode escribe a `.claude/agents/`), puede invocar `translate(canonical, "claude_code")` directamente.

Ver `docs/multi-ide-mcp-hardening/MATRIZ-NATIVA-IDES.md` seccion 4 para las decisiones completas.

---

## 3. API publica

```python
from cortex.ide.canonical_tools import (
    translate,
    translate_list,
    get_validated_ides,
    get_canonical_tools,
    UnknownCanonicalToolError,
    UnvalidatedIDEError,
)
```

### `translate(canonical, ide) -> str | None`

Traduce un tool canonico al nombre que el IDE espera.

- Devuelve `str` si el IDE acepta el tool en su frontmatter `tools:`.
- Devuelve `None` si el IDE acepta el tool pero NO lo declara en frontmatter (ej. MCP tools en opencode, que se descubren dinamicamente).
- Lanza `UnknownCanonicalToolError` si `canonical` no es del vocabulario.
- Lanza `UnvalidatedIDEError` si `ide` no es uno de los validados.

### `translate_list(canonical_tools, ide) -> list[str]`

Traduce una lista de tools canonicos. Filtra los `None` automaticamente — el output esta listo para inyectar en el frontmatter del archivo del IDE.

### `get_validated_ides() -> list[str]`

Devuelve `["claude_code", "opencode"]`. Lista canonica de IDEs que tienen traduccion certificada.

### `get_canonical_tools() -> list[str]`

Devuelve la lista completa de tools canonicos declarados en el `Literal[CanonicalTool]`.

---

## 4. Vocabulario actual

### Filesystem operations

| Canonical | Significado |
|---|---|
| `read_file` | Leer un archivo del filesystem |
| `write_file` | Escribir/sobrescribir un archivo |
| `edit_file` | Editar un archivo (modificar in-place) |

### Shell

| Canonical | Significado |
|---|---|
| `execute_command` | Ejecutar un comando de shell |

### Cortex MCP tools

| Canonical | Significado |
|---|---|
| `cortex_search` | Busqueda en memoria episodica + semantica |
| `cortex_context` | Recuperar contexto enriquecido |
| `cortex_save_session` | Persistir nota de sesion en el vault |
| `cortex_validate_handoff` | Validar YAML handoff contra schema |
| `cortex_verify_session_claims` | Cross-check de claims contra git diff |
| `cortex_sync_ticket` | Sync de ticket externo (Jira/Linear/etc.) |
| `cortex_create_spec` | Crear spec de implementacion |
| `cortex_ping` | Health check del MCP server (Fase 2) |
| ~~`cortex_delegate_task`~~ | ELIMINADO en Fase 5 (2026-05-15) — la delegacion ahora es nativa del IDE |

---

## 5. Como agregar un tool canonico nuevo

1. Agregar el nombre al `Literal[CanonicalTool]` en `canonical_tools.py`.
2. Agregar entry en `_TOOL_NAME_BY_IDE` con traduccion para CADA IDE validado.
3. Si la traduccion es `None` para algun IDE, justificar con un comentario inline.
4. Agregar mencion en este documento (seccion 4).
5. Correr tests: `pytest tests/unit/ide/test_canonical_tools.py`.

El test `test_every_canonical_tool_has_entry_in_matrix` falla si olvidas el paso 2 — esto es intencional como red de seguridad.

---

## 6. Como agregar un IDE validado nuevo

1. Validar el IDE contra su documentacion oficial vigente. Documentar en `docs/multi-ide-mcp-hardening/MATRIZ-NATIVA-IDES.md` la estructura nativa (paths, formato de archivos, vocabulario de tools, mecanismo MCP).
2. Obtener firma del creador (no agregar IDEs sin esto).
3. Agregar el nombre al `Literal[ValidatedIDE]` en `canonical_tools.py`.
4. Agregar columna del IDE en `_TOOL_NAME_BY_IDE` para CADA tool canonico.
5. Si el IDE NO declara algun tool en frontmatter, el valor es `None`.
6. Correr tests: `test_every_validated_ide_has_entry_for_every_tool` falla si olvidas el paso 4.

---

## 7. Como NO usar este modulo

- **NO inventar IDEs nuevos sin firma del creador.** Si necesitas validar uno, abrir un plan separado.
- **NO modificar prompts canonicos** para "evitar" la traduccion. Los prompts referencian nombres canonicos. Punto.
- **NO inyectar tools MCP en frontmatter de opencode.** opencode los descubre dinamicamente.
- **NO usar este modulo para codex o pi.** codex no tiene frontmatter `tools:`; pi no se toca.

---

## 8. Tests

Cobertura completa en `tests/unit/ide/test_canonical_tools.py` (49 tests):

- Cobertura de la matriz (cada tool x cada IDE validado tiene entry).
- No-orphan: la matriz no tiene IDEs no listados en `ValidatedIDE`.
- Traduccion correcta para filesystem y MCP (parametrizada por tool).
- Filtrado de `None` en `translate_list`.
- Errores claros para tools desconocidos y IDEs no validados.
- Cobertura del vocabulario contra los tools que los prompts canonicos referencian.
