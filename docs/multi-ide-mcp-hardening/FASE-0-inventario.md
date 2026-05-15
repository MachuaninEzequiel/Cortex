# FASE 0 — Inventario y verificacion

**Semaforo:** Verde (read-only).
**Pre-requisitos:** Ninguno.
**Bloquea:** Fase 1, Fase 3, Fase 4, Fase 6.

---

## Objetivo

Producir un mapa completo y verificado del estado actual del sistema en las tres areas que el plan toca, **antes de mover ningun byte de codigo**:

1. Copias paralelas de prompts canonicos (subagentes, skills) en el repo.
2. Adapters de IDE existentes y la forma exacta en que cada uno nombra los tools (Read vs read_file vs etc.).
3. Callers actuales del `cortex_delegate_task` / `cortex_delegate_batch` MCP, dentro del repo y en el ecosistema documentado.

El output de esta fase es **un solo documento** (`INVENTARIO.md` dentro de esta misma carpeta) que sirve como input verificado para Fases 1, 3, 4, 5 y 6.

---

## Tasks

### Task 0.1 — Inventariar copias de prompts canonicos

Buscar en el repo todas las ocurrencias de los archivos de prompt:

```
- .cortex/subagents/*.md
- .cortex/skills/*.md
- cortex-pi/.pi/agents/*.md
- Cualquier otro path que contenga prompts referenciados por nombre (cortex-documenter, cortex-code-explorer, cortex-code-implementer, cortex-SDDwork, cortex-sync, cortex-test-verifier, cortex-security-auditor)
```

Para cada par de archivos con el mismo nombre logico (ej. `cortex-documenter.md` en dos paths):
- Hacer diff binario.
- Si difieren: registrar las diferencias semanticas (no solo whitespace) en una tabla.

**Archivos a inspeccionar (no exhaustivo, ampliar si Task 0.1 descubre mas):**
- `.cortex/subagents/cortex-documenter.md`
- `cortex-pi/.pi/agents/cortex-documenter.md`
- `.cortex/subagents/cortex-code-explorer.md`
- `cortex-pi/.pi/agents/cortex-code-explorer.md`
- `.cortex/subagents/cortex-code-implementer.md`
- `cortex-pi/.pi/agents/cortex-code-implementer.md`
- `cortex-pi/.pi/agents/cortex-SDDwork.md`
- `cortex-pi/.pi/agents/cortex-sync.md`
- `cortex-pi/.pi/agents/cortex-security-auditor.md`
- `cortex-pi/.pi/agents/cortex-test-verifier.md`

### Task 0.2 — Inventariar adapters de IDE y vocabulario de tools

Para cada archivo en `cortex/ide/adapters/*.py`:
- Identificar los nombres exactos que el IDE espera para los tools de filesystem (read/write/edit/bash) y MCP.
- Identificar el archivo de configuracion que cada IDE escribe (`.claude/settings.json`, `.mcp.json`, equivalentes de cursor, codex, opencode, pi, antigravity, hermes, vscode, windsurf, zed).
- Identificar si cada IDE soporta delegacion nativa a subagentes y, si si, que mecanismo usa (Task tool, comando CLI, agent invocation, etc.).

### Task 0.3 — Inventariar callers del delegate experimental

Buscar en el repo todas las invocaciones de:
- `cortex_delegate_task` (string + import)
- `cortex_delegate_batch` (string + import)
- `_delegate_task`, `_delegate_batch` (metodos internos)
- `_store_task_result`, `_get_task_result` (helpers asociados)

Reportar:
- Path:linea de cada caller.
- Si el caller esta en codigo de produccion o solo en tests/scripts.
- Si la eliminacion del tool dejaria al caller huerfano o si el caller tiene fallback.

### Task 0.4 — Inventariar el estado del MCP server

Documentar el shape actual del MCP server (`cortex/mcp/server.py`):
- Lista de tools expuestos via `handle_list_tools`.
- Operaciones que ejecutan subprocess (git, otros).
- Operaciones que cargan modelos (ONNX, embeddings).
- Operaciones que pueden bloquear (IO de disco, red, locks).
- Configuracion de logging (handlers, destinos).
- Manejo de concurrencia (threads, asyncio, locks).

