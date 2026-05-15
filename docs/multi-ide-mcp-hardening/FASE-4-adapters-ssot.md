# FASE 4 — Adapters de IDE leen de SSoT y traducen via canonical_tools

**Semaforo:** Amarillo (toca el flujo de instalacion de todos los adopters).
**Pre-requisitos:** Fase 0 cerrada, Fase 2 cerrada, Fase 3 cerrada.
**Bloquea:** Fase 5.

---

> ## IMPORTANTE — Alcance corregido (firmado 2026-05-15)
>
> Este archivo fue escrito originalmente asumiendo que los 11 adapters podian tratarse uniformemente con un solo patron de "lectura SSoT + traduccion de tools". La investigacion contra documentacion oficial 2026 (consolidada en [`MATRIZ-NATIVA-IDES.md`](MATRIZ-NATIVA-IDES.md)) revelo que la realidad es heterogenea. El creador firmo las decisiones arquitecturales en `MATRIZ-NATIVA-IDES.md` seccion 4. Lectura obligatoria antes de empezar Fase 4.
>
> **Alcance corregido** (`MATRIZ-NATIVA-IDES.md` seccion 5):
>
> | Adapter | Accion | Tamaño |
> |---|---|---|
> | `claude_code` | Inyectar `tools` traducido en frontmatter de subagents. | Pequeño |
> | `opencode` | Limpiar `tools` field (solo lowercase nativos). | Mediano |
> | `cursor` | **Rediseno**: 3 subagents en `.cursor/agents/`, eliminar SDDwork-cursor hibrido y `build_cursor_prompts()`. | Mediano |
> | `codex` | **Rediseno**: AGENTS.md en root con flujo secuencial, MCP en TOML `[mcp_servers.cortex]`, eliminar `.codex/agents/*.md` y `.codex/skills/*.md`. | Grande |
> | `pi` | **NO TOCAR** (decision 1 del creador — respeta contribuciones de comunidad en `cortex-pi/`). | Cero |
> | `vscode`, `claude_desktop`, `windsurf`, `antigravity`, `hermes`, `zed` | Marcar como "no validado contra docs oficiales 2026" en `cortex/ide/registry.py` y en doc. **No reescribir codigo**. | Cero (solo metadata) |
>
> El resto del documento describe el patron general (lectura SSoT, canonical-tools translation, no reescritura de body). Ese patron sigue siendo correcto para claude_code, opencode, cursor — pero NO para codex (que es rediseno total) ni pi (no se toca).

---

## Objetivo

Refactorizar los adapters en `cortex/ide/adapters/*.py` para que:

1. Lean los prompts canonicos **exclusivamente** desde `.cortex/subagents/*.md` y `.cortex/skills/*.md` (Single Source of Truth).
2. Traduzcan el frontmatter `tools:` usando `cortex/ide/canonical_tools.py`.
3. **NO modifiquen el cuerpo del prompt.** Cero reescritura semantica.
4. Generen los archivos especificos del IDE en el formato correcto (path, frontmatter, sintaxis).
5. Inyecten el bloque pre-flight check de `cortex_ping` en los prompts canonicos correspondientes (cortex-documenter, cortex-code-explorer, cortex-code-implementer).

Coherencia con principio rector #2 (SSoT) y #5 (instalacion es especifica por IDE, comportamiento es uniforme).

---

## Tasks

### Task 4.1 — Auditar drift entre `cortex-pi/.pi/agents/` y `.cortex/subagents/`

Esto se basa en lo que `INVENTARIO.md` (Fase 0, Task 0.1) reporto:

- **Si los archivos son identicos byte a byte (modulo whitespace):** marcar `cortex-pi/.pi/agents/` como obsoleta. Tras la fase, el adapter de opencode/pi GENERA su propia copia desde `.cortex/subagents/`. La copia estatica se borra.
- **Si hay drift semantico:** decidir con el creador cual version es la correcta. Reconciliar en `.cortex/subagents/`. Luego eliminar `cortex-pi/.pi/agents/`.

**Output de la task:** una decision documentada en `docs/multi-ide-mcp-hardening/DRIFT-RESOLUTION.md` que registre cada archivo, cual version se mantuvo, y por que.

### Task 4.2 — Refactorizar `claude_code` adapter

**Archivo:** `cortex/ide/adapters/claude_code.py`.

**Cambios:**
- En `inject_profiles`: leer cada subagente desde `.cortex/subagents/<name>.md` (ya pasa, pero confirmar).
- Para el frontmatter del archivo inyectado en `.claude/agents/<name>.md`:
  - `name:` y `description:` literal del archivo canonico.
  - `tools:` traducido usando `canonical_tools.translate_list(<lista_canonica_del_canonico>, "claude_code")`.
  - Para extraer la lista canonica del archivo canonico, parsear su frontmatter `tools:` (esto requiere que los archivos canonicos en `.cortex/subagents/` tengan la lista de tools en su frontmatter — ya la tienen, ej. `tools: read_file, write_file, cortex_save_session, ...`).