### Task 0.5 — Producir INVENTARIO.md

Consolidar todo en `docs/multi-ide-mcp-hardening/INVENTARIO.md` con la siguiente estructura:

```markdown
# Inventario — estado previo al plan multi-IDE & MCP hardening
Fecha: 2026-05-15

## 1. Copias paralelas de prompts
| Logical name | Path A | Path B | Diferencias semanticas |

## 2. Adapters de IDE
| IDE | Adapter file | tools nativos | config files | mecanismo de delegacion |

## 3. Callers del delegate MCP
| Caller path:linea | Tipo (prod/test/script) | Huerfanizable |

## 4. Shape actual del MCP server
- Tools expuestos: [...]
- Subprocess sites: [...]
- Lazy loaded models: [...]
- Bloqueantes potenciales: [...]
- Logging: [...]
- Concurrencia: [...]

## 5. Hallazgos imprevistos
(Cualquier cosa que aparezca que NO estaba en el plan original)
```

---

## Archivos involucrados (read-only)

- Todos los listados en Tasks 0.1 a 0.4.
- Output: `docs/multi-ide-mcp-hardening/INVENTARIO.md` (nuevo).

---

## Criterios de aceptacion

- [ ] `INVENTARIO.md` existe y cubre las 5 secciones.
- [ ] Cada copia de prompt tiene su diff documentado (o se documenta explicitamente "identicos byte a byte").
- [ ] Cada adapter de IDE tiene su tabla de nombres de tools.
- [ ] Todos los callers del delegate estan listados con path:linea.
- [ ] Hallazgos imprevistos discutidos con el creador antes de cerrar la fase.

---

## Gate de cero deuda tecnica

- [ ] No queda ninguna pregunta abierta sobre "hay mas copias de X?" — la busqueda fue exhaustiva.
- [ ] Si Task 0.1 detecto drift semantico entre copias, esta documentado en `INVENTARIO.md` como input para Fase 4 (no se "resuelve" en Fase 0; pero queda registrado).
- [ ] Si Task 0.3 detecto callers huerfanizables, esta listado para Fase 5.
- [ ] No hay archivos creados/modificados de codigo. Esta fase es 100% read + 1 documento.

---

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| El inventario subestima copias y aparecen mas durante Fase 4 | Usar `grep` exhaustivo con varias queries (nombre del agente, partial paths, doc_type tokens). Documentar la query exacta para que la Fase 4 pueda re-validar. |
| Los nombres reales de tools de algunos IDEs cambiaron en versiones recientes | Cross-checkear contra la documentacion oficial de cada IDE; si hay duda, marcar como "verificar en runtime durante Fase 3". |
| Un caller del delegate vive fuera del repo (en cortex-pi separado, en docs externos) | Documentar el alcance limitado del inventario en `INVENTARIO.md` y advertir en Fase 5. |

---

## Estimacion

1-2 sesiones (sin tocar codigo). El bottleneck es leer y diff de los prompts, no producir el reporte.

---

## Handoff a Fase 1

`INVENTARIO.md` esta cerrado y aprobado por el creador. Las secciones 4 (shape MCP) y 5 (hallazgos) son input directo de Fase 1.

Output formal del handoff:

```yaml
agent: fase-0-inventario
status: completed
artifacts_produced:
  - docs/multi-ide-mcp-hardening/INVENTARIO.md
verified_claims:
  - "Cubierta la totalidad de copias de prompts canonicos en el repo"
  - "Cubiertos todos los adapters de IDE en cortex/ide/adapters/"
  - "Cubierto el shape actual de cortex/mcp/server.py"
unverified_claims:
  - "(si aplica) callers del delegate fuera del repo no inventariados"
context_for_next:
  - "Fase 1 puede empezar; Fase 3 puede empezar en paralelo si se decide asi"
```