- El cuerpo del prompt: copia literal, sin reescritura. La funcion actual `strip_markdown_frontmatter` se mantiene.
- **Inyectar el bloque pre-flight check** en los prompts de `cortex-documenter`, `cortex-code-explorer`, `cortex-code-implementer`. Este bloque se inyecta **en el archivo canonico** (.cortex/subagents/*.md), no en la copia del IDE — asi todos los IDEs lo heredan.

### Task 4.3 — Refactorizar adapters restantes uniformemente

Aplicar el mismo patron a:
- `cortex/ide/adapters/opencode.py`
- `cortex/ide/adapters/cursor.py`
- `cortex/ide/adapters/codex.py`
- `cortex/ide/adapters/pi.py`
- `cortex/ide/adapters/vscode.py`
- `cortex/ide/adapters/windsurf.py`
- `cortex/ide/adapters/zed.py`
- `cortex/ide/adapters/antigravity.py`
- `cortex/ide/adapters/claude_desktop.py`
- `cortex/ide/adapters/hermes.py`

Cada adapter:
- Lee desde `.cortex/subagents/` y `.cortex/skills/`.
- Frontmatter traducido via `canonical_tools.translate_list`.
- Cuerpo literal.
- Configura el MCP server discovery en el archivo de config del IDE.
- Genera la sintaxis nativa de delegacion del IDE (ver Task 4.4).

### Task 4.4 — Definir mecanismo de delegacion por IDE

Para cada adapter, declarar explicitamente como soporta la delegacion a subagentes:

| IDE | Mecanismo de delegacion |
|---|---|
| claude_code | Task tool nativo con `subagent_type: <name>`; archivos en `.claude/agents/<name>.md` |
| opencode | Comando `opencode run --agent <path> --task <text>` |
| cursor | (a definir, dependiendo de soporte de Cursor para subagentes) |
| codex | (a definir) |
| pi | (a definir, posiblemente igual que opencode) |
| ... | ... |

Si un IDE NO soporta subagentes nativamente, el adapter declara `supports_delegation = False` y la documentacion del IDE en este plan deja claro que el agente principal asume el trabajo (no falla, no fallback opencode).

**Archivo nuevo:** `cortex/ide/base.py` (probablemente ya existe; ampliar) con un atributo declarativo `supports_delegation: bool` y `delegation_mechanism: str` para cada adapter.

### Task 4.5 — Inyectar bloque pre-flight check en prompts canonicos

**Archivos modificados:**
- `.cortex/subagents/cortex-documenter.md`
- `.cortex/subagents/cortex-code-explorer.md`
- `.cortex/subagents/cortex-code-implementer.md`
- `cortex-pi/.pi/agents/cortex-SDDwork.md` (si Task 4.1 confirmo que esta es la SSoT del SDDwork; si no, reconciliar a `.cortex/subagents/`)
- `cortex-pi/.pi/agents/cortex-sync.md` (idem)

**Bloque a inyectar (al inicio del cuerpo, antes de "Tabla de Routing Canonica" o equivalente):**

```markdown
## Pre-flight check (obligatorio)

Antes de cualquier otra operacion, invocar `cortex_ping`. Si la respuesta no es `status: ok`, abortar la operacion con error claro al usuario:

> El MCP server de Cortex no esta disponible (status: <status>; last_error: <error>). Reinicia el IDE o ejecuta `cortex doctor` para diagnosticar.

NO intentar fallback manual. NO escribir markdown a mano. NO degradar features.

---
```

### Task 4.6 — Eliminar copias paralelas en `cortex-pi/.pi/agents/`

Una vez que los adapters generan correctamente sus copias desde SSoT, las copias estaticas en `cortex-pi/.pi/agents/` (que actualmente sirven como SSoT secundaria para opencode/pi) **se eliminan del git**.

El adapter de pi/opencode las regenera al hacer `cortex setup`. El adopter las ve aparecer en su propia copia local del proyecto, no en el repo de Cortex.

**Excepcion:** si Fase 4 Task 4.1 detecta archivos en `cortex-pi/.pi/agents/` que NO tienen contraparte en `.cortex/subagents/`, esos primero se migran a `.cortex/subagents/` (con discusion de drift) y luego se elimina la copia paralela.

### Task 4.7 — Tests por adapter

Para cada adapter:
- Test unitario: `inject_profiles(project_root)` produce el archivo esperado en el path esperado, con el frontmatter esperado y el cuerpo literal del canonico.
- Test de integridad: el cuerpo inyectado es **byte-equivalente** al cuerpo canonico (modulo el bloque pre-flight check inyectado por Task 4.5, que es deterministico).

---

## Archivos involucrados

- Modificados:
  - `cortex/ide/adapters/*.py` (los 11 adapters listados).
  - `cortex/ide/base.py` (agregar atributos declarativos).
  - `.cortex/subagents/*.md` (inyectar pre-flight check en los que corresponda).
  - `cortex-pi/.pi/agents/*.md` (reconciliacion + posible eliminacion).
- Nuevos:
  - `tests/unit/ide/test_<adapter>_inject.py` (uno por adapter).
  - `docs/multi-ide-mcp-hardening/DRIFT-RESOLUTION.md`.
- Eliminados:
  - `cortex-pi/.pi/agents/*.md` (los que se decidio borrar en Task 4.6).

---

## Criterios de aceptacion

- [ ] Cada adapter pasa su test de inyeccion (frontmatter correcto + cuerpo literal).
- [ ] El cuerpo de los prompts canonicos NO se reescribe en ningun adapter (verificado por test byte-equivalente).
- [ ] El bloque pre-flight check aparece en los prompts canonicos de los 3 (o mas) subagentes que usan MCP de Cortex.
- [ ] `cortex-pi/.pi/agents/` se vacio (o se documento por que algun archivo se mantuvo).
- [ ] La inyeccion en Claude Code regenera correctamente `.claude/agents/cortex-documenter.md` con `tools: Read, Write, mcp__cortex__cortex_save_session, ...` (frontmatter traducido).
- [ ] Smoke manual: en un proyecto limpio, correr `cortex setup full --ide claude-code` y verificar que los archivos generados son correctos.

---

## Gate de cero deuda tecnica

- [ ] CERO archivos canonicos duplicados sin justificacion documentada.
- [ ] CERO adapters que reescriben el cuerpo del prompt.
- [ ] CERO referencias a `read_file` / `write_file` / nombres canonicos en el frontmatter inyectado por adapters de IDEs que no usan esos nombres.
- [ ] CERO codigo de "compatibilidad legacy" para mantener las copias paralelas que se eliminan.
- [ ] La `DRIFT-RESOLUTION.md` cierra explicitamente cada conflicto detectado en Task 4.1.
- [ ] CHANGELOG actualizado: "Multi-IDE uniformity: prompts canonicos ahora son SSoT, adapters traducen via canonical_tools."
- [ ] No se introducen flags de feature para "viejo modo" vs "nuevo modo" — el corte es definitivo.

---

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Eliminar `cortex-pi/.pi/agents/` rompe a un adopter de opencode que ya tenia el repo clonado | Documentar en CHANGELOG: "Re-correr `cortex setup agent --ide opencode` para regenerar." Idempotencia del setup garantiza no romper estado. |
| El bloque pre-flight check inyectado en .cortex/subagents/ rompe la lectura del archivo si tiene un parser estricto | El bloque es markdown estandar; se inyecta antes del primer `##` del cuerpo. Tests de parsing unitario. |
| Un adapter de IDE nuevo se agrega despues sin actualizar `canonical_tools.py` | Test de Fase 3 (`test_no_orphan_ides`) lo bloquea en CI. |
| Un IDE no soporta delegacion: el agente principal queda sobrecargado | Documentar la limitacion del IDE en `docs/architecture/ide-support-matrix.md` (nuevo). El usuario decide si usa ese IDE sabiendo el trade-off. |

---

## Estimacion

3 sesiones. La cantidad de adapters (11) es lo que mas tiempo come. Cada adapter es repetitivo pero requiere validacion individual.

---

## Handoff a Fase 5

```yaml
agent: fase-4-adapters-ssot
status: completed
artifacts_produced:
  - cortex/ide/adapters/*.py (11 adapters refactorizados)
  - cortex/ide/base.py (atributos declarativos)
  - .cortex/subagents/*.md (con pre-flight check)
  - tests/unit/ide/test_<adapter>_inject.py (11 tests)
  - docs/multi-ide-mcp-hardening/DRIFT-RESOLUTION.md
  - docs/architecture/ide-support-matrix.md
artifacts_removed:
  - cortex-pi/.pi/agents/*.md (los obsoletos)
verified_claims:
  - "Cada adapter genera la inyeccion correcta sin tocar cuerpo del prompt"
  - "Pre-flight check presente en los subagentes que usan MCP"
  - "Single Source of Truth confirmada en .cortex/subagents/ y .cortex/skills/"
context_for_next:
  - "Fase 5 puede eliminar cortex_delegate_task del MCP — cada IDE ya tiene su delegacion nativa"
```
